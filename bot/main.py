import logging
from functools import partial

from telegram.ext import Application, MessageHandler, filters

from bot.config import load_config
from bot.handlers import photo_handler, text_handler, video_handler, video_note_handler, voice_handler
from bot.history import ConversationHistory
from bot.odoo import OdooClient, OdooConfig
from bot.rate_limiter import RateLimiter

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    config = load_config()
    rate_limiter = RateLimiter(max_per_minute=config.rate_limit_per_minute)
    history = ConversationHistory()
    odoo = OdooClient(OdooConfig(
        url=config.odoo_url, db=config.odoo_db,
        user=config.odoo_user, password=config.odoo_password,
    ))

    deps = {"config": config, "rate_limiter": rate_limiter, "history": history, "odoo": odoo}

    app = Application.builder().token(config.telegram_token).build()

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, partial(text_handler, **deps))
    )
    app.add_handler(
        MessageHandler(filters.VOICE, partial(voice_handler, **deps))
    )
    app.add_handler(
        MessageHandler(filters.PHOTO, partial(photo_handler, **deps))
    )
    app.add_handler(
        MessageHandler(filters.VIDEO, partial(video_handler, **deps))
    )
    app.add_handler(
        MessageHandler(filters.VIDEO_NOTE, partial(video_note_handler, **deps))
    )

    logger.info("Bot starting (polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()
