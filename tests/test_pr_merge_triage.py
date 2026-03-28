from __future__ import annotations

from scripts.system.pr_merge_triage import build_triage, classify_pr


def test_classify_pr_respects_needs_rebase_label():
    pr = {
        "number": 608,
        "isDraft": False,
        "labels": [{"name": "needs-rebase"}],
    }

    status, reason = classify_pr(pr, [])

    assert status == "blocked"
    assert reason == "needs-rebase"


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
