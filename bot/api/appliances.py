"""Appliance endpoints for the HODOOR web interface."""

import asyncio
import logging

from fastapi import APIRouter, HTTPException, status

from fastapi import File, UploadFile

from bot.api.deps import CurrentUser, get_deps
from bot.api.models import ApplianceResponse, ChatHistoryItem, ChatMessageRequest, ChatMessageResponse
from datetime import UTC, datetime
import base64

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/appliances", tags=["appliances"])


def _list_appliances(odoo) -> list[dict]:
    result = odoo.search_records(
        "maintenance.equipment",
        domain=[],
        fields=["id", "name", "category_id", "model", "serial_no", "partner_id",
                "partner_ref", "cost", "warranty_date", "effective_date",
                "location", "note", "create_date", "image_128"],
        limit=50,
    )
    return result.get("records", [])


def _get_appliance_with_maintenance(odoo, equipment_id: int) -> dict | None:
    result = odoo.get_record(
        "maintenance.equipment",
        equipment_id,
        fields=["id", "name", "category_id", "model", "serial_no", "partner_id",
                "partner_ref", "cost", "warranty_date", "effective_date",
                "location", "note", "create_date", "image_128"],
    )
    if "error" in result:
        return None
    record = result["record"]

    # Fetch maintenance requests for this equipment
    maint = odoo.search_records(
        "maintenance.request",
        domain=[["equipment_id", "=", equipment_id]],
        fields=["id", "name", "description", "schedule_date", "maintenance_type", "stage_id"],
        limit=50,
    )
    record["maintenance_requests"] = maint.get("records", [])
    return record


def _resolve_m2o(value) -> str | None:
    """Extract display name from a many2one field ([id, name] or False)."""
    if isinstance(value, (list, tuple)) and len(value) > 1:
        return value[1]
    return None


def _build_appliance_response(record: dict) -> ApplianceResponse:
    return ApplianceResponse(
        id=record["id"],
        name=record.get("name") or "",
        category=_resolve_m2o(record.get("category_id")),
        model=record.get("model") or None,
        serial_no=record.get("serial_no") or None,
        vendor=_resolve_m2o(record.get("partner_id")),
        vendor_ref=record.get("partner_ref") or None,
        cost=record.get("cost") or None,
        warranty_date=str(record["warranty_date"]) if record.get("warranty_date") else None,
        effective_date=str(record["effective_date"]) if record.get("effective_date") else None,
        location=record.get("location") or None,
        note=record.get("note") or None,
        create_date=str(record.get("create_date") or ""),
        image_128=f"data:image/png;base64,{record['image_128']}" if record.get("image_128") else None,
        maintenance_requests=record.get("maintenance_requests", []),
    )


@router.get("", response_model=list[ApplianceResponse])
async def list_appliances(current_user: CurrentUser):
    deps = get_deps()
    odoo = deps["odoo"]
    try:
        records = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _list_appliances(odoo)
        )
    except Exception as exc:
        logger.error("Appliance list error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not fetch appliances from Odoo.",
        )
    return [_build_appliance_response(r) for r in records]


@router.get("/{equipment_id}", response_model=ApplianceResponse)
async def get_appliance(equipment_id: int, current_user: CurrentUser):
    deps = get_deps()
    odoo = deps["odoo"]
    try:
        record = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _get_appliance_with_maintenance(odoo, equipment_id)
        )
    except Exception as exc:
        logger.error("Appliance detail error id=%d: %s", equipment_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not fetch appliance from Odoo.",
        )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appliance not found.")
    return _build_appliance_response(record)


@router.post("/{equipment_id}/photo")
async def upload_appliance_photo(
    equipment_id: int,
    current_user: CurrentUser,
    photo: UploadFile = File(...),
):
    """Upload a photo to an Odoo equipment's image_128 field."""
    deps = get_deps()
    odoo = deps["odoo"]

    photo_bytes = await photo.read()
    b64_image = base64.b64encode(photo_bytes).decode()

    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: odoo.update_record("maintenance.equipment", equipment_id, {"image_128": b64_image}),
        )
    except Exception as exc:
        logger.error("Photo upload error id=%d: %s", equipment_id, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not upload photo.")

    return {"ok": True, "image_128": f"data:image/png;base64,{b64_image}"}


@router.post("/{equipment_id}/chat", response_model=ChatMessageResponse)
async def appliance_chat(equipment_id: int, body: ChatMessageRequest, current_user: CurrentUser):
    """Per-appliance chat thread. Uses a namespaced history key."""
    deps = get_deps()
    user_id = current_user.id
    thread_key = f"{user_id}:{equipment_id}"

    history_obj = deps["history"]
    config = deps["config"]
    odoo = deps["odoo"]

    # Verify appliance exists
    try:
        record = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _get_appliance_with_maintenance(odoo, equipment_id)
        )
    except Exception as exc:
        logger.error("Appliance chat lookup error id=%d: %s", equipment_id, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Odoo error.")
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appliance not found.")

    appliance_name = record.get("name", f"Equipement #{equipment_id}")

    def _run():
        from bot.llm import get_response

        past = history_obj.get(thread_key)
        context_text = f"[A propos de: {appliance_name}] {body.text}"
        history_obj.add_user(thread_key, body.text)
        reply = get_response(context_text, config, odoo, history=past)
        history_obj.add_assistant(thread_key, reply)
        return reply

    try:
        reply = await asyncio.get_event_loop().run_in_executor(None, _run)
    except Exception as exc:
        logger.error("Appliance chat error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI service error.")

    return ChatMessageResponse(reply=reply, timestamp=datetime.now(UTC).isoformat())


@router.get("/{equipment_id}/chat", response_model=list[ChatHistoryItem])
async def get_appliance_chat_history(equipment_id: int, current_user: CurrentUser):
    deps = get_deps()
    thread_key = f"{current_user.id}:{equipment_id}"
    messages = deps["history"].get(thread_key)
    return [ChatHistoryItem(role=m["role"], content=m["content"]) for m in messages]
