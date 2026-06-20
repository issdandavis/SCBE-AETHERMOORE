#!/usr/bin/env python3
"""Aether Forge memory -- the AI's build memory. Remember verified builds; reuse them.

Every verified build leaves a lossless prime "deed". This stores each one as a
RECIPE (intent -> moves -> deed) and, on the next request, RECALLS a matching
recipe and reuses its proven move-set instead of re-deriving the plan. The Forge
gets faster (skip the planning) AND more reliable (reuse something already verified)
the more it builds. The win compounds with build complexity.

    python scripts/forge_memory.py "I want a task tracker with due dates"
    python scripts/forge_memory.py "a to-do where I set deadlines and mark things done"
    python scripts/forge_memory.py --recipes      # what it has learned
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import _MOVES, _exec, assemble, prime_signature  # noqa: E402
from forge_speak import parse_intent, synth_spec  # noqa: E402

RECIPES = Path(os.environ.get("FORGE_RECIPES_PATH") or Path(__file__).resolve().parent / "forge_recipes.json")


def load() -> list:
    return json.loads(RECIPES.read_text(encoding="utf-8")) if RECIPES.exists() else []


def save(recipes: list):
    RECIPES.write_text(json.dumps(recipes, indent=2), encoding="utf-8")


def recall(caps: set, recipes: list):
    """Best-fit verified recipe whose moves cover the needed capabilities (least over-build)."""
    fits = [r for r in recipes if r.get("verified") and set(caps) <= set(r["moves"])]
    return min(fits, key=lambda r: len(r["moves"])) if fits else None


def _build(moves: list, spec: dict):
    """Assemble the move-set and verify it against the spec by RUNNING it."""
    name, src, _w, used = assemble(["app m"] + [m for m in moves if m in _MOVES])
    ok = True
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        app = Path(d) / "m.py"
        app.write_text(src, encoding="utf-8")
        for argv, expect in spec["steps"]:
            rc, out = _exec(app, argv)
            ok = ok and rc == 0 and (expect is None or expect in out)
    return used, src, ok


def build_with_memory(intent: str):
    caps, _gaps = parse_intent(intent)
    if not caps:
        print(f'  could not understand "{intent}"')
        return
    spec = synth_spec(caps, intent)
    recipes = load()
    t0 = time.perf_counter()
    hit = recall(set(caps), recipes)

    if hit:
        used, src, ok = _build(hit["moves"], spec)
        dt = (time.perf_counter() - t0) * 1000
        print(f'\n  "{intent}"')
        print(f"  -> REUSED a remembered recipe (deed {hit['deed']})")
        print(f"     learned from: \"{hit['intent']}\"")
        print(
            f"  -> rebuilt {len(used)} moves, verified by running: "
            f"{'YES' if ok else 'NO'}   {dt:.0f}ms (no re-derivation)"
        )
    else:
        # derive: cover the caps with the smallest move-set, build, verify, remember
        used, src, ok = _build(caps, spec)
        deed = prime_signature(used)
        dt = (time.perf_counter() - t0) * 1000
        print(f'\n  "{intent}"')
        print(f"  -> DERIVED new (no recipe matched), verified by running: {'YES' if ok else 'NO'}   {dt:.0f}ms")
        if ok:
            recipes.append({"intent": intent, "caps": caps, "moves": used, "deed": deed, "verified": True})
            save(recipes)
            print(f"  -> REMEMBERED as recipe #{len(recipes)} (deed {deed}). Next time it's a reuse.")


def main():
    if "--recipes" in sys.argv:
        recipes = load()
        print(f"\n  learned recipes: {len(recipes)}")
        for i, r in enumerate(recipes, 1):
            print(f"   {i}. \"{r['intent']}\"  ->  {', '.join(r['moves'])}  (deed {r['deed']})")
        print()
        return
    intent = " ".join(a for a in sys.argv[1:] if not a.startswith("--")).strip()
    if not intent:
        intent = "I want a task tracker with due dates"
    build_with_memory(intent)


if __name__ == "__main__":
    main()
