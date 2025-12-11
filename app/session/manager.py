"""Session manager for DynamoDB operations."""

import uuid
from datetime import datetime

from botocore.exceptions import ClientError

from app.db import create_sessions_table, get_table
from app.session.models import Message, Session


class SessionManager:
    """Manager for session CRUD operations."""

    def __init__(self) -> None:
        create_sessions_table()
        self._table = get_table()

    def create_session(self, title: str = "New Session") -> Session:
        """Create a new session.

        Args:
            title: Session title.

        Returns:
            Created session.
        """
        session = Session(
            id=str(uuid.uuid4()),
            title=title,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self._table.put_item(Item=session.to_dict())
        return session

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID.

        Args:
            session_id: Session ID.

        Returns:
            Session or None if not found.
        """
        try:
            response = self._table.get_item(Key={"id": session_id})
            item = response.get("Item")
            if item:
                return Session.from_dict(item)
            return None
        except ClientError:
            return None

    def list_sessions(self, limit: int = 50) -> list[Session]:
        """List all sessions.

        Args:
            limit: Maximum number of sessions to return.

        Returns:
            List of sessions sorted by updated_at desc.
        """
        try:
            response = self._table.scan(Limit=limit)
            items = response.get("Items", [])

            sessions = [Session.from_dict(item) for item in items]
            sessions.sort(key=lambda s: s.updated_at, reverse=True)
            return sessions
        except ClientError:
            return []

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session ID.

        Returns:
            True if deleted, False otherwise.
        """
        try:
            self._table.delete_item(Key={"id": session_id})
            return True
        except ClientError:
            return False

    def update_session(self, session: Session) -> bool:
        """Update a session.

        Args:
            session: Session to update.

        Returns:
            True if updated, False otherwise.
        """
        try:
            session.updated_at = datetime.utcnow()
            self._table.put_item(Item=session.to_dict())
            return True
        except ClientError:
            return False

    def add_message(self, session_id: str, message: Message) -> bool:
        """Add a message to a session.

        Args:
            session_id: Session ID.
            message: Message to add.

        Returns:
            True if added, False otherwise.
        """
        session = self.get_session(session_id)
        if not session:
            return False

        session.add_message(message)
        return self.update_session(session)

    def get_messages(self, session_id: str) -> list[Message]:
        """Get all messages from a session.

        Args:
            session_id: Session ID.

        Returns:
            List of messages.
        """
        session = self.get_session(session_id)
        if not session:
            return []
        return session.messages

    def update_title(self, session_id: str, title: str) -> bool:
        """Update session title.

        Args:
            session_id: Session ID.
            title: New title.

        Returns:
            True if updated, False otherwise.
        """
        session = self.get_session(session_id)
        if not session:
            return False

        session.title = title
        return self.update_session(session)

    def update_tokens(self, session_id: str, tokens: int) -> bool:
        """Update total tokens used.

        Args:
            session_id: Session ID.
            tokens: Tokens to add.

        Returns:
            True if updated, False otherwise.
        """
        session = self.get_session(session_id)
        if not session:
            return False

        session.total_tokens += tokens
        return self.update_session(session)