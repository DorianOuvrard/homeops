"""OpenAI function-calling tool definitions and dispatcher."""

import json
import logging

from bot.config import BotConfig
from bot.odoo import OdooClient
from bot.search import search_common_issues, search_product_docs

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
    {
        "type": "function",
        "function": {
            "name": "search_product_docs",
            "description": (
                "Search the web for product documentation, user manuals, technical specs, or repair guides. "
                "Use when the user asks about a specific product reference, model number, or needs technical info "
                "about an equipment (e.g. 'notice du Samsung WW90T554DAW', 'fiche technique chaudière Saunier Duval')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Product reference, model number, or descriptive search terms",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_mode",
            "description": (
                "Switch the conversation mode. "
                "Call set_mode('onboarding') to start the appliance discovery flow. "
                "Call set_mode('default') when the onboarding is finished (after the final recap)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["onboarding", "default"],
                        "description": "The mode to switch to",
                    },
                },
                "required": ["mode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_common_issues",
            "description": (
                "Search for recurring problems, common failures, and user complaints about an appliance. "
                "Use when the user asks about known issues, frequent breakdowns, or reliability of an equipment "
                "(e.g. 'problèmes courants lave-vaisselle Bosch', 'pannes fréquentes chaudière Saunier Duval')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Appliance name, brand, model, or descriptive search terms",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


def _extract_base64(image_urls: list[str] | None) -> str | None:
    """Extract raw base64 from the first data URI, if any."""
    if not image_urls:
        return None
    for url in image_urls:
        if url.startswith("data:") and ";base64," in url:
            return url.split(";base64,", 1)[1]
    return None


def dispatch(
    config: BotConfig,
    odoo: OdooClient,
    name: str,
    arguments: str,
    on_mode_change=None,
    image_urls: list[str] | None = None,
) -> str:
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
                    if args.get("model") == "maintenance.equipment":
                        b64 = _extract_base64(image_urls)
                        if b64 and "image_1920" not in args["values"]:
                            args["values"]["image_1920"] = b64
                    result = odoo.create_record(**args)
            case "update_record":
                if args.get("model") == "maintenance.equipment":
                    b64 = _extract_base64(image_urls)
                    if b64 and "image_1920" not in args.get("values", {}):
                        args.setdefault("values", {})["image_1920"] = b64
                result = odoo.update_record(**args)
            case "delete_record":
                result = odoo.delete_record(**args)
            case "set_mode":
                mode = args.get("mode", "default")
                if on_mode_change:
                    on_mode_change(mode)
                result = {"success": True, "mode": mode}
            case "search_product_docs":
                if not config.tavily_api_key:
                    result = {"error": "TAVILY_API_KEY not configured"}
                else:
                    result = search_product_docs(config.tavily_api_key, **args)
            case "search_common_issues":
                if not config.tavily_api_key:
                    result = {"error": "TAVILY_API_KEY not configured"}
                else:
                    result = search_common_issues(config.tavily_api_key, **args)
            case _:
                result = {"error": f"Unknown tool: {name}"}
    except Exception as exc:
        logger.error("Tool %s failed: %s", name, exc)
        result = {"error": str(exc)}

    return json.dumps(result, default=str, ensure_ascii=False)
