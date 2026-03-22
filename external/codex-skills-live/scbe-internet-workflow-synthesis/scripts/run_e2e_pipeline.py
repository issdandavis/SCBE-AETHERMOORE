#!/usr/bin/env python3
"""Run baseline web-research pipeline then tune system variables."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


THIS_DIR = Path(__file__).resolve().parent


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_in_repo(repo_root: Path, maybe_relative: str) -> Path:
    path = Path(maybe_relative)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def quote_cmd(cmd: Sequence[str]) -> str:
    return " ".join(shlex.quote(part) for part in cmd)


def run_cmd(cmd: list[str], cwd: Path, allow_returncodes: set[int]) -> int:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    print(proc.stdout, end="")
    if proc.returncode not in allow_returncodes:
        raise RuntimeError(f"Command failed ({proc.returncode}): {quote_cmd(cmd)}")
    return int(proc.returncode)


def latest_summary_path(repo_root: Path, run_root: str) -> Path:
    base = resolve_in_repo(repo_root, run_root)
    if not base.exists():
        raise RuntimeError(f"run root not found: {base}")
    candidates = []
    for child in base.iterdir():
        if child.is_dir():
            summary = child / "summary.json"
            if summary.exists():
                candidates.append(summary)
    if not candidates:
        raise RuntimeError(f"no summary.json found under: {base}")
    candidates.sort(key=lambda p: p.parent.name)
    return candidates[-1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SCBE internet workflow baseline + tuning")
    parser.add_argument("--repo-root", default=".", help="SCBE repo root")
    parser.add_argument("--profile", required=True, help="Pipeline profile JSON")
    parser.add_argument("--python-exe", default=sys.executable, help="Python executable for subprocesses")
    parser.add_argument("--skip-baseline", action="store_true", help="Skip baseline and tune from --summary")
    parser.add_argument("--summary", default="", help="Existing summary.json path (required with --skip-baseline)")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()
    profile_path = resolve_in_repo(repo_root, args.profile)
    profile = read_json(profile_path)

    web = profile.get("web_research", {})
    if not isinstance(web, dict):
        raise SystemExit("profile.web_research must be an object")

    tuning = profile.get("governance_tuning", {})
    if not isinstance(tuning, dict):
        raise SystemExit("profile.governance_tuning must be an object")

    summary_path: Path
    baseline_exit = None
    if args.skip_baseline:
        if not args.summary:
            raise SystemExit("--summary is required with --skip-baseline")
        summary_path = resolve_in_repo(repo_root, args.summary)
    else:
        baseline_cmd = [
            args.python_exe,
            "scripts/web_research_training_pipeline.py",
            "--max-per-topic",
            str(int(web.get("max_per_topic", 6) or 6)),
            "--backend",
            str(web.get("backend", "playwright")),
            "--max-tabs",
            str(int(web.get("max_tabs", 6) or 6)),
            "--run-root",
            str(web.get("run_root", "training/runs/web_research")),
            "--intake-dir",
            str(web.get("intake_dir", "training/intake/web_research")),
        ]

        topics = web.get("topics", [])
        if isinstance(topics, list) and topics:
            baseline_cmd.append("--topics")
            baseline_cmd.extend([str(item) for item in topics if str(item).strip()])

        query = str(web.get("query", "") or "").strip()
        if query:
            baseline_cmd.extend(["--query", query])

        if bool(web.get("skip_core_check", False)):
            baseline_cmd.append("--skip-core-check")

        n8n_webhook = str(web.get("n8n_webhook", "") or "").strip()
        if n8n_webhook:
            baseline_cmd.extend(["--n8n-webhook", n8n_webhook])

        if args.dry_run:
            print(f"[dry-run] baseline: {quote_cmd(baseline_cmd)}")
            run_root = resolve_in_repo(
                repo_root, str(web.get("run_root", "training/runs/web_research"))
            )
            summary_path = run_root / "<run_id>" / "summary.json"
        else:
            baseline_exit = run_cmd(baseline_cmd, cwd=repo_root, allow_returncodes={0, 2})
            summary_path = latest_summary_path(
                repo_root, str(web.get("run_root", "training/runs/web_research"))
            )

    config_path = resolve_in_repo(
        repo_root, str(tuning.get("cloud_kernel_config", "training/cloud_kernel_pipeline.json"))
    )
    output_config_path = resolve_in_repo(
        repo_root,
        str(tuning.get("output_cloud_kernel_config", "training/cloud_kernel_pipeline.tuned.json")),
    )
    output_report_path = resolve_in_repo(
        repo_root,
        str(tuning.get("output_report", "artifacts/internet_workflow_tuning_report.json")),
    )
    output_runtime_path = resolve_in_repo(
        repo_root,
        str(tuning.get("output_runtime_profile", "training/internet_workflow_profile.tuned.json")),
    )

    tune_cmd = [
        args.python_exe,
        str((THIS_DIR / "tune_system_variables.py").resolve()),
        "--summary",
        str(summary_path),
        "--config",
        str(config_path),
        "--output-config",
        str(output_config_path),
        "--runtime-profile",
        str(profile_path),
        "--output-runtime-profile",
        str(output_runtime_path),
        "--target-quarantine-ratio",
        str(float(tuning.get("target_quarantine_ratio", 0.08))),
        "--output-report",
        str(output_report_path),
    ]

    if args.dry_run:
        print(f"[dry-run] tune: {quote_cmd(tune_cmd)}")
    else:
        run_cmd(tune_cmd, cwd=repo_root, allow_returncodes={0})

    result = {
        "status": "ok",
        "baseline_exit_code": baseline_exit,
        "summary_path": str(summary_path),
        "tuned_config": str(output_config_path),
        "tuning_report": str(output_report_path),
        "tuned_runtime_profile": str(output_runtime_path),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
