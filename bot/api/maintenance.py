"""Maintenance task endpoints for the HODOOR web interface."""

import asyncio
import logging

from fastapi import APIRouter, HTTPException, status

from bot.api.deps import CurrentUser, get_deps
from bot.api.models import MaintenanceStageResponse, MaintenanceTaskResponse, MaintenanceUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/maintenance", tags=["maintenance"])

_TASK_FIELDS = [
    "id", "name", "description", "schedule_date",
    "maintenance_type", "stage_id", "equipment_id",
]


def _resolve_m2o(value) -> tuple[int | None, str | None]:
    """Extract id and display name from a many2one field ([id, name] or False)."""
    if isinstance(value, (list, tuple)) and len(value) > 1:
        return value[0], value[1]
    return None, None


def _build_task_response(record: dict) -> MaintenanceTaskResponse:
    eq_id, eq_name = _resolve_m2o(record.get("equipment_id"))
    stage_id, stage_name = _resolve_m2o(record.get("stage_id"))
    return MaintenanceTaskResponse(
        id=record["id"],
        name=record.get("name") or "",
        description=record.get("description") or None,
        schedule_date=str(record["schedule_date"]) if record.get("schedule_date") else None,
        maintenance_type=record.get("maintenance_type") or None,
        stage_id=stage_id,
        stage_name=stage_name,
        equipment_id=eq_id,
        equipment_name=eq_name,
    )


@router.get("", response_model=list[MaintenanceTaskResponse])
async def list_maintenance(current_user: CurrentUser):
    deps = get_deps()
    odoo = deps["odoo"]
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: odoo.search_records(
                "maintenance.request",
                domain=[["stage_id.name", "not in", ["Repaired", "Scrap"]]],
                fields=_TASK_FIELDS,
                limit=50,
                order="schedule_date asc",
            ),
        )
    except Exception as exc:
        logger.error("Maintenance list error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not fetch maintenance tasks from Odoo.",
        )
    return [_build_task_response(r) for r in result.get("records", [])]


@router.patch("/{task_id}", response_model=MaintenanceTaskResponse)
async def update_maintenance(task_id: int, body: MaintenanceUpdateRequest, current_user: CurrentUser):
    deps = get_deps()
    odoo = deps["odoo"]

    values: dict = {}
    if body.stage_id is not None:
        values["stage_id"] = body.stage_id
    if body.schedule_date is not None:
        values["schedule_date"] = body.schedule_date

    if not values:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to update.")

    try:
        def _update():
            odoo.update_record("maintenance.request", task_id, values)
            result = odoo.get_record("maintenance.request", task_id, fields=_TASK_FIELDS)
            if "error" in result:
                return None
            return result["record"]

        record = await asyncio.get_event_loop().run_in_executor(None, _update)
    except Exception as exc:
        logger.error("Maintenance update error id=%d: %s", task_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not update maintenance task in Odoo.",
        )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return _build_task_response(record)


@router.get("/stages", response_model=list[MaintenanceStageResponse])
async def list_stages(current_user: CurrentUser):
    deps = get_deps()
    odoo = deps["odoo"]
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: odoo.search_records(
                "maintenance.stage",
                domain=[],
                fields=["id", "name"],
                limit=20,
            ),
        )
    except Exception as exc:
        logger.error("Maintenance stages error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not fetch maintenance stages from Odoo.",
        )
    return [MaintenanceStageResponse(id=r["id"], name=r["name"]) for r in result.get("records", [])]
