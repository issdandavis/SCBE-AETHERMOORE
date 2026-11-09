import json
import math

import pytest

from python.scbe.algebraic_radial_token_table import (
    AlgebraicRadialTokenTable,
    EvidenceState,
    RadialTableSpec,
    RelationEvidence,
    TokenCarrier,
    ZeroKind,
)


def _distance(left, right):
    return math.sqrt(math.fsum((a - b) ** 2 for a, b in zip(left, right, strict=True)))


def test_seeded_geometry_and_receipt_are_reproducible() -> None:
    spec = RadialTableSpec(cell_count=16, sector_count=4, dimensions=6, seed=41)
    first = AlgebraicRadialTokenTable(spec)
    second = AlgebraicRadialTokenTable(spec)
    assert first.base_cells == second.base_cells
    assert first.receipt() == second.receipt()
    assert (
        first.base_cells
        != AlgebraicRadialTokenTable(RadialTableSpec(cell_count=16, sector_count=4, dimensions=6, seed=42)).base_cells
    )


def test_scalar_seed_lifts_into_a_wide_finite_carrier_and_json_receipt() -> None:
    table = AlgebraicRadialTokenTable(
        RadialTableSpec(
            cell_count=16,
            sector_count=4,
            dimensions=64,
            depth_count=1,
            neighbor_count=2,
            seed=0,
        )
    )
    token = TokenCarrier("source:scalar-origin:0")
    vector = table.token_vector(token)
    occupancy = table.assign((token,))
    relays = table.build_relays()
    receipt = table.receipt(occupancies=occupancy, relays=relays)
    assert vector is not None and len(vector) == 64
    assert math.isclose(math.sqrt(sum(value * value for value in vector)), 1.0)
    assert len(receipt["receipt_sha256"]) == 64
    json.dumps(receipt, allow_nan=False)


def test_sector_move_preserves_norms_and_internal_distances() -> None:
    table = AlgebraicRadialTokenTable(RadialTableSpec(cell_count=16, sector_count=4, dimensions=8, seed=7))
    moved = table.move((0.1, -2.0, 1e30, -1e30))
    for base, shifted in zip(table.base_cells, moved, strict=True):
        assert math.isclose(
            _distance(base.coordinates, (0.0,) * 8),
            _distance(shifted.coordinates, (0.0,) * 8),
            abs_tol=1e-12,
        )
    for sector in range(4):
        indices = [cell.cell_id for cell in table.base_cells if cell.sector == sector]
        for left in indices:
            for right in indices:
                assert math.isclose(
                    _distance(
                        table.base_cells[left].coordinates,
                        table.base_cells[right].coordinates,
                    ),
                    _distance(moved[left].coordinates, moved[right].coordinates),
                    abs_tol=1e-12,
                )


def test_token_assignment_uses_identity_and_explicit_weights_with_tie_receipt() -> None:
    table = AlgebraicRadialTokenTable(RadialTableSpec(cell_count=16, sector_count=4, dimensions=4, seed=3))
    token = TokenCarrier("source:7:byte-span:2-5", (0.5, -0.5, 0.25, 0.0))
    first = table.assign((token,))[0]
    second = table.assign((token,))[0]
    assert first == second
    assert first.cell_id in first.tied_cell_ids
    assert first.score is not None and math.isfinite(first.score)


def test_absent_unmeasured_and_measured_neutral_are_distinct() -> None:
    table = AlgebraicRadialTokenTable(
        RadialTableSpec(
            cell_count=8,
            sector_count=2,
            dimensions=4,
            neutral_tolerance=1.0,
        )
    )
    source, target = table.base_cells[:2]
    absent = table.relation(source, target, 0, RelationEvidence(EvidenceState.ABSENT))
    unmeasured = table.relation(source, target, 0, RelationEvidence(EvidenceState.UNMEASURED))
    neutral = table.relation(
        source,
        target,
        0,
        RelationEvidence(EvidenceState.MEASURED, multiplier=0.0, zero_kind=ZeroKind.POSITIVE_LIMIT),
    )
    assert absent.trit is None and absent.raw_value is None
    assert unmeasured.trit is None and unmeasured.raw_value is None
    assert absent.evidence is EvidenceState.ABSENT
    assert unmeasured.evidence is EvidenceState.UNMEASURED
    assert neutral.evidence is EvidenceState.MEASURED
    assert neutral.trit == 0 and neutral.magnitude == 0.0
    assert neutral.zero_kind is ZeroKind.POSITIVE_LIMIT


def test_relays_are_sparse_local_plus_portal_normalized_and_deterministic() -> None:
    table = AlgebraicRadialTokenTable(
        RadialTableSpec(
            cell_count=16,
            sector_count=4,
            dimensions=6,
            depth_count=3,
            neighbor_count=2,
            portal_count=1,
            seed=11,
        )
    )
    relays = table.build_relays(table.move((0.0, 0.2, -0.4, 1.5)))
    assert relays == table.build_relays(table.move((0.0, 0.2, -0.4, 1.5)))
    assert len(relays) == 16 * 3 * 3
    cells_per_sector = 4
    for source in range(16):
        for depth in range(3):
            outgoing = [edge for edge in relays if edge.source == source and edge.depth == depth]
            assert len(outgoing) == 3
            assert sum(not edge.portal for edge in outgoing) == 2
            assert sum(edge.portal for edge in outgoing) == 1
            assert all(
                (edge.source // cells_per_sector != edge.target // cells_per_sector) == edge.portal for edge in outgoing
            )
            assert math.isclose(sum(edge.magnitude for edge in outgoing), 1.0, abs_tol=1e-12)
            assert all(edge.trit in (-1, 0, 1) for edge in outgoing)


def test_movement_preserves_local_relays_but_can_realign_portals() -> None:
    table = AlgebraicRadialTokenTable(
        RadialTableSpec(
            cell_count=16,
            sector_count=4,
            dimensions=6,
            depth_count=2,
            neighbor_count=2,
            portal_count=2,
            seed=19,
        )
    )
    base = table.build_relays()
    moved = table.build_relays(table.move((0.0, 1.5, -2.0, 0.75)))
    base_local = {(e.source, e.target, e.depth): e.raw_value for e in base if not e.portal}
    moved_local = {(e.source, e.target, e.depth): e.raw_value for e in moved if not e.portal}
    assert base_local.keys() == moved_local.keys()
    assert all(math.isclose(base_local[key], moved_local[key], abs_tol=1e-12) for key in base_local)
    base_portals = {(e.source, e.target, e.depth) for e in base if e.portal}
    moved_portals = {(e.source, e.target, e.depth) for e in moved if e.portal}
    assert base_portals != moved_portals


def test_unmeasured_relation_is_sieved_without_becoming_neutral() -> None:
    table = AlgebraicRadialTokenTable(RadialTableSpec(cell_count=8, sector_count=2, dimensions=4, neighbor_count=2))
    blocked = {(0, 1, 0): RelationEvidence(EvidenceState.UNMEASURED)}
    relays = table.build_relays(evidence=blocked)
    assert not any(edge.source == 0 and edge.target == 1 and edge.depth == 0 for edge in relays)


def test_flash_is_bounded_by_normalized_outgoing_channels() -> None:
    table = AlgebraicRadialTokenTable(RadialTableSpec(cell_count=8, sector_count=2, dimensions=4, neighbor_count=2))
    relays = table.build_relays()
    state = {cell_id: (1.0, -1.0) for cell_id in range(8)}
    first = table.flash(state, relays, depth=0, residual=False)
    second = table.flash(state, relays, depth=0, residual=False)
    assert first == second
    assert all(all(math.isfinite(value) for value in vector) for vector in first.values())


def test_invalid_shapes_and_nonfinite_inputs_fail_closed() -> None:
    with pytest.raises(ValueError):
        RadialTableSpec(cell_count=10, sector_count=3)
    table = AlgebraicRadialTokenTable(RadialTableSpec(cell_count=8, sector_count=2, dimensions=4))
    with pytest.raises(ValueError):
        table.move((0.0,))
    with pytest.raises(ValueError):
        table.move((0.0, math.inf))
    with pytest.raises(ValueError):
        table.token_vector(TokenCarrier("x", (1.0, 2.0)))
