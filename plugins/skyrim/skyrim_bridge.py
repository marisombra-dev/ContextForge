"""
ContextForge — Skyrim SE Bridge v0.2
Reads game state written by ContextForge.esp (our own plugin)
and translates it into the ContextForge universal schema,
then POSTs it to the core server.

No MinAI dependency. No CHIM dependency.
Just our plugin, our file, our format.

Requirements:
    Skyrim SE + SKSE64 + PapyrusUtil SE + ContextForge.esp

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

CONTEXTFORGE_URL  = "http://localhost:7842"
GAME_NAME         = "Skyrim Special Edition"
GAME_ID           = "skyrim-se"
PLUGIN_VERSION    = "0.2"

# Path to the state file written by ContextForge.esp
# Default Steam path — update if yours is different
STATE_FILE_PATH = "C:/Program Files (x86)/Steam/steamapps/common/Skyrim Special Edition/Data/ContextForge/current_state.json"


# ── State Reader ───────────────────────────────────────────────────────────────

def read_state(path: str = STATE_FILE_PATH) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


# ── Schema Translator ──────────────────────────────────────────────────────────

def translate_to_cf_schema(
    raw: dict,
    update_type: str = "heartbeat",
    event_type:  Optional[str] = None,
) -> dict:
    """
    Translate the raw state file into the ContextForge universal schema.
    Our ESP writes flat dot-notation keys via JsonUtil.
    This function unpacks that into the nested CF schema.
    """

    # ── Player ─────────────────────────────────────────────────────────────
    health_cur  = raw.get("player.health_current", 0)
    health_max  = raw.get("player.health_max", 1)
    stamina_cur = raw.get("player.stamina_current", 0)
    stamina_max = raw.get("player.stamina_max", 1)
    magicka_cur = raw.get("player.magicka_current", 0)
    magicka_max = raw.get("player.magicka_max", 1)

    player = {
        "name":            raw.get("player.name", "Dragonborn"),
        "level":           raw.get("player.level", 1),
        "health_percent":  round(health_cur  / max(health_max,  1), 2),
        "stamina_percent": round(stamina_cur / max(stamina_max, 1), 2),
        "magicka_percent": round(magicka_cur / max(magicka_max, 1), 2),
        "status_effects":  [],
        "equipped_weapon": raw.get("player.equipped_right"),
        "equipped_spell":  raw.get("player.equipped_left"),
        "dragon_souls":    raw.get("player.dragon_souls", 0),
        "is_sneaking":     raw.get("player.is_sneaking", False),
        "is_swimming":     raw.get("player.is_swimming", False),
    }

    # ── Location ───────────────────────────────────────────────────────────
    location = {
        "name":       raw.get("location.cell_name", "Unknown"),
        "region":     raw.get("location.hold", ""),
        "is_indoor":  raw.get("location.is_interior", False),
        "is_dungeon": _infer_dungeon(raw.get("location.cell_name", "")),
    }

    # ── World ──────────────────────────────────────────────────────────────
    world = {
        "time_of_day": _parse_game_hour(raw.get("world.game_hour", 12.0)),
        "weather":     raw.get("world.weather", "Clear"),
        "in_combat":   raw.get("world.in_combat", False),
        "is_sneaking": raw.get("player.is_sneaking", False),
        "is_swimming": raw.get("player.is_swimming", False),
    }

    # ── Quests ─────────────────────────────────────────────────────────────
    quest_count   = raw.get("quests.active_count", 0)
    active_quests = []
    for i in range(quest_count):
        prefix = f"quests.active[{i}]"
        name = raw.get(f"{prefix}.name")
        if name:
            active_quests.append({
                "name":              name,
                "current_objective": raw.get(f"{prefix}.objective", ""),
                "stage":             raw.get(f"{prefix}.stage", 0),
            })

    quests = {"active": active_quests}

    # ── Nearby entities ────────────────────────────────────────────────────
    actor_count     = raw.get("entities_nearby_count", 0)
    entities_nearby = []
    for i in range(min(actor_count, 10)):
        prefix = f"entities_nearby[{i}]"
        name = raw.get(f"{prefix}.name")
        if name:
            is_follower = raw.get(f"{prefix}.is_follower", False)
            is_hostile  = raw.get(f"{prefix}.is_hostile", False)
            entities_nearby.append({
                "name":        name,
                "type":        "follower" if is_follower else "npc",
                "disposition": "hostile" if is_hostile else "neutral",
                "is_hostile":  is_hostile,
                "distance":    raw.get(f"{prefix}.distance", 0),
            })

    # ── Plugin extras ──────────────────────────────────────────────────────
    followers = [e["name"] for e in entities_nearby if e["type"] == "follower"]

    bounty = {
        hold: raw.get(f"bounty.{hold}", 0)
        for hold in ["whiterun", "solitude", "windhelm", "riften",
                     "markarth", "falkreath", "winterhold", "morthal", "dawnstar"]
        if raw.get(f"bounty.{hold}", 0) > 0
    }

    plugin_extras = {
        "current_followers":       followers,
        "times_died_this_session": raw.get("session_deaths", 0),
        "dragon_souls":            raw.get("player.dragon_souls", 0),
        "bounty":                  bounty,
    }

    return {
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
        "recent_events":   [],
        "plugin_extras":   plugin_extras,
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_game_hour(game_hour: float) -> str:
    hour    = int(game_hour)
    minute  = int((game_hour % 1) * 60)
    period  = "AM" if hour < 12 else "PM"
    display = hour if hour <= 12 else hour - 12
    display = display or 12
    return f"{display}:{minute:02d} {period}"


def _infer_dungeon(cell_name: str) -> bool:
    hints = ["barrow", "cave", "mine", "ruins", "crypt",
             "lair", "keep", "tomb", "fort", "tower"]
    return any(h in cell_name.lower() for h in hints)


# ── Sender ─────────────────────────────────────────────────────────────────────

def send_to_contextforge(cf_state: dict, endpoint: str = "/state", timeout: float = 5.0) -> Optional[str]:
    url = CONTEXTFORGE_URL + endpoint
    try:
        response = httpx.post(url, json=cf_state, timeout=timeout)
        response.raise_for_status()
        return response.json().get("response")
    except httpx.ConnectError:
        return None
    except httpx.TimeoutException:
        return None
    except httpx.HTTPStatusError as e:
        print(f"[Bridge] Server error {e.response.status_code}: {e.response.text}")
        return None


def send_heartbeat(raw_state: dict) -> Optional[str]:
    cf_state = translate_to_cf_schema(raw_state, update_type="heartbeat")
    return send_to_contextforge(cf_state)


def send_event(raw_state: dict, event_type: str) -> Optional[str]:
    cf_state = translate_to_cf_schema(raw_state, update_type="event", event_type=event_type)
    return send_to_contextforge(cf_state)


# ── Test mode ──────────────────────────────────────────────────────────────────

def _run_test():
    fake_raw = {
        "player.name":              "Lyra",
        "player.level":             14,
        "player.health_current":    180.0,
        "player.health_max":        210.0,
        "player.stamina_current":   95.0,
        "player.stamina_max":       120.0,
        "player.magicka_current":   60.0,
        "player.magicka_max":       100.0,
        "player.dragon_souls":      3,
        "player.is_sneaking":       True,
        "player.equipped_right":    "Iron Sword",
        "player.equipped_left":     "Flames",
        "location.cell_name":       "Bleak Falls Barrow",
        "location.hold":            "Whiterun Hold",
        "location.is_interior":     True,
        "world.game_hour":          22.5,
        "world.weather":            "Clear",
        "world.in_combat":          True,
        "quests.active_count":      1,
        "quests.active[0].name":    "A Blade in the Dark",
        "quests.active[0].stage":   10,
        "quests.active[0].objective": "Stage 10",
        "entities_nearby_count":    2,
        "entities_nearby[0].name":  "Draugr Overlord",
        "entities_nearby[0].is_hostile": True,
        "entities_nearby[0].is_follower": False,
        "entities_nearby[0].distance": 312.0,
        "entities_nearby[1].name":  "Lydia",
        "entities_nearby[1].is_hostile": False,
        "entities_nearby[1].is_follower": True,
        "entities_nearby[1].distance": 85.0,
        "session_deaths":           1,
    }

    print("\n── Raw ESP state ─────────────────────────────────────")
    print(json.dumps(fake_raw, indent=2))

    translated = translate_to_cf_schema(fake_raw)
    print("\n── Translated ContextForge schema ────────────────────")
    print(json.dumps(translated, indent=2))

    print("\n── Attempting to send to ContextForge server ─────────")
    result = send_to_contextforge(translated)
    if result:
        print(f"\nDM says: {result}\n")
    else:
        print("Server not reachable — translation test passed, send skipped.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ContextForge Skyrim Bridge")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--path", default=STATE_FILE_PATH)
    args = parser.parse_args()

    if args.test:
        _run_test()
    else:
        print("This module is called by skyrim_heartbeat_loop.py. Use --test for standalone testing.")
