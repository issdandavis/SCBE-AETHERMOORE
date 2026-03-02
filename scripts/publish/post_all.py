#!/usr/bin/env python3
"""
Master publishing script. Runs all platform posting scripts based on available credentials.

Checks which env vars are set for each platform and only runs scripts
where all required credentials are present.

Required env vars by platform:
    Reddit:     REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD
    Medium:     MEDIUM_TOKEN
    Twitter/X:  TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
    LinkedIn:   LINKEDIN_ACCESS_TOKEN
    HackerNews: HN_USERNAME, HN_PASSWORD

Usage:
    python scripts/publish/post_all.py
    python scripts/publish/post_all.py --dry-run      # Check credentials without posting
    python scripts/publish/post_all.py --only reddit   # Run only one platform
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent

# Platform definitions: name, script file, required env vars
PLATFORMS = [
    {
        "name": "Reddit",
        "script": "post_to_reddit.py",
        "env_vars": ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_PASSWORD"],
        "target": "r/aisafety, r/MachineLearning",
    },
    {
        "name": "Medium",
        "script": "post_to_medium.py",
        "env_vars": ["MEDIUM_TOKEN"],
        "target": "Draft article",
    },
    {
        "name": "Twitter/X",
        "script": "post_to_twitter.py",
        "env_vars": ["TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET"],
        "target": "Thread",
    },
    {
        "name": "LinkedIn",
        "script": "post_to_linkedin.py",
        "env_vars": ["LINKEDIN_ACCESS_TOKEN"],
        "target": "Share post",
    },
    {
        "name": "Hacker News",
        "script": "post_to_hackernews.py",
        "env_vars": ["HN_USERNAME", "HN_PASSWORD"],
        "target": "Show HN submission",
    },
]


def check_credentials(platform: dict) -> tuple[bool, list[str]]:
    """Check if all required env vars are set. Returns (all_present, missing_list)."""
    missing = [var for var in platform["env_vars"] if not os.environ.get(var)]
    return len(missing) == 0, missing


def run_script(platform: dict) -> tuple[bool, str]:
    """Run a platform posting script. Returns (success, output)."""
    script_path = SCRIPT_DIR / platform["script"]

    if not script_path.exists():
        return False, f"Script not found: {script_path}"

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(SCRIPT_DIR.parents[1]),  # Run from repo root
        )

        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"

        return result.returncode == 0, output.strip()

    except subprocess.TimeoutExpired:
        return False, "Script timed out after 120 seconds."
    except Exception as exc:
        return False, f"Failed to run script: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish to all configured platforms.")
    parser.add_argument("--dry-run", action="store_true", help="Check credentials without posting.")
    parser.add_argument("--only", type=str, help="Run only the specified platform (case-insensitive).")
    args = parser.parse_args()

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print("=" * 60)
    print(f"  SCBE-AetherMoore Multi-Platform Publisher")
    print(f"  {timestamp}")
    if args.dry_run:
        print(f"  MODE: DRY RUN (credential check only)")
    print("=" * 60)
    print()

    # Filter platforms if --only is specified
    platforms = PLATFORMS
    if args.only:
        target = args.only.lower()
        platforms = [p for p in PLATFORMS if target in p["name"].lower()]
        if not platforms:
            print(f"ERROR: No platform matching '{args.only}'. Available: {', '.join(p['name'] for p in PLATFORMS)}")
            return 1

    results = []

    for platform in platforms:
        print(f"--- {platform['name']} ({platform['target']}) ---")

        creds_ok, missing = check_credentials(platform)

        if not creds_ok:
            print(f"  SKIPPED: Missing credentials: {', '.join(missing)}")
            results.append({"platform": platform["name"], "status": "SKIPPED", "reason": f"Missing: {', '.join(missing)}"})
            print()
            continue

        print(f"  Credentials: OK ({len(platform['env_vars'])} env vars set)")

        if args.dry_run:
            print(f"  DRY RUN: Would post to {platform['target']}")
            results.append({"platform": platform["name"], "status": "DRY_RUN", "reason": "Credentials verified"})
            print()
            continue

        print(f"  Posting...")
        success, output = run_script(platform)

        # Indent and print the script output
        for line in output.split("\n"):
            print(f"  | {line}")

        if success:
            results.append({"platform": platform["name"], "status": "SUCCESS", "reason": ""})
        else:
            results.append({"platform": platform["name"], "status": "FAILED", "reason": output.split("\n")[-1] if output else "Unknown error"})

        print()

    # --- Summary ---
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)

    succeeded = [r for r in results if r["status"] == "SUCCESS"]
    failed = [r for r in results if r["status"] == "FAILED"]
    skipped = [r for r in results if r["status"] == "SKIPPED"]
    dry_run = [r for r in results if r["status"] == "DRY_RUN"]

    for r in results:
        status_icon = {
            "SUCCESS": "[OK]",
            "FAILED": "[FAIL]",
            "SKIPPED": "[SKIP]",
            "DRY_RUN": "[DRY]",
        }.get(r["status"], "[??]")

        detail = f"  ({r['reason']})" if r["reason"] else ""
        print(f"  {status_icon} {r['platform']}{detail}")

    print()
    print(f"  Posted: {len(succeeded)}  |  Failed: {len(failed)}  |  Skipped: {len(skipped)}  |  Dry run: {len(dry_run)}")
    print("=" * 60)

    # Return 0 if nothing failed (skips are OK)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
