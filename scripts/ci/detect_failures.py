#!/usr/bin/env python3
"""CI Failure Detector — Extracts structured failure info from GitHub Actions.

Usage:
    python scripts/ci/detect_failures.py                  # Check latest failed run
    python scripts/ci/detect_failures.py --run-id 12345   # Check specific run
    python scripts/ci/detect_failures.py --branch main    # Check latest on branch
    python scripts/ci/detect_failures.py --json            # Output as JSON for piping

The output is a structured failure report that can be piped to the auto-fixer.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Known failure patterns mapped to fix strategies ──────────────────────────

FAILURE_PATTERNS = [
    {
        "id": "ts_type_error",
        "pattern": r"error TS\d+:",
        "extract": r"(.+?)\((\d+),(\d+)\): error (TS\d+): (.+)",
        "category": "typescript",
        "fix_strategy": "typecheck_fix",
        "description": "TypeScript type error",
    },
    {
        "id": "py_import_error",
        "pattern": r"(?:ModuleNotFoundError|ImportError): (?:No module named|cannot import name)",
        "extract": r"(?:ModuleNotFoundError|ImportError): (?:No module named '([^']+)'|cannot import name '([^']+)' from '([^']+)')",
        "category": "python",
        "fix_strategy": "import_fix",
        "description": "Python missing module or import",
    },
    {
        "id": "py_collection_error",
        "pattern": r"ERROR collecting tests/",
        "extract": r"ERROR collecting (tests/\S+)",
        "category": "python",
        "fix_strategy": "test_collection_fix",
        "description": "Pytest collection error",
    },
    {
        "id": "black_format",
        "pattern": r"would reformat|Black.*check.*failed",
        "extract": r"would reformat (.+?)$",
        "category": "formatting",
        "fix_strategy": "black_format",
        "description": "Python Black formatting",
    },
    {
        "id": "flake8_lint",
        "pattern": r"[A-Z]\d{3} ",
        "extract": r"(.+?):(\d+):\d+: ([A-Z]\d{3}) (.+)",
        "category": "lint",
        "fix_strategy": "lint_fix",
        "description": "Flake8 lint error",
    },
    {
        "id": "test_failure",
        "pattern": r"FAILED tests/",
        "extract": r"FAILED (tests/\S+)",
        "category": "test",
        "fix_strategy": "test_fix",
        "description": "Test assertion failure",
    },
    {
        "id": "action_not_found",
        "pattern": r"An action could not be found at the URI",
        "extract": r"An action could not be found at the URI '([^']+)'",
        "category": "workflow",
        "fix_strategy": "action_ref_fix",
        "description": "GitHub Action reference broken",
    },
    {
        "id": "npm_audit",
        "pattern": r"npm audit.*found \d+ vulnerabilities",
        "extract": r"found (\d+) vulnerabilities",
        "category": "security",
        "fix_strategy": "npm_audit_fix",
        "description": "npm audit vulnerability",
    },
    {
        "id": "build_error",
        "pattern": r"npm ERR!|Build failed",
        "extract": r"npm ERR! (.+)",
        "category": "build",
        "fix_strategy": "build_fix",
        "description": "Build/compile error",
    },
]


@dataclass
class FailureMatch:
    pattern_id: str
    category: str
    fix_strategy: str
    description: str
    raw_match: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    details: Optional[str] = None


@dataclass
class FailureReport:
    run_id: int
    workflow_name: str
    branch: str
    failing_jobs: list[str] = field(default_factory=list)
    failures: list[FailureMatch] = field(default_factory=list)
    raw_error_lines: list[str] = field(default_factory=list)
    fix_commands: list[str] = field(default_factory=list)


def run_gh(args: list[str]) -> str:
    result = subprocess.run(
        ["gh"] + args, capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace"
    )
    return result.stdout.strip()


def get_latest_failed_run(branch: Optional[str] = None) -> Optional[dict]:
    cmd = ["run", "list", "--limit", "10", "--json", "databaseId,name,conclusion,headBranch"]
    if branch:
        cmd.extend(["--branch", branch])
    output = run_gh(cmd)
    if not output:
        return None
    runs = json.loads(output)
    for r in runs:
        if r["conclusion"] == "failure":
            return r
    return None


def get_failing_jobs(run_id: int) -> list[str]:
    output = run_gh([
        "run", "view", str(run_id), "--json", "jobs",
        "--jq", '.jobs[] | select(.conclusion == "failure") | .name',
    ])
    return [j for j in output.split("\n") if j.strip()]


def get_run_logs(run_id: int) -> str:
    result = subprocess.run(
        ["gh", "run", "view", str(run_id), "--log"],
        capture_output=True, timeout=120,
    )
    # Handle encoding issues on Windows
    try:
        return result.stdout.decode("utf-8", errors="replace")
    except AttributeError:
        return result.stdout or ""


def strip_log_prefix(line: str) -> str:
    """Strip GitHub Actions log prefix (job name, step, timestamp, ##[error])."""
    # Remove "job\tstep\ttimestamp ##[error]" prefix
    if "##[error]" in line:
        line = line.split("##[error]")[-1].strip()
    # Remove "job\tstep\ttimestamp" prefix (tab-separated)
    parts = line.split("\t")
    if len(parts) >= 3:
        line = parts[-1].strip()
    # Remove ISO timestamp prefix
    line = re.sub(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z\s*", "", line)
    return line


def classify_failures(log_text: str) -> list[FailureMatch]:
    matches = []
    seen = set()

    for pattern_def in FAILURE_PATTERNS:
        for raw_line in log_text.split("\n"):
            line = strip_log_prefix(raw_line)
            if re.search(pattern_def["pattern"], line):
                m = re.search(pattern_def["extract"], line)
                if m:
                    key = (pattern_def["id"], m.group(0)[:100])
                    if key in seen:
                        continue
                    seen.add(key)

                    match = FailureMatch(
                        pattern_id=pattern_def["id"],
                        category=pattern_def["category"],
                        fix_strategy=pattern_def["fix_strategy"],
                        description=pattern_def["description"],
                        raw_match=m.group(0)[:200],
                    )

                    # Extract file/line when available
                    groups = m.groups()
                    if pattern_def["id"] == "ts_type_error" and len(groups) >= 2:
                        match.file_path = groups[0]
                        if len(groups) >= 2 and groups[1]:
                            match.line_number = int(groups[1])
                        if len(groups) >= 5:
                            match.details = groups[4][:200]
                    elif pattern_def["id"] in ("py_import_error", "py_collection_error"):
                        match.file_path = groups[0] if groups[0] else None
                        match.details = m.group(0)
                    elif pattern_def["id"] in ("black_format", "flake8_lint"):
                        match.file_path = groups[0]

                    matches.append(match)

    return matches


def generate_fix_commands(failures: list[FailureMatch]) -> list[str]:
    commands = []
    strategies_seen = set()

    for f in failures:
        if f.fix_strategy in strategies_seen:
            continue
        strategies_seen.add(f.fix_strategy)

        if f.fix_strategy == "black_format":
            commands.append("python -m black --target-version py311 --line-length 120 src/ tests/")
        elif f.fix_strategy == "typecheck_fix":
            commands.append(
                f'claude -p "Fix the TypeScript type error in {f.file_path or "the codebase"}: {f.raw_match}. '
                f'Read the file, understand the error, apply minimal fix."'
            )
        elif f.fix_strategy == "import_fix":
            commands.append(
                f'claude -p "Fix the Python import error: {f.raw_match}. '
                f'Add try/except with pytest.importorskip or fix the import path."'
            )
        elif f.fix_strategy == "test_collection_fix":
            commands.append(
                f'claude -p "Fix pytest collection error in {f.file_path}: {f.details or f.raw_match}. '
                f'Add conditional import guards so the test skips gracefully."'
            )
        elif f.fix_strategy == "lint_fix":
            commands.append("python -m flake8 --max-line-length=120 src/ tests/ --select=E,W,F --statistics")
        elif f.fix_strategy == "action_ref_fix":
            commands.append(
                f'claude -p "Fix broken GitHub Action reference: {f.raw_match}. '
                f'Update the action version in .github/workflows/ to a valid ref."'
            )
        elif f.fix_strategy == "test_fix":
            commands.append(
                f'claude -p "Fix failing test {f.file_path}: read the test, understand what changed, fix the assertion."'
            )
        elif f.fix_strategy == "npm_audit_fix":
            commands.append("npm audit fix")
        elif f.fix_strategy == "build_fix":
            commands.append("npm run build 2>&1 | head -30")

    return commands


def detect(run_id: Optional[int] = None, branch: Optional[str] = None) -> Optional[FailureReport]:
    if run_id:
        info_raw = run_gh(["run", "view", str(run_id), "--json", "databaseId,name,headBranch"])
        info = json.loads(info_raw) if info_raw else {}
    else:
        info = get_latest_failed_run(branch)
        if not info:
            return None
        run_id = info["databaseId"]

    report = FailureReport(
        run_id=run_id,
        workflow_name=info.get("name", "unknown"),
        branch=info.get("headBranch", "unknown"),
    )

    report.failing_jobs = get_failing_jobs(run_id)

    logs = get_run_logs(run_id)
    report.failures = classify_failures(logs)

    # Also capture raw error lines for unclassified failures
    for line in logs.split("\n"):
        if "##[error]" in line and len(report.raw_error_lines) < 30:
            clean = line.split("##[error]")[-1].strip()
            if clean and len(clean) > 10:
                report.raw_error_lines.append(clean[:300])

    report.fix_commands = generate_fix_commands(report.failures)

    return report


def main():
    parser = argparse.ArgumentParser(description="Detect CI failures and suggest fixes")
    parser.add_argument("--run-id", type=int, help="Specific run ID to analyze")
    parser.add_argument("--branch", type=str, help="Branch to check (default: latest failed)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--auto-fix", action="store_true", help="Pipe to auto-fixer")
    args = parser.parse_args()

    report = detect(run_id=args.run_id, branch=args.branch)

    if not report:
        print("No failed runs found.")
        sys.exit(0)

    if args.json:
        out = {
            "run_id": report.run_id,
            "workflow": report.workflow_name,
            "branch": report.branch,
            "failing_jobs": report.failing_jobs,
            "failure_count": len(report.failures),
            "failures": [asdict(f) for f in report.failures],
            "raw_errors": report.raw_error_lines[:10],
            "fix_commands": report.fix_commands,
        }
        print(json.dumps(out, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  CI FAILURE REPORT — Run {report.run_id}")
        print(f"{'='*60}")
        print(f"  Workflow: {report.workflow_name}")
        print(f"  Branch:   {report.branch}")
        print(f"  Failed jobs: {', '.join(report.failing_jobs)}")
        print()

        if report.failures:
            print(f"  Classified failures ({len(report.failures)}):")
            for f in report.failures:
                print(f"    [{f.category}] {f.description}")
                if f.file_path:
                    print(f"      File: {f.file_path}:{f.line_number or ''}")
                print(f"      Match: {f.raw_match[:120]}")
                print()
        else:
            print("  No classified failures (check raw errors below)")

        if report.raw_error_lines:
            print(f"  Raw error lines ({len(report.raw_error_lines)}):")
            for line in report.raw_error_lines[:10]:
                print(f"    {line[:120]}")
            print()

        if report.fix_commands:
            print(f"  Suggested fix commands ({len(report.fix_commands)}):")
            for cmd in report.fix_commands:
                print(f"    $ {cmd}")
            print()

    if args.auto_fix:
        print("\n  Auto-fix mode: dispatching to fixer...")
        fix_report_path = f"artifacts/ci/failure_report_{report.run_id}.json"
        subprocess.run(["mkdir", "-p", "artifacts/ci"], capture_output=True)
        with open(fix_report_path, "w") as f:
            json.dump({"run_id": report.run_id, "failures": [asdict(x) for x in report.failures], "fix_commands": report.fix_commands}, f, indent=2)
        print(f"  Report saved to {fix_report_path}")
        # Dispatch to auto_fix.py
        subprocess.run([sys.executable, "scripts/ci/auto_fix.py", "--report", fix_report_path])


if __name__ == "__main__":
    main()
