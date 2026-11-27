#!/usr/bin/env python3
"""Start protected checks and enable auto-merge for a generated pull request.

Pull requests created with ``GITHUB_TOKEN`` leave their ``pull_request``
workflow runs in ``action_required``.  Approving only one run is not enough:
every required branch-protection check must start before auto-merge can finish.

This helper verifies the PR target, waits for the required workflow runs for
one exact head SHA, approves those named runs, and then enables squash
auto-merge. It never approves runs from another commit, workflow, or event.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Iterable
from typing import Any
from urllib.parse import urlparse

DEFAULT_REQUIRED_WORKFLOWS = ("CI", "Conflict Marker Guard")
FAILURE_CONCLUSIONS = {
    "cancelled",
    "failure",
    "startup_failure",
    "timed_out",
}
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


class GateError(RuntimeError):
    """Raised when a generated PR cannot be advanced safely."""


def _run_gh(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _head_pr_runs(payload: dict[str, Any], head_sha: str) -> list[dict[str, Any]]:
    """Return only pull-request runs attached to the exact generated commit."""
    return [
        run
        for run in payload.get("workflow_runs", [])
        if run.get("head_sha") == head_sha and run.get("event") == "pull_request"
    ]


def _latest_by_workflow(runs: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Keep the newest run for each workflow name."""
    latest: dict[str, dict[str, Any]] = {}
    for run in runs:
        name = str(run.get("name", ""))
        if not name:
            continue
        previous = latest.get(name)
        ordering = (int(run.get("run_attempt") or 0), int(run.get("id") or 0))
        previous_ordering = (
            (
                int(previous.get("run_attempt") or 0),
                int(previous.get("id") or 0),
            )
            if previous
            else (-1, -1)
        )
        if ordering > previous_ordering:
            latest[name] = run
    return latest


def _required_state(
    runs: Iterable[dict[str, Any]], required_workflows: Iterable[str]
) -> tuple[list[str], list[str]]:
    """Return missing and failed required workflow names."""
    latest = _latest_by_workflow(runs)
    missing: list[str] = []
    failed: list[str] = []
    for name in required_workflows:
        run = latest.get(name)
        if run is None:
            missing.append(name)
            continue
        conclusion = str(run.get("conclusion") or "").lower()
        if conclusion in FAILURE_CONCLUSIONS:
            failed.append(f"{name} ({conclusion})")
    return missing, failed


def _fetch_runs(repo: str, head_sha: str) -> list[dict[str, Any]]:
    endpoint = (
        f"repos/{repo}/actions/runs?head_sha={head_sha}&event=pull_request&per_page=100"
    )
    result = _run_gh(["api", endpoint])
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GateError(f"GitHub returned invalid workflow-run JSON: {exc}") from exc
    return _head_pr_runs(payload, head_sha)


def _pr_number_for_repo(repo: str, pr_url: str) -> int:
    parsed = urlparse(pr_url)
    parts = [part for part in parsed.path.split("/") if part]
    expected = repo.split("/")
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != "github.com"
        or len(parts) != 4
        or parts[:2] != expected
        or parts[2] != "pull"
        or not parts[3].isdigit()
    ):
        raise GateError(f"--pr-url must identify a pull request in {repo}")
    return int(parts[3])


def verify_pr_target(repo: str, pr_url: str, head_sha: str, base_ref: str) -> None:
    """Bind the supplied URL, head SHA, and base branch before approvals."""
    pr_number = _pr_number_for_repo(repo, pr_url)
    result = _run_gh(
        [
            "pr",
            "view",
            str(pr_number),
            "--repo",
            repo,
            "--json",
            "headRefOid,baseRefName,state",
        ]
    )
    try:
        pull_request = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GateError(f"GitHub returned invalid pull-request JSON: {exc}") from exc
    if str(pull_request.get("state", "")).upper() != "OPEN":
        raise GateError("Generated pull request is not open")
    if str(pull_request.get("headRefOid", "")).lower() != head_sha.lower():
        raise GateError("Generated pull request head does not match --head-sha")
    if pull_request.get("baseRefName") != base_ref:
        raise GateError(f"Generated pull request does not target {base_ref}")


def wait_for_required_runs(
    repo: str,
    head_sha: str,
    required_workflows: tuple[str, ...],
    *,
    timeout_seconds: float,
    poll_seconds: float,
    fetch_runs: Callable[[str, str], list[dict[str, Any]]] = _fetch_runs,
) -> list[dict[str, Any]]:
    """Wait until every named workflow has registered a run for the head SHA."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        runs = fetch_runs(repo, head_sha)
        missing, failed = _required_state(runs, required_workflows)
        if failed:
            raise GateError("Required workflow already failed: " + ", ".join(failed))
        if not missing:
            return runs
        if time.monotonic() >= deadline:
            raise GateError(
                "Timed out waiting for required workflow runs: " + ", ".join(missing)
            )
        print("Waiting for required workflow runs: " + ", ".join(missing), flush=True)
        time.sleep(poll_seconds)


def approve_gated_runs(
    repo: str,
    head_sha: str,
    runs: Iterable[dict[str, Any]],
    allowed_workflows: Iterable[str],
) -> list[int]:
    """Approve named action-required PR runs for this exact head SHA."""
    allowed = set(allowed_workflows)
    approved: list[int] = []
    latest_runs = _latest_by_workflow(runs).values()
    for run in sorted(latest_runs, key=lambda item: int(item.get("id") or 0)):
        if run.get("head_sha") != head_sha or run.get("event") != "pull_request":
            continue
        if run.get("name") not in allowed:
            continue
        if str(run.get("conclusion") or "").lower() != "action_required":
            continue
        run_id = int(run["id"])
        _run_gh(
            ["api", "--method", "POST", f"repos/{repo}/actions/runs/{run_id}/approve"]
        )
        approved.append(run_id)
        print(f"Approved gated workflow run {run_id}: {run.get('name', 'unknown')}")
    return approved


def enable_auto_merge(pr_url: str) -> None:
    """Enable squash auto-merge, tolerating an already-enabled merge queue."""
    result = _run_gh(["pr", "merge", "--auto", "--squash", pr_url], check=False)
    combined = "\n".join(
        part for part in (result.stdout, result.stderr) if part
    ).strip()
    if result.returncode == 0:
        if combined:
            print(combined)
        return
    tolerated = ("Merge already in progress", "Base branch was modified")
    if any(marker in combined for marker in tolerated):
        print(combined)
        return
    raise GateError(
        f"Could not enable auto-merge: {combined or 'gh returned no error text'}"
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--pr-url", required=True)
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--required-workflow", action="append", default=[])
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    required = tuple(args.required_workflow) or DEFAULT_REQUIRED_WORKFLOWS
    if not REPO_RE.fullmatch(args.repo):
        raise GateError("--repo must be in owner/name form")
    if not SHA_RE.fullmatch(args.head_sha):
        raise GateError("--head-sha must be a full 40-character Git SHA")
    if args.timeout_seconds <= 0 or args.poll_seconds <= 0:
        raise GateError("timeout and poll intervals must be positive")

    verify_pr_target(args.repo, args.pr_url, args.head_sha, args.base_ref)
    runs = wait_for_required_runs(
        args.repo,
        args.head_sha.lower(),
        required,
        timeout_seconds=args.timeout_seconds,
        poll_seconds=args.poll_seconds,
    )
    approved = approve_gated_runs(args.repo, args.head_sha.lower(), runs, required)
    if not approved:
        print("Required workflow runs were already started; no approvals needed.")
    enable_auto_merge(args.pr_url)
    print(f"Generated PR gate armed for {args.head_sha.lower()}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"generated-pr-gate: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
