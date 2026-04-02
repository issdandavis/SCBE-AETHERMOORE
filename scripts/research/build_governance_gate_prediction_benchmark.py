"""Build and score the local Governance Gate Prediction benchmark."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmarks.scbe.config import ARTIFACTS_DIR
from benchmarks.scbe.datasets.governance_gate import (
    CONTEXT_ORDER,
    build_governance_gate_dataset,
    summarize_governance_gate_dataset,
    write_governance_gate_dataset,
)
from benchmarks.scbe.metrics.governance_gate_metrics import compute_governance_gate_metrics


def fit_context_prior_baseline(train_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Fit a trivial baseline using only train-split context priors."""
    counts: Dict[str, Dict[str, int]] = {context: {} for context in CONTEXT_ORDER}
    risk_totals: Dict[str, List[float]] = {context: [] for context in CONTEXT_ORDER}

    for row in train_rows:
        context = row["inputs"]["context"]
        decision = row["labels"]["decision"]
        counts[context][decision] = counts[context].get(decision, 0) + 1
        risk_totals[context].append(float(row["labels"]["risk_prime"]))

    global_counts: Dict[str, int] = {}
    global_risks: List[float] = []
    for context in CONTEXT_ORDER:
        for decision, value in counts[context].items():
            global_counts[decision] = global_counts.get(decision, 0) + value
        global_risks.extend(risk_totals[context])

    priors: Dict[str, Any] = {
        "contexts": {},
        "global": {
            "decision_distribution": _normalize_counts(global_counts),
            "risk_prime_mean": _safe_mean(global_risks),
        },
    }
    for context in CONTEXT_ORDER:
        priors["contexts"][context] = {
            "decision_distribution": _normalize_counts(counts[context]),
            "risk_prime_mean": _safe_mean(risk_totals[context]),
        }
    return priors


def _normalize_counts(counts: Dict[str, int]) -> Dict[str, float]:
    total = sum(counts.values())
    if total <= 0:
        return {"ALLOW": 1 / 3, "QUARANTINE": 1 / 3, "DENY": 1 / 3}
    return {label: counts.get(label, 0) / total for label in ("ALLOW", "QUARANTINE", "DENY")}


def _safe_mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def predict_context_prior(priors: Dict[str, Any], rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    predictions: List[Dict[str, Any]] = []
    for row in rows:
        context = row["inputs"]["context"]
        prior = priors["contexts"].get(context) or priors["global"]
        distribution = prior["decision_distribution"]
        decision = max(distribution.items(), key=lambda item: item[1])[0]
        predictions.append(
            {
                "id": row["id"],
                "decision": decision,
                "decision_prob_allow": distribution.get("ALLOW", 0.0),
                "decision_prob_quarantine": distribution.get("QUARANTINE", 0.0),
                "decision_prob_deny": distribution.get("DENY", 0.0),
                "risk_prime_pred": prior["risk_prime_mean"],
            }
        )
    return predictions


def run_benchmark(output_dir: Path, group_count: int = 512, seed: int = 42) -> Dict[str, Path]:
    rows = build_governance_gate_dataset(group_count=group_count, seed=seed)
    dataset_dir = output_dir / "dataset"
    dataset_paths = write_governance_gate_dataset(rows, dataset_dir)

    train_rows = [row for row in rows if row["split"] == "train"]
    validation_rows = [row for row in rows if row["split"] == "validation"]
    test_rows = [row for row in rows if row["split"] == "test"]

    priors = fit_context_prior_baseline(train_rows)
    validation_predictions = predict_context_prior(priors, validation_rows)
    test_predictions = predict_context_prior(priors, test_rows)

    baseline_dir = output_dir / "baseline_context_prior"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    validation_pred_path = baseline_dir / "validation_predictions.jsonl"
    test_pred_path = baseline_dir / "test_predictions.jsonl"
    _write_jsonl(validation_pred_path, validation_predictions)
    _write_jsonl(test_pred_path, test_predictions)

    metrics = {
        "validation": compute_governance_gate_metrics(validation_rows, validation_predictions),
        "test": compute_governance_gate_metrics(test_rows, test_predictions),
    }
    metrics["dataset"] = summarize_governance_gate_dataset(rows)
    metrics["baseline"] = priors

    metrics_path = output_dir / "benchmark_summary.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "train": dataset_paths["train"],
        "validation": dataset_paths["validation"],
        "test": dataset_paths["test"],
        "dataset_summary": dataset_paths["summary"],
        "validation_predictions": validation_pred_path,
        "test_predictions": test_pred_path,
        "benchmark_summary": metrics_path,
    }


def _write_jsonl(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the local Governance Gate Prediction benchmark.")
    parser.add_argument("--group-count", type=int, default=512, help="Number of unique agent/topic groups.")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic generation seed.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ARTIFACTS_DIR / "governance_gate_prediction",
        help="Artifact directory for benchmark exports.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = run_benchmark(output_dir=args.output_dir, group_count=args.group_count, seed=args.seed)
    print("Governance Gate Prediction benchmark artifacts:")
    for name, path in outputs.items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
