"""
ContextForge — Voice Manager
Listens passively for player speech and coordinates TTS playback
of DM responses. Runs alongside the overlay — no hotkeys, no buttons.

He speaks when he has something to say.
You speak when you feel like it.
That's the whole design.

Usage:
    python voice_manager.py
    python voice_manager.py --tts-only   (speak responses, don't listen)
"""

import asyncio
import argparse
import threading
import httpx
from typing import Optional

from voice_router import VoiceRouter


# ── Config ─────────────────────────────────────────────────────────────────────

CONTEXTFORGE_URL   = "http://localhost:7842"
POLL_INTERVAL      = 2.0    # seconds between checking for new DM responses
LISTEN_LOOP_PAUSE  = 0.5    # brief pause between listen cycles


# ── Colour output ──────────────────────────────────────────────────────────────

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"

def log(msg, colour=RESET):
    from datetime import datetime
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{colour}[{ts}] {msg}{RESET}")


# ── TTS Watcher ────────────────────────────────────────────────────────────────

class TTSWatcher:
    """
    Polls /latest on the CF server. When a new DM response arrives,
    speaks it aloud via the voice router. Runs in its own thread.
    """

    def __init__(self, voice_router: VoiceRouter):
        self.router        = voice_router
        self.last_spoken   = None
        self.running       = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _run(self):
        server_warned = False

        while self.running:
            try:
                response = httpx.get(
                    f"{CONTEXTFORGE_URL}/latest",
                    timeout=2.0
                )
                response.raise_for_status()
                data = response.json()

                dm_response = data.get("response")

                if dm_response and dm_response != self.last_spoken:
                    self.last_spoken = dm_response
                    log(f"DM: {dm_response[:80]}{'...' if len(dm_response) > 80 else ''}", GREEN)
                    # Speak on a separate thread so polling doesn't stall
                    threading.Thread(
                        target=lambda: asyncio.run(self.router.speak(dm_response)),
                        daemon=True
                    ).start()

                if server_warned:
                    log("Reconnected to ContextForge.", GREEN)
                    server_warned = False

            except httpx.ConnectError:
                if not server_warned:
                    log("ContextForge server not reachable. Waiting...", YELLOW)
                    server_warned = True
            except Exception as e:
                log(f"TTS watcher error: {e}", RED)

            import time
            time.sleep(POLL_INTERVAL)


# ── STT Listener ───────────────────────────────────────────────────────────────

class STTListener:
    """
    Listens passively for player speech.
    When something is said, sends it to /chat on the CF server.
    The DM responds — TTSWatcher picks it up and speaks it.

    No hotkeys. No push to talk. Just... listening.
    """

    def __init__(self, voice_router: VoiceRouter):
        self.router  = voice_router
        self.running = False

    async def run(self):
        self.running = True
        log("Listening for your voice...", GREEN)

        while self.running:
            try:
                # Record until player stops talking
                text = await self.router.listen()

                if text and len(text.strip()) > 2:
                    log(f"You: {text}", YELLOW)
                    await self._send_to_chat(text)

                await asyncio.sleep(LISTEN_LOOP_PAUSE)

            except KeyboardInterrupt:
                break
            except Exception as e:
                log(f"STT error: {e}", RED)
                await asyncio.sleep(1.0)

    async def _send_to_chat(self, message: str):
        """POST player speech to /chat on the CF server."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{CONTEXTFORGE_URL}/chat",
                    json={"message": message},
                    timeout=10.0,
                )
                response.raise_for_status()

        except httpx.ConnectError:
            log("Could not reach ContextForge server.", RED)
        except Exception as e:
            log(f"Chat send error: {e}", RED)

    def stop(self):
        self.running = False


# ── Main ───────────────────────────────────────────────────────────────────────

async def run(config: dict, tts_only: bool = False):
    """
    Start the voice manager.

    tts_only=True: speak DM responses, don't listen for player speech.
    Useful if you want voice output but prefer typing.
    """

    voice_router = VoiceRouter(config)

    # Always start TTS watcher
    tts_watcher = TTSWatcher(voice_router)
    tts_watcher.start()
    log("TTS watcher started — he'll speak when he has something to say.", GREEN)

    if tts_only:
        log("STT disabled (--tts-only mode). Type in the overlay to talk to him.", YELLOW)
        try:
            while True:
                await asyncio.sleep(1.0)
        except KeyboardInterrupt:
            pass
    else:
        # Start passive listener
        stt_listener = STTListener(voice_router)
        try:
            await stt_listener.run()
        except KeyboardInterrupt:
            pass
        finally:
            stt_listener.stop()

    tts_watcher.stop()
    log("Voice manager stopped.", YELLOW)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    import pathlib

    parser = argparse.ArgumentParser(description="ContextForge Voice Manager")
    parser.add_argument(
        "--tts-only",
        action="store_true",
        help="Speak DM responses but don't listen for player voice input"
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to contextforge.config.json"
    )
    args = parser.parse_args()

    # Load config
    config_path = pathlib.Path(args.config or "contextforge.config.json")
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        # Minimal default — ElevenLabs TTS, Whisper API STT
        config = {
            "voice": {
                "tts_enabled": True,
                "stt_enabled": not args.tts_only,
                "tts_backend": "elevenlabs",
                "stt_backend": "whisper_api",
                "tts": {
                    "api_key_env":      "ELEVENLABS_API_KEY",
                    "voice_id":         "onwK4e9ZLuTAKqWW03F9",
                    "stability":        0.45,
                    "similarity_boost": 0.75,
                    "style":            0.35,
                },
                "stt": {
                    "api_key_env":       "OPENAI_API_KEY",
                    "language":          "en",
                    "silence_threshold": 0.01,
                    "silence_duration":  1.5,
                }
            }
        }

    asyncio.run(run(config, tts_only=args.tts_only))
