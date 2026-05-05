"""Handle the DPO-on-v8 job verdict: collate logs, save report, summarize.

Reads the HF Jobs log for the given job id, extracts the inline gate report
that the DPO dispatcher prints, saves a durable copy, and prints a single
verdict line.

Usage:
    python scripts/hf_jobs/handle_dpo_on_v8_result.py <job_id>

The dispatcher prints lines like:
    {"event": "gate_report", "report": {... "overall_pass": true ...}}
    {"event": "training_complete", "summary": {...}}
We extract those and write them to:
    training/runs/coding-agent-qwen-stage6-boss-dpo-on-v8/eval/<job_id>.json

Exit code: 0 if gate passed, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = REPO_ROOT / "training" / "runs" / "coding-agent-qwen-stage6-boss-dpo-on-v8"
EVAL_DIR = RUN_DIR / "eval"


def fetch_logs(job_id: str) -> str:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    result = subprocess.run(
        ["hf", "jobs", "logs", job_id],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        text=True,
        timeout=120,
        check=False,
    )
    return result.stdout + "\n" + result.stderr


def extract_json_events(logs: str, event_name: str) -> list[dict]:
    found = []
    for line in logs.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("event") == event_name:
            found.append(obj)
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("job_id")
    args = ap.parse_args()

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    logs = fetch_logs(args.job_id)
    raw_log_path = EVAL_DIR / f"{args.job_id}.log"
    raw_log_path.write_text(logs, encoding="utf-8", errors="replace")

    gate_reports = extract_json_events(logs, "gate_report")
    summaries = extract_json_events(logs, "training_complete")

    report = gate_reports[-1].get("report") if gate_reports else None
    summary = summaries[-1].get("summary") if summaries else None

    out_path = EVAL_DIR / f"{args.job_id}_verdict.json"
    out_path.write_text(
        json.dumps(
            {
                "job_id": args.job_id,
                "report": report,
                "summary": summary,
                "raw_log_path": str(raw_log_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if report is None:
        print(f"verdict=NO_REPORT job={args.job_id} log={raw_log_path}", flush=True)
        return 2

    overall_pass = bool(report.get("overall_pass"))
    must_pass_all_ok = bool(report.get("must_pass_all_ok"))
    n_pass = report.get("n_pass", 0)
    n_total = report.get("n_total", 0)
    pass_rate = report.get("pass_rate", 0.0)
    pushed = bool((summary or {}).get("pushed_adapter", False))

    verdict = "PASS" if overall_pass else "FAIL"
    print(
        f"verdict={verdict} pass_rate={pass_rate:.3f} n_pass={n_pass}/{n_total} "
        f"must_pass_all_ok={must_pass_all_ok} pushed_adapter={pushed} "
        f"saved={out_path}",
        flush=True,
    )

    if not overall_pass:
        missing = {r.get("id"): r.get("missing_required") for r in report.get("results", [])}
        print(f"missing_per_prompt={json.dumps(missing)}", flush=True)

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
