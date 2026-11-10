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
        ((1,) * 32, {"split_error_threshold": float("inf")}),
    ],
)
def test_invalid_shapes_and_budgets_fail_closed(opcodes, kwargs) -> None:
    with pytest.raises(ValueError):
        build_sector_gradient_mesh(_table(), opcodes, **kwargs)
