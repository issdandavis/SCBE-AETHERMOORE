#!/usr/bin/env python3
"""Build buyer-ready evidence pack from governed browser runs + optional training report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SCBE evidence pack")
    parser.add_argument("--jobs-file", default="examples/aetherbrowse_tasks.sample.json")
    parser.add_argument("--output-root", default="artifacts/evidence_packs")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--url", default=None)
    parser.add_argument("--kernel-version", default="scbe-kernel-v1")
    parser.add_argument("--profile-id", default="default-safe")
    parser.add_argument("--training-run-dir", default=None, help="Optional training run dir with hf_training_metrics.json")
    return parser.parse_args()


def run_swarm_runner(args: argparse.Namespace, pack_dir: Path) -> Path:
    out_json = pack_dir / "aetherbrowse_summary.json"
    artifacts_root = pack_dir / "aetherbrowse_artifacts"
    screenshots = pack_dir / "screenshots"

    cmd = [
        sys.executable,
        "scripts/aetherbrowse_swarm_runner.py",
        "--jobs-file",
        args.jobs_file,
        "--artifact-root",
        str(artifacts_root),
        "--output-json",
        str(out_json),
        "--save-screenshots-dir",
        str(screenshots),
        "--kernel-version",
        args.kernel_version,
        "--profile-id",
        args.profile_id,
    ]
    if args.api_key:
        cmd.extend(["--api-key", args.api_key])
    if args.url:
        cmd.extend(["--url", args.url])

    subprocess.run(cmd, check=True)
    return out_json


def build_scorecard(summary: dict[str, Any], training: dict[str, Any] | None) -> dict[str, Any]:
    rows = [r for r in summary.get("results", []) if isinstance(r, dict)]
    decision_counts: dict[str, int] = {}
    scores: list[float] = []
    for row in rows:
        decision = str(row.get("decision", "UNKNOWN"))
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
        if row.get("verification_score") is not None:
            scores.append(float(row["verification_score"]))
    avg_score = (sum(scores) / len(scores)) if scores else 0.0

    out: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "browser_evidence": {
            "run_id": summary.get("run_id"),
            "total_jobs": int(summary.get("total_jobs", 0)),
            "success_jobs": int(summary.get("success_jobs", 0)),
            "failed_jobs": int(summary.get("failed_jobs", 0)),
            "decision_counts": decision_counts,
            "avg_verification_score": round(avg_score, 6),
        },
    }
    if training:
        growth = training.get("growth", {})
        out["training_evidence"] = {
            "run_id": training.get("run_id"),
            "sample_count": training.get("data", {}).get("sample_count"),
            "label_count": training.get("data", {}).get("label_count"),
            "growth_confirmed": bool(growth.get("confirmed", False)),
            "val_accuracy_gain": growth.get("val_accuracy_gain"),
            "val_loss_drop": growth.get("val_loss_drop"),
            "best_val_accuracy": growth.get("best_val_accuracy"),
            "best_epoch": growth.get("best_epoch"),
        }
    return out


def write_markdown(scorecard: dict[str, Any], path: Path) -> None:
    browser = scorecard["browser_evidence"]
    lines = [
        "# SCBE Evidence Pack Summary",
        "",
        f"- generated_at_utc: `{scorecard['generated_at_utc']}`",
        f"- browser_run_id: `{browser['run_id']}`",
        f"- total_jobs: `{browser['total_jobs']}`",
        f"- success_jobs: `{browser['success_jobs']}`",
        f"- failed_jobs: `{browser['failed_jobs']}`",
        f"- avg_verification_score: `{browser['avg_verification_score']}`",
        f"- decision_counts: `{json.dumps(browser['decision_counts'], sort_keys=True)}`",
    ]
    training = scorecard.get("training_evidence")
    if training:
        lines.extend(
            [
                "",
                "## Training Growth",
                f"- training_run_id: `{training['run_id']}`",
                f"- sample_count: `{training['sample_count']}`",
                f"- label_count: `{training['label_count']}`",
                f"- growth_confirmed: `{training['growth_confirmed']}`",
                f"- val_accuracy_gain: `{training['val_accuracy_gain']}`",
                f"- val_loss_drop: `{training['val_loss_drop']}`",
                f"- best_val_accuracy: `{training['best_val_accuracy']}` (epoch `{training['best_epoch']}`)",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pack_dir = Path(args.output_root) / run_id
    pack_dir.mkdir(parents=True, exist_ok=True)

    summary_path = run_swarm_runner(args, pack_dir)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    training_metrics = None
    if args.training_run_dir:
        t = Path(args.training_run_dir) / "hf_training_metrics.json"
        if t.exists():
            training_metrics = json.loads(t.read_text(encoding="utf-8"))

    scorecard = build_scorecard(summary, training_metrics)
    scorecard_path = pack_dir / "scorecard.json"
    scorecard_path.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")
    write_markdown(scorecard, pack_dir / "README.md")

    print("Evidence pack created:", pack_dir)
    print("Scorecard:", scorecard_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

