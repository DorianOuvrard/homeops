import logging

from openai import OpenAI, APIError, APIConnectionError, RateLimitError

from bot.config import BotConfig

logger = logging.getLogger(__name__)


def get_response(
    text: str,
    config: BotConfig,
    image_urls: list[str] | None = None,
    history: list[dict] | None = None,
) -> str:
    """Send text (and optionally images) to OpenAI ChatGPT and return the reply.

    Returns a user-friendly error message instead of raising, so callers
    never need to handle LLM exceptions.
    """
    client = OpenAI(api_key=config.openai_api_key)

    if image_urls:
        user_content: list[dict] | str = [
            {"type": "image_url", "image_url": {"url": url}}
            for url in image_urls
        ]
        user_content.append({"type": "text", "text": text or "Describe what you see."})
    else:
        user_content = text

    messages = [{"role": "system", "content": config.system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_content})

    try:
        completion = client.chat.completions.create(
            model=config.openai_model,
            messages=messages,
        )
        return completion.choices[0].message.content or "(empty response)"
    except RateLimitError:
        logger.warning("OpenAI rate limit hit.")
        return "I'm being rate-limited by the AI provider right now. Please try again in a moment."
    except APIConnectionError:
        logger.warning("OpenAI connection error.")
        return "I couldn't reach the AI service. Check your internet connection and try again."
    except APIError as exc:
        logger.error("OpenAI API error: %s", exc)
        return "The AI service returned an error. Please try again later."
    except Exception as exc:
        logger.error("Unexpected LLM error: %s", exc)
        return "Something went wrong on my end. Please try again."
