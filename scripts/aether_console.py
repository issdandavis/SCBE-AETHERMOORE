#!/usr/bin/env python3
"""Aether Console -- interacting with SCBE as a Choice-of-Games-style game.

The whole point: you never face a blank prompt. The top is the scene / AI field;
the bottom is where you type -- a NUMBER to take a choice you can see, or plain
English to talk to the AI. Scenes branch, nest, and loop back to a hub, the way an
interactive-fiction game does.

Run it:
    python scripts/aether_console.py
    python scripts/aether_console.py --demo     # non-interactive render (for tests)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CATALOG = Path(__file__).resolve().parent / "powershell" / "AetherMenu.catalog.json"

_C = {
    "cyan": "\033[36m",
    "dim": "\033[2m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "bold": "\033[1m",
    "mag": "\033[35m",
    "reset": "\033[0m",
}


def c(s: str, name: str) -> str:
    return f"{_C.get(name, '')}{s}{_C['reset']}"


# A line of flavor per scene so it reads like a game, not a control panel.
NARRATION = {
    "__hub__": "You stand at the heart of the system. Doors hum around you -- pick one, or just speak.",
    "GitHub": "The forge. Where your work becomes real and ships to the world.",
    "Tokens & Cube": "The lexicon. Turn plain words into the six sacred tongues.",
    "Chemistry": "The crucible. Words become atoms, bonds, and orbitals.",
    "Safety & Governance": "The gate. Decide what is allowed to pass.",
    "Code & AI": "The familiar. Ask, and it answers; command, and it acts.",
    "Notes & Vault": "The archive. Everything you have ever written, within reach.",
    "System & Health": "The engine room. Check the pulse of the machine.",
    "See & Feel (Synesthesia)": "The prism. See, hear, and feel any thought.",
}


def _enable_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))["categories"]


def _git(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, cwd=str(REPO), timeout=5).stdout.strip()
    except Exception:
        return ""


def status_line():
    branch = _git(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or "-"
    repo = _git(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]) or REPO.name
    return repo, branch


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def header(title: str, narration: str = ""):
    repo, branch = status_line()
    w = min(shutil.get_terminal_size((74, 24)).columns, 74)
    print(c("=" * w, "cyan"))
    print(c(f"  >> {title}", "bold"))
    print(c(f"     repo {repo}  -  branch {branch}", "dim"))
    print(c("=" * w, "cyan"))
    if narration:
        print()
        print(c(f"  {narration}", "mag"))


def run_command(cmd: str):
    print(c(f"\n  > {cmd}\n", "green"))
    env = dict(os.environ, PYTHONPATH=".")
    try:
        subprocess.run(cmd, shell=True, cwd=str(REPO), env=env)
    except Exception as e:  # pragma: no cover
        print(c(f"  (error: {e})", "red"))


def ask_ai(q: str):
    run_command(f'python scbe.py ask "{q}"')


def take_choice(action: dict):
    cmd = action["command"]
    if action.get("needs_input"):
        prompt = action.get("input_prompt") or "Value"
        val = input(c(f"  {prompt}\n  < ", "yellow"))
        cmd = cmd.replace("{input}", val)
    if action.get("run_mode") == "confirm":
        print(c(f"\n  This will run:  {cmd}", "yellow"))
        if input(c("  Do it? [y/N] < ", "yellow")).strip().lower() not in ("y", "yes"):
            print(c("  (skipped)", "dim"))
            return
    run_command(cmd)


def play_scene(cat: dict):
    while True:
        clear()
        header(f"{cat.get('icon', '')} {cat['category']}", NARRATION.get(cat["category"], ""))
        print()
        actions = cat["actions"]
        for i, a in enumerate(actions, 1):
            print(c(f"   {i:>2})  ", "cyan") + a["label"])
            if a.get("desc"):
                print(c(f"        {a['desc']}", "dim"))
        print(c("\n    b) back to the hub      q) quit", "dim"))
        print(c("\n  Type a number -- or just talk to the AI:", "dim"))
        sel = input(c("  < ", "mag")).strip()
        low = sel.lower()
        if low in ("q", "quit"):
            sys.exit(0)
        if low in ("b", "back", ""):
            return
        if sel.isdigit() and 1 <= int(sel) <= len(actions):
            take_choice(actions[int(sel) - 1])
            input(c("\n  (press Enter to continue)", "dim"))
        else:
            ask_ai(sel)
            input(c("\n  (press Enter to continue)", "dim"))


def play_hub(cats: list):
    while True:
        clear()
        header("AETHER CONSOLE  -  what do you want to do?", NARRATION["__hub__"])
        print()
        for i, cat in enumerate(cats, 1):
            print(c(f"   {i:>2})  ", "cyan") + f"{cat.get('icon', '')}  {cat['category']}")
        print(c("\n    a) ask the AI anything       q) quit", "green"))
        print(c("\n  Pick a number -- or type anything to ask the AI:", "dim"))
        sel = input(c("  < ", "mag")).strip()
        low = sel.lower()
        if low in ("q", "quit"):
            break
        if low in ("a", "ask"):
            q = input(c("  ask < ", "yellow"))
            if q:
                ask_ai(q)
                input(c("\n  (press Enter)", "dim"))
            continue
        if sel.isdigit() and 1 <= int(sel) <= len(cats):
            play_scene(cats[int(sel) - 1])
        elif sel:
            ask_ai(sel)
            input(c("\n  (press Enter)", "dim"))
    print(c("\n  the doors go quiet. bye.\n", "dim"))


def demo():
    """Non-interactive render of the hub + first scene, for verification."""
    _enable_utf8()
    cats = load_catalog()
    header("AETHER CONSOLE  -  what do you want to do?", NARRATION["__hub__"])
    print()
    for i, cat in enumerate(cats, 1):
        print(f"   {i:>2})  {cat.get('icon', '')}  {cat['category']}")
    print("\n--- scene render:", cats[0]["category"], "---")
    for i, a in enumerate(cats[0]["actions"], 1):
        tag = " [needs input]" if a.get("needs_input") else ""
        tag += " [confirm]" if a.get("run_mode") == "confirm" else ""
        print(f"   {i:>2})  {a['label']}{tag}")
    print(f"\nOK: {len(cats)} scenes, {sum(len(x['actions']) for x in cats)} choices loaded.")


def main():
    if "--demo" in sys.argv:
        demo()
        return
    _enable_utf8()
    if os.name == "nt":
        os.system("")  # enable ANSI/VT on Windows 10+
    try:
        cats = load_catalog()
    except Exception as e:
        print(f"Aether catalog not found ({CATALOG}): {e}")
        return
    play_hub(cats)


if __name__ == "__main__":
    main()
