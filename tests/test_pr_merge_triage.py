from __future__ import annotations

import subprocess

from scripts.system.pr_merge_triage import build_triage, classify_pr, run_gh


def test_classify_pr_respects_needs_rebase_label():
    pr = {
        "number": 608,
        "isDraft": False,
        "labels": [{"name": "needs-rebase"}],
    }

    status, reason = classify_pr(pr, [])

    assert status == "blocked"
    assert reason == "needs-rebase"


def test_classify_pr_waits_when_github_reports_no_checks():
    pr = {
        "number": 609,
        "isDraft": False,
        "labels": [],
    }

    status, reason = classify_pr(pr, [])

    assert status == "wait"
    assert reason == "no checks reported"


def test_run_gh_accepts_the_cli_no_checks_exit(monkeypatch):
    completed = subprocess.CompletedProcess(
        args=["gh", "pr", "checks", "609", "--json", "bucket,name"],
        returncode=1,
        stdout="",
        stderr="no checks reported on the 'automation/feed' branch\n",
    )
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed)

    assert run_gh(["pr", "checks", "609", "--json", "bucket,name"]) == []


def test_build_triage_orders_merge_ready_first():
    prs = [
        {
            "number": 2,
            "title": "blocked",
            "headRefName": "blocked",
            "isDraft": False,
            "labels": [{"name": "needs-rebase"}],
            "url": "x",
        },
        {
            "number": 1,
            "title": "ready",
            "headRefName": "ready",
            "isDraft": False,
            "labels": [],
            "url": "y",
        },
    ]
    checks = {
        1: [{"bucket": "pass", "name": "ci"}],
        2: [{"bucket": "pass", "name": "ci"}],
    }

    triage = build_triage(prs, checks)

    assert triage[0]["number"] == 1
    assert triage[0]["status"] == "merge-ready"
