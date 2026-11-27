from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.system import generated_pr_gate as gate

HEAD = "a" * 40


def _run(
    run_id: int,
    name: str,
    *,
    sha: str = HEAD,
    event: str = "pull_request",
    conclusion: str = "action_required",
    attempt: int = 1,
) -> dict:
    return {
        "id": run_id,
        "name": name,
        "head_sha": sha,
        "event": event,
        "conclusion": conclusion,
        "run_attempt": attempt,
    }


def test_head_pr_runs_rejects_other_commits_and_events():
    payload = {
        "workflow_runs": [
            _run(1, "CI"),
            _run(2, "CI", sha="b" * 40),
            _run(3, "CI", event="push"),
        ]
    }

    assert gate._head_pr_runs(payload, HEAD) == [payload["workflow_runs"][0]]


def test_required_state_uses_latest_attempt_and_reports_failures():
    runs = [
        _run(1, "CI", conclusion="failure"),
        _run(2, "CI", conclusion="success", attempt=2),
        _run(3, "Conflict Marker Guard", conclusion="timed_out"),
    ]

    missing, failed = gate._required_state(runs, gate.DEFAULT_REQUIRED_WORKFLOWS)

    assert missing == []
    assert failed == ["Conflict Marker Guard (timed_out)"]


def test_wait_for_required_runs_polls_until_both_exist(monkeypatch):
    calls = iter(
        [
            [_run(1, "CI")],
            [_run(1, "CI"), _run(2, "Conflict Marker Guard")],
        ]
    )
    monkeypatch.setattr(gate.time, "sleep", lambda _seconds: None)

    runs = gate.wait_for_required_runs(
        "owner/repo",
        HEAD,
        gate.DEFAULT_REQUIRED_WORKFLOWS,
        timeout_seconds=5,
        poll_seconds=0.01,
        fetch_runs=lambda _repo, _sha: next(calls),
    )

    assert {run["name"] for run in runs} == {"CI", "Conflict Marker Guard"}


def test_approve_gated_runs_approves_only_named_workflows_on_exact_head(monkeypatch):
    commands: list[list[str]] = []

    def fake_run(args: list[str], *, check: bool = True):
        commands.append(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(gate, "_run_gh", fake_run)
    runs = [
        _run(12, "CI"),
        _run(10, "Conflict Marker Guard"),
        _run(11, "CodeQL", conclusion="success"),
        _run(14, "Untrusted Future Workflow"),
        _run(13, "Other", sha="b" * 40),
    ]

    approved = gate.approve_gated_runs(
        "owner/repo", HEAD, runs, gate.DEFAULT_REQUIRED_WORKFLOWS
    )

    assert approved == [10, 12]
    assert commands == [
        ["api", "--method", "POST", "repos/owner/repo/actions/runs/10/approve"],
        ["api", "--method", "POST", "repos/owner/repo/actions/runs/12/approve"],
    ]


def test_pr_number_rejects_cross_repo_or_non_github_url():
    assert (
        gate._pr_number_for_repo("owner/repo", "https://github.com/owner/repo/pull/12")
        == 12
    )
    with pytest.raises(gate.GateError):
        gate._pr_number_for_repo("owner/repo", "https://github.com/other/repo/pull/12")
    with pytest.raises(gate.GateError):
        gate._pr_number_for_repo("owner/repo", "https://example.com/owner/repo/pull/12")


def test_verify_pr_target_binds_head_and_base(monkeypatch):
    def fake_run(_args: list[str], *, check: bool = True):
        payload = '{"headRefOid":"' + HEAD + '","baseRefName":"main","state":"OPEN"}'
        return subprocess.CompletedProcess(_args, 0, payload, "")

    monkeypatch.setattr(gate, "_run_gh", fake_run)

    gate.verify_pr_target(
        "owner/repo", "https://github.com/owner/repo/pull/12", HEAD, "main"
    )
    with pytest.raises(gate.GateError, match="head does not match"):
        gate.verify_pr_target(
            "owner/repo", "https://github.com/owner/repo/pull/12", "b" * 40, "main"
        )


def test_update_pr_branch_uses_exact_expected_head(monkeypatch):
    commands: list[list[str]] = []

    def fake_run(args: list[str], *, check: bool = True):
        commands.append(args)
        return subprocess.CompletedProcess(
            args, 0, '{"message":"Updating pull request branch."}', ""
        )

    monkeypatch.setattr(gate, "_run_gh", fake_run)

    gate.update_pr_branch("owner/repo", 12, HEAD)

    assert commands == [
        [
            "api",
            "--method",
            "PUT",
            "repos/owner/repo/pulls/12/update-branch",
            "-f",
            f"expected_head_sha={HEAD}",
        ]
    ]


def test_wait_until_merged_updates_behind_and_rearms_exact_new_head(monkeypatch):
    updated_head = "b" * 40
    pull_requests = iter(
        [
            {
                "headRefOid": HEAD,
                "baseRefName": "main",
                "state": "OPEN",
                "mergeStateStatus": "BEHIND",
                "isCrossRepository": False,
            },
            {
                "headRefOid": HEAD,
                "baseRefName": "main",
                "state": "OPEN",
                "mergeStateStatus": "BEHIND",
                "isCrossRepository": False,
            },
            {
                "headRefOid": updated_head,
                "baseRefName": "main",
                "state": "OPEN",
                "mergeStateStatus": "BLOCKED",
                "isCrossRepository": False,
            },
            {
                "headRefOid": updated_head,
                "baseRefName": "main",
                "state": "MERGED",
                "mergeStateStatus": "UNKNOWN",
                "isCrossRepository": False,
            },
        ]
    )
    updates: list[tuple[str, int, str]] = []
    armed: list[str] = []
    monkeypatch.setattr(gate, "_fetch_pr", lambda _repo, _number: next(pull_requests))
    monkeypatch.setattr(
        gate,
        "update_pr_branch",
        lambda repo, number, sha: updates.append((repo, number, sha)),
    )
    monkeypatch.setattr(
        gate,
        "arm_pr_head",
        lambda _repo, _url, sha, _base, _required, **_kwargs: armed.append(sha),
    )
    monkeypatch.setattr(gate.time, "sleep", lambda _seconds: None)

    merged_head = gate.wait_until_merged(
        "owner/repo",
        "https://github.com/owner/repo/pull/12",
        12,
        HEAD,
        "main",
        gate.DEFAULT_REQUIRED_WORKFLOWS,
        timeout_seconds=5,
        poll_seconds=0.01,
        run_timeout_seconds=1,
        run_poll_seconds=0.01,
    )

    assert updates == [("owner/repo", 12, HEAD)]
    assert armed == [updated_head]
    assert merged_head == updated_head


def test_wait_until_merged_rejects_unexpected_head_change(monkeypatch):
    monkeypatch.setattr(
        gate,
        "_fetch_pr",
        lambda _repo, _number: {
            "headRefOid": "b" * 40,
            "baseRefName": "main",
            "state": "OPEN",
            "mergeStateStatus": "BLOCKED",
            "isCrossRepository": False,
        },
    )

    with pytest.raises(gate.GateError, match="without an authorized base update"):
        gate.wait_until_merged(
            "owner/repo",
            "https://github.com/owner/repo/pull/12",
            12,
            HEAD,
            "main",
            gate.DEFAULT_REQUIRED_WORKFLOWS,
            timeout_seconds=5,
            poll_seconds=0.01,
            run_timeout_seconds=1,
            run_poll_seconds=0.01,
        )


def test_generated_workflows_share_serial_merge_concurrency():
    repo_root = Path(__file__).resolve().parents[1]
    for relative_path in (
        ".github/workflows/daily-repo-stats.yml",
        ".github/workflows/research-feed.yml",
    ):
        workflow = (repo_root / relative_path).read_text(encoding="utf-8")
        assert (
            "\nconcurrency:\n  group: generated-content-pr\n  cancel-in-progress: false\n"
            in workflow
        )
        assert "timeout-minutes: 60" in workflow


@pytest.mark.parametrize(
    "message", ["Merge already in progress", "Base branch was modified"]
)
def test_enable_auto_merge_tolerates_known_queue_races(monkeypatch, message):
    monkeypatch.setattr(
        gate,
        "_run_gh",
        lambda _args, check=False: subprocess.CompletedProcess(_args, 1, "", message),
    )

    gate.enable_auto_merge("https://github.com/owner/repo/pull/1")


def test_enable_auto_merge_rejects_unknown_failure(monkeypatch):
    monkeypatch.setattr(
        gate,
        "_run_gh",
        lambda _args, check=False: subprocess.CompletedProcess(
            _args, 1, "", "permission denied"
        ),
    )

    with pytest.raises(gate.GateError, match="permission denied"):
        gate.enable_auto_merge("https://github.com/owner/repo/pull/1")
