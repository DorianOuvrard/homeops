#!/usr/bin/env python3
"""Seed Jeedom with virtual devices for Bran demo.

Requires the 'virtual' plugin to be installed in Jeedom.
Run: uv run python scripts/seed_jeedom.py
"""

import json
import random
import sys
import time
import urllib.request

JEEDOM_URL = "http://localhost:9080"
API_KEY = "cegJQp5AstRCOHbOfyDJFflwXhM5wxJrIblu5G7cHO6SLgYKB4MS1nP5S5NnRSsL"

ENDPOINT = f"{JEEDOM_URL}/core/api/jeeApi.php"


def rpc(method: str, params: dict | None = None):
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": method,
        "params": {"apikey": API_KEY, **(params or {})},
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        ENDPOINT, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read())
    if body.get("error"):
        raise RuntimeError(f"Jeedom error: {body['error']}")
    return body.get("result")


def simple_http(type_param: str, **kwargs):
    """Use the simple HTTP API for operations not in JSON-RPC."""
    params = f"apikey={API_KEY}&type={type_param}"
    for k, v in kwargs.items():
        params += f"&{k}={v}"
    url = f"{ENDPOINT}?{params}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode()


# Virtual devices to create, simulating real home equipment
DEVICES = [
    {
        "name": "Climatiseur Salon",
        "sensors": [
            {"name": "Température", "subtype": "numeric", "value": "22.5", "unite": "°C"},
            {"name": "Consommation", "subtype": "numeric", "value": "850", "unite": "W"},
            {"name": "État", "subtype": "binary", "value": "1", "unite": ""},
        ],
    },
    {
        "name": "Lave-linge",
        "sensors": [
            {"name": "Consommation", "subtype": "numeric", "value": "45", "unite": "W"},
            {"name": "Vibration", "subtype": "numeric", "value": "0.2", "unite": "g"},
            {"name": "Cycle en cours", "subtype": "binary", "value": "0", "unite": ""},
        ],
    },
    {
        "name": "Réfrigérateur",
        "sensors": [
            {"name": "Température", "subtype": "numeric", "value": "4.2", "unite": "°C"},
            {"name": "Consommation", "subtype": "numeric", "value": "120", "unite": "W"},
            {"name": "Porte ouverte", "subtype": "binary", "value": "0", "unite": ""},
        ],
    },
    {
        "name": "Chauffe-eau",
        "sensors": [
            {"name": "Température eau", "subtype": "numeric", "value": "55.0", "unite": "°C"},
            {"name": "Consommation", "subtype": "numeric", "value": "0", "unite": "W"},
        ],
    },
    {
        "name": "Portail électrique",
        "sensors": [
            {"name": "État", "subtype": "binary", "value": "0", "unite": ""},
            {"name": "Cycles", "subtype": "numeric", "value": "3847", "unite": ""},
        ],
    },
]


def check_virtual_plugin():
    """Check if virtual plugin is available."""
    try:
        # Try to list existing virtual devices
        result = rpc("eqLogic::byType", {"type": "virtual"})
        return True
    except Exception as e:
        if "class" in str(e).lower() or "plugin" in str(e).lower():
            return False
        # Other errors might mean the plugin exists but has no devices
        return True


def create_virtual_device(device_conf: dict) -> int | None:
    """Create a virtual device with its sensors using Jeedom's internal API."""
    # Use save method to create the eqLogic
    eq_data = {
        "name": device_conf["name"],
        "eqType_name": "virtual",
        "isEnable": "1",
        "isVisible": "1",
        "configuration": {},
    }

    try:
        result = rpc("eqLogic::save", {"eqLogic": eq_data})
        eq_id = result.get("id") if isinstance(result, dict) else result
        print(f"  Created device: {device_conf['name']} (id={eq_id})")

        # Create info commands for each sensor
        for sensor in device_conf["sensors"]:
            cmd_data = {
                "name": sensor["name"],
                "type": "info",
                "subType": sensor["subtype"],
                "eqLogic_id": str(eq_id),
                "eqType": "virtual",
                "unite": sensor.get("unite", ""),
                "isVisible": "1",
                "configuration": {},
            }
            cmd_result = rpc("cmd::save", {"cmd": cmd_data})
            cmd_id = cmd_result.get("id") if isinstance(cmd_result, dict) else cmd_result
            print(f"    + {sensor['name']} = {sensor['value']} {sensor.get('unite', '')}")

            # Set initial value
            if cmd_id and sensor.get("value"):
                try:
                    rpc("cmd::event", {"id": str(cmd_id), "value": sensor["value"]})
                except Exception:
                    # Fallback: use simple HTTP API
                    try:
                        simple_http("cmd", id=cmd_id, value=sensor["value"])
                    except Exception:
                        pass

        return eq_id
    except Exception as e:
        print(f"  Error creating {device_conf['name']}: {e}")
        return None


def main():
    print("=== Bran Demo: Seeding Jeedom ===\n")

    # Check connection
    try:
        result = rpc("ping")
        assert result == "pong"
        print("Connected to Jeedom\n")
    except Exception as e:
        print(f"Cannot connect to Jeedom at {JEEDOM_URL}: {e}")
        sys.exit(1)

    # Check if virtual plugin is installed
    if not check_virtual_plugin():
        print("WARNING: Virtual plugin might not be installed.")
        print("Install it from Jeedom Market: Plugins > Plugin management > Search 'virtual'")
        print("Attempting to create devices anyway...\n")

    # Check existing virtual devices
    try:
        existing = rpc("eqLogic::byType", {"type": "virtual"}) or []
        if existing:
            print(f"Found {len(existing)} existing virtual device(s)")
            for d in existing:
                print(f"  - {d.get('name', '?')} (id={d.get('id')})")
            print()
            resp = input("Delete existing virtual devices and recreate? [y/N] ")
            if resp.lower() == "y":
                for d in existing:
                    rpc("eqLogic::remove", {"id": str(d["id"])})
                    print(f"  Deleted: {d.get('name')}")
                print()
    except Exception:
        pass

    # Create devices
    print(f"Creating {len(DEVICES)} virtual devices...\n")
    created_ids = []
    for device_conf in DEVICES:
        eq_id = create_virtual_device(device_conf)
        if eq_id:
            created_ids.append(eq_id)
        time.sleep(0.5)

    print(f"\nDone! Created {len(created_ids)}/{len(DEVICES)} devices.")
    print(f"\nJeedom UI: {JEEDOM_URL}")
    print(f"API key: {API_KEY[:20]}...")


if __name__ == "__main__":
    main()
