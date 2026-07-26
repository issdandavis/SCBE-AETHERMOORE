import pytest

from src.coding_spine.toroidal_tendril_lattice import (
    Dyadic,
    ProjectivePoint,
    compile_toroidal_lattice,
    decay_reinforcement,
    project_scroll_window,
    reinforce_verified,
    route_tendril,
    shortest_wrapped_delta,
    tendril_receipt,
)


def test_projective_points_include_canonical_infinity_and_reject_floats():
    assert ProjectivePoint(2, 4, 2) == ProjectivePoint(1, 2, 1)
    assert ProjectivePoint(-2, -4, 0) == ProjectivePoint(1, 2, 0)
    assert ProjectivePoint(1, 2, 0).at_infinity
    with pytest.raises(ValueError):
        ProjectivePoint(0, 0, 0)
    with pytest.raises(TypeError):
        ProjectivePoint(1.0, 2, 1)


def test_torus_preserves_winding_and_breaks_half_period_ties_positive():
    lattice = compile_toroidal_lattice(
        [{"id": "v", "x": 12, "y": -1}],
        period_x=10,
        period_y=8,
    )
    vertex = lattice.vertices[0]
    assert (vertex.local_x, vertex.winding_x) == (2, 1)
    assert (vertex.local_y, vertex.winding_y) == (7, -1)
    assert shortest_wrapped_delta(0, 5, 10) == 5
    assert shortest_wrapped_delta(5, 0, 10) == 5


def test_sparse_viewport_keeps_blank_implicit_and_uses_zoom_lod():
    lattice = compile_toroidal_lattice(
        [
            {"id": "base", "x": 0, "y": 0, "zoom_level": 0},
            {"id": "deep", "x": 0, "y": 0, "zoom_level": 5},
            {"id": "far", "x": 100, "y": 0, "zoom_level": 0},
            {"id": "north", "projective": [0, 1, 0]},
        ],
        period_x=256,
        period_y=256,
    )
    overview = project_scroll_window(
        lattice, center_x=0, center_y=0, width=10, height=10, zoom=0
    )
    assert [item.id for item in overview.vertices] == ["base"]
    assert overview.implicit_blank is True
    assert overview.infinity_directions == (("north", ProjectivePoint(0, 1, 0)),)
    detail = project_scroll_window(
        lattice, center_x=0, center_y=0, width=10, height=10, zoom=5
    )
    assert [item.id for item in detail.vertices] == ["base", "deep"]
    assert detail.vertices[0].screen_x == Dyadic(0, 0)


def test_verified_reinforcement_saturates_changes_route_and_decays():
    lattice = compile_toroidal_lattice(
        [
            {"id": "a", "role": "Scout"},
            {"id": "b", "role": "Tank"},
            {"id": "c", "role": "Sniper"},
        ],
        [
            {"id": "ab", "source": "a", "target": "b"},
            {"id": "ac", "source": "a", "target": "c"},
            {"id": "cb", "source": "c", "target": "b"},
        ],
        period_x=16,
        period_y=16,
        saturation=3,
    )
    assert route_tendril(lattice, "a", "b").arc_ids == ("ab",)
    unchanged = reinforce_verified(lattice, ["ac", "cb"], verified=0, amount=9)
    assert unchanged == lattice
    reinforced = reinforce_verified(lattice, ["ac", "cb"], verified=1, amount=9)
    assert [arc.reinforcement for arc in reinforced.arcs if arc.id in {"ac", "cb"}] == [3, 3]
    assert route_tendril(reinforced, "a", "b").arc_ids == ("ac", "cb")
    decayed = decay_reinforcement(reinforced, amount=2)
    assert [arc.reinforcement for arc in decayed.arcs if arc.id in {"ac", "cb"}] == [1, 1]
    with pytest.raises(TypeError):
        reinforce_verified(lattice, ["ab"], verified=1.0)


def test_viewport_is_bounded_and_deterministic():
    vertices = [{"id": name, "x": 0, "y": 0} for name in ("c", "a", "b")]
    lattice = compile_toroidal_lattice(vertices, period_x=8, period_y=8)
    window = project_scroll_window(
        lattice, center_x=0, center_y=0, width=4, height=4, zoom=0, max_items=2
    )
    assert [item.id for item in window.vertices] == ["a", "b"]
    assert window.truncated is True


def test_receipt_is_order_independent_and_self_reinforcement_is_not_evidence():
    vertices = [{"id": "b", "x": 2}, {"id": "a", "x": 1}]
    arcs = [{"id": "edge", "source": "a", "target": "b", "angle": 60}]
    first = compile_toroidal_lattice(vertices, arcs, period_x=7, period_y=7)
    second = compile_toroidal_lattice(reversed(vertices), arcs, period_x=7, period_y=7)
    first_receipt = tendril_receipt(first)
    second_receipt = tendril_receipt(second)
    assert first_receipt["sha256"] == second_receipt["sha256"]
    assert first_receipt["independent_evidence"] is False


def test_compile_rejects_float_coordinates():
    with pytest.raises(TypeError):
        compile_toroidal_lattice(
            [{"id": "bad", "x": 0.5, "y": 0}],
            period_x=8,
            period_y=8,
        )
