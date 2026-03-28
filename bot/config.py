import dataclasses
import os


@dataclasses.dataclass(frozen=True)
class BotConfig:
    telegram_token: str
    openai_api_key: str
    rate_limit_per_minute: int = 20
    openai_model: str = "gpt-5.4-mini-2026-03-17"
    system_prompt: str = "You are a helpful personal assistant on Telegram. Be concise."


def load_config() -> BotConfig:
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()

    if not token:
        raise RuntimeError("TELEGRAM_TOKEN environment variable is required but not set.")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is required but not set.")

    rate_limit = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "20"))

    return BotConfig(
        telegram_token=token,
        openai_api_key=api_key,
        rate_limit_per_minute=rate_limit,
    )
