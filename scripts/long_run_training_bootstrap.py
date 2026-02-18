#!/usr/bin/env python3
"""Bootstrap long-run training across Hugging Face, Vertex, Kubernetes, and AWS.

The default mode is dry-run so this is safe to run from your terminal at night and
review what would execute before launching any provider jobs.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PLAN_PATH = Path("training/long_run_multicloud_training_plan.json")
DEFAULT_RUN_ROOT = Path("training/runs")
TIMESTAMP_FORMAT = "%Y%m%d-%H%M%SZ"


@dataclass
class ProviderResult:
    provider_id: str
    provider_name: str
    status: str
    command: str | None = None
    log_file: str | None = None
    pid: int | None = None
    reasons: list[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run long-form multi-cloud training plan")
    parser.add_argument(
        "--plan",
        default=str(DEFAULT_PLAN_PATH),
        help="Path to training plan JSON",
    )
    parser.add_argument(
        "--hours",
        type=float,
        default=None,
        help="Training wall-time budget for all providers",
    )
    parser.add_argument(
        "--providers",
        default="",
        help="Comma-separated provider IDs to run (defaults to all active providers)",
    )
    parser.add_argument(
        "--run-root",
        default=str(DEFAULT_RUN_ROOT),
        help="Directory where run artifacts/logs are written",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render commands and requirements only (default behavior)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute selected commands (this starts real jobs)",
    )
    parser.add_argument(
        "--allow-pending",
        action="store_true",
        help="Include providers marked as pending in the plan",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for each executed process to exit (not recommended for 8h jobs)",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only print the manifest summary and skip launch logic",
    )
    return parser.parse_args()


def load_plan(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("providers"), list):
        raise ValueError(f"Plan file {path} is missing a top-level providers array")
    return data


def normalize_provider_ids(raw: str) -> set[str]:
    return {item.strip() for item in raw.split(",") if item.strip()}


def build_context(plan: dict[str, Any], args: argparse.Namespace, repo_root: Path, run_root: Path) -> dict[str, str]:
    return {
        "program_name": plan.get("program_name", "scbe-training"),
        "duration_hours": str(args.hours or plan.get("default_duration_hours", 8)),
        "run_root": str(run_root),
        "run_dir": str(run_root),
        "repo_root": str(repo_root),
        "timestamp": datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT),
        "vertex_command_args": "--dry-run" if args.dry_run else "",
    }


def substitute_command(command: str, context: dict[str, str]) -> str:
    try:
        return command.format(**context)
    except KeyError as exc:
        raise ValueError(f"Missing placeholder in command: {exc.args[0]}")


def resolve_selection(plan: dict[str, Any], requested: set[str], allow_pending: bool) -> list[dict[str, Any]]:
    providers = []
    selected = requested if requested else None

    for provider in plan["providers"]:
        provider_id = provider.get("id")
        if not provider_id:
            continue
        if selected and provider_id not in selected:
            continue
        if not allow_pending and provider.get("status") == "pending":
            continue
        providers.append(provider)

    return providers


def validate_requested_providers(plan: dict[str, Any], requested: set[str]) -> list[str]:
    available = {provider.get("id") for provider in plan["providers"] if provider.get("id")}
    return sorted(requested - available)


def required_missing(commands: list[str], env_vars: list[str]) -> tuple[list[str], list[str]]:
    missing_tools = [tool for tool in commands if shutil.which(tool) is None]
    missing_env = [var for var in env_vars if not os.environ.get(var)]
    return missing_tools, missing_env


def run_provider(
    provider: dict[str, Any],
    context: dict[str, str],
    repo_root: Path,
    dry_run: bool,
    wait: bool,
) -> ProviderResult:
    provider_id = provider["id"]
    provider_name = provider.get("name", provider_id)
    result = ProviderResult(provider_id=provider_id, provider_name=provider_name, status="skipped")

    rendered_command = substitute_command(provider["command"], context)
    result.command = rendered_command

    working_directory = repo_root / provider.get("working_directory", ".")
    required_tools = provider.get("required_tools", [])
    required_env = provider.get("required_env", [])
    missing_tools, missing_env = required_missing(required_tools, required_env)
    if missing_tools:
        result.reasons.append(f"missing tools: {', '.join(missing_tools)}")
    if missing_env:
        result.reasons.append(f"missing env vars: {', '.join(missing_env)}")
    if missing_tools or missing_env:
        return result

    result.status = "planned"
    if dry_run:
        return result

    log_dir = Path(context["run_root"]) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{provider_id}.log"
    proc_env = os.environ.copy()

    proc = subprocess.Popen(
        rendered_command,
        cwd=str(working_directory),
        shell=True,
        stdout=log_path.open("w", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        env=proc_env,
    )
    result.status = "running" if not wait else "completed"
    result.pid = proc.pid
    result.log_file = str(log_path)

    if wait:
        return_code = proc.wait()
        result.status = "completed" if return_code == 0 else f"failed:{return_code}"
    return result


def write_summary(plan: dict[str, Any], results: list[ProviderResult], run_root: Path, dry_run: bool) -> Path:
    report = {
        "plan": {
            "program_name": plan.get("program_name"),
            "program_version": plan.get("program_version"),
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "dry_run": dry_run,
        },
        "providers": [
            {
                "id": item.provider_id,
                "name": item.provider_name,
                "status": item.status,
                "command": item.command,
                "pid": item.pid,
                "log_file": item.log_file,
                "notes": item.reasons,
            }
            for item in results
        ],
    }

    run_root.mkdir(parents=True, exist_ok=True)
    report_path = run_root / "training_bootstrap_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report_path


def print_summary(results: list[ProviderResult], report_path: Path) -> None:
    print("\nBootstrapping summary:")
    for item in results:
        reasons = f" ({', '.join(item.reasons)})" if item.reasons else ""
        print(f"- {item.provider_id}: {item.status}{reasons}")
        if item.command:
            print(f"  cmd: {item.command}")
        if item.pid:
            print(f"  pid: {item.pid}")
        if item.log_file:
            print(f"  log: {item.log_file}")
    print(f"\nReport written to: {report_path}")


def main() -> int:
    args = parse_args()
    if args.execute and args.dry_run:
        raise SystemExit("--execute and --dry-run are mutually exclusive")

    if not args.execute and not args.dry_run and not args.summary_only:
        args.dry_run = True

    repo_root = Path(__file__).resolve().parents[1]
    plan_path = Path(args.plan)
    if not plan_path.is_absolute():
        plan_path = (repo_root / plan_path).resolve()

    plan = load_plan(plan_path)
    requested_providers = normalize_provider_ids(args.providers)
    unknown = validate_requested_providers(plan, requested_providers)
    if unknown:
        raise SystemExit(f"Unknown provider IDs requested: {', '.join(unknown)}")
    run_root = Path(args.run_root)
    if not run_root.is_absolute():
        run_root = (repo_root / run_root).resolve()

    run_id = datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)
    selected = resolve_selection(
        plan,
        requested=requested_providers,
        allow_pending=args.allow_pending,
    )
    if not selected:
        raise SystemExit("No providers selected by this invocation.")

    context = build_context(plan=plan, args=args, repo_root=repo_root, run_root=run_root / run_id)
    results = []

    if args.summary_only:
        print("Plan:", plan_path)
        print("Run ID:", run_id)
        print("Duration:", context["duration_hours"], "hours")
        for provider in selected:
            print(f"- {provider.get('id')} ({provider.get('status')}): {provider.get('name')}")
        return 0

    for provider in selected:
        results.append(
            run_provider(
                provider=provider,
                context=context,
                repo_root=repo_root,
                dry_run=args.dry_run,
                wait=args.wait,
            )
        )

    report_path = write_summary(plan, results, Path(context["run_root"]), args.dry_run)
    print_summary(results, report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
