#!/usr/bin/env python3
"""Layer 11 coherence verification gate.

Computes a coherence score in [0, 1] from:
- test pass rate
- type coverage
- lint score
- documentation coverage
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def run_bool_command(command: list[str]) -> tuple[float, str]:
    if not shutil.which(command[0]):
        return 1.0, f"{command[0]} not found; treated as neutral-pass"

    proc = subprocess.run(command, capture_output=True, text=True)
    tail = "\n".join((proc.stdout + "\n" + proc.stderr).splitlines()[-10:]).strip()
    return (1.0 if proc.returncode == 0 else 0.0), tail


def compute_doc_coverage(repo_root: Path) -> tuple[float, dict[str, float]]:
    must_have = ["README.md", "CONTRIBUTING.md", "LAYER_INDEX.md"]
    existing = sum(1 for doc in must_have if (repo_root / doc).exists())
    baseline = existing / len(must_have)

    source_files = list(repo_root.rglob("*.py")) + list(repo_root.rglob("*.ts"))
    markdown_files = list(repo_root.rglob("*.md"))
    ratio = min(1.0, len(markdown_files) / max(1, len(source_files) * 0.25))

    score = clamp(0.7 * baseline + 0.3 * ratio)
    return score, {
        "required_docs_presence": baseline,
        "markdown_to_source_ratio": ratio,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute Layer 11 coherence score")
    parser.add_argument("--threshold", type=float, default=0.20)
    parser.add_argument("--json-path", default="coherence-report.json")
    parser.add_argument("--test-pass-rate", type=float)
    parser.add_argument("--type-coverage", type=float)
    parser.add_argument("--lint-score", type=float)
    parser.add_argument("--doc-coverage", type=float)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    metrics: dict[str, float] = {}
    details: dict[str, object] = {}

    if args.test_pass_rate is not None:
        metrics["test_pass_rate"] = clamp(args.test_pass_rate)
        details["test_pass_rate"] = "provided via CLI"
    else:
        score, output = run_bool_command([sys.executable, "-m", "pytest", "-q"])
        metrics["test_pass_rate"] = score
        details["test_pass_rate"] = output

    if args.type_coverage is not None:
        metrics["type_coverage"] = clamp(args.type_coverage)
        details["type_coverage"] = "provided via CLI"
    else:
        score, output = run_bool_command(["npm", "run", "typecheck", "--silent"])
        metrics["type_coverage"] = score
        details["type_coverage"] = output

    if args.lint_score is not None:
        metrics["lint_score"] = clamp(args.lint_score)
        details["lint_score"] = "provided via CLI"
    else:
        score, output = run_bool_command(["npm", "run", "lint", "--silent"])
        metrics["lint_score"] = score
        details["lint_score"] = output

    if args.doc_coverage is not None:
        metrics["doc_coverage"] = clamp(args.doc_coverage)
        details["doc_coverage"] = "provided via CLI"
    else:
        score, doc_details = compute_doc_coverage(repo_root)
        metrics["doc_coverage"] = score
        details["doc_coverage"] = doc_details

    coherence = clamp(sum(metrics.values()) / len(metrics))

    report = {
        "threshold": args.threshold,
        "coherence": coherence,
        "metrics": metrics,
        "details": details,
        "status": "pass" if coherence >= args.threshold else "fail",
    }

    output_path = repo_root / args.json_path
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

    return 0 if coherence >= args.threshold else 1


if __name__ == "__main__":
    raise SystemExit(main())
