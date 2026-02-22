"""
memory_manager.py — ContextForge Core
--------------------------------------
Persistent, cross-game memory for the DM.
He follows the player. Not the character. Not the game. The player.

Memory lives in /memory/{player_id}.json — local, private, gitignored.
One unified identity accumulates across every game, every session.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional


# ── Config ──────────────────────────────────────────────────────────────────

MEMORY_DIR = Path(__file__).parent.parent / "memory"
MAX_RECENT_EVENTS = 50       # hard cap before summarization kicks in
MAX_SUMMARY_ENTRIES = 10     # how many condensed summaries to keep long-term


# ── Data shape ───────────────────────────────────────────────────────────────

def _default_player_memory(player_id: str) -> dict:
    """
    The blank slate. What the DM knows before he knows anything.
    Which is nothing. Which he will fix.
    """
    return {
        "player_id": player_id,
        "name_preference": None,          # what they asked him to call them
        "first_seen": time.time(),
        "last_seen": time.time(),
        "session_count": 0,
        "games_played": [],               # list of game slugs, in order
        "current_game": None,
        "personality_notes": [],          # DM's running observations about the player
        "recurring_patterns": [],         # "always rushes boss fights", "never reads quests"
        "notable_moments": [],            # hand-picked memories worth keeping forever
        "recent_events": [],              # rolling window, trimmed each session
        "long_term_summaries": [],        # compressed history when recent_events overflows
        "dm_last_remark": None,           # last thing the DM said — for continuity
    }


# ── Core I/O ─────────────────────────────────────────────────────────────────

def _memory_path(player_id: str) -> Path:
    return MEMORY_DIR / f"{player_id}.json"


def load_memory(player_id: str) -> dict:
    """
    Load player memory from disk.
    If none exists yet, create a fresh slate and save it immediately.
    """
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path = _memory_path(player_id)

    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            memory = json.load(f)
        # Patch missing keys if schema has evolved
        defaults = _default_player_memory(player_id)
        for key, value in defaults.items():
            memory.setdefault(key, value)
        return memory
    else:
        fresh = _default_player_memory(player_id)
        save_memory(fresh)
        return fresh


def save_memory(memory: dict) -> None:
    """Write memory to disk. Called at session end and after significant events."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path = _memory_path(memory["player_id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


# ── Session lifecycle ─────────────────────────────────────────────────────────

def start_session(player_id: str, game: str) -> dict:
    """
    Called when a session begins.
    Updates tracking fields, returns the loaded memory.
    """
    memory = load_memory(player_id)
    memory["last_seen"] = time.time()
    memory["session_count"] += 1
    memory["current_game"] = game

    if game not in memory["games_played"]:
        memory["games_played"].append(game)

    save_memory(memory)
    return memory


def end_session(memory: dict, session_summary: Optional[str] = None) -> None:
    """
    Called when a session ends.
    Trims recent_events if needed, optionally appends a summary.
    """
    memory["last_seen"] = time.time()
    memory["current_game"] = None

    if session_summary:
        _append_summary(memory, session_summary)

    _trim_recent_events(memory)
    save_memory(memory)


# ── Event logging ─────────────────────────────────────────────────────────────

def log_event(memory: dict, event: dict, autosave: bool = False) -> None:
    """
    Log a game event into recent_events.
    event should be a dict with at least: {"type": str, "description": str, "game": str}
    """
    event.setdefault("timestamp", time.time())
    event.setdefault("game", memory.get("current_game", "unknown"))
    memory["recent_events"].append(event)

    if autosave:
        save_memory(memory)


def log_pattern(memory: dict, pattern: str) -> None:
    """
    Record a behavioral pattern the DM has noticed.
    e.g. "Always fast-travels the moment combat starts"
    Deduped so he doesn't repeat himself.
    """
    if pattern not in memory["recurring_patterns"]:
        memory["recurring_patterns"].append(pattern)


def log_notable_moment(memory: dict, moment: str) -> None:
    """
    Pin a moment worth remembering forever.
    These survive summarization. These are what he brings up at 3am.
    """
    memory["notable_moments"].append({
        "moment": moment,
        "game": memory.get("current_game", "unknown"),
        "timestamp": time.time()
    })


def set_name_preference(memory: dict, name: str) -> None:
    """What the player wants to be called. Sacred. Never overwritten without asking."""
    memory["name_preference"] = name
    save_memory(memory)


def set_dm_last_remark(memory: dict, remark: str) -> None:
    """Track the DM's last line so he doesn't repeat himself awkwardly."""
    memory["dm_last_remark"] = remark


# ── Summarization ─────────────────────────────────────────────────────────────

def _trim_recent_events(memory: dict) -> None:
    """
    If recent_events exceeds MAX_RECENT_EVENTS, compress the oldest half
    into a single summary string and push it to long_term_summaries.
    Keeps the file lean. Keeps the DM sharp.
    """
    events = memory["recent_events"]
    if len(events) <= MAX_RECENT_EVENTS:
        return

    overflow = events[:MAX_RECENT_EVENTS // 2]
    memory["recent_events"] = events[MAX_RECENT_EVENTS // 2:]

    summary = _compress_events(overflow)
    _append_summary(memory, summary)


def _append_summary(memory: dict, summary: str) -> None:
    """Push a summary into long_term_summaries, trimming if over cap."""
    memory["long_term_summaries"].append({
        "summary": summary,
        "timestamp": time.time(),
        "game": memory.get("current_game", "unknown")
    })
    # Keep only the most recent N summaries
    if len(memory["long_term_summaries"]) > MAX_SUMMARY_ENTRIES:
        memory["long_term_summaries"] = memory["long_term_summaries"][-MAX_SUMMARY_ENTRIES:]


def _compress_events(events: list) -> str:
    """
    Naive compression: join descriptions into a paragraph.
    Future versions can pipe this through the LLM for real summarization.
    For now — honest, functional, good enough.
    """
    descriptions = [
        e.get("description", str(e)) for e in events if e
    ]
    return " | ".join(descriptions)


# ── Context builder ───────────────────────────────────────────────────────────

def build_dm_context(memory: dict) -> str:
    """
    Produce a compact context string the DM gets injected into his system prompt.
    Everything he needs to remember without everything he's ever seen.
    """
    lines = []

    name = memory.get("name_preference") or "the player"
    lines.append(f"Player: {name}")
    lines.append(f"Sessions together: {memory['session_count']}")

    games = memory.get("games_played", [])
    if games:
        lines.append(f"Games played: {', '.join(games)}")

    patterns = memory.get("recurring_patterns", [])
    if patterns:
        lines.append("Patterns I've noticed:")
        for p in patterns:
            lines.append(f"  - {p}")

    moments = memory.get("notable_moments", [])
    if moments:
        lines.append("Moments worth remembering:")
        for m in moments[-5:]:  # only last 5 notable moments in prompt
            lines.append(f"  - [{m['game']}] {m['moment']}")

    summaries = memory.get("long_term_summaries", [])
    if summaries:
        lines.append("What I remember from before:")
        for s in summaries[-3:]:  # last 3 summaries
            lines.append(f"  - {s['summary']}")

    recent = memory.get("recent_events", [])
    if recent:
        lines.append("Recent events this session:")
        for e in recent[-10:]:  # last 10 events
            lines.append(f"  - {e.get('description', str(e))}")

    last = memory.get("dm_last_remark")
    if last:
        lines.append(f"Last thing I said: \"{last}\"")

    return "\n".join(lines)


# ── Quick debug ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Smoke test — creates a player, runs a fake session, prints context
    print("=== ContextForge Memory Manager — Smoke Test ===\n")

    mem = start_session("test_player", "skyrim")
    set_name_preference(mem, "Dovahkiin")

    log_event(mem, {"type": "combat", "description": "Rushed a dragon before buffs. Again."})
    log_event(mem, {"type": "exploration", "description": "Skipped the entire main quest to go fishing."})
    log_pattern(mem, "Always rushes the boss. Every game. No exceptions.")
    log_notable_moment(mem, "Named her horse Gerald and then immediately got him killed.")

    set_dm_last_remark(mem, "You know, most people *meet* the Jarl before declaring war on him.")

    print(build_dm_context(mem))
    print("\n--- Saving and reloading ---\n")

    end_session(mem, session_summary="Short session. Chaotic. On brand.")

    reloaded = load_memory("test_player")
    print(build_dm_context(reloaded))
    print("\n✓ Memory persisted and reloaded correctly.")

    # Cleanup test file
    _memory_path("test_player").unlink(missing_ok=True)
