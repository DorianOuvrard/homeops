"""Slash-command logic shared between Telegram handlers and PWA API.

Each function returns a plain string reply. No Telegram or FastAPI
dependencies so both interfaces can call them identically.
"""

import logging
from datetime import datetime

from bot import session
from bot.config import BotConfig
from bot.history import ConversationHistory
from bot.llm import get_response
from bot.odoo import OdooClient

logger = logging.getLogger(__name__)


def cmd_new(user_id: int | str, history: ConversationHistory) -> str:
    history.clear(user_id)
    return "Nouvelle conversation démarrée."


def cmd_reset(
    user_id: int | str, history: ConversationHistory, odoo: OdooClient
) -> str:
    history.clear(user_id)
    count = 0
    for model in ("maintenance.request", "maintenance.equipment"):
        result = odoo.search_records(model, domain=[], fields=["id"], limit=50)
        for rec in result.get("records", []):
            odoo.delete_record(model, rec["id"])
            count += 1
    return f"Reset: historique vidé, {count} équipement(s) supprimé(s)."


def cmd_scan(
    user_id: int | str,
    config: BotConfig,
    history: ConversationHistory,
    odoo: OdooClient,
) -> str:
    history.clear(user_id)
    count = 0
    for model in ("maintenance.request", "maintenance.equipment"):
        result = odoo.search_records(model, domain=[], fields=["id"], limit=50)
        for rec in result.get("records", []):
            odoo.delete_record(model, rec["id"])
            count += 1
    session.force_onboarding(user_id)
    return f"Scan reset: {count} enregistrement(s) supprimé(s). Rechargement..."


def cmd_plan(
    user_id: int | str,
    config: BotConfig,
    history: ConversationHistory,
    odoo: OdooClient,
) -> str:
    session.force_onboarding(user_id)
    result = odoo.search_records(
        "maintenance.request",
        domain=[["maintenance_type", "=", "preventive"]],
        fields=["id"],
        limit=50,
    )
    for rec in result.get("records", []):
        odoo.delete_record("maintenance.request", rec["id"])
    trigger_msg = "J'ai fini, fais le récap et le plan de prévention."
    history.add_user(user_id, trigger_msg)
    reply = get_response(
        trigger_msg,
        config,
        odoo,
        history=[],
        system_prompt=config.onboarding_prompt,
        on_mode_change=session.mode_callback(user_id),
    )
    history.add_assistant(user_id, reply)
    return reply


def cmd_todayevents(odoo: OdooClient) -> str:
    start_at = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_at = start_at.replace(hour=23, minute=59, second=59)
    result = odoo.get_events_between(start_at, end_at)
    records = result["records"]
    if not records:
        return "Aucune demande planifiée aujourd'hui dans Odoo."
    lines = ["Demandes planifiées du jour dans Odoo :"]
    for record in records:
        lines.append(
            f"- {record.get('schedule_date')} : "
            f"{record.get('display_name') or record.get('name')}"
        )
    return "\n".join(lines[:40])


def dispatch_command(
    text: str,
    user_id: int | str,
    config: BotConfig,
    history: ConversationHistory,
    odoo: OdooClient,
) -> str | None:
    """If text is a known slash command, execute it and return the reply.

    Returns None if the text is not a command.
    """
    cmd = text.strip().split()[0].lower() if text.strip() else ""
    match cmd:
        case "/new":
            return cmd_new(user_id, history)
        case "/reset":
            return cmd_reset(user_id, history, odoo)
        case "/scan":
            return cmd_scan(user_id, config, history, odoo)
        case "/plan":
            return cmd_plan(user_id, config, history, odoo)
        case "/todayevents":
            return cmd_todayevents(odoo)
        case _:
            return None
