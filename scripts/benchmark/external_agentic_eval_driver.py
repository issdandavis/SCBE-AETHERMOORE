#!/usr/bin/env python3
"""Adapter scaffold for SWE-bench / Terminal-Bench style agentic evals.

This driver gives SCBE a first-class external-eval lane without claiming public
leaderboard parity. It validates manifests, records sandbox policy, and can run
local verifier commands only when explicitly requested.
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
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.crypto.sacred_tongue_payload_bijection import prove_dict  # noqa: E402

DEFAULT_MANIFEST = (
    REPO_ROOT / "config" / "eval" / "external_agentic_eval_tasks.sample.json"
)
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "external_agentic_eval"
SUITES = {"swe_bench", "terminal_bench", "repo_native"}
SANDBOXES = {"host", "docker", "github_actions"}


@dataclass(frozen=True)
class ExternalEvalTask:
    task_id: str
    suite: str
    title: str
    repo: str
    instructions: str
    verify_command: list[str]
    sandbox: str
    expected_artifacts: list[str]
    max_attempts: int
    critic: bool
    rerank: bool


def load_manifest(path: Path) -> list[ExternalEvalTask]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("tasks") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("manifest must be a list or an object with tasks")
    tasks: list[ExternalEvalTask] = []
    for row in rows:
        suite = str(row["suite"])
        sandbox = str(row.get("sandbox", "docker"))
        if suite not in SUITES:
            raise ValueError(f"unknown suite for {row.get('task_id')}: {suite}")
        if sandbox not in SANDBOXES:
            raise ValueError(f"unknown sandbox for {row.get('task_id')}: {sandbox}")
        verify = row.get("verify_command", [])
        if not isinstance(verify, list) or not all(isinstance(x, str) for x in verify):
            raise ValueError(
                f"verify_command must be list[str] for {row.get('task_id')}"
            )
        tasks.append(
            ExternalEvalTask(
                task_id=str(row["task_id"]),
                suite=suite,
                title=str(row.get("title", row["task_id"])),
                repo=str(row.get("repo", "")),
                instructions=str(row.get("instructions", "")),
                verify_command=verify,
                sandbox=sandbox,
                expected_artifacts=[str(x) for x in row.get("expected_artifacts", [])],
                max_attempts=max(1, int(row.get("max_attempts", 3))),
                critic=bool(row.get("critic", True)),
                rerank=bool(row.get("rerank", True)),
            )
        )
    return tasks


def validate_tasks(tasks: list[ExternalEvalTask]) -> dict[str, Any]:
    problems: list[str] = []
    seen: set[str] = set()
    for task in tasks:
        if task.task_id in seen:
            problems.append(f"duplicate task_id: {task.task_id}")
        seen.add(task.task_id)
        if task.suite in {"swe_bench", "terminal_bench"} and task.sandbox == "host":
            problems.append(
                f"{task.task_id}: external evals should not default to host sandbox"
            )
        if not task.instructions:
            problems.append(f"{task.task_id}: missing instructions")
        if not task.verify_command:
            problems.append(f"{task.task_id}: missing verify_command")
    return {"ok": not problems, "task_count": len(tasks), "problems": problems}


def run_task(task: ExternalEvalTask, execute: bool) -> dict[str, Any]:
    base = {
        "task_id": task.task_id,
        "suite": task.suite,
        "title": task.title,
        "repo": task.repo,
        "sandbox": task.sandbox,
        "trajectory_scaling": {
            "max_attempts": task.max_attempts,
            "critic": task.critic,
            "rerank": task.rerank,
        },
        "expected_artifacts": task.expected_artifacts,
        "parity_claim": "not_claimed",
    }
    if not execute:
        return {**base, "status": "planned", "ok": True}
    if task.sandbox != "host":
        return {
            **base,
            "status": "not_executed",
            "ok": True,
            "reason": "non-host sandbox adapter is planned but not executed by this local driver",
        }
    proc = subprocess.run(
        task.verify_command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=600,
        check=False,
    )
    return {
        **base,
        "status": "executed",
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-2500:],
        "stderr_tail": proc.stderr[-2500:],
    }


def write_report(
    tasks: list[ExternalEvalTask], output_root: Path, execute: bool
) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    results = [run_task(task, execute) for task in tasks]
    payload = {
        "schema_version": "scbe_external_agentic_eval_v1",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "execute": execute,
        "ok": all(row.get("ok") for row in results),
        "limits": [
            "SWE-bench and Terminal-Bench parity is not claimed until their official task runners are wired.",
            "Docker/GitHub Actions sandboxes are represented as policy here; this local script only executes host verifiers.",
        ],
        "results": results,
    }
    core = {k: v for k, v in payload.items() if k != "sacred_tongue_bijection"}
    payload["sacred_tongue_bijection"] = prove_dict(core)
    report_path = output_root / "latest_report.json"
    report_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    md = [
        "# External Agentic Eval Adapter",
        "",
        "| Task | Suite | Sandbox | Status | Attempts | Parity |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for row in results:
        md.append(
            f"| `{row['task_id']}` | `{row['suite']}` | `{row['sandbox']}` | `{row['status']}` | "
            f"{row['trajectory_scaling']['max_attempts']} | `{row['parity_claim']}` |"
        )
    st = payload.get("sacred_tongue_bijection") or {}
    md.extend(
        [
            "",
            "## Sacred Tongue bijection (canonical report JSON)",
            "",
            f"- **ok**: `{st.get('ok')}`",
            f"- **sha256**: `{st.get('canonical_sha256', '')}`",
            "",
        ]
    )
    md_path = output_root / "latest_report.md"
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"payload": payload, "json": str(report_path), "markdown": str(md_path)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument(
        "--execute", action="store_true", help="Execute host-sandbox verifier commands."
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    tasks = load_manifest(args.manifest)
    validation = validate_tasks(tasks)
    if args.validate_only:
        print(json.dumps(validation, indent=2, sort_keys=True))
        return 0 if validation["ok"] else 1
    if not validation["ok"]:
        print(json.dumps(validation, indent=2, sort_keys=True))
        return 1
    report = write_report(tasks, args.output_root, execute=args.execute)
    print(
        json.dumps(
            {
                "ok": report["payload"]["ok"],
                "json": report["json"],
                "markdown": report["markdown"],
            },
            indent=2,
        )
    )
    return 0 if report["payload"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
