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
from forge import _MOVES, _exec, assemble, prime_signature, show_signature  # noqa: E402
from forge_ai import _BLOCKS, expand, provides  # noqa: E402

# plain-English -> a capability the move library actually provides
_INTENT = {
    "add": ["add", "create", "new", "insert", "put", "jot", "capture", "note down"],
    "list": ["list", "show", "see", "view", "display", "read", "look at", "what's on"],
    "done": ["done", "complete", "finish", "mark", "check off", "tick", "close out"],
    "count": ["count", "total", "how many", "number of", "tally"],
    "clear": ["clear", "reset", "empty", "wipe", "delete all", "start over"],
    "remove": ["remove", "delete", "drop", "take off", "get rid"],
    "due": ["due", "deadline", "due date"],
    "agenda": ["agenda", "schedule", "what's due", "whats due", "upcoming"],
    "find": ["find", "search", "look for", "lookup"],
    "edit": ["edit", "rename", "change the"],
    "priority": ["priority", "important", "urgent", "rank"],
    "sort": ["sort", "reorder", "in order"],
    "tag": ["tag", "label", "categor"],
    "export": ["export", "save to file", "markdown"],
}
_TRACKER_WORDS = ("task", "todo", "to-do", "to do", "tracker", "checklist", "list of")
# things we honestly still do NOT have a move for (so we say so instead of faking)
_GAPS = {
    "remind": "reminders",
    "recur": "recurring tasks",
    "repeat": "recurring tasks",
    "sync": "cloud sync",
    "share": "sharing with people",
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
    if "due" in caps and "add" in caps:
        steps.append((["due", "0", "friday"], "due friday"))
    if "agenda" in caps:
        steps.append((["agenda"], "milk" if "add" in caps else None))
    if "priority" in caps and "add" in caps:
        steps.append((["priority", "0", "high"], "priority"))
    if "find" in caps and "add" in caps:
        steps.append((["find", "milk"], "milk"))
    if "tag" in caps and "add" in caps:
        steps.append((["tag", "0", "home"], None))
    if "sort" in caps and "add" in caps:
        steps.append((["sort"], None))
    if "edit" in caps and "add" in caps:
        steps.append((["edit", "0", "bread"], "edited"))
    if "export" in caps:
        steps.append((["export"], None))
    if not steps and caps:
        steps.append(([caps[0]], None))
    return {"goal": text.strip(), "steps": steps}


def _run_spec(move_tokens, spec):
    """Assemble the given move tokens into a real app and verify it by RUNNING the spec.

    Shared by both paths: derive (set-cover -> moves) and reuse (a remembered
    recipe's proven moves). Reuse re-runs the spec too -- memory never replaces
    verification, it only skips the planning.
    """
    name, src, _w, used = assemble(["app forged"] + list(move_tokens))
    ok, results = True, []
    with tempfile.TemporaryDirectory() as d:
        app = Path(d) / f"{name}.py"
        app.write_text(src, encoding="utf-8")
        for argv, expect in spec["steps"]:
            rc, out = _exec(app, argv)
            good = rc == 0 and (expect is None or expect in out)
            ok = ok and good
            results.append((argv, good, out.strip()[:40]))
    return used, src, ok, results


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
    used, src, ok, results = _run_spec(expand(plan), spec)
    return plan, used, src, ok, results


def forge(text: str) -> dict:
    """The one build call: plain words -> a verified, remembered build.

    Prints nothing and returns everything, so a HUMAN (the `scbe forge` CLI) and an
    AI (calling this directly) take the EXACT same path: parse intent -> check build
    memory -> reuse a proven recipe or derive + remember -> verify by RUNNING. The
    `reused` flag and `deed` make the self-improving loop observable from outside.
    """
    caps, gaps = parse_intent(text)
    if not caps:
        return {"ok": False, "reason": "no-intent", "intent": text, "caps": [], "gaps": gaps}
    spec = synth_spec(caps, text)

    # MEMORY: reuse a VERIFIED recipe if one already covers these capabilities;
    # otherwise derive now and remember it -- so each build makes the next faster.
    # Memory is best-effort: any hiccup falls back to a fresh derive, never a crash.
    hit, recipes = None, None
    try:
        from forge_memory import load, recall  # lazy import: forge_memory imports us

        recipes = load()
        hit = recall(set(caps), recipes)
    except Exception:
        recipes = None

    if hit:
        used, src, ok, results = _run_spec([m for m in hit["moves"] if m in _MOVES], spec)
        plan, reused = ["memory"], True
        origin = f'REUSED memory (deed {hit["deed"]}, first learned from "{hit["intent"]}")'
    else:
        plan, used, src, ok, results = solve(spec)
        origin, reused = "DERIVED fresh", False
        if ok and recipes is not None:
            from forge_memory import save

            recipes.append(
                {"intent": text, "caps": caps, "moves": used, "deed": prime_signature(used), "verified": True}
            )
            save(recipes)
            origin += f" -> REMEMBERED as recipe #{len(recipes)} (next time it's a reuse)"

    return {
        "ok": ok,
        "reason": "built",
        "intent": text,
        "caps": caps,
        "gaps": gaps,
        "plan": plan,
        "used": used,
        "src": src,
        "results": results,
        "origin": origin,
        "reused": reused,
        "deed": prime_signature(used),
        "lines": src.count("\n") + 1,
    }


def _render(text: str, r: dict):
    """Print the plain-English forge result (shared by speak() and the --out path)."""
    print(f'\n  YOU SAID: "{text}"')
    if r.get("reason") == "no-intent":
        print("  I couldn't turn that into something I can build yet.")
        print("  Try words like: add, see/list, mark done, count, remove, clear -- or 'a task tracker'.")
        return
    print(f"  I UNDERSTOOD you want to: {', '.join(r['caps'])}")
    print(f"  -> {r['origin']}")
    print(
        f"  -> built it from {len(r['plan'])} building block(s): {', '.join(r['plan'])}  "
        f"({len(r['used'])} moves, {r['lines']} lines, on the binary Turing base)"
    )
    print()
    for argv, good, out in r["results"]:
        print(f"   [{'OK' if good else 'XX'}] forged {' '.join(argv):<16} -> {out}")
    show_signature(r["used"])
    print(f"\n  BUILT + VERIFIED: {'YES -- it runs and does what you asked' if r['ok'] else 'NO'}")
    if r["gaps"]:
        print(f"  HONEST GAPS (no move for these yet): {', '.join(r['gaps'])}")
        print(
            f'   -> I built everything else and proved it. Say "add a {r["gaps"][0].split(" / ")[0]} move" and I will.'
        )


def speak(text: str):
    """Human-facing printer over forge() -- the original plain-English experience."""
    r = forge(text)
    _render(text, r)
    return r["ok"]


def main():
    # Free-text intent, with an optional "--out PATH" that SAVES the forged+verified app.
    # Honest by design: it writes only a build that actually verified, and a write
    # failure is reported and exits non-zero -- never swallowed into a fake success.
    argv = list(sys.argv[1:])
    out_path = None
    if "--out" in argv:
        i = argv.index("--out")
        if i + 1 >= len(argv):
            print("  error: --out needs a file path, e.g. --out app.py", file=sys.stderr)
            raise SystemExit(2)
        out_path = argv[i + 1]
        del argv[i : i + 2]
    text = " ".join(argv).strip() or "I want a task tracker I can mark done and count"

    if out_path is None:
        speak(text)
        return

    r = forge(text)
    _render(text, r)
    if not r.get("ok"):
        print(f"\n  NOT writing {out_path}: the build did not verify (won't save broken code).", file=sys.stderr)
        raise SystemExit(1)
    try:
        Path(out_path).write_text(r["src"], encoding="utf-8")
    except OSError as e:
        print(f"\n  COULD NOT WRITE {out_path}: {e}", file=sys.stderr)
        raise SystemExit(1)
    print(f"\n  WROTE the forged, verified app -> {out_path}  ({r['lines']} lines)")


if __name__ == "__main__":
    main()
