"""Tests for the folding-fan grid relation system."""

from __future__ import annotations

import math

import pytest

from python.scbe.folding_fan_grid import (
    FAN_SHAPES,
    CellEdge,
    FanCell,
    FanShapeSpec,
    FoldingFanGrid,
    RelationKind,
    build_all_shapes,
    list_fan_shapes,
)


def test_list_shapes_covers_catalog() -> None:
    names = list_fan_shapes()
    assert "semicircle" in names
    assert "full_circle" in names
    assert "accordion" in names
    assert "nested_rings" in names
    assert "half_board" in names
    assert "sector_grid" in names
    assert "multi_hinge" in names
    assert set(names) == set(FAN_SHAPES)


def test_all_shapes_build_nonempty() -> None:
    grids = build_all_shapes()
    for name, grid in grids.items():
        assert len(grid) > 0, name
        assert len(grid.edges()) > 0, name
        assert grid.shape_name == name


def test_semicircle_mirror_and_path() -> None:
    g = FoldingFanGrid("semicircle", blades=6, rings=3)
    assert len(g) == 6 * 3
    pairs = g.fold_pairs()
    assert pairs  # has fold mirrors
    # blade 0 mirrors blade 5
    a = g.get_cell(0, 1)
    b = g.get_cell(5, 1)
    kinds = {e.kind for e in g.relations_between(a, b)}
    assert RelationKind.FOLD_MIRROR in kinds
    path = g.shortest_path((0, 0), (3, 2))
    assert path is not None
    assert path[0] == g.get_cell(0, 0)
    assert path[-1] == g.get_cell(3, 2)


def test_full_circle_wraps_blades() -> None:
    g = FoldingFanGrid("full_circle", blades=8, rings=2)
    # last blade adjacent to first
    a = g.get_cell(0, 0)
    b = g.get_cell(7, 0)
    kinds = {e.kind for e in g.relations_between(a, b)}
    assert RelationKind.ADJACENT_BLADE in kinds


def test_accordion_mountain_valley_creases() -> None:
    g = FoldingFanGrid("accordion", rings=6)
    creases = g.edges(kinds=[RelationKind.ADJACENT_RING])
    folds = [e.meta.get("fold") for e in creases]
    assert folds
    assert set(folds) <= {"M", "V"}
    # alternating along the strip
    by_ring = sorted(creases, key=lambda e: min(e.a.ring, e.b.ring))
    seq = [e.meta["fold"] for e in by_ring]
    for i in range(len(seq) - 1):
        assert seq[i] != seq[i + 1]


def test_custom_relation_and_filter() -> None:
    g = FoldingFanGrid("sector_grid", blades=3, rings=3)
    g.add_relation((0, 0), (2, 2), kind="support", weight=2.5, name="support")
    edges = g.relations_between((0, 0), (2, 2))
    assert any(e.kind is RelationKind.CUSTOM and e.meta.get("name") == "support" for e in edges)
    neigh = g.neighbors((0, 0), kinds=["support"])
    assert any(n.label() == "b2r2" for n, _ in neigh)
    # custom name filter on edges()
    assert len(g.edges(kinds=["support"])) == 1


def test_half_board_connectx_dimensions() -> None:
    g = FoldingFanGrid("half_board")  # 7 blades x 6 rings default
    assert g.spec.blades == 7
    assert g.spec.rings == 6
    assert len(g) == 42
    # diagonals present for win-line style walks
    assert g.edges(kinds=[RelationKind.DIAGONAL])


def test_multi_hinge_chain() -> None:
    g = FoldingFanGrid("multi_hinge")
    assert g.spec.hinges == 3
    # hinge_chain links same blade/ring across hinges
    chain = g.edges(kinds=["hinge_chain"])
    assert chain
    a = g.get_cell(0, 1, hinge=0)
    b = g.get_cell(0, 1, hinge=1)
    assert g.relations_between(a, b)


def test_incidence_matrix_shape() -> None:
    g = FoldingFanGrid("nested_rings", blades=4, rings=3)
    cells, edges, matrix = g.incidence()
    assert len(matrix) == len(cells)
    assert all(len(row) == len(edges) for row in matrix)
    # each edge has exactly two 1s
    for j in range(len(edges)):
        col_sum = sum(matrix[i][j] for i in range(len(cells)))
        assert col_sum == 2


def test_polar_coordinates_finite() -> None:
    g = FoldingFanGrid("semicircle", blades=5, rings=3)
    for c in g:
        x, y = g.polar(c)
        assert math.isfinite(x) and math.isfinite(y)


def test_no_self_loop() -> None:
    with pytest.raises(ValueError):
        CellEdge(FanCell(0, 0), FanCell(0, 0), RelationKind.CUSTOM)


def test_custom_shape_spec() -> None:
    spec = FanShapeSpec(
        name="tiny",
        blades=2,
        rings=2,
        wrap_blades=False,
        mirror=True,
        diagonals=False,
        hinge_links=True,
    )
    g = FoldingFanGrid(spec)
    assert len(g) == 4
    assert g.fold_pairs()


def test_to_dict_round_schema() -> None:
    g = FoldingFanGrid("sector_grid", blades=2, rings=2)
    g.add_relation((0, 0), (1, 1), name="bond", weight=0.75)
    d = g.to_dict()
    assert d["schema"] == "folding_fan_grid_v1"
    assert d["cell_count"] == 4
    assert d["edge_count"] >= 1
    assert any(e["meta"].get("name") == "bond" for e in d["edges"])  # type: ignore[index]


def test_subgraph_and_filter() -> None:
    g = FoldingFanGrid("semicircle", blades=4, rings=3)
    outer = g.filter_cells(lambda c: c.ring == 2)
    assert all(c.ring == 2 for c in outer)
    sub = g.subgraph_edges(outer, kinds=[RelationKind.ADJACENT_BLADE])
    assert all(e.a.ring == 2 and e.b.ring == 2 for e in sub)


def test_unknown_shape_raises() -> None:
    with pytest.raises(KeyError):
        FoldingFanGrid("not_a_real_fan")
