import dataclasses
import os
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text()


def _compose_prompt(name: str) -> str:
    tone = _load_prompt("tone")
    body = _load_prompt(name)
    return f"{body}\n\n{tone}"


@dataclasses.dataclass(frozen=True)
class BotConfig:
    telegram_token: str
    openai_api_key: str
    odoo_url: str
    odoo_db: str
    odoo_user: str
    odoo_password: str
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "CwhRBWXzGAHq8TQ4Fs17"
    tavily_api_key: str = ""
    rate_limit_per_minute: int = 20
    openai_model: str = "gpt-5.4-2026-03-05"
    system_prompt: str = dataclasses.field(default_factory=lambda: _compose_prompt("system"))
    onboarding_prompt: str = dataclasses.field(default_factory=lambda: _compose_prompt("system_onboarding"))
    # Web API settings
    jwt_secret: str = ""
    sqlite_path: str = "data/hodoor.db"
    api_port: int = 8000
    # Jeedom (Bran module)
    jeedom_url: str = ""
    jeedom_api_key: str = ""
    jeedom_mock: bool = False


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
        odoo_url=os.environ.get("ODOO_URL", "http://localhost:8069"),
        odoo_db=os.environ.get("ODOO_DB", "homeops"),
        odoo_user=os.environ.get("ODOO_USER", ""),
        odoo_password=os.environ.get("ODOO_PASSWORD", ""),
        elevenlabs_api_key=os.environ.get("ELEVENLABS_API_KEY", ""),
        elevenlabs_voice_id=os.environ.get("ELEVENLABS_VOICE_ID", "CwhRBWXzGAHq8TQ4Fs17"),
        tavily_api_key=os.environ.get("TAVILY_API_KEY", ""),
        rate_limit_per_minute=rate_limit,
        jwt_secret=os.environ.get("JWT_SECRET", ""),
        sqlite_path=os.environ.get("SQLITE_PATH", "data/hodoor.db"),
        api_port=int(os.environ.get("PORT", os.environ.get("API_PORT", "8000"))),
        jeedom_url=os.environ.get("JEEDOM_URL", "http://localhost:9080"),
        jeedom_api_key=os.environ.get("JEEDOM_API_KEY", ""),
        jeedom_mock=os.environ.get("JEEDOM_MOCK", "").lower() in ("true", "1", "yes"),
    )
