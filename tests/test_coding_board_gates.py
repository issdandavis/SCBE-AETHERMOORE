"""Tests for coding_board_gates -- reversible gate alphabet bound to the coding board (option A).

Proves: every operation in the alphabet is a true reversible gate (run then unrun = identity); an assigned
board IS a reversible circuit; the CBJ jump-back == Bennett uncompute (rewind the tail = run only the
prefix, nothing erased); the board solves over the gate alphabet; gates are role-tagged for the squad (C).
"""

from __future__ import annotations

from python.scbe.coding_board import Board, Operator, region_must_agree, solve
from python.scbe.coding_board_gates import (
    CHECK,
    GATE_ALPHABET,
    TRANSFORM,
    circuit_from_board,
    gate_names,
    gate_role,
    jumpback_is_uncompute,
    run_board,
    uncompute_after,
)
from python.scbe.reversible_circuit import run, unrun


# ---- every operation is a true reversible gate -------------------------------------------------
def test_every_alphabet_gate_is_reversible():
    reg = {"a": 5, "b": 3, "scratch": 0, "out": 0}
    for name, (gate, _role) in GATE_ALPHABET.items():
        assert unrun(run(dict(reg), [gate]), [gate]) == reg, "gate %r is not reversible" % name


# ---- role-scoped sub-alphabets for the future role squad (C) -----------------------------------
def test_role_tags_partition_the_alphabet_for_the_squad():
    transforms = set(gate_names(TRANSFORM))
    checks = set(gate_names(CHECK))
    assert transforms and checks
    assert transforms.isdisjoint(checks)
    assert transforms | checks == set(gate_names())
    assert all(gate_role(n) == TRANSFORM for n in transforms)


# ---- an assigned board IS a reversible circuit -------------------------------------------------
def test_assigned_board_is_a_reversible_circuit():
    ops = [Operator("o%d" % i, gate_names(TRANSFORM)) for i in range(3)]
    board = Board(ops, [])
    assign = {"o0": "xor_a_b", "o1": "add_a_1", "o2": "xor_b_a"}
    reg = {"a": 9, "b": 4}
    there = run_board(dict(reg), board, assign)
    back = unrun(there, circuit_from_board(board, assign))
    assert back == reg  # forward then full reverse is the identity (no information lost)


# ---- the CBJ jump-back is a true Bennett uncompute --------------------------------------------
def test_jumpback_equals_uncompute_no_garbage():
    ops = [Operator("o%d" % i, gate_names(TRANSFORM)) for i in range(4)]
    board = Board(ops, [])
    assign = {"o0": "add_a_1", "o1": "xor_a_b", "o2": "add_b_1", "o3": "xor_b_a"}
    reg = {"a": 2, "b": 7}
    # jumping back to operator 1 must equal having run only operators 0..1 -- erasing nothing
    assert jumpback_is_uncompute(reg, board, assign, checkpoint=1)
    restored = uncompute_after(run_board(dict(reg), board, assign), board, assign, checkpoint=1)
    only_prefix = run_board(dict(reg), board, {"o0": assign["o0"], "o1": assign["o1"]})
    assert restored == only_prefix


# ---- the board still solves over the gate alphabet --------------------------------------------
def test_board_solves_over_the_gate_alphabet():
    ops = [Operator("o0", gate_names(TRANSFORM), region="r"), Operator("o1", gate_names(TRANSFORM), region="r")]
    board = Board(ops, [region_must_agree])
    res = solve(board)
    assert res.solved and res.energy == 0
    assert res.assignment["o0"] == res.assignment["o1"]  # the interface (same reversible gate) matches
    assert res.assignment["o0"] in GATE_ALPHABET  # ...and it is a real gate from the alphabet
