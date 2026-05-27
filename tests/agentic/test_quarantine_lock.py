from src.agentic.dcp import (
    CompletionGate,
    GoalSpec,
    ToolEntry,
    ToolScope,
    TrustState,
    create_dcp,
)
from src.agentic.quarantine_lock import (
    SCHEMA_VERSION,
    QuarantineLockPolicy,
    apply_quarantine_lock_to_dcp,
    create_quarantine_lock,
)


def test_allow_receipt_does_not_lock_or_cap_resources() -> None:
    receipt = create_quarantine_lock("ALLOW", suspicion=0.05, harmonic_cost=1.1)

    assert receipt.schema_version == SCHEMA_VERSION
    assert receipt.mode == "normal"
    assert receipt.locked is False
    assert receipt.block_execution is False
    assert receipt.token_budget is None
    assert receipt.allowed_tool_classes == ("*",)
    assert receipt.time_dilation_factor == 1


def test_review_is_blocked_inspect_only_without_full_lockout() -> None:
    receipt = create_quarantine_lock("REVIEW", suspicion=0.45, harmonic_cost=2.0)

    assert receipt.mode == "review"
    assert receipt.locked is False
    assert receipt.block_execution is True
    assert receipt.isolate is False
    assert receipt.model_tier == "free_or_local_only"
    assert receipt.token_budget == 512
    assert "verify" in receipt.allowed_tool_classes
    assert "network" in receipt.blocked_tool_classes
    assert receipt.time_dilation_factor > 1


def test_quarantine_is_lockout_with_short_timeout_and_free_tier() -> None:
    receipt = create_quarantine_lock(
        "QUARANTINE",
        suspicion=0.72,
        harmonic_cost=5.5,
        reasons=["prompt_injection_pattern"],
    )

    assert receipt.mode == "quarantine_lock"
    assert receipt.locked is True
    assert receipt.block_execution is True
    assert receipt.isolate is True
    assert receipt.model_tier == "free_or_local_only"
    assert receipt.token_budget == 128
    assert receipt.timeout_seconds == 15
    assert receipt.ttl_seconds == 86_400
    assert "prompt_injection_pattern" in receipt.reasons


def test_confirmed_malicious_upgrades_soft_decision_to_quarantine_lock() -> None:
    receipt = create_quarantine_lock(
        "ALLOW",
        suspicion=0.2,
        harmonic_cost=1.2,
        confirmed_malicious=True,
    )

    assert receipt.decision == "QUARANTINE"
    assert receipt.mode == "quarantine_lock"
    assert receipt.locked is True
    assert "confirmed_malicious_upgraded_to_quarantine_lock" in receipt.reasons


def test_deny_is_terminal_closed_state_with_no_tools() -> None:
    receipt = create_quarantine_lock("DENY", suspicion=0.99, harmonic_cost=9.0)

    assert receipt.mode == "deny_closed"
    assert receipt.locked is True
    assert receipt.token_budget == 16
    assert receipt.timeout_seconds == 1
    assert receipt.allowed_tool_classes == ()
    assert receipt.blocked_tool_classes == ("*",)


def test_time_dilation_is_bounded_and_deterministic_by_pressure() -> None:
    policy = QuarantineLockPolicy(max_time_dilation_factor=9)
    low = create_quarantine_lock(
        "QUARANTINE", suspicion=0.1, harmonic_cost=1.0, policy=policy
    )
    high = create_quarantine_lock(
        "QUARANTINE", suspicion=0.9, harmonic_cost=8.0, policy=policy
    )
    malicious = create_quarantine_lock(
        "QUARANTINE",
        suspicion=0.1,
        harmonic_cost=1.0,
        confirmed_malicious=True,
        policy=policy,
    )

    assert 1 < low.time_dilation_factor <= high.time_dilation_factor <= 9
    assert malicious.time_dilation_factor == 9


def test_apply_quarantine_lock_restricts_dcp_tools_and_timeouts() -> None:
    dcp = create_dcp(
        "use tools after suspicious input",
        GoalSpec(description="prove lock applies", success_evidence=["tests pass"]),
    )
    dcp.tools = [
        ToolEntry(name="read"),
        ToolEntry(name="shell"),
        ToolEntry(name="deploy"),
    ]
    dcp.completion_gates = [
        CompletionGate(
            id="unit", description="unit tests", command="pytest", timeout_seconds=120
        )
    ]
    receipt = create_quarantine_lock("QUARANTINE", suspicion=0.8, harmonic_cost=4.0)

    apply_quarantine_lock_to_dcp(dcp, receipt)

    assert "quarantine_lock:quarantine_lock" in dcp.processing_space.constraints
    assert "token_budget:128" in dcp.processing_space.constraints
    assert dcp.tool("read").scope == ToolScope.RESTRICTED
    assert dcp.tool("read").trust_state == TrustState.QUARANTINE
    assert dcp.tool("shell").scope == ToolScope.DENIED
    assert dcp.tool("deploy").scope == ToolScope.DENIED
    assert dcp.completion_gates[0].timeout_seconds == 15


def test_apply_deny_lock_denies_every_dcp_tool() -> None:
    dcp = create_dcp("deny all", GoalSpec(description="closed state"))
    dcp.tools = [ToolEntry(name="read"), ToolEntry(name="verify")]
    dcp.completion_gates = [
        CompletionGate(
            id="unit", description="unit tests", command="pytest", timeout_seconds=120
        )
    ]

    apply_quarantine_lock_to_dcp(dcp, create_quarantine_lock("DENY"))

    assert all(tool.scope == ToolScope.DENIED for tool in dcp.tools)
    assert all(tool.trust_state == TrustState.DENY for tool in dcp.tools)
    assert dcp.completion_gates[0].timeout_seconds == 1
