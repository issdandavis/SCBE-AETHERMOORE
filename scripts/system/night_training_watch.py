#!/usr/bin/env python3
"""Night-safe watcher for SCBE remote training and bijective coding gates.

This script is intentionally conservative: it observes remote jobs, pulls Kaggle
artifacts only when the kernel is no longer running, refreshes local scorecards,
and runs focused bijective coding tests. It does not modify source code.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "night_watch"
DEFAULT_HF_JOB_ID = "69f83c4998a8d679adfb8ddd"
DEFAULT_KAGGLE_ROUND = "coding-approval-metrics-v2"
DEFAULT_KAGGLE_KERNEL = "issacizrealdavis/polly-auto-coding-approval-metrics-v1"

FOCUSED_BIJECTIVE_TESTS = [
    "tests/coding_spine/test_bijective_reasoning_code_packet.py",
    "tests/benchmarks/test_bijective_tongue_gate.py",
    "tests/benchmarks/test_scbe_bijective_round_trip_score.py",
    "tests/crypto/test_sacred_tongues.py",
]

CommandRunner = Callable[[list[str], int], dict[str, Any]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_command(command: list[str], timeout: int) -> dict[str, Any]:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    started = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        return {
            "command": command,
            "returncode": proc.returncode,
            "duration_sec": round(time.monotonic() - started, 3),
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": 124,
            "duration_sec": round(time.monotonic() - started, 3),
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or f"Timed out after {timeout}s",
            "timed_out": True,
        }


def _parse_jsonish(stdout: str) -> Any:
    text = stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def _classify_status(result: dict[str, Any]) -> str:
    body = f"{result.get('stdout', '')}\n{result.get('stderr', '')}".lower()
    if result.get("timed_out"):
        return "timeout"
    if result.get("returncode") not in (0, None):
        return "error"
    if any(token in body for token in ("running", "queued", "pending", "scheduling", "scheduled")):
        return "running"
    if any(token in body for token in ("complete", "completed", "success", "succeeded", "finished", " passed")):
        return "complete"
    if any(token in body for token in ("failed", "error", "cancelled", "canceled")):
        return "error"
    return "unknown"


def _compact_result(result: dict[str, Any], *, max_chars: int = 1800) -> dict[str, Any]:
    compact = dict(result)
    for key in ("stdout", "stderr"):
        value = str(compact.get(key) or "")
        compact[key] = value[-max_chars:] if len(value) > max_chars else value
    return compact


def collect_once(
    *,
    hf_job_id: str = DEFAULT_HF_JOB_ID,
    kaggle_round: str = DEFAULT_KAGGLE_ROUND,
    kaggle_kernel: str = DEFAULT_KAGGLE_KERNEL,
    run_tests: bool = True,
    pull_completed_kaggle: bool = True,
    runner: CommandRunner = _run_command,
    test_timeout: int = 240,
) -> dict[str, Any]:
    hf = runner(
        [sys.executable, "scripts/system/dispatch_coding_agent_hf_job.py", "status", "--json"],
        180,
    )
    hf_inspect = runner(["hf", "jobs", "inspect", hf_job_id], 120)
    kaggle_direct = runner(["kaggle", "kernels", "status", kaggle_kernel], 120)
    kaggle_round_status = runner([sys.executable, "scripts/kaggle_auto/launch.py", "--status"], 120)

    hf_status = _classify_status(hf_inspect)
    if hf_status == "unknown":
        hf_status = _classify_status(hf)
    kaggle_status = _classify_status(kaggle_direct)
    actions: list[dict[str, Any]] = []

    if pull_completed_kaggle and kaggle_status == "complete":
        actions.append(
            {
                "name": "kaggle_pull",
                "result": runner(
                    [
                        sys.executable,
                        "scripts/kaggle_auto/launch.py",
                        "--pull",
                        "--round",
                        kaggle_round,
                    ],
                    300,
                ),
            }
        )

    scorecard = runner(
        [
            sys.executable,
            "scripts/eval/score_agentic_training_system.py",
            "--hf-job-id",
            hf_job_id,
            "--write",
            "--json",
        ],
        240,
    )

    tests: dict[str, Any] | None = None
    if run_tests:
        tests = runner([sys.executable, "-m", "pytest", *FOCUSED_BIJECTIVE_TESTS, "-q"], test_timeout)

    score_payload = _parse_jsonish(str(scorecard.get("stdout") or ""))
    report = {
        "schema_version": "scbe_night_training_watch_v1",
        "generated_utc": _utc_now(),
        "hf": {
            "job_id": hf_job_id,
            "status": hf_status,
            "ps_result": _compact_result(hf),
            "inspect_result": _compact_result(hf_inspect),
        },
        "kaggle": {
            "round": kaggle_round,
            "kernel": kaggle_kernel,
            "status": kaggle_status,
            "direct_result": _compact_result(kaggle_direct),
            "round_result": _compact_result(kaggle_round_status),
        },
        "scorecard": {
            "status": _classify_status(scorecard),
            "overall_score": score_payload.get("overall_score") if isinstance(score_payload, dict) else None,
            "model_promotion_score": score_payload.get("model_promotion_score")
            if isinstance(score_payload, dict)
            else None,
            "rank": score_payload.get("rank") if isinstance(score_payload, dict) else None,
            "result": _compact_result(scorecard),
        },
        "bijective_coding": {
            "focused_tests": FOCUSED_BIJECTIVE_TESTS,
            "status": _classify_status(tests) if tests else "skipped",
            "result": _compact_result(tests) if tests else None,
        },
        "actions": [
            {"name": action["name"], "result": _compact_result(action["result"])}
            for action in actions
        ],
        "night_safety": {
            "source_edits": False,
            "destructive_actions": False,
            "pull_completed_kaggle": pull_completed_kaggle,
        },
    }
    report["attention_required"] = [
        name
        for name, status in (
            ("hf", report["hf"]["status"]),
            ("kaggle", report["kaggle"]["status"]),
            ("scorecard", report["scorecard"]["status"]),
            ("bijective_coding", report["bijective_coding"]["status"]),
        )
        if status in ("error", "timeout")
    ]
    # The watcher is successful when it writes an honest report. Remote lane
    # failures are surfaced in attention_required instead of making the
    # scheduled task look broken every cycle.
    report["ok"] = True
    return report


def write_report(report: dict[str, Any], out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    latest = out_dir / "latest.json"
    journal = out_dir / "night_training_watch.jsonl"
    paths = {"latest": str(latest), "journal": str(journal)}
    payload = {**report, "paths": paths}
    latest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with journal.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hf-job-id", default=DEFAULT_HF_JOB_ID)
    parser.add_argument("--kaggle-round", default=DEFAULT_KAGGLE_ROUND)
    parser.add_argument("--kaggle-kernel", default=DEFAULT_KAGGLE_KERNEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-kaggle-pull", action="store_true")
    parser.add_argument("--test-timeout", type=int, default=240)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = collect_once(
        hf_job_id=args.hf_job_id,
        kaggle_round=args.kaggle_round,
        kaggle_kernel=args.kaggle_kernel,
        run_tests=not args.skip_tests,
        pull_completed_kaggle=not args.skip_kaggle_pull,
        test_timeout=args.test_timeout,
    )
    paths = write_report(report, args.out_dir)
    report["paths"] = paths
    print(
        json.dumps(
            report
            if args.json
            else {
                "ok": report["ok"],
                "hf": report["hf"]["status"],
                "kaggle": report["kaggle"]["status"],
                "scorecard": report["scorecard"]["status"],
                "bijective_coding": report["bijective_coding"]["status"],
                "paths": paths,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
