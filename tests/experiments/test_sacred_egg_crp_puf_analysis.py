import csv
import json

import pytest

from scripts.experiments.sacred_egg_crp_puf_analysis import (
    CrpMeasurement,
    analyze_measurements,
    load_measurements,
    metrics_to_report,
    write_report,
)


def auth_candidate_rows() -> list[CrpMeasurement]:
    return [
        CrpMeasurement("unit-a", "challenge-1", "0", (0.10, 0.10, 0.90, 0.90)),
        CrpMeasurement("unit-a", "challenge-1", "1", (0.11, 0.11, 0.89, 0.89)),
        CrpMeasurement("unit-b", "challenge-1", "0", (0.90, 0.90, 0.10, 0.10)),
        CrpMeasurement("unit-b", "challenge-1", "1", (0.89, 0.89, 0.11, 0.11)),
        CrpMeasurement("unit-a", "challenge-2", "0", (0.90, 0.10, 0.10, 0.90)),
        CrpMeasurement("unit-b", "challenge-2", "0", (0.10, 0.90, 0.90, 0.10)),
    ]


def overlapping_rows() -> list[CrpMeasurement]:
    return [
        CrpMeasurement("unit-a", "challenge-1", "0", (0.10, 0.10, 0.90, 0.90)),
        CrpMeasurement("unit-a", "challenge-1", "1", (0.90, 0.90, 0.10, 0.10)),
        CrpMeasurement("unit-b", "challenge-1", "0", (0.11, 0.11, 0.89, 0.89)),
        CrpMeasurement("unit-b", "challenge-1", "1", (0.12, 0.12, 0.88, 0.88)),
    ]


def test_auth_candidate_separates_genuine_from_impostor() -> None:
    metrics = analyze_measurements(auth_candidate_rows())

    assert metrics.schema_version == "sacred_egg_crp_puf_analysis_v1"
    assert metrics.architecture_status == "CHALLENGE_SELECTOR_CRP_PUF_CANDIDATE_2026_05"
    assert metrics.device_count == 2
    assert metrics.challenge_count == 2
    assert metrics.genuine.count == 2
    assert metrics.impostor.count == 5
    assert metrics.reliability == 1.0
    assert metrics.challenge_separation > 0.0
    assert metrics.works_for_authentication is True
    assert metrics.estimated_t_bits == 0
    assert metrics.estimated_impostor_delta_bits > 0


def test_overlap_rejects_authentication_claim() -> None:
    metrics = analyze_measurements(overlapping_rows())

    assert metrics.works_for_authentication is False
    assert metrics.challenge_separation <= 0.0


def test_load_measurements_from_csv(tmp_path) -> None:
    path = tmp_path / "crp.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["device_id", "challenge_id", "read_id", "r0", "r1"])
        writer.writerow(["unit-a", "challenge-1", "0", "0.1", "0.9"])
        writer.writerow(["unit-a", "challenge-1", "1", "0.11", "0.88"])

    rows, features = load_measurements(path)

    assert features == ["r0", "r1"]
    assert rows == [
        CrpMeasurement("unit-a", "challenge-1", "0", (0.1, 0.9)),
        CrpMeasurement("unit-a", "challenge-1", "1", (0.11, 0.88)),
    ]


def test_report_carries_sacred_egg_role(tmp_path) -> None:
    metrics = analyze_measurements(auth_candidate_rows())
    report = metrics_to_report(metrics, feature_names=["r0"] * metrics.feature_count)
    path = tmp_path / "report.json"

    write_report(report, path)
    loaded = json.loads(path.read_text(encoding="utf-8"))

    assert loaded["verdict"] == "auth_candidate"
    assert "Sacred Egg / GeoSeal context" in loaded["sacred_egg_role"]
    assert "challenge_id selection" in loaded["recommended_next"]


def test_load_requires_response_columns(tmp_path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("device_id,challenge_id,read_id\nunit-a,c1,0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="response column"):
        load_measurements(path)
