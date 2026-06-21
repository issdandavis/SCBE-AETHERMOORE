"""Tests for coding_squad -- the clone-trooper/Polly-Pad role squad over the coding board (option C).

Proves: roles carry goals + role-scoped gate sub-alphabets; geometric buddy-pairs cover the whole roster
(hyperbolic proximity); the squad solves the board to the energy-0 ground state and records the
coordination (pairs, region coverage, RECON's targets); deterministic.
"""

from __future__ import annotations

from python.scbe.coding_board import Board, Operator, region_must_agree
from python.scbe.coding_board_gates import CHECK, TRANSFORM, gate_names
from python.scbe.coding_squad import SQUAD, cover_regions, geometric_pairs, solve_with_squad


# ---- roles carry goals + role-scoped sub-alphabets (the Polly-Pad loadout) ---------------------
def test_roles_have_goals_and_scoped_alphabets():
    by_name = {r.name: r for r in SQUAD}
    assert set(["ARCHITECT", "RECON", "CODER", "CHECK", "OPTIMIZER"]).issubset(by_name)
    assert all(r.goal for r in SQUAD)
    assert by_name["CODER"].gate_role == TRANSFORM
    assert by_name["CHECK"].gate_role == CHECK
    assert set(by_name["CODER"].legal_operations()) == set(gate_names(TRANSFORM))
    assert by_name["ARCHITECT"].legal_operations() == ()  # a non-coding (coordination) role


# ---- geometric buddy-pairs cover the whole roster ---------------------------------------------
def test_geometric_pairs_cover_every_role():
    pairs = geometric_pairs(SQUAD)
    named = set()
    for a, b, dist in pairs:
        named.add(a)
        if b is not None:
            named.add(b)
        assert dist >= 0.0  # a real hyperbolic distance
    assert named == {r.name for r in SQUAD}  # everyone is on a team (or solos)


# ---- the squad solves the board + records the coordination ------------------------------------
def test_squad_solves_board_and_records_coverage():
    ops = [Operator("o0", gate_names(TRANSFORM), region="r"), Operator("o1", gate_names(TRANSFORM), region="r")]
    board = Board(ops, [region_must_agree])
    res = solve_with_squad(board)
    assert res.solved and res.energy == 0
    assert res.assignment["o0"] == res.assignment["o1"]  # interface matches
    assert set(res.targets) == {"o0", "o1"}  # RECON found the unknowns
    assert "r" in res.coverage  # the region is covered by a buddy team
    assert res.roster["CODER"].endswith("ops")  # the loadout sizes are recorded


def test_recon_targets_exclude_knowns():
    ops = [
        Operator("o0", gate_names(TRANSFORM), region="r", fixed="id"),
        Operator("o1", gate_names(TRANSFORM), region="r"),
    ]
    res = solve_with_squad(Board(ops, []))
    assert res.targets == ["o1"]  # the fixed (known) operator is not a target


def test_cover_regions_with_no_regions_is_one_zone():
    ops = [Operator("o0", gate_names(TRANSFORM)), Operator("o1", gate_names(TRANSFORM))]
    cov = cover_regions(Board(ops, []), geometric_pairs(SQUAD))
    assert list(cov.keys()) == ["<whole-board>"]


def test_squad_is_deterministic():
    ops = [Operator("o0", gate_names(TRANSFORM), region="r"), Operator("o1", gate_names(TRANSFORM), region="r")]
    board = Board(ops, [region_must_agree])
    a = solve_with_squad(board)
    b = solve_with_squad(board)
    assert a.pairs == b.pairs and a.coverage == b.coverage and a.assignment == b.assignment
