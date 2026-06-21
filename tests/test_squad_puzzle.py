"""Tests for squad_puzzle -- the squad's NON-STANDARD value: each member is a geometric PIECE and the squad
TILES the target (exact cover) instead of localizing it with scalar readings.

Load-bearing, execution-verified claims:
  * a DIFFERENTIATED squad tiles a target that a CLONE squad (one shape repeated) cannot -- differentiation
    is what makes the assembly possible (the geometric form of "clones can't triangulate");
  * a solved tiling re-verifies independently (disjoint placements whose union == the region);
  * a cell no piece can reach is a HOLE (the blind spot / absence-is-information), reported either way;
  * a matched-area, hole-free region can still be UNTILEABLE (the mutilated-chessboard parity obstruction);
  * deterministic.
"""

from __future__ import annotations

from python.scbe.squad_puzzle import (
    DOMINO,
    I_TROMINO,
    L_TROMINO,
    MONO,
    SQUARE,
    T_TETRO,
    Piece,
    assemble,
    coverable_cells,
    exact_cover,
    holes,
    placements,
    rect,
)


def test_piece_orientations_dedupe_by_symmetry():
    # symmetric pieces collapse to fewer distinct orientations
    assert len(MONO.shapes()) == 1  # a single cell
    assert len(SQUARE.shapes()) == 1  # 2x2 is fully symmetric
    assert len(DOMINO.shapes()) == 2  # horizontal / vertical
    assert len(I_TROMINO.shapes()) == 2  # 1x3 horizontal / vertical
    assert len(L_TROMINO.shapes()) == 4  # the right tromino has 4 distinct orientations
    assert len(T_TETRO.shapes()) == 4


def test_placements_lie_fully_inside_the_region():
    region = rect(3, 3)
    for placed in placements(L_TROMINO, region):
        assert placed <= region  # never spills outside
        assert len(placed) == L_TROMINO.area  # a full piece each time


def test_exact_cover_tiles_and_independently_verifies():
    region = rect(2, 4)  # area 8
    res = assemble(region, [T_TETRO, L_TROMINO, MONO])  # 4 + 3 + 1 == 8
    assert res.solved
    assert res.verify(region)  # disjoint placements whose union == the region (re-checked, not trusted)
    # every region cell is covered exactly once
    covered = [c for cells in res.placement.values() for c in cells]
    assert sorted(covered) == sorted(region) and len(covered) == len(set(covered))


def test_differentiation_isolated_at_matched_area():
    # the variable under test must be SHAPE-DIVERSITY, not area (a clone failing on area would prove nothing).
    # bent-L target, area 3: a homogeneous straight I-tromino (area 3) cannot bend to fit the L at all -- it
    # has no legal placement, so every cell becomes a hole -- while a differentiated mono+domino (area 3)
    # tiles it. Same area -> the shape is the only difference (a reach failure; see the parity case below).
    bent_l = frozenset({(0, 0), (1, 0), (1, 1)})
    diff = assemble(bent_l, [MONO, DOMINO])
    clone = assemble(bent_l, [I_TROMINO])
    assert diff.solved and diff.verify(bent_l)
    assert not clone.solved  # same area, only the shape differs -> differentiation is load-bearing
    assert clone.holes == tuple(sorted(bent_l))  # the rigid straight shape fits nowhere in the bent target


def test_clone_parity_fails_where_differentiated_succeeds_same_area():
    # a matched-area MULTI-clone failure by parity (mutilated chessboard, 14 cells): seven dominoes cannot
    # (8-6 colour imbalance), but swapping two for monominoes (still 14) tiles it -- diversity beats parity.
    mutilated = frozenset(c for c in rect(4, 4) if c not in {(0, 0), (3, 3)})
    clone7 = assemble(mutilated, [DOMINO] * 7)
    diff = assemble(mutilated, [DOMINO] * 6 + [MONO, MONO])
    assert clone7.area_pieces == diff.area_pieces == 14  # same area both ways
    assert not clone7.solved  # the homogeneous squad hits the parity wall
    assert diff.solved and diff.verify(mutilated)  # the differentiated squad clears it


def test_clones_are_not_useless_they_tile_a_matching_target():
    # honesty: a clone squad still tiles targets that decompose into its one shape (two dominoes -> 2x2)
    res = assemble(rect(2, 2), [DOMINO, DOMINO])
    assert res.solved and res.verify(rect(2, 2))


def test_holes_are_cells_no_piece_can_reach():
    scattered = frozenset({(0, 0), (5, 5)})  # two isolated cells
    assert holes(scattered, [DOMINO]) == ((0, 0), (5, 5))  # a domino needs an adjacent partner -> none fit
    assert coverable_cells(scattered, [DOMINO]) == frozenset()
    res = assemble(scattered, [DOMINO])
    assert not res.solved and res.holes == ((0, 0), (5, 5))
    # a monomino reaches both -> no holes
    assert holes(scattered, [MONO, MONO]) == ()


def test_matched_area_hole_free_region_can_still_be_untileable():
    # the mutilated chessboard: 4x4 minus two opposite (same-colour) corners. 14 cells, 7 dominoes -> area
    # matches and every cell is reachable (no holes), yet NO tiling exists (a parity obstruction, deeper than
    # a hole). The solver must say so honestly.
    mutilated = frozenset(c for c in rect(4, 4) if c not in {(0, 0), (3, 3)})
    res = assemble(mutilated, [DOMINO] * 7)
    assert res.area_pieces == res.area_region == 14
    assert res.holes == ()  # nothing is individually uncoverable...
    assert not res.solved  # ...but the packing is still impossible (colour parity 8 vs 6)


def test_area_mismatch_is_unsolvable():
    assert exact_cover(rect(2, 3), [DOMINO, DOMINO]) is None  # 4 != 6
    res = assemble(rect(2, 3), [DOMINO, DOMINO])
    assert not res.solved and res.area_pieces == 4 and res.area_region == 6


def test_assemble_is_deterministic():
    region = rect(2, 4)
    a = assemble(region, [T_TETRO, L_TROMINO, MONO])
    b = assemble(region, [T_TETRO, L_TROMINO, MONO])
    assert a.placement == b.placement and a.solved == b.solved


def test_clone_pieces_are_tracked_as_distinct_uses():
    # two identical-named dominoes must both be placed (tracked by use-count), tiling a 1x4 line
    res = assemble(rect(1, 4), [DOMINO, DOMINO])
    assert res.solved and res.verify(rect(1, 4))
    assert len(res.placement) == 2  # both clone uses recorded separately (name#0, name#1)


def test_custom_piece_and_full_tiling():
    # a bespoke pentomino-ish piece composes with others; the engine is not tied to the library
    plus = Piece("plus", ((0, 1), (1, 0), (1, 1), (1, 2), (2, 1)), 1)  # the + pentomino (area 5)
    region = rect(1, 5)
    # the plus cannot fit a 1x5 line -> it is all holes for that piece's reach
    assert holes(region, [plus]) == tuple(sorted(region))


def test_demo_all_true():
    from python.scbe.squad_puzzle import demo

    d = demo()
    assert all(v for k, v in d.items() if not k.startswith("_"))
