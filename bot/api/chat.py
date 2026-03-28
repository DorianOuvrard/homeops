"""Chat endpoints for the HODOOR web interface."""

import asyncio
import base64
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from bot.api.deps import CurrentUser, get_deps
from bot.api.models import ChatHistoryItem, ChatMessageRequest, ChatMessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _run_get_response(deps: dict, text: str, image_urls: list[str] | None, user_id: str) -> str:
    """Run get_response in a thread pool to avoid blocking the event loop."""
    from bot.llm import get_response

    history_obj = deps["history"]
    config = deps["config"]
    odoo = deps["odoo"]

    past = history_obj.get(user_id)
    history_obj.add_user(user_id, f"[photo] {text}" if image_urls else text)
    reply = get_response(
        text,
        config,
        odoo,
        image_urls=image_urls,
        history=past,
    )
    history_obj.add_assistant(user_id, reply)
    return reply


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(body: ChatMessageRequest, current_user: CurrentUser):
    deps = get_deps()
    user_id = current_user.id
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
    return ChatMessageResponse(
        reply=reply,
        timestamp=datetime.now(UTC).isoformat(),
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

    b64 = base64.b64encode(photo_bytes).decode()
    mime = photo.content_type or "image/jpeg"
    image_url = f"data:{mime};base64,{b64}"

    try:
        reply = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: _run_get_response(deps, text, [image_url], user_id),
        )
    except Exception as exc:
        logger.error("Photo chat error for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI service error.",
        )
    return ChatMessageResponse(
        reply=reply,
        timestamp=datetime.now(UTC).isoformat(),
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
