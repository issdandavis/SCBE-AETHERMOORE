"""Tests for coding_board -- the operator/operation CSP board (all-at-once coding substrate).

Proves: the solve reaches the energy-0 ground state on solvable boards; forward-checking narrows each
operator's legal vector from the knowns; CBJ targets the EARLIEST (root-cause) operator; an unsolvable
board is reported honestly (not faked); the metric is deterministic.
"""

from __future__ import annotations

from python.scbe.coding_board import (
    Board,
    Operator,
    all_distinct_in_region,
    energy,
    forbidden_after,
    jumpback_target,
    narrowed_domains,
    region_must_agree,
    solve,
    violations,
)


# ---- spatial solve: region must AGREE (interface contract) -------------------------------------
def test_region_agreement_board_solves_to_ground_state():
    b = Board(
        operators=[Operator("o0", ("a", "b"), region="r"), Operator("o1", ("a", "b"), region="r")],
        constraints=[region_must_agree],
    )
    res = solve(b)
    assert res.solved and res.energy == 0
    assert res.assignment["o0"] == res.assignment["o1"]  # the interface matches


# ---- spatial solve: region must be DISTINCT (sudoku row) ---------------------------------------
def test_distinct_region_board_solves_to_a_permutation():
    ops = [Operator("c%d" % i, ("1", "2", "3"), region="row") for i in range(3)]
    b = Board(ops, [all_distinct_in_region])
    res = solve(b)
    assert res.solved and res.energy == 0
    assert len(set(res.assignment.values())) == 3  # all distinct


# ---- operator != operation + knowns lock a cell ------------------------------------------------
def test_fixed_operator_is_a_known_and_constrains_the_rest():
    b = Board(
        operators=[Operator("o0", ("a", "b"), region="r", fixed="a"), Operator("o1", ("a", "b"), region="r")],
        constraints=[region_must_agree],
    )
    res = solve(b)
    assert res.solved and res.assignment["o0"] == "a" and res.assignment["o1"] == "a"


# ---- forward-checking narrows the legal vector from the knowns ---------------------------------
def test_narrowing_prunes_the_legal_vector_using_knowns():
    b = Board(
        operators=[Operator("o0", ("a", "b"), region="r"), Operator("o1", ("a", "b"), region="r")],
        constraints=[region_must_agree],
    )
    narrowed = narrowed_domains(b, {"o0": "a"})
    assert narrowed["o1"] == ("a",)  # given o0=a, o1's only consistent operation is 'a'


# ---- CBJ jumps to the root cause, not one step back -------------------------------------------
def test_cbj_targets_the_earliest_conflicting_operator():
    # o0 and o2 share region r and disagree; o1 is unrelated -> the conflict's root is index 0, not 1.
    b = Board(
        operators=[Operator("o0", ("a",), region="r"), Operator("o1", ("x",)), Operator("o2", ("b",), region="r")],
        constraints=[region_must_agree],
    )
    target = jumpback_target(b, {"o0": "a", "o1": "x", "o2": "b"})
    assert target == 0  # root cause (earliest), not max(involved)-1 == 1


# ---- temporal constraint (across board/program order) -----------------------------------------
def test_temporal_forbidden_after_is_a_violation():
    b = Board(
        operators=[Operator("o0", ("open",)), Operator("o1", ("write",))],
        constraints=[forbidden_after("open", "write")],  # 'write' must not come after 'open'
    )
    vs = violations(b, {"o0": "open", "o1": "write"})
    assert vs and vs[0].involved == [0, 1]


# ---- honesty: unsolvable board is reported, not faked; energy = violation count; determinism ---
def test_unsolvable_board_is_reported_not_faked():
    # a region cannot simultaneously AGREE and be DISTINCT -> no assignment has energy 0
    b = Board(
        operators=[Operator("o0", ("a", "b"), region="r"), Operator("o1", ("a", "b"), region="r")],
        constraints=[region_must_agree, all_distinct_in_region],
    )
    res = solve(b)
    assert res.solved is False  # honest: it does not pretend to solve


def test_energy_is_violation_count_and_deterministic():
    b = Board(
        operators=[Operator("o0", ("a", "b"), region="r"), Operator("o1", ("a", "b"), region="r")],
        constraints=[region_must_agree],
    )
    assert energy(b, {"o0": "a", "o1": "b"}) == 1  # one disagreement
    assert energy(b, {"o0": "a", "o1": "a"}) == 0  # admissible
    assert solve(b).assignment == solve(b).assignment  # deterministic
