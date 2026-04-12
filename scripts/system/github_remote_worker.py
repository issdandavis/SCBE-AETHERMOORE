#!/usr/bin/env python3
"""Dispatch and monitor free remote jobs on GitHub Actions."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
WORKFLOW_NAME = "free-remote-worker.yml"
DEFAULT_REPO = os.environ.get("SCBE_GITHUB_REMOTE_REPO", "issdandavis/SCBE-AETHERMOORE")
PRESETS: dict[str, dict[str, str]] = {
    "python-smoke": {
        "description": "Run the validated Python smoke slice for browser and constants tests",
        "task_label": "python-smoke",
        "command": "python -m pytest tests/aetherbrowser tests/aethermoore_constants",
        "install_mode": "auto",
        "working_directory": ".",
        "artifact_glob": "",
    },
    "tax-sample": {
        "description": "Run the tax CLI sample calculation",
        "task_label": "tax-sample",
        "command": "python -m tools.tax.cli calculate --input tools/tax/sample_input.json",
        "install_mode": "auto",
        "working_directory": ".",
        "artifact_glob": "",
    },
    "stasm-smoke": {
        "description": "Assemble and execute the STASM hello world sample",
        "task_label": "stasm-smoke",
        "command": "python -m tools.stasm.assembler examples/hello_world.sts /tmp/hello.bin && python -m tools.stvm.vm /tmp/hello.bin",
        "install_mode": "auto",
        "working_directory": ".",
        "artifact_glob": "",
    },
}


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

    proc = _run(gh_cmd, capture=True)
    if proc.returncode != 0:
        if proc.stdout:
            print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, end="", file=sys.stderr)
        return proc.returncode

    combined_output = "".join(part for part in (proc.stdout, proc.stderr) if part)
    if combined_output:
        print(combined_output, end="")

    match = re.search(r"/actions/runs/(\d+)", combined_output)
    run_id = match.group(1) if match else None

    print(f"Dispatched {WORKFLOW_NAME} on branch {branch}")
    if args.watch:
        if run_id:
            return _watch_run_id(args.repo, run_id, poll_seconds=args.poll_seconds)
        return _watch(args.repo, branch=branch, poll_seconds=args.poll_seconds)
    return 0


def _presets(_: argparse.Namespace) -> int:
    for name, spec in sorted(PRESETS.items()):
        print(f"{name}: {spec['description']}")
    return 0


def _preset(args: argparse.Namespace) -> int:
    spec = PRESETS.get(args.preset_name)
    if spec is None:
        available = ", ".join(sorted(PRESETS))
        print(f"Unknown preset: {args.preset_name}. Available presets: {available}", file=sys.stderr)
        return 2

    args.command = spec["command"]
    args.task_label = args.task_label or spec["task_label"]
    args.install_mode = args.install_mode or spec["install_mode"]
    args.working_directory = args.working_directory or spec["working_directory"]
    args.artifact_glob = args.artifact_glob if args.artifact_glob is not None else spec["artifact_glob"]
    return _dispatch(args)


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
    return _watch_run_id(repo, run_id, poll_seconds=poll_seconds)


def _watch_run_id(repo: str, run_id: str, *, poll_seconds: int = 10) -> int:
    run = json.loads(_must(["gh", "run", "view", "-R", repo, run_id, "--json", "databaseId,conclusion,url"]))
    print(f"Watching run {run_id}: {run['url']}")
    watch_proc = _run(["gh", "run", "watch", "-R", repo, run_id, "--interval", str(poll_seconds)])
    refreshed = json.loads(_must(["gh", "run", "view", "-R", repo, run_id, "--json", "databaseId,conclusion,url"]))
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

    presets = subparsers.add_parser("presets", help="List built-in remote job presets")
    presets.set_defaults(handler=_presets)

    preset = subparsers.add_parser("preset", help="Trigger a built-in remote job preset")
    preset.add_argument("preset_name", choices=sorted(PRESETS), help="Preset to dispatch")
    preset.add_argument("--repo", default=DEFAULT_REPO, help="GitHub repository in owner/name form")
    preset.add_argument("--task-label", help="Override the preset task label")
    preset.add_argument("--python-version", default="3.11", help="Python version for the worker")
    preset.add_argument(
        "--install-mode",
        choices=("auto", "editable", "requirements", "none"),
        help="Override the preset dependency bootstrap strategy",
    )
    preset.add_argument("--working-directory", help="Override the preset working directory relative to repo root")
    preset.add_argument("--artifact-glob", default=None, help="Override the preset additional artifact glob")
    preset.add_argument("--ref", help="Git ref or branch to run the workflow on; defaults to the remote repo default branch")
    preset.add_argument("--watch", action="store_true", help="Watch the dispatched run until completion")
    preset.add_argument("--poll-seconds", type=int, default=10, help="Polling interval for watch mode")
    preset.add_argument("--dry-run", action="store_true", help="Print the gh command instead of dispatching")
    preset.set_defaults(handler=_preset)

    status = subparsers.add_parser("status", help="Show the latest remote worker run")
    status.add_argument("--repo", default=DEFAULT_REPO, help="GitHub repository in owner/name form")
    status.add_argument("--branch", help="Filter by branch")
    status.set_defaults(handler=_status)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    repo = getattr(args, "repo", None)
    if repo is not None:
        try:
            resolved = _repo_name(repo)
        except RuntimeError as exc:
            print(f"GitHub repo lookup failed: {exc}", file=sys.stderr)
            return 2
        if resolved != repo:
            print(f"Resolved GitHub repo: {resolved}")
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
