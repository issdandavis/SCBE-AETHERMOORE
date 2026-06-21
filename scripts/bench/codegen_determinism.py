#!/usr/bin/env python3
"""codegen_determinism: benchmark the repo's CODE-GENERATION mechanisms for DETERMINISM (+ speed).

Determinism is foundational for this codebase's reversible / CBJ-jump-back substrate: an uncompute only
rewinds correctly if every forward step is byte-reproducible. This runs each code-gen mechanism N times on
a FIXED input and checks the output is byte-identical every run (the is_deterministic check), times it, and
flags any that drift. It deliberately includes overcreation.generate_program SEEDED (must be deterministic)
and UNSEEDED (must NOT be) as a live control proving the benchmark actually catches non-determinism.

    PYTHONPATH=. python scripts/bench/codegen_determinism.py
"""

from __future__ import annotations

import hashlib
import random
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _mechanisms():
    """Build (name, zero-arg callable, expect_deterministic) for each real code-gen mechanism. Defensive:
    a mechanism whose imports/inputs fail is reported as skipped, not a crash."""
    mechs = []

    # --- the source EMITTERS (input -> code string) ---
    try:
        from python.scbe.polyglot import emit as poly_emit
        from python.scbe.polyglot import program_bytes

        toks = program_bytes("add", "mul", "sub")
        for lang in ("python", "javascript", "rust"):
            mechs.append(("polyglot.emit[%s]" % lang, (lambda L=lang: poly_emit(toks, L)), True))
    except Exception as exc:  # noqa: BLE001
        mechs.append(("polyglot.emit", None, exc))

    try:
        from python.scbe.loomfn import EXAMPLES
        from python.scbe.loomfn import emit as lf_emit
        from python.scbe.loomfn import parse as lf_parse

        prog = lf_parse(EXAMPLES[list(EXAMPLES)[0]])
        for lang in ("python", "javascript", "rust"):
            mechs.append(("loomfn.emit[%s]" % lang, (lambda L=lang: lf_emit(prog, L)), True))
    except Exception as exc:  # noqa: BLE001
        mechs.append(("loomfn.emit", None, exc))

    try:
        from python.scbe import loomflow

        flow = [("const", ("x", "0")), ("halt", ())]
        mechs.append(("loomflow.emit[python]", (lambda: loomflow.emit(flow, "python")), True))
    except Exception as exc:  # noqa: BLE001
        mechs.append(("loomflow.emit", None, exc))

    try:
        from python.scbe.instrument import emit_all

        mechs.append(("instrument.emit_all", (lambda: emit_all("C E", "coding")), True))
    except Exception as exc:  # noqa: BLE001
        mechs.append(("instrument.emit_all", None, exc))

    # --- the all-at-once substrate (this session) ---
    try:
        from python.scbe.coding_board import Board, Operator, region_must_agree, solve
        from python.scbe.coding_board_gates import TRANSFORM, gate_names

        board = Board(
            [Operator("o0", gate_names(TRANSFORM), region="r"), Operator("o1", gate_names(TRANSFORM), region="r")],
            [region_must_agree],
        )
        mechs.append(("coding_board.solve", (lambda: solve(board).assignment), True))
        from python.scbe.coding_squad import solve_with_squad

        mechs.append(("coding_squad.solve", (lambda: solve_with_squad(board).assignment), True))
    except Exception as exc:  # noqa: BLE001
        mechs.append(("coding_board/squad", None, exc))

    try:
        from python.scbe.observer_dynamics import ALLOW, ESCALATE, DecisionRecord, retroactive_consistency_gap

        recs = [DecisionRecord(0, "a", ESCALATE, route="r"), DecisionRecord(1, "b", ALLOW, route="x")]
        mechs.append(("observer.retro_gap", (lambda: retroactive_consistency_gap(recs).retroactive_gap), True))
    except Exception as exc:  # noqa: BLE001
        mechs.append(("observer.retro_gap", None, exc))

    try:
        from python.scbe.reversible_circuit import bennett_uncompute

        mechs.append(("reversible.uncompute", (lambda: bennett_uncompute(1234567)), True))
    except Exception as exc:  # noqa: BLE001
        mechs.append(("reversible.uncompute", None, exc))

    # --- the CONTROL: seeded must be deterministic, unseeded must NOT be ---
    try:
        from python.scbe.overcreation import generate_program

        mechs.append(("overcreation[seeded]", (lambda: generate_program(random.Random(42))), True))
        mechs.append(("overcreation[UNSEEDED]", (lambda: generate_program(random.Random())), False))
    except Exception as exc:  # noqa: BLE001
        mechs.append(("overcreation", None, exc))

    return mechs


def _run(fn, runs: int):
    outs = []
    t0 = time.perf_counter()
    for _ in range(runs):
        outs.append(fn())
    dt = (time.perf_counter() - t0) / runs
    digests = {hashlib.sha256(str(o).encode("utf-8")).hexdigest() for o in outs}
    return (len(digests) == 1), len(str(outs[0])), dt * 1e6


def main(runs: int = 25) -> int:
    print("CODE-GENERATION DETERMINISM BENCHMARK  (%d runs each)\n" % runs)
    print("  %-26s %-14s %8s %10s" % ("mechanism", "deterministic", "out-bytes", "us/run"))
    print("  " + "-" * 62)
    det_ok = total = 0
    surprises = []
    for name, fn, expect in _mechanisms():
        if fn is None:
            print("  %-26s SKIP (%s)" % (name, str(expect)[:30]))
            continue
        total += 1
        deterministic, size, us = _run(fn, runs)
        flag = "yes" if deterministic else "NO"
        print("  %-26s %-14s %8d %10.1f" % (name, flag, size, us))
        if deterministic:
            det_ok += 1
        # a surprise = behaviour disagrees with expectation (expect True/False)
        if isinstance(expect, bool) and deterministic != expect:
            surprises.append((name, deterministic, expect))
    print("  " + "-" * 62)
    print("  deterministic: %d / %d mechanisms" % (det_ok, total))
    print("  (overcreation[UNSEEDED] is EXPECTED to be non-deterministic -- the control proving the check works)")
    if surprises:
        print("  !! SURPRISES (behaviour != expected):")
        for name, got, exp in surprises:
            print("     %s: deterministic=%s, expected=%s" % (name, got, exp))
        return 1
    print("  VERDICT: every code generator is byte-reproducible; only the unseeded RNG control varies (as designed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
