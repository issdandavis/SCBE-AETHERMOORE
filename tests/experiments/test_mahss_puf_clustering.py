"""Tests for the PUF clustering harness.

Covers the user's stated criterion (max_intra < min_inter) under various
noise conditions, plus the noise-budget sweep and edge-case handling."""

from __future__ import annotations

import numpy as np
import pytest

from python.scbe.mahss_puf_clustering import (
    ClusterReport,
    cluster_report,
    find_critical_noise_sigma,
    measurement_from_geometry,
    measurement_from_variant,
    simulate_cluster_test,
    simulate_copies,
)
from python.scbe.mahss_crypto_lattice import apply_crypto_seed
from scripts.experiments.mahss_metamaterial_sim import VARIANTS


# --------------------------------------------------------------------------
# Measurement adapters
# --------------------------------------------------------------------------


def test_measurement_from_variant_is_deterministic_and_fixed_length():
    base = VARIANTS[0]
    seeded = apply_crypto_seed(base, seed=42)
    a = measurement_from_variant(seeded)
    b = measurement_from_variant(seeded)
    assert np.array_equal(a, b)
    assert a.shape == (10,)
    assert a.dtype == float


def test_measurement_from_geometry_matches_perturb_field():
    m = measurement_from_geometry(seed=42, num_ridges=16, scale_mm=0.5)
    assert m.shape == (16,)
    assert np.all(np.abs(m) <= 0.5 * 0.05 + 1e-9)


# --------------------------------------------------------------------------
# Simulation
# --------------------------------------------------------------------------


def test_simulate_copies_zero_noise_is_identical():
    base = VARIANTS[0]
    fn = lambda s: measurement_from_variant(apply_crypto_seed(base, s))
    copies = simulate_copies(seed=7, n_copies=4, measurement_fn=fn, noise_sigma=0.0)
    assert len(copies) == 4
    for c in copies[1:]:
        assert np.array_equal(c, copies[0])


def test_simulate_copies_nonzero_noise_distinguishes_copies():
    base = VARIANTS[0]
    fn = lambda s: measurement_from_variant(apply_crypto_seed(base, s))
    copies = simulate_copies(seed=7, n_copies=4, measurement_fn=fn, noise_sigma=0.05)
    # No two copies should be exactly equal under positive noise
    for i in range(len(copies)):
        for j in range(i + 1, len(copies)):
            assert not np.array_equal(copies[i], copies[j])


def test_simulate_copies_rejects_invalid_args():
    fn = lambda s: np.zeros(5)
    with pytest.raises(ValueError):
        simulate_copies(seed=1, n_copies=0, measurement_fn=fn, noise_sigma=0.0)
    with pytest.raises(ValueError):
        simulate_copies(seed=1, n_copies=2, measurement_fn=fn, noise_sigma=-0.1)


# --------------------------------------------------------------------------
# Clustering verdict
# --------------------------------------------------------------------------


def test_cluster_report_zero_noise_strict_passes():
    """With zero noise and distinct seeds, intra=0 for every pair and
    inter>0 for every pair, so the strict verdict trivially holds."""

    report = simulate_cluster_test(
        {"alice": 1, "bob": 2}, n_copies=3, noise_sigma=0.0
    )
    assert report.strict_pass is True
    assert report.max_intra == pytest.approx(0.0, abs=1e-12)
    assert report.min_inter > 0.0
    assert report.margin > 0.0


def test_cluster_report_small_noise_still_passes():
    """At small enough noise (<< inter-identity separation), strict
    clustering must still hold for the AuxeticVariant axis."""

    report = simulate_cluster_test(
        {"alice": 1, "bob": 2}, n_copies=5, noise_sigma=0.001
    )
    assert report.strict_pass is True
    assert report.margin > 0.0


def test_cluster_report_huge_noise_fails():
    """At absurd noise, intra distances exceed inter distances and the
    strict verdict must FAIL — sanity check that the harness reports
    failure, not silently rubber-stamps."""

    # 10x the magnitude of the AuxeticVariant fields — guaranteed to
    # destroy clustering.
    report = simulate_cluster_test(
        {"alice": 1, "bob": 2}, n_copies=8, noise_sigma=10000.0
    )
    assert report.strict_pass is False


def test_cluster_report_requires_at_least_two_identities():
    with pytest.raises(ValueError, match="at least 2 identities"):
        cluster_report({"only_one": [np.array([1.0]), np.array([1.1])]})


def test_cluster_report_requires_at_least_two_copies_per_identity():
    with pytest.raises(ValueError, match="copies"):
        cluster_report(
            {
                "alice": [np.array([1.0])],  # singleton
                "bob": [np.array([2.0]), np.array([2.1])],
            }
        )


def test_cluster_report_returns_full_distance_lists():
    report = cluster_report(
        {
            "a": [np.array([0.0, 0.0]), np.array([0.1, 0.0])],
            "b": [np.array([5.0, 0.0]), np.array([5.0, 0.1])],
        }
    )
    assert len(report.intra_distances) == 2  # one pair per identity
    assert len(report.inter_distances) == 4  # 2x2 cross pairs
    assert report.strict_pass is True


def test_cluster_report_to_dict_is_json_friendly():
    report = simulate_cluster_test(
        {"alice": 1, "bob": 2}, n_copies=3, noise_sigma=0.0
    )
    import json
    blob = json.dumps(report.to_dict())
    decoded = json.loads(blob)
    assert decoded["strict_pass"] is True


# --------------------------------------------------------------------------
# Noise budget sweep
# --------------------------------------------------------------------------


def test_find_critical_noise_sigma_returns_threshold():
    """The sweep must (a) include sigma=0 as passing, (b) report a
    passing sigma <= a failing sigma, and (c) flip from pass to fail
    monotonically when noise is the only changing variable."""

    result = find_critical_noise_sigma(
        {"alice": 1, "bob": 2},
        n_copies=4,
        sigma_grid=[0.0, 0.001, 0.01, 1.0, 100.0, 10000.0],
    )
    assert result["max_passing_sigma"] is not None
    assert result["first_failing_sigma"] is not None
    assert result["max_passing_sigma"] < result["first_failing_sigma"]
    # First row (sigma=0) must pass
    assert result["sweep"][0]["strict_pass"] is True
    # Last row (sigma=10000) must fail
    assert result["sweep"][-1]["strict_pass"] is False


def test_find_critical_noise_sigma_default_grid():
    result = find_critical_noise_sigma({"alice": 1, "bob": 2}, n_copies=3)
    assert "sweep" in result
    assert len(result["sweep"]) >= 5


# --------------------------------------------------------------------------
# Geometry-axis clustering (lower-level signal)
# --------------------------------------------------------------------------


def test_geometry_axis_clustering_passes_at_zero_noise():
    """Same harness, lower-level measurement axis (per-ridge mm
    displacements). Clustering must still pass at zero noise."""

    fn = lambda s: measurement_from_geometry(s, num_ridges=16, scale_mm=0.5)
    report = simulate_cluster_test(
        {"alice": 1, "bob": 2},
        n_copies=4,
        noise_sigma=0.0,
        measurement_fn=fn,
    )
    assert report.strict_pass is True
