"""Odoo XML-RPC client for the Telegram bot."""

import logging
import threading
import xmlrpc.client
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

# Fields that are almost always useful, per common model patterns.
_DEFAULT_FIELDS = ["id", "name", "display_name", "create_date", "write_date"]
_DEFAULT_LIMIT = 10
_MAX_LIMIT = 50


@dataclass(frozen=True)
class OdooConfig:
    url: str
    db: str
    user: str
    password: str


class OdooClient:
    """Thin wrapper around Odoo's XML-RPC API."""

    def __init__(self, config: OdooConfig) -> None:
        self._config = config
        self._uid: int | None = None
        self._lock = threading.Lock()
        self._common = xmlrpc.client.ServerProxy(f"{config.url}/xmlrpc/2/common")
        self._models = xmlrpc.client.ServerProxy(f"{config.url}/xmlrpc/2/object")

    @property
    def uid(self) -> int:
        if self._uid is None:
            self._uid = self._common.authenticate(
                self._config.db, self._config.user, self._config.password, {}
            )
            logger.info("Authenticated to Odoo as uid=%d", self._uid)
        return self._uid

    def _execute(self, model: str, method: str, *args, **kwargs):
        with self._lock:
            return self._models.execute_kw(
                self._config.db, self.uid, self._config.password,
                model, method, *args, **kwargs,
            )

    def search_records(
        self,
        model: str,
        domain: list | None = None,
        fields: list[str] | None = None,
        limit: int = _DEFAULT_LIMIT,
        offset: int = 0,
        order: str | None = None,
    ) -> dict:
        domain = domain or []
        limit = min(limit, _MAX_LIMIT)
        opts: dict = {"fields": fields or _DEFAULT_FIELDS, "limit": limit, "offset": offset}
        if order:
            opts["order"] = order
        records = self._execute(model, "search_read", [domain], opts)
        total = self._execute(model, "search_count", [domain])
        return {"records": records, "total": total, "limit": limit, "offset": offset, "model": model}

    def get_record(self, model: str, record_id: int, fields: list[str] | None = None) -> dict:
        records = self._execute(model, "read", [[record_id]], {"fields": fields or _DEFAULT_FIELDS})
        if not records:
            return {"error": f"Record {model}/{record_id} not found"}
        return {"record": records[0]}

    def list_models(self) -> dict:
        models = self._execute("ir.model", "search_read", [[]], {"fields": ["model", "name"], "limit": 200})
        return {"models": [{"model": m["model"], "name": m["name"]} for m in models], "total": len(models)}

    def create_record(self, model: str, values: dict) -> dict:
        record_id = self._execute(model, "create", [values])
        name = self._execute(model, "read", [[record_id]], {"fields": ["display_name"]})
        return {
            "success": True,
            "record": {"id": record_id, "display_name": name[0]["display_name"] if name else ""},
            "message": f"Created {model} #{record_id}",
        }

    def update_record(self, model: str, record_id: int, values: dict) -> dict:
        self._execute(model, "write", [[record_id], values])
        name = self._execute(model, "read", [[record_id]], {"fields": ["display_name"]})
        return {
            "success": True,
            "record": {"id": record_id, "display_name": name[0]["display_name"] if name else ""},
            "message": f"Updated {model} #{record_id}",
        }

    def delete_record(self, model: str, record_id: int) -> dict:
        name = self._execute(model, "read", [[record_id]], {"fields": ["display_name"]})
        display = name[0]["display_name"] if name else str(record_id)
        self._execute(model, "unlink", [[record_id]])
        return {"success": True, "deleted_id": record_id, "deleted_name": display, "message": f"Deleted {model} #{record_id}"}

    def get_fields(self, model: str) -> dict:
        fields = self._execute(model, "fields_get", [], {"attributes": ["string", "type", "required", "readonly"]})
        return {"model": model, "fields": fields}

    def get_events_between(self, start_at: datetime, end_at: datetime) -> dict:
        start_str = start_at.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_at.strftime("%Y-%m-%d %H:%M:%S")
        domain = [
            ("schedule_date", ">=", start_str),
            ("schedule_date", "<=", end_str),
        ]
        fields = ["id", "name", "description", "schedule_date", "display_name"]
        records = self._execute(
            "maintenance.request",
            "search_read",
            [domain],
            {"fields": fields, "limit": _MAX_LIMIT, "order": "schedule_date asc"},
        )
        return {"records": records, "count": len(records), "start": start_str, "end": end_str}
