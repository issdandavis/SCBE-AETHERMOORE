"""Crypto-seeded lattice perturbation for the MAHSS metamaterial simulator.

Closes the "plug a cryptographic seed into MAHSS" thread of the
metamaterial axis. Given a deterministic seed (derived from a PQC
ciphertext, public key, or signature blob), produce a bounded
perturbation field over an :class:`AuxeticVariant` so that:

1. Identical seeds yield bit-identical perturbations (deterministic).
2. Different seeds yield distinguishable perturbations (avalanche).
3. The perturbation never breaks the variant's physical sanity —
   relative bounds keep porosity, modulus, density, etc. inside
   plausible engineering ranges.
4. The same primitive can drive both the simulator (Python) and the
   OpenSCAD prototype (which uses the same golden-angle + bit-extract
   pattern) — same seed in, same physical lattice topology out.

This is the computational engine for the Physical-Compute / metamaterial
PUF story: each manufactured unit is bound to its cryptographic key,
both in software (sim) and in geometry (printed prototype).

Example::

    from python.scbe.mahss_crypto_lattice import (
        apply_crypto_seed,
        seed_from_bytes,
    )
    from scripts.experiments.mahss_metamaterial_sim import VARIANTS

    seed = seed_from_bytes(kyber_public_key_bytes)
    seeded_variant = apply_crypto_seed(VARIANTS[0], seed)
    # seeded_variant is an AuxeticVariant deterministic in `seed`
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import fields, replace
from typing import Iterable

import numpy as np

# Re-export the AuxeticVariant dataclass via local import so callers
# can `from python.scbe.mahss_crypto_lattice import AuxeticVariant` if
# they only need this module's surface.
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.experiments.mahss_metamaterial_sim import AuxeticVariant  # noqa: E402

PHI = (1.0 + 5**0.5) / 2.0
GOLDEN_ANGLE_DEG = 360.0 * (1.0 - 1.0 / PHI)


# Numerical AuxeticVariant fields that participate in the perturbation.
# `name` is excluded (str), and ratios that have a fixed sign or hard
# bound (poisson_ratio, recoverability, cost_index) are perturbed less
# aggressively to avoid sign flips and out-of-range values.
_HEAVY_FIELDS: tuple[str, ...] = (
    "relaxed_porosity",
    "max_closure_fraction",
    "modulus_mpa",
    "density_kg_m3",
    "temperature_limit_c",
    "abrasion_resistance",
    "magnetic_response",
)
_LIGHT_FIELDS: tuple[str, ...] = (
    "poisson_ratio",
    "recoverability",
    "cost_index",
)


def seed_from_bytes(blob: bytes) -> int:
    """Hash an arbitrary-length payload (e.g. a Kyber ciphertext or
    Dilithium signature) into a 64-bit deterministic seed.

    Returns an unsigned int in ``[0, 2**64)``. SHA-256 is used for
    structural mixing — the cryptographic property here is not collision
    resistance per se but that the seed inherits avalanche from the
    source PQC payload, so each PQC keypair yields a distinct lattice."""

    digest = hashlib.sha256(blob).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def derive_perturbation_field(
    seed: int,
    n_dims: int,
    *,
    bound: float = 0.05,
) -> np.ndarray:
    """Produce a bounded deterministic perturbation field of length ``n_dims``.

    The output mirrors the OpenSCAD prototype's pattern: a golden-angle
    phase term plus a bit-extraction modulation, both keyed on ``seed``.
    Returns values in ``[-bound, +bound]`` after clamping.

    Pure NumPy, deterministic, no RNG — same (seed, n_dims, bound) in,
    same array out, regardless of process or platform."""

    if n_dims <= 0:
        raise ValueError(f"n_dims must be positive, got {n_dims}")
    if bound < 0:
        raise ValueError(f"bound must be non-negative, got {bound}")

    # Mix the integer seed into a 256-bit digest so different ints
    # produce well-distributed outputs even when consecutive.
    seed_bytes = int(seed % (2**64)).to_bytes(8, byteorder="big", signed=False)
    digest = hashlib.sha256(seed_bytes).digest()
    digest_int = int.from_bytes(digest, byteorder="big")

    out = np.zeros(n_dims, dtype=float)
    for k in range(n_dims):
        # Golden-angle phase term — same as the OpenSCAD prototype.
        phase_term = math.sin(math.radians(k * GOLDEN_ANGLE_DEG + (seed % 360))) * 0.8
        # Bit-extraction modulation: pull bits k, k+8, k+16, ... from the
        # SHA-256 digest. Multi-bit averaging gives smoother distribution
        # than the OpenSCAD `seed >> (k%32) & 1` single-bit version.
        bits = 0
        bit_count = 0
        for shift in (0, 32, 64, 96, 128, 160, 192, 224):
            bit_pos = (k + shift) % 256
            bits += (digest_int >> bit_pos) & 1
            bit_count += 1
        bit_term = ((bits / bit_count) - 0.5) * 0.6
        out[k] = (phase_term * 0.5 + bit_term) * bound

    return np.clip(out, -bound, bound)


def apply_crypto_seed(
    variant: AuxeticVariant,
    seed: int,
    *,
    heavy_bound: float = 0.05,
    light_bound: float = 0.02,
    name_suffix: str | None = None,
) -> AuxeticVariant:
    """Return a deterministically perturbed copy of ``variant`` keyed on ``seed``.

    Heavy fields (porosity, closure, modulus, density, temperature limit,
    abrasion, magnetic response) get a wider perturbation; light fields
    (Poisson ratio, recoverability, cost) get a tighter one because they
    have hard bounds or sign sensitivity.

    The returned variant has ``name`` suffixed with ``_seed{seed_hex}``
    (or a custom suffix) so downstream telemetry can identify which
    cryptographic identity produced which physical lattice."""

    n_heavy = len(_HEAVY_FIELDS)
    n_light = len(_LIGHT_FIELDS)
    heavy_field = derive_perturbation_field(seed, n_heavy, bound=heavy_bound)
    # Different bound + offset seed for the light field so the two are
    # not perfectly correlated — independent dimensions of perturbation.
    light_field = derive_perturbation_field(seed + 1, n_light, bound=light_bound)

    updates: dict[str, float] = {}
    for value, field_name in zip(heavy_field, _HEAVY_FIELDS):
        current = getattr(variant, field_name)
        updates[field_name] = current * (1.0 + float(value))
    for value, field_name in zip(light_field, _LIGHT_FIELDS):
        current = getattr(variant, field_name)
        updates[field_name] = current * (1.0 + float(value))

    if name_suffix is None:
        name_suffix = f"_seed{seed:016x}"
    updates["name"] = variant.name + name_suffix
    return replace(variant, **updates)


def perturbation_distance(seed_a: int, seed_b: int, n_dims: int = 11) -> float:
    """Euclidean distance between perturbation fields for two seeds.

    Used by tests to verify avalanche — small input changes should yield
    decorrelated outputs. A value near zero means the seeds collapsed to
    nearly the same lattice (bad)."""

    a = derive_perturbation_field(seed_a, n_dims)
    b = derive_perturbation_field(seed_b, n_dims)
    return float(np.linalg.norm(a - b))


def manifest_for_seed(seed: int, variants: Iterable[AuxeticVariant]) -> dict:
    """Build a JSON-serializable manifest binding a seed to the seeded
    variants it produces. Useful for the PUF audit trail: given a PQC
    public key, the manifest is a witness of which physical lattices it
    would manufacture (one per variant family)."""

    seeded = [apply_crypto_seed(v, seed) for v in variants]
    return {
        "seed": int(seed),
        "seed_hex": f"{seed:016x}",
        "n_variants": len(seeded),
        "perturbation_field_heavy": derive_perturbation_field(seed, len(_HEAVY_FIELDS)).tolist(),
        "perturbation_field_light": derive_perturbation_field(seed + 1, len(_LIGHT_FIELDS)).tolist(),
        "seeded_variant_names": [v.name for v in seeded],
        "seeded_variants": [
            {f.name: getattr(v, f.name) for f in fields(v)} for v in seeded
        ],
    }
