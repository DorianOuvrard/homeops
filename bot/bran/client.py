"""Jeedom JSON-RPC 2.0 client for the Bran module."""

import json
import logging
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class JeedomClient:
    """Thin wrapper around the Jeedom JSON-RPC API."""

    def __init__(self, url: str, api_key: str) -> None:
        self.url = url.rstrip("/")
        self.api_key = api_key
        self._endpoint = f"{self.url}/core/api/jeeApi.php"

    def _call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": method,
            "params": {"apikey": self.api_key, **(params or {})},
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            self._endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())

        if "error" in body and body["error"]:
            msg = body["error"].get("message", str(body["error"]))
            raise RuntimeError(f"Jeedom RPC error: {msg}")
        return body.get("result")

    def ping(self) -> bool:
        try:
            return self._call("ping") == "pong"
        except Exception:
            return False

    def list_devices(self) -> list[dict]:
        return self._call("eqLogic::all") or []

    def get_device_full(self, device_id: int) -> dict:
        return self._call("eqLogic::fullById", {"id": str(device_id)})

    def get_commands(self, device_id: int) -> list[dict]:
        return self._call("cmd::byEqLogicId", {"eqLogic_id": str(device_id)}) or []

    def set_command_value(self, cmd_id: int, value: str) -> Any:
        """Push a value to an info command (useful for virtual devices)."""
        return self._call("cmd::event", {"id": str(cmd_id), "value": value})

    def get_history(self, cmd_id: int) -> list[dict]:
        """Get 24h history for a command. Returns [{"datetime": ..., "value": ...}, ...]."""
        return self._call("cmd::getHistory", {"id": str(cmd_id)}) or []

    def list_objects(self) -> list[dict]:
        """List all Jeedom objects (rooms)."""
        return self._call("object::all") or []
