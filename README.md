
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
- Delivers commentary, lore context, strategy, and merciless teasing through a clean overlay interface
- Remembers your history — across sessions, across playthroughs, across games

---

**The first conversation**

When you launch ContextForge for the first time, your DM introduces themselves like this:

*"Before we begin — I feel like we should be properly introduced. What are you going to call me?"*

Gender, name, personality flavor — established naturally, conversationally, before a single dungeon is entered. No settings menus. No dropdowns. Just a relationship starting the way relationships actually start.

---

**Current status**

Proof of concept targeting Skyrim SE, using MinAI for game state awareness.

The architecture is designed from the ground up to be game-agnostic. Every new plugin the community builds extends your DM's reach into a new world. Someone who loves Elden Ring builds the Elden Ring plugin. Someone who loves Baldur's Gate 3 builds that one. The framework grows more powerful every time someone scratches their own itch.

That's the model. That's the invitation.

---

**What we need**

- Python/Node developers comfortable with LLM API integration
- Skyrim modders familiar with SKSE and MinAI
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

**Getting Started / Contributing**

*(Documentation incoming — this is an early flag in the ground. If you're reading this and thinking "I could build that plugin" — yes. You could. Please do.)*
