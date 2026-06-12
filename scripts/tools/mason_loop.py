#!/usr/bin/env python3
"""mason_loop — drift-driven staged controller over the mason backward-solver.

Fuses two results:
  - mason_solve derives a slot's chisel-fills BACKWARD from the verifier
    (invert / bisect / harvest+confirm), with zero model calls; and
  - the staged-reasoning null test, which found that the load-bearing lever is the
    DRIFT SIGNAL, not a turn index: consolidate when the state stalls, don't grind a
    fixed budget. [scripts/research/staged_prime_reasoning.py]

Here the STATE is the verifier residual — how many of a slot's acceptance checks
still fail (graded, not the binary pass/fail of mason._verify). Each candidate fill
is a TURN; residual is the reasoning state; DRIFT is its change. The controller:

  - climbs capability RUNGS for a slot — invert (read-off / binary-search) →
    harvest+confirm (candidates straight from the request) → model (a pluggable
    proposer; the escalation hook when deterministic solving is exhausted);
  - within a rung, abandons it the moment residual STALLS (no improvement for
    `patience` turns — drift→0 unsolved), instead of exhausting every candidate;
  - keeps a sketchpad of attempts and sub-compacts it when it fills;
  - SEALS the stone with a GeoSeal-style receipt the moment residual hits 0;
  - escalates (names the next rung) when every rung flatlines — honest residue.

Run:
  python scripts/tools/mason_loop.py build pacman_core [--json]
  python scripts/tools/mason_loop.py slot calc_core tokenizer
"""

from __future__ import annotations

import argparse
import ast
import itertools
import json
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mason  # noqa: E402
import mason_solve  # noqa: E402

PATIENCE = 5  # non-improving turns before a CONTINUOUS rung is judged stalled (drift→0)
CHECKPOINT_EVERY = 3
CTX_BUDGET = 80
ENUM_CAP = 2000  # safety cap on a deterministic enumeration rung's candidate set
_BAD_RESIDUAL = 10**6  # a candidate that won't even chisel/parse


# ─────────────────────────────────────────────────────────────────────────────
# Graded verifier residual — the reasoning STATE that drifts.
# ─────────────────────────────────────────────────────────────────────────────


def _atomic_checks(acceptance: str) -> list[str]:
    """Top-level statements of a request, each an independent check to count."""
    return [ast.unparse(stmt) for stmt in ast.parse(acceptance).body]


def residual(defs_code: str, acceptance: str) -> int:
    """How many of the request's top-level checks FAIL against the placed code.

    0 means the slot is satisfied in place (same bar as mason._verify passing); a
    larger number means further away. This graded signal is what lets the loop see
    progress and drift, instead of a single pass/fail at the end.
    """
    checks = _atomic_checks(acceptance)
    lines = [defs_code, "", "__fail = 0"]
    for src in checks:
        lines.append("try:")
        lines.append(textwrap.indent(src, "    "))
        lines.append("except Exception:")
        lines.append("    __fail += 1")
    lines.append("print('RESIDUAL', __fail)")
    with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as fh:
        fh.write("\n".join(lines))
        tmp = Path(fh.name)
    try:
        proc = subprocess.run([sys.executable, str(tmp)], capture_output=True, text=True, timeout=30, check=False)
    finally:
        tmp.unlink(missing_ok=True)
    for tok in reversed(proc.stdout.split()):
        if tok.isdigit():
            return int(tok)
    return _BAD_RESIDUAL  # the module didn't even import/run (e.g. NameError at top)


# ─────────────────────────────────────────────────────────────────────────────
# Sketchpad + tagged sub-compaction (the survivors from the staged null test).
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Note:
    turn: int
    tag: str
    text: str

    def tokens(self) -> int:
        return max(1, len(self.text) // 4)


@dataclass
class Sketchpad:
    notes: list = field(default_factory=list)

    def write(self, turn: int, tag: str, text: str) -> None:
        self.notes.append(Note(turn, tag, text))

    def tokens(self) -> int:
        return sum(n.tokens() for n in self.notes)

    def compact(self, keep_recent: int = 4) -> bool:
        if len(self.notes) <= keep_recent:
            return False
        old, recent = self.notes[:-keep_recent], self.notes[-keep_recent:]
        by_tag: dict[str, list] = {}
        for n in old:
            by_tag.setdefault(n.tag, []).append(n)
        lines = [f"[{t}] x{len(ns)} turns {ns[0].turn}-{ns[-1].turn}" for t, ns in by_tag.items()]
        self.notes = [Note(recent[0].turn, "COMPACT", " ; ".join(lines))] + recent
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Capability rungs — the ordered candidate streams the controller climbs.
# ─────────────────────────────────────────────────────────────────────────────


def _pinned(slot: mason.Slot, piece: mason.Piece, placed: list[str]) -> dict:
    """Holes the verifier pins directly: == read-off, or >=/<= binary search."""
    symbols = mason_solve.hole_symbols(piece)
    pinned: dict = {}
    for hole in piece.holes:
        sym = symbols.get(hole)
        pin = mason_solve.pin_from_request(sym, slot.acceptance) if sym else None
        if pin and pin[0] == "eq":
            pinned[hole] = pin[1]
        elif pin and pin[0] in ("ge", "le"):
            others = {h: pinned.get(h, 1) for h in piece.holes if h != hole}
            val = mason_solve.bisect_int(piece, placed, slot.acceptance, hole, others, pin[0])
            if val is not None:
                pinned[hole] = val
    return pinned


def _rungs(slot: mason.Slot, piece: mason.Piece, placed: list[str], proposer=None):
    """Yield (rung_name, candidate_iterator, kind) outer→escalation, lazily.

    kind 'enumeration' = a closed, capped candidate set (residual is flat-then-zero;
    run it to completion). kind 'continuous' = an open-ended proposer whose residual
    can move gradually — this is where the drift-stall trigger genuinely applies.
    """
    holes = list(piece.holes)
    if not holes:
        yield "invert", iter([{}]), "enumeration"
        return
    pinned = _pinned(slot, piece, placed)
    if len(pinned) == len(holes):
        yield "invert", iter([dict(pinned)]), "enumeration"
    ints, colls, ops = mason_solve.harvest(slot.acceptance)
    cand_lists = []
    for hole in holes:
        if hole in pinned:
            cand_lists.append([pinned[hole]])
        else:
            cand_lists.append(mason_solve.candidates_for(hole, piece, slot.acceptance, ints, colls, ops))

    def harvest_gen():
        for choice in itertools.islice(itertools.product(*cand_lists), ENUM_CAP):
            yield dict(zip(holes, choice))

    yield "harvest", harvest_gen(), "enumeration"
    if proposer is not None:
        yield "model", iter(proposer(slot, piece, placed)), "continuous"


# ─────────────────────────────────────────────────────────────────────────────
# The drift-driven staged controller.
# ─────────────────────────────────────────────────────────────────────────────


def solve_slot_staged(slot, piece, placed, *, patience=PATIENCE, proposer=None) -> dict:
    """Solve one slot as a staged loop: residual is the state, drift is its change.

    Abandons a rung when residual stalls (drift→0 unsolved for `patience` turns),
    seals on residual 0 with a receipt, escalates (names the rung) on flatline.
    """
    pad = Sketchpad()
    turns = 0
    best = (None, _BAD_RESIDUAL)
    drift_trace: list[int] = []
    rung_log: list[dict] = []

    for rung_name, gen, kind in _rungs(slot, piece, placed, proposer):
        last_ckpt = None
        since_improve = 0
        tried = 0
        for fills in gen:
            turns += 1
            tried += 1
            try:
                chiseled = piece.chisel(fills)
                r = residual("\n\n".join(placed + [chiseled]), slot.acceptance)
            except Exception:
                r = _BAD_RESIDUAL
            pad.write(turns, rung_name, f"{fills} -> r={r}")
            if r < best[1]:
                best, since_improve = (dict(fills), r), 0
            else:
                since_improve += 1
            if turns % CHECKPOINT_EVERY == 0:
                if last_ckpt is not None:
                    drift_trace.append(abs(r - last_ckpt))
                last_ckpt = r
            if r == 0:
                rung_log.append({"rung": rung_name, "tried": tried, "outcome": "sealed"})
                return {
                    "slot": slot.name,
                    "stone": piece.name,
                    "solved": True,
                    "fills": fills,
                    "rung": rung_name,
                    "turns": turns,
                    "residual": 0,
                    "drift_trace": drift_trace,
                    "seal": mason._seal(chiseled),
                    "rung_log": rung_log,
                }
            # Drift-stall abandonment applies ONLY to a continuous (open-ended) rung;
            # a closed enumeration runs its capped set to completion (flat residual is
            # its normal texture, not a stall). This is the null-test lever in its
            # correct home — judging when an open search has stopped paying off.
            if kind == "continuous" and since_improve >= patience:
                pad.write(turns, "stall", f"{rung_name} stalled at r={best[1]} after {since_improve} flat turns")
                rung_log.append({"rung": rung_name, "tried": tried, "outcome": "stalled"})
                break
            if pad.tokens() > CTX_BUDGET:
                pad.compact()
        else:
            rung_log.append({"rung": rung_name, "tried": tried, "outcome": "exhausted"})

    ladder = mason.MODEL_LADDER
    escalate_to = ladder[1] if proposer is None else ladder[2]
    return {
        "slot": slot.name,
        "stone": piece.name,
        "solved": False,
        "best_residual": best[1] if best[1] < _BAD_RESIDUAL else None,
        "turns": turns,
        "drift_trace": drift_trace,
        "residue_holes": [h for h in piece.holes],
        "escalate_to": escalate_to,
        "rung_log": rung_log,
    }


def build_staged(schematic, pieces, *, proposer=None) -> dict:
    """Build a schematic slot-by-slot through the drift-driven controller."""
    placed: list[str] = []
    log: list[dict] = []
    for slot in schematic.slots:
        res = solve_slot_staged(slot, pieces[slot.piece], placed, proposer=proposer)
        log.append(res)
        if not res["solved"]:
            return {
                "schema_version": "scbe_mason_loop_v1",
                "schematic": schematic.name,
                "slots_solved": sum(1 for r in log if r["solved"]),
                "slots_total": len(schematic.slots),
                "town_complete": False,
                "halted_at": slot.name,
                "log": log,
            }
        placed.append(pieces[slot.piece].chisel(res["fills"]))
    ok, detail = mason._verify("\n\n".join(placed).rstrip("\n"), schematic.integration)
    return {
        "schema_version": "scbe_mason_loop_v1",
        "schematic": schematic.name,
        "slots_solved": sum(1 for r in log if r["solved"]),
        "slots_total": len(schematic.slots),
        "town_complete": ok,
        "integration_detail": "" if ok else detail,
        "log": log,
    }


def _print(result: dict) -> None:
    print(f"=== mason_loop · '{result['schematic']}' (drift-driven, residual=state) ===\n")
    for r in result["log"]:
        if r["solved"]:
            rl = " -> ".join(f"{e['rung']}:{e['outcome']}({e['tried']})" for e in r["rung_log"])
            print(f"  SEALED {r['slot']:10s} via {r['rung']:7s} in {r['turns']} turns  [{rl}]")
            if r["fills"]:
                print(f"         fills {r['fills']}   drift {r['drift_trace']}   {r['seal'][:24]}")
        else:
            rl = " -> ".join(f"{e['rung']}:{e['outcome']}({e['tried']})" for e in r["rung_log"])
            print(f"  ESCALATE {r['slot']:8s} best_residual={r['best_residual']} -> {r['escalate_to']}  [{rl}]")
    print()
    if result["town_complete"]:
        n, total = result["slots_solved"], result["slots_total"]
        print(f"  TOWN COMPLETE — {n}/{total} sealed drift-driven; integration passed")
    else:
        where = result.get("halted_at") or "integration"
        print(f"  HALTED at '{where}' — {result['slots_solved']}/{result['slots_total']} sealed")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="mason_loop", description="Drift-driven staged mason controller.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pb = sub.add_parser("build", help="build a schematic drift-driven")
    pb.add_argument("schematic", choices=sorted(mason.REGISTRY))
    pb.add_argument("--json", action="store_true")
    ps = sub.add_parser("slot", help="solve a single slot drift-driven")
    ps.add_argument("schematic", choices=sorted(mason.REGISTRY))
    ps.add_argument("slot")
    ps.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)
    schematic, pieces, _ = mason.REGISTRY[args.schematic]
    if args.cmd == "slot":
        slot = next((s for s in schematic.slots if s.name == args.slot), None)
        if slot is None:
            print(f"no slot {args.slot!r} in {args.schematic}", file=sys.stderr)
            return 2
        res = solve_slot_staged(slot, pieces[slot.piece], [])
        print(json.dumps(res, indent=2))
        return 0 if res["solved"] else 1
    result = build_staged(schematic, pieces)
    print(json.dumps(result, indent=2)) if args.json else _print(result)
    return 0 if result["town_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
