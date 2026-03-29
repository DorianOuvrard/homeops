"""Chat endpoints for the HODOOR web interface."""

import asyncio
import base64
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from bot.api.deps import CurrentUser, get_deps
from bot.api.models import ChatHistoryItem, ChatMessageRequest, ChatMessageResponse

UPLOADS_DIR = Path("data/uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


async def _generate_audio(reply: str, config) -> str | None:
    """Generate TTS audio (MP3) for a reply, save to disk, return URL or None."""
    if not config.elevenlabs_api_key:
        return None
    try:
        from bot.tts import _clean_for_speech, _ELEVENLABS_TTS_URL
        import httpx

        speech_text = _clean_for_speech(reply)
        if not speech_text:
            return None

        # Call ElevenLabs directly and save raw MP3 (browser-compatible)
        url = f"{_ELEVENLABS_TTS_URL}/{config.elevenlabs_voice_id}"
        headers = {"xi-api-key": config.elevenlabs_api_key, "Content-Type": "application/json"}
        payload = {"text": speech_text, "model_id": "eleven_multilingual_v2"}

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                filename = f"tts-{uuid.uuid4().hex}.mp3"
                (UPLOADS_DIR / filename).write_bytes(resp.content)
                return f"/api/v1/uploads/{filename}"
            logger.warning("ElevenLabs returned %d for web TTS", resp.status_code)
    except Exception as exc:
        logger.warning("TTS generation failed: %s", exc)
    return None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _build_anomaly_summary(config) -> str:
    """Build a summary of current Jeedom anomalies for LLM context."""
    try:
        from bot.bran.api import _links, _get_jeedom
        import statistics

        jeedom = _get_jeedom()
        anomalies = []
        devices = jeedom.list_devices()
        for device in devices:
            if not device.get("isEnable", 1):
                continue
            cmds = jeedom.get_commands(device["id"])
            for cmd in cmds:
                if cmd.get("type") != "info" or cmd.get("subType") != "numeric":
                    continue
                try:
                    history = jeedom.get_history(cmd["id"])
                    if len(history) < 20:
                        continue
                    vals = [float(p["value"]) for p in history if p.get("value")]
                    baseline = vals[:int(len(vals) * 0.8)]
                    b_mean = statistics.mean(baseline)
                    b_stdev = statistics.stdev(baseline) if len(baseline) > 1 else 0
                    current = float(cmd.get("currentValue", 0))
                    if current > b_mean + 2 * b_stdev:
                        anomalies.append(
                            f"- {device['name']} / {cmd['name']}: {current} {cmd.get('unite', '')} "
                            f"(normal: {b_mean:.1f} ± {b_stdev:.1f})"
                        )
                except Exception:
                    continue
        if anomalies:
            return "[Alertes capteurs Jeedom]\n" + "\n".join(anomalies)
    except Exception:
        pass
    return ""


def _run_get_response(deps: dict, text: str, image_urls: list[str] | None, user_id: str) -> str:
    """Run get_response in a thread pool to avoid blocking the event loop."""
    from bot.llm import get_response
    from bot import session

    history_obj = deps["history"]
    config = deps["config"]
    odoo = deps["odoo"]

    # Inject Jeedom anomaly context for plan/recap requests
    enriched_text = text
    if any(kw in text.lower() for kw in ["plan", "récap", "recap", "prévention", "prevention", "entretien"]):
        anomaly_summary = _build_anomaly_summary(config)
        if anomaly_summary:
            enriched_text = f"{anomaly_summary}\n\n{text}"

    past = history_obj.get(user_id)
    session.detect_onboarding(user_id, past, odoo)
    history_obj.add_user(user_id, f"[photo] {text}" if image_urls else text)
    reply = get_response(
        enriched_text,
        config,
        odoo,
        image_urls=image_urls,
        history=past,
        system_prompt=session.get_system_prompt(user_id, config),
        on_mode_change=session.mode_callback(user_id),
    )
    history_obj.add_assistant(user_id, reply)
    return reply


def _run_get_response_photo(deps: dict, text: str, image_urls: list[str], user_id: str) -> str:
    """Like _run_get_response but history already has the user message (with image path)."""
    from bot.llm import get_response
    from bot import session

    history_obj = deps["history"]
    config = deps["config"]
    odoo = deps["odoo"]

    past = history_obj.get(user_id)
    session.detect_onboarding(user_id, past, odoo)
    reply = get_response(
        text,
        config,
        odoo,
        image_urls=image_urls,
        history=past,
        system_prompt=session.get_system_prompt(user_id, config),
        on_mode_change=session.mode_callback(user_id),
    )
    history_obj.add_assistant(user_id, reply)
    return reply


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(body: ChatMessageRequest, current_user: CurrentUser):
    deps = get_deps()
    user_id = current_user.id

    # Intercept slash commands before hitting the LLM
    if body.text.strip().startswith("/"):
        from bot.commands import dispatch_command

        try:
            reply = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: dispatch_command(
                    body.text, user_id, deps["config"], deps["history"], deps["odoo"]
                ),
            )
        except Exception as exc:
            logger.error("Command error for user %s: %s", user_id, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Command execution error.",
            )
        if reply is not None:
            return ChatMessageResponse(
                reply=reply,
                timestamp=datetime.now(UTC).isoformat(),
            )

    try:
        reply = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: _run_get_response(deps, body.text, None, user_id),
        )
    except Exception as exc:
        logger.error("Chat error for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI service error.",
        )
    audio_url = await _generate_audio(reply, deps["config"])
    return ChatMessageResponse(
        reply=reply,
        timestamp=datetime.now(UTC).isoformat(),
        audio_url=audio_url,
    )


@router.post("/message/photo", response_model=ChatMessageResponse)
async def send_photo_message(
    current_user: CurrentUser,
    text: str = Form(default="Analyse cette photo."),
    photo: UploadFile = File(...),
):
    deps = get_deps()
    user_id = current_user.id

    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are accepted.",
        )

    photo_bytes = await photo.read()
    if len(photo_bytes) > 20 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Photo must be under 20 MB.",
        )

    # Save photo to disk for persistence
    ext = (photo.content_type or "image/jpeg").split("/")[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    (UPLOADS_DIR / filename).write_bytes(photo_bytes)
    saved_url = f"/api/v1/uploads/{filename}"

    # Add user message with image URL to history
    history_obj = deps["history"]
    history_obj.add_user(user_id, f"[image:{saved_url}] {text}")

    b64 = base64.b64encode(photo_bytes).decode()
    mime = photo.content_type or "image/jpeg"
    image_url = f"data:{mime};base64,{b64}"

    try:
        reply = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: _run_get_response_photo(deps, text, [image_url], user_id),
        )
    except Exception as exc:
        logger.error("Photo chat error for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI service error.",
        )
    audio_url = await _generate_audio(reply, deps["config"])
    return ChatMessageResponse(
        reply=reply,
        timestamp=datetime.now(UTC).isoformat(),
        audio_url=audio_url,
    )


@router.get("/history", response_model=list[ChatHistoryItem])
async def get_history(current_user: CurrentUser):
    deps = get_deps()
    history_obj = deps["history"]
    messages = history_obj.get(current_user.id)
    return [ChatHistoryItem(role=m["role"], content=m["content"]) for m in messages]


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(current_user: CurrentUser):
    deps = get_deps()
    deps["history"].clear(current_user.id)
