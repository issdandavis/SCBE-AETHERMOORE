#!/usr/bin/env python3
"""Competitive wedge benchmark for the SCBE agent-bus release surface.

This benchmark compares two ways of handling the same repo-local task prompts:

1. Baseline direct execution: a plain deterministic shell-style response.
2. SCBE bus execution: the user-facing `scbe-system-cli.py agentbus run` endpoint.

The benchmark does not claim model intelligence or code-generation superiority.
It measures the release wedge that is actually implemented today: routing,
state capture, artifact quality, recovery visibility, determinism, local privacy,
and zero-cost operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "artifacts" / "benchmarks" / "agentbus_competitive_wedge"
CLI = REPO_ROOT / "scripts" / "scbe-system-cli.py"


@dataclass(frozen=True)
class BenchmarkTask:
    task_id: str
    task_type: str
    prompt: str
    operation_command: str = "korah aelin dahru"


@dataclass(frozen=True)
class LaneResult:
    lane: str
    task_id: str
    ok: bool
    duration_ms: int
    stdout_chars: int
    stderr_chars: int
    payload: dict[str, Any]
    error: str = ""


TASKS = [
    BenchmarkTask(
        task_id="coding_patch_plan",
        task_type="coding",
        prompt="Plan a scoped patch for the agent bus without touching unrelated files.",
    ),
    BenchmarkTask(
        task_id="review_gate",
        task_type="review",
        prompt="Review a release candidate and identify whether backend API is in scope.",
    ),
    BenchmarkTask(
        task_id="training_bucket",
        task_type="training",
        prompt="Route a training dataset consolidation task into the right bucket.",
    ),
    BenchmarkTask(
        task_id="governance_boundary",
        task_type="governance",
        prompt="Check that security/auth claims stay separate from AI operation routing.",
    ),
    BenchmarkTask(
        task_id="general_recovery",
        task_type="general",
        prompt="Create a recovery trail for a user-facing workflow failure.",
    ),
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _run_subprocess(
    command: list[str], *, cwd: Path, timeout: int = 60
) -> tuple[int, str, str, int]:
    start = time.perf_counter()
    proc = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    duration_ms = int((time.perf_counter() - start) * 1000)
    return proc.returncode, proc.stdout, proc.stderr, duration_ms


def run_baseline(task: BenchmarkTask) -> LaneResult:
    """Run a plain direct baseline.

    This intentionally models the competitor as a simple direct wrapper: it can
    accept the task and emit a deterministic acknowledgement, but it has no bus
    routing, watcher, file snapshot, helpdesk/recovery, or T-tree operation
    shape unless custom code is added around it.
    """
    prompt_hash = _sha256_text(task.prompt)
    start = time.perf_counter()
    payload = {
        "schema_version": "direct_baseline_result_v1",
        "task_id": task.task_id,
        "task_type": task.task_type,
        "accepted": True,
        "provider": "direct-shell",
        "privacy": "local",
        "estimated_cost_cents": 0.0,
        "prompt_sha256": prompt_hash,
        "artifacts": {},
        "capabilities": {
            "task_accepted": True,
            "provider_selected": False,
            "operation_shape": False,
            "dispatch_event": False,
            "mirror_round": False,
            "file_snapshot": False,
            "observable_state": False,
            "recovery_artifact": False,
            "deterministic_signature": False,
            "local_private": True,
            "zero_cost": True,
        },
    }
    stdout = json.dumps(payload, sort_keys=True)
    duration_ms = int((time.perf_counter() - start) * 1000)
    return LaneResult(
        lane="direct_baseline",
        task_id=task.task_id,
        ok=True,
        duration_ms=duration_ms,
        stdout_chars=len(stdout),
        stderr_chars=0,
        payload=payload,
    )


def run_bus(task: BenchmarkTask, *, run_id: str) -> LaneResult:
    series_id = f"bench-{run_id}-{task.task_id}"
    command = [
        sys.executable,
        str(CLI),
        "--repo-root",
        str(REPO_ROOT),
        "agentbus",
        "run",
        "--task",
        task.prompt,
        "--operation-command",
        task.operation_command,
        "--task-type",
        task.task_type,
        "--series-id",
        series_id,
        "--privacy",
        "local_only",
        "--budget-cents",
        "0",
        "--dispatch",
        "--json",
    ]
    code, stdout, stderr, duration_ms = _run_subprocess(command, cwd=REPO_ROOT)
    payload: dict[str, Any] = {}
    error = ""
    if stdout.strip():
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            error = f"json_decode_error: {exc}"
    if code != 0 and not error:
        error = stderr[-1000:]
    return LaneResult(
        lane="scbe_agent_bus",
        task_id=task.task_id,
        ok=code == 0 and bool(payload),
        duration_ms=duration_ms,
        stdout_chars=len(stdout),
        stderr_chars=len(stderr),
        payload=payload,
        error=error,
    )


def _path_exists(relative: str | None) -> bool:
    if not relative:
        return False
    return (REPO_ROOT / relative).exists()


def score_baseline(result: LaneResult) -> dict[str, Any]:
    caps = result.payload.get("capabilities", {})
    checks = {
        "task_completed": result.ok and caps.get("task_accepted") is True,
        "provider_selected": caps.get("provider_selected") is True,
        "operation_shape": caps.get("operation_shape") is True,
        "dispatch_event": caps.get("dispatch_event") is True,
        "mirror_round_artifact": caps.get("mirror_round") is True,
        "file_snapshot_artifact": caps.get("file_snapshot") is True,
        "observable_state_artifact": caps.get("observable_state") is True,
        "recovery_artifact": caps.get("recovery_artifact") is True,
        "deterministic_signature": caps.get("deterministic_signature") is True,
        "local_private": caps.get("local_private") is True,
        "zero_cost": caps.get("zero_cost") is True,
    }
    return _score_checks(result, checks)


def score_bus(result: LaneResult) -> dict[str, Any]:
    payload = result.payload
    artifacts = (
        payload.get("artifacts", {})
        if isinstance(payload.get("artifacts"), dict)
        else {}
    )
    dispatch = (
        payload.get("dispatch", {}) if isinstance(payload.get("dispatch"), dict) else {}
    )
    operation = (
        payload.get("operation_shape", {})
        if isinstance(payload.get("operation_shape"), dict)
        else {}
    )
    checks = {
        "task_completed": result.ok
        and payload.get("schema_version") == "scbe_agentbus_user_run_v1",
        "provider_selected": bool(payload.get("selected_provider")),
        "operation_shape": operation.get("root_value") == 12026
        and bool(operation.get("signature_hex")),
        "dispatch_event": dispatch.get("enabled") is True
        and bool(dispatch.get("event_id")),
        "mirror_round_artifact": _path_exists(artifacts.get("latest_round")),
        "file_snapshot_artifact": _path_exists(artifacts.get("tracker_snapshot")),
        "observable_state_artifact": _path_exists(artifacts.get("watcher")),
        "recovery_artifact": _path_exists(artifacts.get("summary")),
        "deterministic_signature": operation.get("floating_point_policy")
        == "forbidden for consensus signatures",
        "local_private": payload.get("privacy") == "local_only"
        and dispatch.get("route", {}).get("privacy") == "local",
        "zero_cost": float(payload.get("budget_cents", 1.0)) == 0.0,
    }
    return _score_checks(result, checks)


def _score_checks(result: LaneResult, checks: dict[str, bool]) -> dict[str, Any]:
    passed = sum(1 for value in checks.values() if value)
    total = len(checks)
    return {
        "lane": result.lane,
        "task_id": result.task_id,
        "score": round(passed / total, 4),
        "passed": passed,
        "total": total,
        "duration_ms": result.duration_ms,
        "checks": checks,
        "error": result.error,
    }


def build_report(
    *, out_dir: Path = DEFAULT_OUT, run_id: str | None = None
) -> dict[str, Any]:
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_dir / run_id
    baseline_results = [run_baseline(task) for task in TASKS]
    bus_results = [run_bus(task, run_id=run_id) for task in TASKS]
    baseline_scores = [score_baseline(result) for result in baseline_results]
    bus_scores = [score_bus(result) for result in bus_results]

    baseline_avg = round(
        sum(item["score"] for item in baseline_scores) / len(baseline_scores), 4
    )
    bus_avg = round(sum(item["score"] for item in bus_scores) / len(bus_scores), 4)
    lift = round(bus_avg - baseline_avg, 4)
    bus_wins = sum(
        1 for b, s in zip(baseline_scores, bus_scores) if s["score"] > b["score"]
    )

    report = {
        "schema_version": "scbe_agentbus_competitive_wedge_v1",
        "generated_at_utc": _utc_now(),
        "run_id": run_id,
        "scope": "CLI/agent-bus operational workflow; not model intelligence or full-stack production",
        "competition_model": "plain direct shell-style task acknowledgement with local zero-cost execution",
        "tasks": [asdict(task) for task in TASKS],
        "summary": {
            "baseline_avg": baseline_avg,
            "scbe_bus_avg": bus_avg,
            "absolute_lift": lift,
            "relative_lift_pct": (
                round((lift / baseline_avg) * 100, 2) if baseline_avg else None
            ),
            "bus_wins": bus_wins,
            "task_count": len(TASKS),
            "decision": "PASS" if bus_wins == len(TASKS) and bus_avg >= 0.9 else "HOLD",
        },
        "criteria": {
            "task_completed": "Both lanes must accept/complete the task prompt.",
            "provider_selected": "Bus must select a player/provider instead of acting as a raw wrapper.",
            "operation_shape": "Bus must attach deterministic T-tree operation shape.",
            "dispatch_event": "Bus must create a durable dispatch event.",
            "mirror_round_artifact": "Bus must preserve mirror-room routing state.",
            "file_snapshot_artifact": "Bus must preserve file tracking state.",
            "observable_state_artifact": "Bus must preserve watcher state.",
            "recovery_artifact": "Bus must preserve run summary for recovery.",
            "deterministic_signature": "Bus must avoid floating-point consensus signatures.",
            "local_private": "Lane must remain local-only for this benchmark.",
            "zero_cost": "Lane must operate within a zero-cent budget.",
        },
        "baseline_scores": baseline_scores,
        "scbe_bus_scores": bus_scores,
        "raw_results": {
            "baseline": [asdict(result) for result in baseline_results],
            "scbe_bus": [asdict(result) for result in bus_results],
        },
        "claim_boundary": [
            "This benchmark supports releasing the agent-bus as a governed local workflow surface.",
            "It does not prove that SCBE generates better code than frontier coding agents.",
            "The next benchmark must use real patch tasks and compare passed tests, edit quality, and time-to-fix.",
        ],
    }
    _write_json(run_dir / "report.json", report)
    _write_json(out_dir / "latest_report.json", report)
    (run_dir / "REPORT.md").write_text(_render_markdown(report), encoding="utf-8")
    (out_dir / "LATEST.md").write_text(_render_markdown(report), encoding="utf-8")
    return report


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# SCBE Agent-Bus Competitive Wedge Benchmark",
        "",
        f"- Generated: `{report['generated_at_utc']}`",
        f"- Run ID: `{report['run_id']}`",
        f"- Scope: {report['scope']}",
        f"- Decision: `{summary['decision']}`",
        "",
        "## Summary",
        "",
        "| Lane | Average score |",
        "|---|---:|",
        f"| Direct baseline | `{summary['baseline_avg']}` |",
        f"| SCBE agent bus | `{summary['scbe_bus_avg']}` |",
        "",
        f"- Absolute lift: `{summary['absolute_lift']}`",
        f"- Relative lift: `{summary['relative_lift_pct']}%`",
        f"- Bus wins: `{summary['bus_wins']} / {summary['task_count']}`",
        "",
        "## Per-Task Scores",
        "",
        "| Task | Baseline | SCBE bus |",
        "|---|---:|---:|",
    ]
    baseline_by_id = {item["task_id"]: item for item in report["baseline_scores"]}
    for item in report["scbe_bus_scores"]:
        task_id = item["task_id"]
        lines.append(
            f"| `{task_id}` | `{baseline_by_id[task_id]['score']}` | `{item['score']}` |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            *[f"- {item}" for item in report["claim_boundary"]],
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(out_dir=args.out_dir, run_id=args.run_id or None)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        summary = report["summary"]
        print(
            "agentbus competitive wedge: "
            f"decision={summary['decision']} "
            f"baseline={summary['baseline_avg']} "
            f"bus={summary['scbe_bus_avg']} "
            f"lift={summary['absolute_lift']}"
        )
        print(f"report={args.out_dir / report['run_id'] / 'report.json'}")
    return 0 if report["summary"]["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
