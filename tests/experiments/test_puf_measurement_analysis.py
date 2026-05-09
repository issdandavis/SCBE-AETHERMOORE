import csv
import json

import pytest

from scripts.experiments.puf_measurement_analysis import (
    Measurement,
    analyze_measurements,
    bootstrap_gap_ci,
    load_measurements,
    metrics_to_report,
    write_report,
)


def separated_measurements() -> list[Measurement]:
    return [
        Measurement(
            "seed-a-print-0",
            "0",
            (0.10, 0.10, 0.10, 0.10, 0.90, 0.90, 0.90, 0.90),
            "seed-a",
        ),
        Measurement(
            "seed-a-print-0",
            "1",
            (0.11, 0.11, 0.11, 0.11, 0.89, 0.89, 0.89, 0.89),
            "seed-a",
        ),
        Measurement(
            "seed-a-print-1",
            "0",
            (0.90, 0.90, 0.10, 0.10, 0.10, 0.10, 0.90, 0.90),
            "seed-a",
        ),
        Measurement(
            "seed-b-print-0",
            "0",
            (0.90, 0.90, 0.90, 0.90, 0.10, 0.10, 0.10, 0.10),
            "seed-b",
        ),
        Measurement(
            "seed-b-print-0",
            "1",
            (0.89, 0.89, 0.89, 0.89, 0.11, 0.11, 0.11, 0.11),
            "seed-b",
        ),
        Measurement(
            "seed-b-print-1",
            "0",
            (0.10, 0.10, 0.90, 0.90, 0.90, 0.90, 0.10, 0.10),
            "seed-b",
        ),
    ]


def overlapping_measurements() -> list[Measurement]:
    return [
        Measurement("seed-a-print-0", "0", (0.10, 0.10, 0.90, 0.90), "seed-a"),
        Measurement("seed-a-print-0", "1", (0.11, 0.11, 0.89, 0.89), "seed-a"),
        Measurement("seed-a-print-1", "0", (0.10, 0.10, 0.90, 0.90), "seed-a"),
        Measurement("seed-b-print-0", "0", (0.90, 0.90, 0.10, 0.10), "seed-b"),
        Measurement("seed-b-print-0", "1", (0.89, 0.89, 0.11, 0.11), "seed-b"),
    ]


def test_analyze_measurements_reports_separated_puf_candidate() -> None:
    metrics = analyze_measurements(separated_measurements())

    assert metrics.schema_version == "aetherfab_puf_measurement_analysis_v1"
    assert metrics.device_count == 4
    assert metrics.measurement_count == 6
    assert metrics.reliability == 1.0
    assert metrics.clone.count == 4
    assert metrics.clone_gap > 0.0
    assert metrics.uniqueness > 0.45
    assert metrics.separation_margin > 0.0
    assert metrics.works_for_fuzzy_extractor is True
    assert metrics.works_against_seed_clone is True
    assert metrics.estimated_t_bits == 0
    assert metrics.estimated_clone_delta_bits > 0
    assert metrics.estimated_delta_bits > 0


def test_analyze_measurements_rejects_overlapping_candidate() -> None:
    metrics = analyze_measurements(overlapping_measurements())

    assert metrics.clone_gap <= 0.0
    assert metrics.works_against_seed_clone is False


def test_load_measurements_from_wide_csv(tmp_path) -> None:
    path = tmp_path / "impedance.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["device_id", "seed_id", "read_id", "z_1hz", "z_10hz"])
        writer.writerow(["seed-a-print-0", "seed-a", "0", "0.1", "0.2"])
        writer.writerow(["seed-a-print-0", "seed-a", "1", "0.1", "0.21"])

    rows, features = load_measurements(path)

    assert features == ["z_1hz", "z_10hz"]
    assert rows == [
        Measurement("seed-a-print-0", "0", (0.1, 0.2), "seed-a"),
        Measurement("seed-a-print-0", "1", (0.1, 0.21), "seed-a"),
    ]


def test_report_contains_verdict_and_next_step(tmp_path) -> None:
    metrics = analyze_measurements(separated_measurements())
    report = metrics_to_report(
        metrics, feature_names=["f0"] * metrics.feature_count, gap_ci=(0.25, 0.75)
    )
    path = tmp_path / "report.json"

    write_report(report, path)
    loaded = json.loads(path.read_text(encoding="utf-8"))

    assert loaded["verdict"] == "clone_resistant_candidate"
    assert (
        loaded["architecture_status"]
        == "RAW_SEEDED_TOPOLOGY_PUF_DISCONFIRMED_STANDALONE_2026_05"
    )
    assert "Parked raw seeded-topology diagnostic" in loaded["status_note"]
    assert "Sacred Eggs" in loaded["status_note"]
    assert "challenge-selector" in loaded["recommended_pivot"]
    assert loaded["separation_margin_ci95"] == {"low": 0.25, "high": 0.75}
    assert "ECC" in loaded["recommended_next"]


def test_bootstrap_gap_ci_is_deterministic() -> None:
    ci_a = bootstrap_gap_ci(separated_measurements(), iterations=20, seed=7)
    ci_b = bootstrap_gap_ci(separated_measurements(), iterations=20, seed=7)

    assert ci_a == ci_b
    assert ci_a[0] <= ci_a[1]


def test_load_measurements_requires_feature_columns(tmp_path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("device_id,read_id\nseed-a,0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="numeric feature"):
        load_measurements(path)
