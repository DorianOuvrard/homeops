import logging

from openai import OpenAI, APIError, APIConnectionError, RateLimitError

from bot.config import BotConfig

logger = logging.getLogger(__name__)


def get_response(text: str, config: BotConfig) -> str:
    """Send text to OpenAI ChatGPT and return the reply.

    Returns a user-friendly error message instead of raising, so callers
    never need to handle LLM exceptions.
    """
    client = OpenAI(api_key=config.openai_api_key)

    try:
        completion = client.chat.completions.create(
            model=config.openai_model,
            messages=[
                {"role": "system", "content": config.system_prompt},
                {"role": "user", "content": text},
            ],
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
