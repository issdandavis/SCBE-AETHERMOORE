"""Contract checks for the bijective frequency transport benchmark."""

from __future__ import annotations

import json

from scripts.benchmark.bijective_frequency_transport import run_benchmark, write_report


def test_benchmark_reports_exact_recovery_and_honest_bounds(tmp_path) -> None:
    payload = run_benchmark()

    assert payload["fixture"]["command_count"] == 10
    assert all(payload["checks"].values())
    assert payload["claim_status"]["single_lane_recovery"] == "SUPPORTED_STRUCTURAL"
    assert payload["claim_status"]["two_lane_recovery"] == "OUTSIDE_CONTRACT"
    assert payload["claim_status"]["free_capacity"] == "REFUTED_BY_ACCOUNTING"
    assert (
        payload["controls"]["five_plus_one_parity_wire_bytes"]
        < payload["controls"]["sixfold_repetition_wire_bytes"]
    )

    json_path, markdown_path = write_report(payload, tmp_path / "report.json")
    round_trip = json.loads(json_path.read_text(encoding="utf-8"))
    assert round_trip["checks"] == payload["checks"]
    assert "physical hardware" in markdown_path.read_text(encoding="utf-8")
