"""
GitHub Workflow Audit & Self-Healing Dashboard
================================================

Maps all workflow health into a single view.
Identifies failures, triages them, and generates fix plans.

Usage:
    python scripts/system/github_workflow_audit.py
    python scripts/system/github_workflow_audit.py --fix   # attempt auto-fixes
    python scripts/system/github_workflow_audit.py --json   # machine-readable output
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WorkflowRun:
    name: str
    branch: str
    status: str
    conclusion: str
    run_id: int
    created_at: str


@dataclass
class WorkflowHealth:
    name: str
    category: str
    state: str  # active/disabled
    last_conclusion: str  # success/failure/skipped/None
    last_branch: str
    last_run_id: int | None
    failure_reason: str | None
    triage: str  # green/yellow/red
    fix_suggestion: str | None


def run_gh(args: list[str]) -> str:
    """Run a gh CLI command and return stdout."""
    result = subprocess.run(
        ["gh"] + args,
        capture_output=True, text=True, timeout=30,
        cwd=str(Path(__file__).resolve().parent.parent.parent),
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "gh command failed"
        raise RuntimeError(message)
    return result.stdout.strip()


def categorize_workflow_name(name: str) -> str:
    normalized = name.lower()
    if any(token in normalized for token in ("codeql", "security", "audit", "guard", "triage", "stale")):
        return "security"
    if any(
        token in normalized
        for token in ("deploy", "release", "publish", "docker", "pages", "gke", "eks", "aws", "kindle")
    ):
        return "deploy"
    if any(token in normalized for token in ("training", "dataset", "huggingface", "vertex", "notion")):
        return "training"
    if any(token in normalized for token in ("nightly", "daily", "ops", "loop", "sync", "rebase", "merge", "changelog")):
        return "automation"
    return "ci"


def local_workflow_files(repo_root: Path) -> list[Path]:
    return sorted((repo_root / ".github" / "workflows").glob("*.yml"))


def audit_local_workflows(repo_root: Path, reason: str | None = None) -> list[WorkflowHealth]:
    results = []
    for workflow_file in local_workflow_files(repo_root):
        display_name = workflow_file.stem
        results.append(
            WorkflowHealth(
                name=display_name,
                category=categorize_workflow_name(display_name),
                state="local",
                last_conclusion="local_only",
                last_branch="",
                last_run_id=None,
                failure_reason=reason,
                triage="yellow",
                fix_suggestion="Live GitHub workflow status unavailable from this shell; local workflow inventory generated instead.",
            )
        )
    return results


def get_workflows() -> list[dict]:
    """Get all workflows."""
    raw = run_gh(["workflow", "list", "--json", "name,state,id"])
    return json.loads(raw) if raw else []


def get_recent_runs(limit: int = 30) -> list[WorkflowRun]:
    """Get recent workflow runs."""
    raw = run_gh([
        "run", "list", "--limit", str(limit),
        "--json", "databaseId,status,conclusion,name,headBranch,createdAt"
    ])
    runs = json.loads(raw) if raw else []
    return [
        WorkflowRun(
            name=r["name"],
            branch=r.get("headBranch", ""),
            status=r.get("status", ""),
            conclusion=r.get("conclusion", ""),
            run_id=r.get("databaseId", 0),
            created_at=r.get("createdAt", ""),
        )
        for r in runs
    ]


def get_failure_log(run_id: int) -> str:
    """Get the failed log for a run."""
    try:
        return run_gh(["run", "view", str(run_id), "--log-failed"])[:2000]
    except Exception:
        return ""


def triage_failure(name: str, log: str) -> tuple[str, str]:
    """Triage a failure and suggest a fix."""
    log_lower = log.lower()

    # Known patterns
    if "import" in log_lower and "error" in log_lower:
        return "yellow", "Missing import/dependency — add to requirements or skip in CI with pytest marker"
    if "collection error" in log_lower:
        return "yellow", "Test collection error — missing module. Add conftest skip or install dependency"
    if "node.js 20" in log_lower and "deprecated" in log_lower:
        return "yellow", "Node.js 20 deprecation warning — update actions to support Node 24"
    if "timeout" in log_lower:
        return "red", "Timeout — workflow taking too long. Check for infinite loops or resource exhaustion"
    if "permission" in log_lower and "denied" in log_lower:
        return "red", "Permission denied — check workflow permissions and secrets"
    if "rate limit" in log_lower:
        return "yellow", "Rate limited — add retry logic or reduce API calls"
    if "assertionerror" in log_lower or "assert" in log_lower:
        return "red", "Test assertion failure — real bug, needs code fix"
    if "out of memory" in log_lower or "oom" in log_lower:
        return "red", "Out of memory — reduce test parallelism or split into smaller jobs"

    return "yellow", "Unknown failure — review logs manually"


def audit() -> list[WorkflowHealth]:
    """Run full audit of all workflows."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    try:
        workflows = get_workflows()
        runs = get_recent_runs(50)
        if not workflows:
            return audit_local_workflows(repo_root, "GitHub CLI returned no workflows")
    except Exception as exc:  # noqa: BLE001
        return audit_local_workflows(repo_root, str(exc))

    # Map latest run per workflow
    latest: dict[str, WorkflowRun] = {}
    for run in runs:
        if run.name not in latest:
            latest[run.name] = run

    results = []
    for wf in workflows:
        name = wf["name"]
        state = wf.get("state", "unknown")
        run = latest.get(name)

        if not run:
            results.append(WorkflowHealth(
                name=name, category=categorize_workflow_name(name), state=state, last_conclusion="never_run",
                last_branch="", last_run_id=None,
                failure_reason=None, triage="yellow",
                fix_suggestion="Workflow has never run — trigger manually or check triggers",
            ))
            continue

        if run.conclusion == "success":
            results.append(WorkflowHealth(
                name=name, category=categorize_workflow_name(name), state=state, last_conclusion="success",
                last_branch=run.branch, last_run_id=run.run_id,
                failure_reason=None, triage="green", fix_suggestion=None,
            ))
        elif run.conclusion == "skipped":
            results.append(WorkflowHealth(
                name=name, category=categorize_workflow_name(name), state=state, last_conclusion="skipped",
                last_branch=run.branch, last_run_id=run.run_id,
                failure_reason=None, triage="green", fix_suggestion=None,
            ))
        elif run.conclusion == "failure":
            log = get_failure_log(run.run_id)
            triage, fix = triage_failure(name, log)
            results.append(WorkflowHealth(
                name=name, category=categorize_workflow_name(name), state=state, last_conclusion="failure",
                last_branch=run.branch, last_run_id=run.run_id,
                failure_reason=log[:500] if log else "No log available",
                triage=triage, fix_suggestion=fix,
            ))
        else:
            results.append(WorkflowHealth(
                name=name, category=categorize_workflow_name(name), state=state, last_conclusion=run.conclusion or "unknown",
                last_branch=run.branch, last_run_id=run.run_id,
                failure_reason=None, triage="yellow", fix_suggestion=None,
            ))

    return sorted(results, key=lambda r: {"red": 0, "yellow": 1, "green": 2}.get(r.triage, 3))


def print_dashboard(results: list[WorkflowHealth]):
    """Print human-readable dashboard."""
    icons = {"green": "+", "yellow": "~", "red": "!"}

    print("=" * 70)
    print("  SCBE-AETHERMOORE GitHub Workflow Audit")
    print("=" * 70)

    red = [r for r in results if r.triage == "red"]
    yellow = [r for r in results if r.triage == "yellow"]
    green = [r for r in results if r.triage == "green"]

    print(f"\n  RED: {len(red)} | YELLOW: {len(yellow)} | GREEN: {len(green)} | TOTAL: {len(results)}")

    for section, items, color in [("RED — Needs Fix", red, "red"), ("YELLOW — Warning", yellow, "yellow"), ("GREEN — Passing", green, "green")]:
        if items:
            print(f"\n--- {section} ({len(items)}) ---")
            for r in items:
                icon = icons[color]
                print(f"  [{icon}] {r.name} [{r.category}]")
                if r.last_conclusion and r.last_conclusion != "success":
                    print(f"      Last: {r.last_conclusion} on {r.last_branch}")
                if r.fix_suggestion:
                    print(f"      Fix: {r.fix_suggestion}")

    print(f"\n{'=' * 70}")


def main():
    args = sys.argv[1:]
    as_json = "--json" in args

    print("Auditing GitHub workflows...")
    results = audit()

    if as_json:
        output = [
            {
                "name": r.name,
                "category": r.category,
                "state": r.state,
                "conclusion": r.last_conclusion,
                "triage": r.triage,
                "branch": r.last_branch,
                "fix": r.fix_suggestion,
            }
            for r in results
        ]
        print(json.dumps(output, indent=2))
    else:
        print_dashboard(results)

    # Save to artifacts
    out_dir = Path(__file__).resolve().parent.parent.parent / "artifacts" / "system-audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "workflow_audit.json", "w") as f:
        json.dump([
            {
                "name": r.name,
                "category": r.category,
                "state": r.state,
                "conclusion": r.last_conclusion,
                "triage": r.triage,
                "branch": r.last_branch,
                "run_id": r.last_run_id,
                "fix": r.fix_suggestion,
                "failure_reason": r.failure_reason,
            }
            for r in results
        ], f, indent=2)
    print(f"\nSaved to {out_dir / 'workflow_audit.json'}")

    # Generate SFT training pairs from audit results
    sft_dir = Path(__file__).resolve().parent.parent.parent / "training" / "sft_records"
    sft_dir.mkdir(parents=True, exist_ok=True)
    sft_file = sft_dir / "sft_workflow_audit.jsonl"
    sft_pairs = []
    for r in results:
        pair = {
            "instruction": f"What is the status of the '{r.name}' GitHub workflow?",
            "output": json.dumps({
                "name": r.name,
                "category": r.category,
                "conclusion": r.last_conclusion,
                "triage": r.triage,
                "fix": r.fix_suggestion,
            }),
            "label": f"workflow_audit_{r.triage}",
            "timestamp": time.time(),
        }
        sft_pairs.append(pair)

        # Generate fix-oriented SFT for failures
        if r.triage in ("red", "yellow") and r.fix_suggestion:
            fix_pair = {
                "instruction": f"The '{r.name}' workflow failed with conclusion '{r.last_conclusion}'. How do I fix it?",
                "output": r.fix_suggestion,
                "label": f"workflow_fix_{r.triage}",
                "timestamp": time.time(),
            }
            sft_pairs.append(fix_pair)

    with open(sft_file, "w") as f:
        for pair in sft_pairs:
            f.write(json.dumps(pair) + "\n")
    print(f"Generated {len(sft_pairs)} SFT training pairs at {sft_file}")

    # Push to HuggingFace if --push flag
    if "--push" in args:
        try:
            from huggingface_hub import HfApi
            import os
            api = HfApi(token=os.environ.get("HF_TOKEN"))
            api.upload_file(
                path_or_fileobj=str(sft_file),
                path_in_repo="data/sft_workflow_audit.jsonl",
                repo_id="issdandavis/scbe-aethermoore-training-data",
                repo_type="dataset",
            )
            print("Pushed SFT pairs to HuggingFace dataset")
        except Exception as e:
            print(f"HF push failed: {e}")


if __name__ == "__main__":
    main()
