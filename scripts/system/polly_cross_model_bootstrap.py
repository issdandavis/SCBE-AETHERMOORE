#!/usr/bin/env python3
"""
Polly cross-model training bootstrap.

Purpose:
- Build a cross-model training funnel from game + lore + commerce data.
- Run governance audit before training.
- Optionally push dataset to Hugging Face.
- Optionally trigger Colab training.
- Optionally launch HYDRA multi-model trainer (dry-run/head/all).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = "training-data/funnel_cross_model"
DEFAULT_HF_REPO = "issdandavis/scbe-aethermoore-training-data"
DEFAULT_INCLUDE_GLOBS = [
    "training-data/game_sessions/**/*.jsonl",
    "training-data/game_design_sessions/**/*.jsonl",
    "training-data/gacha_sessions/**/*.jsonl",
    "training-data/lore_sessions/**/*.jsonl",
    "training-data/npc_roundtable_sessions/**/*.jsonl",
    "training-data/sidekick/**/*.jsonl",
    "training-data/hf-digimon-egg/**/*.jsonl",
    "training-data/space_commerce_sessions/**/*.jsonl",
    "training-data/dm_sessions/**/*.jsonl",
    "training-data/graphics_feedback/**/*.jsonl",
]
DEFAULT_EXCLUDE_GLOBS = [
    "training-data/funnel/**/*.jsonl",
    "training-data/funnel_cross_model/**/*.jsonl",
]


@dataclass
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "stdout_preview": self.stdout[-4000:],
            "stderr_preview": self.stderr[-2000:],
        }


def _run(cmd: list[str], cwd: Path) -> CommandResult:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
    )
    return CommandResult(
        command=cmd,
        returncode=int(proc.returncode),
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap Polly cross-model training")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Funnel output directory")
    parser.add_argument("--hf-repo", default=DEFAULT_HF_REPO, help="HF dataset repository")
    parser.add_argument("--max-records", type=int, default=0, help="Cap records in funnel build")
    parser.add_argument(
        "--run-trainer",
        choices=("none", "dry-run", "head", "all"),
        default="dry-run",
        help="HYDRA trainer mode",
    )
    parser.add_argument(
        "--head",
        choices=("KO", "AV", "RU", "CA", "UM", "DR"),
        default="KO",
        help="Head used when --run-trainer head",
    )
    parser.add_argument("--push-hf", action="store_true", help="Push funnel artifacts to HF dataset repo")
    parser.add_argument(
        "--trigger-colab",
        action="store_true",
        help="Trigger Colab after funnel build",
    )
    parser.add_argument("--tongue", default="KO", help="Tongue used for Colab trigger metadata")
    parser.add_argument("--colab-notebook-url", default="", help="Optional Colab notebook override")
    parser.add_argument("--push-model", action="store_true", help="Push trained adapters to HF (non dry-run modes)")
    parser.add_argument("--audit-threshold", type=float, default=0.78, help="Anomaly threshold for training_auditor")
    parser.add_argument(
        "--allow-quarantine",
        action="store_true",
        help="Continue training even when governance audit quarantines data",
    )
    parser.add_argument(
        "--include-glob",
        action="append",
        default=[],
        help="Additional include glob(s) for funnel builder",
    )
    return parser.parse_args()


def build_funnel(args: argparse.Namespace, repo_root: Path, output_dir: Path) -> CommandResult:
    try:
        output_arg = str(output_dir.relative_to(repo_root))
    except ValueError:
        output_arg = str(output_dir)

    cmd = [
        sys.executable,
        "scripts/build_hydra_training_funnel.py",
        "--repo-root",
        str(repo_root),
        "--output-dir",
        output_arg,
        "--hf-repo",
        args.hf_repo,
        "--tongue",
        args.tongue,
    ]

    include_globs = list(DEFAULT_INCLUDE_GLOBS) + list(args.include_glob or [])
    for pattern in include_globs:
        cmd.extend(["--include-glob", pattern])

    for pattern in DEFAULT_EXCLUDE_GLOBS:
        cmd.extend(["--exclude-glob", pattern])

    if args.max_records > 0:
        cmd.extend(["--max-records", str(int(args.max_records))])
    if args.push_hf:
        cmd.append("--push-hf")
    if args.trigger_colab:
        cmd.append("--trigger-colab")
    if args.colab_notebook_url.strip():
        cmd.extend(["--colab-notebook-url", args.colab_notebook_url.strip()])

    return _run(cmd, cwd=repo_root)


def run_audit(args: argparse.Namespace, repo_root: Path, merged_path: Path, audit_path: Path) -> CommandResult:
    cmd = [
        sys.executable,
        "scripts/training_auditor.py",
        "--jsonl",
        str(merged_path),
        "--threshold",
        str(args.audit_threshold),
        "--out",
        str(audit_path),
    ]
    return _run(cmd, cwd=repo_root)


def run_hydra_trainer(args: argparse.Namespace, repo_root: Path) -> CommandResult:
    cmd = [sys.executable, "training/vertex_hydra_trainer.py"]
    if args.run_trainer == "dry-run":
        cmd.append("--dry-run")
    elif args.run_trainer == "head":
        cmd.extend(["--head", args.head])
    elif args.run_trainer == "all":
        cmd.append("--all")

    if args.push_model and args.run_trainer in {"head", "all"}:
        cmd.append("--push")
    return _run(cmd, cwd=repo_root)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()
    output_dir = (repo_root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    started_utc = datetime.now(timezone.utc).isoformat()
    summary: dict[str, Any] = {
        "started_utc": started_utc,
        "repo_root": str(repo_root),
        "output_dir": str(output_dir),
        "config": {
            "hf_repo": args.hf_repo,
            "run_trainer": args.run_trainer,
            "head": args.head,
            "push_hf": bool(args.push_hf),
            "trigger_colab": bool(args.trigger_colab),
            "push_model": bool(args.push_model),
            "audit_threshold": float(args.audit_threshold),
            "allow_quarantine": bool(args.allow_quarantine),
        },
        "steps": {},
    }

    # Step 1: Build funnel
    funnel_result = build_funnel(args, repo_root, output_dir)
    summary["steps"]["build_funnel"] = funnel_result.to_dict()
    if funnel_result.returncode != 0:
        summary["status"] = "failed_build_funnel"
        report_path = output_dir / "cross_model_bootstrap_report.json"
        report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 1

    build_summary_path = output_dir / "build_summary.json"
    build_summary = _load_json(build_summary_path)
    summary["steps"]["funnel_summary"] = build_summary
    merged_path = output_dir / "merged_all.jsonl"
    if not merged_path.exists():
        summary["status"] = "failed_missing_merged_dataset"
        report_path = output_dir / "cross_model_bootstrap_report.json"
        report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 1

    # Step 2: Governance audit
    audit_path = output_dir / "merged_all.audit.json"
    audit_result = run_audit(args, repo_root, merged_path, audit_path)
    audit_report = _load_json(audit_path)
    summary["steps"]["audit"] = {
        "command": audit_result.command,
        "returncode": audit_result.returncode,
        "status": audit_report.get("status", "UNKNOWN"),
        "flagged_count": audit_report.get("flagged_count"),
        "flagged_ratio": audit_report.get("flagged_ratio"),
        "hashchain_root": audit_report.get("hashchain_root"),
        "report_path": str(audit_path),
    }

    quarantine = str(audit_report.get("status", "")).upper() == "QUARANTINE"
    if quarantine and not args.allow_quarantine:
        summary["status"] = "quarantined_stop"
        summary["message"] = "Dataset quarantined by governance audit. Use --allow-quarantine to force training."
        report_path = output_dir / "cross_model_bootstrap_report.json"
        report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 2

    # Step 3: Optional trainer
    if args.run_trainer != "none":
        train_result = run_hydra_trainer(args, repo_root)
        summary["steps"]["trainer"] = train_result.to_dict()
        if train_result.returncode != 0:
            summary["status"] = "trainer_failed"
            report_path = output_dir / "cross_model_bootstrap_report.json"
            report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            print(json.dumps(summary, indent=2))
            return 1

    summary["status"] = "ok"
    summary["finished_utc"] = datetime.now(timezone.utc).isoformat()
    report_path = output_dir / "cross_model_bootstrap_report.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary["report_path"] = str(report_path)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
