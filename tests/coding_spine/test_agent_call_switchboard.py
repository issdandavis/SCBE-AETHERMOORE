from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.coding_spine.agent_call_switchboard import build_switchboard_snapshot, evaluate_call_request
from src.coding_spine.agent_tool_policy import geoseal_command_to_tool_class

ROOT = Path(__file__).resolve().parents[2]


def test_switchboard_grants_non_colliding_calls() -> None:
    existing = [
        {
            "call_id": "call-codex-tests",
            "agent_id": "agent.codex",
            "lane": "verification",
            "resource": "tests/training",
            "mode": "read",
            "state": "active",
        }
    ]

    decision = evaluate_call_request(
        existing,
        {
            "call_id": "call-cursor-ui",
            "agent_id": "agent.cursor",
            "lane": "ui",
            "resource": "scbe-visual-system",
            "mode": "write",
        },
    )

    assert decision["decision"] == "GRANT"
    assert decision["ok"] is True
    assert decision["collisions"] == []


def test_switchboard_queues_same_surface_write_collision() -> None:
    existing = [
        {
            "call_id": "call-cursor-geoshell",
            "agent_id": "agent.cursor",
            "lane": "ui",
            "resource": "scbe-visual-system",
            "mode": "write",
            "state": "active",
            "priority": 5,
        }
    ]

    decision = evaluate_call_request(
        existing,
        {
            "call_id": "call-codex-geoshell",
            "agent_id": "agent.codex",
            "lane": "ui",
            "resource": "scbe-visual-system",
            "mode": "write",
            "priority": 5,
        },
    )

    assert decision["decision"] == "QUEUE"
    assert decision["ok"] is False
    assert decision["reason"] == "exclusive_surface_collision"
    assert decision["collisions"][0]["call_id"] == "call-cursor-geoshell"
    assert decision["switchboard_event"]["task_type"] == "switchboard"


def test_switchboard_blocks_lower_priority_collision() -> None:
    decision = evaluate_call_request(
        [
            {
                "call_id": "call-claude-apply",
                "agent_id": "agent.claude",
                "lane": "apply",
                "resource": "src/geoseal_cli.py",
                "mode": "apply",
                "state": "reserved",
                "priority": 1,
            }
        ],
        {
            "call_id": "call-codex-apply",
            "agent_id": "agent.codex",
            "lane": "apply",
            "resource": "src/geoseal_cli.py",
            "mode": "apply",
            "priority": 9,
        },
    )

    assert decision["decision"] == "BLOCK"
    assert decision["collisions"][0]["priority"] == 1


def test_switchboard_snapshot_groups_active_calls_by_lane() -> None:
    snapshot = build_switchboard_snapshot(
        [
            {"call_id": "a", "agent_id": "agent.a", "lane": "training", "resource": "sft", "state": "active"},
            {"call_id": "b", "agent_id": "agent.b", "lane": "training", "resource": "eval", "state": "done"},
        ]
    )

    assert snapshot["active_count"] == 1
    assert list(snapshot["by_lane"]) == ["training"]
    assert snapshot["by_lane"]["training"][0]["call_id"] == "a"


def test_geoseal_call_switchboard_cli(tmp_path: Path) -> None:
    calls = tmp_path / "calls.json"
    calls.write_text(
        json.dumps(
            [
                {
                    "call_id": "call-cursor-ui",
                    "agent_id": "agent.cursor",
                    "lane": "ui",
                    "resource": "scbe-visual-system",
                    "mode": "write",
                    "state": "active",
                }
            ]
        ),
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "call-switchboard",
            "--calls",
            str(calls),
            "--request",
            (
                '{"call_id":"call-codex-ui","agent_id":"agent.codex",'
                '"lane":"ui","resource":"scbe-visual-system","mode":"write"}'
            ),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["decision"] == "QUEUE"
    assert payload["collisions"][0]["agent_id"] == "agent.cursor"


def test_call_switchboard_is_read_policy_surface() -> None:
    assert geoseal_command_to_tool_class("call-switchboard") == "read"


def test_agent_harness_exposes_call_switchboard_route() -> None:
    from src.coding_spine.agent_tool_bridge import build_agent_harness_manifest_v1

    manifest = build_agent_harness_manifest_v1(inline_goal="coordinate codex and cursor", permission_mode="observe")

    assert "call_switchboard_json" in manifest["geoseal_cli"]
    assert "call_switchboard" in manifest["mcp_style_exports"]["resources"]
    read_contract = next(row for row in manifest["tool_contracts"] if row["tool"] == "read")
    assert "call-switchboard" in read_contract["routes"]
