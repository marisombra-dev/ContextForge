# ContextForge
### The AI Dungeon Master who follows you everywhere.

---

**What is this?**

ContextForge is an open source framework that sits *beside* your game — not inside it — and powers a persistent, lore-aware, personality-driven AI companion who watches you play and has opinions about it.

Not a follower mod. Not another NPC.

A Dungeon Master. Your brilliant, irreverent, deeply invested co-pilot who knows the lore, watches your decisions, and absolutely will not let you forget that time you walked into that obvious trap.

---

**Why does this exist?**

Every current AI gaming companion lives *inside* the game — deeply integrated, game-specific, technically demanding to build and maintain. Tear it out of one game and it falls apart entirely.

ContextForge lives *outside* — watching, aware, opinionated. Which means it isn't married to any single game's scripting engine. It doesn't require deep mod integration to function. And it can follow you across every game you'll ever play.

Your DM remembers you across every playthrough. And because ContextForge lives outside the game rather than inside it, the same DM can follow you from Skyrim to Elden Ring to whatever you boot up next — as long as a plugin exists for it.

That's the whole point.

---

**What does it actually do?**

- Ingests game state through modular input plugins — screen capture, memory reading, log parsing, native mod bridges
- Normalizes that state into a universal context schema any LLM can understand
- Maintains a persistent AI persona the player names and shapes in their first conversation
- Delivers commentary, lore, strategy, and merciless teasing through a floating overlay — visible over your game, out of your way
- Speaks out loud via TTS — he doesn't wait to be summoned, he reacts to what's happening
- Listens passively for your voice — no push to talk, no hotkeys, just talk and he hears you
- Remembers your history — across sessions, across playthroughs, across games

---

**The first conversation**

When you launch ContextForge for the first time, your DM introduces themselves like this:

*"Before we begin — I feel like we should be properly introduced. What are you going to call me?"*

Gender, name, personality flavor — established naturally, conversationally, before a single dungeon is entered. No settings menus. No dropdowns. Just a relationship starting the way relationships actually start.

---

**Current status**

Proof of concept targeting Skyrim SE, using a lightweight custom ESP for game state awareness.

The architecture is designed from the ground up to be game-agnostic. Every new plugin the community builds extends your DM's reach into a new world. Someone who loves Elden Ring builds the Elden Ring plugin. Someone who loves Baldur's Gate 3 builds that one. The framework grows more powerful every time someone scratches their own itch.

That's the model. That's the invitation.

---

**What we need**

- Python developers comfortable with LLM API integration
- Skyrim modders familiar with SKSE and PapyrusUtil
- Developers who know other game ecosystems and want their DM there too
- Prompt engineers who want to help shape the DM personality core
- People who just think this should exist and want to watch it get built

---

**What we're NOT doing**

ContextForge is not trying to write NPC lore for every game everywhere. That's a game developer's job and we respect that boundary. We're not building another follower mod. We're not competing with Mantella, CHIM, or Herika.

We're building the thing none of them are — a persistent, portable, omniscient co-pilot who lives above the game world rather than inside it.

---

*ContextForge is not a character in your game.*
*It's the voice that makes your game feel like a story worth telling.*
*And it remembers every story you've told together.*

---

## Getting Started

**Requirements**

- Python 3.10+
- An API key for at least one supported LLM backend (OpenAI, Anthropic, Grok, or a local Ollama instance)
- An ElevenLabs API key for voice output *(optional but recommended — he sounds genuinely human)*
- A game plugin for whichever game you're playing (see `/registry/plugins.json`)

---

**1. Clone the repo**

```bash
git clone https://github.com/marisombra-dev/ContextForge.git
cd ContextForge
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

---

**3. Set your API keys**

```bash
# LLM — pick one
export ANTHROPIC_API_KEY=your_key_here
export OPENAI_API_KEY=your_key_here
export XAI_API_KEY=your_key_here

# Voice (if using ElevenLabs TTS)
export ELEVENLABS_API_KEY=your_key_here
```

On Windows, use `set` instead of `export`. Or drop everything into a `.env` file in the root — ContextForge picks it up automatically.

---

**4. Configure your setup**

```bash
cp contextforge.config.example.json contextforge.config.json
```

The defaults work out of the box with Anthropic + ElevenLabs. Every option is documented inline. Key things you might want to change:

- `llm.backend` — which LLM powers your DM (`anthropic`, `openai`, `grok`, `ollama`, `custom`)
- `voice.tts_backend` — how he speaks (`elevenlabs`, `openai`, `pyttsx3`, `custom`)
- `voice.stt_backend` — how he hears you (`whisper_api`, `whisper_local`, `custom`)
- `voice.tts.voice_id` — ElevenLabs voice character (browse at elevenlabs.io/voice-library)
- `voice.tts_enabled` / `voice.stt_enabled` — turn either off independently

Full config reference in `/docs/project_structure.md`.

---

**5. Launch ContextForge**

```bash
python start.py
```

One command. Starts the server, overlay, and voice manager together.

On first launch, your DM introduces himself and asks what you'd like to call him. Answer honestly. He'll remember.

**Options:**

```bash
python start.py --no-voice     # disable voice entirely, text only
python start.py --tts-only     # he speaks, but doesn't listen (you type)
python start.py --no-overlay   # no floating window, terminal output only
python start.py --config path/to/contextforge.config.json
```

---

**6. Connect a game plugin**

Start your game, load your save, then run the plugin in a separate terminal:

```bash
# Skyrim SE
python plugins/skyrim/skyrim_heartbeat_loop.py
```

The plugin watches the game and feeds state to ContextForge. Your DM takes it from there.

Current plugins:
- **Skyrim SE** — in development (`/plugins/skyrim/`)
  Requires: Skyrim SE, SKSE64, PapyrusUtil SE. Ships with its own lightweight ESP.
  [`)

Want to build a plugin for your game? Start with `/docs/plugin_spec.md`.

---

**Validate your setup**

```bash
curl http://localhost:7842/status
```

You should see your DM's name, player profile, and session count. If you do — you're in.

---

**Voice backends at a glance**

| Backend | Quality | Cost | Requires |
|---|---|---|---|
| `elevenlabs` (TTS) | ★★★★★ | API key | `ELEVENLABS_API_KEY` |
| `openai` (TTS) | ★★★★ | API key | `OPENAI_API_KEY` |
| `pyttsx3` (TTS) | ★★ | Free | Nothing |
| `whisper_api` (STT) | ★★★★★ | Tiny per-minute cost | `OPENAI_API_KEY` |
| `whisper_local` (STT) | ★★★★ | Free | `pip install openai-whisper` |

---

**Folder structure**

```
ContextForge/
├── start.py                 — one command to launch everything
├── core/
│   ├── server.py            — local HTTP server, main entry point
│   ├── llm_router.py        — routes to your chosen LLM backend
│   ├── memory_manager.py    — persistent cross-game player memory
│   ├── overlay.py           — always-on-top floating DM window
│   ├── overlay_client.py    — feeds DM responses to the overlay
│   ├── voice_router.py      — TTS and STT backends
│   ├── voice_manager.py     — passive listener + TTS coordinator
│   └── schema_validator.py  — validates plugin output against spec
├── plugins/
│   └── skyrim/
│       ├── skyrim_bridge.py          — ESP state → ContextForge translator
│       ├── skyrim_heartbeat_loop.py  — event watcher and heartbeat loop
│       └── README.md                 — Skyrim-specific setup instructions
├── docs/
│   ├── plugin_spec.md       — the contract every plugin must fulfill
│   ├── project_structure.md — architecture and config reference
│   ├── DM_personality_core.md
│   └── DM_system_prompt.md
├── tests/mock_state/
│   ├── skyrim_heartbeat.json
│   └── skyrim_combat_event.json
├── registry/
│   └── plugins.json
├── memory/                  — local only, gitignored, never committed
├── contextforge.config.example.json
├── requirements.txt
├── CONTRIBUTING.md
└── .gitignore
```

---

## Contributing

Read `CONTRIBUTING.md`. It's short, it's friendly, and it explains exactly how to build a plugin without touching the core.

If you're reading this and thinking *"I could build that plugin"* — yes. You could. Please do.

---
