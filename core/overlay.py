"""
ContextForge — DM Overlay
A lightweight, always-on-top transparent window that displays
the DM's responses while you play.

Sits in the corner. Fades out. Stays out of your way.
Shows up when he has something to say.

Usage:
    python overlay.py
    python overlay.py --position bottom_right --opacity 0.85
"""

import tkinter as tk
import argparse
import threading
import queue
import time


# ── Config ─────────────────────────────────────────────────────────────────────

DEFAULT_POSITION    = "bottom_right"
DEFAULT_OPACITY     = 0.88
DEFAULT_FADE_AFTER  = 8       # seconds before message fades out
FADE_DURATION       = 1.5     # seconds the fade animation takes
WINDOW_WIDTH        = 420
WINDOW_HEIGHT       = 120
PADDING             = 20      # pixels from screen edge
POLL_INTERVAL_MS    = 200     # how often the UI checks the message queue


# ── Colours & fonts ────────────────────────────────────────────────────────────

BG_COLOUR   = "#0d0d0d"
TEXT_COLOUR = "#e8d5b0"       # warm parchment — readable, not harsh
NAME_COLOUR = "#8a6f4e"       # muted gold for the DM's name
FONT_NAME   = ("Georgia", 11)
FONT_TEXT   = ("Georgia", 11)


# ── Overlay Window ─────────────────────────────────────────────────────────────

class DMOverlay:
    def __init__(self, position=DEFAULT_POSITION, opacity=DEFAULT_OPACITY, fade_after=DEFAULT_FADE_AFTER):
        self.position   = position
        self.opacity    = opacity
        self.fade_after = fade_after

        self.message_queue = queue.Queue()
        self.fade_job      = None
        self.current_alpha = opacity

        self._build_window()
        self._position_window()

    def _build_window(self):
        self.root = tk.Tk()
        self.root.title("ContextForge")
        self.root.overrideredirect(True)          # no title bar
        self.root.attributes("-topmost", True)    # always on top
        self.root.attributes("-alpha", 0.0)       # start invisible
        self.root.configure(bg=BG_COLOUR)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        # Subtle rounded feel via inner frame
        self.frame = tk.Frame(
            self.root,
            bg=BG_COLOUR,
            padx=14,
            pady=10,
        )
        self.frame.pack(fill=tk.BOTH, expand=True)

        # DM name label
        self.name_label = tk.Label(
            self.frame,
            text="",
            font=("Georgia", 9, "italic"),
            fg=NAME_COLOUR,
            bg=BG_COLOUR,
            anchor="w",
        )
        self.name_label.pack(fill=tk.X)

        # Message text
        self.text_label = tk.Label(
            self.frame,
            text="",
            font=FONT_TEXT,
            fg=TEXT_COLOUR,
            bg=BG_COLOUR,
            wraplength=WINDOW_WIDTH - 30,
            justify=tk.LEFT,
            anchor="w",
        )
        self.text_label.pack(fill=tk.BOTH, expand=True)

        # Click anywhere on overlay to dismiss early
        self.root.bind("<Button-1>", lambda e: self._fade_out())

    def _position_window(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w  = WINDOW_WIDTH
        h  = WINDOW_HEIGHT

        positions = {
            "bottom_right": (sw - w - PADDING, sh - h - PADDING - 48),
            "bottom_left":  (PADDING, sh - h - PADDING - 48),
            "top_right":    (sw - w - PADDING, PADDING),
            "top_left":     (PADDING, PADDING),
        }

        x, y = positions.get(self.position, positions["bottom_right"])
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def show_message(self, text: str, dm_name: str = ""):
        """Push a message into the queue — thread-safe."""
        self.message_queue.put((text, dm_name))

    def _display_message(self, text: str, dm_name: str):
        """Actually update the UI — must run on main thread."""
        # Cancel any pending fade
        if self.fade_job:
            self.root.after_cancel(self.fade_job)
            self.fade_job = None

        # Update text
        self.name_label.config(text=dm_name if dm_name else "")
        self.text_label.config(text=text)

        # Snap to full opacity
        self.current_alpha = self.opacity
        self.root.attributes("-alpha", self.current_alpha)

        # Schedule fade after display duration
        self.fade_job = self.root.after(
            int(self.fade_after * 1000),
            self._fade_out
        )

    def _fade_out(self):
        """Animate fade to invisible."""
        steps      = 20
        step_time  = int((FADE_DURATION * 1000) / steps)
        step_alpha = self.current_alpha / steps

        def _step(remaining):
            nonlocal step_alpha
            if remaining <= 0:
                self.root.attributes("-alpha", 0.0)
                return
            new_alpha = max(0.0, self.root.attributes("-alpha") - step_alpha)
            self.root.attributes("-alpha", new_alpha)
            self.root.after(step_time, lambda: _step(remaining - 1))

        _step(steps)

    def _poll_queue(self):
        """Check message queue and update UI. Runs on main thread via after()."""
        try:
            while not self.message_queue.empty():
                text, dm_name = self.message_queue.get_nowait()
                self._display_message(text, dm_name)
        except queue.Empty:
            pass
        self.root.after(POLL_INTERVAL_MS, self._poll_queue)

    def run(self):
        """Start the overlay. Blocks until window is closed."""
        self.root.after(POLL_INTERVAL_MS, self._poll_queue)
        self.root.mainloop()

    def destroy(self):
        self.root.quit()


# ── Standalone test ────────────────────────────────────────────────────────────

def _test_overlay(position, opacity):
    """
    Show a few test messages so you can see the overlay
    without needing the full ContextForge stack running.
    """
    overlay = DMOverlay(position=position, opacity=opacity)

    test_messages = [
        ("You're back. I was beginning to think you'd gotten lost between saves.", "Marcus"),
        ("That's a bold choice. Wrong, but bold.", "Marcus"),
        ("You walked into that trap on purpose. I refuse to believe otherwise.", "Marcus"),
    ]

    def push_messages():
        time.sleep(1.0)
        for text, name in test_messages:
            overlay.show_message(text, name)
            time.sleep(4.0)

    t = threading.Thread(target=push_messages, daemon=True)
    t.start()
    overlay.run()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ContextForge DM Overlay")
    parser.add_argument(
        "--position",
        choices=["bottom_right", "bottom_left", "top_right", "top_left"],
        default=DEFAULT_POSITION,
    )
    parser.add_argument(
        "--opacity",
        type=float,
        default=DEFAULT_OPACITY,
        help="Overlay opacity 0.0-1.0"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Show test messages without needing ContextForge running"
    )
    args = parser.parse_args()

    if args.test:
        _test_overlay(args.position, args.opacity)
    else:
        # Normal mode — overlay waits for overlay_client.py to feed it messages
        overlay = DMOverlay(position=args.position, opacity=args.opacity)
        overlay.run()
