"""
ContextForge — Core Server v0.2
Local HTTP server that receives game state from plugins,
validates it, and routes it to the LLM router.

Now with persistent cross-game memory.
He remembers you. Every time.

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
from schema_validator import validate_data
from memory_manager import (
    start_session,
    end_session,
    log_event,
    log_pattern,
    log_notable_moment,
    set_name_preference,
    set_dm_last_remark,
    build_dm_context,
    save_memory,
)


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
    "version": "0.2",
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
        "player_id":            "default_player",   # future: multi-profile support
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
            config = {**DEFAULT_CONFIG, **loaded}
            log(f"Config loaded from {config_path}", GREEN)
            return config

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

async def run_onboarding(router: LLMRouter, config: dict, memory: dict) -> dict:
    """
    First run experience — DM introduces himself and establishes
    name and gender with the player. What they tell him here
    goes straight into memory. He won't ask again.
    """
    print(f"\n{BOLD}{'─' * 60}{RESET}")
    print(f"{BOLD}  Welcome to ContextForge{RESET}")
    print(f"{'─' * 60}\n")

    opening = await router.send(
        player_message="[SYSTEM: First launch. Introduce yourself and ask the player what to call you. Be exactly who you are.]",
        mode=ResponseMode.ENGAGED
    )
    print(f"\n  {GREEN}{opening}{RESET}\n")

    player_input = input("  You: ").strip()

    # Save what they want to be called — permanently
    set_name_preference(memory, player_input)
    log(f"Player name saved to memory: {player_input}", GREEN)

    response = await router.send(
        player_message=player_input,
        mode=ResponseMode.ENGAGED
    )
    print(f"\n  {GREEN}{response}{RESET}\n")

    gender_prompt = await router.send(
        player_message="[SYSTEM: Naturally ask the player if they'd prefer you to present as male or female. Keep it light.]",
        mode=ResponseMode.ENGAGED
    )
    print(f"  {GREEN}{gender_prompt}{RESET}\n")

    gender_input = input("  You: ").strip().lower()
    gender = "female" if any(w in gender_input for w in ["female", "woman", "her", "she", "girl"]) else "male"

    wrap_up = await router.send(
        player_message=f"[SYSTEM: Player chose {gender} presentation. Confirm warmly and say you're ready to play.]",
        mode=ResponseMode.ENGAGED
    )
    print(f"\n  {GREEN}{wrap_up}{RESET}\n")

    # Track the DM's last line
    set_dm_last_remark(memory, wrap_up)

    # Save onboarding to config
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

    router: LLMRouter = None   # Injected at server start
    config: dict      = None
    memory: dict      = None   # Loaded once, kept hot, saved on significant events

    def log_message(self, format, *args):
        pass  # Suppress default HTTP logging

    def _respond(self, status: int, body: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_GET(self):

        # ── /status — health check ─────────────────────────────────────────
        if self.path == "/status":
            mem = self.memory or {}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status":        "running",
                "version":       "0.2",
                "dm_name":       self.config.get("dm", {}).get("name", "Not configured"),
                "backend":       self.config.get("llm", {}).get("backend", "Unknown"),
                "player":        mem.get("name_preference", "Unknown"),
                "session_count": mem.get("session_count", 0),
                "games_played":  mem.get("games_played", []),
            }).encode())
            return

        self._respond(404, {"error": "Unknown endpoint"})

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

            errors, warnings = validate_data(data)
            if errors:
                log(f"Invalid state received: {errors}", RED)
                self._respond(400, {"error": "Schema validation failed", "errors": errors})
                return

            game  = data.get("game_name", "unknown")
            loc   = data.get("location", {}).get("name", "Unknown location")
            utype = data.get("update_type", "heartbeat")
            etype = data.get("event_type", "")
            tag   = f"{utype}" + (f":{etype}" if etype else "")
            log(f"← {game} | {loc} | {tag}", GREEN)

            # Log the event into memory
            if self.memory is not None:
                description = f"[{game}] {loc} — {tag}"
                log_event(self.memory, {
                    "type":        utype,
                    "event_type":  etype,
                    "description": description,
                    "game":        game,
                    "location":    loc,
                }, autosave=False)

            # Build memory context to inject into the DM's awareness
            memory_context = build_dm_context(self.memory) if self.memory else ""

            mode = ResponseMode.EVENT if utype == "event" else ResponseMode.AMBIENT

            async def get_response():
                return await self.router.send(
                    game_state=data,
                    mode=mode,
                    memory_context=memory_context,
                )

            response_text = asyncio.run(get_response())
            log(f"→ DM: {response_text[:80]}{'...' if len(response_text) > 80 else ''}", YELLOW)

            # Remember what he just said
            if self.memory is not None:
                set_dm_last_remark(self.memory, response_text)
                save_memory(self.memory)

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
            game_state = data.get("game_state")

            if not message:
                self._respond(400, {"error": "No message provided"})
                return

            log(f"← Player: {message[:80]}", GREEN)

            memory_context = build_dm_context(self.memory) if self.memory else ""

            async def get_response():
                return await self.router.send(
                    game_state=game_state,
                    player_message=message,
                    mode=ResponseMode.ENGAGED,
                    memory_context=memory_context,
                )

            response_text = asyncio.run(get_response())
            log(f"→ DM: {response_text[:80]}{'...' if len(response_text) > 80 else ''}", YELLOW)

            # Track what he said and save
            if self.memory is not None:
                set_dm_last_remark(self.memory, response_text)
                save_memory(self.memory)

            self._respond(200, {"response": response_text})
            return

        # ── /memory/note — pin a notable moment from outside ──────────────
        if self.path == "/memory/note":
            length = int(self.headers.get("Content-Length", 0))
            raw    = self.rfile.read(length)

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                self._respond(400, {"error": "Invalid JSON"})
                return

            moment = data.get("moment", "")
            if not moment:
                self._respond(400, {"error": "No moment provided"})
                return

            if self.memory is not None:
                log_notable_moment(self.memory, moment)
                save_memory(self.memory)
                log(f"★ Notable moment pinned: {moment[:60]}", YELLOW)

            self._respond(200, {"saved": True})
            return

        # ── /memory/pattern — log a recurring behavior ────────────────────
        if self.path == "/memory/pattern":
            length = int(self.headers.get("Content-Length", 0))
            raw    = self.rfile.read(length)

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                self._respond(400, {"error": "Invalid JSON"})
                return

            pattern = data.get("pattern", "")
            if not pattern:
                self._respond(400, {"error": "No pattern provided"})
                return

            if self.memory is not None:
                log_pattern(self.memory, pattern)
                save_memory(self.memory)
                log(f"◎ Pattern logged: {pattern[:60]}", YELLOW)

            self._respond(200, {"saved": True})
            return

        self._respond(404, {"error": "Unknown endpoint"})


# ── Server startup ─────────────────────────────────────────────────────────────

def start_server(config: dict, memory: dict):
    router = LLMRouter(config)

    ContextForgeHandler.router = router
    ContextForgeHandler.config = config
    ContextForgeHandler.memory = memory

    host = config["server"]["host"]
    port = config["server"]["port"]

    server = HTTPServer((host, port), ContextForgeHandler)

    player_name = memory.get("name_preference") or "Not configured"
    sessions    = memory.get("session_count", 0)
    games       = memory.get("games_played", [])

    print(f"\n{BOLD}{'─' * 60}{RESET}")
    print(f"{BOLD}  ContextForge v0.2{RESET}")
    print(f"{'─' * 60}")
    print(f"  Listening on  {GREEN}http://{host}:{port}{RESET}")
    print(f"  LLM Backend   {GREEN}{config['llm']['backend']} / {config['llm']['model']}{RESET}")
    print(f"  DM Name       {GREEN}{config['dm'].get('name', 'Not configured')}{RESET}")
    print(f"  Player        {GREEN}{player_name}{RESET} ({sessions} sessions)")
    if games:
        print(f"  Games played  {GREEN}{', '.join(games)}{RESET}")
    print(f"\n  Endpoints:")
    print(f"    POST /state            — receive game state from plugin")
    print(f"    POST /state/validate   — validate state schema only")
    print(f"    POST /chat             — player message to DM")
    print(f"    POST /memory/note      — pin a notable moment")
    print(f"    POST /memory/pattern   — log a recurring behavior")
    print(f"    GET  /status           — health check")
    print(f"{'─' * 60}\n")

    log("Server started. He remembers everything. 🖤", GREEN)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Session ending — saving memory...", YELLOW)
        end_session(memory, session_summary=f"Session {sessions} ended cleanly.")
        log("Good game. 👋", YELLOW)
        server.shutdown()


# ── Main ───────────────────────────────────────────────────────────────────────

async def main(config_path: Optional[str] = None):
    config = load_config(config_path)

    # Load (or create) player memory before anything else
    player_id   = config.get("memory", {}).get("player_id", "default_player")
    current_game = "unknown"  # will be updated when first /state arrives
    memory      = start_session(player_id, current_game)
    log(f"Memory loaded for player: {memory.get('name_preference') or player_id}", GREEN)

    # Run onboarding if first launch
    if not config["dm"].get("onboarding_complete"):
        router = LLMRouter(config)
        config = await run_onboarding(router, config, memory)

    # Start server — memory travels with it
    server_thread = Thread(target=start_server, args=(config, memory), daemon=True)
    server_thread.start()
    server_thread.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ContextForge Core Server")
    parser.add_argument("--config", help="Path to contextforge.config.json", default=None)
    args = parser.parse_args()

    asyncio.run(main(args.config))
