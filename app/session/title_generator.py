"""Session title generator using Claude."""
import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)


async def generate_title(first_message: str) -> str:
    """Generate a session title from the first user message.

    Args:
        first_message: The first user message in the session.

    Returns:
        Generated title (max 50 chars).
    """
    if not settings.anthropic_api_key:
        return _fallback_title(first_message)

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=50,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"다음 사용자 메시지를 요약하여 짧은 제목(최대 5단어)을 생성해주세요. "
                        f"제목만 반환하고, 따옴표나 구두점은 제외해주세요:\n\n{first_message}"
                    ),
                }
            ],
        )
        title = response.content[0].text.strip()
        logger.info(f"generated title: {title}")

        return title[:50] if len(title) > 50 else title

    except Exception as e:
        logger.error(f"Failed to generate title: {e}")
        return _fallback_title(first_message)


def _fallback_title(message: str) -> str:
    """Generate fallback title from message.

    Args:
        message: User message.

    Returns:
        Truncated message as title.
    """
    title = message.strip()[:47]
    if len(message) > 47:
        title += "..."
    return title


async def regenerate_title_from_conversation(messages: list[dict]) -> str:
    """Regenerate a session title from full conversation history.

    Args:
        messages: List of conversation messages with 'role' and 'content' keys.

    Returns:
        Generated title (max 50 chars).
    """
    if not messages:
        return "New Session"

    if not settings.anthropic_api_key:
        # Fallback: use first user message
        for msg in messages:
            if msg.get("role") == "user":
                return _fallback_title(msg.get("content", ""))
        return "New Session"

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        # Build conversation summary
        conversation_text = "\n".join(
            f"{msg['role'].upper()}: {msg['content'][:200]}"
            for msg in messages
            if msg.get("role") in ("user", "assistant")
        )

        # Limit to avoid token overflow
        if len(conversation_text) > 1500:
            conversation_text = conversation_text[:1500] + "..."

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=50,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"다음 대화 내용을 요약하여 짧은 제목(최대 5단어)을 생성해주세요. "
                        f"제목만 반환하고, 따옴표나 구두점은 제외해주세요:\n\n{conversation_text}"
                    ),
                }
            ],
        )
        logger.info(f"regenerated title: {response.content[0].text}")

        title = response.content[0].text.strip()
        return title[:50] if len(title) > 50 else title

    except Exception as e:
        logger.error(f"Failed to regenerate title: {e}")
        # Fallback: use first user message
        for msg in messages:
            if msg.get("role") == "user":
                return _fallback_title(msg.get("content", ""))
        return "New Session"
