"""Run synthetic HYDRA mission-1000 and publish dashboard summary."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _count_duplicate_locks(jobs_obj: Dict[str, Any]) -> int:
    lock_counts: Dict[str, int] = {}
    for job in jobs_obj.get("jobs", []):
        lock = str(job.get("page_lock", "")).strip()
        if lock:
            lock_counts[lock] = lock_counts.get(lock, 0) + 1
    return sum(max(0, c - 1) for c in lock_counts.values())


def _publish_to_notion(summary: Dict[str, Any], mission_id: str, dashboard_db: str, notion_api_key: str) -> bool:
    headers = {
        "Authorization": f"Bearer {notion_api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    payload = {
        "parent": {"database_id": dashboard_db},
        "properties": {
            "Name": {"title": [{"text": {"content": f"{mission_id} {summary['run_id']}"}}]},
            "Status": {"select": {"name": "PASS" if summary["mission_pass"] else "FAIL"}},
            "Mission ID": {"rich_text": [{"text": {"content": mission_id}}]},
            "Run ID": {"rich_text": [{"text": {"content": summary["run_id"]}}]},
            "Failure Rate": {"number": summary["failure_rate"]},
            "Duplicate Locks": {"number": summary["duplicate_lock_incidents"]},
            "Action Count": {"number": summary["total_actions"]},
            "Decision Records": {"number": summary["decision_records"]},
        },
    }
    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as res:
            _ = res.read()
        return True
    except urllib.error.URLError:
        return False


def main() -> None:
    p = argparse.ArgumentParser(description="Run HYDRA mission 1000-step synthetic acceptance flow.")
    p.add_argument("--jobs-file", default="docs/hydra/MISSION_1000_SYNTHETIC_JOBS.json")
    p.add_argument("--output-dir", default="artifacts/hydra/mission_1000")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--max-actions-per-request", type=int, default=5)
    p.add_argument("--seed", type=int, default=1000)
    p.add_argument("--run-id", default="mission1000-seeded")
    p.add_argument("--url", default=os.getenv("SCBE_BROWSER_WEBHOOK_URL", "http://127.0.0.1:8001/v1/integrations/n8n/browse"))
    p.add_argument("--api-key", default=os.getenv("SCBE_API_KEY", "mission-synthetic-key"))
    a = p.parse_args()

    output_dir = Path(a.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "swarm_summary.json"

    cmd = [
        sys.executable,
        "scripts/aetherbrowse_swarm_runner.py",
        "--jobs-file",
        a.jobs_file,
        "--url",
        a.url,
        "--api-key",
        a.api_key,
        "--concurrency",
        str(a.concurrency),
        "--max-actions-per-request",
        str(a.max_actions_per_request),
        "--seed",
        str(a.seed),
        "--run-id",
        a.run_id,
        "--output-json",
        str(summary_path),
        "--artifact-root",
        str(output_dir / "runner_artifacts"),
    ]
    subprocess.run(cmd, check=True)

    swarm_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    jobs_obj = json.loads(Path(a.jobs_file).read_text(encoding="utf-8"))
    total_actions = sum(len(job.get("actions", [])) for job in jobs_obj.get("jobs", []))

    failed_actions = 0
    decision_records = 0
    missing_trace_hashes = 0
    for row in swarm_summary.get("results", []):
        if not isinstance(row, dict):
            continue
        resp = row.get("response") if isinstance(row.get("response"), dict) else {}
        failed_actions += int(resp.get("blocked_actions", 0) or 0)
        if row.get("decision_record_path"):
            decision_records += 1
        if not str(row.get("trace_hash", "")).strip():
            missing_trace_hashes += 1

    failure_rate = round((failed_actions / total_actions) if total_actions else 1.0, 6)
    duplicate_lock_incidents = _count_duplicate_locks(jobs_obj)
    mission_pass = (
        total_actions == 1000
        and failure_rate <= 0.01
        and duplicate_lock_incidents <= 2
        and decision_records == len(jobs_obj.get("jobs", []))
        and missing_trace_hashes == 0
    )

    acceptance_summary = {
        "mission_id": "MISSION_1000_SYNTHETIC",
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id": swarm_summary.get("run_id"),
        "total_jobs": len(jobs_obj.get("jobs", [])),
        "total_actions": total_actions,
        "failed_actions": failed_actions,
        "failure_rate": failure_rate,
        "duplicate_lock_incidents": duplicate_lock_incidents,
        "decision_records": decision_records,
        "missing_trace_hashes": missing_trace_hashes,
        "mission_pass": mission_pass,
        "swarm_summary_path": str(summary_path),
    }

    acceptance_path = output_dir / "mission_1000_acceptance_summary.json"
    acceptance_path.write_text(json.dumps(acceptance_summary, indent=2), encoding="utf-8")

    dashboard_db = os.getenv("NOTION_TESTING_DASHBOARD_DB", "").strip()
    notion_key = (os.getenv("NOTION_API_KEY", "") or os.getenv("NOTION_TOKEN", "")).strip()
    notion_attempted = bool(dashboard_db and notion_key)
    notion_posted = False
    if notion_attempted:
        notion_posted = _publish_to_notion(acceptance_summary, "MISSION_1000_SYNTHETIC", dashboard_db, notion_key)

    notion_log = {
        "attempted": notion_attempted,
        "posted": notion_posted,
        "dashboard_database": dashboard_db or None,
    }
    (output_dir / "notion_dashboard_log.json").write_text(json.dumps(notion_log, indent=2), encoding="utf-8")

    print(json.dumps({"status": "ok", **acceptance_summary, "notion": notion_log}, indent=2))


if __name__ == "__main__":
    main()
