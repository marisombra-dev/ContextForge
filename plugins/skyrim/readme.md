# ContextForge — Skyrim SE Plugin

The official Skyrim Special Edition plugin for ContextForge.
Bridges your game state to your DM via MinAI.

---

## What this does

Watches Skyrim while you play. Reads game state from MinAI every 2 seconds,
fires events immediately when something significant happens, and sends a full
heartbeat every 30 seconds. Your DM sees everything.

---

## Requirements

Before this plugin will work, you need:

- **Skyrim Special Edition** (LE not supported)
- **SKSE64** — [skse.silverlock.org](https://skse.silverlock.org)
- **MinAI** — [github.com/MinAI](https://github.com/MinAI-Project/MinAI) — provides the game state bridge
- **ContextForge core** running on `localhost:7842` — [github.com/marisombra-dev/ContextForge](https://github.com/marisombra-dev/ContextForge)
- **Python 3.10+**
- **httpx** — `pip install httpx`

---

## Installation

**1. Install SKSE64 and MinAI**

Follow the instructions in each project's README. MinAI needs to be installed
and running before this plugin can read anything.

Confirm MinAI is working by checking that `current_state.json` is being written
to its output folder. That file is what this plugin reads.

**2. Clone or download this plugin**

If you cloned the main ContextForge repo, this plugin lives at:
```
ContextForge/plugins/skyrim/
```

**3. Configure the MinAI path**

Open `skyrim_bridge.py` and update this line to match your MinAI installation:

```python
MINAI_STATE_PATH = "C:/MinAI/current_state.json"
```

If you're not sure where MinAI writes its state file, check MinAI's own config.

**4. Start ContextForge core first**

```bash
cd ContextForge
python core/server.py
```

He needs to be running before the bridge starts sending him things.

**5. Launch Skyrim and load your save**

Get into the game before starting the loop. MinAI needs an active game session
to write state.

**6. Start the bridge**

```bash
cd ContextForge/plugins/skyrim
python skyrim_heartbeat_loop.py
```

You should see:
```
[12:00:00] Loop started. Watching for Skyrim...
[12:00:02] MinAI state found. Watching.
[12:00:02] Heartbeat →
[12:00:03] DM: Well. Here we are again...
```

That's him. He's watching. 🖤

---

## Options

```bash
# Faster heartbeat (15 seconds instead of 30)
python skyrim_heartbeat_loop.py --interval 15

# Custom MinAI path
python skyrim_heartbeat_loop.py --minai-path "D:/Games/MinAI/current_state.json"
```

---

## Events the DM reacts to immediately

| Event | What triggers it |
|---|---|
| `combat_start` | Combat begins |
| `combat_end` | Combat ends |
| `player_death` | Health hits zero |
| `location_change` | You enter a new cell |
| `level_up` | Player levels up |
| `quest_update` | Active quest stage changes |
| `dialogue_start` | Conversation with NPC begins |

Everything else comes through on the heartbeat.

---

## Testing without Skyrim running

```bash
python skyrim_bridge.py --test
```

Uses the mock state file from the ContextForge repo to test translation and
server connection without needing Skyrim open. Useful for confirming your
setup is working before you launch the game.

---

## Troubleshooting

**"MinAI state not found. Waiting for Skyrim to launch..."**
MinAI isn't writing its state file yet. Make sure Skyrim is running with an
active save loaded, and that MinAI is installed correctly.

**"ContextForge server not reachable."**
`server.py` isn't running. Start it first, then the loop will reconnect
automatically on the next cycle.

**DM is responding but state seems wrong**
Check that `MINAI_STATE_PATH` in `skyrim_bridge.py` points to the correct file.
Run `--test` mode and inspect the translated output — the raw MinAI state
prints alongside it so you can see what's being read.

---

## Contributing

If MinAI changes its output format and something breaks, the fix lives entirely
in `skyrim_bridge.py` in the translation functions. Nothing else needs to change.

If you want to add a new event type, add the detector to `EventDetector.update()`
in `skyrim_heartbeat_loop.py` and the event string to `plugins.json` in the
core registry.

Pull requests welcome.

---

*Built alongside ContextForge v0.2*
*One afternoon. One vision. Legendary copy-paste energy.*
