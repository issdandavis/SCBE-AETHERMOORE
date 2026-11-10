import json

import pytest

from python.scbe.algebraic_radial_token_table import (
    AlgebraicRadialTokenTable,
    RadialTableSpec,
)
from python.scbe.sector_gradient_growth import build_sector_gradient_mesh


def _table() -> AlgebraicRadialTokenTable:
    return AlgebraicRadialTokenTable(
        RadialTableSpec(
            cell_count=32,
            sector_count=4,
            dimensions=8,
            depth_count=2,
            neighbor_count=2,
            seed=37,
        )
    )


def test_gradient_mesh_is_deterministic_bounded_and_receipted() -> None:
    opcodes = tuple((index * 11 + (index // 8) * 7) % 64 for index in range(32))
    first = build_sector_gradient_mesh(_table(), opcodes, max_depth=3, max_gradient_stops=2, split_error_threshold=1.0)
    second = build_sector_gradient_mesh(_table(), opcodes, max_depth=3, max_gradient_stops=2, split_error_threshold=1.0)
    assert first.receipt() == second.receipt()
    assert first.metrics.max_observed_depth <= 3
    assert first.metrics.root_count == 4
    assert first.metrics.node_count <= 4 * (2 ** (3 + 1) - 1)
    assert first.metrics.adaptive_gradient_mse <= first.metrics.fixed_gradient_mse + 1e-12
    assert first.metrics.fixed_gradient_mse <= first.metrics.flat_mse + 1e-12
    json.dumps(first.receipt(), allow_nan=False)


def test_high_variance_grows_nodes_and_leaf_coverage_is_exact() -> None:
    opcodes = tuple((0, 0, 0, 0, 63, 63, 63, 63) * 4)
    mesh = build_sector_gradient_mesh(_table(), opcodes, max_depth=3, max_gradient_stops=2, split_error_threshold=1.0)
    covered = [cell_id for leaf in mesh.leaves for cell_id in leaf.sample_cell_ids]
    assert mesh.metrics.grown_node_count > 0
    assert sorted(covered) == list(range(32))
    assert len(covered) == len(set(covered))


def test_uniform_color_is_a_no_growth_negative_control() -> None:
    mesh = build_sector_gradient_mesh(_table(), (21,) * 32, max_depth=3, split_error_threshold=0.0)
    assert mesh.metrics.node_count == mesh.metrics.root_count == 4
    assert mesh.metrics.leaf_count == 4
    assert mesh.metrics.flat_mse == 0.0
    assert mesh.metrics.adaptive_gradient_mse == 0.0


def test_pixel_render_packs_more_shades_than_the_source_opcode_colors() -> None:
    opcodes = tuple((index * 9) % 64 for index in range(32))
    mesh = build_sector_gradient_mesh(_table(), opcodes, max_depth=2, max_gradient_stops=3, split_error_threshold=16.0)
    image = mesh.render(size=96)
    rendered = set(image.get_flattened_data()) - {(0, 0, 0)}
    source = set(mesh.colors)
    assert image.size == (96, 96)
    assert len(rendered) > len(source)


def test_leaf_fidelity_budget_preserves_growth_and_reduces_error() -> None:
    nonlinear_ramp = (0, 63, 15, 48, 5, 58, 21, 42)
    opcodes = tuple((value + sector * 3) % 64 for sector in range(4) for value in nonlinear_ramp)
    coarse = build_sector_gradient_mesh(
        _table(),
        opcodes,
        max_depth=2,
        max_gradient_stops=2,
        leaf_gradient_stops=2,
        split_error_threshold=1.0,
        min_samples_to_split=5,
    )
    packed = build_sector_gradient_mesh(
        _table(),
        opcodes,
        max_depth=2,
        max_gradient_stops=2,
        leaf_gradient_stops=8,
        split_error_threshold=1.0,
        min_samples_to_split=5,
    )
    assert tuple(node.child_ids for node in coarse.nodes) == tuple(node.child_ids for node in packed.nodes)
    assert packed.metrics.grown_node_count == coarse.metrics.grown_node_count > 0
    assert packed.metrics.packed_stop_count > coarse.metrics.packed_stop_count
    assert packed.metrics.adaptive_gradient_mse < coarse.metrics.adaptive_gradient_mse
    background = (1, 2, 3)
    coarse_colors = set(coarse.render(size=96, background=background).get_flattened_data()) - {background}
    packed_colors = set(packed.render(size=96, background=background).get_flattened_data()) - {background}
    assert len(packed_colors) > len(coarse_colors)


def test_pixel_grade_leaf_palette_accepts_more_than_64_source_aligned_stops() -> None:
    table = AlgebraicRadialTokenTable(
        RadialTableSpec(
            cell_count=260,
            sector_count=4,
            dimensions=8,
            depth_count=2,
            neighbor_count=2,
            seed=41,
        )
    )
    mesh = build_sector_gradient_mesh(
        table,
        tuple(index % 64 for index in range(260)),
        max_depth=0,
        max_gradient_stops=3,
        leaf_gradient_stops=65,
    )
    assert mesh.metrics.node_count == mesh.metrics.root_count == 4
    assert mesh.metrics.packed_stop_count == 260
    assert all(len(leaf.gradient_stops) == 65 for leaf in mesh.leaves)


def test_shuffled_binding_changes_the_receipt_at_equal_budget() -> None:
    opcodes = tuple((index * 5) % 64 for index in range(32))
    shuffled = tuple(reversed(opcodes))
    original = build_sector_gradient_mesh(_table(), opcodes, max_depth=2, max_gradient_stops=2)
    control = build_sector_gradient_mesh(_table(), shuffled, max_depth=2, max_gradient_stops=2)
    assert original.config == control.config
    assert original.receipt()["receipt_sha256"] != control.receipt()["receipt_sha256"]


@pytest.mark.parametrize(
    "opcodes,kwargs",
    [
        ((1,) * 31, {}),
        ((1,) * 31 + (256,), {}),
        ((1,) * 32, {"max_depth": 13}),
        ((1,) * 32, {"max_gradient_stops": 0}),
        ((1,) * 32, {"max_gradient_stops": 3, "leaf_gradient_stops": 2}),
        ((1,) * 32, {"leaf_gradient_stops": 257}),
        ((1,) * 32, {"split_error_threshold": float("inf")}),
    ],
)
def test_invalid_shapes_and_budgets_fail_closed(opcodes, kwargs) -> None:
    with pytest.raises(ValueError):
        build_sector_gradient_mesh(_table(), opcodes, **kwargs)
