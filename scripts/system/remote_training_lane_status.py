#!/usr/bin/env python3
"""Collect lightweight status for active remote training lanes."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = (
    REPO_ROOT / "artifacts" / "training_hub" / "remote_training_lane_status.json"
)
HF_PROFILE_ID = "coding-agent-qwen-geoshell-pair-agent-v1"
HF_FALLBACK_JOB_ID = "69f83c4998a8d679adfb8ddd"
KAGGLE_ROUND = "coding-approval-metrics-v2"
KAGGLE_KERNEL = "issacizrealdavis/polly-auto-coding-approval-metrics-v1"


def _run(command: list[str], timeout: int = 120) -> dict[str, Any]:
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
        )
    except FileNotFoundError as exc:
        return {
            "command": command,
            "returncode": 127,
            "stdout": "",
            "stderr": f"missing executable: {exc.filename}",
        }
    return {
        "command": command,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _compact_run(result: dict[str, Any], *, stdout_limit: int = 4000) -> dict[str, Any]:
    stdout = str(result.get("stdout", ""))
    stderr = str(result.get("stderr", ""))
    return {
        "command": result.get("command", []),
        "returncode": result.get("returncode"),
        "stdout": stdout[:stdout_limit],
        "stdout_truncated": len(stdout) > stdout_limit,
        "stderr": stderr[:stdout_limit],
        "stderr_truncated": len(stderr) > stdout_limit,
    }


def _summarize_hf_inspect(result: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "returncode": result.get("returncode"),
        "stage": None,
        "message": None,
        "url": None,
        "created_at": None,
        "flavor": None,
    }
    try:
        payload = json.loads(str(result.get("stdout") or "[]"))
        job = payload[0] if isinstance(payload, list) and payload else {}
    except json.JSONDecodeError:
        job = {}
    if isinstance(job, dict):
        status = job.get("status") if isinstance(job.get("status"), dict) else {}
        summary.update(
            {
                "stage": status.get("stage"),
                "message": status.get("message"),
                "url": job.get("url"),
                "created_at": job.get("created_at"),
                "flavor": job.get("flavor"),
            }
        )
    return summary


def _latest_hf_job_id() -> str:
    packet_root = REPO_ROOT / "artifacts" / "hf_coding_agent_jobs" / HF_PROFILE_ID
    packets = sorted(packet_root.glob("*/job_packet.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for packet in packets:
        try:
            payload = json.loads(packet.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        job_id = str((payload.get("dispatch") or {}).get("job_id") or "").strip()
        if payload.get("dispatched") and job_id:
            return job_id
    return HF_FALLBACK_JOB_ID


def collect_status() -> dict[str, Any]:
    hf_job_id = _latest_hf_job_id()
    hf_status = _run(
        [
            sys.executable,
            "scripts/system/dispatch_coding_agent_hf_job.py",
            "status",
            "--json",
        ]
    )
    hf_inspect = _run(["hf", "jobs", "inspect", hf_job_id])
    kaggle_status = _run([sys.executable, "scripts/kaggle_auto/launch.py", "--status"])
    kaggle_kernel_status = _run(["kaggle", "kernels", "status", KAGGLE_KERNEL])
    scorecard = (
        REPO_ROOT
        / "artifacts"
        / "training_evals"
        / "agentic_system_scorecard_2026-05-02.json"
    )
    scorecard_payload = (
        json.loads(scorecard.read_text(encoding="utf-8")) if scorecard.exists() else {}
    )
    return {
        "schema_version": "scbe_remote_training_lane_status_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hf": {
            "job_id": hf_job_id,
            "status_command": "python scripts/system/dispatch_coding_agent_hf_job.py status --json",
            "inspect_command": f"hf jobs inspect {hf_job_id}",
            "inspect": _summarize_hf_inspect(hf_inspect),
            "raw": _compact_run(hf_status),
            "inspect_raw": _compact_run(hf_inspect, stdout_limit=0),
        },
        "kaggle": {
            "round": KAGGLE_ROUND,
            "kernel": KAGGLE_KERNEL,
            "status_command": "python scripts/kaggle_auto/launch.py --status",
            "kernel_status_command": f"kaggle kernels status {KAGGLE_KERNEL}",
            "pull_command": f"python scripts/kaggle_auto/launch.py --pull --round {KAGGLE_ROUND}",
            "raw": kaggle_status,
            "kernel_raw": kaggle_kernel_status,
        },
        "scorecard": {
            "overall_score": scorecard_payload.get("overall_score"),
            "model_promotion_score": scorecard_payload.get("model_promotion_score"),
            "rank": scorecard_payload.get("rank"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = collect_status()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            report if args.json else {"ok": True, "out": str(args.out)},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
