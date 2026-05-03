from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.system.geoseal_github_ops import (
    build_github_plan,
    execute_github_plan,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_github_plan_routes_actions_runs_to_ca_lane() -> None:
    plan = build_github_plan(mode="runs", repo="owner/repo", limit=3)

    assert plan["schema_version"] == "scbe_geoseal_github_ops_v1"
    assert plan["mode"] == "runs"
    assert plan["commands"][0]["lane"] == "CA"
    assert plan["commands"][0]["argv"] == ["gh", "run", "list", "--limit", "3", "--repo", "owner/repo"]
    assert plan["mutating_commands_enabled"] is False


def test_github_status_uses_repo_view_for_target_repo() -> None:
    plan = build_github_plan(mode="status", repo="owner/repo")

    assert plan["commands"][0]["argv"] == ["gh", "auth", "status"]
    assert plan["commands"][1]["argv"] == [
        "gh",
        "repo",
        "view",
        "owner/repo",
        "--json",
        "nameWithOwner,defaultBranchRef,isPrivate,viewerPermission",
    ]


def test_github_plan_assess_code_prefers_local_read_only_gates() -> None:
    plan = build_github_plan(mode="assess-code")

    assert [command["lane"] for command in plan["commands"]] == ["RU", "DR"]
    assert plan["commands"][0]["argv"] == ["git", "status", "--short"]
    assert "harness_release_readiness.py" in plan["commands"][1]["argv"][1]


def test_github_plan_run_view_requires_run_id() -> None:
    plan = build_github_plan(mode="run-view")

    assert plan["commands"] == []
    assert plan["notes"] == ["run-view needs --run-id before it can execute."]


def test_execute_github_plan_runs_only_allowlisted_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(argv, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="  - Token: gho_secret\nok\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    plan = {
        "schema_version": "scbe_geoseal_github_ops_v1",
        "commands": [
            {
                "lane": "KO",
                "purpose": "allowed",
                "argv": ["gh", "status", "--repo", "owner/repo"],
                "mutates": False,
                "cwd": str(REPO_ROOT),
            },
            {
                "lane": "RU",
                "purpose": "blocked",
                "argv": ["gh", "pr", "merge", "1"],
                "mutates": True,
                "cwd": str(REPO_ROOT),
            },
        ],
    }

    result = execute_github_plan(plan)

    assert calls == [["gh", "status", "--repo", "owner/repo"]]
    assert result["results"][0]["returncode"] == 0
    assert "gho_secret" not in result["results"][0]["stdout"]
    assert "Token: <redacted>" in result["results"][0]["stdout"]
    assert result["results"][1]["skipped"] is True
    assert "read-only allowlist" in result["results"][1]["stderr"]


def test_geoseal_cli_github_dry_run_json() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "github",
            "--mode",
            "workflow-list",
            "--repo",
            "owner/repo",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["mode"] == "workflow-list"
    assert payload["commands"][0]["argv"] == ["gh", "workflow", "list", "--repo", "owner/repo"]
