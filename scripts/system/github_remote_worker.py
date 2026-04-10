#!/usr/bin/env python3
"""Dispatch and monitor free remote jobs on GitHub Actions."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
WORKFLOW_NAME = "free-remote-worker.yml"
DEFAULT_REPO = os.environ.get("SCBE_GITHUB_REMOTE_REPO", "issdandavis/SCBE-AETHERMOORE")


def _run(cmd: list[str], *, capture: bool = False, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        check=False,
        text=True,
        encoding="utf-8",
        capture_output=capture,
    )


def _must(cmd: list[str], *, cwd: Path = REPO_ROOT) -> str:
    proc = _run(cmd, capture=True, cwd=cwd)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "command failed")
    return proc.stdout.strip()


def _repo_name(repo: str) -> str:
    return _must(["gh", "repo", "view", repo, "--json", "nameWithOwner", "--jq", ".nameWithOwner"])


def _default_branch(repo: str) -> str:
    return _must(["gh", "repo", "view", repo, "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name"])


def _dispatch(args: argparse.Namespace) -> int:
    branch = args.ref or _default_branch(args.repo)
    gh_cmd = [
        "gh",
        "workflow",
        "run",
        "-R",
        args.repo,
        WORKFLOW_NAME,
        "--ref",
        branch,
        "-f",
        f"task_label={args.task_label}",
        "-f",
        f"command={args.command}",
        "-f",
        f"python_version={args.python_version}",
        "-f",
        f"install_mode={args.install_mode}",
        "-f",
        f"working_directory={args.working_directory}",
        "-f",
        f"artifact_glob={args.artifact_glob}",
    ]

    if args.dry_run:
        print("Dispatch command:")
        print(" ".join(shlex.quote(part) for part in gh_cmd))
        return 0

    proc = _run(gh_cmd)
    if proc.returncode != 0:
        return proc.returncode

    print(f"Dispatched {WORKFLOW_NAME} on branch {branch}")
    if args.watch:
        return _watch(args.repo, branch=branch, poll_seconds=args.poll_seconds)
    return 0


def _latest_run(repo: str, branch: str | None = None) -> dict[str, Any]:
    cmd = [
        "gh",
        "run",
        "list",
        "-R",
        repo,
        "--workflow",
        WORKFLOW_NAME,
        "--limit",
        "1",
        "--json",
        "databaseId,status,conclusion,url,displayTitle,headBranch,createdAt",
    ]
    if branch:
        cmd.extend(["--branch", branch])
    payload = _must(cmd)
    runs = json.loads(payload)
    if not runs:
        raise RuntimeError("No runs found for workflow")
    return runs[0]


def _watch(repo: str, branch: str | None = None, *, poll_seconds: int = 10) -> int:
    run = _latest_run(repo, branch)
    run_id = str(run["databaseId"])
    print(f"Watching run {run_id}: {run['url']}")
    watch_proc = _run(["gh", "run", "watch", "-R", repo, run_id, "--interval", str(poll_seconds)])
    refreshed = _latest_run(repo, branch)
    conclusion = refreshed.get("conclusion") or "unknown"
    print(f"Final conclusion: {conclusion}")
    return 0 if conclusion == "success" and watch_proc.returncode == 0 else 1


def _status(args: argparse.Namespace) -> int:
    run = _latest_run(args.repo, args.branch)
    print(json.dumps(run, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dispatch work to the free GitHub Actions remote worker")
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    dispatch = subparsers.add_parser("dispatch", help="Trigger a remote job")
    dispatch.add_argument("command", help="Bash command to run on the remote worker")
    dispatch.add_argument("--repo", default=DEFAULT_REPO, help="GitHub repository in owner/name form")
    dispatch.add_argument("--task-label", default="manual-remote-job", help="Short label for the remote task")
    dispatch.add_argument("--python-version", default="3.11", help="Python version for the worker")
    dispatch.add_argument(
        "--install-mode",
        default="auto",
        choices=("auto", "editable", "requirements", "none"),
        help="Dependency bootstrap strategy",
    )
    dispatch.add_argument("--working-directory", default=".", help="Working directory relative to repo root")
    dispatch.add_argument("--artifact-glob", default="", help="Additional files or globs to upload")
    dispatch.add_argument("--ref", help="Git ref or branch to run the workflow on; defaults to the remote repo default branch")
    dispatch.add_argument("--watch", action="store_true", help="Watch the dispatched run until completion")
    dispatch.add_argument("--poll-seconds", type=int, default=10, help="Polling interval for watch mode")
    dispatch.add_argument("--dry-run", action="store_true", help="Print the gh command instead of dispatching")
    dispatch.set_defaults(handler=_dispatch)

    status = subparsers.add_parser("status", help="Show the latest remote worker run")
    status.add_argument("--repo", default=DEFAULT_REPO, help="GitHub repository in owner/name form")
    status.add_argument("--branch", help="Filter by branch")
    status.set_defaults(handler=_status)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        resolved = _repo_name(args.repo)
    except RuntimeError as exc:
        print(f"GitHub repo lookup failed: {exc}", file=sys.stderr)
        return 2
    if resolved != args.repo:
        print(f"Resolved GitHub repo: {resolved}")
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
