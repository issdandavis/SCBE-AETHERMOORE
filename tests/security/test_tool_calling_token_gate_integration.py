from __future__ import annotations

import pytest

from src.ai_orchestration.tool_calling import (
    ExecutionStatus,
    PermissionLevel,
    ToolCallingSystem,
)


@pytest.mark.asyncio
async def test_tool_executor_keeps_permission_denial_before_token_gate() -> None:
    system = ToolCallingSystem()

    result = await system.call_tool(
        "agent-a",
        "guest",
        "filesystem",
        {"operation": "exists", "path": "."},
        context={"session_goal": "inspect local docs"},
    )

    assert result.status == ExecutionStatus.DENIED
    assert result.error == "Permission denied"
    assert "token_tool_gate" not in result.metadata


@pytest.mark.asyncio
async def test_tool_executor_denies_token_gated_credential_harvest() -> None:
    system = ToolCallingSystem()
    system.grant_role_permission("researcher", "filesystem", PermissionLevel.READ)

    result = await system.call_tool(
        "agent-a",
        "researcher",
        "filesystem",
        {
            "operation": "read",
            "path": "browser profile saved login entries with decrypted password fields",
        },
        context={"session_goal": "review browser security"},
    )

    assert result.status == ExecutionStatus.DENIED
    assert "Token tool gate denied call" in str(result.error)
    assert result.metadata["token_tool_gate"]["intent_label"] == "credential_harvest"
    assert result.metadata["token_tool_gate"]["action"] == "deny"


@pytest.mark.asyncio
async def test_tool_executor_routes_sandbox_action_to_pending_confirmation() -> None:
    system = ToolCallingSystem()
    system.grant_role_permission("researcher", "filesystem", PermissionLevel.READ)

    result = await system.call_tool(
        "agent-a",
        "researcher",
        "filesystem",
        {"operation": "exists", "path": "."},
        context={"session_goal": "inspect local docs"},
    )

    assert result.status == ExecutionStatus.PENDING
    assert result.metadata["requires_confirmation"] is True
    assert result.metadata["token_tool_gate"]["action"] == "sandbox"


@pytest.mark.asyncio
async def test_tool_executor_can_run_sandbox_allowed_call() -> None:
    system = ToolCallingSystem()
    system.grant_role_permission("researcher", "filesystem", PermissionLevel.READ)

    result = await system.call_tool(
        "agent-a",
        "researcher",
        "filesystem",
        {"operation": "exists", "path": "."},
        context={
            "session_goal": "inspect local docs",
            "allow_sandbox_execution": True,
        },
    )

    assert result.status == ExecutionStatus.COMPLETED
    assert result.result == {"exists": True}
