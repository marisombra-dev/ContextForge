"""
ContextForge — Skyrim Heartbeat Loop
Runs continuously alongside Skyrim, firing state updates to the
ContextForge core server on a 30-second heartbeat and immediately
on significant game events.

This is the thing that keeps him watching.

Usage:
    python skyrim_heartbeat_loop.py
    python skyrim_heartbeat_loop.py --interval 15
    python skyrim_heartbeat_loop.py --minai-path "C:/custom/path/current_state.json"
"""

import time
import argparse
import json
from datetime import datetime
from typing import Optional

from skyrim_bridge import (
    read_minai_state,
    send_heartbeat,
    send_event,
    MINAI_STATE_PATH,
)


# ── Config ─────────────────────────────────────────────────────────────────────

DEFAULT_HEARTBEAT_INTERVAL = 30   # seconds between ambient heartbeats
EVENT_POLL_INTERVAL        = 2    # seconds between event checks (fast loop)


# ── Colour output ──────────────────────────────────────────────────────────────

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"

def log(msg, colour=RESET):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{colour}[{ts}] {msg}{RESET}")


# ── Event Detector ─────────────────────────────────────────────────────────────

class EventDetector:
    """
    Watches game state between heartbeats and fires immediately
    when something worth interrupting the DM for actually happens.

    Tracks previous state so it can diff against current state.
    If MinAI changes its output shape, fix the extractors below.
    """

    def __init__(self):
        self.prev_state: Optional[dict] = None

    def update(self, current_state: dict) -> list[str]:
        """
        Compare current state to previous. Return list of event_type strings
        that fired this cycle. Empty list means nothing interesting happened.
        """
        if self.prev_state is None:
            self.prev_state = current_state
            return []

        events = []

        # Combat start / end
        prev_combat = self.prev_state.get("combat", {}).get("in_combat", False)
        curr_combat = current_state.get("combat", {}).get("in_combat", False)
        if not prev_combat and curr_combat:
            events.append("combat_start")
        if prev_combat and not curr_combat:
            events.append("combat_end")

        # Player death
        prev_health = self.prev_state.get("player", {}).get("health_current", 1)
        curr_health = current_state.get("player", {}).get("health_current", 1)
        if prev_health > 0 and curr_health <= 0:
            events.append("player_death")

        # Location change
        prev_cell = self.prev_state.get("location", {}).get("cell_name", "")
        curr_cell = current_state.get("location", {}).get("cell_name", "")
        if prev_cell and curr_cell and prev_cell != curr_cell:
            events.append("location_change")

        # Level up
        prev_level = self.prev_state.get("player", {}).get("level", 0)
        curr_level = current_state.get("player", {}).get("level", 0)
        if curr_level > prev_level:
            events.append("level_up")

        # Quest update — new objective or new active quest
        prev_quests = {
            q.get("name"): q.get("stage")
            for q in self.prev_state.get("quests", {}).get("active", [])
        }
        curr_quests = {
            q.get("name"): q.get("stage")
            for q in current_state.get("quests", {}).get("active", [])
        }
        if curr_quests != prev_quests:
            events.append("quest_update")

        # Dialogue start
        prev_dialogue = self.prev_state.get("in_dialogue", False)
        curr_dialogue = current_state.get("in_dialogue", False)
        if not prev_dialogue and curr_dialogue:
            events.append("dialogue_start")

        self.prev_state = current_state
        return events


# ── Main Loop ──────────────────────────────────────────────────────────────────

def run(heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL, minai_path: str = MINAI_STATE_PATH):
    """
    Main execution loop.

    Fast inner loop: polls every EVENT_POLL_INTERVAL seconds for events.
    Slow outer beat: fires a heartbeat every heartbeat_interval seconds.

    If the server isn't running, it waits quietly and retries.
    If MinAI isn't running, it waits quietly and retries.
    It does not panic. It does not crash. It just waits.
    """

    detector       = EventDetector()
    last_heartbeat = 0.0
    server_warned  = False
    minai_warned   = False

    print(f"\n{'─' * 55}")
    print(f"  ContextForge — Skyrim Bridge")
    print(f"  Heartbeat every {heartbeat_interval}s | Events polled every {EVENT_POLL_INTERVAL}s")
    print(f"  MinAI path: {minai_path}")
    print(f"{'─' * 55}\n")

    log("Loop started. Watching for Skyrim...", GREEN)

    while True:
        try:
            now = time.time()

            # ── Read MinAI state ───────────────────────────────────────────
            state = read_minai_state(minai_path)

            if state is None:
                if not minai_warned:
                    log("MinAI state not found. Waiting for Skyrim to launch...", YELLOW)
                    minai_warned = True
                time.sleep(EVENT_POLL_INTERVAL)
                continue
            else:
                if minai_warned:
                    log("MinAI state found. Watching.", GREEN)
                    minai_warned = False

            # ── Check for events ───────────────────────────────────────────
            fired_events = detector.update(state)

            for event_type in fired_events:
                log(f"Event: {event_type}", YELLOW)
                response = send_event(state, event_type)
                if response:
                    log(f"DM: {response[:80]}{'...' if len(response) > 80 else ''}", GREEN)
                    server_warned = False
                else:
                    if not server_warned:
                        log("ContextForge server not reachable. Start server.py.", RED)
                        server_warned = True

            # ── Heartbeat ──────────────────────────────────────────────────
            if now - last_heartbeat >= heartbeat_interval:
                log("Heartbeat →", YELLOW)
                response = send_heartbeat(state)
                if response:
                    log(f"DM: {response[:80]}{'...' if len(response) > 80 else ''}", GREEN)
                    server_warned = False
                else:
                    if not server_warned:
                        log("ContextForge server not reachable. Start server.py.", RED)
                        server_warned = True
                last_heartbeat = now

            time.sleep(EVENT_POLL_INTERVAL)

        except KeyboardInterrupt:
            log("\nLoop stopped. Good session. 👋", YELLOW)
            break
        except Exception as e:
            log(f"Unexpected error: {e}", RED)
            time.sleep(EVENT_POLL_INTERVAL)
            continue


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ContextForge Skyrim Heartbeat Loop")
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_HEARTBEAT_INTERVAL,
        help=f"Heartbeat interval in seconds (default: {DEFAULT_HEARTBEAT_INTERVAL})"
    )
    parser.add_argument(
        "--minai-path",
        type=str,
        default=MINAI_STATE_PATH,
        help="Path to MinAI current_state.json"
    )
    args = parser.parse_args()

    run(heartbeat_interval=args.interval, minai_path=args.minai_path)
