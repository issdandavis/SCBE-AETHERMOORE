#!/usr/bin/env python3
"""Start protected checks and enable auto-merge for a generated pull request.

Pull requests created with ``GITHUB_TOKEN`` leave their ``pull_request``
workflow runs in ``action_required``.  Approving only one run is not enough:
every required branch-protection check must start before auto-merge can finish.

This helper verifies the PR target, waits for the required workflow runs for
one exact head SHA, approves those named runs, and then enables squash
auto-merge. It remains alive until the PR merges. If ``main`` advances first,
it updates the generated branch with an exact expected-head precondition and
re-arms checks for the resulting SHA. It never approves runs from another
commit, workflow, or event.
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


def _fetch_pr(repo: str, pr_number: int) -> dict[str, Any]:
    result = _run_gh(
        [
            "pr",
            "view",
            str(pr_number),
            "--repo",
            repo,
            "--json",
            "headRefOid,baseRefName,state,mergeStateStatus,isCrossRepository",
        ]
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GateError(f"GitHub returned invalid pull-request JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise GateError("GitHub returned an invalid pull-request payload")
    return payload


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


def verify_pr_target(repo: str, pr_url: str, head_sha: str, base_ref: str) -> int:
    """Bind the supplied URL, head SHA, and base branch before approvals."""
    pr_number = _pr_number_for_repo(repo, pr_url)
    pull_request = _fetch_pr(repo, pr_number)
    if str(pull_request.get("state", "")).upper() != "OPEN":
        raise GateError("Generated pull request is not open")
    if pull_request.get("isCrossRepository"):
        raise GateError(
            "Generated pull request must use a branch in the same repository"
        )
    if str(pull_request.get("headRefOid", "")).lower() != head_sha.lower():
        raise GateError("Generated pull request head does not match --head-sha")
    if pull_request.get("baseRefName") != base_ref:
        raise GateError(f"Generated pull request does not target {base_ref}")
    return pr_number


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


def update_pr_branch(repo: str, pr_number: int, expected_head_sha: str) -> None:
    """Update a behind branch only if it still has the verified head SHA."""
    _run_gh(
        [
            "api",
            "--method",
            "PUT",
            f"repos/{repo}/pulls/{pr_number}/update-branch",
            "-f",
            f"expected_head_sha={expected_head_sha}",
        ]
    )
    print(f"Requested base update for generated PR at {expected_head_sha}.", flush=True)


def arm_pr_head(
    repo: str,
    pr_url: str,
    head_sha: str,
    base_ref: str,
    required_workflows: tuple[str, ...],
    *,
    timeout_seconds: float,
    poll_seconds: float,
) -> None:
    """Approve and auto-merge one verified, exact PR head."""
    verify_pr_target(repo, pr_url, head_sha, base_ref)
    runs = wait_for_required_runs(
        repo,
        head_sha,
        required_workflows,
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
    )
    verify_pr_target(repo, pr_url, head_sha, base_ref)
    approved = approve_gated_runs(repo, head_sha, runs, required_workflows)
    if not approved:
        print("Required workflow runs were already started; no approvals needed.")
    enable_auto_merge(pr_url)
    print(f"Generated PR gate armed for {head_sha}.", flush=True)


def wait_until_merged(
    repo: str,
    pr_url: str,
    pr_number: int,
    head_sha: str,
    base_ref: str,
    required_workflows: tuple[str, ...],
    *,
    timeout_seconds: float,
    poll_seconds: float,
    run_timeout_seconds: float,
    run_poll_seconds: float,
) -> str:
    """Hold workflow concurrency until the PR merges, updating behind heads."""
    deadline = time.monotonic() + timeout_seconds
    current_head = head_sha.lower()
    update_pending = False

    while True:
        pull_request = _fetch_pr(repo, pr_number)
        state = str(pull_request.get("state", "")).upper()
        observed_head = str(pull_request.get("headRefOid", "")).lower()
        merge_state = str(pull_request.get("mergeStateStatus", "")).upper()

        if pull_request.get("isCrossRepository"):
            raise GateError(
                "Generated pull request changed to a cross-repository branch"
            )
        if pull_request.get("baseRefName") != base_ref:
            raise GateError(f"Generated pull request no longer targets {base_ref}")
        if not SHA_RE.fullmatch(observed_head):
            raise GateError("Generated pull request returned an invalid head SHA")
        head_advanced = observed_head != current_head
        if head_advanced:
            if not update_pending:
                raise GateError(
                    "Generated pull request head changed without an authorized base update"
                )
            current_head = observed_head
            update_pending = False
            print(
                f"Generated PR advanced to authorized head {current_head}.", flush=True
            )

        if state == "MERGED":
            print(f"Generated pull request merged at head {current_head}.", flush=True)
            return current_head
        if state == "CLOSED":
            raise GateError("Generated pull request closed before it merged")
        if state != "OPEN":
            raise GateError(
                f"Generated pull request returned unexpected state: {state or 'empty'}"
            )

        if head_advanced:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise GateError("Timed out waiting for generated pull request to merge")
            arm_pr_head(
                repo,
                pr_url,
                current_head,
                base_ref,
                required_workflows,
                timeout_seconds=min(run_timeout_seconds, remaining),
                poll_seconds=run_poll_seconds,
            )

        if merge_state == "DIRTY":
            raise GateError("Generated pull request has merge conflicts")
        if merge_state == "BEHIND" and not update_pending:
            update_pr_branch(repo, pr_number, current_head)
            update_pending = True

        if time.monotonic() >= deadline:
            pending_note = " after requesting a base update" if update_pending else ""
            raise GateError(
                "Timed out waiting for generated pull request to merge" + pending_note
            )
        time.sleep(poll_seconds)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--pr-url", required=True)
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--required-workflow", action="append", default=[])
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--merge-timeout-seconds", type=float, default=2400.0)
    parser.add_argument("--merge-poll-seconds", type=float, default=10.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    required = tuple(args.required_workflow) or DEFAULT_REQUIRED_WORKFLOWS
    if not REPO_RE.fullmatch(args.repo):
        raise GateError("--repo must be in owner/name form")
    if not SHA_RE.fullmatch(args.head_sha):
        raise GateError("--head-sha must be a full 40-character Git SHA")
    if (
        args.timeout_seconds <= 0
        or args.poll_seconds <= 0
        or args.merge_timeout_seconds <= 0
        or args.merge_poll_seconds <= 0
    ):
        raise GateError("timeout and poll intervals must be positive")

    head_sha = args.head_sha.lower()
    pr_number = verify_pr_target(args.repo, args.pr_url, head_sha, args.base_ref)
    arm_pr_head(
        args.repo,
        args.pr_url,
        head_sha,
        args.base_ref,
        required,
        timeout_seconds=args.timeout_seconds,
        poll_seconds=args.poll_seconds,
    )
    wait_until_merged(
        args.repo,
        args.pr_url,
        pr_number,
        head_sha,
        args.base_ref,
        required,
        timeout_seconds=args.merge_timeout_seconds,
        poll_seconds=args.merge_poll_seconds,
        run_timeout_seconds=args.timeout_seconds,
        run_poll_seconds=args.poll_seconds,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"generated-pr-gate: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
