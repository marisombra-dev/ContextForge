# ContextForge — Skyrim SE Plugin

The official Skyrim Special Edition plugin for ContextForge.
Ships with its own lightweight ESP — no external AI mod dependencies.

---

## What this does

Watches Skyrim while you play. A small ESP runs inside the game and writes your
current game state to a JSON file every 30 seconds, plus immediately when
something significant happens. ContextForge reads that file and your DM reacts.

He sees your health, your location, your active quests, nearby enemies, your
followers, your bounty, the time of day, the weather, whether you're sneaking
into somewhere you absolutely should not be sneaking into. All of it.

---

## Requirements

- **Skyrim Special Edition** (LE not supported)
- **SKSE64** — [skse.silverlock.org](https://skse.silverlock.org)
- **PapyrusUtil SE** — [nexusmods.com/skyrimspecialedition/mods/13048](https://www.nexusmods.com/skyrimspecialedition/mods/13048)
- **Skyrim SE Creation Kit** — free on Steam, needed to compile the scripts
- **ContextForge core** running on `localhost:7842`
- **Python 3.10+**
- **httpx** — included in `requirements.txt`

That's it. No AI mods. No NPC overhauls. No compatibility headaches.

---

## How it works

The plugin has two parts:

**Inside Skyrim** — a Papyrus script (`ContextForge.psc`) runs on a quest that
autostarts when you load a save. It collects game state and writes it to
`Data/ContextForge/current_state.json` using PapyrusUtil's JsonUtil.

**Outside Skyrim** — `skyrim_heartbeat_loop.py` watches that file, detects
changes, and POSTs updates to the ContextForge core server. Your DM responds.

---

## Installation

**1. Install SKSE64**

Follow the instructions at [skse.silverlock.org](https://skse.silverlock.org).
Make sure it launches correctly before continuing.

**2. Install PapyrusUtil SE**

Download from Nexus and install via your mod manager (MO2, Vortex, etc.).
PapyrusUtil is one of the most widely used SKSE libraries — you may already have it.

**3. Compile the Papyrus scripts**

The scripts live in `plugins/skyrim/papyrus/`:
- `ContextForge.psc`
- `ContextForgeQuestReporter.psc`

To compile them:

1. Open the **Skyrim SE Creation Kit** (free on Steam)
2. Go to **Gameplay → Papyrus Script Manager**
3. Click **Compile** and point it at the `papyrus/` folder
4. Compiled `.pex` files will be generated
5. Place the `.pex` files in your Skyrim `Data/Scripts/` folder

**4. Install ContextForge.esp**

*(ESP file coming in a future release — for now, create it manually in the CK:)*

1. Open the Creation Kit
2. Create a new Quest named `CFMainQuest`
3. Set it to **Start Game Enabled**
4. Add `ContextForge` as a script on the quest
5. Save as `ContextForge.esp`
6. Place `ContextForge.esp` in your `Data/` folder and enable it in your load order

**5. Configure the state file path**

Open `skyrim_bridge.py` and update `STATE_FILE_PATH` to match your Skyrim install:

```python
# Steam default
STATE_FILE_PATH = "C:/Program Files (x86)/Steam/steamapps/common/Skyrim Special Edition/Data/ContextForge/current_state.json"

# GOG
STATE_FILE_PATH = "C:/GOG Games/Skyrim Special Edition/Data/ContextForge/current_state.json"
```

**6. Start ContextForge core**

```bash
python start.py
```

He needs to be running before the bridge starts sending him things.

**7. Launch Skyrim and load your save**

The ESP will autostart `CFMainQuest` and begin writing state immediately.
Confirm it's working by checking that the file exists:

```
Data/ContextForge/current_state.json
```

If the file is there and updating — you're in.

**8. Start the bridge**

```bash
python plugins/skyrim/skyrim_heartbeat_loop.py
```

You should see:
```
[12:00:00] Loop started. Watching for Skyrim...
[12:00:02] State file found. Watching.
[12:00:02] Heartbeat →
[12:00:03] DM: Well. Here we are again...
```

That's him. He's watching. 🖤

---

## Options

```bash
# Faster heartbeat
python skyrim_heartbeat_loop.py --interval 15

# Custom state file path
python skyrim_heartbeat_loop.py --path "D:/Games/Skyrim/Data/ContextForge/current_state.json"
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

## Adding quest tracking

1. Open the quest in the Creation Kit
2. Add `ContextForgeQuestReporter` as a script
3. Set the `QuestDisplayName` property to a human-readable name
4. Compile and save

The DM will now know when that quest advances.

---

## Testing without Skyrim running

```bash
python skyrim_bridge.py --test
```

Uses a fake state that mirrors real ESP output. Run this first to confirm your
Python setup is working before you touch the Creation Kit.

---

## Troubleshooting

**State file not appearing**
The ESP isn't running. Check that `ContextForge.esp` is enabled, SKSE64 is
launching correctly, and PapyrusUtil is installed. Open the in-game console
and type `sqv CFMainQuest` — if the quest shows as running, the script is active.

**State file exists but isn't updating**
PapyrusUtil may not be installed correctly. Reinstall it and confirm it appears
in your SKSE plugin list.

**"ContextForge server not reachable"**
`start.py` isn't running. Start it first — the bridge reconnects automatically.

**DM state seems wrong or stale**
Check `STATE_FILE_PATH` in `skyrim_bridge.py`. Run `--test` mode and inspect
the raw output against what you expect.

---

## File locations

```
plugins/skyrim/
├── skyrim_bridge.py          — reads state file, translates to CF schema
├── skyrim_heartbeat_loop.py  — event watcher and heartbeat loop
├── papyrus/
│   ├── ContextForge.psc              — main game state script
│   └── ContextForgeQuestReporter.psc — attach to quests for tracking
└── README.md
```

Compiled `.pex` files → `Data/Scripts/`
State file → `Data/ContextForge/current_state.json`

---

## Contributing

Extensions to what the ESP tracks live in `ContextForge.psc`.
The bridge translator in `skyrim_bridge.py` needs a matching update
to surface new data to ContextForge.

Pull requests welcome.

---

*Built for ContextForge v0.2*
*One vision. Two afternoons. Legendary copy-paste energy.*
