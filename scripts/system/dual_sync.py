#!/usr/bin/env python3
"""
dual_sync.py -- GitHub <-> GitLab bidirectional mirror sync

Detects which remote is ahead, pulls from the leader, pushes to the follower.
Handles branch protection by optionally creating PRs/MRs when direct push is blocked.

Usage:
    python scripts/system/dual_sync.py --status
    python scripts/system/dual_sync.py --sync
    python scripts/system/dual_sync.py --sync --create-pr-if-blocked
    python scripts/system/dual_sync.py --sync --branch main
    python scripts/system/dual_sync.py --install-hook

Environment:
    GITLAB_TOKEN  -- read from config/connector_oauth/.env.connector.oauth
    GitHub auth   -- uses gh CLI (must be logged in via `gh auth login`)

Remotes:
    origin  = GitHub  (git@github.com:issdandavis/SCBE-AETHERMOORE.git)
    gitlab  = GitLab  (https://...@gitlab.com/issdandavis7795/SCBE-AETHERMOORE.git)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / "config" / "connector_oauth" / ".env.connector.oauth"
GITHUB_REMOTE = "origin"
GITLAB_REMOTE = "gitlab"
GITLAB_PROJECT = "issdandavis7795/SCBE-AETHERMOORE"
GITHUB_REPO = "issdandavis/SCBE-AETHERMOORE"
HOOK_SOURCE = REPO_ROOT / "scripts" / "git-hooks" / "post-push-gitlab.sh"
HOOK_DEST = REPO_ROOT / ".git" / "hooks" / "post-push"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def run(cmd: list[str], *, cwd: Optional[Path] = None, check: bool = True,
        capture: bool = True, timeout: int = 60) -> subprocess.CompletedProcess:
    """Run a subprocess command and return the result."""
    cwd = cwd or REPO_ROOT
    return subprocess.run(
        cmd, cwd=str(cwd), capture_output=capture, text=True,
        check=check, timeout=timeout,
    )


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Shorthand for git commands in the repo root."""
    return run(["git", *args], check=check)


def load_gitlab_token() -> Optional[str]:
    """Load GITLAB_TOKEN from env file or environment."""
    token = os.environ.get("GITLAB_TOKEN")
    if token:
        return token
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key == "GITLAB_TOKEN":
                return val
    return None


def current_branch() -> str:
    """Return the current git branch name."""
    r = git("rev-parse", "--abbrev-ref", "HEAD")
    return r.stdout.strip()


def fetch_all() -> None:
    """Fetch from both remotes."""
    git("fetch", GITHUB_REMOTE, "--prune", check=False)
    git("fetch", GITLAB_REMOTE, "--prune", check=False)


def remote_head(remote: str, branch: str) -> Optional[str]:
    """Get the HEAD commit SHA of a remote branch, or None if it doesn't exist."""
    r = git("rev-parse", f"{remote}/{branch}", check=False)
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def local_head(branch: str) -> Optional[str]:
    """Get the HEAD commit SHA of a local branch."""
    r = git("rev-parse", branch, check=False)
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def commit_count_between(base: str, tip: str) -> int:
    """Count commits from base to tip (tip is ahead by N)."""
    r = git("rev-list", "--count", f"{base}..{tip}", check=False)
    if r.returncode != 0:
        return 0
    return int(r.stdout.strip())


def is_ancestor(ancestor: str, descendant: str) -> bool:
    """Check if ancestor is an ancestor of descendant."""
    r = git("merge-base", "--is-ancestor", ancestor, descendant, check=False)
    return r.returncode == 0


def push_to_remote(remote: str, branch: str) -> tuple[bool, str]:
    """Push branch to remote. Returns (success, message)."""
    r = git("push", remote, branch, check=False)
    output = (r.stdout or "") + (r.stderr or "")
    if r.returncode == 0:
        return True, f"Pushed {branch} to {remote}"
    if "protected branch" in output.lower() or "denied" in output.lower() or "pre-receive hook" in output.lower():
        return False, f"Push to {remote}/{branch} blocked (branch protection)"
    return False, f"Push to {remote}/{branch} failed: {output.strip()}"


# ---------------------------------------------------------------------------
# PR / MR creation
# ---------------------------------------------------------------------------
def create_github_pr(source_branch: str, target_branch: str, title: str) -> Optional[str]:
    """Create a GitHub PR using gh CLI. Returns PR URL or None."""
    r = run(["gh", "pr", "create",
             "--repo", GITHUB_REPO,
             "--head", source_branch,
             "--base", target_branch,
             "--title", title,
             "--body", f"Auto-created by dual_sync.py on {datetime.now(timezone.utc).isoformat()}"],
            check=False)
    if r.returncode == 0:
        return r.stdout.strip()
    print(f"  [WARN] GitHub PR creation failed: {r.stderr.strip()}")
    return None


def create_gitlab_mr(source_branch: str, target_branch: str, title: str) -> Optional[str]:
    """Create a GitLab MR using the API. Returns MR URL or None."""
    token = load_gitlab_token()
    if not token:
        print("  [WARN] No GITLAB_TOKEN found -- cannot create GitLab MR")
        return None
    import urllib.request
    import urllib.error
    project_id = GITLAB_PROJECT.replace("/", "%2F")
    url = f"https://gitlab.com/api/v4/projects/{project_id}/merge_requests"
    data = json.dumps({
        "source_branch": source_branch,
        "target_branch": target_branch,
        "title": title,
        "remove_source_branch": False,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "PRIVATE-TOKEN": token,
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            mr = json.loads(resp.read().decode())
            return mr.get("web_url")
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"  [WARN] GitLab MR creation failed ({e.code}): {body}")
        return None


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------
def get_sync_status(branch: str) -> dict:
    """Compute sync status for a branch across both remotes."""
    fetch_all()

    gh_head = remote_head(GITHUB_REMOTE, branch)
    gl_head = remote_head(GITLAB_REMOTE, branch)
    loc_head = local_head(branch)

    status: dict = {
        "branch": branch,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "github": {"remote": GITHUB_REMOTE, "sha": gh_head},
        "gitlab": {"remote": GITLAB_REMOTE, "sha": gl_head},
        "local": {"sha": loc_head},
        "sync_state": "unknown",
        "ahead_remote": None,
        "behind_remote": None,
        "commits_ahead": 0,
    }

    if gh_head is None and gl_head is None:
        status["sync_state"] = "branch_missing_both"
        return status

    if gh_head is None:
        status["sync_state"] = "github_missing"
        status["ahead_remote"] = GITLAB_REMOTE
        status["behind_remote"] = GITHUB_REMOTE
        return status

    if gl_head is None:
        status["sync_state"] = "gitlab_missing"
        status["ahead_remote"] = GITHUB_REMOTE
        status["behind_remote"] = GITLAB_REMOTE
        return status

    if gh_head == gl_head:
        status["sync_state"] = "in_sync"
        return status

    # Check which is ahead
    if is_ancestor(gl_head, gh_head):
        ahead_count = commit_count_between(gl_head, gh_head)
        status["sync_state"] = "github_ahead"
        status["ahead_remote"] = GITHUB_REMOTE
        status["behind_remote"] = GITLAB_REMOTE
        status["commits_ahead"] = ahead_count
    elif is_ancestor(gh_head, gl_head):
        ahead_count = commit_count_between(gh_head, gl_head)
        status["sync_state"] = "gitlab_ahead"
        status["ahead_remote"] = GITLAB_REMOTE
        status["behind_remote"] = GITHUB_REMOTE
        status["commits_ahead"] = ahead_count
    else:
        status["sync_state"] = "diverged"

    return status


def sync_branch(branch: str, *, create_pr_if_blocked: bool = False) -> dict:
    """Sync a branch between GitHub and GitLab. Returns result dict."""
    status = get_sync_status(branch)
    result = {**status, "actions": [], "prs_created": []}

    if status["sync_state"] == "in_sync":
        result["actions"].append("Already in sync -- nothing to do")
        return result

    if status["sync_state"] == "branch_missing_both":
        result["actions"].append("Branch missing on both remotes -- nothing to sync")
        return result

    if status["sync_state"] == "diverged":
        result["actions"].append("Remotes have diverged -- manual merge required")
        if create_pr_if_blocked:
            result["actions"].append("Creating sync branches for manual resolution")
            sync_branch_name = f"sync/{branch}-dual-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            git("checkout", "-b", sync_branch_name, f"{GITHUB_REMOTE}/{branch}", check=False)
            git("checkout", branch, check=False)
        return result

    ahead = status["ahead_remote"]
    behind = status["behind_remote"]

    # Fast-forward local to the ahead remote
    result["actions"].append(f"Pulling from {ahead}/{branch}")
    git("checkout", branch, check=False)
    r = git("pull", ahead, branch, "--ff-only", check=False)
    if r.returncode != 0:
        result["actions"].append(f"Fast-forward pull from {ahead} failed -- trying merge")
        r = git("pull", ahead, branch, "--no-edit", check=False)
        if r.returncode != 0:
            result["actions"].append("Merge failed -- manual intervention required")
            return result

    # Push to the behind remote
    result["actions"].append(f"Pushing to {behind}/{branch}")
    success, msg = push_to_remote(behind, branch)
    result["actions"].append(msg)

    if not success and create_pr_if_blocked:
        # Create a sync branch and PR/MR
        sync_branch_name = f"sync/{branch}-from-{ahead}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        git("checkout", "-b", sync_branch_name, check=False)
        push_ok, push_msg = push_to_remote(behind, sync_branch_name)
        result["actions"].append(push_msg)

        if push_ok:
            title = f"[dual-sync] Sync {branch} from {ahead}"
            if behind == GITHUB_REMOTE:
                pr_url = create_github_pr(sync_branch_name, branch, title)
                if pr_url:
                    result["prs_created"].append({"platform": "github", "url": pr_url})
            elif behind == GITLAB_REMOTE:
                mr_url = create_gitlab_mr(sync_branch_name, branch, title)
                if mr_url:
                    result["prs_created"].append({"platform": "gitlab", "url": mr_url})

        # Switch back to original branch
        git("checkout", branch, check=False)

    return result


# ---------------------------------------------------------------------------
# Hook installer
# ---------------------------------------------------------------------------
def install_hook() -> None:
    """Install the post-push git hook that mirrors pushes to GitLab."""
    if not HOOK_SOURCE.exists():
        print(f"[ERROR] Hook source not found: {HOOK_SOURCE}")
        sys.exit(1)
    hooks_dir = REPO_ROOT / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Git doesn't have a native post-push hook, but we can install a
    # post-commit hook or advise using the shell alias approach.
    # Instead we install as a reusable script and print instructions.
    dest = hooks_dir / "post-push-gitlab"
    shutil.copy2(str(HOOK_SOURCE), str(dest))
    print(f"[OK] Copied hook to {dest}")
    print()
    print("Git does not have a built-in post-push hook.")
    print("To auto-push to GitLab after every GitHub push, add this alias:")
    print()
    print('  git config alias.pushall \'!f() { git push origin "$@" && bash .git/hooks/post-push-gitlab "$@"; }; f\'')
    print()
    print("Then use:  git pushall main")
    print("Or use:    python scripts/system/dual_sync.py --sync")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="GitHub <-> GitLab bidirectional sync for SCBE-AETHERMOORE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              %(prog)s --status
              %(prog)s --status --branch main
              %(prog)s --sync
              %(prog)s --sync --create-pr-if-blocked
              %(prog)s --sync --branch main --branch dev
              %(prog)s --install-hook
        """),
    )
    parser.add_argument("--status", action="store_true",
                        help="Show sync status (JSON)")
    parser.add_argument("--sync", action="store_true",
                        help="Perform sync")
    parser.add_argument("--create-pr-if-blocked", action="store_true",
                        help="Create PR/MR if direct push is blocked by branch protection")
    parser.add_argument("--branch", action="append", default=None,
                        help="Branch(es) to sync (default: current branch)")
    parser.add_argument("--all-branches", action="store_true",
                        help="Sync all branches that exist on either remote")
    parser.add_argument("--install-hook", action="store_true",
                        help="Install post-push-gitlab hook")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON (default for --status)")

    args = parser.parse_args()

    if not any([args.status, args.sync, args.install_hook]):
        parser.print_help()
        sys.exit(1)

    if args.install_hook:
        install_hook()
        return

    # Determine branches
    if args.all_branches:
        fetch_all()
        r = git("branch", "-r", "--format", "%(refname:short)")
        branches: set[str] = set()
        for line in r.stdout.strip().splitlines():
            line = line.strip()
            if "->" in line:
                continue
            # strip remote prefix
            for remote in (GITHUB_REMOTE, GITLAB_REMOTE):
                if line.startswith(f"{remote}/"):
                    branches.add(line[len(remote) + 1:])
        branch_list = sorted(branches)
    elif args.branch:
        branch_list = args.branch
    else:
        branch_list = [current_branch()]

    results = []

    for branch in branch_list:
        if args.status:
            st = get_sync_status(branch)
            results.append(st)
        elif args.sync:
            res = sync_branch(branch, create_pr_if_blocked=args.create_pr_if_blocked)
            results.append(res)

    # Output
    if args.json or args.status:
        output = results if len(results) > 1 else results[0]
        print(json.dumps(output, indent=2))
    else:
        for res in results:
            branch = res["branch"]
            state = res.get("sync_state", "unknown")
            print(f"\n=== {branch} ===")
            print(f"  State: {state}")
            for action in res.get("actions", []):
                print(f"  -> {action}")
            for pr in res.get("prs_created", []):
                print(f"  PR/MR: {pr['platform']} -> {pr['url']}")
        print()


if __name__ == "__main__":
    main()
