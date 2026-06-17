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

import json
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
            'def _cmd_add(args, items):\n'
            '    items.append({"text": args.text, "done": False})\n'
            '    print(f"added: {args.text}")'
        ),
        "register": '    "add": {"fn": _cmd_add, "help": "add an item", "args": [("text", {})]},',
    },
    "list": {
        "desc": "print all items",
        "handler": (
            'def _cmd_list(args, items):\n'
            '    if not items:\n'
            '        print("(empty)")\n'
            '    for i, x in enumerate(items):\n'
            '        mark = "x" if x["done"] else " "\n'
            '        print(f"{i}. [{mark}] {x[\'text\']}")'
        ),
        "register": '    "list": {"fn": _cmd_list, "help": "list items", "args": []},',
    },
    "done": {
        "desc": "mark an item done by index",
        "handler": (
            'def _cmd_done(args, items):\n'
            '    items[args.index]["done"] = True\n'
            '    print(f"done: {items[args.index][\'text\']}")'
        ),
        "register": '    "done": {"fn": _cmd_done, "help": "mark done", "args": [("index", {"type": int})]},',
    },
    "remove": {
        "desc": "delete an item by index",
        "handler": (
            'def _cmd_remove(args, items):\n'
            '    x = items.pop(args.index)\n'
            '    print(f"removed: {x[\'text\']}")'
        ),
        "register": '    "remove": {"fn": _cmd_remove, "help": "remove an item", "args": [("index", {"type": int})]},',
    },
    "count": {
        "desc": "report totals",
        "handler": (
            'def _cmd_count(args, items):\n'
            '    done = sum(1 for x in items if x["done"])\n'
            '    print(f"{len(items)} items, {done} done")'
        ),
        "register": '    "count": {"fn": _cmd_count, "help": "count items", "args": []},',
    },
    "clear": {
        "desc": "empty the list",
        "handler": (
            'def _cmd_clear(args, items):\n'
            '    n = len(items)\n'
            '    items.clear()\n'
            '    print(f"cleared {n} items")'
        ),
        "register": '    "clear": {"fn": _cmd_clear, "help": "remove everything", "args": []},',
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
    COMMANDS[args.cmd]["fn"](args, items)
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
}


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
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
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
            print("usage: forge.py puzzle <puzzle-name> \"<moves>\"")
            return
        solve(args[2], puzzle=args[1])
        return
    print(f"unknown command: {cmd}  (try: moves | puzzles | solve | puzzle)")


if __name__ == "__main__":
    main()
