"""
ContextForge — Schema Validator v0.1
Validates plugin output against the ContextForge normalized game state schema.

Usage:
    python schema_validator.py <path_to_json_file>

Example:
    python schema_validator.py tests/mock_state/skyrim_heartbeat.json
"""

import json
import sys
from datetime import datetime


# ── Colour output for terminal ────────────────────────────────────────────────

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):    print(f"  {GREEN}✓{RESET} {msg}")
def warn(msg):  print(f"  {YELLOW}⚠{RESET}  {msg}")
def fail(msg):  print(f"  {RED}✗{RESET} {msg}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}")


# ── Valid values ───────────────────────────────────────────────────────────────

VALID_UPDATE_TYPES = {"heartbeat", "event"}

VALID_EVENT_TYPES = {
    "combat_start", "combat_end", "player_death", "player_critical_health",
    "location_entered", "quest_started", "quest_updated", "quest_completed",
    "quest_failed", "npc_interaction", "level_up", "fast_travel",
    "significant_item_acquired", "time_threshold", "plugin_defined"
}

REQUIRED_TOP_LEVEL_FIELDS = [
    "contextforge_version",
    "plugin_id",
    "game_name",
    "update_type",
    "event_type",
    "timestamp",
    "player",
    "location",
    "world",
    "quests",
    "entities_nearby",
    "recent_events",
    "plugin_extras"
]


# ── Validators ─────────────────────────────────────────────────────────────────

def validate_top_level(data, errors, warnings):
    header("Checking required fields...")
    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in data:
            fail(f"Missing required field: '{field}'")
            errors.append(field)
        else:
            ok(f"'{field}' present")


def validate_update_type(data, errors, warnings):
    header("Checking update_type...")
    ut = data.get("update_type")
    if ut not in VALID_UPDATE_TYPES:
        fail(f"'update_type' must be one of {VALID_UPDATE_TYPES} — got '{ut}'")
        errors.append("update_type_invalid")
    else:
        ok(f"update_type: '{ut}'")

    if ut == "event":
        et = data.get("event_type")
        if et is None:
            fail("'event_type' is required when update_type is 'event'")
            errors.append("event_type_missing")
        elif et not in VALID_EVENT_TYPES:
            fail(f"'event_type' '{et}' is not a recognised event type")
            warn(f"Valid types: {sorted(VALID_EVENT_TYPES)}")
            errors.append("event_type_invalid")
        else:
            ok(f"event_type: '{et}'")

    if ut == "heartbeat" and data.get("event_type") is not None:
        warn("'event_type' is set but update_type is 'heartbeat' — event_type will be ignored")


def validate_timestamp(data, errors, warnings):
    header("Checking timestamp...")
    ts = data.get("timestamp")
    if ts is None:
        fail("'timestamp' is missing")
        errors.append("timestamp_missing")
        return
    try:
        datetime.fromisoformat(ts.replace("Z", "+00:00"))
        ok(f"timestamp valid: {ts}")
    except (ValueError, AttributeError):
        fail(f"'timestamp' is not valid ISO 8601: '{ts}'")
        errors.append("timestamp_invalid")


def validate_player(data, errors, warnings):
    header("Checking player block...")
    player = data.get("player", {})
    if not isinstance(player, dict):
        fail("'player' must be an object")
        errors.append("player_invalid")
        return

    hp = player.get("health_percent")
    if hp is not None:
        if not isinstance(hp, (int, float)) or not (0.0 <= hp <= 1.0):
            fail(f"'player.health_percent' must be a float between 0.0 and 1.0 — got '{hp}'")
            errors.append("health_percent_invalid")
        else:
            ok(f"health_percent: {hp}")

    level = player.get("level")
    if level is not None and not isinstance(level, int):
        fail(f"'player.level' must be an integer — got '{level}'")
        errors.append("level_invalid")
    elif level is not None:
        ok(f"level: {level}")

    if player.get("name") is None:
        warn("'player.name' is null — DM won't be able to address the character by name")


def validate_location(data, errors, warnings):
    header("Checking location block...")
    location = data.get("location", {})
    if not isinstance(location, dict):
        fail("'location' must be an object")
        errors.append("location_invalid")
        return

    if location.get("name") is None:
        warn("'location.name' is null — DM won't know where the player is")
    else:
        ok(f"location: {location.get('name')}")


def validate_quests(data, errors, warnings):
    header("Checking quests block...")
    quests = data.get("quests", {})
    if not isinstance(quests, dict):
        fail("'quests' must be an object")
        errors.append("quests_invalid")
        return

    active = quests.get("active")
    if active is None:
        warn("'quests.active' is null — DM won't have quest context")
    elif not isinstance(active, list):
        fail("'quests.active' must be an array")
        errors.append("quests_active_invalid")
    else:
        ok(f"active quests: {len(active)} found")
        for i, quest in enumerate(active):
            if "name" not in quest:
                fail(f"Quest at index {i} is missing required 'name' field")
                errors.append(f"quest_{i}_missing_name")


def validate_entities(data, errors, warnings):
    header("Checking entities_nearby...")
    entities = data.get("entities_nearby")
    if entities is None:
        warn("'entities_nearby' is null — DM won't know who's around")
        return
    if not isinstance(entities, list):
        fail("'entities_nearby' must be an array")
        errors.append("entities_invalid")
        return

    ok(f"{len(entities)} entities nearby")
    for i, entity in enumerate(entities):
        if "name" not in entity:
            fail(f"Entity at index {i} missing required 'name' field")
            errors.append(f"entity_{i}_missing_name")
        if "type" not in entity:
            fail(f"Entity at index {i} missing required 'type' field")
            errors.append(f"entity_{i}_missing_type")


def validate_recent_events(data, errors, warnings):
    header("Checking recent_events...")
    events = data.get("recent_events")
    if events is None:
        warn("'recent_events' is null — DM won't have event history")
        return
    if not isinstance(events, list):
        fail("'recent_events' must be an array")
        errors.append("recent_events_invalid")
        return

    ok(f"{len(events)} recent events found")
    for i, event in enumerate(events):
        if "event" not in event:
            fail(f"Event at index {i} missing required 'event' field")
            errors.append(f"event_{i}_missing_description")
        if "timestamp" not in event:
            warn(f"Event at index {i} missing 'timestamp' — recommended but not required")


def validate_plugin_extras(data, errors, warnings):
    header("Checking plugin_extras...")
    extras = data.get("plugin_extras")
    if not isinstance(extras, dict):
        fail("'plugin_extras' must be an object (use {} if empty, not null)")
        errors.append("plugin_extras_invalid")
    else:
        keys = list(extras.keys())
        if keys:
            ok(f"plugin_extras contains {len(keys)} custom field(s): {keys}")
        else:
            ok("plugin_extras present and empty — that's fine")


# ── Programmatic validator (used by server.py) ─────────────────────────────────

def validate_data(data: dict):
    """
    Validate a game state dict against the ContextForge schema.
    Returns (errors, warnings) as lists of strings.
    Used by server.py to validate incoming plugin POST requests.
    """
    errors = []
    warnings = []

    validate_top_level(data, errors, warnings)
    validate_update_type(data, errors, warnings)
    validate_timestamp(data, errors, warnings)
    validate_player(data, errors, warnings)
    validate_location(data, errors, warnings)
    validate_quests(data, errors, warnings)
    validate_entities(data, errors, warnings)
    validate_recent_events(data, errors, warnings)
    validate_plugin_extras(data, errors, warnings)

    return errors, warnings


# ── Main ───────────────────────────────────────────────────────────────────────

def validate(filepath):
    print(f"\n{BOLD}ContextForge Schema Validator v0.1{RESET}")
    print(f"Validating: {filepath}\n")

    # Load the file
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"{RED}File not found: {filepath}{RESET}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"{RED}Invalid JSON: {e}{RESET}")
        sys.exit(1)

    errors = []
    warnings = []

    # Run all validators
    validate_top_level(data, errors, warnings)
    validate_update_type(data, errors, warnings)
    validate_timestamp(data, errors, warnings)
    validate_player(data, errors, warnings)
    validate_location(data, errors, warnings)
    validate_quests(data, errors, warnings)
    validate_entities(data, errors, warnings)
    validate_recent_events(data, errors, warnings)
    validate_plugin_extras(data, errors, warnings)

    # Summary
    print(f"\n{'─' * 50}")
    if not errors:
        print(f"\n{GREEN}{BOLD}✓ Valid ContextForge schema{RESET}")
        print(f"  {len(warnings)} warning(s)\n")
    else:
        print(f"\n{RED}{BOLD}✗ Validation failed — {len(errors)} error(s){RESET}")
        print(f"  {len(warnings)} warning(s)\n")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python schema_validator.py <path_to_json_file>")
        sys.exit(1)
    validate(sys.argv[1])
