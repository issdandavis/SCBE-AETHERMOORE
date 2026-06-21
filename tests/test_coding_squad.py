"""Tests for coding_squad -- the clone-trooper/Polly-Pad role squad over the coding board (option C).

Proves: roles carry goals + role-scoped gate sub-alphabets; geometric buddy-pairs cover the whole roster
(hyperbolic proximity); the squad solves the board to the energy-0 ground state and records the
coordination (pairs, region coverage, RECON's targets); deterministic.
"""

from __future__ import annotations

import numpy as np

from python.scbe.coding_board import Board, Operator, region_must_agree
from python.scbe.coding_board_gates import CHECK, TRANSFORM, gate_names
from python.scbe.coding_squad import (
    ROLE_PIECES,
    SQUAD,
    Role,
    board_region,
    coverage_gate,
    cover_regions,
    demo,
    geometric_pairs,
    robust_triangulate,
    squad_basis,
    squad_coverage,
    squad_pieces,
    solve_with_squad,
    triangulate,
)
from python.scbe.squad_puzzle import rect


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


# ---- multidimensional triangulation: differentiation is load-bearing, measured -------------------
def _axis_roles(n, dim):
    # n roles whose profiles are the first n coordinate axes of `dim`-space -> a maximally diverse squad
    out = []
    for i in range(n):
        p = [0.0] * dim
        p[i] = 1.0
        out.append(Role("R%d" % i, "axis %d" % i, None, tuple(p)))
    return out


def test_clone_squad_is_rank_deficient_and_blind():
    # the Bad-Batch claim: a squad of identical clones cannot triangulate. Five copies of one role span a
    # single line -> rank 1, blind in the other dims. Differentiation is what buys resolving power.
    clones = [SQUAD[0]] * 5
    cov = squad_coverage(clones)
    assert cov.rank == 1
    assert not cov.full_rank
    assert len(cov.blind_directions) == cov.dim - 1  # blind everywhere but the clone's one direction


def test_differentiated_squad_spans_more_and_full_rank_when_dim_matched():
    # a diverse squad resolves one dimension per independent member; matching member count to dim -> full rank
    roles = _axis_roles(4, 4)
    cov = squad_coverage(roles)
    assert cov.rank == 4 and cov.full_rank and cov.blind_directions == ()
    assert cov.dilution == 1.0  # orthonormal axes -> perfectly conditioned (dilution 1)


def test_target_in_span_is_recovered_blind_component_is_lost():
    # localize a target the squad CAN see (in its span) -> exact; a target along a BLIND direction -> the
    # squad reads all zeros and recovers nothing (the coverage gap is real, not hand-waved).
    roles = _axis_roles(3, 4)  # sees dims 0,1,2 ; dim 3 is blind
    B = squad_basis(roles)
    seen_target = np.array([2.0, -1.0, 0.5, 0.0])  # lies in the span (no dim-3 component)
    tri = triangulate(roles, (B @ seen_target).tolist())
    assert tri.reading_residual < 1e-9
    assert np.allclose(np.array(tri.target_estimate)[:3], seen_target[:3], atol=1e-9)

    blind_target = np.array([0.0, 0.0, 0.0, 9.0])  # entirely in the blind dim 3
    tri_blind = triangulate(roles, (B @ blind_target).tolist())
    assert np.allclose(B @ blind_target, 0.0)  # the squad literally reads nothing
    assert np.linalg.norm(tri_blind.target_estimate) < 1e-9  # ...so it recovers nothing -- the gap


def test_near_collinear_full_rank_squad_has_high_dilution():
    # differentiation is a matter of degree: two nearly-parallel members are technically independent (full
    # rank) but poorly conditioned -> a large dilution of precision (a sloppy fix), unlike orthogonal axes.
    eps = 1e-3
    roles = [
        Role("A", "", None, (1.0, 0.0)),
        Role("B", "", None, (1.0, eps)),  # almost the same direction as A
    ]
    cov = squad_coverage(roles)
    assert cov.full_rank  # technically independent
    assert cov.dilution > 100.0  # ...but weak differentiation -> high dilution (poor triangulation geometry)


# a 5-member squad in 3-D: rank 3 with a TWO-member margin (n = rank + 2), so dropping the traitor still
# leaves an overdetermined (residual-meaningful) fit -- the redundancy needed to IDENTIFY a bad bearing.
def _redundant_squad():
    return _axis_roles(3, 3) + [
        Role("D1", "diag", None, (1.0, 1.0, 1.0)),
        Role("D2", "diag2", None, (1.0, 2.0, 3.0)),
    ]


def test_robust_triangulate_survives_one_traitor():
    # a differentiated squad with redundancy localizes even when one member reports a corrupted bearing:
    # the least-trimmed fuse drops the worst member and recovers the target; plain lstsq is pulled off.
    roles = _redundant_squad()
    B = squad_basis(roles)
    target = np.array([1.0, 2.0, 3.0])
    readings = (B @ target).tolist()
    readings[1] += 50.0  # member R1 is a traitor (corrupted reading)

    plain = triangulate(roles, readings)
    robust, dropped = robust_triangulate(roles, readings)
    assert dropped == "R1"  # identified the traitor by leave-one-out residual
    assert np.linalg.norm(np.array(robust.target_estimate) - target) < 1e-9  # recovered the true target
    assert np.linalg.norm(np.array(plain.target_estimate) - target) > 1.0  # the naive fuse was pulled off


def test_robust_triangulate_no_traitor_keeps_everyone():
    # with clean readings there is no traitor to drop -> robust returns the full-squad fit, drops nobody
    roles = _redundant_squad()
    B = squad_basis(roles)
    target = np.array([1.0, 2.0, 3.0])
    robust, dropped = robust_triangulate(roles, (B @ target).tolist())
    assert dropped is None
    assert np.linalg.norm(np.array(robust.target_estimate) - target) < 1e-9


def test_robust_triangulate_needs_a_two_member_margin_to_identify():
    # honesty bound: with only rank+1 members, dropping any one leaves an EXACT fit (residual 0) so the
    # traitor cannot be told apart -> robust declines to drop (returns the full, traitor-tainted fit).
    roles = _axis_roles(3, 3) + [Role("D", "diag", None, (1.0, 1.0, 1.0))]  # n = rank + 1 only
    B = squad_basis(roles)
    readings = (B @ np.array([1.0, 2.0, 3.0])).tolist()
    readings[1] += 50.0
    _robust, dropped = robust_triangulate(roles, readings)
    assert dropped is None  # cannot isolate a bad bearing without the 2-member margin


# ---- role -> piece binding + the coverage gate (the squad tiles a board with its shapes) ----------
def test_each_role_carries_a_distinct_piece():
    pieces = {name: p.name for name, p in ROLE_PIECES.items()}
    assert set(pieces) == {r.name for r in SQUAD}  # every role has a piece
    assert len(set(pieces.values())) == len(pieces)  # all distinct shapes (a differentiated squad)


def test_squad_pieces_maps_the_roster_in_order():
    pieces = squad_pieces(SQUAD)
    assert [p.name for p in pieces] == [ROLE_PIECES[r.name].name for r in SQUAD]


def test_coverage_gate_differentiated_covers_clone_leaves_a_gap():
    # a 2x2 block + a 1-wide arm: the differentiated role-pieces reach every cell; a clone roster of the 2x2
    # frame cannot reach the 1-wide arm -> a coverage gap (the rigorous, geometric form of cover_regions).
    board = frozenset(rect(2, 2)) | {(0, 2), (0, 3)}
    diff = coverage_gate(SQUAD, board)
    clone = coverage_gate([SQUAD[0]] * 5, board)  # all ARCHITECT (the 2x2 SQUARE)
    assert diff.covered and diff.holes == () and diff.reachable == diff.total == 6
    assert not clone.covered  # the frame cannot reach the 1-wide seam
    assert clone.holes == ((0, 2), (0, 3)) and clone.reachable == 4


def test_coverage_gate_is_necessary_not_sufficient():
    # honesty: "covered" means every cell is REACHABLE by some piece, NOT that an exact tiling exists. The
    # mutilated chessboard is fully reachable by a domino (no holes) yet untileable by dominoes (parity).
    mutilated = frozenset(c for c in rect(4, 4) if c not in {(0, 0), (3, 3)})
    optimizer_only = [r for r in SQUAD if r.name == "OPTIMIZER"] * 7  # OPTIMIZER carries the domino
    gate = coverage_gate(optimizer_only, mutilated)
    assert gate.covered and gate.holes == ()  # no reach gap...
    # ...but reachability does not promise a tiling (the parity wall is checked by squad_puzzle.assemble)


# ---- the gate wired into solve_with_squad (governance pre-check before the solve) -----------------
def _three_op_board():
    # 3 operators -> board_region packs them into an L-tromino (cells (0,0),(0,1),(1,0)); a 2x2 frame can't
    # fit it, so a clone roster of ARCHITECT(frame) cannot cover this board.
    ops = [Operator("o%d" % i, gate_names(TRANSFORM), region="r") for i in range(3)]
    return Board(ops, [region_must_agree])


def test_board_region_packs_operators_into_a_grid():
    assert board_region(_three_op_board()) == frozenset({(0, 0), (0, 1), (1, 0)})  # L-tromino for n=3, w=2


def test_solve_with_squad_attaches_the_coverage_gate():
    board = _three_op_board()
    res = solve_with_squad(board)  # default SQUAD, require_coverage off
    assert res.gate is not None and res.gate.covered  # the differentiated roster reaches the whole layout
    assert res.solved and not res.rejected  # and it still solves the CSP


def test_require_coverage_rejects_a_clone_roster_before_solving():
    board = _three_op_board()
    clone = [SQUAD[0]] * 5  # all ARCHITECT (the 2x2 frame) -> cannot reach a 3-cell L layout
    res = solve_with_squad(board, roles=clone, require_coverage=True)
    assert res.rejected and not res.solved  # rejected BEFORE the solve for a coverage gap
    assert res.gate is not None and not res.gate.covered and len(res.gate.holes) == 3
    assert res.assignment == {}  # no solve was attempted


def test_clone_roster_without_require_coverage_still_solves_but_flags_the_gap():
    # default behaviour is FLAG, not reject: the gap is reported on the gate, but the CSP still solves
    board = _three_op_board()
    clone = [SQUAD[0]] * 5
    res = solve_with_squad(board, roles=clone)  # require_coverage defaults False
    assert not res.rejected and res.solved  # solved despite the geometric gap (gate is a diagnostic here)
    assert res.gate is not None and not res.gate.covered  # ...but the gap is flagged for the caller


# ---- the Landauer energy ledger wired into the solve (the bijective-time arc meets the squad) -----
def test_clean_forward_only_solve_pays_zero_landauer_energy():
    # no CBJ jump-backs -> nothing erased -> 0 J. The honest Landauer point: the cost is in the erasures.
    board = Board([Operator("o0", gate_names(TRANSFORM)), Operator("o1", gate_names(TRANSFORM))], [])
    res = solve_with_squad(board)
    assert res.solved and res.jumps == []
    assert res.squad_energy is not None
    assert res.squad_energy.overwrites == 0 and res.squad_energy.irreversible_joules == 0.0


def test_backtracking_solve_charges_the_cbj_redecisions_at_the_landauer_floor():
    # op0 (domain A,B -> 1 bit) is the CBJ jump-back target; one re-decision pays one Landauer quantum, and
    # the -1 dead-end sentinel is NOT a real re-decision (excluded from the charge).
    board = Board(
        [
            Operator("o0", ("A", "B"), region="r"),
            Operator("o1", ("B",), region="r", fixed="B"),
            Operator("o2", ("A",), region="r"),
        ],
        [region_must_agree],
    )
    res = solve_with_squad(board)
    assert -1 in res.jumps  # the solver hit a dead end (sentinel present)
    e = res.squad_energy
    assert e.overwrites == 1 and e.bits_erased == 1  # only the valid jump (op0), decision_bits(2) == 1
    assert e.irreversible_joules > 0.0  # the dissipating (overwrite) solve pays the floor
    assert e.reversible_joules == 0.0  # logging the jumps as an undo-tape would erase nothing (Bennett)


def test_rejected_board_meters_no_energy_no_solve_ran():
    # require_coverage rejects before solving -> no CBJ re-decisions happened -> squad_energy stays None
    res = solve_with_squad(_three_op_board(), roles=[SQUAD[0]] * 5, require_coverage=True)
    assert res.rejected and res.squad_energy is None


def test_triangulation_demo_all_true():
    d = demo()
    assert all(v for k, v in d.items() if not k.startswith("_"))
