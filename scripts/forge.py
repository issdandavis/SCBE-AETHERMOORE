#!/usr/bin/env python3
"""Aether Speed Forge -- build a project the way a speedcuber solves a cube.

The cube is the PROJECT. Each move is a high-level ABSTRACTION (a whole feature,
not a line of code). A short sequence of moves assembles a real, runnable project
-- that's the leverage: few moves in, a lot of working code out.

This v1 forges a real list/CRUD CLI app (the tractable "cube"); the move library
is deliberately small + honest. Puzzle mode gives you a TARGET and checks whether
your move sequence actually reaches it (by running the assembled app), and scores
the solve like a cube solve: moves used, lines emitted, leverage, solved y/n.

    python scripts/forge.py solve "app tasks; add; list; done"     # forge it
    python scripts/forge.py puzzle todo-basic "app t; add; list; done"  # solve a puzzle
    python scripts/forge.py moves                                  # list the moves
    python scripts/forge.py puzzles                                # list the puzzles
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ---------------------------------------------------------------- the move library
# Each command-move contributes a handler function + one COMMANDS registry entry.
# These are real, composable CRUD abstractions over a json-backed list of items.

_MOVES: dict[str, dict] = {
    "add": {
        "desc": "append an item",
        "handler": (
            "def _cmd_add(args, items):\n"
            '    items.append({"text": args.text, "done": False})\n'
            '    print(f"added: {args.text}")'
        ),
        "register": '    "add": {"fn": _cmd_add, "help": "add an item", "args": [("text", {})]},',
    },
    "list": {
        "desc": "print all items",
        "handler": (
            "def _cmd_list(args, items):\n"
            "    if not items:\n"
            '        print("(empty)")\n'
            "    for i, x in enumerate(items):\n"
            '        mark = "x" if x["done"] else " "\n'
            "        print(f\"{i}. [{mark}] {x['text']}\")"
        ),
        "register": '    "list": {"fn": _cmd_list, "help": "list items", "args": []},',
    },
    "done": {
        "desc": "mark an item done by index",
        "handler": (
            "def _cmd_done(args, items):\n"
            '    items[args.index]["done"] = True\n'
            "    print(f\"done: {items[args.index]['text']}\")"
        ),
        "register": '    "done": {"fn": _cmd_done, "help": "mark done", "args": [("index", {"type": int})]},',
    },
    "remove": {
        "desc": "delete an item by index",
        "handler": (
            "def _cmd_remove(args, items):\n" "    x = items.pop(args.index)\n" "    print(f\"removed: {x['text']}\")"
        ),
        "register": '    "remove": {"fn": _cmd_remove, "help": "remove an item", "args": [("index", {"type": int})]},',
    },
    "count": {
        "desc": "report totals",
        "handler": (
            "def _cmd_count(args, items):\n"
            '    done = sum(1 for x in items if x["done"])\n'
            '    print(f"{len(items)} items, {done} done")'
        ),
        "register": '    "count": {"fn": _cmd_count, "help": "count items", "args": []},',
    },
    "clear": {
        "desc": "empty the list",
        "handler": (
            "def _cmd_clear(args, items):\n"
            "    n = len(items)\n"
            "    items.clear()\n"
            '    print(f"cleared {n} items")'
        ),
        "register": '    "clear": {"fn": _cmd_clear, "help": "remove everything", "args": []},',
    },
    "due": {
        "desc": "set a due date on an item by index",
        "handler": 'def _cmd_due(args, items):\n    items[args.index]["due"] = args.date\n    print(f"due {args.date}: {items[args.index][\'text\']}")',  # noqa: E501
        "register": '    "due": {"fn": _cmd_due, "help": "set a due date by index", "args": [("index", {"type": int}), ("date", {})]},',  # noqa: E501
    },
    "agenda": {
        "desc": "list items showing due dates",
        "handler": 'def _cmd_agenda(args, items):\n    if not items:\n        print("(empty)")\n    for i, x in enumerate(items):\n        mark = "x" if x["done"] else " "\n        due = x.get("due")\n        suffix = f" (due: {due})" if due else ""\n        print(f"{i}. [{mark}] {x[\'text\']}{suffix}")',  # noqa: E501
        "register": '    "agenda": {"fn": _cmd_agenda, "help": "list items with due dates", "args": []},',
    },
    "find": {
        "desc": "search items by a word and print the matching ones with their index",
        "handler": 'def _cmd_find(args, items):\n    needle = args.word.lower()\n    hits = [(i, x) for i, x in enumerate(items) if needle in x["text"].lower()]\n    if not hits:\n        print(f"no matches for: {args.word}")\n        return\n    for i, x in hits:\n        mark = "x" if x["done"] else " "\n        print(f"{i}. [{mark}] {x[\'text\']}")',  # noqa: E501
        "register": '    "find": {"fn": _cmd_find, "help": "find items by word", "args": [("word", {})]},',
    },
    "edit": {
        "desc": "change an item's text by index",
        "handler": 'def _cmd_edit(args, items):\n    old = items[args.index]["text"]\n    items[args.index]["text"] = args.text\n    print(f"edited {args.index}: {old!r} -> {args.text!r}")',  # noqa: E501
        "register": '    "edit": {"fn": _cmd_edit, "help": "edit item text by index", "args": [("index", {"type": int}), ("text", {})]},',  # noqa: E501
    },
    "priority": {
        "desc": "set priority (high/medium/low) on an item by index",
        "handler": 'def _cmd_priority(args, items):\n    level = args.level.lower()\n    valid = ("high", "medium", "low")\n    if level not in valid:\n        print(f"invalid priority: {args.level} (use high/medium/low)")\n        return\n    items[args.index]["priority"] = level\n    print(f"priority: {items[args.index][\'text\']} -> {level}")',  # noqa: E501
        "register": '    "priority": {"fn": _cmd_priority, "help": "set priority high/medium/low on an item", "args": [("index", {"type": int}), ("level", {})]},',  # noqa: E501
    },
    "sort": {
        "desc": "reorder items by priority (high first)",
        "handler": 'def _cmd_sort(args, items):\n    rank = {"high": 0, "medium": 1, "low": 2, "none": 3}\n    items.sort(key=lambda x: rank.get(x.get("priority", "none"), 3))\n    print(f"sorted {len(items)} items by priority")',  # noqa: E501
        "register": '    "sort": {"fn": _cmd_sort, "help": "sort items by priority", "args": []},',
    },
    "tag": {
        "desc": "tag an item by index",
        "handler": 'def _cmd_tag(args, items):\n    item = items[args.index]\n    item.setdefault("tags", []).append(args.label)\n    print(f"tagged {args.index} with {args.label}: {item[\'tags\']}")',  # noqa: E501
        "register": '    "tag": {"fn": _cmd_tag, "help": "tag an item", "args": [("index", {"type": int}), ("label", {})]},',  # noqa: E501
    },
    "export": {
        "desc": "write items to items.md as a checklist",
        "handler": 'def _cmd_export(args, items):\n    from pathlib import Path\n    out = Path("items.md")\n    lines = ["# Items", ""]\n    for x in items:\n        mark = "x" if x["done"] else " "\n        lines.append(f"- [{mark}] {x[\'text\']}")\n    if not items:\n        lines.append("_(no items)_")\n    out.write_text("\\n".join(lines) + "\\n", encoding="utf-8")\n    print(f"exported {len(items)} items -> {out}")',  # noqa: E501
        "register": '    "export": {"fn": _cmd_export, "help": "write items to items.md checklist", "args": []},',
    },
}
_APP_TEMPLATE = '''#!/usr/bin/env python3
"""{name} -- forged by Aether Speed Forge from {nmoves} moves: {movestr}"""
import argparse
import json
from pathlib import Path

STORE = Path(__file__).with_suffix(".json")


def _load():
    return json.loads(STORE.read_text(encoding="utf-8")) if STORE.exists() else []


def _save(items):
    STORE.write_text(json.dumps(items, indent=2), encoding="utf-8")


{handlers}


COMMANDS = {{
{registrations}
}}


def main(argv=None):
    p = argparse.ArgumentParser(prog="{name}")
    sub = p.add_subparsers(dest="cmd", required=True)
    for cname, spec in COMMANDS.items():
        sp = sub.add_parser(cname, help=spec["help"])
        for aname, akw in spec["args"]:
            sp.add_argument(aname, **akw)
    args = p.parse_args(argv)
    items = _load()
    try:
        COMMANDS[args.cmd]["fn"](args, items)
    except IndexError:
        idx = getattr(args, "index", "?")
        print(f"no item at index {{idx}} (have {{len(items)}})")
        raise SystemExit(2)
    _save(items)


if __name__ == "__main__":
    main()
'''

# ---------------------------------------------------------------- puzzles (targets)
# A puzzle = a target the forged app must satisfy, checked by RUNNING the app.
# steps: a list of (argv, expected_substring_in_output_or_None)

_PUZZLES = {
    "todo-basic": {
        "goal": "A task CLI you can add to, list, and mark done.",
        "steps": [
            (["add", "buy milk"], "added"),
            (["list"], "buy milk"),
            (["done", "0"], "done"),
            (["list"], "[x]"),
        ],
    },
    "inventory": {
        "goal": "Track items, count them, and clear the list.",
        "steps": [
            (["add", "widget"], "added"),
            (["add", "gadget"], "added"),
            (["count"], "2 items"),
            (["clear"], "cleared 2"),
            (["count"], "0 items"),
        ],
    },
    "planner": {
        "goal": "Plan tasks with due dates, priorities, and search.",
        "steps": [
            (["add", "buy milk"], "added"),
            (["due", "0", "friday"], "due friday"),
            (["agenda"], "friday"),
            (["priority", "0", "high"], "priority"),
            (["find", "milk"], "buy milk"),
        ],
    },
}


# --- lossless prime signature + glyph: "no number lost; too long -> a shape" --------
_PRIMES_POS = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]
_MOVE_ID = {name: i + 1 for i, name in enumerate(_MOVES)}  # stable id per move


def prime_signature(used: list[str]) -> int:
    """Ordered move list -> ONE number (Godel/prime code). Reversible; loses nothing."""
    sig = 1
    for i, m in enumerate(used):
        sig *= _PRIMES_POS[i] ** _MOVE_ID.get(m, 0)
    return sig


def decode_signature(sig: int) -> list[str]:
    """Factor the number back to the EXACT ordered move list."""
    inv = {v: k for k, v in _MOVE_ID.items()}
    out = []
    for p in _PRIMES_POS:
        if sig % p != 0:
            break
        e = 0
        while sig % p == 0:
            sig //= p
            e += 1
        out.append(inv.get(e, "?"))
    return out


def render_glyph(sig: int, width: int = 16) -> list[str]:
    """Fold the (possibly huge) number into a 2D shape: its bits on a grid -- a glyph."""
    nbytes = max(1, (sig.bit_length() + 7) // 8)
    bits = bin(int.from_bytes(sig.to_bytes(nbytes, "big"), "big"))[2:].zfill(nbytes * 8)
    rows = [bits[i : i + width] for i in range(0, len(bits), width)]
    return ["".join("#" if b == "1" else "." for b in r) for r in rows]


def show_signature(used: list[str]):
    sig = prime_signature(used)
    ok = decode_signature(sig) == used
    print(f"\n  prime signature (one number, reversible): {sig}")
    print(f"   factors back to: {decode_signature(sig)}   NO MOVE LOST: {ok}")
    print("   too long to read in a line -> it becomes a SHAPE:")
    for row in render_glyph(sig):
        print("     " + row)


def parse_moves(text: str) -> list[str]:
    raw = [m.strip() for chunk in text.split(";") for m in chunk.split("\n")]
    return [m for m in raw if m]


def assemble(moves: list[str]):
    """Apply a move sequence -> (app_name, source_code, warnings)."""
    name = "app"
    warnings = []
    handlers, registrations, used = [], [], []
    for mv in moves:
        parts = mv.split()
        op = parts[0]
        if op == "app":
            name = parts[1] if len(parts) > 1 else "app"
            continue
        if op not in _MOVES:
            warnings.append(f"unknown move: {op}")
            continue
        if op in used:
            warnings.append(f"duplicate move ignored: {op}")
            continue
        used.append(op)
        handlers.append(_MOVES[op]["handler"])
        registrations.append(_MOVES[op]["register"])
    src = _APP_TEMPLATE.format(
        name=name,
        nmoves=len(used),
        movestr=", ".join(used) or "(none)",
        handlers="\n\n\n".join(handlers) if handlers else "# (no commands)",
        registrations="\n".join(registrations),
    )
    return name, src, warnings, used


def run_app(src: str, argv: list[str]):
    with tempfile.TemporaryDirectory() as d:
        app = Path(d) / "app.py"
        app.write_text(src, encoding="utf-8")
        # replay each step in the same dir so the json store persists across steps
        return app, d


def _exec(app: Path, argv: list[str]):
    r = subprocess.run(
        [sys.executable, str(app), *argv],
        capture_output=True,
        cwd=app.parent,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    )
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def solve(move_text: str, puzzle: str | None = None):
    moves = parse_moves(move_text)
    t0 = time.perf_counter()
    name, src, warnings, used = assemble(moves)
    lines = src.count("\n") + 1

    print(f"\n  forged '{name}' from {len(used)} moves: {', '.join(used)}")
    for w in warnings:
        print(f"   ! {w}")
    print(f"   -> {lines} lines of real, runnable code")

    # always self-check: the app at least parses + runs --help
    with tempfile.TemporaryDirectory() as d:
        app = Path(d) / f"{name}.py"
        app.write_text(src, encoding="utf-8")
        rc, out = _exec(app, ["--help"])
        runs = rc == 0
        print(f"   -> assembles + runs: {'YES' if runs else 'NO'}")

        solved = None
        if puzzle:
            spec = _PUZZLES.get(puzzle)
            if not spec:
                print(f"   ! unknown puzzle: {puzzle}")
            else:
                print(f"\n  PUZZLE [{puzzle}]: {spec['goal']}")
                ok = True
                for argv, expect in spec["steps"]:
                    rc, out = _exec(app, argv)
                    hit = (expect is None) or (expect in out)
                    ok = ok and rc == 0 and hit
                    flag = "OK" if (rc == 0 and hit) else "XX"
                    print(f"   [{flag}] {name} {' '.join(argv):<20} -> {out.strip()[:46]}")
                solved = ok

    dt = (time.perf_counter() - t0) * 1000
    leverage = round(lines / max(1, len(used)), 1)
    show_signature(used)
    print("\n  " + "=" * 56)
    print(f"  moves: {len(used)}   lines: {lines}   leverage: {leverage} lines/move   {dt:.0f}ms")
    if solved is not None:
        print(f"  SOLVED: {'YES -- target reached' if solved else 'NO -- not all checks passed'}")
    print("  " + "=" * 56)
    return solved


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd = args[0]
    if cmd == "moves":
        print("  moves (each is one abstraction):")
        print("    app <name>   start a project")
        for k, v in _MOVES.items():
            print(f"    {k:<10}  {v['desc']}")
        return
    if cmd == "puzzles":
        print("  puzzles (targets to reach):")
        for k, v in _PUZZLES.items():
            print(f"    {k:<14}  {v['goal']}")
        return
    if cmd == "solve":
        solve(args[1] if len(args) > 1 else "")
        return
    if cmd == "puzzle":
        if len(args) < 3:
            print('usage: forge.py puzzle <puzzle-name> "<moves>"')
            return
        solve(args[2], puzzle=args[1])
        return
    print(f"unknown command: {cmd}  (try: moves | puzzles | solve | puzzle)")


if __name__ == "__main__":
    main()
