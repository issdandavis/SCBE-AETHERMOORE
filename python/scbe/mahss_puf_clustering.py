"""PUF clustering analysis harness for the crypto-seeded Dynamo Core.

Software complement to the next physical-proof step: print N copies of
seed A and N copies of seed B, measure a response signal on each, and
verify that intra-identity distances stay below inter-identity
distances. The user's stated criterion::

    distance(Alice_copy1, Alice_copy2) < distance(Alice, Bob)

This harness:

1. Defines a measurement vector type (anything mappable to ``np.ndarray``).
2. Simulates measurement with Gaussian noise on the seeded prediction so
   we can probe the noise budget the printer/measurement must beat
   BEFORE physical parts return.
3. Reports pairwise distances, intra/inter aggregates, and a strict
   verdict (max_intra < min_inter) plus a soft verdict (mean_intra
   below mean_inter by k * std_inter).
4. Has measurement adapters for both the seeded ``AuxeticVariant``
   (high-level: porosity, modulus, density, etc.) and the geometric
   perturbation field (low-level: per-ridge mm displacements).

When real measurements arrive, drop them into ``cluster_report`` directly
— skip the simulation step. The verdict logic is identical.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Callable, Iterable, Mapping

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from python.scbe.mahss_crypto_lattice import (  # noqa: E402
    AuxeticVariant,
    apply_crypto_seed,
    derive_perturbation_field,
)


# --------------------------------------------------------------------------
# Measurement adapters: what numeric vector represents one printed copy?
# --------------------------------------------------------------------------

# Numeric fields of an AuxeticVariant that vary under the perturbation.
# Order is fixed so all copies use the same coordinate system.
_VARIANT_MEASUREMENT_FIELDS: tuple[str, ...] = (
    "poisson_ratio",
    "relaxed_porosity",
    "max_closure_fraction",
    "modulus_mpa",
    "density_kg_m3",
    "temperature_limit_c",
    "abrasion_resistance",
    "magnetic_response",
    "recoverability",
    "cost_index",
)


def measurement_from_variant(variant: AuxeticVariant) -> np.ndarray:
    """Map a seeded variant to a fixed-length numeric vector.

    Used as the "predicted measurement" for a printed copy: simulator
    says this part should resonate at this modulus, have this density,
    etc. Real measurements would slot into the same vector layout."""

    return np.array(
        [getattr(variant, name) for name in _VARIANT_MEASUREMENT_FIELDS],
        dtype=float,
    )


def measurement_from_geometry(seed: int, num_ridges: int = 16, scale_mm: float = 0.5) -> np.ndarray:
    """Map a seed to its physical-displacement signature (mm).

    Used when the measurement axis is per-ridge dimensional readout
    (e.g. caliper / CMM / interferometric scan of the auxetic ridges).
    Lower-level than :func:`measurement_from_variant`."""

    field_unitless = derive_perturbation_field(seed, num_ridges, bound=0.05)
    return field_unitless * scale_mm


# --------------------------------------------------------------------------
# Simulation: prediction + noise
# --------------------------------------------------------------------------


def simulate_copies(
    seed: int,
    *,
    n_copies: int,
    measurement_fn: Callable[[int], np.ndarray],
    noise_sigma: float,
    rng: np.random.Generator | None = None,
) -> list[np.ndarray]:
    """Produce ``n_copies`` simulated measurements for one identity.

    ``noise_sigma`` is in the units of the measurement vector. Each
    coordinate is corrupted independently with a Gaussian of that std.
    For a real measurement run the noise model is whatever the metrology
    produces — replace this with the actual data and skip the function."""

    if n_copies <= 0:
        raise ValueError(f"n_copies must be positive, got {n_copies}")
    if noise_sigma < 0:
        raise ValueError(f"noise_sigma must be non-negative, got {noise_sigma}")

    rng = rng if rng is not None else np.random.default_rng(seed=seed)
    base = measurement_fn(seed)
    if noise_sigma == 0.0:
        return [base.copy() for _ in range(n_copies)]
    return [base + rng.normal(0.0, noise_sigma, size=base.shape) for _ in range(n_copies)]


# --------------------------------------------------------------------------
# Distance + clustering verdict
# --------------------------------------------------------------------------


def _pairwise(measurements: list[np.ndarray]) -> list[float]:
    return [float(np.linalg.norm(a - b)) for a, b in combinations(measurements, 2)]


@dataclass(frozen=True)
class ClusterReport:
    """Result of a clustering analysis.

    Strict verdict: ``max_intra < min_inter`` (every same-identity pair
    is closer than every different-identity pair). This is the user's
    stated PUF criterion. Hard, but the right bar — if it doesn't hold,
    no fancy threshold can rescue the authentication claim.

    Soft verdict: ``mean_intra + k_std * std_intra < mean_inter`` (the
    intra distribution sits below the inter distribution by a margin in
    intra-std units). Useful when the strict verdict marginally fails
    due to a single outlier copy."""

    n_identities: int
    n_total_copies: int
    intra_distances: list[float]
    inter_distances: list[float]
    mean_intra: float
    mean_inter: float
    max_intra: float
    min_inter: float
    std_intra: float
    std_inter: float
    strict_pass: bool
    soft_pass: bool
    soft_k_std: float
    margin: float  # min_inter - max_intra; > 0 means strict pass

    def to_dict(self) -> dict:
        return {
            "n_identities": self.n_identities,
            "n_total_copies": self.n_total_copies,
            "mean_intra": self.mean_intra,
            "mean_inter": self.mean_inter,
            "max_intra": self.max_intra,
            "min_inter": self.min_inter,
            "std_intra": self.std_intra,
            "std_inter": self.std_inter,
            "strict_pass": self.strict_pass,
            "soft_pass": self.soft_pass,
            "soft_k_std": self.soft_k_std,
            "margin": self.margin,
        }


def cluster_report(
    measurements_by_identity: Mapping[str, Iterable[np.ndarray]],
    *,
    soft_k_std: float = 2.0,
) -> ClusterReport:
    """Compute the clustering verdict for a labelled set of measurements.

    ``measurements_by_identity`` maps each identity label (e.g. "alice",
    "bob") to its list of measurement vectors. Requires at least 2
    identities AND at least 2 copies per identity for intra-distances
    to exist. Otherwise raises ``ValueError`` so the caller can't
    silently get a degenerate verdict."""

    by_id = {k: list(v) for k, v in measurements_by_identity.items()}
    if len(by_id) < 2:
        raise ValueError(
            f"need at least 2 identities to test clustering, got {len(by_id)}"
        )
    for ident, copies in by_id.items():
        if len(copies) < 2:
            raise ValueError(
                f"identity {ident!r} has {len(copies)} copies; need >= 2 "
                "for intra-distance to exist"
            )

    intra: list[float] = []
    for copies in by_id.values():
        intra.extend(_pairwise(copies))

    inter: list[float] = []
    idents = list(by_id.keys())
    for i, j in combinations(range(len(idents)), 2):
        for a in by_id[idents[i]]:
            for b in by_id[idents[j]]:
                inter.append(float(np.linalg.norm(a - b)))

    mean_intra = float(np.mean(intra))
    mean_inter = float(np.mean(inter))
    max_intra = float(np.max(intra))
    min_inter = float(np.min(inter))
    std_intra = float(np.std(intra))
    std_inter = float(np.std(inter))

    strict_pass = max_intra < min_inter
    soft_pass = (mean_intra + soft_k_std * std_intra) < mean_inter
    margin = min_inter - max_intra

    return ClusterReport(
        n_identities=len(by_id),
        n_total_copies=sum(len(v) for v in by_id.values()),
        intra_distances=intra,
        inter_distances=inter,
        mean_intra=mean_intra,
        mean_inter=mean_inter,
        max_intra=max_intra,
        min_inter=min_inter,
        std_intra=std_intra,
        std_inter=std_inter,
        strict_pass=strict_pass,
        soft_pass=soft_pass,
        soft_k_std=soft_k_std,
        margin=margin,
    )


# --------------------------------------------------------------------------
# Convenience: simulate-and-report
# --------------------------------------------------------------------------


def simulate_cluster_test(
    seeds_by_identity: Mapping[str, int],
    *,
    n_copies: int,
    noise_sigma: float,
    measurement_fn: Callable[[int], np.ndarray] | None = None,
    soft_k_std: float = 2.0,
    rng_root: int | None = 0,
) -> ClusterReport:
    """Simulate ``n_copies`` measurements per identity at ``noise_sigma``
    and return the clustering report.

    When ``measurement_fn`` is None, defaults to
    ``lambda seed: measurement_from_variant(apply_crypto_seed(VARIANTS[1], seed))``
    using the ``mae_silicone_ferrite_lattice`` baseline (a magnetically
    responsive variant — what the Dynamo Core actually uses)."""

    from scripts.experiments.mahss_metamaterial_sim import VARIANTS

    if measurement_fn is None:
        baseline = VARIANTS[1]

        def measurement_fn(seed: int) -> np.ndarray:
            return measurement_from_variant(apply_crypto_seed(baseline, seed))

    by_id: dict[str, list[np.ndarray]] = {}
    for offset, (ident, seed) in enumerate(seeds_by_identity.items()):
        # Per-identity rng so noise is reproducible without identities
        # interfering with each other's draws.
        rng = (
            np.random.default_rng(seed=(rng_root or 0) + offset)
            if rng_root is not None
            else None
        )
        by_id[ident] = simulate_copies(
            seed,
            n_copies=n_copies,
            measurement_fn=measurement_fn,
            noise_sigma=noise_sigma,
            rng=rng,
        )
    return cluster_report(by_id, soft_k_std=soft_k_std)


def find_critical_noise_sigma(
    seeds_by_identity: Mapping[str, int],
    *,
    n_copies: int,
    measurement_fn: Callable[[int], np.ndarray] | None = None,
    sigma_grid: list[float] | None = None,
    rng_root: int | None = 0,
) -> dict:
    """Probe the noise budget: the largest ``sigma`` at which strict
    clustering still holds.

    Concretely answers: "how repeatable must my printer/measurement be
    for the PUF claim to hold?" — anything looser than the returned
    sigma will fail the strict verdict. Sweeps a grid; returns the
    highest passing sigma plus the full table."""

    if sigma_grid is None:
        sigma_grid = [0.0, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0]
    table: list[dict] = []
    last_pass: float | None = None
    first_fail: float | None = None
    for sigma in sigma_grid:
        report = simulate_cluster_test(
            seeds_by_identity,
            n_copies=n_copies,
            noise_sigma=sigma,
            measurement_fn=measurement_fn,
            rng_root=rng_root,
        )
        row = {
            "sigma": sigma,
            "strict_pass": report.strict_pass,
            "margin": report.margin,
            "max_intra": report.max_intra,
            "min_inter": report.min_inter,
        }
        table.append(row)
        if report.strict_pass:
            last_pass = sigma
        elif first_fail is None:
            first_fail = sigma
    return {
        "max_passing_sigma": last_pass,
        "first_failing_sigma": first_fail,
        "sweep": table,
    }
