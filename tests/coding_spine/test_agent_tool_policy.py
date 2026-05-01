"""Tests for harness-aligned tool policy enforcement."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_geoseal_command_maps_loop_dispatch_execute_to_cloud():
    from src.coding_spine.agent_tool_policy import geoseal_command_to_tool_class

    assert geoseal_command_to_tool_class("loop-dispatch", execute=False) == "read"
    assert geoseal_command_to_tool_class("loop-dispatch", execute=True) == "network_or_cloud"


def test_observe_denies_cloud_tool():
    from src.coding_spine.agent_tool_policy import evaluate_harness_tool_policy

    r = evaluate_harness_tool_policy(permission_mode="observe", tool_class="network_or_cloud")
    assert r["ok"] is False
    assert r["decision"] == "DENY"


def test_cloud_dispatch_allows_cloud_tool():
    from src.coding_spine.agent_tool_policy import evaluate_harness_tool_policy

    r = evaluate_harness_tool_policy(permission_mode="cloud-dispatch", tool_class="network_or_cloud")
    assert r["ok"] is True


def test_workspace_write_requires_approval_env_for_cloud():
    from src.coding_spine.agent_tool_policy import evaluate_harness_tool_policy

    r = evaluate_harness_tool_policy(
        permission_mode="workspace-write",
        tool_class="network_or_cloud",
        cloud_dispatch_approval="",
    )
    assert r["ok"] is False
    assert r["decision"] == "QUARANTINE"
    r2 = evaluate_harness_tool_policy(
        permission_mode="workspace-write",
        tool_class="network_or_cloud",
        cloud_dispatch_approval="1",
    )
    assert r2["ok"] is True
    assert r2["decision"] == "ALLOW"


def test_workspace_write_approval_reads_env_when_param_omitted():
    from src.coding_spine.agent_tool_policy import evaluate_harness_tool_policy

    old = os.environ.pop("SCBE_POLICY_APPROVE_CLOUD_DISPATCH", None)
    try:
        r = evaluate_harness_tool_policy(permission_mode="workspace-write", tool_class="network_or_cloud")
        assert r["ok"] is False
        os.environ["SCBE_POLICY_APPROVE_CLOUD_DISPATCH"] = "yes"
        r2 = evaluate_harness_tool_policy(permission_mode="workspace-write", tool_class="network_or_cloud")
        assert r2["ok"] is True
    finally:
        os.environ.pop("SCBE_POLICY_APPROVE_CLOUD_DISPATCH", None)
        if old is not None:
            os.environ["SCBE_POLICY_APPROVE_CLOUD_DISPATCH"] = old


def test_loop_dispatch_execute_observe_denied_cli_json():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "loop-dispatch",
            "--provider",
            "github",
            "--task",
            "list_runs",
            "--permission-mode",
            "observe",
            "--execute",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={k: v for k, v in os.environ.items() if k != "SCBE_POLICY_APPROVE_CLOUD_DISPATCH"},
        timeout=60,
    )
    assert proc.returncode == 2
    out = json.loads(proc.stdout)
    assert "policy" in out
    assert out["policy"]["ok"] is False


def test_loop_dispatch_execute_cloud_dispatch_reaches_execute_gate_json():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "loop-dispatch",
            "--provider",
            "github",
            "--task",
            "list_runs",
            "--permission-mode",
            "cloud-dispatch",
            "--execute",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={k: v for k, v in os.environ.items() if k not in ("SCBE_AGENTIC_LOOP_EXECUTE",)},
        timeout=60,
    )
    assert proc.returncode == 2
    out = json.loads(proc.stdout)
    assert "execute_gate" in out
    assert out["policy"]["ok"] is True
