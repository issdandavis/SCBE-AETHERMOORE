"""MAHSS-driven toy optimization for auxetic metamaterial variants.

This is a deterministic simulation harness, not a CFD/FEM solver. It converts
candidate auxetic material designs into five physics-flavored mechanism
vectors, folds them through MAHSS, and ranks designs by a transparent objective.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import sys
from typing import Iterable, Mapping, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.mahss import (
    MAHSSConfig,
    asymmetric_well_probabilities,
    build_mahss,
    l2_normalize,
    length_square_probabilities,
    polar_vector_probabilities,
    radial_power_profile,
)
from python.scbe.space_filling import bits_for_cardinality, morton_encode

SCHEMA_VERSION = "scbe_mahss_metamaterial_sim_v1"
MECHANISMS = (
    "flow_pressure",
    "magnetic_actuation",
    "auxetic_porosity",
    "thermal_inertia",
    "abrasion_sheath",
)
DIM = 64


@dataclass(frozen=True)
class AuxeticVariant:
    """Material/design constants for a toy auxetic layer."""

    name: str
    poisson_ratio: float
    relaxed_porosity: float
    max_closure_fraction: float
    modulus_mpa: float
    density_kg_m3: float
    temperature_limit_c: float
    abrasion_resistance: float
    magnetic_response: float
    recoverability: float
    cost_index: float


@dataclass(frozen=True)
class OperatingPoint:
    """Shared operating assumptions for candidate evaluation."""

    radius_m: float = 0.05
    length_m: float = 0.25
    pressure_diff_pa: float = 45_000.0
    magnetic_field_t: float = 0.55
    omega_rad_s: float = 80.0
    delta_t_k: float = 180.0
    operating_temp_c: float = 160.0
    fluid_density_kg_m3: float = 920.0
    thermal_expansion_1_k: float = 8.0e-4
    target_filter_porosity: float = 0.55
    target_release_porosity: float = 0.08


VARIANTS: tuple[AuxeticVariant, ...] = (
    AuxeticVariant(
        name="nitinol_phi_braid",
        poisson_ratio=-0.72,
        relaxed_porosity=0.62,
        max_closure_fraction=0.78,
        modulus_mpa=28_000.0,
        density_kg_m3=6450.0,
        temperature_limit_c=420.0,
        abrasion_resistance=0.70,
        magnetic_response=0.35,
        recoverability=0.92,
        cost_index=0.86,
    ),
    AuxeticVariant(
        name="mae_silicone_ferrite_lattice",
        poisson_ratio=-0.55,
        relaxed_porosity=0.70,
        max_closure_fraction=0.68,
        modulus_mpa=4.5,
        density_kg_m3=1550.0,
        temperature_limit_c=190.0,
        abrasion_resistance=0.42,
        magnetic_response=0.95,
        recoverability=0.84,
        cost_index=0.40,
    ),
    AuxeticVariant(
        name="kevlar_sacrificial_reentrant",
        poisson_ratio=-0.48,
        relaxed_porosity=0.58,
        max_closure_fraction=0.54,
        modulus_mpa=70_000.0,
        density_kg_m3=1440.0,
        temperature_limit_c=260.0,
        abrasion_resistance=0.96,
        magnetic_response=0.18,
        recoverability=0.76,
        cost_index=0.52,
    ),
    AuxeticVariant(
        name="tpu_reentrant_lattice",
        poisson_ratio=-0.82,
        relaxed_porosity=0.74,
        max_closure_fraction=0.62,
        modulus_mpa=32.0,
        density_kg_m3=1210.0,
        temperature_limit_c=95.0,
        abrasion_resistance=0.50,
        magnetic_response=0.12,
        recoverability=0.88,
        cost_index=0.20,
    ),
    AuxeticVariant(
        name="carbon_peek_high_temp_lattice",
        poisson_ratio=-0.38,
        relaxed_porosity=0.52,
        max_closure_fraction=0.46,
        modulus_mpa=4200.0,
        density_kg_m3=1520.0,
        temperature_limit_c=315.0,
        abrasion_resistance=0.82,
        magnetic_response=0.10,
        recoverability=0.80,
        cost_index=0.66,
    ),
)


def build_actuation_grid(steps: int) -> tuple[float, ...]:
    """Return an inclusive 0..1 actuation grid."""

    if steps < 2:
        raise ValueError("actuation steps must be >= 2")
    return tuple(float(idx / (steps - 1)) for idx in range(steps))


def expand_variants(
    base_variants: Sequence[AuxeticVariant] = VARIANTS,
    *,
    variants_per_base: int = 1,
) -> tuple[AuxeticVariant, ...]:
    """Create a larger deterministic candidate board from bounded variants.

    This is a stress-test generator, not materials certification. It preserves
    each base material family while perturbing constants with a phi-phase so
    search modes can be compared on a larger algebraic board.
    """

    if variants_per_base < 1:
        raise ValueError("variants_per_base must be >= 1")
    if variants_per_base == 1:
        return tuple(base_variants)

    phi = (1.0 + math.sqrt(5.0)) / 2.0
    expanded: list[AuxeticVariant] = []
    for base_idx, base in enumerate(base_variants):
        for idx in range(variants_per_base):
            if idx == 0:
                expanded.append(base)
                continue
            phase = 2.0 * math.pi * ((idx + 1) / phi + base_idx / (len(base_variants) + 1.0))
            phase2 = 2.0 * math.pi * ((idx + 1) / (phi * phi) + (base_idx + 1) / (len(base_variants) + 2.0))
            expanded.append(
                AuxeticVariant(
                    name=f"{base.name}_stress_{idx:02d}",
                    poisson_ratio=-clamp(abs(base.poisson_ratio) * (1.0 + 0.10 * math.sin(phase)), 0.20, 1.25),
                    relaxed_porosity=clamp(base.relaxed_porosity + 0.055 * math.sin(phase2), 0.18, 0.88),
                    max_closure_fraction=clamp(
                        base.max_closure_fraction + 0.070 * math.cos(phase),
                        0.20,
                        0.92,
                    ),
                    modulus_mpa=base.modulus_mpa * (1.0 + 0.18 * math.sin(phase + 0.40)),
                    density_kg_m3=base.density_kg_m3 * (1.0 + 0.10 * math.cos(phase2 - 0.20)),
                    temperature_limit_c=base.temperature_limit_c + 32.0 * math.sin(phase - 0.70),
                    abrasion_resistance=clamp(base.abrasion_resistance + 0.075 * math.cos(phase2), 0.05, 1.0),
                    magnetic_response=clamp(base.magnetic_response + 0.080 * math.sin(phase + phase2), 0.02, 1.0),
                    recoverability=clamp(base.recoverability + 0.050 * math.cos(phase - phase2), 0.05, 1.0),
                    cost_index=clamp(base.cost_index + 0.090 * math.sin(phase2 + 0.25), 0.02, 1.0),
                )
            )
    return tuple(expanded)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def auxetic_porosity(variant: AuxeticVariant, actuation_fraction: float) -> float:
    """Estimate open-area fraction under controlled closure actuation.

    The earlier discussion used Poisson ratio as the intuition. Here the
    simulator uses a control-level closure fraction so actuation monotonically
    closes the baffle-hose, which is the behavior we want to rank.
    """

    actuation = clamp(actuation_fraction, 0.0, 1.0)
    closure = clamp(variant.max_closure_fraction * actuation * abs(variant.poisson_ratio), 0.0, 0.94)
    return clamp(variant.relaxed_porosity * (1.0 - closure) ** 2, 0.005, variant.relaxed_porosity)


def cross_section_area(op: OperatingPoint) -> float:
    return math.pi * op.radius_m**2


def swept_volume(op: OperatingPoint) -> float:
    return cross_section_area(op) * op.length_m


def pressure_force(op: OperatingPoint) -> float:
    return op.pressure_diff_pa * cross_section_area(op)


def magnetic_force(variant: AuxeticVariant, op: OperatingPoint, actuation_fraction: float) -> float:
    area = cross_section_area(op)
    actuation_gain = 0.35 + 0.65 * clamp(actuation_fraction, 0.0, 1.0)
    return 1200.0 * variant.magnetic_response * op.magnetic_field_t**2 * area * actuation_gain


def inertia_force(op: OperatingPoint) -> float:
    mass = swept_volume(op) * op.fluid_density_kg_m3
    return mass * op.omega_rad_s**2 * op.radius_m


def thermal_force(op: OperatingPoint) -> float:
    volume = swept_volume(op)
    return op.thermal_expansion_1_k * op.delta_t_k * volume * op.fluid_density_kg_m3 * 9.81


def release_threshold(variant: AuxeticVariant, op: OperatingPoint, porosity: float) -> float:
    stiffness_n = variant.modulus_mpa * 1_000_000.0 * cross_section_area(op) * 4.0e-5
    closure_load = stiffness_n * clamp(1.0 - porosity, 0.0, 1.0)
    abrasion_bonus = 1.0 + 0.25 * variant.abrasion_resistance
    return max(1e-9, closure_load * abrasion_bonus)


def normalized(value: float, scale: float) -> float:
    return clamp(value / max(scale, 1e-9), 0.0, 1.0)


def feature_vector(values: Iterable[float], *, dim: int = DIM) -> tuple[float, ...]:
    vector = np.zeros(dim, dtype=float)
    packed = [float(value) for value in values]
    if len(packed) > dim:
        raise ValueError("too many feature values for MAHSS vector")
    vector[: len(packed)] = packed
    norm = float(np.linalg.norm(vector))
    if norm > 0:
        vector = vector / norm
    return tuple(float(x) for x in vector)


def mechanism_vectors(
    variant: AuxeticVariant,
    op: OperatingPoint,
    *,
    actuation_fraction: float,
) -> tuple[dict[str, tuple[float, ...]], dict[str, float]]:
    porosity = auxetic_porosity(variant, actuation_fraction)
    f_pressure = pressure_force(op)
    f_magnetic = magnetic_force(variant, op, actuation_fraction)
    f_inertia = inertia_force(op)
    f_thermal = thermal_force(op)
    f_total = f_pressure + f_magnetic + f_inertia + f_thermal
    threshold = release_threshold(variant, op, porosity)
    force_margin = f_total / threshold
    temp_headroom = clamp((variant.temperature_limit_c - op.operating_temp_c) / variant.temperature_limit_c, -1.0, 1.0)
    mass_index = normalized(variant.density_kg_m3, 7000.0)
    closure_fraction = clamp(1.0 - porosity / max(variant.relaxed_porosity, 1e-9), 0.0, 1.0)

    metrics = {
        "actuation_fraction": actuation_fraction,
        "porosity": porosity,
        "closure_fraction": closure_fraction,
        "pressure_force_n": f_pressure,
        "magnetic_force_n": f_magnetic,
        "inertia_force_n": f_inertia,
        "thermal_force_n": f_thermal,
        "total_force_n": f_total,
        "release_threshold_n": threshold,
        "force_margin": force_margin,
        "temperature_headroom": temp_headroom,
        "mass_index": mass_index,
    }

    vectors = {
        "flow_pressure": feature_vector(
            [
                normalized(f_pressure, 500.0),
                porosity,
                1.0 - abs(op.target_filter_porosity - porosity),
                closure_fraction,
            ]
        ),
        "magnetic_actuation": feature_vector(
            [
                variant.magnetic_response,
                normalized(f_magnetic, 5.0),
                actuation_fraction,
                closure_fraction,
            ]
        ),
        "auxetic_porosity": feature_vector(
            [
                abs(variant.poisson_ratio),
                variant.relaxed_porosity,
                porosity,
                closure_fraction,
                variant.recoverability,
            ]
        ),
        "thermal_inertia": feature_vector(
            [
                normalized(f_inertia, 300.0),
                normalized(f_thermal, 10.0),
                max(0.0, temp_headroom),
                1.0 - mass_index,
            ]
        ),
        "abrasion_sheath": feature_vector(
            [
                variant.abrasion_resistance,
                variant.recoverability,
                max(0.0, temp_headroom),
                1.0 - variant.cost_index,
            ]
        ),
    }
    return vectors, metrics


def objective_router(objective: str) -> dict[str, float]:
    routers: dict[str, dict[str, float]] = {
        "balanced": {
            "flow_pressure": 0.20,
            "magnetic_actuation": 0.18,
            "auxetic_porosity": 0.24,
            "thermal_inertia": 0.18,
            "abrasion_sheath": 0.20,
        },
        "filter": {
            "flow_pressure": 0.34,
            "magnetic_actuation": 0.10,
            "auxetic_porosity": 0.26,
            "thermal_inertia": 0.10,
            "abrasion_sheath": 0.20,
        },
        "release": {
            "flow_pressure": 0.12,
            "magnetic_actuation": 0.30,
            "auxetic_porosity": 0.26,
            "thermal_inertia": 0.22,
            "abrasion_sheath": 0.10,
        },
        "high_heat": {
            "flow_pressure": 0.12,
            "magnetic_actuation": 0.10,
            "auxetic_porosity": 0.18,
            "thermal_inertia": 0.32,
            "abrasion_sheath": 0.28,
        },
    }
    if objective not in routers:
        raise ValueError(f"unknown objective: {objective}")
    return routers[objective]


def objective_query(objective: str) -> tuple[float, ...]:
    seeds: Mapping[str, tuple[float, ...]] = {
        "balanced": (0.70, 0.60, 0.68, 0.60, 0.70),
        "filter": (0.95, 0.35, 0.75, 0.30, 0.70),
        "release": (0.45, 0.95, 0.85, 0.75, 0.45),
        "high_heat": (0.35, 0.40, 0.55, 0.95, 0.90),
    }
    return feature_vector(seeds[objective])


def candidate_key(variant: AuxeticVariant, actuation_fraction: float) -> str:
    return f"{variant.name}@{actuation_fraction:.6f}"


def candidate_sketch_vector(
    variant: AuxeticVariant,
    op: OperatingPoint,
    *,
    objective: str,
    actuation_fraction: float,
) -> tuple[float, ...]:
    """Cheap Tang-style preselection sketch before full MAHSS scoring.

    The sketch superposes mechanism vectors with the objective router, then
    boosts candidates whose sketch points toward the objective query. Its
    squared norm becomes the classical length-square sampling weight. This is
    the dequantized "measurement" step: promising candidates are more likely to
    be folded/unbound, while exhaustive mode remains available for audit.
    """

    vectors, _metrics = mechanism_vectors(variant, op, actuation_fraction=actuation_fraction)
    router = objective_router(objective)
    sketch = np.zeros(DIM, dtype=float)
    for name in MECHANISMS:
        sketch += router[name] * np.asarray(vectors[name], dtype=float)
    query = np.asarray(objective_query(objective), dtype=float)
    alignment = max(0.0, float(np.dot(l2_normalize(sketch), l2_normalize(query))))
    boosted = sketch * (1.0 + alignment)
    return tuple(float(x) for x in boosted)


def select_length_square_candidates(
    candidates: Sequence[tuple[AuxeticVariant, float]],
    op: OperatingPoint,
    *,
    objective: str,
    sample_budget: int,
    sample_seed: int,
    sampling_power: float = 2.0,
) -> tuple[list[tuple[AuxeticVariant, float]], dict[str, float]]:
    """Select candidates by Tang-style squared-length sampling.

    The highest-probability sketch is always retained, then the rest of the
    budget is sampled without replacement from the length-square distribution.
    """

    if sample_budget <= 0:
        raise ValueError("sample_budget must be > 0")
    if sample_budget >= len(candidates):
        sketches = {
            candidate_key(variant, actuation): candidate_sketch_vector(
                variant,
                op,
                objective=objective,
                actuation_fraction=actuation,
            )
            for variant, actuation in candidates
        }
        return list(candidates), length_square_probabilities(sketches, dim=DIM, power=sampling_power)

    sketches = {
        candidate_key(variant, actuation): candidate_sketch_vector(
            variant,
            op,
            objective=objective,
            actuation_fraction=actuation,
        )
        for variant, actuation in candidates
    }
    probabilities = length_square_probabilities(sketches, dim=DIM, power=sampling_power)
    top_key = max(probabilities, key=probabilities.get)
    remaining_keys = [key for key in probabilities if key != top_key]
    remaining_budget = min(sample_budget - 1, len(remaining_keys))
    selected_keys = {top_key}
    if remaining_budget > 0:
        weights = np.asarray([probabilities[key] for key in remaining_keys], dtype=float)
        weights = weights / float(np.sum(weights))
        rng = np.random.default_rng(sample_seed)
        sampled = rng.choice(remaining_keys, size=remaining_budget, replace=False, p=weights)
        selected_keys.update(str(key) for key in sampled)
    selected = [
        (variant, actuation)
        for variant, actuation in candidates
        if candidate_key(variant, actuation) in selected_keys
    ]
    return selected, probabilities


def select_length_square_beam_candidates(
    candidates: Sequence[tuple[AuxeticVariant, float]],
    op: OperatingPoint,
    *,
    objective: str,
    sample_budget: int,
    sampling_power: float = 2.0,
) -> tuple[list[tuple[AuxeticVariant, float]], dict[str, float]]:
    """Select the top cheap sketches by squared-length probability."""

    if sample_budget <= 0:
        raise ValueError("sample_budget must be > 0")
    sketches = {
        candidate_key(variant, actuation): candidate_sketch_vector(
            variant,
            op,
            objective=objective,
            actuation_fraction=actuation,
        )
        for variant, actuation in candidates
    }
    probabilities = length_square_probabilities(sketches, dim=DIM, power=sampling_power)
    selected_keys = {
        key
        for key, _probability in sorted(probabilities.items(), key=lambda item: item[1], reverse=True)[:sample_budget]
    }
    selected = [
        (variant, actuation)
        for variant, actuation in candidates
        if candidate_key(variant, actuation) in selected_keys
    ]
    return selected, probabilities


def select_radial_power_candidates(
    candidates: Sequence[tuple[AuxeticVariant, float]],
    op: OperatingPoint,
    *,
    objective: str,
    sample_budget: int,
    sample_seed: int,
    path_history: Sequence[str] = (),
    base_power: float = 2.0,
    radial_gain: float = 0.125,
    beam: bool = False,
) -> tuple[list[tuple[AuxeticVariant, float]], dict[str, float], dict[str, dict[str, float]]]:
    """Select candidates by adaptive radial exponent probabilities."""

    if sample_budget <= 0:
        raise ValueError("sample_budget must be > 0")
    sketches = {
        candidate_key(variant, actuation): candidate_sketch_vector(
            variant,
            op,
            objective=objective,
            actuation_fraction=actuation,
        )
        for variant, actuation in candidates
    }
    profile = radial_power_profile(
        sketches,
        objective_query(objective),
        dim=DIM,
        path_history=path_history,
        base_power=base_power,
        radial_gain=radial_gain,
    )
    probabilities = {key: row["probability"] for key, row in profile.items()}
    if sample_budget >= len(candidates):
        return list(candidates), probabilities, profile

    if beam:
        selected_keys = {
            key for key, _ in sorted(probabilities.items(), key=lambda item: item[1], reverse=True)[:sample_budget]
        }
    else:
        top_key = max(probabilities, key=probabilities.get)
        remaining_keys = [key for key in probabilities if key != top_key]
        remaining_budget = min(sample_budget - 1, len(remaining_keys))
        selected_keys = {top_key}
        if remaining_budget > 0:
            weights = np.asarray([probabilities[key] for key in remaining_keys], dtype=float)
            weights = weights / float(np.sum(weights))
            rng = np.random.default_rng(sample_seed)
            sampled = rng.choice(remaining_keys, size=remaining_budget, replace=False, p=weights)
            selected_keys.update(str(key) for key in sampled)

    selected = [
        (variant, actuation)
        for variant, actuation in candidates
        if candidate_key(variant, actuation) in selected_keys
    ]
    return selected, probabilities, profile


def select_uniform_candidates(
    candidates: Sequence[tuple[AuxeticVariant, float]],
    *,
    sample_budget: int,
    sample_seed: int,
) -> list[tuple[AuxeticVariant, float]]:
    """Industry-standard seeded uniform baseline for budgeted search."""

    if sample_budget <= 0:
        raise ValueError("sample_budget must be > 0")
    if sample_budget >= len(candidates):
        return list(candidates)
    rng = np.random.default_rng(sample_seed)
    idxs = rng.choice(len(candidates), size=sample_budget, replace=False)
    return [candidates[int(idx)] for idx in sorted(idxs)]


def select_morton_stride_candidates(
    candidates: Sequence[tuple[AuxeticVariant, float]],
    *,
    sample_budget: int,
    variant_order: Sequence[str],
    actuation_values: Sequence[float],
) -> tuple[list[tuple[AuxeticVariant, float]], dict[str, object]]:
    """Select evenly spaced representatives along Morton/Z-order path."""

    if sample_budget <= 0:
        raise ValueError("sample_budget must be > 0")
    variant_index = {name: idx for idx, name in enumerate(variant_order)}
    actuation_index = {float(value): idx for idx, value in enumerate(actuation_values)}
    bits = max(bits_for_cardinality(len(variant_order)), bits_for_cardinality(len(actuation_values)))
    ordered = sorted(
        candidates,
        key=lambda pair: morton_encode(
            (variant_index[pair[0].name], actuation_index[float(pair[1])]),
            bits=bits,
        ),
    )
    if sample_budget >= len(ordered):
        selected = ordered
    elif sample_budget == 1:
        selected = [ordered[len(ordered) // 2]]
    else:
        idxs = sorted(
            {
                round(idx * (len(ordered) - 1) / (sample_budget - 1))
                for idx in range(sample_budget)
            }
        )
        selected = [ordered[int(idx)] for idx in idxs]
    telemetry = {
        "schema_version": "scbe_morton_stride_selection_v1",
        "bits": bits,
        "ordered_candidate_count": len(ordered),
        "selected_keys": [candidate_key(variant, actuation) for variant, actuation in selected],
    }
    return selected, telemetry


def select_polar_beam_candidates(
    candidates: Sequence[tuple[AuxeticVariant, float]],
    op: OperatingPoint,
    *,
    objective: str,
    sample_budget: int,
    sampling_power: float = 2.0,
) -> tuple[list[tuple[AuxeticVariant, float]], dict[str, float], dict[str, dict[str, float]]]:
    """Select candidates from dual positive/negative polar search surfaces."""

    if sample_budget <= 0:
        raise ValueError("sample_budget must be > 0")
    query = np.asarray(objective_query(objective), dtype=float)
    sketches: dict[str, tuple[float, ...]] = {}
    for variant, actuation in candidates:
        base = np.asarray(
            candidate_sketch_vector(variant, op, objective=objective, actuation_fraction=actuation),
            dtype=float,
        )
        centered = base - query
        signed = base * np.sign(centered + 1e-12)
        sketches[candidate_key(variant, actuation)] = tuple(float(x) for x in signed)

    polar = polar_vector_probabilities(sketches, dim=DIM, power=sampling_power)
    combined = {
        key: 0.5 * row["positive_probability"] + 0.5 * row["negative_probability"] + 0.05 * row["contrast"]
        for key, row in polar.items()
    }
    total = sum(combined.values())
    probabilities = {key: value / total for key, value in combined.items()}
    selected_keys = {
        key for key, _ in sorted(probabilities.items(), key=lambda item: item[1], reverse=True)[:sample_budget]
    }
    selected = [
        (variant, actuation)
        for variant, actuation in candidates
        if candidate_key(variant, actuation) in selected_keys
    ]
    return selected, probabilities, polar


def select_asymmetric_well_candidates(
    candidates: Sequence[tuple[AuxeticVariant, float]],
    op: OperatingPoint,
    *,
    objective: str,
    sample_budget: int,
    beta: float = 0.25,
    negative_gain: float = 1.0,
    sampling_power: float = 2.0,
) -> tuple[list[tuple[AuxeticVariant, float]], dict[str, float], dict[str, dict[str, float]]]:
    """Select by a target-centered asymmetric potential well.

    This is the "can be negative but prefers positive" search surface. The
    signed space is the candidate residual against the objective query; positive
    residuals pass normally, while negative residuals are compressed instead of
    hard-clipped.
    """

    if sample_budget <= 0:
        raise ValueError("sample_budget must be > 0")
    sketches = {
        candidate_key(variant, actuation): candidate_sketch_vector(
            variant,
            op,
            objective=objective,
            actuation_fraction=actuation,
        )
        for variant, actuation in candidates
    }
    profile = asymmetric_well_probabilities(
        sketches,
        objective_query(objective),
        dim=DIM,
        beta=beta,
        negative_gain=negative_gain,
        power=sampling_power,
    )
    probabilities = {key: row["probability"] for key, row in profile.items()}
    selected_keys = {
        key for key, _ in sorted(probabilities.items(), key=lambda item: item[1], reverse=True)[:sample_budget]
    }
    selected = [
        (variant, actuation)
        for variant, actuation in candidates
        if candidate_key(variant, actuation) in selected_keys
    ]
    return selected, probabilities, profile


def constructive_dissonance_profile(
    candidates: Sequence[tuple[AuxeticVariant, float]],
    op: OperatingPoint,
    *,
    objective: str,
) -> dict[str, dict[str, float]]:
    """Score useful disagreement between mechanism views.

    Constructive dissonance is not maximum disagreement. It is disagreement
    that still has a shared direction toward the query. Destructive dissonance
    is high spread with low query alignment, and should be pruned.
    """

    query = np.asarray(objective_query(objective), dtype=float)
    router = objective_router(objective)
    profile: dict[str, dict[str, float]] = {}
    for variant, actuation in candidates:
        vectors, _metrics = mechanism_vectors(variant, op, actuation_fraction=actuation)
        normalized_views = np.vstack([l2_normalize(np.asarray(vectors[name], dtype=float)) for name in MECHANISMS])
        alignments = np.asarray([max(0.0, float(np.dot(row, l2_normalize(query)))) for row in normalized_views])
        centroid = l2_normalize(np.average(normalized_views, axis=0, weights=[router[name] for name in MECHANISMS]))
        centroid_alignment = max(0.0, float(np.dot(centroid, l2_normalize(query))))
        spread = float(np.mean(np.linalg.norm(normalized_views - centroid, axis=1)))
        alignment_mean = float(np.mean(alignments))
        alignment_floor = float(np.min(alignments))
        destructive = spread * (1.0 - centroid_alignment)
        constructive = spread * (0.50 * centroid_alignment + 0.35 * alignment_mean + 0.15 * alignment_floor)
        score = constructive - 0.5 * destructive
        profile[candidate_key(variant, actuation)] = {
            "spread": spread,
            "centroid_alignment": centroid_alignment,
            "alignment_mean": alignment_mean,
            "alignment_floor": alignment_floor,
            "constructive_dissonance": constructive,
            "destructive_dissonance": destructive,
            "score": score,
        }
    return profile


def select_constructive_dissonance_candidates(
    candidates: Sequence[tuple[AuxeticVariant, float]],
    op: OperatingPoint,
    *,
    objective: str,
    sample_budget: int,
) -> tuple[list[tuple[AuxeticVariant, float]], dict[str, float], dict[str, dict[str, float]]]:
    """Prune to candidates with useful mechanism disagreement."""

    if sample_budget <= 0:
        raise ValueError("sample_budget must be > 0")
    profile = constructive_dissonance_profile(candidates, op, objective=objective)
    min_score = min(row["score"] for row in profile.values())
    shifted = {key: row["score"] - min_score + 1e-9 for key, row in profile.items()}
    total = sum(shifted.values())
    probabilities = {key: value / total for key, value in shifted.items()}
    selected_keys = {
        key for key, _ in sorted(profile.items(), key=lambda item: item[1]["score"], reverse=True)[:sample_budget]
    }
    selected = [
        (variant, actuation)
        for variant, actuation in candidates
        if candidate_key(variant, actuation) in selected_keys
    ]
    return selected, probabilities, profile


def select_algebraic_hybrid_candidates(
    candidates: Sequence[tuple[AuxeticVariant, float]],
    op: OperatingPoint,
    *,
    objective: str,
    sample_budget: int,
    variant_order: Sequence[str],
    actuation_values: Sequence[float],
    sampling_power: float = 2.125,
    radial_gain: float = 0.125,
    path_history: Sequence[str] = (),
) -> tuple[list[tuple[AuxeticVariant, float]], dict[str, float], dict[str, object]]:
    """One algebraic selector combining the useful search signals.

    Score components:
    - Morton index: reversible origin/path coordinate, used only as a locality
      tie-breaker;
    - Tang/radial probability: energy plus query/history steering;
    - constructive dissonance: mechanism disagreement that still points toward
      the query;
    - coarse-group coverage: keep variant coverage before spending fine evals.
    """

    if sample_budget <= 0:
        raise ValueError("sample_budget must be > 0")
    variant_index = {name: idx for idx, name in enumerate(variant_order)}
    actuation_index = {float(value): idx for idx, value in enumerate(actuation_values)}
    bits = max(bits_for_cardinality(len(variant_order)), bits_for_cardinality(len(actuation_values)))
    sketches = {
        candidate_key(variant, actuation): candidate_sketch_vector(
            variant,
            op,
            objective=objective,
            actuation_fraction=actuation,
        )
        for variant, actuation in candidates
    }
    radial = radial_power_profile(
        sketches,
        objective_query(objective),
        dim=DIM,
        path_history=path_history,
        base_power=sampling_power,
        radial_gain=radial_gain,
    )
    dissonance = constructive_dissonance_profile(candidates, op, objective=objective)
    morton_values = {
        candidate_key(variant, actuation): morton_encode(
            (variant_index[variant.name], actuation_index[float(actuation)]),
            bits=bits,
        )
        for variant, actuation in candidates
    }
    max_morton = max(morton_values.values()) or 1
    max_constructive = max(max(0.0, row["score"]) for row in dissonance.values()) or 1.0
    raw_scores: dict[str, float] = {}
    for variant, actuation in candidates:
        key = candidate_key(variant, actuation)
        radial_prob = radial[key]["probability"]
        constructive = max(0.0, dissonance[key]["score"]) / max_constructive
        locality = 1.0 - (morton_values[key] / max_morton)
        coverage = 1.0 / (1.0 + variant_index[variant.name])
        raw_scores[key] = 0.90 * radial_prob + 0.08 * constructive + 0.01 * coverage + 0.01 * locality

    total = sum(raw_scores.values())
    probabilities = {key: value / total for key, value in raw_scores.items()}

    selected_keys = {
        key for key, _score in sorted(raw_scores.items(), key=lambda item: item[1], reverse=True)[:sample_budget]
    }

    selected = [
        (variant, actuation)
        for variant, actuation in candidates
        if candidate_key(variant, actuation) in selected_keys
    ]
    telemetry = {
        "schema_version": "scbe_mahss_algebraic_hybrid_selector_v1",
        "bits": bits,
        "selected_keys": [candidate_key(variant, actuation) for variant, actuation in selected],
        "top_scores": {
            key: round(value, 12)
            for key, value in sorted(raw_scores.items(), key=lambda item: item[1], reverse=True)[: min(8, len(raw_scores))]
        },
        "formula": "0.90*radial_probability + 0.08*normalized_constructive_dissonance + 0.01*coverage + 0.01*morton_locality",
    }
    return selected, probabilities, telemetry


def select_mirror_beam_candidates(
    candidates: Sequence[tuple[AuxeticVariant, float]],
    op: OperatingPoint,
    *,
    objective: str,
    sample_budget: int,
    curvature: float = 1.0,
) -> tuple[list[tuple[AuxeticVariant, float]], dict[str, dict[str, float]]]:
    """One-pass hyperbolic-resonance candidate selection.

    Projects every candidate sketch into the Poincare ball at curvature c
    (the bent space), computes hyperbolic distance from the query in a
    single batched pass (the beam), then returns the top-K candidates by
    smallest distance (the speck of reflection). Because hyperbolic
    distance grows exponentially with Euclidean distance near the ball
    boundary, the strongest match separates from near-misses exponentially:
    the right answer reflects brightest without iterative beam refinement.

    Cost: O(N * d) for projection + distance + ranking, then O(K * score_cost)
    for full scoring of the top-K. No random sampling, no path history,
    no sequential beam refinement. Pure batched algebra over a fixed
    bent-space metric.
    """

    if sample_budget <= 0:
        raise ValueError("sample_budget must be > 0")
    if curvature <= 0:
        raise ValueError("curvature must be > 0")

    sketches = {
        candidate_key(variant, actuation): candidate_sketch_vector(
            variant,
            op,
            objective=objective,
            actuation_fraction=actuation,
        )
        for variant, actuation in candidates
    }

    sqrt_c = math.sqrt(curvature)

    def _project_to_ball(v: np.ndarray) -> np.ndarray:
        norm = float(np.linalg.norm(v))
        if norm == 0.0:
            return np.zeros_like(v)
        scale = math.tanh(sqrt_c * norm) / (sqrt_c * norm)
        return v * scale

    query_vec = np.asarray(objective_query(objective), dtype=float)
    q_ball = _project_to_ball(query_vec)
    q_norm_sq = float(np.dot(q_ball, q_ball))

    distances: dict[str, float] = {}
    raw_norms: dict[str, float] = {}
    for key, sketch in sketches.items():
        s_arr = np.asarray(sketch, dtype=float)
        s_ball = _project_to_ball(s_arr)
        s_norm_sq = float(np.dot(s_ball, s_ball))
        diff = s_ball - q_ball
        diff_sq = float(np.dot(diff, diff))
        denom = max(1e-12, (1.0 - s_norm_sq) * (1.0 - q_norm_sq))
        cosh_arg = max(1.0, 1.0 + 2.0 * diff_sq / denom)
        distances[key] = math.acosh(cosh_arg)
        raw_norms[key] = float(np.linalg.norm(s_arr))

    selected_keys = {
        key for key, _ in sorted(distances.items(), key=lambda item: item[1])[:sample_budget]
    }
    selected = [
        (variant, actuation)
        for variant, actuation in candidates
        if candidate_key(variant, actuation) in selected_keys
    ]

    telemetry = {
        key: {
            "hyperbolic_distance": round(distances[key], 9),
            "reflection_amplitude": round(math.exp(-distances[key]), 9),
            "euclidean_norm": round(raw_norms[key], 9),
        }
        for key in distances
    }
    return selected, telemetry


def select_multigrid_candidates(
    candidates: Sequence[tuple[AuxeticVariant, float]],
    *,
    coarse_actuation: float = 0.5,
) -> tuple[list[tuple[AuxeticVariant, float]], dict[str, list[tuple[AuxeticVariant, float]]]]:
    """Pick the coarse-grid representative for each variant.

    Multigrid first pass: one actuation per variant (the one closest to
    ``coarse_actuation``). The fine-pass selector consumes the per-variant
    grouping returned alongside.
    """

    by_variant: dict[str, list[tuple[AuxeticVariant, float]]] = {}
    for variant, actuation in candidates:
        by_variant.setdefault(variant.name, []).append((variant, actuation))
    coarse_picks: list[tuple[AuxeticVariant, float]] = []
    for group in by_variant.values():
        pick = min(group, key=lambda pair: abs(pair[1] - coarse_actuation))
        coarse_picks.append(pick)
    return coarse_picks, by_variant


def score_candidate(
    variant: AuxeticVariant,
    op: OperatingPoint,
    *,
    objective: str,
    actuation_fraction: float,
) -> dict[str, object]:
    vectors, metrics = mechanism_vectors(variant, op, actuation_fraction=actuation_fraction)
    result = build_mahss(
        vectors,
        objective_query(objective),
        config=MAHSSConfig(dim=DIM, fold_strength=0.35, router_temperature=0.8),
        router_weights=objective_router(objective),
    )

    porosity = float(metrics["porosity"])
    temp_headroom = float(metrics["temperature_headroom"])
    filter_fit = 1.0 - abs(op.target_filter_porosity - porosity)
    release_fit = 1.0 - abs(op.target_release_porosity - porosity)
    force_score = normalized(math.log1p(max(0.0, float(metrics["force_margin"]))), 4.0)
    durability = (
        0.40 * variant.abrasion_resistance
        + 0.25 * variant.recoverability
        + 0.25 * max(0.0, temp_headroom)
        + 0.10 * (1.0 - normalized(variant.density_kg_m3, 7000.0))
    )
    cost_penalty = 0.08 * variant.cost_index
    temp_violation_penalty = abs(min(0.0, temp_headroom))
    strain_penalty = 0.35 * result.cross_manifold_strain

    if objective == "filter":
        objective_score = 0.40 * filter_fit + 0.25 * durability + 0.20 * force_score + 0.15 * result.peak_margin
        objective_score -= 0.12 * temp_violation_penalty
    elif objective == "release":
        objective_score = 0.34 * release_fit + 0.30 * force_score + 0.18 * durability + 0.18 * result.peak_margin
        objective_score -= 0.14 * temp_violation_penalty
    elif objective == "high_heat":
        objective_score = 0.42 * durability + 0.23 * force_score + 0.20 * release_fit + 0.15 * result.peak_margin
        objective_score -= 0.62 * temp_violation_penalty
    else:
        objective_score = (
            0.24 * filter_fit + 0.22 * release_fit + 0.22 * durability + 0.20 * force_score + 0.12 * result.peak_margin
        )
        objective_score -= 0.10 * temp_violation_penalty

    score = objective_score - cost_penalty - strain_penalty
    return {
        "variant": variant.name,
        "score": round(float(score), 9),
        "objective_score": round(float(objective_score), 9),
        "metrics": {key: round(float(value), 9) for key, value in metrics.items()},
        "mahss": {
            "schema_version": result.schema_version,
            "selected_mechanism": result.selected_mechanism,
            "peak_margin": round(float(result.peak_margin), 9),
            "cross_manifold_strain": round(float(result.cross_manifold_strain), 9),
            "illumination": result.illumination,
            "router_weights": result.router_weights,
        },
    }


def run_simulation(
    *,
    objective: str = "balanced",
    op: OperatingPoint | None = None,
    variants: Iterable[AuxeticVariant] = VARIANTS,
    actuation_grid: Iterable[float] = (0.0, 0.25, 0.5, 0.75, 1.0),
    search_mode: str = "exhaustive",
    sample_budget: int | None = None,
    sample_seed: int = 17,
    sampling_power: float = 2.0,
    radial_gain: float = 0.125,
    path_history: Sequence[str] = (),
) -> dict[str, object]:
    operating_point = op or OperatingPoint()
    variant_list = tuple(variants)
    actuation_values = tuple(float(value) for value in actuation_grid)
    candidate_pool = [(variant, actuation) for variant in variant_list for actuation in actuation_values]
    sampling_probabilities: dict[str, float] | None = None
    radial_profile: dict[str, dict[str, float]] | None = None
    polar_profile: dict[str, dict[str, float]] | None = None
    asymmetric_profile: dict[str, dict[str, float]] | None = None
    dissonance_profile: dict[str, dict[str, float]] | None = None
    multigrid_telemetry: dict[str, object] | None = None
    morton_telemetry: dict[str, object] | None = None
    hybrid_telemetry: dict[str, object] | None = None
    mirror_telemetry: dict[str, dict[str, float]] | None = None
    if search_mode == "multigrid":
        top_k_variants = max(1, int(sample_budget)) if sample_budget else 2
        coarse_picks, _by_variant = select_multigrid_candidates(candidate_pool)
        coarse_scored: list[tuple[AuxeticVariant, float, dict[str, object]]] = []
        for variant, actuation_fraction in coarse_picks:
            result = score_candidate(
                variant,
                operating_point,
                objective=objective,
                actuation_fraction=float(actuation_fraction),
            )
            coarse_scored.append((variant, float(actuation_fraction), result))
        coarse_scored.sort(key=lambda row: float(row[2]["score"]), reverse=True)
        top_names = {row[0].name for row in coarse_scored[:top_k_variants]}
        coarse_keys = {(row[0].name, row[1]) for row in coarse_scored}
        fine_to_score = [
            (variant, actuation_fraction)
            for variant, actuation_fraction in candidate_pool
            if variant.name in top_names and (variant.name, actuation_fraction) not in coarse_keys
        ]
        fine_scored = [
            score_candidate(
                variant,
                operating_point,
                objective=objective,
                actuation_fraction=float(actuation_fraction),
            )
            for variant, actuation_fraction in fine_to_score
        ]
        ranked = [row[2] for row in coarse_scored] + fine_scored
        ranked.sort(key=lambda item: float(item["score"]), reverse=True)
        multigrid_telemetry = {
            "coarse_pass": [
                {
                    "variant": row[0].name,
                    "actuation": row[1],
                    "score": round(float(row[2]["score"]), 9),
                }
                for row in coarse_scored
            ],
            "top_k": top_k_variants,
            "top_variants": sorted(top_names),
            "coarse_evaluations": len(coarse_scored),
            "fine_evaluations": len(fine_scored),
            "total_evaluations": len(coarse_scored) + len(fine_scored),
            "exhaustive_budget": len(candidate_pool),
        }
        return {
            "schema_version": SCHEMA_VERSION,
            "objective": objective,
            "operating_point": asdict(operating_point),
            "mechanisms": list(MECHANISMS),
            "variant_count": len(variant_list),
            "search_mode": search_mode,
            "candidate_pool_count": len(candidate_pool),
            "candidate_count": len(ranked),
            "evaluated_candidate_count": len(ranked),
            "length_square_sampling": {
                "enabled": False,
                "sampling_power": sampling_power,
                "radial_gain": None,
                "sample_budget": sample_budget,
                "sample_seed": sample_seed,
                "path_history": list(path_history),
                "probabilities": {},
                "radial_hints": {},
            },
            "multigrid": multigrid_telemetry,
            "top_design": ranked[0],
            "ranked": ranked,
        }
    if search_mode == "exhaustive":
        selected_candidates = candidate_pool
    elif search_mode == "uniform_sampled":
        budget = sample_budget if sample_budget is not None else max(1, int(math.ceil(math.sqrt(len(candidate_pool)))))
        selected_candidates = select_uniform_candidates(candidate_pool, sample_budget=budget, sample_seed=sample_seed)
    elif search_mode == "morton_stride":
        budget = sample_budget if sample_budget is not None else max(1, int(math.ceil(math.sqrt(len(candidate_pool)))))
        selected_candidates, morton_telemetry = select_morton_stride_candidates(
            candidate_pool,
            sample_budget=budget,
            variant_order=[variant.name for variant in variant_list],
            actuation_values=actuation_values,
        )
    elif search_mode == "tang_sampled":
        budget = sample_budget if sample_budget is not None else max(1, int(math.ceil(math.sqrt(len(candidate_pool)))))
        selected_candidates, sampling_probabilities = select_length_square_candidates(
            candidate_pool,
            operating_point,
            objective=objective,
            sample_budget=budget,
            sample_seed=sample_seed,
            sampling_power=sampling_power,
        )
    elif search_mode == "tang_beam":
        budget = sample_budget if sample_budget is not None else max(1, int(math.ceil(math.sqrt(len(candidate_pool)))))
        selected_candidates, sampling_probabilities = select_length_square_beam_candidates(
            candidate_pool,
            operating_point,
            objective=objective,
            sample_budget=budget,
            sampling_power=sampling_power,
        )
    elif search_mode in {"radial_sampled", "radial_beam"}:
        budget = sample_budget if sample_budget is not None else max(1, int(math.ceil(math.sqrt(len(candidate_pool)))))
        selected_candidates, sampling_probabilities, radial_profile = select_radial_power_candidates(
            candidate_pool,
            operating_point,
            objective=objective,
            sample_budget=budget,
            sample_seed=sample_seed,
            path_history=path_history,
            base_power=sampling_power,
            radial_gain=radial_gain,
            beam=search_mode == "radial_beam",
        )
    elif search_mode == "polar_beam":
        budget = sample_budget if sample_budget is not None else max(1, int(math.ceil(math.sqrt(len(candidate_pool)))))
        selected_candidates, sampling_probabilities, polar_profile = select_polar_beam_candidates(
            candidate_pool,
            operating_point,
            objective=objective,
            sample_budget=budget,
            sampling_power=sampling_power,
        )
    elif search_mode == "asymmetric_well":
        budget = sample_budget if sample_budget is not None else max(1, int(math.ceil(math.sqrt(len(candidate_pool)))))
        selected_candidates, sampling_probabilities, asymmetric_profile = select_asymmetric_well_candidates(
            candidate_pool,
            operating_point,
            objective=objective,
            sample_budget=budget,
            sampling_power=sampling_power,
        )
    elif search_mode == "dissonance_pruned":
        budget = sample_budget if sample_budget is not None else max(1, int(math.ceil(math.sqrt(len(candidate_pool)))))
        selected_candidates, sampling_probabilities, dissonance_profile = select_constructive_dissonance_candidates(
            candidate_pool,
            operating_point,
            objective=objective,
            sample_budget=budget,
        )
    elif search_mode == "algebraic_hybrid":
        budget = sample_budget if sample_budget is not None else max(1, int(math.ceil(math.sqrt(len(candidate_pool)))))
        selected_candidates, sampling_probabilities, hybrid_telemetry = select_algebraic_hybrid_candidates(
            candidate_pool,
            operating_point,
            objective=objective,
            sample_budget=budget,
            variant_order=[variant.name for variant in variant_list],
            actuation_values=actuation_values,
            sampling_power=sampling_power,
            radial_gain=radial_gain,
            path_history=path_history,
        )
    elif search_mode == "mirror_beam":
        budget = sample_budget if sample_budget is not None else max(1, int(math.ceil(math.sqrt(len(candidate_pool)))))
        selected_candidates, mirror_telemetry = select_mirror_beam_candidates(
            candidate_pool,
            operating_point,
            objective=objective,
            sample_budget=budget,
        )
    else:
        raise ValueError(f"unknown search_mode: {search_mode}")

    ranked: list[dict[str, object]] = []
    for variant, actuation_fraction in selected_candidates:
        ranked.append(
            score_candidate(
                variant,
                operating_point,
                objective=objective,
                actuation_fraction=float(actuation_fraction),
            )
        )
    ranked.sort(key=lambda item: float(item["score"]), reverse=True)
    return {
        "schema_version": SCHEMA_VERSION,
        "objective": objective,
        "operating_point": asdict(operating_point),
        "mechanisms": list(MECHANISMS),
        "variant_count": len(variant_list),
        "search_mode": search_mode,
        "candidate_pool_count": len(candidate_pool),
        "candidate_count": len(ranked),
        "evaluated_candidate_count": len(ranked),
        "length_square_sampling": {
            "enabled": search_mode
            in {
                "tang_sampled",
                "tang_beam",
                "radial_sampled",
                "radial_beam",
                "polar_beam",
                "asymmetric_well",
                "dissonance_pruned",
                "algebraic_hybrid",
            },
            "sampling_power": sampling_power,
            "radial_gain": radial_gain if search_mode in {"radial_sampled", "radial_beam"} else None,
            "sample_budget": sample_budget,
            "sample_seed": sample_seed,
            "path_history": list(path_history),
            "probabilities": {
                key: round(value, 12)
                for key, value in sorted((sampling_probabilities or {}).items(), key=lambda item: item[1], reverse=True)
            },
            "radial_hints": {
                key: {
                    field: round(value, 12)
                    for field, value in row.items()
                    if field in {"alignment", "redundancy", "novelty", "quasicrystal_phase", "power", "probability"}
                }
                for key, row in sorted(
                    (radial_profile or {}).items(),
                    key=lambda item: item[1]["probability"],
                    reverse=True,
                )[: min(8, len(radial_profile or {}))]
            },
            "polar_hints": {
                key: {
                    field: round(value, 12)
                    for field, value in row.items()
                    if field
                    in {
                        "positive_probability",
                        "negative_probability",
                        "polarity",
                        "contrast",
                        "dual_entropy",
                    }
                }
                for key, row in sorted(
                    (polar_profile or {}).items(),
                    key=lambda item: item[1]["contrast"],
                    reverse=True,
                )[: min(8, len(polar_profile or {}))]
            },
            "dissonance_hints": {
                key: {
                    field: round(value, 12)
                    for field, value in row.items()
                    if field
                    in {
                        "spread",
                        "centroid_alignment",
                        "alignment_mean",
                        "alignment_floor",
                        "constructive_dissonance",
                        "destructive_dissonance",
                        "score",
                    }
                }
                for key, row in sorted(
                    (dissonance_profile or {}).items(),
                    key=lambda item: item[1]["score"],
                    reverse=True,
                )[: min(8, len(dissonance_profile or {}))]
            },
            "asymmetric_hints": {
                key: {
                    field: round(value, 12)
                    for field, value in row.items()
                    if field
                    in {
                        "probability",
                        "transformed_norm",
                        "positive_residual_norm",
                        "negative_residual_norm",
                    }
                }
                for key, row in sorted(
                    (asymmetric_profile or {}).items(),
                    key=lambda item: item[1]["probability"],
                    reverse=True,
                )[: min(8, len(asymmetric_profile or {}))]
            },
        },
        "top_design": ranked[0],
        "morton": morton_telemetry,
        "algebraic_hybrid": hybrid_telemetry,
        "mirror": mirror_telemetry,
        "ranked": ranked,
    }


def write_report(report: Mapping[str, object], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compare_search_modes(
    *,
    objective: str = "balanced",
    sample_budget: int = 6,
    sample_seed: int = 17,
    variants: Iterable[AuxeticVariant] = VARIANTS,
    actuation_grid: Iterable[float] = (0.0, 0.25, 0.5, 0.75, 1.0),
) -> dict[str, object]:
    """Pure-math side-by-side search comparison.

    Baselines:
    - exhaustive: old full-grid proof mode;
    - uniform_sampled: common budgeted random-search baseline;
    - tang_beam_2: fixed Tang squared-length beam;
    - tang_beam_2_125: sharpened fixed-power beam;
    - radial_beam_2_125: path-aware adaptive radial exponent beam.
    """

    variant_list = tuple(variants)
    actuation_values = tuple(float(value) for value in actuation_grid)
    exhaustive = run_simulation(
        objective=objective,
        search_mode="exhaustive",
        variants=variant_list,
        actuation_grid=actuation_values,
    )
    best = exhaustive["top_design"]
    assert isinstance(best, dict)
    best_score = float(best["score"])
    baseline_history = [f"{best['variant']}@{best['metrics']['actuation_fraction']:.6f}"]
    runs = {
        "exhaustive": exhaustive,
        "uniform_sampled": run_simulation(
            objective=objective,
            search_mode="uniform_sampled",
            sample_budget=sample_budget,
            sample_seed=sample_seed,
            variants=variant_list,
            actuation_grid=actuation_values,
        ),
        "tang_beam_2": run_simulation(
            objective=objective,
            search_mode="tang_beam",
            sample_budget=sample_budget,
            sample_seed=sample_seed,
            sampling_power=2.0,
            variants=variant_list,
            actuation_grid=actuation_values,
        ),
        "tang_beam_2_125": run_simulation(
            objective=objective,
            search_mode="tang_beam",
            sample_budget=sample_budget,
            sample_seed=sample_seed,
            sampling_power=2.125,
            variants=variant_list,
            actuation_grid=actuation_values,
        ),
        "radial_beam_2_125": run_simulation(
            objective=objective,
            search_mode="radial_beam",
            sample_budget=sample_budget,
            sample_seed=sample_seed,
            sampling_power=2.125,
            radial_gain=0.125,
            path_history=baseline_history,
            variants=variant_list,
            actuation_grid=actuation_values,
        ),
        "polar_beam_2_125": run_simulation(
            objective=objective,
            search_mode="polar_beam",
            sample_budget=sample_budget,
            sample_seed=sample_seed,
            sampling_power=2.125,
            variants=variant_list,
            actuation_grid=actuation_values,
        ),
        "asymmetric_well_2_125": run_simulation(
            objective=objective,
            search_mode="asymmetric_well",
            sample_budget=sample_budget,
            sample_seed=sample_seed,
            sampling_power=2.125,
            variants=variant_list,
            actuation_grid=actuation_values,
        ),
        "morton_stride": run_simulation(
            objective=objective,
            search_mode="morton_stride",
            sample_budget=sample_budget,
            variants=variant_list,
            actuation_grid=actuation_values,
        ),
        "dissonance_pruned": run_simulation(
            objective=objective,
            search_mode="dissonance_pruned",
            sample_budget=sample_budget,
            variants=variant_list,
            actuation_grid=actuation_values,
        ),
        "algebraic_hybrid": run_simulation(
            objective=objective,
            search_mode="algebraic_hybrid",
            sample_budget=sample_budget,
            sampling_power=2.125,
            radial_gain=0.125,
            path_history=baseline_history,
            variants=variant_list,
            actuation_grid=actuation_values,
        ),
        "multigrid_top2": run_simulation(
            objective=objective,
            search_mode="multigrid",
            sample_budget=2,
            variants=variant_list,
            actuation_grid=actuation_values,
        ),
        "mirror_beam_c1": run_simulation(
            objective=objective,
            search_mode="mirror_beam",
            sample_budget=sample_budget,
            variants=variant_list,
            actuation_grid=actuation_values,
        ),
    }
    summary: dict[str, dict[str, object]] = {}
    for name, report in runs.items():
        top = report["top_design"]
        assert isinstance(top, dict)
        score = float(top["score"])
        summary[name] = {
            "top_variant": top["variant"],
            "top_actuation": top["metrics"]["actuation_fraction"],
            "top_score": round(score, 9),
            "score_regret_vs_exhaustive": round(best_score - score, 9),
            "evaluated_candidate_count": report["evaluated_candidate_count"],
        }
    return {
        "schema_version": "scbe_mahss_search_comparison_v1",
        "objective": objective,
        "sample_budget": sample_budget,
        "sample_seed": sample_seed,
        "candidate_pool_count": len(variant_list) * len(actuation_values),
        "variant_count": len(variant_list),
        "actuation_count": len(actuation_values),
        "exhaustive_best_score": round(best_score, 9),
        "summary": summary,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--objective", choices=("balanced", "filter", "release", "high_heat"), default="balanced")
    parser.add_argument(
        "--search-mode",
        choices=(
            "exhaustive",
            "uniform_sampled",
            "morton_stride",
            "dissonance_pruned",
            "algebraic_hybrid",
            "tang_sampled",
            "tang_beam",
            "radial_sampled",
            "radial_beam",
            "polar_beam",
            "asymmetric_well",
            "multigrid",
            "mirror_beam",
        ),
        default="exhaustive",
    )
    parser.add_argument(
        "--sample-budget",
        type=int,
        default=None,
        help="Candidate count for --search-mode tang_sampled. Default is ceil(sqrt(candidate pool)).",
    )
    parser.add_argument("--sample-seed", type=int, default=17, help="Deterministic seed for Tang-style sampling.")
    parser.add_argument("--sampling-power", type=float, default=2.0, help="Norm exponent for Tang/radial sampling.")
    parser.add_argument("--radial-gain", type=float, default=0.125, help="Adaptive radial exponent gain.")
    parser.add_argument(
        "--variants-per-base",
        type=int,
        default=1,
        help="Deterministically expand each base material family for large-board stress tests.",
    )
    parser.add_argument(
        "--actuation-steps",
        type=int,
        default=5,
        help="Inclusive 0..1 actuation grid size for stress tests.",
    )
    parser.add_argument(
        "--path-history",
        default="",
        help="Comma-separated candidate keys already explored, e.g. name@0.500000,name@0.750000.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/mahss_metamaterial/mahss_metamaterial_sim_v1.json"),
        help="JSON report path.",
    )
    parser.add_argument("--json", action="store_true", help="Print full JSON report.")
    parser.add_argument("--compare", action="store_true", help="Run side-by-side search baseline comparison.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    variants = expand_variants(variants_per_base=args.variants_per_base)
    actuation_grid = build_actuation_grid(args.actuation_steps)
    if args.compare:
        report = compare_search_modes(
            objective=args.objective,
            sample_budget=args.sample_budget or 6,
            sample_seed=args.sample_seed,
            variants=variants,
            actuation_grid=actuation_grid,
        )
        write_report(report, args.output)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(f"wrote {args.output}")
            for name, row in report["summary"].items():
                assert isinstance(row, dict)
                print(
                    f"{name}: top={row['top_variant']}@{row['top_actuation']} "
                    f"score={row['top_score']} regret={row['score_regret_vs_exhaustive']} "
                    f"evals={row['evaluated_candidate_count']}"
                )
        return 0

    report = run_simulation(
        objective=args.objective,
        search_mode=args.search_mode,
        sample_budget=args.sample_budget,
        sample_seed=args.sample_seed,
        sampling_power=args.sampling_power,
        radial_gain=args.radial_gain,
        variants=variants,
        actuation_grid=actuation_grid,
        path_history=tuple(part.strip() for part in args.path_history.split(",") if part.strip()),
    )
    write_report(report, args.output)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        top = report["top_design"]
        assert isinstance(top, dict)
        print(f"wrote {args.output}")
        print(f"top={top['variant']} score={top['score']} objective={args.objective} search={args.search_mode}")
        metrics = top["metrics"]
        assert isinstance(metrics, dict)
        print(f"porosity={metrics['porosity']} actuation={metrics['actuation_fraction']}")
        mahss = top["mahss"]
        assert isinstance(mahss, dict)
        print(f"mahss_selected={mahss['selected_mechanism']} strain={mahss['cross_manifold_strain']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
