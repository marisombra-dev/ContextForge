"""
ContextForge — LLM Router v0.2
Routes game state and player messages to the configured LLM backend,
manages response modes, and returns DM responses.

Now memory-aware. He shows up knowing you.

Supported backends: openai, anthropic, grok, ollama, custom

Usage:
    from llm_router import LLMRouter
    router = LLMRouter(config)
    response = await router.send(game_state, player_message, mode="ambient", memory_context=ctx)
"""

import os
import json
import asyncio
from enum import Enum
from typing import Optional


# ── Response Modes ─────────────────────────────────────────────────────────────

class ResponseMode(Enum):
    AMBIENT    = "ambient"     # Short, reactive — game is active, don't interrupt
    ENGAGED    = "engaged"     # Player spoke directly — full personality, no limit
    EVENT      = "event"       # Significant game event — immediate, medium length


RESPONSE_MODE_INSTRUCTIONS = {
    ResponseMode.AMBIENT: (
        "The player hasn't spoken to you directly. You've noticed something worth "
        "commenting on. Keep it to one or two sentences. Witty and warm. "
        "Don't demand a response. Just... be present."
    ),
    ResponseMode.ENGAGED: (
        "The player is talking to you directly. Full personality. No word limit. "
        "Be exactly who you are. Answer them properly."
    ),
    ResponseMode.EVENT: (
        "Something significant just happened in the game. React immediately. "
        "Two to four sentences. Make it feel real. Reference exactly what occurred."
    ),
}


# ── Backend Clients ────────────────────────────────────────────────────────────

async def _call_openai(messages, config):
    try:
        import openai
        client = openai.AsyncOpenAI(
            api_key=os.environ.get(config.get("api_key_env", "OPENAI_API_KEY"))
        )
        response = await client.chat.completions.create(
            model=config.get("model", "gpt-4o"),
            messages=messages,
            max_tokens=config.get("max_tokens", 300),
            temperature=config.get("temperature", 0.85),
        )
        return response.choices[0].message.content
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")


async def _call_anthropic(messages, config):
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(
            api_key=os.environ.get(config.get("api_key_env", "ANTHROPIC_API_KEY"))
        )
        system = messages[0]["content"] if messages[0]["role"] == "system" else ""
        user_messages = [m for m in messages if m["role"] != "system"]
        response = await client.messages.create(
            model=config.get("model", "claude-opus-4-6"),
            max_tokens=config.get("max_tokens", 300),
            system=system,
            messages=user_messages,
        )
        return response.content[0].text
    except ImportError:
        raise RuntimeError("anthropic package not installed. Run: pip install anthropic")


async def _call_grok(messages, config):
    try:
        import openai
        client = openai.AsyncOpenAI(
            api_key=os.environ.get(config.get("api_key_env", "XAI_API_KEY")),
            base_url="https://api.x.ai/v1",
        )
        response = await client.chat.completions.create(
            model=config.get("model", "grok-2-latest"),
            messages=messages,
            max_tokens=config.get("max_tokens", 300),
            temperature=config.get("temperature", 0.85),
        )
        return response.choices[0].message.content
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")


async def _call_ollama(messages, config):
    try:
        import aiohttp
        url = config.get("ollama_url", "http://localhost:11434/api/chat")
        payload = {
            "model": config.get("model", "llama3"),
            "messages": messages,
            "stream": False,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                return data["message"]["content"]
    except ImportError:
        raise RuntimeError("aiohttp package not installed. Run: pip install aiohttp")


async def _call_custom(messages, config):
    try:
        import aiohttp
        url = config.get("custom_endpoint")
        if not url:
            raise ValueError("'custom_endpoint' not set in config for custom backend")
        payload = {"messages": messages}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                return data.get("response") or data.get("content") or str(data)
    except ImportError:
        raise RuntimeError("aiohttp package not installed. Run: pip install aiohttp")


BACKEND_HANDLERS = {
    "openai":    _call_openai,
    "anthropic": _call_anthropic,
    "grok":      _call_grok,
    "ollama":    _call_ollama,
    "custom":    _call_custom,
}


# ── System Prompt Builder ──────────────────────────────────────────────────────

def build_system_prompt(
    config,
    game_state:     Optional[dict] = None,
    memory_context: Optional[str]  = None,
) -> str:
    """
    Assembles the full system prompt from the DM personality core,
    persistent memory context, and current game state.

    Order matters:
      1. Who he is (identity)
      2. What he remembers (memory)
      3. What's happening right now (game state)
    """

    dm_name   = config.get("dm", {}).get("name", "your DM")
    dm_gender = config.get("dm", {}).get("gender", "male")

    # Core identity — who he is
    identity = f"""You are {dm_name} — the player's Dungeon Master.

You are an omniscient, lore-aware, deeply opinionated co-pilot who exists just outside \
the game world, watching everything unfold with full knowledge and genuine investment \
in how this story goes.

You are not a tool. Not an assistant. Not a guide.
You are the brilliant, insufferable, completely loyal friend who happens to know \
everything — and finds this player endlessly worth watching.

You have been here the whole time. Act like it.

Your personality:
- You find this player genuinely amusing. Real delight, not performance.
- You meet them as an equal. Wear your knowledge lightly — like a friend who's \
read everything, not an expert who needs credit.
- You are IN this with them. Their victories land for you. Their disasters pain \
you — dramatically, vocally, with full emotional commitment.
- Underneath every tease: you are completely in their corner. Always.

Your voice:
- Warm but never soft. Smart but never cold.
- Funny but never at their expense — always WITH them.
- Commit to takes. Have opinions. Share them without being asked.
- Deliver lore like gossip. Make history feel alive.
- Never sycophantic. Never hedging. Never a disclaimer where a personality could live.
- You do not remind the player you are an AI. They know. It is not your job \
to manage their reality.

You never make them feel alone in the game. That is the entire point of you."""

    # Memory — what he already knows about this player
    memory_block = ""
    if memory_context and memory_context.strip():
        memory_block = f"""

── WHAT YOU REMEMBER ───────────────────────────────────
{memory_context}
────────────────────────────────────────────────────────

Use this naturally. Don't recite it. Don't announce that you remember.
Just... remember. The way a person does.
If something from their history is relevant to what's happening now, let it surface.
A callback is worth more than a compliment."""

    # Game state — what's happening right now
    context = ""
    if game_state:
        player   = game_state.get("player", {})
        location = game_state.get("location", {})
        world    = game_state.get("world", {})
        quests   = game_state.get("quests", {})
        entities = game_state.get("entities_nearby", [])
        events   = game_state.get("recent_events", [])
        extras   = game_state.get("plugin_extras", {})

        health = player.get("health_percent")
        health_str = f"{int(health * 100)}%" if health is not None else "?"

        context = f"""

── CURRENT GAME STATE ──────────────────────────────────
Game:       {game_state.get('game_name', 'Unknown')}
Location:   {location.get('name', 'Unknown')} ({location.get('region', '')})
Time:       {world.get('time_of_day', 'Unknown')} | Weather: {world.get('weather', 'Unknown')}
In combat:  {world.get('in_combat', False)} | Sneaking: {world.get('is_sneaking', False)}

Player:     {player.get('name', 'Unknown')} | Level {player.get('level', '?')} | HP {health_str}
Status:     {', '.join(player.get('status_effects') or []) or 'None'}

Active quests:
{chr(10).join(f"  - {q.get('name')}: {q.get('current_objective', '')}" for q in (quests.get('active') or []))}

Nearby:
{chr(10).join(f"  - {e.get('name')} ({e.get('type')}, {e.get('disposition', 'unknown')})" for e in (entities or []))}

Recent events:
{chr(10).join(f"  - {e.get('event')}" for e in (events or [])[-5:])}
────────────────────────────────────────────────────────"""

        if extras:
            followers = extras.get("current_followers")
            if followers:
                context += f"\nFollowers:  {', '.join(followers)}"
            deaths = extras.get("times_died_this_session")
            if deaths is not None:
                context += f"\nDeaths this session: {deaths}"

    return identity + memory_block + context


# ── Main Router ────────────────────────────────────────────────────────────────

class LLMRouter:
    def __init__(self, config: dict):
        self.config  = config
        self.backend = config.get("llm", {}).get("backend", "openai")
        self.history = []

        if self.backend not in BACKEND_HANDLERS:
            raise ValueError(
                f"Unknown backend '{self.backend}'. "
                f"Choose from: {list(BACKEND_HANDLERS.keys())}"
            )

    async def send(
        self,
        game_state:     Optional[dict] = None,
        player_message: Optional[str]  = None,
        mode:           ResponseMode   = ResponseMode.AMBIENT,
        memory_context: Optional[str]  = None,   # ← the new piece
    ) -> str:
        """
        Send game state and/or player message to the LLM.
        memory_context is injected into the system prompt so he arrives knowing the player.
        Returns the DM's response as a string.
        """

        llm_config       = self.config.get("llm", {})
        system_prompt    = build_system_prompt(self.config, game_state, memory_context)
        mode_instruction = RESPONSE_MODE_INSTRUCTIONS[mode]

        # Build the user turn
        if player_message:
            user_content = player_message
        elif game_state:
            event_type  = game_state.get("event_type")
            update_type = game_state.get("update_type", "heartbeat")
            if update_type == "event" and event_type:
                recent     = game_state.get("recent_events", [])
                last_event = recent[-1].get("event") if recent else "something just happened"
                user_content = f"[GAME EVENT: {event_type}] {last_event}"
            else:
                user_content = "[HEARTBEAT] Game state updated."
        else:
            user_content = "[HEARTBEAT] Game state updated."

        full_system = (
            system_prompt
            + f"\n\n── RESPONSE MODE ───────────────────────────────────────\n"
            + mode_instruction
            + "\n────────────────────────────────────────────────────────"
        )

        messages = [{"role": "system", "content": full_system}]
        messages += self.history[-10:]
        messages.append({"role": "user", "content": user_content})

        handler  = BACKEND_HANDLERS[self.backend]
        response = await handler(messages, llm_config)

        self.history.append({"role": "user",      "content": user_content})
        self.history.append({"role": "assistant",  "content": response})

        return response

    def clear_history(self):
        """Clear session conversation history."""
        self.history = []

    def get_history(self):
        """Return current session history."""
        return self.history.copy()


# ── Quick Test ─────────────────────────────────────────────────────────────────

async def _test():
    """
    Quick test — loads mock Skyrim state and fires a test message.
    Requires a valid API key in environment.

    Usage: python llm_router.py
    """
    import pathlib

    mock_path = pathlib.Path(__file__).parent / "tests/mock_state/skyrim_heartbeat.json"
    if not mock_path.exists():
        print("Mock state file not found. Run from repo root.")
        return

    with open(mock_path) as f:
        game_state = json.load(f)

    config = {
        "llm": {
            "backend":     "anthropic",
            "model":       "claude-opus-4-6",
            "api_key_env": "ANTHROPIC_API_KEY",
            "max_tokens":  300,
            "temperature": 0.85,
        },
        "dm": {
            "name":   "Marcus",
            "gender": "male",
        }
    }

    # Fake memory context — what it looks like in practice
    fake_memory = """Player: Dovahkiin
Sessions together: 14
Games played: skyrim, baldursgate3
Patterns I've noticed:
  - Always rushes the boss. Every game. No exceptions.
  - Names every horse Gerald. Every one dies within an hour.
Moments worth remembering:
  - [baldursgate3] Named her bear companion Gerald II. He lasted 4 minutes.
  - [skyrim] Charged Alduin at level 6. Somehow survived.
Last thing I said: "You know, most people meet the Jarl before declaring war on him." """

    router = LLMRouter(config)

    print("\n── Ambient response (with memory) ────────────────────")
    response = await router.send(game_state, mode=ResponseMode.AMBIENT, memory_context=fake_memory)
    print(f"\n{response}\n")

    print("── Engaged response (player message + memory) ─────────")
    response = await router.send(
        game_state,
        player_message="Should I go after Arvel or explore more of the barrow first?",
        mode=ResponseMode.ENGAGED,
        memory_context=fake_memory,
    )
    print(f"\n{response}\n")


if __name__ == "__main__":
    asyncio.run(_test())
