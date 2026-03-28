import base64
import io
import logging
import subprocess
import tempfile
import xmlrpc.client
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from bot.config import BotConfig
from bot.history import ConversationHistory
from bot.llm import get_response
from bot.odoo import OdooClient
from bot.rate_limiter import RateLimiter
from bot.tts import text_to_speech

logger = logging.getLogger(__name__)

_RATE_LIMITED_MSG = (
    "You're sending messages too fast. Please wait a moment before trying again."
)
_CALENDAR_TRIGGER = "calendar send"


async def _send_typing(update: Update) -> None:
    await update.message.chat.send_action(ChatAction.TYPING)  # type: ignore[union-attr]


async def _reply(update: Update, reply: str, config: BotConfig) -> None:
    """Send reply as voice + text caption. Falls back to text-only if TTS fails."""
    await update.message.chat.send_action(ChatAction.RECORD_VOICE)  # type: ignore[union-attr]
    audio = await text_to_speech(reply, config)
    if audio:
        await update.message.reply_voice(voice=io.BytesIO(audio), caption=reply[:1024])  # type: ignore[union-attr]
    else:
        await update.message.reply_text(reply)  # type: ignore[union-attr]


async def new_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    history: ConversationHistory,
) -> None:
    user_id = _user_id(update)
    history.clear(user_id)
    await update.message.reply_text("Nouvelle conversation démarrée.")  # type: ignore[union-attr]


def _user_id(update: Update) -> int:
    return update.effective_user.id  # type: ignore[union-attr]


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
    history: ConversationHistory,
    odoo: OdooClient,
) -> None:
    user_id = _user_id(update)

    if not rate_limiter.is_allowed(user_id):
        await update.message.reply_text(_RATE_LIMITED_MSG)  # type: ignore[union-attr]
        return

    await _send_typing(update)
    user_text = update.message.text or ""  # type: ignore[union-attr]
    logger.info("Text from user %d: %.80s", user_id, user_text)

    if user_text.strip().lower() == _CALENDAR_TRIGGER:
        try:
            event = odoo.create_record(
                "calendar.event",
                {
                    "name": "HomeOps Telegram test",
                    "start": "2026-03-24 13:00:00",
                    "stop": "2026-03-24 14:00:00",
                    "allday": False,
                },
            )
            reply = (
                "Evenement ajoute au calendrier Odoo pour le 24 mars 2026 a 13h. "
                f"Reference: {event['record']['display_name'] or event['record']['id']}."
            )
        except xmlrpc.client.Fault as exc:
            logger.exception("Odoo calendar event creation failed")
            fault = exc.faultString or str(exc)
            if 'database "' in fault and '" does not exist' in fault:
                reply = (
                    f"Impossible de creer l'evenement: la base Odoo configuree "
                    f"({config.odoo_db}) n'existe pas."
                )
            elif "AccessError" in fault or "access" in fault.lower():
                reply = (
                    "Impossible de creer l'evenement: le compte Odoo configure n'a pas "
                    "les droits necessaires sur le calendrier."
                )
            elif "calendar.event" in fault and "doesn't exist" in fault:
                reply = (
                    "Impossible de creer l'evenement: le module calendrier Odoo "
                    "n'est pas disponible sur cette base."
                )
            else:
                reply = (
                    "Impossible de creer l'evenement dans Odoo. "
                    f"Detail technique: {fault[:300]}."
                )
        history.add_user(user_id, user_text)
        history.add_assistant(user_id, reply)
        await _reply(update, reply, config)
        return

    history.add_user(user_id, user_text)
    reply = get_response(user_text, config, odoo, history=history.get(user_id)[:-1])
    history.add_assistant(user_id, reply)

    await _reply(update, reply, config)


async def voice_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    rate_limiter: RateLimiter,
    history: ConversationHistory,
    odoo: OdooClient,
) -> None:
    user_id = _user_id(update)

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
    reply = get_response(transcript, config, odoo, history=history.get(user_id)[:-1])
    history.add_assistant(user_id, reply)

    await _reply(update, reply, config)


async def photo_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    rate_limiter: RateLimiter,
    history: ConversationHistory,
    odoo: OdooClient,
) -> None:
    user_id = _user_id(update)

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

    user_text = caption or "What do you see in this image?"
    history.add_user(user_id, f"[photo] {user_text}")
    reply = get_response(user_text, config, odoo, image_urls=[image_url], history=history.get(user_id)[:-1])
    history.add_assistant(user_id, reply)

    await _reply(update, reply, config)


async def video_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    rate_limiter: RateLimiter,
    history: ConversationHistory,
    odoo: OdooClient,
) -> None:
    user_id = _user_id(update)

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
    reply = get_response(user_text, config, odoo, image_urls=image_urls, history=history.get(user_id)[:-1])
    history.add_assistant(user_id, reply)

    await _reply(update, reply, config)


async def video_note_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    config: BotConfig,
    rate_limiter: RateLimiter,
    history: ConversationHistory,
    odoo: OdooClient,
) -> None:
    user_id = _user_id(update)

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
    reply = get_response(user_text, config, odoo, image_urls=image_urls, history=history.get(user_id)[:-1])
    history.add_assistant(user_id, reply)

    await _reply(update, reply, config)
