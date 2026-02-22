# ContextForge — Project Structure
### Where everything lives and why.

---

## Repository Architecture

ContextForge uses a **multi-repo model**.

The core framework lives here. Plugins live in their own separate repositories, maintained by their authors, and are registered in the plugin registry below.

This means:
- Plugin authors have full ownership of their work
- The core repo stays clean and focused
- Plugins can update independently without core team involvement
- The ecosystem can grow without the main repo becoming unmanageable

---

## Core Repository Structure

```
ContextForge/
│
├── README.md                          # What this is and why it exists
├── CONTRIBUTING.md                    # How to get involved
├── contextforge.config.json           # User configuration (see below)
│
├── core/                              # Core framework — the engine
│   ├── server.py                      # Local HTTP server, receives plugin state
│   ├── llm_router.py                  # LLM backend abstraction layer
│   ├── memory_manager.py              # Persistent memory across sessions
│   ├── context_builder.py             # Assembles game state into LLM context
│   └── overlay.py                     # Player-facing interface
│
├── prompts/                           # DM personality and system prompts
│   ├── DM_system_prompt.md            # The briefing — what gets sent to the LLM
│   └── DM_personality_core.md         # The soul document — what he is
│
├── docs/                              # Documentation
│   ├── plugin_spec.md                 # The contract every plugin must fulfill
│   ├── project_structure.md           # This document
│   └── llm_backends.md                # Supported LLM backends and configuration
│
├── registry/                          # Community plugin registry
│   └── plugins.json                   # Index of all known ContextForge plugins
│
└── tests/                             # Core framework tests
    ├── test_schema_validator.py        # Validates plugin output against spec
    └── mock_state/                    # Mock game state for testing without a game
        ├── skyrim_heartbeat.json
        └── skyrim_combat_event.json
```

---

## Plugin Repository Structure

Each plugin lives in its own repo, typically named `contextforge-plugin-[gamename]`.

```
contextforge-plugin-skyrim/
│
├── README.md                          # How to install and use this plugin
├── plugin.json                        # Plugin manifest (required — see plugin_spec.md)
│
├── src/                               # Plugin source
│   ├── state_reader.py                # Reads game state from the game
│   ├── normalizer.py                  # Translates to ContextForge schema
│   └── event_detector.py             # Identifies and fires event triggers
│
├── mod/                               # Game-side mod files if required
│   └── (e.g. SKSE plugin, Papyrus scripts, MinAI config)
│
└── tests/
    └── test_normalizer.py
```

---

## Configuration — contextforge.config.json

Lives in the root of the installation. Created on first run with sensible defaults.

```json
{
  "version": "0.1",

  "server": {
    "port": 7842,
    "host": "localhost"
  },

  "llm": {
    "backend": "openai",
    "model": "gpt-4o",
    "api_key_env": "OPENAI_API_KEY",
    "max_tokens": 300,
    "temperature": 0.85
  },

  "dm": {
    "name": null,
    "gender": null,
    "onboarding_complete": false
  },

  "memory": {
    "enabled": true,
    "storage_path": "./memory/",
    "max_session_history": 50,
    "cross_game_memory": true
  },

  "overlay": {
    "enabled": true,
    "position": "bottom_right",
    "opacity": 0.9,
    "hotkey": "F9"
  },

  "heartbeat_interval_seconds": 30
}
```

---

## Supported LLM Backends

ContextForge is backend agnostic. Configure in `contextforge.config.json`:

| Backend | Config value | Notes |
|---|---|---|
| OpenAI (GPT-4o etc.) | `"openai"` | Requires `OPENAI_API_KEY` |
| Anthropic (Claude) | `"anthropic"` | Requires `ANTHROPIC_API_KEY` |
| xAI (Grok) | `"grok"` | Requires `XAI_API_KEY` |
| Local via Ollama | `"ollama"` | No API key required |
| Custom endpoint | `"custom"` | Set `custom_endpoint` in config |

---

## Memory Storage

Player memory lives in `/memory/` — never committed to the repo, always local to the player.

```
memory/
├── player_profile.json           # Name, preferences, established DM relationship
├── sessions/                     # Per-session event logs
│   ├── 2024-03-15_skyrim.json
│   └── 2024-03-22_skyrim.json
└── cross_game/                   # Memories that travel between games
    └── persistent_notes.json
```

*The `/memory/` directory is gitignored by default. Player data stays on the player's machine.*

---

## Plugin Registry — registry/plugins.json

```json
{
  "plugins": [
    {
      "plugin_id": "skyrim_se",
      "game_name": "The Elder Scrolls V: Skyrim Special Edition",
      "repo_url": "https://github.com/[author]/contextforge-plugin-skyrim",
      "author": "TBD",
      "status": "in_development",
      "contextforge_min_version": "0.1"
    }
  ]
}
```

Submit a PR to add your plugin to the registry once it's functional.

---

## First Run Experience

On first launch ContextForge checks for `dm.onboarding_complete: false` in config and initiates the introduction sequence:

*"Before we begin — I feel like we should be properly introduced. What are you going to call me?"*

Gender and name are stored in config after this conversation. The DM never introduces himself again — he was always already here.

---

*The structure serves the soul.*
*Everything in its place so he can be fully present in yours.*
