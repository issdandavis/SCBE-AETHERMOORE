from __future__ import annotations

import json

from scripts.benchmark import toy_lwe_fractional_route_benchmark as BENCHMARK


def test_small_fractional_route_benchmark_is_exact_and_writes_receipt(tmp_path) -> None:
    output = tmp_path / "result.json"
    report = BENCHMARK.run(
        seed_start=500,
        seeds=3,
        dimension=4,
        samples=7,
        locality_candidates=12,
        exhaustive_audit_seeds=3,
        output=output,
    )
    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted == report
    assert report["baseline"]["exact_results"] == 3
    assert all(row["exhaustive_audited"] for row in report["rows"])
    assert all(
        row["methods"][method]["total_objective_evaluations"]
        == row["methods"][method]["acquisition_objective_evaluations"]
        + row["methods"][method]["certification_objective_evaluations"]
        for row in report["rows"]
        for method in BENCHMARK.METHODS
    )
    assert report["arithmetic"]["search_uses_floating_point"] is False
    assert report["matrix_locality_diagnostic"]["therefore_available_to_search"] is False
