#!/usr/bin/env python3
"""Aether Forge -- AI controller over a block hierarchy on the binary Turing base.

The stack:
    Layer 0   binary Turing machine (scbe spine: bit-increment + 3-bit opcode VM)
    Layer 1   moves      -- primitive abstractions (add, list, done, ...)
    Layer 2+  blocks      -- compositions of moves, and BLOCKS OF BLOCKS
    top       AI controller -- given a TARGET, auto-selects the blocks that reach
              it (preferring bigger blocks = more leverage), assembles a real
              project, and VERIFIES it by running -- you never pick the moves.

This realizes "option 1: AI as the solver" as goal-directed assembly: detect what
the target needs, cover it with the fewest/biggest building blocks, build, verify.

    python scripts/forge_ai.py auto todo-basic
    python scripts/forge_ai.py auto inventory
    python scripts/forge_ai.py blocks
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import _MOVES, _PUZZLES, _exec, assemble, show_signature  # noqa: E402

# Layer 2+: blocks are compositions of moves; blocks may contain BLOCKS (hierarchy).
_BLOCKS: dict[str, list[str]] = {
    "tracker": ["add", "list", "done"],     # a thing you add to, see, and complete
    "counter": ["count", "clear"],           # totals + reset
    "manager": ["tracker", "counter", "remove"],  # a BLOCK OF BLOCKS
    "planner": ["tracker", "due", "agenda", "priority", "sort"],  # a day-planner
    "organizer": ["tracker", "tag", "find", "export"],           # tag/search/export
}


def expand(tokens: list[str]) -> list[str]:
    """Flatten blocks (recursively) to primitive moves, order-preserving + deduped."""
    out: list[str] = []
    for t in tokens:
        out.extend(expand(_BLOCKS[t]) if t in _BLOCKS else [t])
    seen, res = set(), []
    for m in out:
        if m not in seen:
            seen.add(m)
            res.append(m)
    return res


def provides(token: str) -> set[str]:
    if token in _BLOCKS:
        return set(expand([token]))
    return {token} if token in _MOVES else set()


def auto_solve(puzzle: str):
    spec = _PUZZLES.get(puzzle)
    if not spec:
        print(f"  unknown puzzle: {puzzle}   (try: {', '.join(_PUZZLES)})")
        return
    needed = sorted({step[0][0] for step in spec["steps"]})
    print(f"\n  TARGET '{puzzle}': {spec['goal']}")
    print(f"  AI controller: needs commands {needed}")

    # goal-directed greedy set-cover, preferring the biggest building blocks
    candidates = list(_BLOCKS) + list(_MOVES)
    plan, remaining = [], set(needed)
    t0 = time.perf_counter()
    while remaining:
        best = max(candidates, key=lambda c: len(provides(c) & remaining))
        if not (provides(best) & remaining):
            break
        plan.append(best)
        remaining -= provides(best)

    moves = ["app forged"] + expand(plan)
    name, src, _warn, used = assemble(moves)

    # VERIFY by running the assembled app against the target
    ok = True
    with tempfile.TemporaryDirectory() as d:
        app = Path(d) / f"{name}.py"
        app.write_text(src, encoding="utf-8")
        results = []
        for argv, expect in spec["steps"]:
            rc, out = _exec(app, argv)
            hit = (expect is None) or (expect in out)
            ok = ok and rc == 0 and hit
            results.append((argv, rc == 0 and hit, out.strip()[:42]))
    dt = (time.perf_counter() - t0) * 1000
    lines = src.count("\n") + 1

    print(f"  -> chose {len(plan)} building block(s): {', '.join(plan)}")
    print(f"  -> expands to {len(used)} primitive moves: {', '.join(used)}")
    print(f"  -> grounds on Layer 0 (binary Turing spine): each move is a computation the bit-spine can run")
    print()
    for argv, good, out in results:
        print(f"   [{'OK' if good else 'XX'}] {name} {' '.join(argv):<18} -> {out}")
    lev = round(lines / max(1, len(plan)), 1)
    show_signature(used)
    print("\n  " + "=" * 58)
    print(f"  blocks: {len(plan)}   primitive moves: {len(used)}   lines: {lines}   "
          f"leverage: {lev} lines/block   {dt:.0f}ms")
    print(f"  SOLVED: {'YES -- controller reached the target, verified by running' if ok else 'NO'}")
    print("  " + "=" * 58)
    return ok


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    if args[0] == "blocks":
        print("  Layer 2+ building blocks (bigger blocks made of smaller blocks):")
        for b, parts in _BLOCKS.items():
            print(f"    {b:<10} = {parts}   -> moves: {expand([b])}")
        return
    if args[0] == "auto":
        if len(args) < 2:
            print(f"usage: forge_ai.py auto <puzzle>   ({', '.join(_PUZZLES)})")
            return
        auto_solve(args[1])
        return
    print(f"unknown command: {args[0]}  (try: auto | blocks)")


if __name__ == "__main__":
    main()
