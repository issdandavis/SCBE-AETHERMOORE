"""MC/DC-style independence verification for ``evaluate_harness_tool_policy``.

Each test proves one condition can flip the outcome while related inputs stay
fixed (unique-cause where possible). ``cloud_dispatch_approval`` injects the
approval string so outcomes do not depend on process environment.

Decision order in implementation (must stay aligned with tests):
  unknown profile -> DENY
  tool_class in blocks -> DENY
  tool_class in allows -> ALLOW
  tool_class in requires_approval -> QUARANTINE unless approval truthy -> ALLOW
  else -> DENY (unlisted for profile)
"""

from __future__ import annotations

import pytest

from src.coding_spine.agent_tool_policy import (
    evaluate_harness_tool_policy,
    geoseal_command_to_tool_class,
)


def test_mcdc_unknown_permission_mode_independent_effect():
    """Changing only permission_mode from valid to invalid flips ok / decision."""
    known = evaluate_harness_tool_policy(permission_mode="observe", tool_class="read")
    assert known["ok"] is True
    assert known["decision"] == "ALLOW"

    unknown = evaluate_harness_tool_policy(permission_mode="not-a-real-mode", tool_class="read")
    assert unknown["ok"] is False
    assert unknown["decision"] == "DENY"
    assert "unknown permission_mode" in unknown["reason"]


def test_mcdc_block_network_in_observe_independent_of_approval_string():
    """network_or_cloud is blocked in observe; approval override must not apply to blocks."""
    r = evaluate_harness_tool_policy(
        permission_mode="observe",
        tool_class="network_or_cloud",
        cloud_dispatch_approval="1",
    )
    assert r["ok"] is False
    assert r["decision"] == "DENY"
    assert "blocked" in r["reason"].lower()


def test_mcdc_same_tool_class_cloud_dispatch_allows_not_blocked():
    """Same tool_class as block test; changing mode removes block -> ALLOW."""
    r = evaluate_harness_tool_policy(permission_mode="cloud-dispatch", tool_class="network_or_cloud")
    assert r["ok"] is True
    assert r["decision"] == "ALLOW"


def test_mcdc_requires_branch_env_off_vs_on_workspace_write_cloud():
    """requires_approval path: only approval string changes QUARANTINE -> ALLOW."""
    off = evaluate_harness_tool_policy(
        permission_mode="workspace-write",
        tool_class="network_or_cloud",
        cloud_dispatch_approval="",
    )
    assert off["ok"] is False
    assert off["decision"] == "QUARANTINE"

    for token in ("1", "true", "TRUE", "yes", "on"):
        on = evaluate_harness_tool_policy(
            permission_mode="workspace-write",
            tool_class="network_or_cloud",
            cloud_dispatch_approval=token,
        )
        assert on["ok"] is True, token
        assert on["decision"] == "ALLOW", token


def test_mcdc_requires_branch_cloud_dispatch_write_workspace():
    """cloud-dispatch: write_workspace requires approval; env gates ALLOW."""
    q = evaluate_harness_tool_policy(
        permission_mode="cloud-dispatch",
        tool_class="write_workspace",
        cloud_dispatch_approval="",
    )
    assert q["ok"] is False
    assert q["decision"] == "QUARANTINE"

    a = evaluate_harness_tool_policy(
        permission_mode="cloud-dispatch",
        tool_class="write_workspace",
        cloud_dispatch_approval="1",
    )
    assert a["ok"] is True
    assert a["decision"] == "ALLOW"


def test_mcdc_requires_maintenance_destructive_filesystem():
    """maintenance: destructive_filesystem is requires_approval, not in allows."""
    q = evaluate_harness_tool_policy(
        permission_mode="maintenance",
        tool_class="destructive_filesystem",
        cloud_dispatch_approval="",
    )
    assert q["ok"] is False
    assert q["decision"] == "QUARANTINE"

    a = evaluate_harness_tool_policy(
        permission_mode="maintenance",
        tool_class="destructive_filesystem",
        cloud_dispatch_approval="on",
    )
    assert a["ok"] is True
    assert a["decision"] == "ALLOW"


def test_mcdc_block_preempts_approval_secrets_maintenance():
    """secrets_or_credentials blocked in maintenance even with approval set."""
    r = evaluate_harness_tool_policy(
        permission_mode="maintenance",
        tool_class="secrets_or_credentials",
        cloud_dispatch_approval="1",
    )
    assert r["ok"] is False
    assert r["decision"] == "DENY"
    assert "blocked" in r["reason"].lower()


def test_mcdc_unlisted_tool_class_observe_execute_tests():
    """observe does not allow execute_tests; not blocked -> final DENY unlisted."""
    r = evaluate_harness_tool_policy(permission_mode="observe", tool_class="execute_tests")
    assert r["ok"] is False
    assert r["decision"] == "DENY"
    assert "not listed" in r["reason"].lower()


def test_mcdc_observe_write_workspace_blocked():
    """write_workspace in blocks for observe."""
    r = evaluate_harness_tool_policy(permission_mode="observe", tool_class="write_workspace")
    assert r["ok"] is False
    assert r["decision"] == "DENY"
    assert "blocked" in r["reason"].lower()


def test_mcdc_workspace_write_allows_execute_tests_without_extra_approval():
    """execute_tests in allows for workspace-write; not requires branch."""
    r = evaluate_harness_tool_policy(
        permission_mode="workspace-write",
        tool_class="execute_tests",
        cloud_dispatch_approval="",
    )
    assert r["ok"] is True
    assert r["decision"] == "ALLOW"


@pytest.mark.parametrize(
    ("command", "execute", "expected"),
    [
        ("loop-dispatch", False, "read"),
        ("loop-dispatch", True, "network_or_cloud"),
        ("testing-cli", False, "read"),
        ("testing-cli", True, "execute_tests"),
        ("code-roundtrip", False, "read"),
        ("code-roundtrip", True, "execute_tests"),
        ("code-packet", False, "read"),
        ("code-packet", True, "read"),
        ("skill-tools", False, "read"),
        ("replay", False, "execute_tests"),
        ("project-scaffold", False, "write_workspace"),
        ("unknown-cmd", False, "read"),
    ],
)
def test_mcdc_geoseal_command_to_tool_class(command: str, execute: bool, expected: str) -> None:
    assert geoseal_command_to_tool_class(command, execute=execute) == expected


def test_mcdc_permission_mode_normalization():
    r = evaluate_harness_tool_policy(permission_mode="  OBSERVE ", tool_class="read")
    assert r["ok"] is True
    assert r["permission_mode"] == "observe"


def test_mcdc_tool_class_normalization():
    r = evaluate_harness_tool_policy(permission_mode="observe", tool_class=" READ ")
    assert r["ok"] is True
    assert r["tool_class"] == "read"


def test_mcdc_approval_rejects_non_truthy_tokens():
    r = evaluate_harness_tool_policy(
        permission_mode="workspace-write",
        tool_class="network_or_cloud",
        cloud_dispatch_approval="0",
    )
    assert r["ok"] is False
    assert r["decision"] == "QUARANTINE"

    r2 = evaluate_harness_tool_policy(
        permission_mode="workspace-write",
        tool_class="network_or_cloud",
        cloud_dispatch_approval="maybe",
    )
    assert r2["ok"] is False
    assert r2["decision"] == "QUARANTINE"
