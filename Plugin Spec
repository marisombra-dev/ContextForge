# ContextForge — Plugin Specification v0.1
### The contract every plugin must fulfill.

---

## Overview

A ContextForge plugin is a modular adapter that reads game state from a specific game and normalizes it into a universal schema the DM can understand.

The core framework never knows or cares which game is running. That's the plugin's entire job — translate whatever your game exposes into the standard format defined in this document.

If your output matches this spec, your plugin works with ContextForge. That's the whole contract.

---

## Update Architecture — Hybrid Model

Plugins deliver game state in two modes simultaneously:

### 1. Heartbeat Updates
Regular ambient state delivered every **30 seconds** regardless of activity.

Keeps the DM generally aware of the world without flooding the context window with noise. Think of this as the DM glancing up from their notes periodically to see what's happening.

### 2. Event Triggers
Immediate delivery when something significant happens.

The DM shouldn't hear about significant events 30 seconds after they occur. These fire instantly:

- Combat started / ended
- Player death or near-death (health below 20%)
- New location entered
- Quest started, updated, or completed
- Significant NPC interaction initiated
- Player level up
- Fast travel used
- Item of significance acquired
- In-game time threshold crossed (dawn, dusk)

*When in doubt — if a player would tell a friend about it, it's an event trigger.*

---

## The Normalized Game State Schema

Every plugin output — whether heartbeat or event — must conform to this JSON schema.

Unpopulated fields should be passed as `null` rather than omitted entirely. The DM handles null gracefully. Missing fields cause errors.

```json
{
  "contextforge_version": "0.1",
  "plugin_id": "string — unique identifier for your plugin e.g. 'skyrim_se'",
  "game_name": "string — human readable e.g. 'The Elder Scrolls V: Skyrim'",
  "update_type": "heartbeat | event",
  "event_type": "string | null — required if update_type is event, see event types below",
  "timestamp": "ISO 8601 timestamp",

  "player": {
    "name": "string | null — character name if available",
    "level": "integer | null",
    "health_current": "integer | null",
    "health_max": "integer | null",
    "health_percent": "float | null — 0.0 to 1.0",
    "status_effects": ["array of strings | null — e.g. 'poisoned', 'well rested'"],
    "faction_standings": ["array of strings | null — e.g. 'Companions: Allied'"]
  },

  "location": {
    "name": "string | null — current location name",
    "type": "string | null — e.g. 'dungeon', 'city', 'wilderness'",
    "region": "string | null — broader area e.g. 'Whiterun Hold'",
    "is_interior": "boolean | null"
  },

  "world": {
    "time_of_day": "string | null — e.g. 'dawn', 'midday', 'night'",
    "weather": "string | null — e.g. 'clear', 'blizzard', 'rain'",
    "in_combat": "boolean | null",
    "is_sneaking": "boolean | null",
    "is_trespassing": "boolean | null"
  },

  "quests": {
    "active": [
      {
        "name": "string",
        "current_objective": "string | null",
        "stage": "string | null"
      }
    ],
    "recently_completed": ["array of quest name strings | null"],
    "recently_failed": ["array of quest name strings | null"]
  },

  "entities_nearby": [
    {
      "name": "string",
      "type": "string — e.g. 'npc', 'enemy', 'creature', 'merchant'",
      "disposition": "string | null — e.g. 'friendly', 'hostile', 'neutral'",
      "is_essential": "boolean | null"
    }
  ],

  "recent_events": [
    {
      "event": "string — plain language description e.g. 'Player killed Bandit Chief'",
      "timestamp": "ISO 8601 timestamp"
    }
  ],

  "plugin_extras": {}
}
```

---

## The plugin_extras Field

Every game exposes unique state that doesn't fit the universal schema. Don't throw it away — put it in `plugin_extras` as key/value pairs.

The DM will receive it and can use it contextually even without formal schema support. Over time commonly used extras get promoted into the core schema.

**Skyrim example:**
```json
"plugin_extras": {
  "shouts_known": ["Unrelenting Force", "Whirlwind Sprint"],
  "is_werewolf": false,
  "bounty_whiterun": 0,
  "bounty_windhelm": 150,
  "current_followers": ["Lydia"]
}
```

---

## Event Type Reference

When `update_type` is `"event"`, the `event_type` field must be one of:

```
combat_start
combat_end
player_death
player_critical_health
location_entered
quest_started
quest_updated
quest_completed
quest_failed
npc_interaction
level_up
fast_travel
significant_item_acquired
time_threshold
plugin_defined
```

Use `plugin_defined` for game-specific events that don't map to the standard list — and open an issue to propose adding it formally if it's broadly applicable.

---

## Delivery Method

Plugins deliver state to the ContextForge core via a **local HTTP endpoint** running on the player's machine.

```
POST http://localhost:7842/state
Content-Type: application/json

{ ...normalized schema... }
```

Port `7842` is the ContextForge default. Configurable in `contextforge.config.json`.

The core framework handles everything after delivery — LLM routing, context window management, DM response, memory persistence. The plugin's job ends at the POST.

---

## Minimum Viable Plugin

Not every field needs to be populated for a plugin to be useful. A plugin that only delivers:

- `game_name`
- `location.name`
- `player.health_percent`
- `world.in_combat`
- `quests.active`
- `recent_events`

...is already enough for the DM to be meaningfully aware and genuinely useful. 

Start there. Populate more fields as you learn what your game exposes. Ship the imperfect version.

---

## Plugin Registration

Every plugin needs a manifest file — `plugin.json` in the plugin root:

```json
{
  "plugin_id": "skyrim_se",
  "game_name": "The Elder Scrolls V: Skyrim Special Edition",
  "author": "your name or handle",
  "version": "0.1.0",
  "contextforge_min_version": "0.1",
  "description": "Skyrim SE plugin via MinAI bridge",
  "supports_events": true,
  "heartbeat_interval_seconds": 30,
  "repo_url": "optional link to your plugin repo"
}
```

---

## Testing Your Plugin

A test endpoint is available during development:

```
POST http://localhost:7842/state/validate
```

Returns a validation report against this spec — missing required fields, type mismatches, unrecognized event types. Use it before you open a PR.

*(Validator implementation: see core framework issues)*

---

## Questions, edge cases, proposals

Open an issue. Tag it `plugin-spec`.

This document is v0.1 and intentionally open to revision. If your game exposes something valuable that doesn't fit the schema — tell us. The spec should serve the plugins, not the other way around.

---

*Build the bridge. The DM will meet you on the other side.*
