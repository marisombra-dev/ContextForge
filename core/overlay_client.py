"""
ContextForge — Overlay Client
Polls the ContextForge server for new DM responses
and pushes them to the overlay window.

Runs alongside overlay.py in a background thread.

Usage:
    Called automatically by overlay.py in production.
    For standalone testing: python overlay_client.py
"""

import time
import threading
import httpx
from typing import Optional, Callable


# ── Config ─────────────────────────────────────────────────────────────────────

CONTEXTFORGE_URL = "http://localhost:7842"
POLL_INTERVAL    = 2.0    # seconds between server checks


# ── Client ─────────────────────────────────────────────────────────────────────

class OverlayClient:
    """
    Polls /status and a dedicated /latest endpoint on the CF server
    and fires a callback whenever a new DM response arrives.
    """

    def __init__(self, on_message: Callable[[str, str], None]):
        """
        on_message: callable that receives (text, dm_name)
        Called on the polling thread — make sure your UI handler is thread-safe.
        """
        self.on_message   = on_message
        self.last_response = None
        self.running       = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _poll_loop(self):
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
                dm_name     = data.get("dm_name", "")

                # Only fire if this is a new message
                if dm_response and dm_response != self.last_response:
                    self.last_response = dm_response
                    self.on_message(dm_response, dm_name)

                if server_warned:
                    print("[Overlay] Reconnected to ContextForge.")
                    server_warned = False

            except httpx.ConnectError:
                if not server_warned:
                    print("[Overlay] ContextForge server not reachable. Waiting...")
                    server_warned = True
            except httpx.TimeoutException:
                pass
            except Exception as e:
                print(f"[Overlay] Unexpected error: {e}")

            time.sleep(POLL_INTERVAL)


# ── Integrated launcher ────────────────────────────────────────────────────────

def launch_overlay_with_client(position="bottom_right", opacity=0.88):
    """
    Launch the overlay window and start the client polling in the background.
    This is the normal production entry point.
    """
    from overlay import DMOverlay

    overlay = DMOverlay(position=position, opacity=opacity)
    client  = OverlayClient(on_message=overlay.show_message)

    client.start()

    try:
        overlay.run()
    finally:
        client.stop()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ContextForge Overlay Client")
    parser.add_argument(
        "--position",
        choices=["bottom_right", "bottom_left", "top_right", "top_left"],
        default="bottom_right",
    )
    parser.add_argument(
        "--opacity",
        type=float,
        default=0.88,
    )
    args = parser.parse_args()

    launch_overlay_with_client(position=args.position, opacity=args.opacity)
