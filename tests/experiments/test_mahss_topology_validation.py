from __future__ import annotations

import json

import numpy as np

from scripts.experiments.mahss_topology_validation import (
    MEASUREMENT_SCHEMA_VERSION,
    SCHEMA_VERSION,
    TopologySpec,
    apply_manufacturing_noise,
    euclidean_distance,
    extract_measurement_signature,
    extract_topology_signature,
    fingerprint,
    generate_topology,
    load_measurement_csv,
    residue_coefficients,
    run_measurement_validation,
    run_validation,
    synthetic_impulse_trace,
    write_synthetic_measurement_csv,
    write_report,
)


def test_residue_coefficients_are_deterministic_and_bounded() -> None:
    first = residue_coefficients("seed-a", 64)
    second = residue_coefficients("seed-a", 64)
    other = residue_coefficients("seed-b", 64)

    assert np.array_equal(first, second)
    assert not np.array_equal(first, other)
    assert np.max(first) <= 1.0
    assert np.min(first) >= -1.0


def test_generate_topology_is_seed_replayable() -> None:
    spec = TopologySpec(node_count=48, coefficient_count=96)
    first = generate_topology("mahss-seed", spec)
    second = generate_topology("mahss-seed", spec)

    assert first["coefficients_sha256"] == second["coefficients_sha256"]
    assert np.allclose(first["points"], second["points"])
    assert np.allclose(first["channel_width"], second["channel_width"])
    assert np.allclose(first["infill_density"], second["infill_density"])


def test_topology_signatures_separate_different_seeds_more_than_noise() -> None:
    spec = TopologySpec(node_count=72, coefficient_count=128)
    seed_a = generate_topology("seed-a", spec)
    seed_b = generate_topology("seed-b", spec)
    noisy_a = apply_manufacturing_noise(seed_a, noise_seed="seed-a-repeat")

    sig_a = extract_topology_signature(seed_a)
    sig_noisy_a = extract_topology_signature(noisy_a)
    sig_b = extract_topology_signature(seed_b)

    assert euclidean_distance(sig_a, sig_noisy_a) < euclidean_distance(sig_a, sig_b)
    assert fingerprint(sig_a) == fingerprint(extract_topology_signature(generate_topology("seed-a", spec)))


def test_validation_reports_repeatability_authentication_and_quarantine() -> None:
    report = run_validation(seed_count=10, repeats_per_seed=3, spec=TopologySpec(node_count=72, coefficient_count=128))

    assert report["schema_version"] == SCHEMA_VERSION
    metrics = report["metrics"]
    assert metrics["fingerprint_collision_count"] == 0
    assert metrics["separation_margin"] > 0.0
    assert metrics["false_accept_count"] == 0
    assert metrics["false_reject_count"] == 0
    assert report["gate_report"]["G2_repeatability"]["status"] == "pass"
    assert report["gate_report"]["G3_authentication"]["status"] == "pass"
    assert report["decision_record"]["action"] == "QUARANTINE"


def test_write_report_round_trips(tmp_path) -> None:
    report = run_validation(seed_count=4, repeats_per_seed=2, spec=TopologySpec(node_count=48, coefficient_count=96))
    output = tmp_path / "topology_validation.json"

    write_report(report, output)

    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == SCHEMA_VERSION
    assert loaded["metrics"] == report["metrics"]


def test_measurement_signature_is_replayable_for_same_trace() -> None:
    trace = synthetic_impulse_trace("physical-seed", 0, sample_count=128)

    first = extract_measurement_signature(trace)
    second = extract_measurement_signature(trace)

    assert np.allclose(first, second)
    assert fingerprint(first) == fingerprint(second)


def test_synthetic_impulse_response_separates_seeds() -> None:
    same_a = synthetic_impulse_trace("physical-seed-a", 0, sample_count=256)
    same_b = synthetic_impulse_trace("physical-seed-a", 1, sample_count=256)
    other = synthetic_impulse_trace("physical-seed-b", 0, sample_count=256)

    sig_a = extract_measurement_signature(same_a)
    sig_same = extract_measurement_signature(same_b)
    sig_other = extract_measurement_signature(other)

    assert euclidean_distance(sig_a, sig_same) < euclidean_distance(sig_a, sig_other)


def test_measurement_validation_reports_physical_response_margin() -> None:
    measurements = {
        f"seed-{idx}": [synthetic_impulse_trace(f"seed-{idx}", repeat, sample_count=256) for repeat in range(3)]
        for idx in range(6)
    }

    report = run_measurement_validation(measurements, channel="synthetic_impulse", enrollment_repeats=1)

    assert report["schema_version"] == MEASUREMENT_SCHEMA_VERSION
    assert report["metrics"]["separation_margin"] > 0.0
    assert report["metrics"]["false_accept_count"] == 0
    assert report["metrics"]["false_reject_count"] == 0
    assert report["gate_report"]["G3_authentication"]["status"] == "pass"
    assert report["decision_record"]["action"] == "QUARANTINE"


def test_measurement_csv_round_trip(tmp_path) -> None:
    csv_path = tmp_path / "measurements.csv"

    write_synthetic_measurement_csv(csv_path, seed_count=4, repeats_per_seed=3, sample_count=128)
    loaded = load_measurement_csv(csv_path)
    report = run_measurement_validation(loaded)

    assert set(loaded) == {f"mahss-physical-{idx:04d}" for idx in range(4)}
    assert all(len(traces) == 3 for traces in loaded.values())
    assert report["schema_version"] == MEASUREMENT_SCHEMA_VERSION
    assert report["metrics"]["separation_margin"] > 0.0


def test_measurement_validation_uses_centroid_enrollment_for_repeat_noise() -> None:
    measurements = {
        f"seed-{idx}": [synthetic_impulse_trace(f"seed-{idx}", repeat, sample_count=256) for repeat in range(4)]
        for idx in range(8)
    }

    report = run_measurement_validation(measurements, enrollment_repeats=2)

    assert all(row["enrollment_repeat_count"] == 2 for row in report["rows"])
    assert report["metrics"]["false_reject_count"] == 0
    assert report["metrics"]["separation_margin"] > 0.0
