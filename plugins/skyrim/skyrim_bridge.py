"""
ContextForge — Skyrim SE Bridge
Reads game state from MinAI and translates it into
the ContextForge universal schema, then POSTs it to the core server.

This file is the heart of the Skyrim plugin.
Everything else is plumbing. This is the thing.

Usage:
    Called by skyrim_heartbeat_loop.py — don't run directly.
    For manual testing: python skyrim_bridge.py --test
"""

import json
import time
import argparse
import httpx
from typing import Optional


# ── Config ─────────────────────────────────────────────────────────────────────

CONTEXTFORGE_URL = "http://localhost:7842"
GAME_NAME        = "Skyrim Special Edition"
GAME_ID          = "skyrim-se"
PLUGIN_VERSION   = "0.1"

# MinAI typically exposes state via a local file or HTTP endpoint.
# Update this path to match your MinAI installation.
MINAI_STATE_PATH = "C:/MinAI/current_state.json"


# ── MinAI Reader ───────────────────────────────────────────────────────────────

def read_minai_state(state_path: str = MINAI_STATE_PATH) -> Optional[dict]:
    """
    Read current game state from MinAI's output file.
    Returns None if file is missing or malformed — bridge will skip this cycle.
    """
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


# ── Schema Translator ──────────────────────────────────────────────────────────

def translate_to_cf_schema(
    minai_state: dict,
    update_type: str = "heartbeat",
    event_type:  Optional[str] = None,
) -> dict:
    """
    Translate MinAI's raw game state into the ContextForge universal schema.

    MinAI field names are Skyrim-specific and inconsistent.
    ContextForge schema is clean, normalized, game-agnostic.
    This function is the translator between those two worlds.

    If MinAI changes its output format, fix it here. Nowhere else.
    """

    # ── Player ─────────────────────────────────────────────────────────────────
    player_raw = minai_state.get("player", {})

    health_cur = player_raw.get("health_current", 0)
    health_max = player_raw.get("health_max", 1)
    health_pct = round(health_cur / max(health_max, 1), 2)

    stamina_cur = player_raw.get("stamina_current", 0)
    stamina_max = player_raw.get("stamina_max", 1)
    stamina_pct = round(stamina_cur / max(stamina_max, 1), 2)

    magicka_cur = player_raw.get("magicka_current", 0)
    magicka_max = player_raw.get("magicka_max", 1)
    magicka_pct = round(magicka_cur / max(magicka_max, 1), 2)

    player = {
        "name":            player_raw.get("name", "Dragonborn"),
        "level":           player_raw.get("level", 1),
        "health_percent":  health_pct,
        "stamina_percent": stamina_pct,
        "magicka_percent": magicka_pct,
        "status_effects":  player_raw.get("active_effects", []),
        "equipped_weapon": player_raw.get("equipped_right", None),
        "equipped_spell":  player_raw.get("equipped_left", None),
    }

    # ── Location ───────────────────────────────────────────────────────────────
    location_raw = minai_state.get("location", {})

    location = {
        "name":      location_raw.get("cell_name", "Unknown"),
        "region":    location_raw.get("hold", ""),
        "is_indoor": location_raw.get("is_interior", False),
        "is_dungeon": location_raw.get("is_dungeon", False),
    }

    # ── World state ────────────────────────────────────────────────────────────
    world_raw = minai_state.get("world", {})

    world = {
        "time_of_day":  _parse_time(world_raw.get("game_hour", 12)),
        "weather":      world_raw.get("weather", "Clear"),
        "in_combat":    minai_state.get("combat", {}).get("in_combat", False),
        "is_sneaking":  player_raw.get("is_sneaking", False),
        "is_swimming":  player_raw.get("is_swimming", False),
    }

    # ── Quests ─────────────────────────────────────────────────────────────────
    quests_raw = minai_state.get("quests", {})

    active_quests = [
        {
            "name":              q.get("name", "Unknown Quest"),
            "current_objective": q.get("objective", ""),
            "stage":             q.get("stage", 0),
        }
        for q in quests_raw.get("active", [])
    ]

    quests = {
        "active":    active_quests,
        "completed": quests_raw.get("completed_count", 0),
    }

    # ── Nearby entities ────────────────────────────────────────────────────────
    entities_raw = minai_state.get("nearby_actors", [])

    entities_nearby = [
        {
            "name":        e.get("name", "Unknown"),
            "type":        _classify_actor(e),
            "disposition": _parse_disposition(e.get("relationship", 0)),
            "is_hostile":  e.get("is_hostile", False),
            "distance":    e.get("distance", 0),
        }
        for e in entities_raw[:10]  # cap at 10 — DM doesn't need an army list
    ]

    # ── Recent events ──────────────────────────────────────────────────────────
    events_raw = minai_state.get("recent_events", [])

    recent_events = [
        {"event": str(e), "timestamp": time.time()}
        for e in events_raw[-10:]
    ]

    # ── Plugin extras — Skyrim-specific data worth surfacing ───────────────────
    followers_raw = minai_state.get("followers", [])
    plugin_extras = {
        "current_followers":       [f.get("name") for f in followers_raw],
        "times_died_this_session": minai_state.get("session_deaths", 0),
        "dragon_souls":            player_raw.get("dragon_souls", 0),
        "shouts_known":            player_raw.get("shouts_known", 0),
        "bounty":                  _get_bounty(minai_state),
    }

    # ── Assemble ───────────────────────────────────────────────────────────────
    cf_state = {
        "schema_version":  "1.0",
        "plugin_id":       GAME_ID,
        "plugin_version":  PLUGIN_VERSION,
        "game_name":       GAME_NAME,
        "timestamp":       time.time(),
        "update_type":     update_type,
        "event_type":      event_type,
        "player":          player,
        "location":        location,
        "world":           world,
        "quests":          quests,
        "entities_nearby": entities_nearby,
        "recent_events":   recent_events,
        "plugin_extras":   plugin_extras,
    }

    return cf_state


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_time(game_hour: float) -> str:
    """Convert a float game hour (0-24) to a readable time string."""
    hour = int(game_hour)
    minute = int((game_hour % 1) * 60)
    period = "AM" if hour < 12 else "PM"
    display_hour = hour if hour <= 12 else hour - 12
    display_hour = display_hour or 12
    return f"{display_hour}:{minute:02d} {period}"


def _classify_actor(actor: dict) -> str:
    """Classify a nearby actor into a clean type string."""
    if actor.get("is_player_follower"):
        return "follower"
    race = actor.get("race", "").lower()
    if any(r in race for r in ["dragon", "draugr", "falmer", "dwemer"]):
        return "creature"
    if actor.get("is_ghost") or actor.get("is_undead"):
        return "undead"
    return "npc"


def _parse_disposition(relationship_rank: int) -> str:
    """Convert MinAI's numeric relationship rank to a readable disposition."""
    if relationship_rank >= 3:
        return "allied"
    if relationship_rank >= 1:
        return "friendly"
    if relationship_rank == 0:
        return "neutral"
    if relationship_rank == -1:
        return "unfriendly"
    return "hostile"


def _get_bounty(minai_state: dict) -> dict:
    """Extract bounty by hold — Skyrim-specific, too good not to surface."""
    bounty_raw = minai_state.get("bounty", {})
    return {
        hold: amount
        for hold, amount in bounty_raw.items()
        if amount > 0
    }


# ── Sender ─────────────────────────────────────────────────────────────────────

def send_to_contextforge(
    cf_state: dict,
    endpoint: str = "/state",
    timeout: float = 5.0,
) -> Optional[str]:
    """
    POST the translated state to the ContextForge core server.
    Returns the DM's response string, or None if the server isn't reachable.
    """
    url = CONTEXTFORGE_URL + endpoint

    try:
        response = httpx.post(url, json=cf_state, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return data.get("response")

    except httpx.ConnectError:
        # Server not running — fail silently, loop will retry
        return None
    except httpx.TimeoutException:
        return None
    except httpx.HTTPStatusError as e:
        print(f"[Bridge] Server error {e.response.status_code}: {e.response.text}")
        return None


def send_heartbeat(minai_state: dict) -> Optional[str]:
    cf_state = translate_to_cf_schema(minai_state, update_type="heartbeat")
    return send_to_contextforge(cf_state)


def send_event(minai_state: dict, event_type: str) -> Optional[str]:
    cf_state = translate_to_cf_schema(minai_state, update_type="event", event_type=event_type)
    return send_to_contextforge(cf_state)


# ── Test mode ──────────────────────────────────────────────────────────────────

def _run_test():
    """
    Test mode — uses the mock state file from the CF repo.
    Translates it and prints the output without hitting a real server.
    """
    import pathlib

    mock_path = pathlib.Path(__file__).parent.parent / "tests/mock_state/skyrim_heartbeat.json"

    if not mock_path.exists():
        print(f"Mock file not found at {mock_path}")
        print("Run this from the ContextForge repo root, or point to a valid MinAI state file.")
        return

    with open(mock_path) as f:
        raw = json.load(f)

    print("\n── Raw MinAI state ───────────────────────────────────")
    print(json.dumps(raw, indent=2)[:800], "...\n")

    translated = translate_to_cf_schema(raw, update_type="heartbeat")

    print("── Translated ContextForge schema ────────────────────")
    print(json.dumps(translated, indent=2))

    print("\n── Attempting to send to ContextForge server ─────────")
    result = send_to_contextforge(translated)
    if result:
        print(f"\nDM says: {result}\n")
    else:
        print("Server not reachable — translation test passed, send skipped.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ContextForge Skyrim Bridge")
    parser.add_argument("--test", action="store_true", help="Run in test mode using mock state")
    args = parser.parse_args()

    if args.test:
        _run_test()
    else:
        print("This module is called by skyrim_heartbeat_loop.py. Use --test for standalone testing.")
