"""Lazy 21D layer geometry for byte-exact token honeycomb nodes.

The token nest already owns exact identity and an 18-coordinate local carrier.
This module adds three explicitly typed runtime coordinates -- pipeline layer,
node pressure, and unassimilated residue -- to form a 21D routing point.  It
then reuses the existing safe Poincare embedding and dH metric.

The lift is deliberately lazy.  A vocabulary stores one exact token seed, not
fourteen copied vectors.  Layer-address points are generated when geometric
telemetry is requested.  These points do not execute the named 14-layer
pipeline: every point is independently derived from the same token seed.
Geometry never replaces the byte path or grants execution authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterator, Mapping, Sequence

from src.symphonic_cipher.scbe_aethermoore.ai_brain.unified_state import (
    hyperbolic_distance_safe,
    safe_poincare_embed,
)

TOKEN_LAYER_GEOMETRY_SCHEMA = "scbe.token-layer-geometry-21d.v1"
TOKEN_LAYER_TRACE_SCHEMA = "scbe.token-layer-trace-21d.v1"
TOKEN_LAYER_GEOMETRY_PROFILE = "scbe.local18-layer-pressure-residue3.v1"
DH_METRIC_PROFILE = "scbe.poincare-dh-safe.v1"
LOCAL_CARRIER_DIMENSIONS = 18
GEOMETRY_DIMENSIONS = 21
PIPELINE_LAYER_COUNT = 14

PIPELINE_LAYER_NAMES = (
    "complex_context",
    "realification",
    "weighted_transform",
    "poincare_embedding",
    "hyperbolic_distance",
    "breathing_transform",
    "mobius_phase",
    "multi_well",
    "spectral_coherence",
    "spin_coherence",
    "triadic_distance",
    "harmonic_scaling",
    "decision_risk",
    "audio_axis",
)


class TokenLayerGeometryError(ValueError):
    """A token-layer point violated its declared dimensional contract."""


@dataclass(frozen=True, slots=True)
class TokenLayerGeometrySpec:
    """Bounded controls for lazy layer projection and decimal drift."""

    breathing_amplitude: float = 0.08
    decimal_scale: int = 1_000_000

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.breathing_amplitude)
            or not 0.0 <= self.breathing_amplitude < 1.0
        ):
            raise ValueError("breathing_amplitude must be finite in [0, 1)")
        if (
            isinstance(self.decimal_scale, bool)
            or not isinstance(self.decimal_scale, int)
            or self.decimal_scale < 1
        ):
            raise ValueError("decimal_scale must be a positive integer")


def _finite_vector(
    values: Sequence[float], dimensions: int, name: str
) -> tuple[float, ...]:
    if len(values) != dimensions:
        raise TokenLayerGeometryError(
            f"{name} must have {dimensions} dimensions, got {len(values)}"
        )
    vector = tuple(float(value) for value in values)
    if not all(map(math.isfinite, vector)):
        raise TokenLayerGeometryError(f"{name} must contain only finite values")
    return vector


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _round_fixed(value: float, scale: int) -> int:
    """Round to a signed fixed-point tick with ties away from zero."""

    scaled = value * scale
    return (
        int(math.floor(scaled + 0.5)) if scaled >= 0.0 else int(math.ceil(scaled - 0.5))
    )


def local_breathing_factors(
    layer: int,
    *,
    sector_phase: float = 0.0,
    amplitude: float = 0.08,
) -> tuple[float, ...]:
    """Return six phase-offset lobe factors for one of fourteen layers.

    This is not one global scale.  Each consecutive triad of the 18D carrier
    receives a different phase offset, so neighboring lobes can expand while
    others contract.  All factors stay positive when ``amplitude < 1``.
    """

    if isinstance(layer, bool) or not isinstance(layer, int) or not 1 <= layer <= 14:
        raise TokenLayerGeometryError("layer must be an integer in [1, 14]")
    if not math.isfinite(sector_phase):
        raise TokenLayerGeometryError("sector_phase must be finite")
    if not math.isfinite(amplitude) or not 0.0 <= amplitude < 1.0:
        raise TokenLayerGeometryError("amplitude must be finite in [0, 1)")
    layer_phase = 2.0 * math.pi * (layer - 1) / PIPELINE_LAYER_COUNT
    return tuple(
        1.0
        + amplitude * math.sin(layer_phase + sector_phase + 2.0 * math.pi * lobe / 6.0)
        for lobe in range(6)
    )


def lift_token_layer_21d(
    carrier_18d: Sequence[float],
    *,
    layer: int,
    sector: int,
    sector_count: int,
    occupancy: int,
    insertion_energy: float,
    remaining_energy: float,
    spec: TokenLayerGeometrySpec = TokenLayerGeometrySpec(),
) -> dict[str, Any]:
    """Lift one local token carrier into a bounded 21D Poincare point."""

    carrier = _finite_vector(carrier_18d, LOCAL_CARRIER_DIMENSIONS, "carrier_18d")
    if (
        isinstance(sector, bool)
        or not isinstance(sector, int)
        or isinstance(sector_count, bool)
        or not isinstance(sector_count, int)
        or sector_count < 1
        or not 0 <= sector < sector_count
    ):
        raise TokenLayerGeometryError("sector must lie inside sector_count")
    if isinstance(occupancy, bool) or not isinstance(occupancy, int) or occupancy < 1:
        raise TokenLayerGeometryError("occupancy must be a positive integer")
    if (
        not math.isfinite(insertion_energy)
        or not math.isfinite(remaining_energy)
        or insertion_energy < 0.0
        or remaining_energy < 0.0
        or remaining_energy > insertion_energy + 1e-12
    ):
        raise TokenLayerGeometryError("node energies are inconsistent")

    sector_phase = 2.0 * math.pi * sector / sector_count
    factors = local_breathing_factors(
        layer,
        sector_phase=sector_phase,
        amplitude=spec.breathing_amplitude,
    )
    breathed = tuple(
        carrier[index] * factors[index // 3]
        for index in range(LOCAL_CARRIER_DIMENSIONS)
    )
    layer_coordinate = 2.0 * (layer - 1) / (PIPELINE_LAYER_COUNT - 1) - 1.0
    pressure_coordinate = occupancy / (occupancy + 1.0)
    residue_ratio = (
        0.0
        if insertion_energy == 0.0
        else _clamp01(remaining_energy / insertion_energy)
    )
    residue_coordinate = 2.0 * residue_ratio - 1.0
    raw_21d = (*breathed, layer_coordinate, pressure_coordinate, residue_coordinate)
    point = tuple(safe_poincare_embed(list(raw_21d)))
    radius = math.sqrt(math.fsum(value * value for value in point))
    if len(point) != GEOMETRY_DIMENSIONS or not radius < 1.0:
        raise AssertionError("token layer point escaped the 21D Poincare ball")
    return {
        "schema": TOKEN_LAYER_GEOMETRY_SCHEMA,
        "profile": TOKEN_LAYER_GEOMETRY_PROFILE,
        "dh_metric_profile": DH_METRIC_PROFILE,
        "layer": layer,
        "layer_name": PIPELINE_LAYER_NAMES[layer - 1],
        "point_role": "geometric-layer-address-telemetry",
        "layout": {
            "local_carrier": [0, 18],
            "layer_coordinate": 18,
            "pressure_coordinate": 19,
            "residue_coordinate": 20,
        },
        "sector_phase": sector_phase,
        "local_breathing_factors": list(factors),
        "raw_21d": list(raw_21d),
        "poincare_21d": list(point),
        "poincare_radius": radius,
        "runtime_coordinates": {
            "layer": layer_coordinate,
            "pressure": pressure_coordinate,
            "residue": residue_coordinate,
            "residue_ratio": residue_ratio,
        },
        "claim_boundary": {
            "not_unified_brain_state_roles": True,
            "not_phdm_text_embedding_roles": True,
            "geometry_does_not_replace_exact_token_identity": True,
            "pipeline_layer_was_executed": False,
            "execution_authority": False,
        },
    }


def decimal_drift_receipt(
    previous: Sequence[float],
    current: Sequence[float],
    *,
    scale: int = 1_000_000,
) -> dict[str, Any]:
    """Record a reconstructable fixed-point approximation and its residue."""

    left = _finite_vector(previous, GEOMETRY_DIMENSIONS, "previous")
    right = _finite_vector(current, GEOMETRY_DIMENSIONS, "current")
    if isinstance(scale, bool) or not isinstance(scale, int) or scale < 1:
        raise TokenLayerGeometryError("scale must be a positive integer")
    delta = tuple(b - a for a, b in zip(left, right, strict=True))
    ticks = tuple(_round_fixed(value, scale) for value in delta)
    reconstructed = tuple(value / scale for value in ticks)
    residue = tuple(
        value - approx for value, approx in zip(delta, reconstructed, strict=True)
    )
    return {
        "scale": scale,
        "ticks": list(ticks),
        "residue": list(residue),
        "delta_l2": math.sqrt(math.fsum(value * value for value in delta)),
        "residue_l2": math.sqrt(math.fsum(value * value for value in residue)),
        "residue_max_abs": max(map(abs, residue), default=0.0),
    }


def _token_seed(token_row: Mapping[str, Any]) -> dict[str, Any]:
    try:
        carrier = token_row["node_fill"]["carrier_unit_vector"]
        radial = token_row["radial"]
        fill = token_row["node_fill"]
        token_id = str(token_row["canonical_id"])
    except (KeyError, TypeError) as exc:
        raise TokenLayerGeometryError(
            "token row lacks honeycomb geometry fields"
        ) from exc
    insertion = float(fill["insertion_energy"])
    remaining = float(fill["remaining_energy"])
    return {
        "token_id": token_id,
        "carrier": carrier,
        "sector": int(radial["sector"]),
        "occupancy": int(fill["occupancy_after"]),
        "insertion_energy": insertion,
        "remaining_energy": remaining,
    }


def iter_token_layer_points(
    token_row: Mapping[str, Any],
    *,
    sector_count: int,
    spec: TokenLayerGeometrySpec = TokenLayerGeometrySpec(),
) -> Iterator[dict[str, Any]]:
    """Generate fourteen address points without executing pipeline layers."""

    seed = _token_seed(token_row)
    previous: tuple[float, ...] | None = None
    for layer in range(1, PIPELINE_LAYER_COUNT + 1):
        point = lift_token_layer_21d(
            seed["carrier"],
            layer=layer,
            sector=seed["sector"],
            sector_count=sector_count,
            occupancy=seed["occupancy"],
            insertion_energy=seed["insertion_energy"],
            remaining_energy=seed["remaining_energy"],
            spec=spec,
        )
        current = tuple(point["poincare_21d"])
        if previous is None:
            dh_step = 0.0
            drift = {
                "scale": spec.decimal_scale,
                "ticks": [0] * GEOMETRY_DIMENSIONS,
                "residue": [0.0] * GEOMETRY_DIMENSIONS,
                "delta_l2": 0.0,
                "residue_l2": 0.0,
                "residue_max_abs": 0.0,
            }
        else:
            dh_step = hyperbolic_distance_safe(list(previous), list(current))
            drift = decimal_drift_receipt(previous, current, scale=spec.decimal_scale)
        yield {
            **point,
            "token_id": seed["token_id"],
            "dh_from_previous_layer": dh_step,
            "decimal_drift_from_previous_layer": drift,
        }
        previous = current


def build_token_layer_trace(
    token_row: Mapping[str, Any],
    *,
    sector_count: int,
    spec: TokenLayerGeometrySpec = TokenLayerGeometrySpec(),
) -> dict[str, Any]:
    """Materialize one token's fourteen-point geometric address trace."""

    points = list(
        iter_token_layer_points(token_row, sector_count=sector_count, spec=spec)
    )
    return {
        "schema": TOKEN_LAYER_TRACE_SCHEMA,
        "profile": TOKEN_LAYER_GEOMETRY_PROFILE,
        "dh_metric_profile": DH_METRIC_PROFILE,
        "token_id": points[0]["token_id"],
        "spec": asdict(spec),
        "layer_count": len(points),
        "pipeline_layers_executed": False,
        "points": points,
        "metrics": {
            "maximum_radius": max(point["poincare_radius"] for point in points),
            "total_dh_path": math.fsum(
                point["dh_from_previous_layer"] for point in points
            ),
            "maximum_dh_step": max(point["dh_from_previous_layer"] for point in points),
            "maximum_decimal_residue": max(
                point["decimal_drift_from_previous_layer"]["residue_max_abs"]
                for point in points
            ),
        },
        "storage_contract": {
            "token_seed_is_stored_once": True,
            "fourteen_points_are_derived_on_demand": True,
            "exact_byte_identity_stays_in_honeycomb_receipt": True,
        },
    }


def summarize_token_nest_layer_geometry(
    nest: Mapping[str, Any],
    *,
    spec: TokenLayerGeometrySpec = TokenLayerGeometrySpec(),
) -> dict[str, Any]:
    """Stream all token/layer points into a bounded aggregate report."""

    try:
        tokens = nest["tokens"]
        sector_count = int(nest["spec"]["sector_count"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TokenLayerGeometryError("invalid token nest receipt") from exc
    if not isinstance(tokens, list) or not tokens:
        raise TokenLayerGeometryError("token nest must contain tokens")
    point_count = 0
    total_path = 0.0
    max_step = 0.0
    max_radius = 0.0
    max_residue = 0.0
    for token in tokens:
        previous: tuple[float, ...] | None = None
        for point in iter_token_layer_points(
            token, sector_count=sector_count, spec=spec
        ):
            point_count += 1
            step = float(point["dh_from_previous_layer"])
            total_path += step
            max_step = max(max_step, step)
            max_radius = max(max_radius, float(point["poincare_radius"]))
            max_residue = max(
                max_residue,
                float(point["decimal_drift_from_previous_layer"]["residue_max_abs"]),
            )
            current = tuple(point["poincare_21d"])
            if previous is not None:
                reverse = hyperbolic_distance_safe(list(current), list(previous))
                if not math.isclose(step, reverse, rel_tol=1e-12, abs_tol=1e-12):
                    raise AssertionError("dH symmetry failed during token layer scan")
            previous = current
    return {
        "schema": TOKEN_LAYER_GEOMETRY_SCHEMA,
        "profile": TOKEN_LAYER_GEOMETRY_PROFILE,
        "dh_metric_profile": DH_METRIC_PROFILE,
        "spec": asdict(spec),
        "token_count": len(tokens),
        "layer_count": PIPELINE_LAYER_COUNT,
        "pipeline_layers_executed": False,
        "derived_point_count": point_count,
        "maximum_radius": max_radius,
        "mean_dh_path_per_token": total_path / len(tokens),
        "maximum_dh_step": max_step,
        "maximum_decimal_residue": max_residue,
        "nested_address_collision_count": nest.get("metrics", {}).get(
            "nested_address_collision_count"
        ),
        "learned_gain_proven": False,
        "execution_authority": False,
    }


__all__ = [
    "DH_METRIC_PROFILE",
    "GEOMETRY_DIMENSIONS",
    "PIPELINE_LAYER_COUNT",
    "PIPELINE_LAYER_NAMES",
    "TOKEN_LAYER_GEOMETRY_PROFILE",
    "TOKEN_LAYER_GEOMETRY_SCHEMA",
    "TOKEN_LAYER_TRACE_SCHEMA",
    "TokenLayerGeometryError",
    "TokenLayerGeometrySpec",
    "build_token_layer_trace",
    "decimal_drift_receipt",
    "iter_token_layer_points",
    "lift_token_layer_21d",
    "local_breathing_factors",
    "summarize_token_nest_layer_geometry",
]
