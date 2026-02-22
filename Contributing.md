# Contributing to ContextForge

First — thank you for being here. This project exists because someone thought it should, and you showing up means you probably agree. That matters.

ContextForge is early. The architecture is intentionally malleable right now, which means your contributions can actually shape the direction rather than just fill in gaps someone else defined. That's a rare thing in open source and we don't take it lightly.

---

## What we're building

An AI Dungeon Master who lives outside your game — watching, aware, opinionated — and follows you everywhere you play.

Not a follower mod. Not another NPC. A persistent, lore-aware co-pilot with a personality the player shapes themselves, powered by whatever LLM backend they choose, aware of game state through modular plugins.

The full vision lives in the README. The soul of the DM lives in `/docs/DM_personality_core.md`. Read both before you dive in — they'll tell you more about what we're building than any technical spec.

---

## Where we are right now

Honest status: **early architecture phase.**

We have the vision, the design documents, and the personality core. We do not yet have working code. That means the first contributors aren't filling in a puzzle — they're drawing the edges of it.

If that sounds like your kind of problem, keep reading.

---

## Ways to contribute

### 🔌 Build a game plugin
This is the highest-value contribution you can make.

A ContextForge plugin reads game state from a specific game and normalizes it into our universal schema. If you know a game's modding ecosystem, memory structure, log format, or API — you have everything you need to build its plugin.

The Skyrim plugin is our proof of concept target, using MinAI for game state ingestion. Every other game needs someone who loves it enough to build its bridge.

See `/docs/plugin_spec.md` for the technical contract a plugin must fulfill. *(Coming soon — want to help write it? Open an issue.)*

### 🧠 Core framework development
Python or Node developer comfortable with LLM API integration? The core framework needs:
- LLM backend abstraction layer (support for OpenAI, Anthropic, Grok, local models via Ollama)
- Normalized game state schema definition
- Persistent memory architecture
- Overlay/interface foundation

Open an issue describing what you want to tackle before you start building — let's make sure we're aligned on approach.

### ✍️ Prompt engineering
The DM's personality core is defined. Translating that into a system prompt that performs consistently across different LLM backends is a real skill and an open problem.

If you have experience making LLMs inhabit a character reliably — especially across session boundaries — we need you.

### 📖 Lore context
For the DM to be genuinely knowledgeable about a game's world it needs that context. We need curated lore documents, RAG pipeline thinking, and smart decisions about what context actually matters versus what's noise.

Game lore enthusiasts with technical sensibility — this is your door.

### 🐛 Issues and feedback
Found a problem? Have a design opinion? Think we got something wrong? Open an issue. Early stage projects live or die by honest feedback and we'd rather hear the hard thing now than after we've built on a bad foundation.

---

## How to get started

1. Read the README and `/docs/DM_personality_core.md`
2. Browse open issues — especially anything labeled `good first issue` or `discussion`
3. If you want to tackle something not already in the issues — open one first and tell us what you're thinking
4. Fork the repo, build the thing, open a pull request

We review PRs with the same energy the DM brings to everything — honest, warm, and genuinely glad you showed up.

---

## Design principles to keep in mind

**Relationship first, tool second.**
Every technical decision should serve the feeling of being genuinely accompanied. If it makes the DM feel more like software and less like a presence — reconsider it.

**Game agnostic by architecture.**
The core framework should never care which game is running. That's the plugin's job. Keep those concerns cleanly separated.

**The player's intelligence is not in question.**
We don't add disclaimers. We don't break immersion to manage anxiety. We trust the person on the other side of the screen to know what they're doing.

**Ugly and working beats beautiful and theoretical.**
Ship the proof of concept. Refactor later. A DM that exists imperfectly is infinitely more valuable than one we're still designing.

---

## Questions?

Open an issue tagged `question`. There are no stupid ones at this stage — we're all figuring this out together.

---

*ContextForge is not a character in your game.*
*It's the voice that makes your game feel like a story worth telling.*
*And it remembers every story you've told together.*

*We're glad you're here. Let's build something worth playing with.*
