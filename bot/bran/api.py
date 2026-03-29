"""Bran module API: device discovery, live values, and Odoo linking."""

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from bot.api.deps import CurrentUser, get_deps
from bot.api.models import (
    BranDeviceCommand,
    BranDeviceResponse,
    BranLinkRequest,
    BranStatusResponse,
)
from bot.bran.client import JeedomClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bran", tags=["bran"])

_LINKS_FILE = Path("data/bran_links.json")

# In-memory cache of jeedom_device_id -> odoo_equipment_id
_links: dict[int, int] = {}


def _load_links() -> None:
    global _links
    if _LINKS_FILE.exists():
        try:
            _links = {int(k): v for k, v in json.loads(_LINKS_FILE.read_text()).items()}
        except Exception:
            _links = {}


def _save_links() -> None:
    _LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LINKS_FILE.write_text(json.dumps(_links))


_load_links()


def _get_jeedom() -> JeedomClient:
    deps = get_deps()
    config = deps["config"]
    if not config.jeedom_url or not config.jeedom_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Jeedom not configured (JEEDOM_URL / JEEDOM_API_KEY missing).",
        )
    return JeedomClient(config.jeedom_url, config.jeedom_api_key)


def _get_odoo_equipment_map(odoo) -> dict[int, str]:
    """Build a map of equipment_id -> name from Odoo."""
    result = odoo.search_records(
        "maintenance.equipment",
        domain=[],
        fields=["id", "name"],
        limit=100,
    )
    return {r["id"]: r.get("name", "") for r in result.get("records", [])}


# Category inference from device name (maps keywords to Odoo category names)
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Électroménager": ["lave", "frigo", "réfrigér", "four", "micro-onde", "cafetière", "robot", "aspirateur"],
    "Chauffage / Climatisation": ["climatiseur", "clim", "chauff", "radiateur", "pompe à chaleur", "chauffe-eau"],
    "Plomberie": ["ballon", "cumulus", "robinet"],
    "Électricité": ["prise", "interrupteur", "tableau"],
    "Menuiserie / Ouvrants": ["volet", "portail", "porte", "fenêtre", "store"],
    "Extérieur / Jardin": ["tondeuse", "arrosage", "piscine", "portail"],
}


def _infer_category_id(device_name: str, odoo) -> int | None:
    """Guess the Odoo equipment category from the device name."""
    name_lower = device_name.lower()
    target_category = None
    for cat_name, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            target_category = cat_name
            break
    if not target_category:
        return None
    result = odoo.search_records(
        "maintenance.equipment.category",
        domain=[["name", "ilike", target_category]],
        fields=["id"],
        limit=1,
    )
    records = result.get("records", [])
    return records[0]["id"] if records else None


def _auto_match(device_name: str, equipment_map: dict[int, str]) -> int | None:
    """Try to find an existing Odoo equipment that matches the Jeedom device name."""
    name_lower = device_name.lower().strip()
    for eq_id, eq_name in equipment_map.items():
        if eq_name.lower().strip() == name_lower:
            return eq_id
    # Partial match: device name contained in equipment name or vice versa
    for eq_id, eq_name in equipment_map.items():
        eq_lower = eq_name.lower().strip()
        if name_lower in eq_lower or eq_lower in name_lower:
            return eq_id
    return None


def _create_equipment_from_device(device: dict, commands: list[dict], odoo) -> dict:
    """Create an Odoo maintenance.equipment from a Jeedom device."""
    device_name = device.get("name", "Appareil inconnu")
    room = ""
    if isinstance(device.get("object"), dict):
        room = device["object"].get("name", "")

    # Build HTML note with sensor info
    sensor_lines = []
    for cmd in commands:
        if cmd.get("type") == "info":
            val = cmd.get("currentValue", "")
            unite = cmd.get("unite", "")
            sensor_lines.append(f"<li><b>{cmd.get('name', '')}</b>: {val} {unite}</li>")
    note_html = f"<p>Importé depuis Jeedom (Bran)</p>"
    if sensor_lines:
        note_html += f"<ul>{''.join(sensor_lines)}</ul>"

    values: dict = {
        "name": device_name,
        "location": room,
        "note": note_html,
    }

    category_id = _infer_category_id(device_name, odoo)
    if category_id:
        values["category_id"] = category_id

    result = odoo.create_record("maintenance.equipment", values)
    return result


def _build_device_response(
    device: dict,
    commands: list[dict],
    equipment_map: dict[int, str],
) -> BranDeviceResponse:
    device_id = device["id"]
    linked_eq_id = _links.get(device_id)
    # Auto-match if no explicit link exists
    if linked_eq_id is None:
        auto_id = _auto_match(device.get("name", ""), equipment_map)
        if auto_id is not None:
            linked_eq_id = auto_id
            _links[device_id] = auto_id  # persist the auto-match
    linked_eq_name = equipment_map.get(linked_eq_id) if linked_eq_id else None

    cmds = []
    for cmd in commands:
        cmds.append(BranDeviceCommand(
            id=cmd["id"],
            name=cmd.get("name", ""),
            type=cmd.get("type", "info"),
            subtype=cmd.get("subType"),
            value=str(cmd["currentValue"]) if cmd.get("currentValue") is not None else None,
            unite=cmd.get("unite") or None,
        ))

    return BranDeviceResponse(
        id=device_id,
        name=device.get("name", ""),
        is_enable=bool(device.get("isEnable", 1)),
        object_name=device.get("object", {}).get("name") if isinstance(device.get("object"), dict) else None,
        eq_type=device.get("eqType_name"),
        commands=cmds,
        linked_equipment_id=linked_eq_id,
        linked_equipment_name=linked_eq_name,
    )


@router.get("/status", response_model=BranStatusResponse)
async def bran_status(current_user: CurrentUser):
    try:
        jeedom = _get_jeedom()
    except HTTPException:
        return BranStatusResponse(connected=False)

    loop = asyncio.get_event_loop()
    connected = await loop.run_in_executor(None, jeedom.ping)
    count = 0
    if connected:
        try:
            devices = await loop.run_in_executor(None, jeedom.list_devices)
            count = len(devices)
        except Exception:
            pass

    return BranStatusResponse(
        connected=connected,
        device_count=count,
        jeedom_url=jeedom.url,
    )


@router.get("/devices", response_model=list[BranDeviceResponse])
async def list_devices(current_user: CurrentUser):
    jeedom = _get_jeedom()
    deps = get_deps()
    odoo = deps["odoo"]
    loop = asyncio.get_event_loop()

    try:
        devices = await loop.run_in_executor(None, jeedom.list_devices)
        equipment_map = await loop.run_in_executor(None, lambda: _get_odoo_equipment_map(odoo))
    except Exception as exc:
        logger.error("Bran device list error: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    # Fetch commands for each device in parallel
    async def _enrich(device: dict) -> BranDeviceResponse:
        try:
            cmds = await loop.run_in_executor(
                None, lambda d=device: jeedom.get_commands(d["id"])
            )
        except Exception:
            cmds = []
        return _build_device_response(device, cmds, equipment_map)

    results = await asyncio.gather(*[_enrich(d) for d in devices if d.get("isEnable", 1)])
    return list(results)


@router.post("/link/{jeedom_device_id}")
async def link_device(
    jeedom_device_id: int,
    body: BranLinkRequest,
    current_user: CurrentUser,
):
    _links[jeedom_device_id] = body.equipment_id
    await asyncio.get_event_loop().run_in_executor(None, _save_links)
    return {"ok": True, "jeedom_device_id": jeedom_device_id, "equipment_id": body.equipment_id}


@router.post("/import/{jeedom_device_id}")
async def import_device(jeedom_device_id: int, current_user: CurrentUser):
    """Create an Odoo equipment from a Jeedom device and link them."""
    if jeedom_device_id in _links:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device already linked to an equipment.",
        )

    jeedom = _get_jeedom()
    deps = get_deps()
    odoo = deps["odoo"]
    loop = asyncio.get_event_loop()

    try:
        device = await loop.run_in_executor(
            None, lambda: jeedom.get_device_full(jeedom_device_id)
        )
    except Exception as exc:
        logger.error("Bran import: cannot fetch device %d: %s", jeedom_device_id, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Cannot reach Jeedom.")

    commands = device.get("cmds", [])

    try:
        result = await loop.run_in_executor(
            None, lambda: _create_equipment_from_device(device, commands, odoo)
        )
    except Exception as exc:
        logger.error("Bran import: Odoo create failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Cannot create equipment in Odoo.")

    eq_id = result["record"]["id"]
    eq_name = result["record"]["display_name"]

    _links[jeedom_device_id] = eq_id
    await loop.run_in_executor(None, _save_links)

    logger.info("Bran: imported device %d -> equipment %d (%s)", jeedom_device_id, eq_id, eq_name)
    return {"ok": True, "equipment_id": eq_id, "equipment_name": eq_name}


@router.delete("/link/{jeedom_device_id}")
async def unlink_device(jeedom_device_id: int, current_user: CurrentUser):
    _links.pop(jeedom_device_id, None)
    await asyncio.get_event_loop().run_in_executor(None, _save_links)
    return {"ok": True}
