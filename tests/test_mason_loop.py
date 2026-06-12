"""Tests for mason_loop — the drift-driven staged controller over the mason solver.

Locks: (1) the graded verifier residual (the reasoning STATE); (2) deterministic
rungs seal what they can with a receipt; (3) honest escalation when a slot is
under-constrained; and (4) the drift-stall trigger firing in its CORRECT home — a
continuous (model) rung that stops paying off — not on a flat enumeration.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))

import mason  # noqa: E402
import mason_loop  # noqa: E402


def _piece_slot(name):
    schematic, pieces, _ = mason.REGISTRY[name]
    return schematic, pieces


def test_residual_is_graded_zero_when_satisfied():
    _, pieces = _piece_slot("pacman_core")
    world = pieces["world"]
    acc = "assert POINTS_PER_DOT == 1\nassert 'P' in LEVEL"
    assert mason_loop.residual(world.chisel({"POINTS": 1}), acc) == 0
    assert mason_loop.residual(world.chisel({"POINTS": 2}), acc) >= 1  # one check now fails


def test_pacman_world_seals_via_invert_in_one_turn_with_receipt():
    schematic, pieces = _piece_slot("pacman_core")
    slot = next(s for s in schematic.slots if s.name == "world")
    res = mason_loop.solve_slot_staged(slot, pieces[slot.piece], [])
    assert res["solved"] and res["rung"] == "invert" and res["turns"] == 1
    assert res["residual"] == 0 and res["seal"].startswith("geoseal:")


def test_calc_parser_seals_via_harvest_not_stalled():
    # regression: a flat-residual enumeration must run to completion, not be killed
    # by the drift-stall trigger (which belongs only to continuous rungs). The parser
    # request calls tokenize(), so the tokenizer stone must be placed first.
    schematic, pieces = _piece_slot("calc_core")
    placed, res = [], None
    for sname in ("tokenizer", "parser"):
        slot = next(s for s in schematic.slots if s.name == sname)
        res = mason_loop.solve_slot_staged(slot, pieces[slot.piece], placed)
        assert res["solved"], (sname, res)
        placed.append(pieces[slot.piece].chisel(res["fills"]))
    assert res["rung"] == "harvest"  # parser sealed by harvest, not stalled out


def test_full_pacman_build_completes_drift_driven():
    schematic, pieces = _piece_slot("pacman_core")
    r = mason_loop.build_staged(schematic, pieces)
    assert r["town_complete"] and r["slots_solved"] == r["slots_total"]


def test_underconstrained_slot_escalates_honestly():
    # snake world's FOOD is not constrained by its request — no fake fill, an escalate.
    schematic, pieces = _piece_slot("snake_core")
    slot = next(s for s in schematic.slots if s.name == "world")
    res = mason_loop.solve_slot_staged(slot, pieces[slot.piece], [])
    assert not res["solved"]
    assert res["escalate_to"] == mason.MODEL_LADDER[1]  # no proposer -> next rung is mid
    assert res["best_residual"] is not None  # it got partway, honestly reported


def test_model_rung_stalls_on_drift_and_escalates():
    # The drift-stall lever in its correct home: an open-ended proposer whose
    # residual plateaus (unsatisfiable floor) is abandoned after `patience` flat
    # turns and escalated to the big rung — exactly the null-test finding applied.
    piece = mason.Piece(name="knob", shape="config", holes=("A",), template="A = __H_A__")
    slot = mason.Slot(name="knob", piece="knob", acceptance="assert A >= 3\nassert A <= 4\nassert A == 100")

    def proposer(slot, piece, placed):
        return [{"A": 3} for _ in range(8)]

    res = mason_loop.solve_slot_staged(slot, piece, [], proposer=proposer, patience=3)
    assert not res["solved"]
    assert res["escalate_to"] == mason.MODEL_LADDER[2]  # proposer present -> escalate to big
    assert any(e["rung"] == "model" and e["outcome"] == "stalled" for e in res["rung_log"])
