"""Tests for the crypto-seeded MAHSS lattice perturbation.

Covers:
- determinism (same seed -> bit-identical output)
- avalanche (different seeds -> distinguishable lattices)
- bound respect (perturbation never exceeds the configured limit)
- variant validity (seeded variant has same fields, plausible numerics,
  identifiable name suffix)
- bytes adapter (PQC-shaped payload -> 64-bit seed)
- manifest shape (audit-ready JSON-serializable form)
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from python.scbe.mahss_crypto_lattice import (
    apply_crypto_seed,
    derive_perturbation_field,
    manifest_for_seed,
    perturbation_distance,
    seed_from_bytes,
)
from scripts.experiments.mahss_metamaterial_sim import VARIANTS


def test_derive_perturbation_field_is_deterministic():
    a = derive_perturbation_field(seed=0xDEADBEEF, n_dims=11)
    b = derive_perturbation_field(seed=0xDEADBEEF, n_dims=11)
    assert np.array_equal(a, b)


def test_derive_perturbation_field_avalanche():
    """Adjacent seeds must yield distinguishable perturbations.
    Distance > 0.01 in 11D space at default bound 0.05 is a healthy
    floor — collapse to ~0 would mean the SHA-256 mixing failed."""

    a = derive_perturbation_field(seed=42, n_dims=11)
    b = derive_perturbation_field(seed=43, n_dims=11)
    distance = float(np.linalg.norm(a - b))
    assert distance > 0.01, f"avalanche too weak: distance={distance}"


def test_derive_perturbation_field_respects_bound():
    bound = 0.05
    field = derive_perturbation_field(seed=12345, n_dims=64, bound=bound)
    assert np.all(field >= -bound - 1e-9)
    assert np.all(field <= bound + 1e-9)


def test_derive_perturbation_field_zero_bound_is_zero():
    field = derive_perturbation_field(seed=999, n_dims=11, bound=0.0)
    assert np.allclose(field, 0.0)


def test_derive_perturbation_field_rejects_invalid_dims():
    with pytest.raises(ValueError):
        derive_perturbation_field(seed=1, n_dims=0)


def test_derive_perturbation_field_rejects_negative_bound():
    with pytest.raises(ValueError):
        derive_perturbation_field(seed=1, n_dims=4, bound=-0.1)


def test_apply_crypto_seed_deterministic():
    base = VARIANTS[0]
    seeded_a = apply_crypto_seed(base, seed=7)
    seeded_b = apply_crypto_seed(base, seed=7)
    assert seeded_a == seeded_b


def test_apply_crypto_seed_different_seeds_yield_different_variants():
    base = VARIANTS[0]
    a = apply_crypto_seed(base, seed=1)
    b = apply_crypto_seed(base, seed=2)
    assert a != b
    assert a.name != b.name


def test_apply_crypto_seed_preserves_variant_fields():
    base = VARIANTS[0]
    seeded = apply_crypto_seed(base, seed=42)
    # All numeric fields perturbed by < 5%/2% relative bound — sign and
    # magnitude category preserved (no negatives turning positive etc.)
    assert seeded.relaxed_porosity > 0
    assert seeded.modulus_mpa > 0
    assert seeded.density_kg_m3 > 0
    # poisson_ratio is negative for auxetics; sign must survive.
    assert seeded.poisson_ratio < 0
    # Heavy bound 0.05 is a soft cap on relative magnitude.
    assert abs(seeded.relaxed_porosity / base.relaxed_porosity - 1.0) <= 0.05 + 1e-9
    assert abs(seeded.modulus_mpa / base.modulus_mpa - 1.0) <= 0.05 + 1e-9


def test_apply_crypto_seed_name_suffix_includes_hex():
    base = VARIANTS[0]
    seeded = apply_crypto_seed(base, seed=0xCAFEBABE)
    assert seeded.name.startswith(base.name)
    assert "cafebabe" in seeded.name.lower()


def test_apply_crypto_seed_custom_name_suffix():
    base = VARIANTS[0]
    seeded = apply_crypto_seed(base, seed=1, name_suffix="_drone007")
    assert seeded.name.endswith("_drone007")


def test_seed_from_bytes_is_deterministic_and_64bit():
    blob = b"\x00" * 1088  # Kyber768 ciphertext length
    a = seed_from_bytes(blob)
    b = seed_from_bytes(blob)
    assert a == b
    assert 0 <= a < 2**64


def test_seed_from_bytes_avalanche():
    a = seed_from_bytes(b"public-key-A" + b"\x00" * 100)
    b = seed_from_bytes(b"public-key-B" + b"\x00" * 100)
    assert a != b


def test_perturbation_distance_zero_for_same_seed():
    assert perturbation_distance(99, 99) == pytest.approx(0.0)


def test_perturbation_distance_positive_for_different_seeds():
    assert perturbation_distance(99, 100) > 0.0


def test_manifest_for_seed_is_json_serializable():
    seed = 0x1234_5678_9ABC_DEF0
    manifest = manifest_for_seed(seed, VARIANTS[:2])
    blob = json.dumps(manifest)
    decoded = json.loads(blob)
    assert decoded["seed"] == seed
    assert decoded["seed_hex"] == f"{seed:016x}"
    assert decoded["n_variants"] == 2
    assert len(decoded["seeded_variant_names"]) == 2
    # Every variant entry must include all original AuxeticVariant fields
    assert "relaxed_porosity" in decoded["seeded_variants"][0]


def test_full_pqc_pipeline_smoke():
    """End-to-end: PQC-shaped bytes -> seed -> seeded variant. The
    'cryptographic' property tested here is just structural: each
    distinct PQC public-key blob must produce a distinct seeded variant."""

    pk_a = b"alice-pubkey" + b"\xaa" * 1076
    pk_b = b"bob-pubkey" + b"\xbb" * 1078
    seed_a = seed_from_bytes(pk_a)
    seed_b = seed_from_bytes(pk_b)
    assert seed_a != seed_b

    base = VARIANTS[0]
    variant_a = apply_crypto_seed(base, seed_a)
    variant_b = apply_crypto_seed(base, seed_b)
    assert variant_a != variant_b
    # Each unit's relaxed_porosity is the PUF-readable fingerprint dim 0.
    assert variant_a.relaxed_porosity != variant_b.relaxed_porosity
