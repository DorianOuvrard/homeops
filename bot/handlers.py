import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import BotConfig
from bot.llm import get_response
from bot.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

_RATE_LIMITED_MSG = (
    "You're sending messages too fast. Please wait a moment before trying again."
)


def _user_id(update: Update) -> int:
    # update.effective_user is always set for messages from real users.
    return update.effective_user.id  # type: ignore[union-attr]


async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    rate_limiter: RateLimiter,
) -> None:
    user_id = _user_id(update)

    if not rate_limiter.is_allowed(user_id):
        logger.info("Rate limit exceeded for user %d", user_id)
        await update.message.reply_text(_RATE_LIMITED_MSG)  # type: ignore[union-attr]
        return

    user_text = update.message.text or ""  # type: ignore[union-attr]
    logger.info("Text from user %d: %.80s", user_id, user_text)

    reply = get_response(user_text, config)
    await update.message.reply_text(reply)  # type: ignore[union-attr]


async def voice_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    rate_limiter: RateLimiter,
) -> None:
    user_id = _user_id(update)

    if not rate_limiter.is_allowed(user_id):
        await update.message.reply_text(_RATE_LIMITED_MSG)  # type: ignore[union-attr]
        return

    logger.info("Voice message from user %d", user_id)
    await update.message.reply_text(  # type: ignore[union-attr]
        "Received your voice message. Voice processing will be available in a future update."
    )


async def photo_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    rate_limiter: RateLimiter,
) -> None:
    user_id = _user_id(update)

    if not rate_limiter.is_allowed(user_id):
        await update.message.reply_text(_RATE_LIMITED_MSG)  # type: ignore[union-attr]
        return

    logger.info("Photo from user %d", user_id)
    await update.message.reply_text(  # type: ignore[union-attr]
        "Received your photo. Image analysis will be available in a future update."
    )


async def video_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    rate_limiter: RateLimiter,
) -> None:
    user_id = _user_id(update)

    if not rate_limiter.is_allowed(user_id):
        await update.message.reply_text(_RATE_LIMITED_MSG)  # type: ignore[union-attr]
        return

    logger.info("Video from user %d", user_id)
    await update.message.reply_text(  # type: ignore[union-attr]
        "Received your video. Video processing will be available in a future update."
    )
