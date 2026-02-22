"""
ContextForge — Core Server v0.1
Local HTTP server that receives game state from plugins,
validates it, and routes it to the LLM router.

Runs on localhost:7842 by default.

Usage:
    python server.py
    python server.py --config path/to/contextforge.config.json
"""

import json
import asyncio
import argparse
import pathlib
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Optional

from llm_router import LLMRouter, ResponseMode
from schema_validator import validate_data  # we'll add this function below


# ── Colour output ──────────────────────────────────────────────────────────────

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def log(msg, colour=RESET):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{colour}[{ts}] {msg}{RESET}")


# ── Default config ─────────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "version": "0.1",
    "server": {
        "port": 7842,
        "host": "localhost"
    },
    "llm": {
        "backend":      "anthropic",
        "model":        "claude-opus-4-6",
        "api_key_env":  "ANTHROPIC_API_KEY",
        "max_tokens":   300,
        "temperature":  0.85,
    },
    "dm": {
        "name":                 None,
        "gender":               None,
        "onboarding_complete":  False,
    },
    "memory": {
        "enabled":              True,
        "storage_path":         "./memory/",
        "max_session_history":  50,
        "cross_game_memory":    True,
    },
    "overlay": {
        "enabled":   True,
        "position":  "bottom_right",
        "opacity":   0.9,
        "hotkey":    "F9",
    },
    "heartbeat_interval_seconds": 30,
}


# ── Config loader ──────────────────────────────────────────────────────────────

def load_config(config_path: Optional[str] = None) -> dict:
    if config_path:
        path = pathlib.Path(config_path)
        if path.exists():
            with open(path) as f:
                loaded = json.load(f)
            # Merge with defaults so missing keys don't cause errors
            config = {**DEFAULT_CONFIG, **loaded}
            log(f"Config loaded from {config_path}", GREEN)
            return config

    # Look for config in current directory
    default_path = pathlib.Path("contextforge.config.json")
    if default_path.exists():
        with open(default_path) as f:
            loaded = json.load(f)
        config = {**DEFAULT_CONFIG, **loaded}
        log("Config loaded from contextforge.config.json", GREEN)
        return config

    log("No config file found — using defaults", YELLOW)
    return DEFAULT_CONFIG


# ── Onboarding ─────────────────────────────────────────────────────────────────

async def run_onboarding(router: LLMRouter, config: dict) -> dict:
    """
    First run experience — DM introduces himself and establishes
    name and gender with the player.
    """
    print(f"\n{BOLD}{'─' * 60}{RESET}")
    print(f"{BOLD}  Welcome to ContextForge{RESET}")
    print(f"{'─' * 60}\n")

    # Opening line — always this, always genuine
    opening = await router.send(
        player_message="[SYSTEM: First launch. Introduce yourself and ask the player what to call you. Be exactly who you are.]",
        mode=ResponseMode.ENGAGED
    )
    print(f"\n  {GREEN}{opening}{RESET}\n")

    # Get the player's chosen name
    player_input = input("  You: ").strip()

    # Let the DM respond and confirm
    response = await router.send(
        player_message=player_input,
        mode=ResponseMode.ENGAGED
    )
    print(f"\n  {GREEN}{response}{RESET}\n")

    # Ask about gender preference naturally
    gender_prompt = await router.send(
        player_message="[SYSTEM: Naturally ask the player if they'd prefer you to present as male or female. Keep it light.]",
        mode=ResponseMode.ENGAGED
    )
    print(f"  {GREEN}{gender_prompt}{RESET}\n")

    gender_input = input("  You: ").strip().lower()

    gender = "female" if any(w in gender_input for w in ["female", "woman", "her", "she", "girl"]) else "male"

    # Confirm and wrap up onboarding
    wrap_up = await router.send(
        player_message=f"[SYSTEM: Player chose {gender} presentation. Confirm warmly and say you're ready to play.]",
        mode=ResponseMode.ENGAGED
    )
    print(f"\n  {GREEN}{wrap_up}{RESET}\n")

    # Save to config
    config["dm"]["name"]                = player_input
    config["dm"]["gender"]              = gender
    config["dm"]["onboarding_complete"] = True

    config_path = pathlib.Path("contextforge.config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    log("Onboarding complete — config saved", GREEN)
    return config


# ── Request Handler ────────────────────────────────────────────────────────────

class ContextForgeHandler(BaseHTTPRequestHandler):

    router: LLMRouter = None  # Injected at server start
    config: dict      = None

    def log_message(self, format, *args):
        # Suppress default HTTP logging — we have our own
        pass

    def _respond(self, status: int, body: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_POST(self):

        # ── /state — receive game state from plugin ────────────────────────
        if self.path == "/state":
            length = int(self.headers.get("Content-Length", 0))
            raw    = self.rfile.read(length)

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                self._respond(400, {"error": "Invalid JSON"})
                return

            # Validate against schema
            errors, warnings = validate_data(data)
            if errors:
                log(f"Invalid state received: {errors}", RED)
                self._respond(400, {"error": "Schema validation failed", "errors": errors})
                return

            # Log what we received
            game    = data.get("game_name", "Unknown game")
            loc     = data.get("location", {}).get("name", "Unknown location")
            utype   = data.get("update_type", "heartbeat")
            etype   = data.get("event_type", "")
            tag     = f"{utype}" + (f":{etype}" if etype else "")
            log(f"← {game} | {loc} | {tag}", GREEN)

            # Determine response mode
            if utype == "event":
                mode = ResponseMode.EVENT
            else:
                mode = ResponseMode.AMBIENT

            # Route to LLM asynchronously
            async def get_response():
                return await self.router.send(game_state=data, mode=mode)

            response_text = asyncio.run(get_response())
            log(f"→ DM: {response_text[:80]}{'...' if len(response_text) > 80 else ''}", YELLOW)

            self._respond(200, {"response": response_text})
            return

        # ── /state/validate — validate without routing to LLM ─────────────
        if self.path == "/state/validate":
            length = int(self.headers.get("Content-Length", 0))
            raw    = self.rfile.read(length)

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                self._respond(400, {"error": "Invalid JSON"})
                return

            errors, warnings = validate_data(data)
            self._respond(200, {
                "valid":    len(errors) == 0,
                "errors":   errors,
                "warnings": warnings,
            })
            return

        # ── /chat — player speaks directly to the DM ──────────────────────
        if self.path == "/chat":
            length = int(self.headers.get("Content-Length", 0))
            raw    = self.rfile.read(length)

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                self._respond(400, {"error": "Invalid JSON"})
                return

            message    = data.get("message", "")
            game_state = data.get("game_state")  # Optional — include for context

            if not message:
                self._respond(400, {"error": "No message provided"})
                return

            log(f"← Player: {message[:80]}", GREEN)

            async def get_response():
                return await self.router.send(
                    game_state=game_state,
                    player_message=message,
                    mode=ResponseMode.ENGAGED
                )

            response_text = asyncio.run(get_response())
            log(f"→ DM: {response_text[:80]}{'...' if len(response_text) > 80 else ''}", YELLOW)

            self._respond(200, {"response": response_text})
            return

        # ── /status — health check ─────────────────────────────────────────
        if self.path == "/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status":  "running",
                "version": "0.1",
                "dm_name": self.config.get("dm", {}).get("name", "Not configured"),
                "backend": self.config.get("llm", {}).get("backend", "Unknown"),
            }).encode())
            return

        self._respond(404, {"error": "Unknown endpoint"})


# ── Server startup ─────────────────────────────────────────────────────────────

def start_server(config: dict):
    router = LLMRouter(config)

    # Inject router and config into handler class
    ContextForgeHandler.router = router
    ContextForgeHandler.config = config

    host = config["server"]["host"]
    port = config["server"]["port"]

    server = HTTPServer((host, port), ContextForgeHandler)

    print(f"\n{BOLD}{'─' * 60}{RESET}")
    print(f"{BOLD}  ContextForge v0.1{RESET}")
    print(f"{'─' * 60}")
    print(f"  Listening on  {GREEN}http://{host}:{port}{RESET}")
    print(f"  LLM Backend   {GREEN}{config['llm']['backend']} / {config['llm']['model']}{RESET}")
    print(f"  DM Name       {GREEN}{config['dm'].get('name', 'Not configured')}{RESET}")
    print(f"\n  Endpoints:")
    print(f"    POST /state          — receive game state from plugin")
    print(f"    POST /state/validate — validate state schema only")
    print(f"    POST /chat           — player message to DM")
    print(f"    GET  /status         — health check")
    print(f"{'─' * 60}\n")

    log("Server started. Waiting for game state...", GREEN)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Shutting down. Good game. 👋", YELLOW)
        server.shutdown()


# ── Main ───────────────────────────────────────────────────────────────────────

async def main(config_path: Optional[str] = None):
    config = load_config(config_path)

    # Run onboarding if first launch
    if not config["dm"].get("onboarding_complete"):
        router = LLMRouter(config)
        config = await run_onboarding(router, config)

    # Start the server in a thread so onboarding can run async
    server_thread = Thread(target=start_server, args=(config,), daemon=True)
    server_thread.start()
    server_thread.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ContextForge Core Server")
    parser.add_argument("--config", help="Path to contextforge.config.json", default=None)
    args = parser.parse_args()

    asyncio.run(main(args.config))
