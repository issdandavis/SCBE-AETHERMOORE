#!/usr/bin/env python3
"""CI Auto-Fixer — Takes a failure report and dispatches fixes.

Usage:
    python scripts/ci/auto_fix.py --report artifacts/ci/failure_report_12345.json
    python scripts/ci/auto_fix.py --detect                    # Detect + fix in one shot
    python scripts/ci/auto_fix.py --detect --branch main      # Detect on specific branch
    python scripts/ci/auto_fix.py --detect --dry-run           # Show what would be fixed

This script:
1. Reads a failure report (from detect_failures.py or --detect)
2. Groups failures by fix strategy
3. Applies deterministic fixes (formatting, imports) directly
4. Dispatches complex fixes to Claude Code CLI
5. Creates a fix branch and PR if changes were made
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=300, **kwargs)


def git_has_changes() -> bool:
    result = run(["git", "diff", "--stat"])
    return bool(result.stdout.strip())


def apply_black_format() -> bool:
    """Apply Black formatting — deterministic, no AI needed."""
    print("  [FIX] Running Black formatter...")
    result = run([sys.executable, "-m", "black", "--target-version", "py311", "--line-length", "120", "src/", "tests/"])
    if result.returncode == 0:
        print(f"    Formatted files")
        return git_has_changes()
    else:
        print(f"    Black failed: {result.stderr[:200]}")
        return False


def apply_npm_audit() -> bool:
    """Run npm audit fix — deterministic."""
    print("  [FIX] Running npm audit fix...")
    _result = run(["npm", "audit", "fix"])
    return git_has_changes()


def apply_claude_fix(prompt: str, dry_run: bool = False) -> bool:
    """Dispatch a fix to Claude Code CLI."""
    if dry_run:
        print(f"    [DRY RUN] Would run: claude -p \"{prompt[:100]}...\"")
        return False

    # Check if claude CLI is available
    claude_path = shutil.which("claude")
    if not claude_path:
        print("    Claude CLI not found — skipping AI fix")
        print(f"    Manual fix needed: {prompt[:200]}")
        return False

    print(f"  [AI FIX] Dispatching to Claude Code...")
    print(f"    Prompt: {prompt[:120]}...")

    result = run([claude_path, "-p", prompt], timeout=120)

    if result.returncode == 0:
        print(f"    Claude applied fix")
        return git_has_changes()
    else:
        print(f"    Claude fix failed: {result.stderr[:200]}")
        return False


def apply_fixes(failures: list[dict], fix_commands: list[str], dry_run: bool = False) -> int:
    """Apply fixes based on failure categories. Returns count of fixes applied."""
    fixes_applied = 0
    strategies_done = set()

    for failure in failures:
        strategy = failure.get("fix_strategy", "")
        if strategy in strategies_done:
            continue
        strategies_done.add(strategy)

        print(f"\n  Strategy: {strategy} ({failure.get('description', '')})")

        if strategy == "black_format":
            if apply_black_format():
                fixes_applied += 1

        elif strategy == "npm_audit_fix":
            if apply_npm_audit():
                fixes_applied += 1

        elif strategy in ("typecheck_fix", "import_fix", "test_collection_fix", "test_fix", "action_ref_fix"):
            # Build a targeted prompt for the AI
            prompt = build_ai_prompt(strategy, failure)
            if apply_claude_fix(prompt, dry_run):
                fixes_applied += 1

        elif strategy == "lint_fix":
            print("    Lint fixes are usually formatting — running Black first")
            if apply_black_format():
                fixes_applied += 1

        elif strategy == "build_fix":
            print("    Build errors need manual investigation")
            print(f"    Error: {failure.get('raw_match', 'unknown')[:200]}")

    return fixes_applied


def build_ai_prompt(strategy: str, failure: dict) -> str:
    """Build a targeted prompt for the Claude CLI fixer."""
    file_path = failure.get("file_path", "")
    raw_match = failure.get("raw_match", "")
    details = failure.get("details", "")

    base = f"In the SCBE-AETHERMOORE repo at {REPO_ROOT}, fix the following CI failure:\n\n"

    if strategy == "typecheck_fix":
        return (
            base + f"TypeScript type error in {file_path}: {raw_match}\n\n"
            "Read the file, understand the type mismatch, and apply the minimal fix. "
            "Common fixes: add type assertion, use new Uint8Array() wrapper, add missing type parameter. "
            "Do NOT add any comments or documentation."
        )
    elif strategy == "import_fix":
        return (
            base + f"Python import error: {raw_match}\n\n"
            "Fix by either:\n"
            "1. Adding the missing export to __init__.py\n"
            "2. Wrapping the import in try/except with pytest.importorskip\n"
            "3. Fixing the import path if the module moved\n"
            "Make the minimal change."
        )
    elif strategy == "test_collection_fix":
        return (
            base + f"Pytest collection error in {file_path}: {details or raw_match}\n\n"
            "Fix by adding conditional import guards so the test skips gracefully:\n"
            "try:\n    import module\nexcept ImportError:\n    module = None\n"
            "pytestmark = pytest.mark.skipif(module is None, reason='dep not installed')"
        )
    elif strategy == "test_fix":
        return (
            base + f"Test assertion failure in {file_path}: {raw_match}\n\n"
            "Read the failing test, understand what changed, and fix the assertion. "
            "If the code behavior changed intentionally, update the test expectation. "
            "If it's a bug in the code, fix the code not the test."
        )
    elif strategy == "action_ref_fix":
        return (
            base + f"Broken GitHub Action reference: {raw_match}\n\n"
            "Update the action version in the workflow YAML to use a valid ref. "
            "Prefer @vN tags over commit SHAs. Check the action's latest release."
        )
    else:
        return base + f"Error: {raw_match}\nFile: {file_path}\nDetails: {details}"


def create_fix_branch_and_pr(run_id: int, fixes_applied: int) -> str | None:
    """Create a fix branch, commit changes, and open a PR."""
    branch_name = f"fix/ci-auto-fix-{run_id}"

    # Create and switch to fix branch
    run(["git", "checkout", "-b", branch_name])
    run(["git", "add", "-A"])

    commit_msg = (
        f"fix(ci): auto-fix {fixes_applied} CI failure(s) from run {run_id}\n\n"
        f"Automated fix generated by scripts/ci/auto_fix.py\n\n"
        f"Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
    )
    run(["git", "commit", "-m", commit_msg])
    run(["git", "push", "origin", branch_name])

    # Create PR
    result = run([
        "gh", "pr", "create",
        "--title", f"fix(ci): auto-fix {fixes_applied} failure(s) from run {run_id}",
        "--body", (
            f"## Summary\n"
            f"Automated CI fix for run {run_id}.\n\n"
            f"**Fixes applied**: {fixes_applied}\n\n"
            f"Generated by `scripts/ci/auto_fix.py`\n\n"
            f"🤖 Generated with [Claude Code](https://claude.com/claude-code)"
        ),
        "--base", "main",
    ])

    if result.returncode == 0:
        pr_url = result.stdout.strip()
        print(f"\n  PR created: {pr_url}")
        # Enable auto-merge
        pr_num = pr_url.rstrip("/").split("/")[-1]
        run(["gh", "pr", "merge", pr_num, "--squash", "--auto"])
        return pr_url

    return None


def main():
    parser = argparse.ArgumentParser(description="Auto-fix CI failures")
    parser.add_argument("--report", type=str, help="Path to failure report JSON")
    parser.add_argument("--detect", action="store_true", help="Run detection first")
    parser.add_argument("--branch", type=str, help="Branch to check (with --detect)")
    parser.add_argument("--run-id", type=int, help="Specific run ID (with --detect)")
    parser.add_argument("--dry-run", action="store_true", help="Show fixes without applying")
    parser.add_argument("--no-pr", action="store_true", help="Don't create a PR")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  SCBE CI AUTO-FIXER")
    print(f"  {datetime.now().isoformat()}")
    print(f"{'='*60}")

    if args.detect:
        # Import detect_failures and run detection
        sys.path.insert(0, str(Path(__file__).parent))
        from detect_failures import detect
        report = detect(run_id=args.run_id, branch=args.branch)
        if not report:
            print("  No failed runs found. All clear!")
            sys.exit(0)

        failures = [{"pattern_id": f.pattern_id, "category": f.category,
                      "fix_strategy": f.fix_strategy, "description": f.description,
                      "raw_match": f.raw_match, "file_path": f.file_path,
                      "line_number": f.line_number, "details": f.details}
                     for f in report.failures]
        fix_commands = report.fix_commands
        run_id = report.run_id
    elif args.report:
        with open(args.report) as f:
            data = json.load(f)
        failures = data.get("failures", [])
        fix_commands = data.get("fix_commands", [])
        run_id = data.get("run_id", 0)
    else:
        print("  Error: specify --detect or --report")
        sys.exit(1)

    if not failures:
        print("  No classified failures to fix.")
        if fix_commands:
            print("\n  Suggested manual commands:")
            for cmd in fix_commands:
                print(f"    $ {cmd}")
        sys.exit(0)

    print(f"\n  Found {len(failures)} failure(s) to fix:")
    for f in failures:
        print(f"    [{f.get('category')}] {f.get('description')}: {f.get('raw_match', '')[:80]}")

    if args.dry_run:
        print("\n  [DRY RUN] Would apply these fix strategies:")
        seen = set()
        for f in failures:
            s = f.get("fix_strategy", "")
            if s not in seen:
                seen.add(s)
                print(f"    - {s}: {f.get('description')}")
        sys.exit(0)

    # Apply fixes
    fixes_applied = apply_fixes(failures, fix_commands, dry_run=args.dry_run)

    print(f"\n  Applied {fixes_applied} fix(es)")

    if fixes_applied > 0 and not args.no_pr:
        create_fix_branch_and_pr(run_id, fixes_applied)
    elif fixes_applied == 0:
        print("  No automated fixes could be applied. Manual intervention needed.")
        if fix_commands:
            print("\n  Suggested commands:")
            for cmd in fix_commands:
                print(f"    $ {cmd}")


if __name__ == "__main__":
    main()
