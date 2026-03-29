#!/usr/bin/env python3
"""Mock Jeedom JSON-RPC server for Bran demo.

Simulates the Jeedom API with virtual devices that have fluctuating sensor values.
Run: uv run python scripts/mock_jeedom.py
"""

import json
import math
import random
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

API_KEY = "mock-jeedom-api-key-for-bran-demo"
PORT = 9080

# Simulated devices with their sensors
DEVICES = [
    {
        "id": 1,
        "name": "Climatiseur Salon",
        "eqType_name": "virtual",
        "isEnable": 1,
        "isVisible": 1,
        "object": {"id": 1, "name": "Salon"},
        "configuration": {
            "manufacturer": "Daikin",
            "model": "FTXM35R",
            "serial": "2450781-03",
            "year": 2024,
            "estimated_price": 1290,
        },
        "commands": [
            {"id": 101, "name": "Température", "type": "info", "subType": "numeric",
             "unite": "°C", "base_value": 22.5, "variance": 1.0},
            {"id": 102, "name": "Consommation", "type": "info", "subType": "numeric",
             "unite": "W", "base_value": 850, "variance": 100},
            {"id": 103, "name": "État", "type": "info", "subType": "binary",
             "unite": "", "base_value": 1, "variance": 0},
        ],
    },
    {
        "id": 2,
        "name": "Lave-linge",
        "eqType_name": "virtual",
        "isEnable": 1,
        "isVisible": 1,
        "object": {"id": 2, "name": "Buanderie"},
        "configuration": {
            "manufacturer": "Samsung",
            "model": "WW90T554DAW",
            "serial": "Y28G900123",
            "year": 2023,
            "estimated_price": 649,
        },
        "commands": [
            {"id": 201, "name": "Consommation", "type": "info", "subType": "numeric",
             "unite": "W", "base_value": 45, "variance": 20},
            {"id": 202, "name": "Vibration", "type": "info", "subType": "numeric",
             "unite": "g", "base_value": 0.2, "variance": 0.1},
            {"id": 203, "name": "Cycle en cours", "type": "info", "subType": "binary",
             "unite": "", "base_value": 0, "variance": 0},
        ],
    },
    {
        "id": 3,
        "name": "Réfrigérateur",
        "eqType_name": "virtual",
        "isEnable": 1,
        "isVisible": 1,
        "object": {"id": 3, "name": "Cuisine"},
        "configuration": {
            "manufacturer": "Liebherr",
            "model": "CNef 4815",
            "serial": "51.692.847.4",
            "year": 2022,
            "estimated_price": 899,
        },
        "commands": [
            {"id": 301, "name": "Température", "type": "info", "subType": "numeric",
             "unite": "°C", "base_value": 4.2, "variance": 0.5},
            {"id": 302, "name": "Consommation", "type": "info", "subType": "numeric",
             "unite": "W", "base_value": 120, "variance": 30},
            {"id": 303, "name": "Porte ouverte", "type": "info", "subType": "binary",
             "unite": "", "base_value": 0, "variance": 0},
        ],
    },
    {
        "id": 4,
        "name": "Chauffe-eau",
        "eqType_name": "virtual",
        "isEnable": 1,
        "isVisible": 1,
        "object": {"id": 4, "name": "Garage"},
        "configuration": {
            "manufacturer": "Atlantic",
            "model": "Zeneo 200L",
            "serial": "ATL-2024-08812",
            "year": 2024,
            "estimated_price": 459,
        },
        "commands": [
            {"id": 401, "name": "Température eau", "type": "info", "subType": "numeric",
             "unite": "°C", "base_value": 55.0, "variance": 3.0},
            {"id": 402, "name": "Consommation", "type": "info", "subType": "numeric",
             "unite": "W", "base_value": 0, "variance": 50},
        ],
    },
    {
        "id": 5,
        "name": "Portail électrique",
        "eqType_name": "virtual",
        "isEnable": 1,
        "isVisible": 1,
        "object": {"id": 5, "name": "Extérieur"},
        "configuration": {
            "manufacturer": "Somfy",
            "model": "Elixo 500 3S RTS",
            "serial": "5121478-A",
            "year": 2021,
            "estimated_price": 750,
        },
        "commands": [
            {"id": 501, "name": "État", "type": "info", "subType": "binary",
             "unite": "", "base_value": 0, "variance": 0},
            {"id": 502, "name": "Cycles", "type": "info", "subType": "numeric",
             "unite": "", "base_value": 3847, "variance": 0},
        ],
    },
]

# Persistent anomalies for demo (cmd_id -> multiplier)
_demo_anomalies: dict[int, float] = {102: 3.0, 401: 1.6}

# Dynamic anomaly state (set via mock::triggerAnomaly)
_anomaly_cmd: int | None = None
_anomaly_multiplier: float = 1.0


def get_current_value(cmd: dict) -> str:
    """Generate a realistic fluctuating value for a sensor."""
    base = cmd["base_value"]
    variance = cmd["variance"]
    cmd_id = cmd["id"]

    if cmd["subType"] == "binary":
        return str(int(base))

    # Sinusoidal drift + random noise
    t = time.time()
    drift = math.sin(t / 30 + cmd_id) * variance * 0.5
    noise = random.gauss(0, variance * 0.2)
    value = base + drift + noise

    # Apply anomalies (demo persistent + dynamic)
    if cmd_id in _demo_anomalies:
        value *= _demo_anomalies[cmd_id]
    if _anomaly_cmd == cmd_id:
        value *= _anomaly_multiplier

    if cmd["subType"] == "numeric":
        if cmd["unite"] in ("°C", "g"):
            return f"{value:.1f}"
        return str(int(max(0, value)))

    return str(value)


def build_cmd_response(cmd: dict) -> dict:
    return {
        "id": cmd["id"],
        "name": cmd["name"],
        "type": cmd["type"],
        "subType": cmd["subType"],
        "unite": cmd.get("unite", ""),
        "isVisible": 1,
        "currentValue": get_current_value(cmd),
        "eqLogic_id": None,  # filled by caller
    }


def build_device_response(device: dict, include_cmds: bool = False) -> dict:
    result = {
        "id": device["id"],
        "name": device["name"],
        "eqType_name": device["eqType_name"],
        "isEnable": device["isEnable"],
        "isVisible": device["isVisible"],
        "object": device.get("object"),
        "configuration": device.get("configuration", {}),
    }
    if include_cmds:
        result["cmds"] = [
            {**build_cmd_response(c), "eqLogic_id": device["id"]}
            for c in device["commands"]
        ]
    return result


def handle_rpc(method: str, params: dict) -> object:
    global _anomaly_cmd, _anomaly_multiplier

    if method == "ping":
        return "pong"

    if method == "version":
        return "4.4.0-mock"

    if method == "eqLogic::all":
        return [build_device_response(d) for d in DEVICES]

    if method == "eqLogic::fullById":
        device_id = int(params.get("id", 0))
        for d in DEVICES:
            if d["id"] == device_id:
                return build_device_response(d, include_cmds=True)
        return {"error": "Device not found"}

    if method == "eqLogic::byType":
        eq_type = params.get("type", "")
        return [build_device_response(d) for d in DEVICES if d["eqType_name"] == eq_type]

    if method == "cmd::byEqLogicId":
        eq_id = int(params.get("eqLogic_id", 0))
        for d in DEVICES:
            if d["id"] == eq_id:
                return [
                    {**build_cmd_response(c), "eqLogic_id": eq_id}
                    for c in d["commands"]
                ]
        return []

    if method == "cmd::execCmd":
        cmd_id = int(params.get("id", 0))
        for d in DEVICES:
            for c in d["commands"]:
                if c["id"] == cmd_id:
                    return {"value": get_current_value(c)}
        return None

    if method == "cmd::event":
        # Accept value updates (for testing)
        cmd_id = int(params.get("id", 0))
        value = params.get("value")
        for d in DEVICES:
            for c in d["commands"]:
                if c["id"] == cmd_id and value is not None:
                    c["base_value"] = float(value)
                    return "ok"
        return None

    if method == "object::all":
        seen = {}
        for d in DEVICES:
            obj = d.get("object", {})
            if obj and obj["id"] not in seen:
                seen[obj["id"]] = obj
        return list(seen.values())

    # Mock-specific: trigger anomaly for demo
    if method == "mock::triggerAnomaly":
        _anomaly_cmd = int(params.get("cmd_id", 102))  # default: clim consumption
        _anomaly_multiplier = float(params.get("multiplier", 2.0))
        print(f"  ANOMALY triggered on cmd {_anomaly_cmd} (x{_anomaly_multiplier})")
        return "anomaly_active"

    if method == "mock::clearAnomaly":
        _anomaly_cmd = None
        _anomaly_multiplier = 1.0
        print("  ANOMALY cleared")
        return "anomaly_cleared"

    if method == "cmd::getHistory":
        cmd_id = int(params.get("id", 0))
        target_cmd = None
        for d in DEVICES:
            for c in d["commands"]:
                if c["id"] == cmd_id:
                    target_cmd = c
                    break
        if not target_cmd or target_cmd["subType"] != "numeric":
            return []
        # Generate 24h of history (every 10 min = 144 points)
        now = time.time()
        points = []
        base = target_cmd["base_value"]
        variance = target_cmd["variance"]
        # Anomaly injection: sharp spike in the last ~15 points
        # 102 = Clim consumption, 401 = Chauffe-eau temperature
        anomaly_cmds = {102: 3.0, 401: 1.6}
        anomaly_start = 130  # point index where anomaly begins
        for i in range(144):
            t = now - (143 - i) * 600
            drift = math.sin(t / 30 + cmd_id) * variance * 0.5
            noise = random.gauss(0, variance * 0.15)
            val = base + drift + noise
            # Ramp up anomaly progressively
            if cmd_id in anomaly_cmds and i >= anomaly_start:
                progress = (i - anomaly_start) / (144 - anomaly_start)
                multiplier = 1 + (anomaly_cmds[cmd_id] - 1) * progress
                val *= multiplier
            if target_cmd["unite"] in ("°C", "g"):
                val = round(val, 1)
            else:
                val = max(0, int(val))
            dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
            points.append({"datetime": dt, "value": str(val)})
        return points

    if method == "plugin::listPlugin":
        return [{"id": "virtual", "name": "Virtual", "isEnable": 1}]

    return None


class JeedomHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            request = json.loads(body)
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id", "1")

        # Check API key
        api_key = params.pop("apikey", None)
        if api_key != API_KEY:
            self.send_json({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32001, "message": "Invalid API key"},
            })
            return

        try:
            result = handle_rpc(method, params)
            self.send_json({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result,
            })
        except Exception as e:
            self.send_json({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": str(e)},
            })

    def do_GET(self):
        """Handle simple HTTP API calls."""
        parsed = urlparse(self.path)
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        if params.get("apikey") != API_KEY:
            self.send_json({"error": "Invalid API key"}, 401)
            return

        req_type = params.get("type", "")
        if req_type == "cmd":
            cmd_id = int(params.get("id", 0))
            value = params.get("value")
            if value is not None:
                handle_rpc("cmd::event", {"id": str(cmd_id), "value": value})
                self.send_json({"result": "ok"})
            else:
                result = handle_rpc("cmd::execCmd", {"id": str(cmd_id)})
                self.send_json({"result": result})
        else:
            self.send_json({"result": "ok"})

    def send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        method_info = ""
        if len(args) >= 1 and "POST" in str(args[0]):
            method_info = " (JSON-RPC)"
        print(f"  [{self.log_date_time_string()}] {args[0] if args else ''}{method_info}")


def main():
    print(f"""
╔══════════════════════════════════════════╗
║       Mock Jeedom for Bran Demo          ║
╠══════════════════════════════════════════╣
║  Port:    {PORT:<30} ║
║  API Key: {API_KEY[:30]:<30} ║
║  Devices: {len(DEVICES):<30} ║
╚══════════════════════════════════════════╝

Devices:""")
    for d in DEVICES:
        cmds = ", ".join(f"{c['name']}" for c in d["commands"])
        print(f"  {d['id']}. {d['name']} ({d['object']['name']}) : {cmds}")

    print(f"""
Trigger anomaly:
  curl -X POST http://localhost:{PORT}/core/api/jeeApi.php \\
    -H 'Content-Type: application/json' \\
    -d '{{"jsonrpc":"2.0","id":"1","method":"mock::triggerAnomaly","params":{{"apikey":"{API_KEY}","cmd_id":102,"multiplier":2.5}}}}'

Clear anomaly:
  curl -X POST http://localhost:{PORT}/core/api/jeeApi.php \\
    -H 'Content-Type: application/json' \\
    -d '{{"jsonrpc":"2.0","id":"1","method":"mock::clearAnomaly","params":{{"apikey":"{API_KEY}"}}}}'
""")

    server = HTTPServer(("0.0.0.0", PORT), JeedomHandler)
    print(f"Mock Jeedom listening on port {PORT}...\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down mock Jeedom")
        server.shutdown()


if __name__ == "__main__":
    main()
