"""
ContextForge — Startup Launcher
Starts the full ContextForge stack with one command.
No more four terminals.

Usage:
    python start.py
    python start.py --no-voice
    python start.py --no-overlay
    python start.py --tts-only
    python start.py --config path/to/contextforge.config.json
"""

import subprocess
import argparse
import sys
import time
import signal
import os
from pathlib import Path


# ── Colour output ──────────────────────────────────────────────────────────────

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def log(msg, colour=RESET):
    print(f"{colour}{msg}{RESET}")


# ── Process manager ────────────────────────────────────────────────────────────

processes = []

def launch(name: str, cmd: list, delay: float = 0.0) -> subprocess.Popen:
    if delay:
        time.sleep(delay)
    log(f"  Starting {name}...", GREEN)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    processes.append((name, proc))
    return proc


def shutdown(signum=None, frame=None):
    log("\nShutting down ContextForge...", YELLOW)
    for name, proc in reversed(processes):
        if proc.poll() is None:
            log(f"  Stopping {name}...", YELLOW)
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
    log("Good game. 👋", GREEN)
    sys.exit(0)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ContextForge Launcher")
    parser.add_argument("--no-voice",   action="store_true", help="Disable voice manager")
    parser.add_argument("--no-overlay", action="store_true", help="Disable overlay")
    parser.add_argument("--tts-only",   action="store_true", help="Voice output only, no microphone")
    parser.add_argument("--config",     default=None,        help="Path to config file")
    args = parser.parse_args()

    python = sys.executable
    config_args = ["--config", args.config] if args.config else []

    print(f"\n{BOLD}{'─' * 55}{RESET}")
    print(f"{BOLD}  ContextForge{RESET}")
    print(f"{'─' * 55}\n")

    # Register clean shutdown
    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # 1. Core server — always first
    launch("Core server", [python, "core/server.py"] + config_args)
    time.sleep(2.0)  # give server time to bind port

    # 2. Overlay
    if not args.no_overlay:
        launch("Overlay", [python, "core/overlay_client.py"])
        time.sleep(0.5)

    # 3. Voice manager
    if not args.no_voice:
        voice_cmd = [python, "core/voice_manager.py"]
        if args.tts_only:
            voice_cmd.append("--tts-only")
        if args.config:
            voice_cmd += ["--config", args.config]
        launch("Voice manager", voice_cmd)
        time.sleep(0.5)

    print(f"\n{GREEN}  ContextForge is running.{RESET}")
    print(f"  Start your game, then run the plugin:")
    print(f"  {YELLOW}python plugins/skyrim/skyrim_heartbeat_loop.py{RESET}")
    print(f"\n  Press Ctrl+C to stop everything.\n")

    # Watch for any process dying unexpectedly
    while True:
        for name, proc in processes:
            if proc.poll() is not None:
                log(f"\n{name} stopped unexpectedly (exit {proc.returncode}).", RED)
                shutdown()
        time.sleep(2.0)


if __name__ == "__main__":
    main()
