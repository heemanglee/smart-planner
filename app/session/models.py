"""Session and Message data models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Tool call information."""

    id: str
    name: str
    input: dict[str, Any]
    result: dict[str, Any] | None = None


class Message(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Message role: user, assistant, or tool")
    content: str = Field(default="", description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tool_calls: list[ToolCall] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tool_calls": [tc.model_dump() for tc in self.tool_calls],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        """Create from dictionary."""
        return cls(
            role=data["role"],
            content=data.get("content", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tool_calls=[ToolCall(**tc) for tc in data.get("tool_calls", [])],
        )


class Session(BaseModel):
    """Chat session model."""

    id: str = Field(..., description="Unique session ID")
    title: str = Field(default="New Session", description="Session title")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    messages: list[Message] = Field(default_factory=list)
    total_tokens: int = Field(default=0, description="Total tokens used")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [msg.to_dict() for msg in self.messages],
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            title=data.get("title", "New Session"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
            total_tokens=data.get("total_tokens", 0),
        )

    def add_message(self, message: Message) -> None:
        """Add a message to the session."""
        self.messages.append(message)
        self.updated_at = datetime.utcnow()

    def get_messages_for_api(self) -> list[dict[str, Any]]:
        """Get messages in Claude API format.
        
        Includes tool_use and tool_result messages so that Claude can
        reference previous tool results and avoid redundant API calls.
        """
        import json
        from decimal import Decimal
        
        def decimal_default(obj):
            """Convert Decimal to float for JSON serialization."""
            if isinstance(obj, Decimal):
                # Convert to int if it's a whole number, otherwise float
                if obj % 1 == 0:
                    return int(obj)
                return float(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
        
        api_messages = []
        for msg in self.messages:
            if msg.role == "user":
                api_messages.append({
                    "role": "user",
                    "content": msg.content,
                })
            elif msg.role == "assistant":
                if msg.tool_calls:
                    # Assistant message with tool calls
                    content = []
                    if msg.content:
                        content.append({"type": "text", "text": msg.content})
                    for tc in msg.tool_calls:
                        content.append({
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": tc.input,
                        })
                    api_messages.append({
                        "role": "assistant",
                        "content": content,
                    })
                    # Add tool results as user message (Claude API format)
                    tool_results = []
                    for tc in msg.tool_calls:
                        if tc.result is not None:
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tc.id,
                                "content": json.dumps(tc.result, ensure_ascii=False, default=decimal_default),
                            })
                    if tool_results:
                        api_messages.append({
                            "role": "user",
                            "content": tool_results,
                        })
                else:
                    api_messages.append({
                        "role": "assistant",
                        "content": msg.content,
                    })
        return api_messages