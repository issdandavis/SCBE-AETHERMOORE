from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "system" / "github_control_plane.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("github_control_plane", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_owner_repo_handles_https_and_strips_git_suffix() -> None:
    module = _load_module()
    assert module.parse_owner_repo("https://github.com/issdandavis/SCBE-AETHERMOORE.git") == "issdandavis/SCBE-AETHERMOORE"


def test_parse_owner_repo_handles_embedded_credentials() -> None:
    module = _load_module()
    remote = "https://oauth2:secret@gitlab.com/issdandavis7795/SCBE-AETHERMOORE.git"
    assert module.parse_owner_repo(remote) == "issdandavis7795/SCBE-AETHERMOORE"


def test_branch_is_protected_respects_exact_current_and_patterns() -> None:
    module = _load_module()
    assert module.branch_is_protected("main", "overnight/2026-03-30", {"main"}, ["overnight/*"]) is True
    assert module.branch_is_protected("overnight/2026-03-30", "overnight/2026-03-30", {"main"}, ["release/*"]) is True
    assert module.branch_is_protected("release/1.0.0", "feature/x", {"main"}, ["release/*"]) is True
    assert module.branch_is_protected("feature/x", "main", {"main"}, ["release/*"]) is False


def test_classify_branches_preserves_open_prs_and_marks_safe_delete() -> None:
    module = _load_module()
    open_prs = [
        module.PullRequestHead(
            number=884,
            title="Flock lifecycle",
            url="https://github.com/issdandavis/SCBE-AETHERMOORE/pull/884",
            head_ref="feat/flock",
            base_ref="main",
            is_draft=False,
        )
    ]
    result = module.classify_branches(
        remote_branches=["main", "feat/flock", "fix/merged", "backup/pre-restart-2026-03-29"],
        merged_into={"main": ["main", "fix/merged"], "overnight/2026-03-30": []},
        open_prs=open_prs,
        current_branch="overnight/2026-03-30",
        owner_repo="issdandavis/SCBE-AETHERMOORE",
        exact_keep={"main", "overnight/2026-03-30"},
        keep_patterns=["overnight/*"],
        review_patterns=["backup/*"],
    )

    keep_branches = {row.branch: row.reason for row in result["keep"]}
    safe_delete_branches = {row.branch for row in result["safe_delete"]}
    review_branches = {row.branch: row.reason for row in result["manual_review"]}

    assert keep_branches["main"] == "protected branch"
    assert keep_branches["feat/flock"] == "open pull request head"
    assert "fix/merged" in safe_delete_branches
    assert review_branches["backup/pre-restart-2026-03-29"] == "not merged into canonical branch"


def test_find_external_pr_heads_marks_fork_style_heads() -> None:
    module = _load_module()
    open_prs = [
        module.PullRequestHead(
            number=881,
            title="Security sanitization",
            url="https://github.com/issdandavis/SCBE-AETHERMOORE/pull/881",
            head_ref="fix/security-url-html-sanitization",
            base_ref="master",
            is_draft=False,
        ),
        module.PullRequestHead(
            number=877,
            title="Notion sync",
            url="https://github.com/issdandavis/SCBE-AETHERMOORE/pull/877",
            head_ref="automation/notion-sync",
            base_ref="main",
            is_draft=False,
        ),
    ]

    external = module.find_external_pr_heads(open_prs, ["automation/notion-sync", "main", "overnight/2026-03-30"])

    assert [pr.number for pr in external] == [881]
