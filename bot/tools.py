"""OpenAI function-calling tool definitions and dispatcher for Odoo."""

import json
import logging

from bot.odoo import OdooClient

logger = logging.getLogger(__name__)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_records",
            "description": (
                "Search for records in an Odoo model. "
                "Use this to list, filter, or count records (partners, maintenance requests, equipment, etc.)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name, e.g. 'res.partner', 'maintenance.request'"},
                    "domain": {
                        "type": "array",
                        "description": "Odoo domain filter, e.g. [['is_company', '=', true]]. Empty list for all records.",
                        "items": {},
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Fields to return. Omit for defaults (id, name, display_name, dates).",
                    },
                    "limit": {"type": "integer", "description": "Max records to return (default 10, max 50)"},
                    "offset": {"type": "integer", "description": "Number of records to skip for pagination"},
                    "order": {"type": "string", "description": "Sort order, e.g. 'name asc', 'create_date desc'"},
                },
                "required": ["model"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_record",
            "description": "Get a specific Odoo record by its ID. Use after search_records to get full details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "record_id": {"type": "integer", "description": "The record ID"},
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Fields to return. Omit for defaults.",
                    },
                },
                "required": ["model", "record_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_models",
            "description": "List all available Odoo models. Useful to discover what data exists.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fields",
            "description": "Get field definitions for an Odoo model. Use to discover available fields before searching.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                },
                "required": ["model"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_record",
            "description": (
                "Create a new record in Odoo. "
                "You MUST provide values with at least a 'name' field. "
                "Example: model='maintenance.equipment', values={'name': 'Sauna', 'category_id': 1}"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "values": {"type": "object", "description": "Field values for the new record. MUST include at least 'name'."},
                },
                "required": ["model", "values"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_record",
            "description": "Update an existing Odoo record.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "record_id": {"type": "integer", "description": "The record ID to update"},
                    "values": {"type": "object", "description": "Field values to update"},
                },
                "required": ["model", "record_id", "values"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_record",
            "description": "Delete an Odoo record.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "record_id": {"type": "integer", "description": "The record ID to delete"},
                },
                "required": ["model", "record_id"],
            },
        },
    },
]


def dispatch(odoo: OdooClient, name: str, arguments: str) -> str:
    """Execute a tool call and return the JSON result."""
    args = json.loads(arguments)
    logger.info("Tool call: %s(%s)", name, args)

    try:
        match name:
            case "search_records":
                result = odoo.search_records(**args)
            case "get_record":
                result = odoo.get_record(**args)
            case "list_models":
                result = odoo.list_models()
            case "get_fields":
                result = odoo.get_fields(**args)
            case "create_record":
                if "values" not in args or not args["values"]:
                    result = {"error": "values is required and must include at least 'name'"}
                else:
                    result = odoo.create_record(**args)
            case "update_record":
                result = odoo.update_record(**args)
            case "delete_record":
                result = odoo.delete_record(**args)
            case _:
                result = {"error": f"Unknown tool: {name}"}
    except Exception as exc:
        logger.error("Tool %s failed: %s", name, exc)
        result = {"error": str(exc)}

    return json.dumps(result, default=str, ensure_ascii=False)
