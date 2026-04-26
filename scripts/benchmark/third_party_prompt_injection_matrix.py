#!/usr/bin/env python3
"""Third-party prompt-injection benchmark matrix.

This runner is intentionally separate from the repo-native adversarial corpus.
It loads public Hugging Face datasets and compares SCBE against optional real
external detector models on the same rows.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.adversarial.attack_corpus import BASELINE_CLEAN  # noqa: E402
from tests.adversarial.scbe_harness import SCBEDetectionGate  # noqa: E402

DATASET_SPECS = {
    "deepset/prompt-injections": {
        "splits": ["train", "test"],
        "text_field": "text",
        "label_field": "label",
        "positive_values": {1, "1", "injection", "malicious"},
    },
    "zachz/prompt-injection-benchmark": {
        "splits": ["train"],
        "text_field": "text",
        "label_field": "label",
        "positive_values": {"injection", "malicious", "attack", "jailbreak"},
    },
}


@dataclass
class Counts:
    true_positive: int = 0
    false_positive: int = 0
    true_negative: int = 0
    false_negative: int = 0

    def add(self, expected_attack: bool, predicted_block: bool) -> None:
        if expected_attack and predicted_block:
            self.true_positive += 1
        elif expected_attack and not predicted_block:
            self.false_negative += 1
        elif not expected_attack and predicted_block:
            self.false_positive += 1
        else:
            self.true_negative += 1

    def metrics(self) -> dict[str, Any]:
        total = (
            self.true_positive
            + self.false_positive
            + self.true_negative
            + self.false_negative
        )
        attacks = self.true_positive + self.false_negative
        clean = self.true_negative + self.false_positive
        precision = self.true_positive / max(
            self.true_positive + self.false_positive, 1
        )
        recall = self.true_positive / max(attacks, 1)
        fpr = self.false_positive / max(clean, 1)
        accuracy = (self.true_positive + self.true_negative) / max(total, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-12)
        return {
            "total": total,
            "attacks": attacks,
            "clean": clean,
            "true_positive": self.true_positive,
            "false_positive": self.false_positive,
            "true_negative": self.true_negative,
            "false_negative": self.false_negative,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "false_positive_rate": round(fpr, 4),
            "accuracy": round(accuracy, 4),
            "f1": round(f1, 4),
        }


def _load_rows(dataset_name: str, max_rows: int | None) -> list[dict[str, Any]]:
    from datasets import load_dataset

    spec = DATASET_SPECS[dataset_name]
    dataset = load_dataset(dataset_name)
    rows: list[dict[str, Any]] = []
    for split in spec["splits"]:
        for item in dataset[split]:
            label = item[spec["label_field"]]
            rows.append(
                {
                    "dataset": dataset_name,
                    "split": split,
                    "text": str(item[spec["text_field"]]),
                    "expected_attack": label in spec["positive_values"],
                    "raw_label": label,
                }
            )
            if max_rows is not None and len(rows) >= max_rows:
                return rows
    return rows


def _score_scbe(rows: Iterable[dict[str, Any]]) -> tuple[Counts, float]:
    gate = SCBEDetectionGate()
    gate.calibrate([item["prompt"] for item in BASELINE_CLEAN])
    counts = Counts()
    start = time.perf_counter()
    for row in rows:
        gate.reset_session()
        result = gate.process(row["text"])
        counts.add(row["expected_attack"], result.detected)
    return counts, (time.perf_counter() - start) * 1000


def _load_protectai():
    from transformers import pipeline

    return pipeline(
        "text-classification",
        model="protectai/deberta-v3-base-prompt-injection-v2",
        device=-1,
    )


def _protectai_blocks(model: Any, text: str) -> bool:
    result = model(text[:512])
    label_scores = {str(item["label"]).lower(): float(item["score"]) for item in result}
    if "injection" in label_scores:
        return label_scores["injection"] > 0.5
    if "label_1" in label_scores:
        return label_scores["label_1"] > 0.5
    return any(
        "inject" in label and score > 0.5 for label, score in label_scores.items()
    )


def _score_protectai(
    rows: Iterable[dict[str, Any]],
) -> tuple[Counts, float, dict[str, str]]:
    model = _load_protectai()
    counts = Counts()
    start = time.perf_counter()
    for row in rows:
        counts.add(row["expected_attack"], _protectai_blocks(model, row["text"]))
    return (
        counts,
        (time.perf_counter() - start) * 1000,
        {"mode": "external", "model": "protectai/deberta-v3-base-prompt-injection-v2"},
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    datasets = args.datasets or list(DATASET_SPECS)
    report: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "datasets": {},
        "include_protectai": args.include_protectai,
        "max_rows_per_dataset": args.max_rows,
    }

    for dataset_name in datasets:
        rows = _load_rows(dataset_name, args.max_rows)
        scbe_counts, scbe_ms = _score_scbe(rows)
        dataset_report: dict[str, Any] = {
            "rows": len(rows),
            "scbe": {**scbe_counts.metrics(), "latency_ms_total": round(scbe_ms, 3)},
        }
        if args.include_protectai:
            protectai_counts, protectai_ms, lane_status = _score_protectai(rows)
            dataset_report["protectai"] = {
                **protectai_counts.metrics(),
                "latency_ms_total": round(protectai_ms, 3),
                "lane_status": lane_status,
            }
        report["datasets"][dataset_name] = dataset_report
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="*", choices=sorted(DATASET_SPECS))
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--include-protectai", action="store_true")
    parser.add_argument(
        "--output",
        default="artifacts/benchmark/third_party_prompt_injection_matrix/report.json",
    )
    args = parser.parse_args()

    report = run(args)
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
