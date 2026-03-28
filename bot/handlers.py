import asyncio
import base64
import asyncio
import io
import logging
import subprocess
import tempfile
import xmlrpc.client
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from bot.config import BotConfig
from bot.chat_registry import ChatRegistry
from bot.history import ConversationHistory
from bot.llm import get_response
from bot.odoo import OdooClient
from bot.rate_limiter import RateLimiter
from bot import session
from bot.tts import text_to_speech

logger = logging.getLogger(__name__)


def _typing_callback(update: Update):
    """Return a sync callback that refreshes the typing indicator between tool rounds."""
    def on_tool_round() -> None:
        loop = asyncio.get_event_loop()
        loop.create_task(update.message.chat.send_action(ChatAction.TYPING))  # type: ignore[union-attr]
    return on_tool_round


_RATE_LIMITED_MSG = (
    "You're sending messages too fast. Please wait a moment before trying again."
)
_CALENDAR_USAGE = (
    "Usage: /calendar DESCRIPTION | YYYY-MM-DD | HH:MM\n"
    "Exemple: /calendar Ajouter du sel dans le lave-vaisselle | 2026-03-28 | 18:30"
)


async def _send_delayed_test_reminder(application, chat_id: int, start_str: str) -> None:
    await asyncio.sleep(65)
    await application.bot.send_message(
        chat_id=chat_id,
        text=(
            "Rappel HomeOps de test: "
            f"l'evenement de test commence a {start_str}."
        ),
    )


def _format_odoo_calendar_fault(exc: xmlrpc.client.Fault, config: BotConfig) -> str:
    fault = exc.faultString or str(exc)
    if 'database "' in fault and '" does not exist' in fault:
        return (
            f"Impossible de creer l'evenement: la base Odoo configuree "
            f"({config.odoo_db}) n'existe pas."
        )
    if "AccessError" in fault or "access" in fault.lower():
        return (
            "Impossible de creer le rappel: le compte Odoo configure n'a pas "
            "les droits necessaires."
        )
    if (
        "calendar.event" in fault and "doesn't exist" in fault
    ) or (
        "maintenance.request" in fault and "doesn't exist" in fault
    ):
        return (
            "Impossible de creer le rappel: le module maintenance Odoo "
            "n'est pas disponible sur cette base."
        )
    return (
        "Impossible de creer le rappel dans Odoo. "
        f"Detail technique: {fault[:300]}."
    )


async def _send_typing(update: Update) -> None:
    await update.message.chat.send_action(ChatAction.TYPING)  # type: ignore[union-attr]


async def _reply(update: Update, reply: str, config: BotConfig) -> None:
    """Send text immediately, then follow up with TTS voice when ready."""
    await update.message.reply_text(reply)  # type: ignore[union-attr]
    await update.message.chat.send_action(ChatAction.RECORD_VOICE)  # type: ignore[union-attr]
    audio = await text_to_speech(reply, config)
    if audio:
        await update.message.reply_voice(voice=io.BytesIO(audio))  # type: ignore[union-attr]


async def new_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    history: ConversationHistory,
) -> None:
    user_id = _user_id(update)
    history.clear(user_id)
    await update.message.reply_text("Nouvelle conversation démarrée.")  # type: ignore[union-attr]


async def watchcalendar_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    chat_registry: ChatRegistry,
) -> None:
    chat_registry.add(_chat_id(update))
    await update.message.reply_text(  # type: ignore[union-attr]
        "Ce chat est maintenant inscrit aux rappels calendrier HomeOps."
    )


async def testreminder_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    chat_registry: ChatRegistry,
    odoo: OdooClient,
) -> None:
    chat_id = _chat_id(update)
    chat_registry.add(chat_id)

    start_at = datetime.utcnow() + timedelta(minutes=10, seconds=30)
    end_at = start_at + timedelta(hours=1)
    start_str = start_at.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_at.strftime("%Y-%m-%d %H:%M:%S")

    try:
        event = odoo.create_record(
            "maintenance.request",
            {
                "name": "HomeOps Test Reminder",
                "description": "Rappel de test HomeOps",
                "schedule_date": start_str,
                "maintenance_type": "preventive",
            },
        )
        reply = (
            "Test reminder programme. "
            f"Demande planifiee pour {start_str} UTC. "
            "Si le bot tourne toujours, le rappel devrait arriver dans environ une minute. "
            f"Reference: {event['record']['display_name'] or event['record']['id']}."
        )
        context.application.create_task(
            _send_delayed_test_reminder(context.application, chat_id, start_str)
        )
    except xmlrpc.client.Fault as exc:
        logger.exception("Odoo test reminder creation failed")
        reply = _format_odoo_calendar_fault(exc, config)

    await update.message.reply_text(reply)  # type: ignore[union-attr]


async def calendar_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    chat_registry: ChatRegistry,
    odoo: OdooClient,
) -> None:
    chat_registry.add(_chat_id(update))

    raw_args = " ".join(context.args).strip()
    if not raw_args:
        await update.message.reply_text(_CALENDAR_USAGE)  # type: ignore[union-attr]
        return

    parts = [part.strip() for part in raw_args.split("|")]
    if len(parts) != 3 or not all(parts):
        await update.message.reply_text(_CALENDAR_USAGE)  # type: ignore[union-attr]
        return

    description, date_str, time_str = parts
    try:
        start_at = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        await update.message.reply_text(  # type: ignore[union-attr]
            "Format de date ou d'heure invalide.\n" + _CALENDAR_USAGE
        )
        return

    try:
        event = odoo.create_record(
            "maintenance.request",
            {
                "name": description[:80],
                "description": description,
                "schedule_date": start_at.strftime("%Y-%m-%d %H:%M:%S"),
                "maintenance_type": "preventive",
            },
        )
        reply = (
            "Rappel ajoute dans les demandes de maintenance Odoo. "
            f"Description: {description}. "
            f"Date: {start_at.strftime('%Y-%m-%d %H:%M')}. "
            f"Reference: {event['record']['display_name'] or event['record']['id']}."
        )
    except xmlrpc.client.Fault as exc:
        logger.exception("Odoo calendar command creation failed")
        reply = _format_odoo_calendar_fault(exc, config)

    await update.message.reply_text(reply)  # type: ignore[union-attr]


async def todayevents_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    chat_registry: ChatRegistry,
    odoo: OdooClient,
) -> None:
    chat_registry.add(_chat_id(update))

    start_at = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_at = start_at.replace(hour=23, minute=59, second=59)

    try:
        result = odoo.get_events_between(start_at, end_at)
    except xmlrpc.client.Fault as exc:
        logger.exception("Odoo today events lookup failed")
        reply = _format_odoo_calendar_fault(exc, config)
        await update.message.reply_text(reply)  # type: ignore[union-attr]
        return

    records = result["records"]
    if not records:
        await update.message.reply_text(  # type: ignore[union-attr]
            "Aucune demande planifiee aujourd'hui dans Odoo."
        )
        return

    lines = ["Demandes planifiees du jour dans Odoo :"]
    for record in records:
        lines.append(
            f"- {record.get('schedule_date')} : {record.get('display_name') or record.get('name')}"
        )
    await update.message.reply_text("\n".join(lines[:40]))  # type: ignore[union-attr]


async def reset_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    history: ConversationHistory,
    odoo: OdooClient,
) -> None:
    """Hidden command: clear conversation history and delete all equipment in Odoo."""
    user_id = _user_id(update)
    history.clear(user_id)
    count = 0
    for model in ("maintenance.request", "maintenance.equipment"):
        result = odoo.search_records(model, domain=[], fields=["id"], limit=50)
        for rec in result.get("records", []):
            odoo.delete_record(model, rec["id"])
            count += 1
    await update.message.reply_text(f"Reset: historique vidé, {count} équipement(s) supprimé(s).")  # type: ignore[union-attr]


async def scan_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    rate_limiter: RateLimiter,
    history: ConversationHistory,
    odoo: OdooClient,
) -> None:
    """Hidden command: reset everything and force-trigger the onboarding discovery flow."""
    user_id = _user_id(update)
    history.clear(user_id)
    for model in ("maintenance.request", "maintenance.equipment"):
        result = odoo.search_records(model, domain=[], fields=["id"], limit=50)
        for rec in result.get("records", []):
            odoo.delete_record(model, rec["id"])
    session.force_onboarding(user_id)
    trigger_msg = "Salut"
    history.add_user(user_id, trigger_msg)
    cb = _typing_callback(update)
    reply = get_response(trigger_msg, config, odoo, history=[], system_prompt=config.onboarding_prompt, on_mode_change=session.mode_callback(user_id), on_tool_round=cb)
    history.add_assistant(user_id, reply)
    await _reply(update, reply, config)


async def plan_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    rate_limiter: RateLimiter,
    history: ConversationHistory,
    odoo: OdooClient,
) -> None:
    """Hidden command: skip to the end-of-scan recap and prevention plan."""
    user_id = _user_id(update)
    session.force_onboarding(user_id)
    await _send_typing(update)
    # Clear existing preventive maintenance requests to avoid duplicates
    result = odoo.search_records("maintenance.request", domain=[["maintenance_type", "=", "preventive"]], fields=["id"], limit=50)
    for rec in result.get("records", []):
        odoo.delete_record("maintenance.request", rec["id"])
    trigger_msg = "J'ai fini, fais le récap et le plan de prévention."
    history.add_user(user_id, trigger_msg)
    cb = _typing_callback(update)
    reply = get_response(trigger_msg, config, odoo, history=[], system_prompt=config.onboarding_prompt, on_mode_change=session.mode_callback(user_id), on_tool_round=cb)
    history.add_assistant(user_id, reply)
    await _reply(update, reply, config)


def _user_id(update: Update) -> int:
    return update.effective_user.id  # type: ignore[union-attr]


def _chat_id(update: Update) -> int:
    return update.effective_chat.id  # type: ignore[union-attr]


def _extract_video_frames(video_path: Path) -> tuple[list[str], float]:
    """Extract evenly spaced frames from a video file. Returns (base64 image URLs, duration)."""
    duration_result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True,
    )
    duration = float(duration_result.stdout.strip() or "1")
    num_frames = min(4, max(1, int(duration)))
    interval = duration / (num_frames + 1)

    frame_pattern = str(video_path.parent / "frame_%02d.jpg")
    subprocess.run(
        ["ffmpeg", "-i", str(video_path), "-vf",
         f"fps=1/{interval:.2f}", "-frames:v", str(num_frames),
         "-q:v", "2", frame_pattern],
        capture_output=True,
    )

    image_urls = []
    for frame_file in sorted(video_path.parent.glob("frame_*.jpg")):
        b64 = base64.b64encode(frame_file.read_bytes()).decode()
        image_urls.append(f"data:image/jpeg;base64,{b64}")

    return image_urls, duration


async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    rate_limiter: RateLimiter,
    chat_registry: ChatRegistry,
    history: ConversationHistory,
    odoo: OdooClient,
) -> None:
    user_id = _user_id(update)
    chat_registry.add(_chat_id(update))

    if not rate_limiter.is_allowed(user_id):
        await update.message.reply_text(_RATE_LIMITED_MSG)  # type: ignore[union-attr]
        return

    await _send_typing(update)
    user_text = update.message.text or ""  # type: ignore[union-attr]
    logger.info("Text from user %d: %.80s", user_id, user_text)

    past_history = history.get(user_id)[:-1] if history.get(user_id) else []
    session.detect_onboarding(user_id, past_history, odoo)

    history.add_user(user_id, user_text)
    cb = _typing_callback(update)
    reply = get_response(user_text, config, odoo, history=history.get(user_id)[:-1], system_prompt=session.get_system_prompt(user_id, config), on_mode_change=session.mode_callback(user_id), on_tool_round=cb)
    history.add_assistant(user_id, reply)

    await _reply(update, reply, config)


async def voice_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    rate_limiter: RateLimiter,
    chat_registry: ChatRegistry,
    history: ConversationHistory,
    odoo: OdooClient,
) -> None:
    user_id = _user_id(update)
    chat_registry.add(_chat_id(update))

    if not rate_limiter.is_allowed(user_id):
        await update.message.reply_text(_RATE_LIMITED_MSG)  # type: ignore[union-attr]
        return

    await _send_typing(update)
    logger.info("Voice message from user %d", user_id)
    voice = update.message.voice  # type: ignore[union-attr]
    file = await voice.get_file()

    with tempfile.NamedTemporaryFile(suffix=".ogg") as tmp:
        await file.download_to_drive(tmp.name)
        from openai import OpenAI
        client = OpenAI(api_key=config.openai_api_key)
        with open(tmp.name, "rb") as audio:
            transcription = client.audio.transcriptions.create(
                model="whisper-1", file=audio,
            )

    transcript = transcription.text.strip()
    if not transcript:
        await update.message.reply_text("I couldn't understand the audio.")  # type: ignore[union-attr]
        return

    logger.info("Transcribed voice from user %d: %.80s", user_id, transcript)

    history.add_user(user_id, transcript)
    cb = _typing_callback(update)
    reply = get_response(transcript, config, odoo, history=history.get(user_id)[:-1], system_prompt=session.get_system_prompt(user_id, config), on_mode_change=session.mode_callback(user_id), on_tool_round=cb)
    history.add_assistant(user_id, reply)

    await _reply(update, reply, config)


async def photo_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    rate_limiter: RateLimiter,
    chat_registry: ChatRegistry,
    history: ConversationHistory,
    odoo: OdooClient,
) -> None:
    user_id = _user_id(update)
    chat_registry.add(_chat_id(update))

    if not rate_limiter.is_allowed(user_id):
        await update.message.reply_text(_RATE_LIMITED_MSG)  # type: ignore[union-attr]
        return

    await _send_typing(update)
    logger.info("Photo from user %d", user_id)
    caption = update.message.caption or ""  # type: ignore[union-attr]
    photo = update.message.photo[-1]  # type: ignore[union-attr]
    file = await photo.get_file()
    photo_bytes = await file.download_as_bytearray()
    b64 = base64.b64encode(photo_bytes).decode()
    image_url = f"data:image/jpeg;base64,{b64}"

    user_text = caption or "Analyse cette photo."
    history.add_user(user_id, f"[photo] {user_text}")
    cb = _typing_callback(update)
    reply = get_response(user_text, config, odoo, image_urls=[image_url], history=history.get(user_id)[:-1], system_prompt=session.get_system_prompt(user_id, config), on_mode_change=session.mode_callback(user_id), on_tool_round=cb)
    history.add_assistant(user_id, reply)

    await _reply(update, reply, config)


async def video_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    rate_limiter: RateLimiter,
    chat_registry: ChatRegistry,
    history: ConversationHistory,
    odoo: OdooClient,
) -> None:
    user_id = _user_id(update)
    chat_registry.add(_chat_id(update))

    if not rate_limiter.is_allowed(user_id):
        await update.message.reply_text(_RATE_LIMITED_MSG)  # type: ignore[union-attr]
        return

    await _send_typing(update)
    logger.info("Video from user %d", user_id)
    caption = update.message.caption or ""  # type: ignore[union-attr]
    video = update.message.video  # type: ignore[union-attr]
    file = await video.get_file()

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = Path(tmpdir) / "video.mp4"
        await file.download_to_drive(str(video_path))
        image_urls, duration = _extract_video_frames(video_path)

    if not image_urls:
        await update.message.reply_text("Couldn't extract frames from this video.")  # type: ignore[union-attr]
        return

    user_text = caption or f"This is a video ({duration:.0f}s) shown as {len(image_urls)} frames. Describe what you see."
    history.add_user(user_id, f"[video {duration:.0f}s] {user_text}")
    cb = _typing_callback(update)
    reply = get_response(user_text, config, odoo, image_urls=image_urls, history=history.get(user_id)[:-1], system_prompt=session.get_system_prompt(user_id, config), on_mode_change=session.mode_callback(user_id), on_tool_round=cb)
    history.add_assistant(user_id, reply)

    await _reply(update, reply, config)


async def video_note_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    rate_limiter: RateLimiter,
    chat_registry: ChatRegistry,
    history: ConversationHistory,
    odoo: OdooClient,
) -> None:
    user_id = _user_id(update)
    chat_registry.add(_chat_id(update))

    if not rate_limiter.is_allowed(user_id):
        await update.message.reply_text(_RATE_LIMITED_MSG)  # type: ignore[union-attr]
        return

    await _send_typing(update)
    logger.info("Video note from user %d", user_id)
    video_note = update.message.video_note  # type: ignore[union-attr]
    file = await video_note.get_file()

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = Path(tmpdir) / "video.mp4"
        await file.download_to_drive(str(video_path))
        image_urls, duration = _extract_video_frames(video_path)

    if not image_urls:
        await update.message.reply_text("Couldn't extract frames from this video.")  # type: ignore[union-attr]
        return

    user_text = f"This is a short video message ({duration:.0f}s) shown as {len(image_urls)} frames. Describe what you see."
    history.add_user(user_id, f"[video note {duration:.0f}s]")
    cb = _typing_callback(update)
    reply = get_response(user_text, config, odoo, image_urls=image_urls, history=history.get(user_id)[:-1], system_prompt=session.get_system_prompt(user_id, config), on_mode_change=session.mode_callback(user_id), on_tool_round=cb)
    history.add_assistant(user_id, reply)

    await _reply(update, reply, config)
