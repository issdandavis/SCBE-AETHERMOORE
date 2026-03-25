from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


scbe_system_cli = _load_module("test_scbe_system_cli_gh", "scripts/scbe-system-cli.py")


def test_gh_doctor_json_reports_blockers(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        scbe_system_cli,
        "_gh_doctor_payload",
        lambda repo_root, pr=None, verify=False, limit=5: {
            "schema_version": "scbe_gh_doctor_v1",
            "generated_at": "2026-03-24T00:00:00Z",
            "ci": {
                "branch": "feat/test",
                "pr": 42,
                "pass_count": 7,
                "fail_count": 1,
                "pending_count": 2,
            },
            "scan": {"open_alerts": 3},
            "prs": {"count": 5, "sample": []},
            "issues": {"count": 4, "sample": []},
            "release": {"tagName": "v1.2.3"},
            "blockers": ["1 CI check(s) failing.", "3 open code-scanning alert(s)."],
            "healthy": False,
        },
    )

    args = argparse.Namespace(repo_root=str(ROOT), pr=None, verify=False, limit=5, json_output=True)
    rc = scbe_system_cli.cmd_gh_doctor(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == "scbe_gh_doctor_v1"
    assert payload["ci"]["fail_count"] == 1
    assert payload["scan"]["open_alerts"] == 3
    assert payload["healthy"] is False
    assert len(payload["blockers"]) == 2


def test_gh_sweep_json_combines_sections_and_fix_lane(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        scbe_system_cli,
        "_gh_doctor_payload",
        lambda repo_root, pr=None, verify=False, limit=5: {
            "schema_version": "scbe_gh_doctor_v1",
            "ci": {"fail_count": 1, "pending_count": 0},
            "scan": {"open_alerts": 2},
            "blockers": ["1 CI check(s) failing.", "2 open code-scanning alert(s)."],
        },
    )
    monkeypatch.setattr(scbe_system_cli, "_gh_prs_payload", lambda limit=5: {"count": 2, "items": [{"number": 10}]})
    monkeypatch.setattr(scbe_system_cli, "_gh_issues_payload", lambda limit=5: {"count": 1, "items": [{"number": 77}]})
    monkeypatch.setattr(
        scbe_system_cli,
        "_gh_pulse_payload",
        lambda: {
            "commit_count": 9, "merged_pr_count": 3, "ci_pass_count": 5,
            "ci_fail_count": 1, "open_scan_alerts": 2,
        },
    )
    monkeypatch.setattr(scbe_system_cli, "_gh_release_payload", lambda: {"tagName": "v9.9.9"})
    monkeypatch.setattr(scbe_system_cli.subprocess, "call", lambda cmd: 0)

    args = argparse.Namespace(
        repo_root=str(ROOT),
        pr=None,
        verify=False,
        limit=5,
        include_release=True,
        fix_ci=True,
        fix_dry_run=True,
        json_output=True,
    )
    rc = scbe_system_cli.cmd_gh_sweep(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == "scbe_gh_sweep_v1"
    assert payload["prs"]["count"] == 2
    assert payload["issues"]["count"] == 1
    assert payload["pulse"]["commit_count"] == 9
    assert payload["release"]["tagName"] == "v9.9.9"
    assert payload["fix"]["dry_run"] is True
    assert payload["healthy"] is False


def test_ops_board_json_aggregates_sections(monkeypatch, capsys) -> None:
    def fake_run_cli_json(repo_root: str, config_path: str, command: list[str]):
        key = tuple(command)
        payload_map = {
            ("doctor",): {"schema_version": "scbe_doctor_v1"},
            ("status",): {"schema_version": "scbe_status_v1"},
            ("gh", "doctor", "--limit", "5"): {
                "schema_version": "scbe_gh_doctor_v1",
                "blockers": ["3 open code-scanning alert(s)."],
            },
            ("colab", "status"): {"schema_version": "scbe_colab_status_v1"},
        }
        return 0, payload_map[key]

    monkeypatch.setattr(scbe_system_cli, "_run_cli_json", fake_run_cli_json)

    args = argparse.Namespace(
        repo_root=str(ROOT),
        config_path="",
        limit=5,
        verify_scan=False,
        skip_github=False,
        skip_colab=False,
        json_output=True,
    )
    rc = scbe_system_cli.cmd_ops_board(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == "scbe_ops_board_v1"
    assert set(payload["sections"]) == {"doctor", "status", "github", "colab"}
    assert payload["healthy"] is False
    assert payload["blockers"] == ["github: 3 open code-scanning alert(s)."]
