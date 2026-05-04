"""Run a local parallelism workflow from a JSON spec.

This script gives you a reusable "my own parallelism system" lane:
- Run multiple Parallel web searches concurrently.
- Run local shell jobs concurrently.
- Save per-job outputs plus a single run report.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "parallelism_system"


@dataclass
class JobResult:
    job_id: str
    job_type: str
    ok: bool
    returncode: int
    started_at_utc: str
    finished_at_utc: str
    elapsed_ms: int
    output_file: str | None
    stdout_tail: str
    stderr_tail: str
    command: list[str] | str


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tail(text: str, max_len: int = 4000) -> str:
    return text[-max_len:] if text else ""


def _run_parallel_search(job: dict[str, Any], run_dir: Path) -> JobResult:
    job_id = str(job["id"])
    objective = str(job["objective"])
    queries = [str(q) for q in job.get("queries", [])]
    max_results = int(job.get("max_results", 10))
    excerpt_budget = int(job.get("excerpt_max_chars_total", 27000))
    output_file = run_dir / f"{job_id}.json"

    cmd: list[str] = [
        "parallel-cli",
        "search",
        objective,
        "--json",
        "--max-results",
        str(max_results),
        "--excerpt-max-chars-total",
        str(excerpt_budget),
        "-o",
        str(output_file),
    ]
    for q in queries:
        cmd.extend(["-q", q])

    started = datetime.now(timezone.utc)
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
    finished = datetime.now(timezone.utc)
    elapsed = int((finished - started).total_seconds() * 1000)
    return JobResult(
        job_id=job_id,
        job_type="parallel_search",
        ok=proc.returncode == 0,
        returncode=proc.returncode,
        started_at_utc=started.isoformat(),
        finished_at_utc=finished.isoformat(),
        elapsed_ms=elapsed,
        output_file=str(output_file) if output_file.exists() else None,
        stdout_tail=_tail(proc.stdout),
        stderr_tail=_tail(proc.stderr),
        command=cmd,
    )


def _run_shell_job(job: dict[str, Any], run_dir: Path) -> JobResult:
    job_id = str(job["id"])
    command = str(job["command"])
    log_file = run_dir / f"{job_id}.log"

    started = datetime.now(timezone.utc)
    proc = subprocess.run(  # nosec B602: developer-only runner; command comes from local JSON spec; shell=True needed for pipe/redirect
        command, cwd=str(REPO_ROOT), shell=True, capture_output=True, text=True, check=False
    )
    finished = datetime.now(timezone.utc)
    elapsed = int((finished - started).total_seconds() * 1000)

    log_body = (
        f"$ {command}\n\n"
        f"[stdout]\n{proc.stdout}\n"
        f"[stderr]\n{proc.stderr}\n"
        f"[exit_code]\n{proc.returncode}\n"
    )
    log_file.write_text(log_body, encoding="utf-8")

    return JobResult(
        job_id=job_id,
        job_type="shell",
        ok=proc.returncode == 0,
        returncode=proc.returncode,
        started_at_utc=started.isoformat(),
        finished_at_utc=finished.isoformat(),
        elapsed_ms=elapsed,
        output_file=str(log_file),
        stdout_tail=_tail(proc.stdout),
        stderr_tail=_tail(proc.stderr),
        command=command,
    )


def _run_job(job: dict[str, Any], run_dir: Path) -> JobResult:
    job_type = str(job.get("type", "")).strip().lower()
    if job_type == "parallel_search":
        return _run_parallel_search(job, run_dir)
    if job_type == "shell":
        return _run_shell_job(job, run_dir)
    raise ValueError(f"Unsupported job type for '{job.get('id', 'unknown')}': {job_type}")


def _write_template(path: Path) -> None:
    template = {
        "name": "my-parallel-lane",
        "description": "Example parallelism workflow mixing web research and local jobs.",
        "jobs": [
            {
                "id": "hf-training-research",
                "type": "parallel_search",
                "objective": "Hugging Face LLM training best practices with TRL and PEFT",
                "queries": ["SFTTrainer", "DPOTrainer", "QLoRA"],
                "max_results": 8,
            },
            {
                "id": "bijective-coding-research",
                "type": "parallel_search",
                "objective": "Bijective and reversible coding techniques for robust code generation",
                "queries": ["reversible programming", "bijective numeration"],
                "max_results": 8,
            },
            {
                "id": "quick-local-check",
                "type": "shell",
                "command": "python --version",
            },
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(template, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _load_spec(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Spec must be a JSON object.")
    jobs = payload.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("Spec must include a non-empty 'jobs' array.")
    seen: set[str] = set()
    for item in jobs:
        if not isinstance(item, dict):
            raise ValueError("Each job must be a JSON object.")
        jid = str(item.get("id", "")).strip()
        if not jid:
            raise ValueError("Each job requires a non-empty 'id'.")
        if jid in seen:
            raise ValueError(f"Duplicate job id: {jid}")
        seen.add(jid)
    return payload


def run_spec(spec_path: Path, output_root: Path, max_workers: int) -> int:
    spec = _load_spec(spec_path)
    name = str(spec.get("name") or "parallelism-run")
    safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in name).strip("-_") or "parallelism-run"
    run_dir = output_root / f"{safe_name}-{_utc_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=True)

    jobs = spec["jobs"]
    started_at = _now_iso()
    results: list[JobResult] = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_run_job, job, run_dir) for job in jobs]
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda r: r.job_id)
    ok_count = sum(1 for r in results if r.ok)
    failed_count = len(results) - ok_count

    report = {
        "schema_version": "parallelism_system_report_v1",
        "name": name,
        "spec_path": str(spec_path),
        "run_dir": str(run_dir),
        "started_at_utc": started_at,
        "finished_at_utc": _now_iso(),
        "workers": max_workers,
        "summary": {"total_jobs": len(results), "ok": ok_count, "failed": failed_count},
        "results": [r.__dict__ for r in results],
    }
    report_path = run_dir / "run_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if failed_count == 0 else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init-template", help="Write a starter workflow JSON spec.")
    init_cmd.add_argument(
        "--out",
        default=str(REPO_ROOT / "config" / "parallelism" / "my_parallelism_system.json"),
        help="Output JSON file path.",
    )

    run_cmd = sub.add_parser("run", help="Run a workflow spec in parallel.")
    run_cmd.add_argument("--spec", required=True, help="Path to workflow JSON spec.")
    run_cmd.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Root folder for run artifacts.")
    run_cmd.add_argument("--workers", type=int, default=max(2, (os.cpu_count() or 2) // 2), help="Parallel worker count.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "init-template":
        out_path = Path(args.out).expanduser().resolve()
        _write_template(out_path)
        print(f"Wrote template: {out_path}")
        return 0

    spec_path = Path(args.spec).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve()
    workers = max(1, int(args.workers))
    return run_spec(spec_path=spec_path, output_root=output_root, max_workers=workers)


if __name__ == "__main__":
    raise SystemExit(main())
