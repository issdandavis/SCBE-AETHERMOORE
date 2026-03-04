#!/usr/bin/env python3
"""
Master publishing script. Runs all platform posting scripts based on available credentials.

Checks which env vars are set for each platform and only runs scripts
where all required credentials are present.

Optional browser fallback:
    If credentials are missing, run Playwright-based posting for supported
    platforms using existing browser session state.

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
    python scripts/publish/post_all.py --browser-fallback --browser-publish --only twitter
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent
BROWSER_FALLBACK_SCRIPT = SCRIPT_DIR / "post_via_browser.py"

# Platform definitions: name, script file, required env vars
PLATFORMS = [
    {
        "name": "Reddit",
        "script": "post_to_reddit.py",
        "env_vars": ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_PASSWORD"],
        "target": "r/aisafety, r/MachineLearning",
        "browser_platform": "reddit",
    },
    {
        "name": "Medium",
        "script": "post_to_medium.py",
        "env_vars": ["MEDIUM_TOKEN"],
        "target": "Draft article",
        "browser_platform": "medium",
    },
    {
        "name": "Twitter/X",
        "script": "post_to_twitter.py",
        "env_vars": ["TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET"],
        "target": "Thread",
        "browser_platform": "x",
    },
    {
        "name": "LinkedIn",
        "script": "post_to_linkedin.py",
        "env_vars": ["LINKEDIN_ACCESS_TOKEN"],
        "target": "Share post",
        "browser_platform": "linkedin",
    },
    {
        "name": "Hacker News",
        "script": "post_to_hackernews.py",
        "env_vars": ["HN_USERNAME", "HN_PASSWORD"],
        "target": "Show HN submission",
        "browser_platform": "hackernews",
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


def run_browser_fallback(platform: dict, args: argparse.Namespace) -> tuple[bool, str]:
    """Run Playwright browser posting fallback. Returns (success, output)."""
    if not BROWSER_FALLBACK_SCRIPT.exists():
        return False, f"Browser fallback script not found: {BROWSER_FALLBACK_SCRIPT}"

    browser_platform = platform.get("browser_platform", "").strip()
    if not browser_platform:
        return False, "No browser fallback mapping defined for this platform."

    cmd = [sys.executable, str(BROWSER_FALLBACK_SCRIPT), "--platform", browser_platform]
    if args.browser_publish:
        cmd.append("--publish")
    if args.browser_headed:
        cmd.append("--headed")

    if args.browser_user_data_dir:
        cmd.extend(["--user-data-dir", args.browser_user_data_dir])
    if args.browser_storage_state:
        cmd.extend(["--storage-state", args.browser_storage_state])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(SCRIPT_DIR.parents[1]),
        )
        output = result.stdout.strip()
        if result.stderr:
            output = f"{output}\nSTDERR:\n{result.stderr.strip()}".strip()

        # Preserve the JSON payload from the fallback script when available.
        if output:
            last_line = output.splitlines()[-1]
            try:
                payload = json.loads(last_line)
                status = payload.get("status", "unknown")
                if status:
                    output = f"{output}\n[post_all] browser_status={status}"
            except json.JSONDecodeError:
                pass

        return result.returncode == 0, output or "No output from browser fallback."
    except subprocess.TimeoutExpired:
        return False, "Browser fallback timed out after 180 seconds."
    except Exception as exc:
        return False, f"Failed to run browser fallback: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish to all configured platforms.")
    parser.add_argument("--dry-run", action="store_true", help="Check credentials without posting.")
    parser.add_argument("--only", type=str, help="Run only the specified platform (case-insensitive).")
    parser.add_argument(
        "--browser-fallback",
        action="store_true",
        help="When API credentials are missing, attempt posting via browser automation.",
    )
    parser.add_argument(
        "--browser-publish",
        action="store_true",
        help="With --browser-fallback, click the final publish button instead of draft-only prep.",
    )
    parser.add_argument(
        "--browser-headed",
        action="store_true",
        help="Run browser fallback in headed mode for interactive debugging.",
    )
    parser.add_argument(
        "--browser-user-data-dir",
        type=str,
        default=os.environ.get("SCBE_BROWSER_USER_DATA_DIR", ""),
        help="Optional persistent browser profile directory for authenticated sessions.",
    )
    parser.add_argument(
        "--browser-storage-state",
        type=str,
        default=os.environ.get("SCBE_BROWSER_STORAGE_STATE", ""),
        help="Optional Playwright storage state file path.",
    )
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
            missing_msg = f"Missing credentials: {', '.join(missing)}"
            print(f"  SKIPPED: {missing_msg}")
            if args.browser_fallback and not args.dry_run:
                print("  Browser fallback: attempting headless posting path...")
                success, output = run_browser_fallback(platform, args)
                for line in output.split("\n"):
                    print(f"  | {line}")

                if success:
                    results.append({"platform": platform["name"], "status": "BROWSER_SUCCESS", "reason": "Posted via browser fallback"})
                else:
                    reason = output.split("\n")[-1] if output else "Browser fallback failed"
                    results.append({"platform": platform["name"], "status": "BROWSER_FAILED", "reason": reason})
                print()
                continue

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
    failed = [r for r in results if r["status"] in {"FAILED", "BROWSER_FAILED"}]
    skipped = [r for r in results if r["status"] == "SKIPPED"]
    dry_run = [r for r in results if r["status"] == "DRY_RUN"]
    browser_success = [r for r in results if r["status"] == "BROWSER_SUCCESS"]

    for r in results:
        status_icon = {
            "SUCCESS": "[OK]",
            "FAILED": "[FAIL]",
            "SKIPPED": "[SKIP]",
            "DRY_RUN": "[DRY]",
            "BROWSER_SUCCESS": "[B-OK]",
            "BROWSER_FAILED": "[B-FAIL]",
        }.get(r["status"], "[??]")

        detail = f"  ({r['reason']})" if r["reason"] else ""
        print(f"  {status_icon} {r['platform']}{detail}")

    print()
    print(
        f"  Posted: {len(succeeded)}  |  Browser posted: {len(browser_success)}  |  "
        f"Failed: {len(failed)}  |  Skipped: {len(skipped)}  |  Dry run: {len(dry_run)}"
    )
    print("=" * 60)

    # Return 0 if nothing failed (skips are OK)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
