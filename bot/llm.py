import logging

from openai import OpenAI, APIError, APIConnectionError, RateLimitError

from bot.config import BotConfig
from bot.odoo import OdooClient
from bot.tools import TOOLS, dispatch

logger = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 10


def get_response(
    text: str,
    config: BotConfig,
    odoo: OdooClient,
    image_urls: list[str] | None = None,
    history: list[dict] | None = None,
    system_prompt: str | None = None,
    on_mode_change=None,
    on_tool_round=None,
    on_tool_call=None,
) -> str | tuple[str, list[str]]:
    """Send text (and optionally images) to OpenAI and return the reply.

    Supports tool calling: if the model requests a tool, we execute it
    and loop until a final text response (up to _MAX_TOOL_ROUNDS).
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

    messages = [{"role": "system", "content": system_prompt or config.system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_content})

    tools_used: list[str] = []

    try:
        for round_num in range(_MAX_TOOL_ROUNDS):
            completion = client.chat.completions.create(
                model=config.openai_model,
                messages=messages,
                tools=TOOLS,
            )
            msg = completion.choices[0].message

            if not msg.tool_calls:
                logger.info("Response after %d tool round(s)", round_num)
                logger.info("LLM reply: %.300s", msg.content)
                reply = msg.content or "(empty response)"
                return (reply, tools_used) if tools_used else reply

            messages.append(msg)

            if on_tool_round:
                on_tool_round()

            for tc in msg.tool_calls:
                logger.info("Round %d: %s(%s)", round_num + 1, tc.function.name, tc.function.arguments)
                tools_used.append(tc.function.name)
                if on_tool_call:
                    on_tool_call(tc.function.name)
                result = dispatch(config, odoo, tc.function.name, tc.function.arguments, on_mode_change=on_mode_change, image_urls=image_urls)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        logger.warning("Hit max tool rounds (%d)", _MAX_TOOL_ROUNDS)
        return "J'ai fait trop d'appels. Reformule ta demande plus simplement."

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
