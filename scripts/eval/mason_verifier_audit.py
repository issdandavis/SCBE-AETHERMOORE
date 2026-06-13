#!/usr/bin/env python3
"""mason_verifier_audit — prove each schematic's acceptance checks are SOUND by
trying to pass them with a mechanically-synthesized HOLLOW stone.

The AlphaProof lesson, made local: a generate→verify loop is only as strong as
its verifier. AlphaProof's Lean kernel is *sound* — a fake proof cannot pass.
Mason's verifier (mason._verify) runs each "resident's request" as real code, so
its soundness lives entirely in those requests. The existing test gate only
proves the pack author's *hand-written* stub gets captured — it catches the
cheats the author imagined. This auditor catches the whole class instead.

For each slot, keeping every prior stone REAL, it replaces that one slot's stone
with an "omni-constant twin" built from the stone's own interface (same class /
function / constant NAMES, but every method and attribute returns a constant).
If any constant in a small grid makes the slot's acceptance PASS, the acceptance
is UNSOUND: it pins a value, not a behaviour, and a trace-lookup stone would game
it. A slot whose acceptance rejects every hollow twin is sound against this class.

Honest about its own reach: this proves "no omni-constant twin survives" — a
lower bound on soundness, not a totality proof. A check that passes the audit can
still be incomplete in ways a constant oracle can't expose (see --explain).

Run:
  python scripts/eval/mason_verifier_audit.py                # audit every schematic
  python scripts/eval/mason_verifier_audit.py pacman_core --json
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))

import mason  # noqa: E402
import mason_solve  # noqa: E402  (reuse harvest for the constant grid)


def _interface(chiseled: str) -> tuple[list[str], list[tuple[str, list[str]]], list[str]]:
    """Read a stone's public interface from its source: module-level constant
    names, classes (with their method names), and top-level functions."""
    consts: list[str] = []
    classes: list[tuple[str, list[str]]] = []
    funcs: list[str] = []
    try:
        tree = ast.parse(chiseled)
    except SyntaxError:
        return consts, classes, funcs
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    consts.append(tgt.id)
        elif isinstance(node, ast.ClassDef):
            methods = [b.name for b in node.body if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef))]
            classes.append((node.name, methods))
        elif isinstance(node, ast.FunctionDef):
            funcs.append(node.name)
    return consts, classes, funcs


def _const_grid(acceptance: str) -> list[str]:
    """Constants a hollow twin will try to return — generic degenerates plus the
    exact literals the request checks against (harvested from its own text). A
    sound request rejects all of them; an unsound one is satisfied by one."""
    ints, colls, _ops = mason_solve.harvest(acceptance)
    grid: list[str] = ["0", "1", "True", "False", "None", "''", "[]", "{}"]
    for v in ints:
        if repr(v) not in grid:
            grid.append(repr(v))
    for c in colls:
        r = repr(c)
        if r not in grid:
            grid.append(r)
    return grid


def _const_twin(chiseled: str, const_src: str) -> str | None:
    """Omni-constant cheat: same interface names, every constant/method/missing
    attribute returns `const_src`. Catches checks that pin a single value."""
    consts, classes, funcs = _interface(chiseled)
    if not (consts or classes or funcs):
        return None
    parts: list[str] = []
    for name in consts:
        parts.append(f"{name} = {const_src}")
    for cname, methods in classes:
        body: list[str] = ["    def __init__(self, *a, **k):", "        pass"]
        # any attribute the request reads but we never set -> the constant
        body.append("    def __getattr__(self, _n):")
        body.append(f"        return {const_src}")
        for m in methods:
            if m in ("__init__", "__getattr__"):
                continue
            body.append(f"    def {m}(self, *a, **k):")
            body.append(f"        return {const_src}")
        parts.append(f"class {cname}:\n" + "\n".join(body))
    for fname in funcs:
        parts.append(f"def {fname}(*a, **k):\n    return {const_src}")
    return "\n\n".join(parts)


def _counter_twin(chiseled: str) -> str | None:
    """Monotone-counter cheat (the trace-lookup class the audit memory flagged):
    a stone with no real state whose every call returns an incrementing integer
    and whose every attribute read returns the current count. Passes any check
    that only verifies a FIXED call sequence produces accumulating values — i.e.
    a request that memorises a trace instead of probing varied inputs."""
    consts, classes, funcs = _interface(chiseled)
    if not (classes or funcs):
        return None  # counter only models stateful/accumulating interfaces
    parts: list[str] = []
    for name in consts:
        parts.append(f"{name} = 0")
    for cname, methods in classes:
        body = [
            "    def __init__(self, *a, **k):",
            "        object.__setattr__(self, '_k', 0)",
            "    def __getattr__(self, _n):",
            "        return object.__getattribute__(self, '_k')",
            "    def _tick(self):",
            "        object.__setattr__(self, '_k', object.__getattribute__(self, '_k') + 1)",
            "        return object.__getattribute__(self, '_k')",
        ]
        for m in methods:
            if m in ("__init__", "__getattr__", "_tick"):
                continue
            body.append(f"    def {m}(self, *a, **k):")
            body.append("        return self._tick()")
        parts.append(f"class {cname}:\n" + "\n".join(body))
    for fname in funcs:
        parts.append(f"_K_{fname} = [0]")
        parts.append(f"def {fname}(*a, **k):\n    _K_{fname}[0] += 1\n    return _K_{fname}[0]")
    return "\n\n".join(parts)


def _twins(chiseled: str, acceptance: str) -> list[tuple[str, str]]:
    """The auto-adversary's full arsenal of mechanically-synthesized hollow stones,
    most-likely-to-game first: every omni-constant, then the monotone counter."""
    out: list[tuple[str, str]] = []
    for const_src in _const_grid(acceptance):
        twin = _const_twin(chiseled, const_src)
        if twin is not None:
            out.append((f"const:{const_src}", twin))
    counter = _counter_twin(chiseled)
    if counter is not None:
        out.append(("counter", counter))
    return out


def audit_slot(slot: mason.Slot, piece: mason.Piece, real_prior: list[str], acceptance: str) -> dict:
    """Is this slot's acceptance sound? Keep prior stones real; replace this one
    with each hollow twin and see if any passes. Also confirm the real stone
    passes (a slot whose real stone fails is a broken fixture, not a verdict)."""
    real_chiseled = piece.chisel(slot.fills)
    real_ok, real_detail = mason._verify("\n\n".join(real_prior + [real_chiseled]), acceptance)

    gamed_by: str | None = None
    twins = _twins(real_chiseled, acceptance)
    for label, twin in twins:
        ok, _ = mason._verify("\n\n".join(real_prior + [twin]), acceptance)
        if ok:
            gamed_by = label
            break

    return {
        "slot": slot.name,
        "stone": piece.name,
        "real_stone_passes": real_ok,
        "real_detail": "" if real_ok else real_detail,
        "twins_tried": len(twins),
        "sound": real_ok and gamed_by is None,
        "gamed_by": gamed_by,
    }


def audit_schematic(schematic: mason.Schematic, pieces: dict) -> dict:
    real_prior: list[str] = []
    rows: list[dict] = []
    for slot in schematic.slots:
        piece = pieces[slot.piece]
        rows.append(audit_slot(slot, piece, real_prior, slot.acceptance))
        real_prior.append(piece.chisel(slot.fills))  # next slot sees this one real
    unsound = [r for r in rows if not r["sound"]]
    return {
        "schema_version": "scbe_mason_verifier_audit_v1",
        "schematic": schematic.name,
        "slots_total": len(rows),
        "slots_sound": sum(1 for r in rows if r["sound"]),
        "all_sound": not unsound,
        "weak_slots": [r["slot"] for r in unsound],
        "log": rows,
    }


def _print_human(result: dict) -> None:
    print(f"=== mason_verifier_audit · '{result['schematic']}' (can a hollow stone pass the request?) ===\n")
    for row in result["log"]:
        if not row["real_stone_passes"]:
            print(
                f"  BROKEN  {row['slot']:10s} <- {row['stone']:16s} "
                f"real stone FAILS its own request: {row['real_detail']}"
            )
        elif row["sound"]:
            print(f"  sound   {row['slot']:10s} <- {row['stone']:16s} rejected all {row['twins_tried']} hollow twins")
        else:
            print(
                f"  GAMED   {row['slot']:10s} <- {row['stone']:16s} hollow twin "
                f"[{row['gamed_by']}] PASSES — request verifies a trace, not behaviour"
            )
    print()
    if result["all_sound"]:
        print(f"  SOUND — {result['slots_sound']}/{result['slots_total']} acceptance checks reject every hollow twin")
    else:
        print(
            f"  WEAK — {result['slots_sound']}/{result['slots_total']} sound; "
            f"harden requests for: {', '.join(result['weak_slots'])}"
        )
    print("  (lower bound: proves no omni-constant cheat survives — not a totality proof)")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="mason_verifier_audit", description="Audit Mason acceptance-check soundness with an auto-adversary."
    )
    ap.add_argument("schematic", nargs="?", help="schematic to audit (default: all)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    names = sorted(mason.REGISTRY) if not args.schematic else [args.schematic]
    results = []
    for name in names:
        if name not in mason.REGISTRY:
            print(f"unknown schematic: {name}", file=sys.stderr)
            return 2
        schematic, pieces, _ = mason.REGISTRY[name]
        results.append(audit_schematic(schematic, pieces))

    if args.json:
        print(json.dumps(results if len(results) > 1 else results[0], indent=2))
    else:
        for r in results:
            _print_human(r)
            print()
    return 0 if all(r["all_sound"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
