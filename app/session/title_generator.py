"""Session title generator using Claude."""

import anthropic

from app.config import settings


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
                        f"Generate a short, descriptive title (max 5 words) for a chat "
                        f"session that starts with this message. Return only the title, "
                        f"no quotes or punctuation:\n\n{first_message}"
                    ),
                }
            ],
        )

        title = response.content[0].text.strip()
        return title[:50] if len(title) > 50 else title

    except Exception:
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