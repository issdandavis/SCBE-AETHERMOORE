#!/usr/bin/env python3
"""Aether Forge -- conversational intent. Meet the user where they are; build when ready.

Talks with ANY user -- a kid, someone drunk, someone who has never coded -- pulls
the real intent out of messy/slangy words, fills a SPEC SHEET turn by turn, asks
plain questions for what's missing, and the moment the spec is buildable it
assembles a real project and VERIFIES it by running. Honest about gaps.

    python scripts/forge_chat.py                          # talk to it
    python scripts/forge_chat.py --say "i wanna keep track of shit i gotta do" \
                                 --say "yeah lemme cross em off" --say "thats it build it"
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import _MOVES  # noqa: E402
from forge_speak import _GAPS, solve, synth_spec  # noqa: E402

# slang / kid / drunk-tolerant: many ways to say each capability
_SLANG = {
    "add": [
        "add",
        "new",
        "put",
        "keep",
        "track",
        "jot",
        "write",
        "note",
        "log",
        "record",
        "stuff",
        "thing",
        "things",
        "shit",
        "gotta",
        "need to",
        "wanna",
        "todo",
        "to do",
        "to-do",
        "list of",
        "gimme",
        "remember",
    ],
    "list": [
        "list",
        "show",
        "see",
        "view",
        "look",
        "read",
        "display",
        "what",
        "whats",
        "check",
        "pull up",
        "my list",
        "everything",
    ],
    "done": [
        "done",
        "finish",
        "complete",
        "mark",
        "check off",
        "cross off",
        "cross em",
        "tick",
        "did it",
        "handled",
        "crossed",
        "knock out",
    ],
    "count": ["count", "how many", "total", "number", "tally", "amount"],
    "remove": ["remove", "delete", "drop", "get rid", "trash", "yeet", "toss", "take off", "kill"],
    "clear": ["clear", "wipe", "reset", "empty", "start over", "fresh", "nuke", "scrap", "blow"],
}
_BUILD = [
    "build",
    "build it",
    "make it",
    "do it",
    "go ahead",
    "thats it",
    "that's it",
    "send it",
    "yes do it",
    "yeah do it",
    "just build",
    "ship it",
    "make the thing",
    "that works",
    "sounds good",
    "go for it",
]
_LISTY = ["track", "keep", "list of", "todo", "to do", "to-do", "checklist", "keep a", "remember"]


def extract(text: str) -> set[str]:
    low = " " + text.lower() + " "
    caps = {cap for cap, words in _SLANG.items() if any(w in low for w in words)}
    if any(w in low for w in _LISTY):  # "keep a list / track stuff" implies add + see
        caps |= {"add", "list"}
    return {c for c in caps if c in _MOVES}


def wants_build(text: str) -> bool:
    low = text.lower()
    # whole-word / phrase match so short triggers like "go" don't fire inside "gotta"
    return any(re.search(r"\b" + re.escape(b) + r"\b", low) for b in _BUILD)


def next_question(ops: set[str]) -> str:
    if "add" in ops and "list" not in ops:
        return "want to be able to SEE the list too?"
    if {"add", "list"} <= ops and "done" not in ops:
        return "want to cross things off when you finish 'em?"
    if "done" in ops and "count" not in ops:
        return "should it tell you how many you've got left? (or say 'build it')"
    return "anything else it should do -- or should I just build it?"


def reply(ops: set[str]) -> str:
    if not ops:
        return (
            "ok, simplest words: what do you want it to let you DO?\n"
            "  (like 'add stuff and see it', or 'keep a list and check things off')"
        )
    nice = ", ".join(ops)
    return f"got it -- so far: {nice}.\n  {next_question(ops)}"


def build(ops: set[str], gaps: set[str]):
    caps = [c for c in ("add", "list", "done", "count", "remove", "clear") if c in ops]
    spec = synth_spec(caps, "your idea")
    plan, used, src, ok, results = solve(spec)
    lines = src.count("\n") + 1
    print(f"\n  >> building it from your words: {', '.join(caps)}")
    print(f"     {len(plan)} block(s): {', '.join(plan)}  ({len(used)} moves, {lines} lines, on the Turing base)")
    for argv, good, out in results:
        print(f"   [{'OK' if good else 'XX'}] {' '.join(argv):<16} -> {out}")
    print(f"  BUILT + VERIFIED: {'YES -- it runs and does what you said' if ok else 'NO'}")
    if gaps:
        g = sorted(gaps)
        print(f"  honest gaps (no move yet): {', '.join(g)} -- say \"add a {g[0].split(' / ')[0]} move\" and I will.")


class Conversation:
    def __init__(self):
        self.ops: set[str] = set()
        self.gaps: set[str] = set()
        self.asked = 0

    def turn(self, text: str) -> bool:
        """Process one user line. Returns True when it has built (conversation can end)."""
        self.ops |= extract(text)
        self.gaps |= {label for kw, label in _GAPS.items() if kw in text.lower()}
        ready = wants_build(text) and self.ops
        # if they keep talking and we already have a coherent thing, offer/auto-build politely
        if not ready and {"add", "list"} <= self.ops and self.asked >= 2:
            ready = True
        if ready:
            build(self.ops, self.gaps)
            return True
        print(f"\n  AETHER: {reply(self.ops)}")
        self.asked += 1
        return False


def chat_loop():
    """Interactive conversational build loop. Shared by this script and `scbe forge --chat`."""
    convo = Conversation()
    print("  AETHER: tell me what you want to make. plain words. (ctrl+c to quit)")
    try:
        while True:
            line = input("\n  YOU: ").strip()
            if not line:
                continue
            if convo.turn(line):
                again = input("\n  build something else? (y/N): ").strip().lower()
                if again not in ("y", "yes"):
                    break
                convo.__init__()
    except (KeyboardInterrupt, EOFError):
        print("\n  later.")


def main():
    says = [a for i, a in enumerate(sys.argv) if sys.argv[i - 1] == "--say"]
    if says:  # scripted (for tests / demos)
        convo = Conversation()
        for line in says:
            print(f"\n  YOU: {line}")
            if convo.turn(line):
                break
        else:
            print("\n  (still gathering -- add another --say, or it builds once it's buildable)")
        return
    chat_loop()


if __name__ == "__main__":
    main()
