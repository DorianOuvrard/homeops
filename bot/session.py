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


def get_system_prompt(user_id: int | str, config: BotConfig) -> str | None:
    """Return the onboarding prompt if user is in onboarding mode, else None."""
    if user_id in _onboarding_users:
        return config.onboarding_prompt
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
