"""Tests for governed GitHub/Copilot DCP routes."""

from src.agentic.dcp import DeployTargetKind, GateResult, TrustLevel, TrustState, validate_dcp
from src.agentic.dcp_routes import (
    GITHUB_COPILOT_PR_COMBO,
    OperationPiece,
    RouteSlot,
    TETRIS_TREE_PR_PIECES,
    TETRIS_TREE_PR_SLOTS,
    approved_agentic_tools,
    copilot_command_route,
    create_github_pr_dcp,
    github_command_route,
    lock_operation_piece,
    route_packet_for_docs,
    route_tetris_tree,
)


def test_approved_tools_include_github_mcp_and_restricted_copilot():
    tools = {tool.name: tool for tool in approved_agentic_tools(include_copilot=True)}

    assert "github-cli" in tools
    assert "codex-github-mcp" in tools
    assert "github-copilot" in tools
    assert tools["github-copilot"].trust_level == TrustLevel.VERIFIED_SECONDARY
    assert tools["github-copilot"].trust_state == TrustState.ALLOW
    assert tools["github-copilot"].scope.value == "restricted"
    assert any("gh-copilot" in source for source in tools["github-copilot"].source_roots)


def test_copilot_can_be_excluded_for_no_external_ai_routes():
    tool_names = {tool.name for tool in approved_agentic_tools(include_copilot=False)}
    assert "github-copilot" not in tool_names
    assert "github-cli" in tool_names


def test_github_command_route_contains_push_pr_watch_and_cleanup_commands():
    route = github_command_route(branch="feat/test-route", title="feat(agentic): test route")
    joined = "\n".join(route.commands)

    assert "git switch -c feat/test-route" in joined
    assert "git push -u origin feat/test-route" in joined
    assert "gh pr create" in joined
    assert "gh pr view --json number,url,state,statusCheckRollup,mergeCommit" in joined
    assert "git push origin --delete feat/test-route" in joined


def test_copilot_command_route_keeps_scbe_verification_after_suggestion():
    route = copilot_command_route(prompt="fix the failing lint")
    joined = "\n".join(route.commands)

    assert "gh extension install github/gh-copilot" in joined
    assert "gh copilot suggest" in joined
    assert "git diff --check HEAD" in joined
    assert "npm run lint" in joined
    assert "python -m pytest tests/agentic/test_dcp.py" in joined


def test_github_copilot_combo_validates():
    assert GITHUB_COPILOT_PR_COMBO.validate_chain() == []


def test_create_github_pr_dcp_has_watcher_before_dispatch_and_validates():
    dcp = create_github_pr_dcp(
        intent="fix a failing CI lane",
        branch="fix/example",
        title="fix(ci): example",
        test_commands=["python -m pytest tests/agentic/test_dcp_routes.py -q"],
    )

    assert validate_dcp(dcp) == []
    assert dcp.deploy_target.kind == DeployTargetKind.PR
    assert dcp.deploy_target.branch == "fix/example"
    assert dcp.watcher_receipt is not None
    assert dcp.watcher_receipt.operation_type == "github_pr"
    assert "statusCheckRollup" in dcp.watcher_receipt.watch_command
    assert dcp.is_complete() is False
    assert all(gate.result == GateResult.PENDING for gate in dcp.completion_gates)


def test_create_github_pr_dcp_marks_secrets_local_only():
    dcp = create_github_pr_dcp(
        intent="route with secrets protected",
        branch="feat/secrets-protected",
        title="feat(agentic): protect secrets",
        test_commands=[],
    )

    assert "CODEX_GITHUB_PERSONAL_ACCESS_TOKEN" in dcp.push_pull_rules.must_stay_local
    assert "config/connector_oauth/.env.connector.oauth" in dcp.push_pull_rules.must_stay_local
    assert any(tool.name == "codex-github-mcp" for tool in dcp.tools)


def test_route_packet_for_docs_is_serializable_and_contains_commands():
    packet = route_packet_for_docs(branch="feat/doc-route", title="feat(agentic): doc route")

    assert packet["dcp"]["deploy_target"]["kind"] == "pr"
    assert packet["github"]["name"] == "github_pr_commands"
    assert packet["copilot"]["name"] == "copilot_proposer_commands"
    assert any("gh pr create" in command for command in packet["github"]["commands"])
    assert all(decision["locked"] for decision in packet["tetris_tree"])


def test_lock_operation_piece_accepts_matching_geometry_and_tool():
    piece = OperationPiece(
        name="lint_piece",
        lane="verify",
        command="npm run lint",
        tool_name="shell",
        requires=["patch"],
        produces=["lint_report"],
        geometry_vector=(0.8, 0.9, 0.9),
        risk_score=0.1,
    )
    slot = RouteSlot(
        name="verify_slot",
        lane="gate",
        accepts=["verify"],
        available=["patch"],
        geometry_vector=(0.8, 0.95, 0.9),
        risk_capacity=0.25,
    )

    decision = lock_operation_piece(piece, slot, approved_agentic_tools())

    assert decision.locked is True
    assert decision.score >= 0.55
    assert decision.reasons == []


def test_lock_operation_piece_rejects_missing_artifacts_and_unapproved_tool():
    piece = OperationPiece(
        name="unsafe_piece",
        lane="publish",
        command="deploy everything",
        tool_name="unknown-tool",
        requires=["green_ci"],
        risk_score=0.9,
    )
    slot = RouteSlot(
        name="publish_slot",
        lane="github",
        accepts=["publish"],
        available=[],
        risk_capacity=0.25,
    )

    decision = lock_operation_piece(piece, slot, approved_agentic_tools())

    assert decision.locked is False
    assert any("missing required artifacts" in reason for reason in decision.reasons)
    assert any("not in the approved bucket" in reason for reason in decision.reasons)
    assert any("exceeds slot capacity" in reason for reason in decision.reasons)


def test_tetris_tree_route_locks_default_pr_sequence_in_order():
    decisions = route_tetris_tree(
        TETRIS_TREE_PR_PIECES,
        TETRIS_TREE_PR_SLOTS,
        approved_agentic_tools(include_copilot=True),
    )

    assert [decision.slot for decision in decisions] == ["inspect", "propose", "verify", "publish"]
    assert [decision.piece for decision in decisions] == [
        "git_status_piece",
        "copilot_candidate_piece",
        "local_gate_piece",
        "github_pr_piece",
    ]
    assert all(decision.locked for decision in decisions)


def test_tetris_tree_rejects_copilot_piece_when_copilot_not_in_bucket():
    decisions = route_tetris_tree(
        TETRIS_TREE_PR_PIECES,
        TETRIS_TREE_PR_SLOTS,
        approved_agentic_tools(include_copilot=False),
    )

    propose = next(decision for decision in decisions if decision.slot == "propose")
    assert propose.locked is False
    assert propose.piece == ""
