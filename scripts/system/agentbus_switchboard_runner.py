#!/usr/bin/env python3
"""Run local/free AgentBus switchboard workflows.

A switchboard workflow is a domino chain: each step hits one known command or
AgentBus route, records receipts, contributes compact bullets, and then lights
the next step. It is intentionally local/free-first.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKFLOW = REPO_ROOT / "config" / "system" / "agent_bus_switchboard_free_v1.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "agent_bus" / "switchboard"


def utc_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_json_maybe(text: str) -> Any | None:
    try:
        return json.loads((text or "").strip())
    except Exception:
        return None


def step_map(workflow: dict[str, Any]) -> dict[str, dict[str, Any]]:
    steps = workflow.get("steps", [])
    if not isinstance(steps, list):
        raise ValueError("workflow.steps must be a list")
    mapped = {}
    for step in steps:
        if not isinstance(step, dict) or not step.get("id"):
            raise ValueError("every workflow step must be an object with id")
        mapped[str(step["id"])] = step
    return mapped


def render_task(step: dict[str, Any], bullets: list[str], failed_step: str = "") -> str:
    base = str(step.get("task", "")).strip()
    context = "\n".join(f"- {bullet}" for bullet in bullets[-24:])
    if context:
        base = f"{base}\n\nPrior accepted bullets:\n{context}"
    if failed_step:
        base = f"{base}\n\nFailed step id: {failed_step}"
    return base


def run_command(command: list[str], *, timeout: int, dry_run: bool) -> dict[str, Any]:
    command = resolve_command(command)
    if dry_run:
        return {
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "timed_out": False,
            "dry_run": True,
            "command": command,
        }
    try:
        proc = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
            "dry_run": False,
            "command": command,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
            "dry_run": False,
            "command": command,
        }


def resolve_command(command: list[str]) -> list[str]:
    if not command:
        return command
    executable = command[0]
    if Path(executable).is_file():
        return command
    resolved = shutil.which(executable)
    if resolved:
        return [resolved, *command[1:]]
    if sys.platform.startswith("win") and not executable.lower().endswith((".exe", ".cmd", ".bat")):
        for suffix in (".cmd", ".exe", ".bat"):
            resolved = shutil.which(f"{executable}{suffix}")
            if resolved:
                return [resolved, *command[1:]]
    return command


def build_agentbus_command(
    workflow: dict[str, Any],
    step: dict[str, Any],
    run_id: str,
    index: int,
    task: str,
) -> list[str]:
    policy = workflow.get("policy", {}) if isinstance(workflow.get("policy"), dict) else {}
    privacy = str(policy.get("privacy", "local_only"))
    budget = str(policy.get("budget_cents", 0))
    provider = str(policy.get("dispatch_provider", "offline"))
    return [
        sys.executable,
        "scripts/scbe-system-cli.py",
        "--repo-root",
        str(REPO_ROOT),
        "agentbus",
        "run",
        "--task",
        task,
        "--operation-command",
        "korah aelin dahru",
        "--task-type",
        str(step.get("task_type", "general")),
        "--series-id",
        run_id,
        "--round-index",
        str(index),
        "--privacy",
        privacy,
        "--budget-cents",
        budget,
        "--max-players",
        "1",
        "--dispatch",
        "--dispatch-provider",
        provider,
        "--json",
    ]


def extract_bullets(step: dict[str, Any], result: dict[str, Any], parsed_stdout: Any | None) -> list[str]:
    bullets = [str(item) for item in step.get("success_bullets", []) if str(item).strip()]
    if isinstance(parsed_stdout, dict):
        selected = parsed_stdout.get("selected_provider")
        if selected:
            bullets.append(f"Step {step['id']} selected provider {selected}.")
        artifacts = parsed_stdout.get("artifacts")
        if isinstance(artifacts, dict):
            summary = artifacts.get("summary")
            if summary:
                bullets.append(f"Step {step['id']} wrote summary artifact {summary}.")
    stdout = str(result.get("stdout", ""))
    if "overall_status" in stdout and "ready" in stdout:
        bullets.append(f"Step {step['id']} reported ready status.")
    return bullets


def run_switchboard(args: argparse.Namespace) -> dict[str, Any]:
    workflow_path = Path(args.workflow).resolve()
    workflow = load_json(workflow_path)
    steps = step_map(workflow)
    run_id = args.run_id or f"agentbus-switchboard-{utc_slug()}"
    run_dir = Path(args.output_root) / run_id
    start_id = args.start or str(workflow.get("start", ""))
    if start_id not in steps:
        raise ValueError(f"start step not found: {start_id}")

    current = start_id
    failed_step = ""
    bullets: list[str] = []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for index in range(1, args.max_steps + 1):
        if not current:
            break
        if current in seen:
            rows.append({"step_id": current, "status": "blocked", "reason": "loop_detected"})
            break
        seen.add(current)
        step = steps[current]
        kind = str(step.get("kind", "agentbus"))
        task = render_task(step, bullets, failed_step=failed_step)
        if kind == "command":
            command = [str(part) for part in step.get("command", [])]
        elif kind == "agentbus":
            command = build_agentbus_command(workflow, step, run_id, index, task)
        else:
            raise ValueError(f"unsupported switchboard step kind: {kind}")

        result = run_command(command, timeout=int(args.timeout_seconds), dry_run=args.dry_run)
        parsed = parse_json_maybe(result.get("stdout", ""))
        ok = result["exit_code"] == 0 and not result["timed_out"]
        step_dir = run_dir / "steps" / f"{index:02d}_{current}"
        write_json(
            step_dir / "receipt.json",
            {
                "step_id": current,
                "title": step.get("title", ""),
                "kind": kind,
                "ok": ok,
                "command": command,
                "exit_code": result["exit_code"],
                "timed_out": result["timed_out"],
                "dry_run": args.dry_run,
                "parsed_stdout": parsed,
            },
        )
        write_text(step_dir / "stdout.txt", str(result.get("stdout", "")))
        write_text(step_dir / "stderr.txt", str(result.get("stderr", "")))
        new_bullets = extract_bullets(step, result, parsed) if ok else []
        bullets.extend(new_bullets)
        row = {
            "index": index,
            "step_id": current,
            "title": step.get("title", ""),
            "kind": kind,
            "status": "pass" if ok else "fail",
            "exit_code": result["exit_code"],
            "receipt": str((step_dir / "receipt.json").resolve()),
            "bullets_added": new_bullets,
        }
        rows.append(row)
        if ok:
            current = str(step.get("next_on_success", "")).strip()
            failed_step = ""
        else:
            failed_step = current
            current = str(step.get("next_on_failure", "")).strip()

    if rows and any(row["status"] == "fail" for row in rows):
        overall = "needs_attention"
    elif rows and not current:
        overall = "pass"
    elif rows and rows[-1]["status"] == "pass":
        overall = "partial_pass"
    else:
        overall = "needs_attention"
    if args.dry_run:
        overall = "dry_run"
    report = {
        "schema_version": "scbe_agent_bus_switchboard_run_v1",
        "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "workflow_path": str(workflow_path),
        "workflow_id": workflow.get("workflow_id", ""),
        "policy": workflow.get("policy", {}),
        "dry_run": args.dry_run,
        "overall_status": overall,
        "steps_executed": len(rows),
        "final_bullets": bullets,
        "rows": rows,
        "report_json": str((run_dir / "report.json").resolve()),
        "report_md": str((run_dir / "report.md").resolve()),
    }
    write_json(run_dir / "report.json", report)
    write_markdown(run_dir / "report.md", report)
    print(json.dumps({"overall_status": overall, "run_id": run_id, "report": report["report_json"]}, indent=2))
    return report


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# AgentBus Switchboard Run",
        "",
        f"- Run ID: `{report['run_id']}`",
        f"- Workflow: `{report['workflow_id']}`",
        f"- Overall: `{report['overall_status']}`",
        f"- Dry run: `{report['dry_run']}`",
        f"- Steps executed: `{report['steps_executed']}`",
        "",
        "## Steps",
        "",
        "| # | Step | Kind | Status | Receipt |",
        "|---:|---|---|---|---|",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row['index']} | `{row['step_id']}` | `{row['kind']}` | `{row['status']}` | `{row['receipt']}` |"
        )
    lines.extend(["", "## Final Bullets", ""])
    for bullet in report["final_bullets"]:
        lines.append(f"- {bullet}")
    write_text(path, "\n".join(lines) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a local/free AgentBus switchboard domino workflow.")
    parser.add_argument("--workflow", default=str(DEFAULT_WORKFLOW))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--start", default="")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run_switchboard(args)
    return 0 if report["overall_status"] in {"pass", "partial_pass", "dry_run"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
