"""Tests for the Deploy Condition Packet (DCP) schema."""

import json
import time

import pytest

from src.agentic.dcp import (
    BENCHMARK_COMBO,
    CLEAN_PR_COMBO,
    CompletionGate,
    ComputeTarget,
    ContextPolicy,
    DeployConditionPacket,
    DeployTarget,
    DeployTargetKind,
    Expectation,
    FailureSemantics,
    FullnessStage,
    GateResult,
    GoalSpec,
    KnownFailure,
    ProcessingSpace,
    PushPullRules,
    RecoveryRoute,
    RepoState,
    SecretsBoundary,
    StorageState,
    ToolEntry,
    ToolMove,
    ToolCombo,
    ToolScope,
    TrustLevel,
    TrustState,
    create_dcp,
    validate_dcp,
)

# ─────────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────────


def test_create_dcp_stamps_uuid_and_timestamp():
    dcp = create_dcp("fix lint failures", GoalSpec("lint passes clean"))
    assert len(dcp.packet_id) == 36  # UUID4 format
    assert dcp.created_at <= time.time()
    assert dcp.schema_version == "dcp-v1"


def test_create_dcp_sets_intent_and_goal():
    dcp = create_dcp("ship feature X", GoalSpec("all gates green", success_evidence=["npm test"]))
    assert dcp.intent == "ship feature X"
    assert dcp.goal.description == "all gates green"
    assert "npm test" in dcp.goal.success_evidence


def test_two_dcps_have_different_ids():
    a = create_dcp("task a", GoalSpec("done a"))
    b = create_dcp("task b", GoalSpec("done b"))
    assert a.packet_id != b.packet_id


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────


def _base_dcp() -> DeployConditionPacket:
    dcp = create_dcp("run tests", GoalSpec("tests pass"))
    dcp.completion_gates = [CompletionGate(id="test", description="pytest", command="python -m pytest tests/ -x")]
    return dcp


def test_valid_dcp_has_no_errors():
    assert validate_dcp(_base_dcp()) == []


def test_validate_rejects_empty_intent():
    dcp = _base_dcp()
    dcp.intent = "   "
    errors = validate_dcp(dcp)
    assert any("intent" in e for e in errors)


def test_validate_rejects_empty_goal_description():
    dcp = _base_dcp()
    dcp.goal.description = ""
    errors = validate_dcp(dcp)
    assert any("goal" in e for e in errors)


def test_validate_rejects_missing_gates():
    dcp = create_dcp("run tests", GoalSpec("tests pass"))
    errors = validate_dcp(dcp)
    assert any("gate" in e for e in errors)


def test_validate_rejects_orphan_recovery_route():
    dcp = _base_dcp()
    dcp.recovery_routes = [RecoveryRoute(on_gate_id="nonexistent", action="fix it")]
    errors = validate_dcp(dcp)
    assert any("nonexistent" in e for e in errors)


def test_validate_rejects_denied_tool_with_allowed_scope():
    dcp = _base_dcp()
    dcp.tools = [ToolEntry(name="shell", scope=ToolScope.ALLOWED, trust_state=TrustState.DENY)]
    errors = validate_dcp(dcp)
    assert any("shell" in e for e in errors)


def test_validate_catches_context_policy_overlap():
    with pytest.raises(ValueError, match="repo_map"):
        ContextPolicy(active_keys=["repo_map"], compactable=["repo_map"])


# ─────────────────────────────────────────────────────────────────────────────
# Completion gates
# ─────────────────────────────────────────────────────────────────────────────


def test_is_complete_only_when_all_required_gates_pass():
    dcp = _base_dcp()
    dcp.completion_gates[0].result = GateResult.PASS
    assert dcp.is_complete()


def test_is_not_complete_with_pending_required_gate():
    dcp = _base_dcp()
    assert not dcp.is_complete()


def test_is_not_complete_with_failed_required_gate():
    dcp = _base_dcp()
    dcp.completion_gates[0].result = GateResult.FAIL
    assert not dcp.is_complete()


def test_optional_gate_failure_does_not_block_completion():
    dcp = _base_dcp()
    dcp.completion_gates[0].result = GateResult.PASS
    dcp.completion_gates.append(
        CompletionGate(id="docs", description="docs build", command="make docs", required=False, result=GateResult.FAIL)
    )
    assert dcp.is_complete()


def test_required_gates_pending_returns_only_pending():
    dcp = _base_dcp()
    dcp.completion_gates.append(
        CompletionGate(id="lint", description="lint", command="npm run lint", result=GateResult.PASS)
    )
    pending = dcp.required_gates_pending()
    assert len(pending) == 1
    assert pending[0].id == "test"


def test_required_gates_failed_returns_only_failed():
    dcp = _base_dcp()
    dcp.completion_gates[0].result = GateResult.FAIL
    failed = dcp.required_gates_failed()
    assert len(failed) == 1 and failed[0].id == "test"


# ─────────────────────────────────────────────────────────────────────────────
# Recovery routes
# ─────────────────────────────────────────────────────────────────────────────


def test_recovery_for_returns_matching_routes():
    dcp = _base_dcp()
    dcp.recovery_routes = [
        RecoveryRoute(on_gate_id="test", action="run black and re-test", max_retries=2),
        RecoveryRoute(on_gate_id="lint", action="run format"),
    ]
    routes = dcp.recovery_for("test")
    assert len(routes) == 1
    assert routes[0].action == "run black and re-test"


def test_recovery_for_unknown_gate_returns_empty():
    dcp = _base_dcp()
    assert dcp.recovery_for("no_such_gate") == []


# ─────────────────────────────────────────────────────────────────────────────
# Tool trust downgrade (source quarantine)
# ─────────────────────────────────────────────────────────────────────────────


def test_tool_downgrade_allow_to_quarantine():
    tool = ToolEntry(name="swe_bench", trust_state=TrustState.ALLOW)
    downgraded = tool.downgrade()
    assert downgraded.trust_state == TrustState.QUARANTINE
    assert tool.trust_state == TrustState.ALLOW  # original unchanged


def test_tool_downgrade_chain_to_deny():
    tool = ToolEntry(name="flaky_source", trust_state=TrustState.ESCALATE)
    assert tool.downgrade().trust_state == TrustState.DENY


def test_tool_downgrade_deny_stays_deny():
    tool = ToolEntry(name="bad_source", trust_state=TrustState.DENY)
    assert tool.downgrade().trust_state == TrustState.DENY


def test_downgrade_tool_by_name_on_dcp():
    dcp = _base_dcp()
    dcp.tools = [ToolEntry(name="shell", trust_state=TrustState.ALLOW)]
    result = dcp.downgrade_tool("shell")
    assert result is True
    assert dcp.tools[0].trust_state == TrustState.QUARANTINE


def test_downgrade_tool_unknown_name_returns_false():
    dcp = _base_dcp()
    assert dcp.downgrade_tool("nonexistent") is False


def test_tool_lookup_by_name():
    dcp = _base_dcp()
    dcp.tools = [ToolEntry(name="github")]
    assert dcp.tool("github") is not None
    assert dcp.tool("missing") is None


# ─────────────────────────────────────────────────────────────────────────────
# Watcher receipt — must be written before push
# ─────────────────────────────────────────────────────────────────────────────


def test_stamp_watcher_receipt_before_push():
    dcp = _base_dcp()
    t_before_stamp = time.time()
    receipt = dcp.stamp_watcher_receipt(
        operation_type="github_pr",
        watch_command="gh pr view 42 --json state,statusCheckRollup",
        on_success="sync_main_and_prune_branch",
        on_failure="fetch_failed_job_log",
    )
    assert receipt.written_at >= t_before_stamp
    assert dcp.watcher_receipt is receipt
    assert receipt.operation_id == dcp.packet_id
    assert receipt.fullness_stage == FullnessStage.LOCAL_CHANGE


def test_advance_fullness_updates_receipt_stage():
    dcp = _base_dcp()
    dcp.stamp_watcher_receipt("npm_publish", "npm view mypackage@latest")
    dcp.advance_fullness(FullnessStage.CI_RUNNING)
    assert dcp.watcher_receipt.fullness_stage == FullnessStage.CI_RUNNING


def test_advance_fullness_to_verified_sets_completed_at():
    dcp = _base_dcp()
    dcp.stamp_watcher_receipt("deploy", "curl health-check")
    dcp.advance_fullness(FullnessStage.VERIFIED)
    assert dcp.watcher_receipt.completed_at is not None
    assert dcp.watcher_receipt.final_stage == FullnessStage.VERIFIED


def test_receipt_written_at_precedes_any_simulated_action():
    dcp = _base_dcp()
    receipt = dcp.stamp_watcher_receipt("github_pr", "gh pr view 1 --json state")
    # simulate some work time has passed
    time_after_work = time.time()
    assert receipt.written_at <= time_after_work


def test_advance_fullness_without_receipt_is_safe():
    dcp = _base_dcp()
    dcp.advance_fullness(FullnessStage.PUSHED)  # no receipt attached — must not crash


# ─────────────────────────────────────────────────────────────────────────────
# Tool chain combos
# ─────────────────────────────────────────────────────────────────────────────


def test_tool_move_cancel_window_fields():
    move = ToolMove(
        name="test",
        cancel_condition="lint_failure_detected_before_frame_12",
        cancel_into="triage_lint_error",
    )
    assert move.cancel_condition is not None
    assert move.cancel_into == "triage_lint_error"


def test_tool_combo_validate_chain_clean():
    combo = ToolCombo(
        name="minimal",
        description="two-step chain",
        moves=[
            ToolMove(name="step1", produces=["artifact_a"]),
            ToolMove(name="step2", requires=["artifact_a"]),
        ],
    )
    assert combo.validate_chain() == []


def test_tool_combo_validate_chain_detects_broken_link():
    combo = ToolCombo(
        name="broken",
        description="step2 needs something step1 doesn't produce",
        moves=[
            ToolMove(name="step1", produces=["artifact_a"]),
            ToolMove(name="step2", requires=["artifact_b"]),  # never produced
        ],
    )
    errors = combo.validate_chain()
    assert len(errors) == 1
    assert "artifact_b" in errors[0]


def test_frame_advantage_counts_as_produced():
    combo = ToolCombo(
        name="frame_adv",
        description="frame_advantage is also available downstream",
        moves=[
            ToolMove(name="build_context", frame_advantage=["repo_map"]),
            ToolMove(name="pick_task", requires=["repo_map"]),
        ],
    )
    assert combo.validate_chain() == []


def test_clean_pr_combo_has_valid_chain():
    assert CLEAN_PR_COMBO.validate_chain() == []


def test_benchmark_combo_has_valid_chain():
    assert BENCHMARK_COMBO.validate_chain() == []


def test_clean_pr_combo_move_names():
    move_names = [m.name for m in CLEAN_PR_COMBO.moves]
    assert "format" in move_names
    assert "lint" in move_names
    assert "test" in move_names
    assert "pr_create" in move_names
    assert "watch_ci" in move_names


# ─────────────────────────────────────────────────────────────────────────────
# Serialization round-trip
# ─────────────────────────────────────────────────────────────────────────────


def _full_dcp() -> DeployConditionPacket:
    dcp = create_dcp(
        "deploy feature to PR",
        GoalSpec(
            description="PR created, CI green, no secrets",
            success_evidence=["gh pr view --json state | jq .state == OPEN"],
            failure_modes=["lint failure", "test timeout"],
        ),
    )
    dcp.expectations = [Expectation("branch is clean", verified=True, verification_command="git status")]
    dcp.known_failures = [KnownFailure(id="flaky-e2e", description="E2E suite flaky on Windows", workaround="skip e2e")]
    dcp.tools = [
        ToolEntry(
            name="github",
            scope=ToolScope.ALLOWED,
            trust_level=TrustLevel.VERIFIED_PRIMARY,
            trust_state=TrustState.ALLOW,
            source_roots=["https://github.com"],
            failure_semantics=FailureSemantics(
                tool_failure="gh CLI may be misconfigured",
                source_contract_failure="GitHub API changed",
                source_integrity_failure="GitHub may be compromised",
            ),
        )
    ]
    dcp.processing_space = ProcessingSpace(compute=ComputeTarget.LOCAL, constraints=["no root"])
    dcp.storage_state = StorageState(
        repo_state=RepoState.DIRTY,
        branch="feat/dcp",
        has_uncommitted_changes=True,
        secrets_boundary=SecretsBoundary.LOCAL_ONLY,
        artifact_paths=["artifacts/dcp_test.json"],
    )
    dcp.context_policy = ContextPolicy(
        active_keys=["goal", "known_failures"],
        compactable=["prior_test_output"],
        pull_on_demand=["full_repo_map"],
    )
    dcp.deploy_target = DeployTarget(kind=DeployTargetKind.PR, branch="feat/dcp", pr_number=None)
    dcp.push_pull_rules = PushPullRules(
        can_push=["branch"],
        must_stay_local=[".env", "secrets/"],
        evidence_to_pull=["ci_log", "pr_status"],
    )
    dcp.completion_gates = [
        CompletionGate(id="lint", description="lint clean", command="npm run lint", required=True),
        CompletionGate(id="test", description="tests pass", command="python -m pytest tests/ -x", required=True),
    ]
    dcp.recovery_routes = [
        RecoveryRoute(on_gate_id="lint", action="npm run format && re-lint", max_retries=1),
        RecoveryRoute(
            on_gate_id="test",
            action="fetch failing test output",
            cancel_condition="known_flaky_detected",
            cancel_into="skip_flaky_rerun",
        ),
    ]
    dcp.stamp_watcher_receipt(
        operation_type="github_pr",
        watch_command="gh pr view --json state,statusCheckRollup",
        on_success="sync_main",
        on_failure="fetch_failed_log",
    )
    return dcp


def test_serialization_round_trip():
    original = _full_dcp()
    as_dict = original.to_dict()
    restored = DeployConditionPacket.from_dict(as_dict)

    assert restored.packet_id == original.packet_id
    assert restored.intent == original.intent
    assert restored.goal.description == original.goal.description
    assert len(restored.expectations) == len(original.expectations)
    assert restored.expectations[0].verified is True
    assert len(restored.known_failures) == 1
    assert restored.known_failures[0].id == "flaky-e2e"
    assert len(restored.tools) == 1
    assert restored.tools[0].trust_state == TrustState.ALLOW
    assert restored.processing_space.compute == ComputeTarget.LOCAL
    assert restored.storage_state.repo_state == RepoState.DIRTY
    assert restored.storage_state.branch == "feat/dcp"
    assert restored.context_policy.active_keys == ["goal", "known_failures"]
    assert restored.deploy_target.kind == DeployTargetKind.PR
    assert restored.push_pull_rules.must_stay_local == [".env", "secrets/"]
    assert len(restored.completion_gates) == 2
    assert len(restored.recovery_routes) == 2
    assert restored.watcher_receipt is not None
    assert restored.watcher_receipt.operation_type == "github_pr"


def test_json_round_trip_is_valid_json():
    dcp = _full_dcp()
    text = dcp.to_json()
    parsed = json.loads(text)  # must not raise
    assert parsed["schema_version"] == "dcp-v1"
    assert "completion_gates" in parsed
    assert "watcher_receipt" in parsed


def test_from_json_is_inverse_of_to_json():
    original = _full_dcp()
    restored = DeployConditionPacket.from_json(original.to_json())
    assert restored.packet_id == original.packet_id
    assert restored.is_complete() == original.is_complete()


# ─────────────────────────────────────────────────────────────────────────────
# Fullness stage ordering
# ─────────────────────────────────────────────────────────────────────────────


def test_fullness_stages_are_strings():
    for stage in FullnessStage:
        assert isinstance(stage.value, str)


def test_verified_stage_is_terminal():
    dcp = _base_dcp()
    dcp.stamp_watcher_receipt("ci", "gh run view")
    dcp.advance_fullness(FullnessStage.VERIFIED)
    r = dcp.watcher_receipt
    assert r.final_stage == FullnessStage.VERIFIED
    assert r.completed_at is not None
