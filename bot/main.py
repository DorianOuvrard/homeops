import logging
from functools import partial

from telegram.ext import Application, MessageHandler, filters

from bot.config import load_config
from bot.handlers import photo_handler, text_handler, video_handler, voice_handler
from bot.rate_limiter import RateLimiter

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    config = load_config()
    rate_limiter = RateLimiter(max_per_minute=config.rate_limit_per_minute)

    app = Application.builder().token(config.telegram_token).build()

    # Bind config and rate_limiter into each handler via partial so the handler
    # signatures remain compatible with python-telegram-bot's callback protocol.
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            partial(text_handler, config=config, rate_limiter=rate_limiter),
        )
    )
    app.add_handler(
        MessageHandler(
            filters.VOICE,
            partial(voice_handler, config=config, rate_limiter=rate_limiter),
        )
    )
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            partial(photo_handler, config=config, rate_limiter=rate_limiter),
        )
    )
    app.add_handler(
        MessageHandler(
            filters.VIDEO,
            partial(video_handler, config=config, rate_limiter=rate_limiter),
        )
    )

    logger.info("Bot starting (polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()
