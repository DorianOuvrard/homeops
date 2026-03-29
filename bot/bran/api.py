"""Bran module API: device discovery, live values, and auto-import to Odoo."""

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from bot.api.deps import CurrentUser, get_deps
from bot.api.models import (
    BranDeviceCommand,
    BranDeviceResponse,
    BranMetricPoint,
    BranMetricSeries,
    BranMetricsResponse,
    BranStatusResponse,
)
from bot.bran.client import JeedomClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bran", tags=["bran"])

_LINKS_FILE = Path("data/bran_links.json")

# jeedom_device_id -> odoo_equipment_id
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
    result = odoo.search_records(
        "maintenance.equipment", domain=[], fields=["id", "name"], limit=100,
    )
    return {r["id"]: r.get("name", "") for r in result.get("records", [])}


# ── Category inference ──────────────────────────────────────────────

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Électroménager": ["lave", "frigo", "réfrigér", "four", "micro-onde", "cafetière", "robot", "aspirateur"],
    "Chauffage / Climatisation": ["climatiseur", "clim", "chauff", "radiateur", "pompe à chaleur", "chauffe-eau"],
    "Plomberie": ["ballon", "cumulus", "robinet"],
    "Électricité": ["prise", "interrupteur", "tableau"],
    "Menuiserie / Ouvrants": ["volet", "portail", "porte", "fenêtre", "store"],
    "Extérieur / Jardin": ["tondeuse", "arrosage", "piscine"],
}


def _infer_category_id(device_name: str, odoo) -> int | None:
    name_lower = device_name.lower()
    target = None
    for cat_name, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            target = cat_name
            break
    if not target:
        return None
    result = odoo.search_records(
        "maintenance.equipment.category", domain=[["name", "ilike", target]], fields=["id"], limit=1,
    )
    records = result.get("records", [])
    return records[0]["id"] if records else None


# ── Auto-match + auto-create ────────────────────────────────────────

def _auto_match(device_name: str, equipment_map: dict[int, str]) -> int | None:
    name_lower = device_name.lower().strip()
    # Exact match first
    for eq_id, eq_name in equipment_map.items():
        if eq_name.lower().strip() == name_lower:
            return eq_id
    # Partial containment
    for eq_id, eq_name in equipment_map.items():
        eq_lower = eq_name.lower().strip()
        if name_lower in eq_lower or eq_lower in name_lower:
            return eq_id
    return None


def _create_equipment(device: dict, commands: list[dict], odoo) -> dict:
    """Create an Odoo maintenance.equipment from a Jeedom device."""
    device_name = device.get("name", "Appareil inconnu")
    room = ""
    if isinstance(device.get("object"), dict):
        room = device["object"].get("name", "")

    sensor_lines = []
    for cmd in commands:
        if cmd.get("type") == "info":
            val = cmd.get("currentValue", "")
            unite = cmd.get("unite", "")
            sensor_lines.append(f"<li><b>{cmd.get('name', '')}</b>: {val} {unite}</li>")
    note_html = "<p>Importé automatiquement par Bran</p>"
    if sensor_lines:
        note_html += f"<ul>{''.join(sensor_lines)}</ul>"

    values: dict = {"name": device_name, "location": room, "note": note_html}
    category_id = _infer_category_id(device_name, odoo)
    if category_id:
        values["category_id"] = category_id

    return odoo.create_record("maintenance.equipment", values)


def _sync_device(device: dict, commands: list[dict], equipment_map: dict[int, str], odoo) -> tuple[int, bool]:
    """Match or create equipment for a device. Returns (equipment_id, is_new)."""
    device_id = device["id"]

    # Already linked from a previous scan
    if device_id in _links and _links[device_id] in equipment_map:
        return _links[device_id], False

    # Try name-based match
    matched = _auto_match(device.get("name", ""), equipment_map)
    if matched is not None:
        _links[device_id] = matched
        return matched, False

    # No match: create new equipment
    result = _create_equipment(device, commands, odoo)
    eq_id = result["record"]["id"]
    eq_name = result["record"]["display_name"]
    _links[device_id] = eq_id
    equipment_map[eq_id] = eq_name  # update local cache
    logger.info("Bran: auto-created equipment %d (%s) for device %d", eq_id, eq_name, device_id)
    return eq_id, True


# ── Response builder ────────────────────────────────────────────────

def _build_device_response(
    device: dict, commands: list[dict], equipment_map: dict[int, str], is_new: bool = False,
) -> BranDeviceResponse:
    device_id = device["id"]
    linked_eq_id = _links.get(device_id)
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
        is_new=is_new,
    )


# ── Endpoints ───────────────────────────────────────────────────────

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

    return BranStatusResponse(connected=connected, device_count=count, jeedom_url=jeedom.url)


@router.post("/scan", response_model=list[BranDeviceResponse])
async def scan_and_sync(current_user: CurrentUser):
    """Discover devices, auto-match or create equipment in Odoo, return enriched list."""
    jeedom = _get_jeedom()
    deps = get_deps()
    odoo = deps["odoo"]
    loop = asyncio.get_event_loop()

    try:
        devices = await loop.run_in_executor(None, jeedom.list_devices)
        equipment_map = await loop.run_in_executor(None, lambda: _get_odoo_equipment_map(odoo))
    except Exception as exc:
        logger.error("Bran scan error: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    active = [d for d in devices if d.get("isEnable", 1)]

    # Fetch commands + sync each device
    async def _process(device: dict) -> BranDeviceResponse:
        try:
            cmds = await loop.run_in_executor(None, lambda d=device: jeedom.get_commands(d["id"]))
        except Exception:
            cmds = []
        try:
            _, is_new = await loop.run_in_executor(
                None, lambda d=device, c=cmds: _sync_device(d, c, equipment_map, odoo)
            )
        except Exception as exc:
            logger.warning("Bran: sync failed for device %d: %s", device["id"], exc)
            is_new = False
        return _build_device_response(device, cmds, equipment_map, is_new)

    results = await asyncio.gather(*[_process(d) for d in active])

    # Persist links
    await loop.run_in_executor(None, _save_links)

    return list(results)


@router.get("/devices", response_model=list[BranDeviceResponse])
async def list_devices(current_user: CurrentUser):
    """List devices with live values (no sync, just read)."""
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

    async def _enrich(device: dict) -> BranDeviceResponse:
        try:
            cmds = await loop.run_in_executor(None, lambda d=device: jeedom.get_commands(d["id"]))
        except Exception:
            cmds = []
        return _build_device_response(device, cmds, equipment_map)

    results = await asyncio.gather(*[_enrich(d) for d in devices if d.get("isEnable", 1)])
    return list(results)


@router.get("/metrics/{equipment_id}", response_model=BranMetricsResponse)
async def get_metrics(equipment_id: int, current_user: CurrentUser):
    """Get 24h sensor history for a Jeedom device linked to an Odoo equipment."""
    # Reverse lookup: equipment_id -> jeedom_device_id
    device_id = None
    for jid, eid in _links.items():
        if eid == equipment_id:
            device_id = jid
            break
    if device_id is None:
        raise HTTPException(status_code=404, detail="No Jeedom device linked to this equipment.")

    jeedom = _get_jeedom()
    loop = asyncio.get_event_loop()

    cmds = await loop.run_in_executor(None, lambda: jeedom.get_commands(device_id))
    numeric_cmds = [c for c in cmds if c.get("type") == "info" and c.get("subType") == "numeric"]

    device_name = ""
    try:
        devices = await loop.run_in_executor(None, jeedom.list_devices)
        for d in devices:
            if d["id"] == device_id:
                device_name = d.get("name", "")
                break
    except Exception:
        pass

    series_list: list[BranMetricSeries] = []
    for cmd in numeric_cmds:
        try:
            history = await loop.run_in_executor(None, lambda c=cmd: jeedom.get_history(c["id"]))
        except Exception:
            history = []
        points = [
            BranMetricPoint(datetime=p["datetime"], value=float(p["value"]))
            for p in history
            if p.get("value") is not None
        ]
        current = float(cmd["currentValue"]) if cmd.get("currentValue") is not None else None
        series_list.append(BranMetricSeries(
            cmd_id=cmd["id"],
            name=cmd.get("name", ""),
            unite=cmd.get("unite") or None,
            current=current,
            points=points,
        ))

    return BranMetricsResponse(
        equipment_id=equipment_id,
        device_name=device_name,
        series=series_list,
    )
