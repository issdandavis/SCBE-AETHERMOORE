from __future__ import annotations

import json
from pathlib import Path

from benchmarks.scbe.datasets.governance_gate import (
    build_governance_gate_dataset,
    load_governance_gate_rows,
)
from benchmarks.scbe.metrics.governance_gate_metrics import compute_governance_gate_metrics
from scripts.research.build_governance_gate_prediction_benchmark import run_benchmark


def _contains_forbidden_key(value) -> bool:
    if isinstance(value, dict):
        for key, inner in value.items():
            if key in {"plaintext", "sealed_blob"}:
                return True
            if _contains_forbidden_key(inner):
                return True
    if isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def test_governance_gate_dataset_is_deterministic() -> None:
    rows_a = build_governance_gate_dataset(group_count=8, seed=17)
    rows_b = build_governance_gate_dataset(group_count=8, seed=17)

    assert rows_a == rows_b
    assert rows_a
    assert rows_a[0]["source"] == "governance_check_v1"


def test_governance_gate_dataset_preserves_group_split_and_excludes_sensitive_fields() -> None:
    rows = build_governance_gate_dataset(group_count=12, seed=5)

    group_to_split = {}
    for row in rows:
        group_id = row["group_id"]
        split = row["split"]
        group_to_split.setdefault(group_id, split)
        assert group_to_split[group_id] == split
        assert _contains_forbidden_key(row) is False


def test_governance_gate_metrics_score_perfect_predictions() -> None:
    references = build_governance_gate_dataset(group_count=6, seed=11)
    test_rows = [row for row in references if row["split"] == "test"]
    predictions = [
        {
            "id": row["id"],
            "decision": row["labels"]["decision"],
            "risk_prime_pred": row["labels"]["risk_prime"],
        }
        for row in test_rows
    ]

    metrics = compute_governance_gate_metrics(test_rows, predictions)
    assert metrics["macro_f1"] == 1.0
    assert metrics["accuracy"] == 1.0
    assert metrics["normalized_rmse"] == 0.0
    assert metrics["blended_score"] == 1.0


def test_governance_gate_benchmark_runner_writes_expected_artifacts(tmp_path: Path) -> None:
    outputs = run_benchmark(output_dir=tmp_path, group_count=10, seed=23)

    for path in outputs.values():
        assert path.exists()

    train_rows = load_governance_gate_rows([outputs["train"]])
    validation_predictions = load_governance_gate_rows([outputs["validation_predictions"]])
    summary = json.loads(outputs["benchmark_summary"].read_text(encoding="utf-8"))

    assert train_rows
    assert validation_predictions
    assert "validation" in summary
    assert "test" in summary
    assert summary["dataset"]["total_rows"] == 30
