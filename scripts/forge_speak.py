#!/usr/bin/env python3
"""Aether Forge -- the plain-English front. Speak your intention; it builds + verifies.

You don't pick moves or write code. You say what you want in words. This maps your
intention to capabilities the controller knows, assembles a real project, RUNS it
to prove it works, and is HONEST about anything it can't build yet (instead of
faking it). No model backend required -- a deterministic intent parser, so every
"BUILT + VERIFIED: YES" is actually executed.

    python scripts/forge_speak.py "I want a task tracker I can mark done and count"
    python scripts/forge_speak.py "let me add things, see them, and clear the list"
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import _MOVES, _exec, assemble  # noqa: E402
from forge_ai import _BLOCKS, expand, provides  # noqa: E402

# plain-English -> a capability the move library actually provides
_INTENT = {
    "add": ["add", "create", "new", "insert", "put", "jot", "capture", "note down"],
    "list": ["list", "show", "see", "view", "display", "read", "look at", "what's on"],
    "done": ["done", "complete", "finish", "mark", "check off", "tick", "close out"],
    "count": ["count", "total", "how many", "number of", "tally"],
    "clear": ["clear", "reset", "empty", "wipe", "delete all", "start over"],
    "remove": ["remove", "delete", "drop", "take off", "get rid"],
}
_TRACKER_WORDS = ("task", "todo", "to-do", "to do", "tracker", "checklist", "list of")
# things we honestly do NOT have a move for yet (so we say so instead of faking)
_GAPS = {
    "due date": "due-dates / deadlines", "deadline": "due-dates / deadlines",
    "priority": "priority levels", "tag": "tags / labels", "label": "tags / labels",
    "sort": "sorting", "search": "search / filter", "filter": "search / filter",
    "remind": "reminders", "category": "categories", "edit": "editing an item",
}


def parse_intent(text: str):
    low = text.lower()
    caps = [cap for cap, words in _INTENT.items() if any(w in low for w in words)]
    if any(w in low for w in _TRACKER_WORDS):
        for c in ("add", "list", "done"):
            if c not in caps:
                caps.append(c)
    gaps = sorted({label for kw, label in _GAPS.items() if kw in low})
    return caps, gaps


def synth_spec(caps: list[str], text: str):
    """Turn the understood capabilities into a runnable verification sequence."""
    steps = []
    if "add" in caps:
        steps.append((["add", "milk"], "added"))
    if "list" in caps:
        steps.append((["list"], "milk" if "add" in caps else None))
    if "done" in caps:
        steps.append((["done", "0"], "done"))
        if "list" in caps:
            steps.append((["list"], "[x]"))
    if "count" in caps:
        steps.append((["count"], "item"))
    if "remove" in caps:
        steps.append((["remove", "0"], "removed"))
    if "clear" in caps:
        steps.append((["clear"], "cleared"))
    if not steps and caps:
        steps.append(([caps[0]], None))
    return {"goal": text.strip(), "steps": steps}


def solve(spec):
    needed = {s[0][0] for s in spec["steps"]}
    candidates = list(_BLOCKS) + list(_MOVES)
    plan, remaining = [], set(needed)
    while remaining:
        best = max(candidates, key=lambda c: len(provides(c) & remaining))
        if not (provides(best) & remaining):
            break
        plan.append(best)
        remaining -= provides(best)
    name, src, _w, used = assemble(["app forged"] + expand(plan))
    ok, results = True, []
    with tempfile.TemporaryDirectory() as d:
        app = Path(d) / f"{name}.py"
        app.write_text(src, encoding="utf-8")
        for argv, expect in spec["steps"]:
            rc, out = _exec(app, argv)
            good = rc == 0 and (expect is None or expect in out)
            ok = ok and good
            results.append((argv, good, out.strip()[:40]))
    return plan, used, src, ok, results


def speak(text: str):
    print(f'\n  YOU SAID: "{text}"')
    caps, gaps = parse_intent(text)
    if not caps:
        print("  I couldn't turn that into something I can build yet.")
        print("  Try words like: add, see/list, mark done, count, remove, clear -- or 'a task tracker'.")
        return False
    print(f"  I UNDERSTOOD you want to: {', '.join(caps)}")
    plan, used, src, ok, results = solve(synth_spec(caps, text))
    lines = src.count("\n") + 1
    print(f"  -> built it from {len(plan)} building block(s): {', '.join(plan)}  "
          f"({len(used)} moves, {lines} lines, on the binary Turing base)")
    print()
    for argv, good, out in results:
        print(f"   [{'OK' if good else 'XX'}] forged {' '.join(argv):<16} -> {out}")
    print(f"\n  BUILT + VERIFIED: {'YES -- it runs and does what you asked' if ok else 'NO'}")
    if gaps:
        print(f"  HONEST GAPS (no move for these yet): {', '.join(gaps)}")
        print(f'   -> I built everything else and proved it. Say "add a {gaps[0].split(" / ")[0]} move" and I will.')
    return ok


def main():
    text = " ".join(sys.argv[1:]).strip() or "I want a task tracker I can mark done and count"
    speak(text)


if __name__ == "__main__":
    main()
