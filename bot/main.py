import asyncio
import dataclasses
import html
import io
import logging
import re
from datetime import datetime, timedelta
from functools import partial

import uvicorn
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot.api.app import create_app
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
from bot.push import send_web_push_broadcast
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
    if result["count"]:
        logger.info(
            "Calendar reminder scan found %s event(s) between %s and %s",
            result["count"],
            result["start"],
            result["end"],
        )
    if not chat_ids:
        logger.info("No Telegram chats registered for reminders; web push will still be attempted")

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
        try:
            push_count = await send_web_push_broadcast(
                app.bot_data["bot_config"],
                "Rappel Hodoor",
                message,
            )
            logger.info("Web push reminder delivery count=%s for record id=%s", push_count, record.get("id"))
            if push_count:
                sent = True
        except Exception as exc:  # pragma: no cover - push/network errors
            logger.warning("Unable to send web push reminder: %s", exc)
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


def _build_telegram_app(config: BotConfig, deps: dict) -> Application:
    """Build the python-telegram-bot Application with all handlers registered."""
    app = Application.builder().token(config.telegram_token).build()

    app.add_handler(
        CommandHandler(
            "calendar",
            partial(
                calendar_handler,
                config=config,
                chat_registry=deps["chat_registry"],
                odoo=deps["odoo"],
            ),
        )
    )
    app.add_handler(CommandHandler("new", partial(new_handler, history=deps["history"])))
    app.add_handler(CommandHandler("reset", partial(reset_handler, history=deps["history"], odoo=deps["odoo"])))
    app.add_handler(CommandHandler("scan", partial(scan_handler, config=config, rate_limiter=deps["rate_limiter"], history=deps["history"], odoo=deps["odoo"])))
    app.add_handler(CommandHandler("plan", partial(plan_handler, config=config, rate_limiter=deps["rate_limiter"], history=deps["history"], odoo=deps["odoo"])))
    app.add_handler(CommandHandler("watchcalendar", partial(watchcalendar_handler, chat_registry=deps["chat_registry"])))
    app.add_handler(
        CommandHandler(
            "testreminder",
            partial(
                testreminder_handler,
                config=config,
                chat_registry=deps["chat_registry"],
                odoo=deps["odoo"],
            ),
        )
    )
    app.add_handler(
        CommandHandler(
            "todayevents",
            partial(
                todayevents_handler,
                config=config,
                chat_registry=deps["chat_registry"],
                odoo=deps["odoo"],
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
    return app


def main() -> None:
    config = load_config()

    if config.jeedom_mock:
        from bot.bran.mock import API_KEY as _mock_api_key, PORT as _mock_port, start_in_thread
        start_in_thread()
        # Override Jeedom config to point at the embedded mock
        config = dataclasses.replace(
            config,
            jeedom_url=f"http://127.0.0.1:{_mock_port}",
            jeedom_api_key=_mock_api_key,
        )

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

    telegram_app = _build_telegram_app(config, deps)

    # Store config in bot_data so reminder loop can access it
    telegram_app.bot_data["bot_config"] = config

    # The reminder loop will be started after Telegram bot initializes
    # (inside FastAPI lifespan, after polling starts). We schedule it
    # as a coroutine that the lifespan will launch.
    async def start_reminder_loop():
        await asyncio.sleep(2)  # Brief delay to let bot connect
        reminder_task = asyncio.create_task(
            reminder_loop(telegram_app, odoo, chat_registry)
        )
        deps["reminder_task"] = reminder_task
        return reminder_task

    deps["telegram_app"] = telegram_app
    deps["start_reminder_loop"] = start_reminder_loop

    fastapi_app = create_app(config, deps)

    logger.info("Starting HODOOR API on port %d...", config.api_port)
    uvicorn.run(fastapi_app, host="0.0.0.0", port=config.api_port, log_level="info")


if __name__ == "__main__":
    main()
