import asyncio
import html
import io
import logging
import re
from datetime import datetime, timedelta
from functools import partial

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot.chat_registry import ChatRegistry
from bot.config import BotConfig, load_config
from bot.handlers import (
    calendar_handler,
    new_handler,
    photo_handler,
    plan_handler,
    reset_handler,
    scan_handler,
    text_handler,
    testreminder_handler,
    todayevents_handler,
    video_handler,
    video_note_handler,
    voice_handler,
    watchcalendar_handler,
)
from bot.history import ConversationHistory
from bot.odoo import OdooClient, OdooConfig
from bot.rate_limiter import RateLimiter
from bot.tts import text_to_speech

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _format_calendar_text(raw_text: str | None) -> str:
    if not raw_text:
        return ""
    text = raw_text
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


async def send_calendar_reminders(app, odoo, chat_registry, reminded: set[str]) -> None:
    now = datetime.utcnow()
    window_start = now + timedelta(minutes=1)
    window_end = window_start + timedelta(minutes=1)

    try:
        result = odoo.get_events_between(window_start, window_end)
    except Exception as exc:  # pragma: no cover - network/service errors
        logger.warning("Calendar reminder scan failed: %s", exc)
        return

    chat_ids = chat_registry.all()
    if not chat_ids:
        return

    for record in result["records"]:
        reminder_key = f"{record['id']}:{record.get('schedule_date')}"
        if reminder_key in reminded:
            continue

        description_text = _format_calendar_text(record.get("description"))
        display_text = _format_calendar_text(record.get("display_name"))
        name_text = _format_calendar_text(record.get("name"))
        reminder_text = (
            description_text
            or display_text
            or name_text
            or "Evenement sans description"
        )
        logger.info(
            "Calendar reminder due in 1 minute: id=%s start=%s text=%s",
            record.get("id"),
            record.get("schedule_date"),
            reminder_text,
        )
        message = reminder_text
        sent = False
        for chat_id in chat_ids:
            try:
                await _send_calendar_notification(app, chat_id, message, app.bot_data["bot_config"])
                sent = True
            except Exception as exc:  # pragma: no cover - Telegram/network errors
                logger.warning("Unable to send reminder to chat %s: %s", chat_id, exc)
        if sent:
            reminded.add(reminder_key)


async def _send_calendar_notification(app, chat_id: int, message: str, config: BotConfig) -> None:
    audio = await text_to_speech(message, config)
    if audio:
        await app.bot.send_voice(
            chat_id=chat_id,
            voice=io.BytesIO(audio),
            caption=message[:1024],
        )
        return
    await app.bot.send_message(chat_id=chat_id, text=message)


async def reminder_loop(app, odoo, chat_registry) -> None:
    reminded: set[str] = set()
    logger.info("Calendar reminder loop started")
    while True:
        await send_calendar_reminders(app, odoo, chat_registry, reminded)
        await asyncio.sleep(60)


async def on_startup(app, *, config, odoo, chat_registry) -> None:
    app.bot_data["bot_config"] = config
    app.bot_data["calendar_reminder_task"] = asyncio.create_task(
        reminder_loop(app, odoo, chat_registry)
    )


async def on_shutdown(app) -> None:
    task = app.bot_data.get("calendar_reminder_task")
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Calendar reminder loop stopped")


def main() -> None:
    config = load_config()
    rate_limiter = RateLimiter(max_per_minute=config.rate_limit_per_minute)
    history = ConversationHistory()
    chat_registry = ChatRegistry()
    odoo = OdooClient(OdooConfig(
        url=config.odoo_url, db=config.odoo_db,
        user=config.odoo_user, password=config.odoo_password,
    ))

    deps = {
        "config": config,
        "rate_limiter": rate_limiter,
        "chat_registry": chat_registry,
        "history": history,
        "odoo": odoo,
    }

    app = (
        Application.builder()
        .token(config.telegram_token)
        .post_init(partial(on_startup, config=config, odoo=odoo, chat_registry=chat_registry))
        .post_shutdown(on_shutdown)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "calendar",
            partial(
                calendar_handler,
                config=config,
                chat_registry=chat_registry,
                odoo=odoo,
            ),
        )
    )
    app.add_handler(CommandHandler("new", partial(new_handler, history=history)))
    app.add_handler(CommandHandler("reset", partial(reset_handler, history=history, odoo=odoo)))
    app.add_handler(CommandHandler("scan", partial(scan_handler, **deps)))
    app.add_handler(CommandHandler("plan", partial(plan_handler, **deps)))
    app.add_handler(CommandHandler("watchcalendar", partial(watchcalendar_handler, chat_registry=chat_registry)))
    app.add_handler(
        CommandHandler(
            "testreminder",
            partial(
                testreminder_handler,
                config=config,
                chat_registry=chat_registry,
                odoo=odoo,
            ),
        )
    )
    app.add_handler(
        CommandHandler(
            "todayevents",
            partial(
                todayevents_handler,
                config=config,
                chat_registry=chat_registry,
                odoo=odoo,
            ),
        )
    )
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
