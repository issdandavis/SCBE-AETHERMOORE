#!/usr/bin/env python3
"""GitHub Inbox Cleaner — automated notification triage with training data generation.

Classifies every GitHub notification, takes the appropriate action (mark read,
close stale PR, merge dependabot, etc.), and logs every decision as an SFT
training pair so the AI learns operations triage.

Usage:
    python scripts/github_inbox_cleaner.py              # Dry run (default)
    python scripts/github_inbox_cleaner.py --execute     # Actually clear inbox
    python scripts/github_inbox_cleaner.py --report      # Summary only
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from ops_training_logger import OpsLogger

STALE_DAYS = 7
VERY_STALE_DAYS = 14
MAX_API_CALLS_PER_MINUTE = 20


def gh(*args: str, input_data: str = "") -> tuple[int, str]:
    """Run a gh CLI command, return (exit_code, stdout)."""
    cmd = ["gh"] + list(args)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            input=input_data or None,
            env=_clean_env(),
        )
        return result.returncode, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return 1, "timeout"


def _clean_env():
    """Return env without stale GH_TOKEN/GITHUB_TOKEN."""
    import os
    env = os.environ.copy()
    env.pop("GH_TOKEN", None)
    env.pop("GITHUB_TOKEN", None)
    return env


def fetch_notifications() -> list[dict]:
    """Fetch all GitHub notifications."""
    code, out = gh("api", "notifications", "--paginate")
    if code != 0:
        print(f"ERROR: Could not fetch notifications: {out}")
        return []
    return json.loads(out) if out else []


def classify_notification(notif: dict) -> dict:
    """Classify a notification and decide on action.

    Returns a dict with:
        category: str (dependabot|ci_fix|security|stale_pr|review_request|issue|info)
        action: str (mark_read|close|merge|review|skip)
        reason: str (human-readable reason for the action)
        priority: int (1=critical, 2=important, 3=routine, 4=noise)
    """
    reason = notif.get("reason", "")
    subject = notif.get("subject", {})
    title = subject.get("title", "")
    stype = subject.get("type", "")
    repo = notif.get("repository", {}).get("full_name", "")
    updated = notif.get("updated_at", "")

    now = datetime.now(timezone.utc)
    try:
        updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        age_days = (now - updated_dt).days
    except (ValueError, AttributeError):
        age_days = 0

    title_lower = title.lower()

    # Security alerts
    if stype == "RepositoryDependabotAlertsThread" or reason == "security_alert":
        return {
            "category": "security",
            "action": "review",
            "reason": f"Security alert: {title}",
            "priority": 1,
        }

    # Dependabot PRs
    if "dependabot" in title_lower or "bump" in title_lower or "chore(deps" in title_lower:
        if "review_requested" in reason:
            return {
                "category": "dependabot",
                "action": "review",
                "reason": f"Dependabot PR needs review: {title}",
                "priority": 2,
            }
        if age_days > STALE_DAYS:
            return {
                "category": "dependabot",
                "action": "mark_read",
                "reason": f"Stale dependabot notification ({age_days}d old): {title}",
                "priority": 4,
            }
        return {
            "category": "dependabot",
            "action": "mark_read",
            "reason": f"Dependabot update: {title}",
            "priority": 3,
        }

    # CI fix PRs (authored by us, already merged or old)
    if stype == "PullRequest" and any(k in title_lower for k in ["fix(ci)", "fix(lint)", "fix(test"]):
        if reason == "state_change":
            return {
                "category": "ci_fix",
                "action": "mark_read",
                "reason": f"CI fix PR state changed: {title}",
                "priority": 4,
            }
        if age_days > STALE_DAYS:
            return {
                "category": "ci_fix",
                "action": "mark_read",
                "reason": f"Old CI fix notification ({age_days}d): {title}",
                "priority": 4,
            }
        return {
            "category": "ci_fix",
            "action": "mark_read",
            "reason": f"CI fix PR: {title}",
            "priority": 3,
        }

    # Security fix PRs
    if stype == "PullRequest" and "fix(security)" in title_lower:
        if age_days > STALE_DAYS:
            return {
                "category": "security_pr",
                "action": "mark_read",
                "reason": f"Old security fix notification ({age_days}d): {title}",
                "priority": 3,
            }
        return {
            "category": "security_pr",
            "action": "review",
            "reason": f"Security fix PR needs review: {title}",
            "priority": 2,
        }

    # Self-created issues (automated)
    if stype == "Issue" and reason in ("author", "subscribed"):
        if "self-improvement" in title_lower or "daily review" in title_lower:
            return {
                "category": "automated_issue",
                "action": "mark_read",
                "reason": f"Automated issue: {title}",
                "priority": 4,
            }
        return {
            "category": "issue",
            "action": "review",
            "reason": f"Issue: {title}",
            "priority": 2,
        }

    # Review requested
    if reason == "review_requested":
        return {
            "category": "review_request",
            "action": "review",
            "reason": f"Review requested: {title}",
            "priority": 2,
        }

    # State changes on our own PRs (merged/closed)
    if reason == "state_change":
        return {
            "category": "state_change",
            "action": "mark_read",
            "reason": f"PR state changed: {title}",
            "priority": 4,
        }

    # Very old notifications
    if age_days > VERY_STALE_DAYS:
        return {
            "category": "stale",
            "action": "mark_read",
            "reason": f"Very stale notification ({age_days}d): {title}",
            "priority": 4,
        }

    # Old authored PRs
    if stype == "PullRequest" and reason == "author" and age_days > STALE_DAYS:
        return {
            "category": "old_pr",
            "action": "mark_read",
            "reason": f"Old PR notification ({age_days}d): {title}",
            "priority": 3,
        }

    # Default: mark as read
    return {
        "category": "info",
        "action": "mark_read",
        "reason": f"{stype} ({reason}): {title}",
        "priority": 3,
    }


def mark_notification_read(thread_id: str) -> bool:
    """Mark a notification thread as read."""
    code, _ = gh("api", "-X", "PATCH", f"notifications/threads/{thread_id}")
    return code == 0


def run_cleanup(execute: bool = False, report_only: bool = False) -> dict:
    """Run the full inbox cleanup."""
    logger = OpsLogger()
    start_time = time.time()

    notifications = fetch_notifications()
    if not notifications:
        print("Inbox is clean. 0 notifications.")
        return {"total": 0, "actions": []}

    # Classify all
    classified = []
    for notif in notifications:
        info = classify_notification(notif)
        info["id"] = notif["id"]
        info["title"] = notif["subject"]["title"]
        info["repo"] = notif.get("repository", {}).get("full_name", "")
        info["type"] = notif["subject"]["type"]
        info["updated"] = notif.get("updated_at", "")
        classified.append(info)

    # Sort by priority
    classified.sort(key=lambda x: x["priority"])

    # Summary
    categories = {}
    for c in classified:
        cat = c["category"]
        categories[cat] = categories.get(cat, 0) + 1

    actions_summary = {}
    for c in classified:
        act = c["action"]
        actions_summary[act] = actions_summary.get(act, 0) + 1

    print(f"\n{'='*60}")
    print(f"  GitHub Inbox Cleanup Report")
    print(f"  {len(notifications)} notifications found")
    print(f"{'='*60}")
    print(f"\nBy category:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat:20s} {count:3d}")
    print(f"\nBy action:")
    for act, count in sorted(actions_summary.items(), key=lambda x: -x[1]):
        print(f"  {act:20s} {count:3d}")

    if report_only:
        print("\n[Report only — no actions taken]")
        return {"total": len(notifications), "categories": categories, "actions_summary": actions_summary}

    # Priority breakdown
    print(f"\nPriority breakdown:")
    for p in [1, 2, 3, 4]:
        items = [c for c in classified if c["priority"] == p]
        labels = {1: "CRITICAL", 2: "IMPORTANT", 3: "ROUTINE", 4: "NOISE"}
        if items:
            print(f"\n  [{labels[p]}] ({len(items)} items)")
            for item in items[:5]:
                marker = "*" if item["action"] == "review" else "-"
                print(f"    {marker} {item['reason'][:70]}")
            if len(items) > 5:
                print(f"    ... and {len(items) - 5} more")

    # Execute actions
    cleared = 0
    reviewed = 0
    skipped = 0
    api_calls = 0

    if execute:
        print(f"\n{'='*60}")
        print("  Executing cleanup actions...")
        print(f"{'='*60}")

        for c in classified:
            if c["action"] == "mark_read":
                if api_calls >= MAX_API_CALLS_PER_MINUTE:
                    print("  Rate limit pause (3s)...")
                    time.sleep(3)
                    api_calls = 0

                success = mark_notification_read(c["id"])
                if success:
                    cleared += 1
                    api_calls += 1
                    print(f"  [CLEARED] {c['reason'][:60]}")
                else:
                    skipped += 1
                    print(f"  [FAILED] {c['reason'][:60]}")

            elif c["action"] == "review":
                reviewed += 1
                print(f"  [NEEDS REVIEW] {c['reason'][:60]}")

            elif c["action"] == "skip":
                skipped += 1
    else:
        print(f"\n[DRY RUN — pass --execute to clear inbox]")
        for c in classified:
            if c["action"] == "mark_read":
                cleared += 1
            elif c["action"] == "review":
                reviewed += 1
            else:
                skipped += 1

    elapsed = time.time() - start_time

    # Log as training data
    logger.log_action(
        action="github_inbox_cleanup",
        what=f"Processed {len(notifications)} notifications: {cleared} cleared, {reviewed} need review, {skipped} skipped",
        why="Automated inbox triage to maintain operational hygiene and reduce notification noise",
        how="python scripts/github_inbox_cleaner.py" + (" --execute" if execute else ""),
        access_path="GitHub notifications API -> classify -> mark_read/review/skip",
        time_taken_seconds=elapsed,
        optimal_time_seconds=min(elapsed, 30),
        outcome="success" if execute else "dry_run",
        could_be_better="Run on schedule (daily cron) with auto-merge for trusted dependabot patches",
        category="github_ops",
        tongue="CA",
    )

    # Log category breakdowns as individual training pairs
    for cat, count in categories.items():
        logger.log_action(
            action=f"triage_{cat}_notifications",
            what=f"Classified {count} {cat} notifications",
            why=f"Notification triage: {cat} category handling",
            how=f"Pattern matching on subject.type, reason, title keywords, age",
            category="github_ops",
            tongue="CA",
        )

    result = {
        "total": len(notifications),
        "cleared": cleared,
        "reviewed": reviewed,
        "skipped": skipped,
        "categories": categories,
        "actions_summary": actions_summary,
        "elapsed_seconds": elapsed,
        "mode": "execute" if execute else "dry_run",
    }

    print(f"\n{'='*60}")
    print(f"  Done in {elapsed:.1f}s")
    print(f"  Cleared: {cleared} | Needs review: {reviewed} | Skipped: {skipped}")
    if not execute:
        print(f"  Training pairs logged: {len(categories) + 1}")
    print(f"{'='*60}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub Inbox Cleaner with training data")
    parser.add_argument("--execute", action="store_true", help="Actually clear notifications")
    parser.add_argument("--report", action="store_true", help="Report only, no actions")
    args = parser.parse_args()

    run_cleanup(execute=args.execute, report_only=args.report)
