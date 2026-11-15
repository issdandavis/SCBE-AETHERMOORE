"""Lazy 21D geometry and decimal drift over exact token nests."""

from __future__ import annotations

import math

import pytest

from python.scbe.token_honeycomb_nest import (
    TokenNestInput,
    build_typed_token_honeycomb,
)
from python.scbe.token_layer_geometry import (
    GEOMETRY_DIMENSIONS,
    PIPELINE_LAYER_COUNT,
    TokenLayerGeometryError,
    TokenLayerGeometrySpec,
    build_token_layer_trace,
    decimal_drift_receipt,
    lift_token_layer_21d,
    local_breathing_factors,
    summarize_token_nest_layer_geometry,
)


def _nest() -> dict:
    return build_typed_token_honeycomb(
        (
            TokenNestInput("alpha", "identifier", b"alpha".hex(), 0),
            TokenNestInput("beta", "identifier", b"beta".hex(), 1),
            TokenNestInput("plus", "operator", b"+".hex(), 2),
        )
    )


def test_local_breathing_has_six_positive_non_global_lobes() -> None:
    factors = local_breathing_factors(6, sector_phase=0.25, amplitude=0.08)
    assert len(factors) == 6
    assert len({round(value, 12) for value in factors}) > 2
    assert all(0.92 <= value <= 1.08 for value in factors)


def test_one_token_builds_fourteen_bounded_21d_points() -> None:
    nest = _nest()
    trace = build_token_layer_trace(nest["tokens"][0], sector_count=nest["spec"]["sector_count"])
    assert trace["layer_count"] == PIPELINE_LAYER_COUNT
    assert trace["pipeline_layers_executed"] is False
    assert [row["layer"] for row in trace["points"]] == list(range(1, 15))
    assert all(len(row["poincare_21d"]) == GEOMETRY_DIMENSIONS for row in trace["points"])
    assert all(row["poincare_radius"] < 1.0 for row in trace["points"])
    assert trace["points"][0]["dh_from_previous_layer"] == 0.0
    assert all(row["dh_from_previous_layer"] >= 0.0 for row in trace["points"])
    assert trace == build_token_layer_trace(nest["tokens"][0], sector_count=nest["spec"]["sector_count"])


def test_decimal_drift_retains_sub_tick_residue() -> None:
    previous = [0.0] * GEOMETRY_DIMENSIONS
    current = [0.0000006, -0.0000006] + [0.0] * (GEOMETRY_DIMENSIONS - 2)
    receipt = decimal_drift_receipt(previous, current, scale=1_000_000)
    assert receipt["ticks"][:2] == [1, -1]
    assert receipt["residue_max_abs"] <= 0.5 / 1_000_000 + 1e-18
    reconstructed = [
        tick / receipt["scale"] + residue for tick, residue in zip(receipt["ticks"], receipt["residue"], strict=True)
    ]
    assert reconstructed == pytest.approx(current)


def test_nest_summary_streams_without_address_loss() -> None:
    nest = _nest()
    summary = summarize_token_nest_layer_geometry(nest)
    assert summary["token_count"] == 3
    assert summary["derived_point_count"] == 3 * PIPELINE_LAYER_COUNT
    assert summary["pipeline_layers_executed"] is False
    assert summary["maximum_radius"] < 1.0
    assert summary["maximum_decimal_residue"] <= 0.5 / 1_000_000 + 1e-15
    assert summary["nested_address_collision_count"] == 0
    assert summary["learned_gain_proven"] is False


def test_invalid_layer_or_energy_fails_closed() -> None:
    carrier = [1.0] + [0.0] * 17
    with pytest.raises(TokenLayerGeometryError, match="layer"):
        lift_token_layer_21d(
            carrier,
            layer=0,
            sector=0,
            sector_count=8,
            occupancy=1,
            insertion_energy=1.0,
            remaining_energy=0.0,
        )
    with pytest.raises(TokenLayerGeometryError, match="energies"):
        lift_token_layer_21d(
            carrier,
            layer=1,
            sector=0,
            sector_count=8,
            occupancy=1,
            insertion_energy=0.25,
            remaining_energy=0.5,
        )


def test_geometry_profile_does_not_claim_brain_state_or_execution() -> None:
    point = lift_token_layer_21d(
        [1.0] + [0.0] * 17,
        layer=1,
        sector=0,
        sector_count=8,
        occupancy=1,
        insertion_energy=1.0,
        remaining_energy=0.0,
        spec=TokenLayerGeometrySpec(),
    )
    assert point["claim_boundary"]["not_unified_brain_state_roles"]
    assert point["claim_boundary"]["not_phdm_text_embedding_roles"]
    assert point["claim_boundary"]["pipeline_layer_was_executed"] is False
    assert point["claim_boundary"]["execution_authority"] is False
    assert math.isfinite(point["poincare_radius"])
