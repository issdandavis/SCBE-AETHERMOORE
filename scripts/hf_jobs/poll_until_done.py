"""Poll an HF Job until its stage is no longer RUNNING/SCHEDULING.

Usage:
    python scripts/hf_jobs/poll_until_done.py <job_id> [--timeout-min 60]

Exits 0 with a final-state line on stdout when the job leaves RUNNING. Tolerates
transient inspect failures (treats them as 'still running' rather than terminal).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time

RUNNING_STAGES = {"RUNNING", "SCHEDULING", "QUEUED"}


def fetch_stage(job_id: str) -> tuple[str, str]:
    try:
        result = subprocess.run(
            ["hf", "jobs", "inspect", job_id],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            return ("UNKNOWN", f"inspect_returncode={result.returncode}")
        data = json.loads(result.stdout)
        if not data:
            return ("UNKNOWN", "empty_response")
        status = data[0].get("status") or {}
        stage = str(status.get("stage", "UNKNOWN"))
        message = str(status.get("message", ""))
        return (stage, message)
    except Exception as exc:
        return ("UNKNOWN", f"exception={type(exc).__name__}:{exc}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("job_id")
    ap.add_argument("--timeout-min", type=int, default=60)
    ap.add_argument("--poll-sec", type=int, default=30)
    args = ap.parse_args()

    deadline = time.time() + args.timeout_min * 60
    last_stage = None
    while time.time() < deadline:
        stage, message = fetch_stage(args.job_id)
        if stage != last_stage:
            print(f"stage={stage} msg={message}", flush=True)
            last_stage = stage
        if stage not in RUNNING_STAGES and stage != "UNKNOWN":
            print(f"FINAL stage={stage} msg={message}", flush=True)
            return 0
        time.sleep(args.poll_sec)

    print(f"TIMEOUT after {args.timeout_min} min, last stage={last_stage}", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
