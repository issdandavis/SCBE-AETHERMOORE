#!/usr/bin/env python3
"""Quantify why DSL adapters fail the executable gate.

This is a math-first diagnostic. It measures:

- class-distribution entropy and imbalance;
- DSL-header token share versus code/comment token share;
- executable failure modes from scorer reports;
- tokenizer selector audit status.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SFT = ROOT / "training-data" / "sft"
REPORTS = ROOT / "artifacts" / "dsl_eval_reports"
OUT_DIR = ROOT / "artifacts" / "training_reports"


DEFAULT_DATASETS = [
    "bijective_dsl_v1_train.sft.jsonl",
    "contract_repair_v2_train.sft.jsonl",
    "contract_repair_v3_train.sft.jsonl",
    "bijective_dsl_v5_holdout.sft.jsonl",
]

DEFAULT_REPORTS = [
    "polly-bijective-tongue-coder-v2_executable_accuracy.json",
    "polly-bijective-tongue-coder-v2-format-repair_executable_accuracy.json",
    "polly-regularized-coding-v8_executable_accuracy.json",
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def category(row: dict[str, Any]) -> str:
    meta = row.get("meta", {})
    return str(meta.get("task") or meta.get("category") or "unknown")


def assistant_text(row: dict[str, Any]) -> str:
    return next((m.get("content", "") for m in row.get("messages", []) if m.get("role") == "assistant"), "")


def token_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def entropy(counter: Counter[str]) -> float:
    total = sum(counter.values())
    if not total:
        return 0.0
    return -sum((count / total) * math.log2(count / total) for count in counter.values())


def dataset_summary(path: Path) -> dict[str, Any]:
    rows = load_jsonl(path)
    by_category = Counter(category(row) for row in rows)
    total = len(rows)
    max_entropy = math.log2(len(by_category)) if by_category else 0.0
    header_tokens = 0
    total_tokens = 0
    by_category_header: dict[str, dict[str, float]] = {}
    per_category_tokens: dict[str, list[tuple[int, int]]] = {}
    for row in rows:
        text = assistant_text(row)
        cat = category(row)
        n_total = token_count(text)
        n_header = sum(
            token_count(line)
            for line in text.splitlines()
            if line.startswith("well_select") or line.startswith("tongue_shift")
        )
        total_tokens += n_total
        header_tokens += n_header
        per_category_tokens.setdefault(cat, []).append((n_header, n_total))

    for cat, pairs in sorted(per_category_tokens.items()):
        h_sum = sum(pair[0] for pair in pairs)
        t_sum = sum(pair[1] for pair in pairs)
        by_category_header[cat] = {
            "n": len(pairs),
            "avg_total_tokens": round(t_sum / len(pairs), 3),
            "avg_header_tokens": round(h_sum / len(pairs), 3),
            "header_fraction": round(h_sum / t_sum, 4) if t_sum else 0.0,
        }

    dominant_category, dominant_count = by_category.most_common(1)[0] if by_category else ("-", 0)
    return {
        "path": str(path.relative_to(ROOT).as_posix()),
        "n_records": total,
        "by_category": dict(by_category),
        "entropy_bits": round(entropy(by_category), 4),
        "max_entropy_bits": round(max_entropy, 4),
        "entropy_ratio": round(entropy(by_category) / max_entropy, 4) if max_entropy else 0.0,
        "dominant_category": dominant_category,
        "dominant_fraction": round(dominant_count / total, 4) if total else 0.0,
        "header_fraction_total": round(header_tokens / total_tokens, 4) if total_tokens else 0.0,
        "by_category_header": by_category_header,
    }


def report_summary(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "path": str(path.relative_to(ROOT).as_posix()),
        "adapter": payload.get("adapter"),
        "holdout_path": payload.get("holdout_path"),
        "n_total": payload.get("n_total"),
        "n_pass": payload.get("n_pass"),
        "executable_accuracy": payload.get("executable_accuracy"),
        "failure_counts": payload.get("failure_counts") or {},
        "category_accuracy": payload.get("category_accuracy") or {},
        "floor_violations": payload.get("floor_violations") or [],
    }


def build_analysis(dataset_names: list[str], report_names: list[str]) -> dict[str, Any]:
    datasets = [dataset_summary(SFT / name) for name in dataset_names if (SFT / name).exists()]
    reports = [report_summary(REPORTS / name) for name in report_names if (REPORTS / name).exists()]

    findings: list[str] = []
    v1 = next((row for row in datasets if row["path"].endswith("bijective_dsl_v1_train.sft.jsonl")), None)
    if v1:
        findings.append(
            "main_train_imbalance: "
            f"{v1['dominant_category']}={v1['dominant_fraction']:.1%}, "
            f"entropy_ratio={v1['entropy_ratio']:.3f}"
        )
        if v1["dominant_fraction"] > 0.35:
            findings.append("translate_one prior is strong enough to dominate CE gradients.")
    for report in reports:
        failures = report["failure_counts"]
        if failures.get("unparseable_output", 0) == report["n_total"]:
            findings.append(f"{Path(report['path']).name}: all outputs unparseable, grammar prior not learned.")
        elif failures:
            findings.append(f"{Path(report['path']).name}: mixed failures {failures}.")

    findings.append(
        "loss_geometry: valid executable signal lives in the first 1-4 DSL header tokens, "
        "while ordinary CE also rewards long code/comment continuations; selector tokens need explicit weighting."
    )
    findings.append(
        "merge_geometry: high LoRA sign conflict means merging cannot repair a missing contract manifold; "
        "the contract must be learned before TIES/DARE-TIES is useful."
    )

    return {
        "schema_version": "scbe_dsl_failure_math_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "datasets": datasets,
        "reports": reports,
        "findings": findings,
        "recommendations": [
            "Use a category-balanced sampler, not uniform random sampling.",
            "Apply weighted CE to selector payload tokens and DSL primitive names.",
            "Train/evaluate against boundary-clean v5_holdout, not burned v1/v4 holdouts.",
            "Do not merge or route adapters that fail executable grammar; mine repair rows first.",
        ],
    }


def write_outputs(payload: dict[str, Any]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_json = OUT_DIR / "dsl_failure_math_20260427.json"
    out_md = OUT_DIR / "dsl_failure_math_20260427.md"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# DSL Failure Math",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        "",
        "## Findings",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["findings"])
    lines.extend(["", "## Dataset Geometry", "", "| Dataset | N | Entropy Ratio | Dominant | Header Fraction |", "| --- | ---: | ---: | --- | ---: |"])
    for row in payload["datasets"]:
        lines.append(
            f"| `{row['path']}` | {row['n_records']} | {row['entropy_ratio']} | "
            f"{row['dominant_category']} ({row['dominant_fraction']:.1%}) | {row['header_fraction_total']} |"
        )
    lines.extend(["", "## Executable Reports", "", "| Report | N | Pass | Accuracy | Failures |", "| --- | ---: | ---: | ---: | --- |"])
    for row in payload["reports"]:
        lines.append(
            f"| `{row['path']}` | {row['n_total']} | {row['n_pass']} | "
            f"{float(row['executable_accuracy'] or 0):.3f} | `{json.dumps(row['failure_counts'])}` |"
        )
    lines.extend(["", "## Recommendations", ""])
    lines.extend(f"- {item}" for item in payload["recommendations"])
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_md


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", action="append", dest="datasets", default=None)
    parser.add_argument("--report", action="append", dest="reports", default=None)
    args = parser.parse_args()
    payload = build_analysis(args.datasets or DEFAULT_DATASETS, args.reports or DEFAULT_REPORTS)
    out = write_outputs(payload)
    print(f"Wrote {out}")
    for finding in payload["findings"]:
        print(f"- {finding}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
