"""Tests for mason_solve — deriving stone chisel-fills BACKWARD from the verifier.

The thesis: for the FILL part of a build the model need not generate anything;
the resident's request already names the answer, so we solve it backward
(invert == / binary-search >= / harvest-and-confirm) with zero model calls, and
honestly report the irreducible residue that is a model's job.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))

import mason  # noqa: E402
import mason_solve  # noqa: E402

_DETERMINISTIC = ("invert", "bisect", "harvest+confirm", "canonical")


def _solve(name):
    schematic, pieces, _ = mason.REGISTRY[name]
    return mason_solve.solve_build(schematic, pieces)


def test_pacman_solves_fully_backward_by_inversion():
    r = _solve("pacman_core")
    assert r["town_complete"], r
    world = next(row for row in r["log"] if row["slot"] == "world")
    # POINTS read straight off `assert POINTS_PER_DOT == 1` — no model, no search.
    assert world["fills"] == {"POINTS": 1}
    assert world["method"]["POINTS"].startswith("invert")


def test_breakout_solves_fully_backward():
    r = _solve("breakout_core")
    assert r["town_complete"], r
    assert r["slots_solved"] == r["slots_total"]


def test_calc_solves_fully_backward_after_coverage_fix():
    r = _solve("calc_core")
    assert r["town_complete"], r
    tok = next(row for row in r["log"] if row["slot"] == "tokenizer")
    # subtraction must be recovered — the gap the backward solver itself exposed.
    assert set(tok["fills"]["OPS"]) == set("+-*/()")


def test_every_solved_method_is_a_deterministic_strategy():
    # nothing is "guessed" — every fill is pinned or confirmed by real execution.
    for name in ("pacman_core", "breakout_core", "calc_core"):
        r = _solve(name)
        for row in r["log"]:
            for m in row["method"].values():
                assert any(m.startswith(p) for p in _DETERMINISTIC), (name, row["slot"], m)


def test_binary_search_converges_on_monotone_hole():
    # genuine reverse binary search: the boundary (CAP - 750 >= 250  =>  CAP >= 1000)
    # is reached over a 10^6 range in ~log2 real executions, not read off a literal.
    piece = mason.Piece(
        name="tank",
        shape="config",
        holes=("CAP",),
        template="CAP = __H_CAP__\n\ndef ok():\n    return CAP - 750 >= 250",
    )
    got = mason_solve.bisect_int(piece, [], "assert ok()", "CAP", {}, "ge", lo=0, hi=1_000_000)
    assert got == 1000, got


def test_inequality_request_routes_through_bisect():
    piece = mason.Piece(name="dam", shape="config", holes=("CAP",), template="CAP = __H_CAP__")
    slot = mason.Slot(name="dam", piece="dam", acceptance="assert CAP >= 500")
    res = mason_solve.solve_slot(slot, piece, [])
    assert res["solved"] and res["fills"]["CAP"] == 500
    assert res["method"]["CAP"].startswith("bisect")


def test_residue_is_reported_not_crashed():
    # snake world FOOD is genuinely unconstrained by the world slot's request — the
    # solver must hand it to a model HONESTLY, never raise and never fake a fill.
    r = _solve("snake_core")
    assert not r["town_complete"]
    assert r.get("halted_at") is not None
    halted = next(row for row in r["log"] if not row["solved"])
    assert halted["residue"]
