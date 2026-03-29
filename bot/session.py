"""Shared session logic for onboarding detection and mode switching.

Both the Telegram handlers and the PWA API endpoints use this module
so that users get identical behavior regardless of the interface.
"""

import logging

from bot.config import BotConfig
from bot.odoo import OdooClient

logger = logging.getLogger(__name__)

_onboarding_users: set[int | str] = set()


def detect_onboarding(
    user_id: int | str, history: list[dict], odoo: OdooClient
) -> None:
    """Auto-trigger onboarding for users with no history and no equipment."""
    if history or user_id in _onboarding_users:
        return
    try:
        result = odoo.search_records(
            "maintenance.equipment", domain=[], fields=["id"], limit=1
        )
        if result.get("total", 0) == 0:
            _onboarding_users.add(user_id)
    except Exception:
        pass


def _build_reference_data(odoo: OdooClient) -> str:
    """Pre-fetch Odoo reference data to avoid redundant LLM tool calls."""
    lines = []
    try:
        cats = odoo.search_records(
            "maintenance.equipment.category", domain=[], fields=["id", "name"], limit=20
        )
        if cats.get("records"):
            lines.append("Catégories (utilise directement ces IDs, pas de search nécessaire) :")
            for c in cats["records"]:
                lines.append(f"  - id={c['id']}: {c['name']}")
    except Exception:
        pass
    try:
        partners = odoo.search_records(
            "res.partner", domain=[["is_company", "=", True]], fields=["id", "name"], limit=30
        )
        if partners.get("records"):
            lines.append("Fabricants déjà connus (utilise directement ces IDs) :")
            for p in partners["records"]:
                lines.append(f"  - id={p['id']}: {p['name']}")
    except Exception:
        pass
    return "\n".join(lines)


def get_system_prompt(user_id: int | str, config: BotConfig, odoo: OdooClient | None = None) -> str | None:
    """Return the onboarding prompt if user is in onboarding mode, else None."""
    if user_id in _onboarding_users:
        prompt = config.onboarding_prompt
        if odoo:
            ref_data = _build_reference_data(odoo)
            if ref_data:
                prompt = f"{prompt}\n\n## Référentiel Odoo (pré-chargé)\n{ref_data}"
        return prompt
    return None


def mode_callback(user_id: int | str):
    """Return a callback that updates the user's conversation mode."""
    def on_mode_change(mode: str) -> None:
        if mode == "onboarding":
            _onboarding_users.add(user_id)
        else:
            _onboarding_users.discard(user_id)
    return on_mode_change


def force_onboarding(user_id: int | str) -> None:
    """Force a user into onboarding mode."""
    _onboarding_users.add(user_id)
