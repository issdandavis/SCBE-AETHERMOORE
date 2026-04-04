#!/usr/bin/env python3
"""Code Scanning Review — Dashboard for GitHub CodeQL alerts.

Usage:
    python scripts/ci/review_code_scanning.py              # Full report
    python scripts/ci/review_code_scanning.py --summary     # One-line summary
    python scripts/ci/review_code_scanning.py --by-rule     # Group by rule
    python scripts/ci/review_code_scanning.py --by-file     # Group by file
    python scripts/ci/review_code_scanning.py --stale       # Find alerts for deleted files
    python scripts/ci/review_code_scanning.py --fixable     # Show only auto-fixable
    python scripts/ci/review_code_scanning.py --json        # JSON output for piping
    python scripts/ci/review_code_scanning.py --verify      # Check if fixes landed in code

This is a READ-ONLY review tool. It does not modify any files.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Rules that can be fixed automatically (deterministic or simple AI fix)
AUTO_FIXABLE_RULES = {
    "py/unused-import": "Remove the unused import line",
    "py/unused-local-variable": "Remove or prefix with underscore",
    "py/unused-global-variable": "Remove the unused variable",
    "py/empty-except": "Add 'except Exception:' and a comment",
    "py/catch-base-exception": "Change 'except BaseException' to 'except Exception'",
    "py/unnecessary-pass": "Remove the pass statement",
    "py/unnecessary-lambda": "Replace lambda with direct callable reference",
    "py/unreachable-statement": "Remove unreachable code after return/raise/break",
    "py/multiple-definition": "Remove the redundant assignment",
    "js/unused-local-variable": "Remove the unused import/variable",
    "py/ineffectual-statement": "Remove or convert to assignment",
    "py/mixed-returns": "Add explicit return None",
}

# Rules that need human judgment
REVIEW_RULES = {
    "py/cyclic-import": "Refactor to break the import cycle",
    "py/file-not-closed": "Use 'with' context manager",
    "py/implicit-string-concatenation-in-list": "Add comma between strings or join them",
    "py/uninitialized-local-variable": "Ensure variable is assigned before use",
    "py/non-iterable-in-for-loop": "Check the type of the iterable",
    "py/pythagorean": "Use math.hypot() instead of manual sqrt(a²+b²)",
}


@dataclass
class Alert:
    number: int
    state: str
    rule_id: str
    severity: str
    file_path: str
    line: int
    message: str
    dismissed_reason: str = ""


@dataclass
class ReviewReport:
    total_open: int = 0
    total_dismissed: int = 0
    total_fixed: int = 0
    by_rule: dict = field(default_factory=lambda: defaultdict(list))
    by_file: dict = field(default_factory=lambda: defaultdict(list))
    by_severity: dict = field(default_factory=Counter)
    auto_fixable: list = field(default_factory=list)
    needs_review: list = field(default_factory=list)
    stale: list = field(default_factory=list)
    already_fixed: list = field(default_factory=list)


def fetch_alerts(state: str = "open") -> list[Alert]:
    """Fetch all code scanning alerts from GitHub API."""
    alerts = []
    page = 1
    while True:
        result = subprocess.run(
            ["gh", "api", f"repos/issdandavis/SCBE-AETHERMOORE/code-scanning/alerts?state={state}&per_page=100&page={page}"],
            capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            break
        data = json.loads(result.stdout)
        if not data:
            break
        for d in data:
            loc = d.get("most_recent_instance", {}).get("location", {})
            alerts.append(Alert(
                number=d["number"],
                state=d["state"],
                rule_id=d["rule"]["id"],
                severity=d.get("rule", {}).get("security_severity_level") or "none",
                file_path=loc.get("path", "unknown"),
                line=loc.get("start_line", 0),
                message=d.get("most_recent_instance", {}).get("message", {}).get("text", "")[:150],
                dismissed_reason=d.get("dismissed_reason", "") or "",
            ))
        page += 1
    return alerts


def file_exists(path: str) -> bool:
    """Check if a file exists in the repo."""
    return (REPO_ROOT / path).exists()


def check_if_fixed(alert: Alert) -> bool:
    """Check if the alert's code pattern still exists in the file."""
    fpath = REPO_ROOT / alert.file_path
    if not fpath.exists():
        return True  # File deleted = fixed

    try:
        lines = fpath.read_text(encoding="utf-8", errors="replace").split("\n")
    except Exception:
        return False

    if alert.line <= 0 or alert.line > len(lines):
        return False

    line_content = lines[alert.line - 1]

    # Rule-specific checks
    if alert.rule_id == "py/unused-import":
        # Check if the import is still there
        import_name = ""
        if "Import of '" in alert.message:
            import_name = alert.message.split("Import of '")[1].split("'")[0]
        return import_name and import_name not in line_content

    if alert.rule_id == "py/catch-base-exception":
        return "BaseException" not in line_content

    if alert.rule_id == "py/empty-except":
        # Check nearby lines for bare except with only pass
        region = "\n".join(lines[max(0, alert.line - 3):alert.line + 3])
        return "except:" not in region or "# " in region

    if alert.rule_id == "py/unused-global-variable":
        var_name = ""
        if "variable '" in alert.message:
            var_name = alert.message.split("variable '")[1].split("'")[0]
        return var_name and var_name not in line_content

    return False


def build_report(alerts: list[Alert], verify: bool = False) -> ReviewReport:
    """Build a structured review report."""
    report = ReviewReport()

    for a in alerts:
        if a.state == "open":
            report.total_open += 1
        elif a.state == "dismissed":
            report.total_dismissed += 1
        elif a.state == "fixed":
            report.total_fixed += 1

        if a.state != "open":
            continue

        report.by_rule[a.rule_id].append(a)
        report.by_file[a.file_path].append(a)
        report.by_severity[a.severity] += 1

        if a.rule_id in AUTO_FIXABLE_RULES:
            report.auto_fixable.append(a)
        elif a.rule_id in REVIEW_RULES:
            report.needs_review.append(a)

        if not file_exists(a.file_path):
            report.stale.append(a)

        if verify and check_if_fixed(a):
            report.already_fixed.append(a)

    return report


def print_summary(report: ReviewReport):
    print(f"CodeQL: {report.total_open} open | {len(report.auto_fixable)} auto-fixable | {len(report.needs_review)} needs review | {len(report.stale)} stale")
    if report.already_fixed:
        print(f"  ({len(report.already_fixed)} already fixed in code, waiting for re-scan)")


def print_full_report(report: ReviewReport):
    print(f"\n{'='*70}")
    print(f"  CODE SCANNING REVIEW — {report.total_open} Open Alerts")
    print(f"{'='*70}")

    print(f"\n  Severity breakdown:")
    for sev in ["critical", "high", "medium", "low", "none"]:
        count = report.by_severity.get(sev, 0)
        if count:
            bar = "#" * min(count, 40)
            print(f"    {sev:<10} {count:>3}  {bar}")

    print(f"\n  By rule ({len(report.by_rule)} distinct rules):")
    for rule, alerts in sorted(report.by_rule.items(), key=lambda x: -len(x[1])):
        fixable = " [auto-fixable]" if rule in AUTO_FIXABLE_RULES else ""
        review = " [needs review]" if rule in REVIEW_RULES else ""
        fix_hint = AUTO_FIXABLE_RULES.get(rule, REVIEW_RULES.get(rule, ""))
        print(f"    {rule:<45} {len(alerts):>3}{fixable}{review}")
        if fix_hint:
            print(f"      Fix: {fix_hint}")

    print(f"\n  Top files by alert count:")
    for fpath, alerts in sorted(report.by_file.items(), key=lambda x: -len(x[1]))[:15]:
        exists = "  " if file_exists(fpath) else " [DELETED]"
        print(f"    {len(alerts):>3}  {fpath}{exists}")

    if report.stale:
        print(f"\n  Stale alerts ({len(report.stale)} — file no longer exists):")
        for a in report.stale:
            print(f"    #{a.number} {a.rule_id} {a.file_path}")

    if report.already_fixed:
        print(f"\n  Already fixed in code ({len(report.already_fixed)} — waiting for CodeQL re-scan):")
        for a in report.already_fixed:
            print(f"    #{a.number} {a.rule_id} {a.file_path}:{a.line}")

    # Actionable summary
    print(f"\n{'='*70}")
    print(f"  ACTION ITEMS")
    print(f"{'='*70}")
    print(f"  Auto-fixable:  {len(report.auto_fixable):>3} (can be fixed by scripts/CI)")
    print(f"  Needs review:  {len(report.needs_review):>3} (human judgment needed)")
    print(f"  Stale:         {len(report.stale):>3} (dismiss — file deleted)")
    if report.already_fixed:
        print(f"  Already fixed: {len(report.already_fixed):>3} (will clear on next CodeQL scan)")
    print()


def print_by_rule(report: ReviewReport):
    for rule, alerts in sorted(report.by_rule.items(), key=lambda x: -len(x[1])):
        fixable = " [AUTO-FIXABLE]" if rule in AUTO_FIXABLE_RULES else ""
        print(f"\n  {rule} ({len(alerts)}){fixable}")
        for a in alerts[:10]:
            print(f"    #{a.number} {a.file_path}:{a.line} — {a.message[:80]}")
        if len(alerts) > 10:
            print(f"    ... and {len(alerts) - 10} more")


def print_by_file(report: ReviewReport):
    for fpath, alerts in sorted(report.by_file.items(), key=lambda x: -len(x[1])):
        exists = "" if file_exists(fpath) else " [DELETED]"
        print(f"\n  {fpath}{exists} ({len(alerts)} alerts)")
        for a in alerts:
            print(f"    L{a.line:>5} {a.rule_id}: {a.message[:80]}")


def main():
    parser = argparse.ArgumentParser(description="Review GitHub CodeQL code scanning alerts")
    parser.add_argument("--summary", action="store_true", help="One-line summary")
    parser.add_argument("--by-rule", action="store_true", help="Group by rule")
    parser.add_argument("--by-file", action="store_true", help="Group by file")
    parser.add_argument("--stale", action="store_true", help="Show only stale alerts")
    parser.add_argument("--fixable", action="store_true", help="Show only auto-fixable")
    parser.add_argument("--verify", action="store_true", help="Check if fixes landed in code")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    print("Fetching alerts from GitHub...", file=sys.stderr)
    alerts = fetch_alerts("open")
    report = build_report(alerts, verify=args.verify)

    if args.json:
        out = {
            "total_open": report.total_open,
            "auto_fixable": len(report.auto_fixable),
            "needs_review": len(report.needs_review),
            "stale": len(report.stale),
            "already_fixed": len(report.already_fixed) if args.verify else None,
            "by_rule": {rule: len(alerts) for rule, alerts in report.by_rule.items()},
            "by_severity": dict(report.by_severity),
            "top_files": {f: len(a) for f, a in sorted(report.by_file.items(), key=lambda x: -len(x[1]))[:10]},
        }
        print(json.dumps(out, indent=2))
    elif args.summary:
        print_summary(report)
    elif args.by_rule:
        print_by_rule(report)
    elif args.by_file:
        print_by_file(report)
    elif args.stale:
        if report.stale:
            print(f"Stale alerts ({len(report.stale)}):")
            for a in report.stale:
                print(f"  #{a.number} {a.rule_id} {a.file_path}:{a.line}")
        else:
            print("No stale alerts.")
    elif args.fixable:
        print(f"Auto-fixable alerts ({len(report.auto_fixable)}):")
        for a in report.auto_fixable:
            fix = AUTO_FIXABLE_RULES.get(a.rule_id, "")
            print(f"  #{a.number} {a.rule_id} {a.file_path}:{a.line}")
            print(f"    {a.message[:100]}")
            print(f"    Fix: {fix}")
    else:
        print_full_report(report)


if __name__ == "__main__":
    main()
