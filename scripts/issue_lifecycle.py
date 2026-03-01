#!/usr/bin/env python3
"""
SCBE Autonomous Issue Lifecycle Pipeline
=========================================

Full pipeline: triage → council → execute → merge → close.

Phases:
  1. INGEST   — Pull open GitHub issues + scan postprocess tasks
  2. TRIAGE   — Auto-classify severity/effort/type, assign priority labels
  3. COUNCIL  — AI group inspection: structured analysis + recommended path
  4. EXECUTE  — For approved items: branch → implement → test → PR
  5. CLOSE    — Merge passing PRs, close resolved issues

Usage:
  # Full pipeline (triage + council report, no auto-execute)
  python scripts/issue_lifecycle.py

  # Triage only
  python scripts/issue_lifecycle.py --phase triage

  # Execute approved items (creates branches + PRs)
  python scripts/issue_lifecycle.py --phase execute --auto-execute

  # Close merged PRs and stale issues
  python scripts/issue_lifecycle.py --phase close

  # Full autonomous run (triage → council → execute → close)
  python scripts/issue_lifecycle.py --auto-execute --auto-close
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "issue-lifecycle"
POSTPROCESS_LATEST = ROOT / "artifacts" / "ops-autopilot" / "latest.json"
TELEGRAM_NOTIFY = ROOT / "scripts" / "telegram_notify.py"


# ── Severity / effort heuristics ──────────────────────────────────────

SEVERITY_KEYWORDS = {
    "critical": 4,
    "security": 4,
    "crash": 4,
    "data loss": 4,
    "vulnerability": 4,
    "priority-high": 3,
    "bug": 3,
    "broken": 3,
    "regression": 3,
    "enhancement": 2,
    "feature": 2,
    "refactor": 1,
    "docs": 1,
    "chore": 1,
    "automated": 1,
    "daily-review": 1,
}

EFFORT_HINTS = {
    "typo": 1,
    "config": 1,
    "label": 1,
    "docs": 1,
    "rename": 1,
    "cleanup": 2,
    "test": 2,
    "fix": 2,
    "upgrade": 2,
    "refactor": 3,
    "feature": 3,
    "implement": 4,
    "system": 4,
    "architecture": 5,
    "protocol": 5,
}

AUTO_SAFE_LABELS = {"automated", "daily-review", "chore", "docs", "stale"}
AUTO_CLOSE_LABELS = {"automated", "daily-review"}


# ── Utilities ─────────────────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _run(cmd: List[str], *, cwd: Path = ROOT, timeout: int = 60) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, timeout=timeout, check=False,
        encoding="utf-8", errors="replace", env=env,
    )


def _gh_json(cmd: List[str]) -> Any:
    result = _run(["gh"] + cmd)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(cmd)} failed: {result.stderr or 'unknown error'}")
    stdout = result.stdout or ""
    return json.loads(stdout) if stdout.strip() else []


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ── Phase 1: INGEST ──────────────────────────────────────────────────

def ingest_github_issues() -> List[Dict[str, Any]]:
    """Pull all open issues from GitHub."""
    issues = _gh_json([
        "issue", "list",
        "--state", "open",
        "--limit", "100",
        "--json", "number,title,body,labels,createdAt,updatedAt,assignees,comments",
    ])
    return issues


def ingest_scan_tasks() -> List[Dict[str, Any]]:
    """Pull tasks from latest scan postprocess."""
    # Find latest postprocess
    scans_dir = ROOT / "artifacts" / "repo_scans"
    if not scans_dir.exists():
        return []

    scan_dirs = sorted(
        [d for d in scans_dir.iterdir() if d.is_dir() and (d / "postprocess" / "tasks.json").exists()],
        key=lambda d: d.name,
        reverse=True,
    )
    if not scan_dirs:
        return []

    tasks_file = scan_dirs[0] / "postprocess" / "tasks.json"
    data = _read_json(tasks_file)
    return data.get("tasks", [])


def ingest_open_prs() -> List[Dict[str, Any]]:
    """Pull open PRs for merge/close tracking."""
    return _gh_json([
        "pr", "list",
        "--state", "open",
        "--limit", "50",
        "--json", "number,title,headRefName,state,mergeable,statusCheckRollup,labels",
    ])


# ── Phase 2: TRIAGE ──────────────────────────────────────────────────

def compute_severity(issue: Dict[str, Any]) -> int:
    """Score 1-4 based on labels + title keywords."""
    score = 1
    text = (issue.get("title", "") + " " + " ".join(
        l.get("name", "") for l in issue.get("labels", [])
    )).lower()
    for keyword, weight in SEVERITY_KEYWORDS.items():
        if keyword in text:
            score = max(score, weight)
    return score


def estimate_effort(issue: Dict[str, Any]) -> int:
    """Score 1-5 based on title/body complexity hints."""
    score = 2  # default medium
    text = (issue.get("title", "") + " " + (issue.get("body") or "")).lower()
    for keyword, weight in EFFORT_HINTS.items():
        if keyword in text:
            score = max(score, weight)
    return score


def classify_type(issue: Dict[str, Any]) -> str:
    """Classify: bug, feature, security, ops, docs, stale."""
    labels = {l.get("name", "").lower() for l in issue.get("labels", [])}
    title = issue.get("title", "").lower()

    if "security" in labels or "vulnerability" in title:
        return "security"
    if "bug" in labels or "crash" in title or "broken" in title:
        return "bug"
    if "enhancement" in labels or "feature" in labels or "feat:" in title:
        return "feature"
    if "automated" in labels or "daily-review" in labels:
        return "ops"
    if "docs" in labels or "documentation" in title:
        return "docs"
    return "task"


def is_stale(issue: Dict[str, Any], stale_days: int = 30) -> bool:
    """Check if issue hasn't been updated in stale_days."""
    updated = issue.get("updatedAt", "")
    if not updated:
        return False
    try:
        updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - updated_dt).days
        return age > stale_days
    except Exception:
        return False


def is_auto_closeable(issue: Dict[str, Any]) -> bool:
    """Daily review failures and automated issues can be batch-closed."""
    labels = {l.get("name", "").lower() for l in issue.get("labels", [])}
    return bool(labels & AUTO_CLOSE_LABELS) and is_stale(issue, stale_days=3)


def triage_issue(issue: Dict[str, Any]) -> Dict[str, Any]:
    """Full triage of a single issue."""
    severity = compute_severity(issue)
    effort = estimate_effort(issue)
    issue_type = classify_type(issue)
    stale = is_stale(issue)
    auto_close = is_auto_closeable(issue)

    # Priority score: severity * 2 - effort (higher = do first)
    priority_score = severity * 2 - effort

    # Match against scan tasks
    matched_scan_tasks = []

    return {
        "number": issue.get("number"),
        "title": issue.get("title"),
        "labels": [l.get("name") for l in issue.get("labels", [])],
        "type": issue_type,
        "severity": severity,
        "effort": effort,
        "priority_score": priority_score,
        "stale": stale,
        "auto_close": auto_close,
        "matched_scan_tasks": matched_scan_tasks,
        "recommendation": _recommend_action(severity, effort, issue_type, stale, auto_close),
    }


def _recommend_action(severity: int, effort: int, issue_type: str, stale: bool, auto_close: bool) -> str:
    if auto_close:
        return "AUTO_CLOSE"
    if stale and severity <= 2:
        return "CLOSE_STALE"
    if severity >= 4 and effort <= 2:
        return "AUTO_FIX"
    if severity >= 3:
        return "PRIORITY_REVIEW"
    if effort <= 2:
        return "QUICK_WIN"
    return "BACKLOG"


def triage_scan_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Triage a scan-generated task."""
    priority = task.get("priority", 5)
    severity = max(1, 5 - priority)  # P1 → severity 4, P4 → severity 1
    return {
        "id": task.get("id"),
        "title": task.get("title"),
        "priority": priority,
        "severity": severity,
        "effort": 3,  # scan tasks are medium effort
        "type": "scan_task",
        "rationale": task.get("rationale", ""),
        "suggested_files": task.get("suggested_files", [])[:10],
        "recommendation": "PRIORITY_REVIEW" if priority <= 2 else "BACKLOG",
        "source": "scan_postprocess",
    }


# ── Phase 3: COUNCIL ─────────────────────────────────────────────────

def council_review(triaged: List[Dict[str, Any]], scan_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    AI group inspection: generate a structured council report.

    The "council" is a deterministic multi-perspective analysis:
    - Security lens: what's the attack surface impact?
    - Revenue lens: does this block or enable money?
    - Tech debt lens: is this creating or reducing debt?
    - Effort lens: what's the ROI (severity / effort)?
    """
    report = {
        "generated_at": _utc_now(),
        "total_issues": len(triaged),
        "total_scan_tasks": len(scan_tasks),
        "verdicts": [],
        "execution_queue": [],
        "close_queue": [],
        "backlog": [],
        "summary": {},
    }

    # Combine and sort by priority
    all_items = []
    for t in triaged:
        all_items.append({**t, "source": "github"})
    for s in scan_tasks:
        all_items.append(s)

    all_items.sort(key=lambda x: (-x.get("severity", 0), x.get("effort", 5)))

    for item in all_items:
        verdict = _council_verdict(item)
        report["verdicts"].append(verdict)

        action = verdict["action"]
        if action in ("AUTO_FIX", "QUICK_WIN"):
            report["execution_queue"].append(verdict)
        elif action in ("AUTO_CLOSE", "CLOSE_STALE"):
            report["close_queue"].append(verdict)
        elif action == "PRIORITY_REVIEW":
            report["execution_queue"].append(verdict)
        else:
            report["backlog"].append(verdict)

    report["summary"] = {
        "execute_count": len(report["execution_queue"]),
        "close_count": len(report["close_queue"]),
        "backlog_count": len(report["backlog"]),
        "highest_severity": max((v.get("severity", 0) for v in report["verdicts"]), default=0),
        "quick_wins": sum(1 for v in report["verdicts"] if v.get("action") == "QUICK_WIN"),
    }

    return report


def _council_verdict(item: Dict[str, Any]) -> Dict[str, Any]:
    """Multi-lens analysis of a single item."""
    severity = item.get("severity", 1)
    effort = item.get("effort", 3)
    item_type = item.get("type", "task")
    roi = round(severity / max(effort, 1), 2)

    # Security lens
    security_note = ""
    if item_type == "security" or severity >= 4:
        security_note = "URGENT: security surface exposed, blocks product trust"
    elif "governance" in item.get("title", "").lower():
        security_note = "governance-related: affects L13 decision integrity"

    # Revenue lens
    revenue_note = ""
    if "api" in item.get("title", "").lower() or "contract" in item.get("title", "").lower():
        revenue_note = "blocks sellable API surface"
    elif item_type == "feature":
        revenue_note = "potential revenue enabler"

    # Tech debt lens
    debt_note = ""
    if item.get("stale"):
        debt_note = "stale item: resolve or close to reduce noise"
    elif effort >= 4:
        debt_note = "high-effort: consider breaking into sub-tasks"

    return {
        "number": item.get("number") or item.get("id"),
        "title": item.get("title"),
        "source": item.get("source", "unknown"),
        "type": item_type,
        "severity": severity,
        "effort": effort,
        "roi": roi,
        "action": item.get("recommendation", "BACKLOG"),
        "security": security_note,
        "revenue": revenue_note,
        "tech_debt": debt_note,
        "rationale": item.get("rationale", ""),
        "suggested_files": item.get("suggested_files", []),
    }


# ── Phase 4: EXECUTE ─────────────────────────────────────────────────

def execute_item(verdict: Dict[str, Any], *, dry_run: bool = True) -> Dict[str, Any]:
    """
    Execute a single triaged item:
    1. Create branch from clean-sync
    2. Apply fix (for known patterns)
    3. Run tests
    4. Create PR
    """
    number = verdict.get("number")
    title = verdict.get("title", "unknown")
    action = verdict.get("action")
    safe_title = re.sub(r"[^a-zA-Z0-9-]", "-", title.lower())[:40].strip("-")
    branch = f"auto/{number}-{safe_title}"

    result = {
        "number": number,
        "title": title,
        "action": action,
        "branch": branch,
        "steps": [],
        "status": "pending",
    }

    if dry_run:
        result["status"] = "dry_run"
        result["steps"].append("DRY RUN: would create branch, apply fix, test, PR")
        return result

    # Step 1: Create branch
    checkout = _run(["git", "checkout", "-b", branch, "clean-sync"])
    if checkout.returncode != 0:
        result["status"] = "failed"
        result["steps"].append(f"branch creation failed: {checkout.stderr}")
        return result
    result["steps"].append(f"created branch {branch}")

    # Step 2: Apply fix based on type
    if action == "AUTO_CLOSE":
        result["status"] = "close_only"
        _run(["git", "checkout", "clean-sync"])
        return result

    # For now, auto-execute creates the branch + PR with analysis
    # Actual code changes would come from AI agent integration

    # Step 3: Run tests
    test_result = _run(
        [sys.executable, "-m", "pytest", "tests/", "-x", "--timeout=60", "-q"],
        timeout=120,
    )
    result["tests_passed"] = test_result.returncode == 0
    result["steps"].append(f"tests: {'passed' if test_result.returncode == 0 else 'FAILED'}")

    # Step 4: Push and create PR
    if test_result.returncode == 0:
        push = _run(["git", "push", "-u", "origin", branch])
        if push.returncode == 0:
            pr_body = _format_pr_body(verdict)
            pr = _run([
                "gh", "pr", "create",
                "--title", f"[auto] #{number}: {title[:60]}",
                "--body", pr_body,
                "--base", "clean-sync",
                "--head", branch,
            ])
            if pr.returncode == 0:
                result["pr_url"] = pr.stdout.strip()
                result["steps"].append(f"PR created: {result['pr_url']}")
                result["status"] = "pr_created"
            else:
                result["steps"].append(f"PR creation failed: {pr.stderr}")
                result["status"] = "push_only"
        else:
            result["steps"].append(f"push failed: {push.stderr}")
            result["status"] = "local_only"
    else:
        result["status"] = "tests_failed"

    # Return to clean-sync
    _run(["git", "checkout", "clean-sync"])
    return result


def _format_pr_body(verdict: Dict[str, Any]) -> str:
    lines = [
        "## Summary",
        f"Auto-triaged from #{verdict.get('number', '?')}",
        f"- Type: {verdict.get('type')}",
        f"- Severity: {verdict.get('severity')}/4",
        f"- Effort: {verdict.get('effort')}/5",
        f"- ROI: {verdict.get('roi')}",
        "",
    ]
    if verdict.get("security"):
        lines.append(f"**Security**: {verdict['security']}")
    if verdict.get("revenue"):
        lines.append(f"**Revenue**: {verdict['revenue']}")
    if verdict.get("rationale"):
        lines.append(f"\n**Rationale**: {verdict['rationale']}")
    if verdict.get("suggested_files"):
        lines.append("\n**Files**:")
        for f in verdict["suggested_files"][:10]:
            lines.append(f"- `{f}`")
    lines.extend([
        "",
        "## Test plan",
        "- [ ] All existing tests pass",
        "- [ ] No new security markers introduced",
        "- [ ] Governance gate passes for affected paths",
        "",
        "Generated by SCBE Issue Lifecycle Pipeline",
    ])
    return "\n".join(lines)


# ── Phase 5: CLOSE ───────────────────────────────────────────────────

def close_stale_issues(close_queue: List[Dict[str, Any]], *, dry_run: bool = True) -> List[Dict[str, Any]]:
    """Close issues marked for auto-close."""
    results = []
    for item in close_queue:
        number = item.get("number")
        if not number or not isinstance(number, int):
            continue

        result = {"number": number, "title": item.get("title"), "action": item.get("action")}

        if dry_run:
            result["status"] = "dry_run"
            results.append(result)
            continue

        comment = _run([
            "gh", "issue", "comment", str(number),
            "--body", f"Auto-closing: {item.get('action', 'stale')}. "
                      f"Triaged by SCBE Issue Lifecycle at {_utc_now()}.",
        ])
        close = _run(["gh", "issue", "close", str(number)])
        result["status"] = "closed" if close.returncode == 0 else "failed"
        result["error"] = close.stderr if close.returncode != 0 else None
        results.append(result)

    return results


def merge_passing_prs(*, dry_run: bool = True) -> List[Dict[str, Any]]:
    """Merge PRs that are passing all checks and labeled auto."""
    prs = ingest_open_prs()
    results = []

    for pr in prs:
        # Only merge auto-created PRs
        head = pr.get("headRefName", "")
        if not head.startswith("auto/"):
            continue

        number = pr.get("number")
        mergeable = pr.get("mergeable", "UNKNOWN")

        # Check status checks
        checks = pr.get("statusCheckRollup", []) or []
        all_passing = all(
            c.get("conclusion") == "SUCCESS" or c.get("status") == "COMPLETED"
            for c in checks
        ) if checks else True  # no checks = mergeable

        result = {
            "number": number,
            "title": pr.get("title"),
            "branch": head,
            "mergeable": mergeable,
            "checks_passing": all_passing,
        }

        if mergeable != "MERGEABLE" or not all_passing:
            result["status"] = "not_ready"
            results.append(result)
            continue

        if dry_run:
            result["status"] = "dry_run"
            results.append(result)
            continue

        merge = _run([
            "gh", "pr", "merge", str(number),
            "--squash",
            "--delete-branch",
            "--body", f"Auto-merged by SCBE Issue Lifecycle at {_utc_now()}",
        ])
        result["status"] = "merged" if merge.returncode == 0 else "failed"
        results.append(result)

    return results


# ── Report formatting ─────────────────────────────────────────────────

def format_council_md(report: Dict[str, Any]) -> str:
    """Render council report as Markdown."""
    lines = [
        "# SCBE Issue Lifecycle — Council Report",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Issues: {report['total_issues']} | Scan tasks: {report['total_scan_tasks']}",
        "",
        f"## Summary",
        f"- Execute: **{report['summary']['execute_count']}**",
        f"- Close: **{report['summary']['close_count']}**",
        f"- Backlog: **{report['summary']['backlog_count']}**",
        f"- Quick wins: {report['summary']['quick_wins']}",
        f"- Highest severity: {report['summary']['highest_severity']}/4",
        "",
    ]

    if report["execution_queue"]:
        lines.append("## Execution Queue (do next)")
        lines.append("")
        lines.append("| # | Title | Type | Sev | Effort | ROI | Action |")
        lines.append("|---|-------|------|-----|--------|-----|--------|")
        for v in report["execution_queue"]:
            lines.append(
                f"| {v['number']} | {v['title'][:50]} | {v['type']} | "
                f"{v['severity']} | {v['effort']} | {v['roi']} | {v['action']} |"
            )
        lines.append("")

        for v in report["execution_queue"]:
            lines.append(f"### {v['number']}: {v['title']}")
            if v.get("security"):
                lines.append(f"- **Security**: {v['security']}")
            if v.get("revenue"):
                lines.append(f"- **Revenue**: {v['revenue']}")
            if v.get("tech_debt"):
                lines.append(f"- **Tech debt**: {v['tech_debt']}")
            if v.get("rationale"):
                lines.append(f"- **Rationale**: {v['rationale']}")
            lines.append("")

    if report["close_queue"]:
        lines.append("## Close Queue")
        lines.append("")
        for v in report["close_queue"]:
            lines.append(f"- #{v['number']}: {v['title']} — {v['action']}")
        lines.append("")

    if report["backlog"]:
        lines.append("## Backlog")
        lines.append("")
        for v in report["backlog"][:20]:
            lines.append(f"- #{v['number']}: {v['title']} (sev={v['severity']}, effort={v['effort']})")
        lines.append("")

    return "\n".join(lines)


def format_telegram(report: Dict[str, Any]) -> str:
    """Format council report for Telegram."""
    s = report.get("summary", {})
    lines = [
        f"*SCBE Council Report*",
        f"Execute: {s.get('execute_count', 0)} | Close: {s.get('close_count', 0)} | Backlog: {s.get('backlog_count', 0)}",
    ]
    for v in report.get("execution_queue", [])[:5]:
        lines.append(f"  #{v['number']}: {v['title'][:40]} [{v['action']}]")
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="SCBE Autonomous Issue Lifecycle Pipeline")
    ap.add_argument("--phase", choices=["all", "triage", "council", "execute", "close"], default="all")
    ap.add_argument("--auto-execute", action="store_true", help="Actually create branches and PRs")
    ap.add_argument("--auto-close", action="store_true", help="Actually close stale/resolved issues")
    ap.add_argument("--auto-merge", action="store_true", help="Actually merge passing auto PRs")
    ap.add_argument("--telegram", action="store_true", help="Send Telegram notification")
    ap.add_argument("--dry-run", action="store_true", help="Print what would happen without doing it")
    ap.add_argument("--out-dir", default=str(ARTIFACTS), help="Output directory")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()

    effective_dry_run = args.dry_run or not (args.auto_execute or args.auto_close or args.auto_merge)

    # Phase 1: INGEST
    print("[1/5] Ingesting issues and scan tasks...")
    issues = ingest_github_issues()
    scan_tasks_raw = ingest_scan_tasks()
    print(f"      {len(issues)} GitHub issues, {len(scan_tasks_raw)} scan tasks")

    # Phase 2: TRIAGE
    print("[2/5] Triaging...")
    triaged = [triage_issue(i) for i in issues]
    scan_triaged = [triage_scan_task(t) for t in scan_tasks_raw]
    print(f"      Triaged {len(triaged)} issues + {len(scan_triaged)} scan tasks")

    triage_report = {
        "generated_at": _utc_now(),
        "issues": triaged,
        "scan_tasks": scan_triaged,
    }
    _write_json(out_dir / f"{stamp}-triage.json", triage_report)

    if args.phase == "triage":
        print(f"      Triage report: {out_dir / f'{stamp}-triage.json'}")
        return 0

    # Phase 3: COUNCIL
    print("[3/5] Council review...")
    council = council_review(triaged, scan_triaged)
    _write_json(out_dir / f"{stamp}-council.json", council)

    council_md = format_council_md(council)
    md_path = out_dir / f"{stamp}-council.md"
    md_path.write_text(council_md, encoding="utf-8")
    print(f"      Council report: {md_path}")
    print(f"      Execute: {council['summary']['execute_count']}, "
          f"Close: {council['summary']['close_count']}, "
          f"Backlog: {council['summary']['backlog_count']}")

    if args.phase == "council":
        return 0

    # Phase 4: EXECUTE
    exec_results = []
    if args.phase in ("all", "execute") and council["execution_queue"]:
        print(f"[4/5] Executing {len(council['execution_queue'])} items (dry_run={effective_dry_run})...")
        for v in council["execution_queue"]:
            result = execute_item(v, dry_run=effective_dry_run)
            exec_results.append(result)
            status = result.get("status", "?")
            print(f"      #{v['number']}: {status}")
    else:
        print("[4/5] Execute: skipped (no items or phase filtered)")

    # Phase 5: CLOSE
    close_results = []
    merge_results = []
    if args.phase in ("all", "close"):
        print(f"[5/5] Closing stale issues + merging passing PRs (dry_run={effective_dry_run})...")
        close_results = close_stale_issues(council["close_queue"], dry_run=not args.auto_close)
        merge_results = merge_passing_prs(dry_run=not args.auto_merge)
        print(f"      Closed: {sum(1 for r in close_results if r.get('status') == 'closed')}")
        print(f"      Merged: {sum(1 for r in merge_results if r.get('status') == 'merged')}")
    else:
        print("[5/5] Close: skipped")

    # Final report
    final = {
        "generated_at": _utc_now(),
        "run_id": stamp,
        "triage": triage_report,
        "council": council,
        "execution": exec_results,
        "closes": close_results,
        "merges": merge_results,
    }
    _write_json(out_dir / f"{stamp}-lifecycle.json", final)
    _write_json(out_dir / "latest.json", final)

    # Telegram
    if args.telegram:
        try:
            msg = format_telegram(council)
            _run([sys.executable, str(TELEGRAM_NOTIFY), "--message", msg], timeout=30)
        except Exception:
            pass

    print(f"\nDone. Full report: {out_dir / f'{stamp}-lifecycle.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
