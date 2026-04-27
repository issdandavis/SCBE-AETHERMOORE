#!/usr/bin/env python3
"""Write a unified watch report for active SCBE remote training runs.

Read-only. Checks:
- Hugging Face Jobs table and optional latest logs for a focus job.
- Kaggle polly-auto kernel statuses.

Outputs:
- artifacts/training_watch/latest.json
- artifacts/training_watch/latest.md
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "artifacts" / "training_watch"
KAGGLE_USER = "issacizrealdavis"
DEFAULT_KAGGLE_REFS = [
    "issacizrealdavis/polly-auto-coding-approval-metrics-v1",
    "issacizrealdavis/polly-auto-bijective-tongue-coder-v2",
    "issacizrealdavis/polly-auto-dsl-syn-v3-fast",
]


@dataclass
class CommandResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int


def run_cmd(args: list[str], timeout: int = 40) -> CommandResult:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except Exception as exc:
        return CommandResult(False, "", str(exc), 1)
    return CommandResult(result.returncode == 0, result.stdout, result.stderr, result.returncode)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_hf_jobs_table(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("JOB ID") or line.startswith("-"):
            continue
        match = re.match(r"^(\S+)\s+(\S+)\s+(.+?)\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(\S+)\s*$", line)
        if not match:
            continue
        job_id, image_or_space, command, created, status = match.groups()
        rows.append(
            {
                "job_id": job_id,
                "image_or_space": image_or_space,
                "command": command,
                "created": created,
                "status": status,
            }
        )
    return rows


def hf_jobs(limit: int) -> tuple[list[dict[str, str]], CommandResult]:
    result = run_cmd(["hf", "jobs", "ps", "-a"], timeout=50)
    rows = parse_hf_jobs_table(result.stdout + "\n" + result.stderr)[:limit] if result.ok else []
    return rows, result


def hf_job_logs(job_id: str, tail: int) -> tuple[list[str], CommandResult]:
    result = run_cmd(["hf", "jobs", "logs", job_id], timeout=70)
    text = result.stdout + "\n" + result.stderr
    return text.splitlines()[-tail:], result


def kaggle_status(ref: str) -> dict[str, str]:
    result = run_cmd(["kaggle", "kernels", "status", ref], timeout=35)
    text = (result.stdout + "\n" + result.stderr).strip()
    lowered = text.lower()
    status = "unknown"
    for candidate in ("running", "complete", "error", "failed", "queued", "cancel"):
        if candidate in lowered:
            status = candidate
            break
    return {
        "ref": ref,
        "status": status,
        "ok": str(result.ok).lower(),
        "raw": text,
    }


def latest_metric_lines(lines: list[str]) -> list[str]:
    keep: list[str] = []
    metric_markers = ("loss", "eval_loss", "mean_token_accuracy", "FINAL_EVAL", "[status]", "ERROR", "WARN")
    for line in lines:
        if any(marker in line for marker in metric_markers):
            keep.append(line)
    return keep[-20:]


def write_reports(payload: dict) -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "latest.json"
    md_path = OUT_DIR / "latest.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Training Watch Report",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        "## Hugging Face Jobs",
        "",
        "| Job | Created | Status |",
        "|---|---:|---|",
    ]
    for job in payload["hf_jobs"]:
        lines.append(f"| `{job['job_id']}` | `{job['created']}` | `{job['status']}` |")
    if not payload["hf_jobs"]:
        lines.append("| none | - | - |")

    lines.extend(["", "## Kaggle Kernels", "", "| Kernel | Status |", "|---|---|"])
    for kernel in payload["kaggle"]:
        lines.append(f"| `{kernel['ref']}` | `{kernel['status']}` |")

    if payload.get("focus_job_id"):
        lines.extend(["", f"## HF Focus Job `{payload['focus_job_id']}`", ""])
        metric_lines = payload.get("focus_metric_lines") or []
        if metric_lines:
            lines.append("```text")
            lines.extend(metric_lines)
            lines.append("```")
        else:
            lines.append("No metric lines found in the latest log tail.")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--focus-hf-job", default="", help="HF job ID to tail for metric lines")
    parser.add_argument("--hf-limit", type=int, default=8)
    parser.add_argument("--log-tail", type=int, default=120)
    parser.add_argument("--kaggle-ref", action="append", default=[], help="Extra Kaggle kernel ref to check")
    args = parser.parse_args()

    jobs, hf_result = hf_jobs(args.hf_limit)
    kaggle_refs = list(dict.fromkeys([*DEFAULT_KAGGLE_REFS, *args.kaggle_ref]))
    kaggle = [kaggle_status(ref) for ref in kaggle_refs]

    focus_lines: list[str] = []
    focus_raw_ok = None
    if args.focus_hf_job:
        lines, log_result = hf_job_logs(args.focus_hf_job, args.log_tail)
        focus_lines = latest_metric_lines(lines)
        focus_raw_ok = log_result.ok

    payload = {
        "generated_at": utc_now(),
        "hf_jobs": jobs,
        "hf_command": asdict(hf_result),
        "kaggle": kaggle,
        "focus_job_id": args.focus_hf_job,
        "focus_log_ok": focus_raw_ok,
        "focus_metric_lines": focus_lines,
    }
    json_path, md_path = write_reports(payload)
    print(f"Wrote {json_path.relative_to(REPO_ROOT)}")
    print(f"Wrote {md_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
