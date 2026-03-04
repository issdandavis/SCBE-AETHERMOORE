"""Asana -> AetherBrowse orchestration bridge.

Pulls scheduled Asana tasks from a project, converts them into browser jobs,
runs governed execution via scripts/aetherbrowse_swarm_runner.py, and writes
results back to Asana as task comments (and optional completion on ALLOW).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

ASANA_BASE_URL = "https://app.asana.com/api/1.0"
URL_RE = re.compile(r"https?://[^\s)]+", re.IGNORECASE)


class AsanaClient:
    def __init__(self, token: str):
        self.token = token.strip()
        if not self.token:
            raise RuntimeError("Missing Asana token.")

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{ASANA_BASE_URL}{path}"
        if params:
            query = urllib.parse.urlencode(params, doseq=True)
            url = f"{url}?{query}"

        payload = None
        if body is not None:
            payload = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(
            url=url,
            data=payload,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Asana API HTTP {exc.code}: {raw}") from exc

    def list_project_tasks(self, project_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        params = {
            "project": project_id,
            "limit": limit,
            "opt_fields": "gid,name,notes,completed,due_on,permalink_url",
        }
        data = self._request("GET", "/tasks", params=params).get("data", [])
        if not isinstance(data, list):
            return []
        return data

    def add_comment(self, task_gid: str, text: str) -> None:
        self._request("POST", f"/tasks/{task_gid}/stories", body={"data": {"text": text}})

    def complete_task(self, task_gid: str) -> None:
        self._request("PUT", f"/tasks/{task_gid}", body={"data": {"completed": True}})


def _extract_url(notes: str) -> Optional[str]:
    match = URL_RE.search(notes or "")
    return match.group(0) if match else None


def _extract_actions(notes: str, fallback_url: str) -> List[Dict[str, Any]]:
    marker = "AETHERBROWSE_ACTIONS:"
    actions: List[Dict[str, Any]] = []
    if notes and marker in notes:
        tail = notes.split(marker, 1)[1].strip()
        if tail:
            try:
                parsed = json.loads(tail)
                if isinstance(parsed, list) and parsed:
                    actions = parsed
            except json.JSONDecodeError:
                actions = []
    if actions:
        return actions
    return [
        {"action": "navigate", "target": fallback_url, "timeout_ms": 12000},
        {"action": "extract", "target": "h1", "timeout_ms": 12000},
        {"action": "screenshot", "target": "full_page", "timeout_ms": 12000},
    ]


def _risk_tier(task_name: str, actions: List[Dict[str, Any]]) -> str:
    name_upper = (task_name or "").upper()
    if "[DELIBERATION]" in name_upper:
        return "DELIBERATION"
    for action in actions:
        kind = str(action.get("action", "")).strip().lower()
        if kind in {"click", "type"}:
            return "DELIBERATION"
    return "REFLEX"


def _task_due_in_scope(task: Dict[str, Any], due_on_or_before: str, include_no_due: bool) -> bool:
    if bool(task.get("completed", False)):
        return False
    due_on = task.get("due_on")
    if not due_on:
        return include_no_due
    return str(due_on) <= due_on_or_before


def _build_jobs(
    tasks: List[Dict[str, Any]],
    project_id: str,
    due_on_or_before: str,
    include_no_due: bool,
    capability_token: str,
) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    now_run = f"asana-{int(time.time())}"
    for task in tasks:
        if not _task_due_in_scope(task, due_on_or_before, include_no_due):
            continue

        task_gid = str(task.get("gid", "")).strip()
        if not task_gid:
            continue
        task_name = str(task.get("name", "")).strip() or f"asana-task-{task_gid}"
        notes = str(task.get("notes", "") or "")
        url = _extract_url(notes) or "https://example.com"
        actions = _extract_actions(notes, url)
        tier = _risk_tier(task_name, actions)

        job: Dict[str, Any] = {
            "job_id": f"asana-{task_gid}",
            "agent_id": "asana-agent",
            "session_id": f"asana-session-{task_gid}",
            "risk_tier": tier,
            "workflow_id": f"asana-project-{project_id}",
            "run_id": now_run,
            "source": "asana",
            "verify": {"max_redirects": 3},
            "actions": actions,
            "_task_gid": task_gid,
            "_task_name": task_name,
            "_task_permalink": task.get("permalink_url"),
        }
        if tier == "DELIBERATION" and capability_token.strip():
            job["capability_token"] = capability_token.strip()
        jobs.append(job)
    return jobs


def _run_swarm_runner(
    *,
    jobs: List[Dict[str, Any]],
    endpoint_url: str,
    api_key: str,
    concurrency: int,
    output_json: Path,
    screenshots_dir: Path,
) -> Dict[str, Any]:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    jobs_file = output_json.parent / "asana_jobs.generated.json"
    jobs_payload = {"jobs": [{k: v for k, v in job.items() if not k.startswith("_")} for job in jobs]}
    jobs_file.write_text(json.dumps(jobs_payload, indent=2), encoding="utf-8")

    repo_root = Path(__file__).resolve().parent.parent
    runner = repo_root / "scripts" / "aetherbrowse_swarm_runner.py"
    cmd = [
        sys.executable,
        str(runner),
        "--jobs-file",
        str(jobs_file),
        "--url",
        endpoint_url,
        "--api-key",
        api_key,
        "--concurrency",
        str(concurrency),
        "--save-screenshots-dir",
        str(screenshots_dir),
        "--output-json",
        str(output_json),
    ]

    proc = subprocess.run(cmd, cwd=str(repo_root), check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Swarm runner failed with exit code {proc.returncode}")

    return json.loads(output_json.read_text(encoding="utf-8"))


def _index_results(summary: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    idx: Dict[str, Dict[str, Any]] = {}
    for item in summary.get("results", []):
        if not isinstance(item, dict):
            continue
        job_id = str(item.get("job_id", "")).strip()
        if job_id:
            idx[job_id] = item
    return idx


def _comment_for_result(task_name: str, task_gid: str, result: Optional[Dict[str, Any]], run_id: str) -> str:
    if not result:
        return f"[SCBE][AetherBrowse] task={task_name} ({task_gid}) run={run_id} status=NO_RESULT"
    decision = result.get("decision")
    score = result.get("verification_score")
    trace_hash = str(result.get("trace_hash", ""))[:12]
    req_err = result.get("request_error")
    return (
        f"[SCBE][AetherBrowse] run={run_id} decision={decision} score={score} "
        f"trace={trace_hash} request_error={req_err}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Orchestrate Asana scheduled tasks into governed browser jobs.")
    parser.add_argument("--project-id", default=os.getenv("ASANA_PROJECT_ID", ""), help="Asana project GID.")
    parser.add_argument("--workspace-id", default=os.getenv("ASANA_WORKSPACE_ID", ""), help="Asana workspace GID (optional).")
    parser.add_argument("--asana-token", default=os.getenv("ASANA_TOKEN", os.getenv("ASANA_ACCESS_TOKEN", "")))
    parser.add_argument("--endpoint-url", default=os.getenv("SCBE_BROWSER_WEBHOOK_URL", "http://127.0.0.1:8001/v1/integrations/n8n/browse"))
    parser.add_argument("--api-key", default=os.getenv("SCBE_API_KEY", os.getenv("N8N_API_KEY", "")))
    parser.add_argument("--max-tasks", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--include-no-due", action="store_true")
    parser.add_argument("--due-on-or-before", default=date.today().isoformat())
    parser.add_argument("--complete-on-allow", action="store_true")
    parser.add_argument("--capability-token", default=os.getenv("SCBE_CAPABILITY_TOKEN", ""))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-json", default="artifacts/asana_bridge/latest_run.json")
    args = parser.parse_args()

    if not args.project_id.strip():
        raise RuntimeError("Missing --project-id (or ASANA_PROJECT_ID)")
    if not args.asana_token.strip():
        raise RuntimeError("Missing --asana-token (or ASANA_TOKEN / ASANA_ACCESS_TOKEN)")
    if not args.api_key.strip():
        raise RuntimeError("Missing --api-key (or SCBE_API_KEY / N8N_API_KEY)")

    client = AsanaClient(args.asana_token)
    tasks = client.list_project_tasks(args.project_id, limit=max(1, args.max_tasks))

    jobs = _build_jobs(
        tasks=tasks,
        project_id=args.project_id,
        due_on_or_before=args.due_on_or_before,
        include_no_due=args.include_no_due,
        capability_token=args.capability_token,
    )
    if not jobs:
        print(json.dumps({"status": "no_jobs", "tasks_seen": len(tasks)}, indent=2))
        return

    output_json = Path(args.output_json)
    screenshots_dir = output_json.parent / "screenshots"

    if args.dry_run:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps({"status": "dry_run", "jobs": jobs}, indent=2), encoding="utf-8")
        print(json.dumps({"status": "dry_run", "jobs_count": len(jobs), "output_json": str(output_json)}, indent=2))
        return

    summary = _run_swarm_runner(
        jobs=jobs,
        endpoint_url=args.endpoint_url,
        api_key=args.api_key,
        concurrency=max(1, args.concurrency),
        output_json=output_json,
        screenshots_dir=screenshots_dir,
    )
    results_idx = _index_results(summary)
    run_id = str(summary.get("run_id", f"asana-{int(time.time())}"))

    for job in jobs:
        task_gid = str(job["_task_gid"])
        task_name = str(job["_task_name"])
        result = results_idx.get(str(job["job_id"]))
        comment = _comment_for_result(task_name, task_gid, result, run_id)
        client.add_comment(task_gid, comment)
        if args.complete_on_allow and result and str(result.get("decision")) == "ALLOW":
            client.complete_task(task_gid)

    print(
        json.dumps(
            {
                "status": "ok",
                "tasks_seen": len(tasks),
                "jobs_run": len(jobs),
                "run_id": run_id,
                "output_json": str(output_json),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
