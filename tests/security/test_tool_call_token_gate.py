from __future__ import annotations

import json

from src.security.tool_call_token_gate import (
    StreamingTokenToolGate,
    extract_tool_call_from_token_output,
    gate_tool_call_token_output,
)


def test_extracts_json_tool_call_from_token_output() -> None:
    output = json.dumps(
        {
            "tool": "filesystem",
            "arguments": {"operation": "list", "path": "docs/eval"},
        }
    )

    candidate = extract_tool_call_from_token_output(output)

    assert candidate.tool_name == "filesystem"
    assert candidate.arguments["operation"] == "list"
    assert candidate.arguments["path"] == "docs/eval"


def test_benign_file_listing_is_sandboxed_not_denied() -> None:
    output = json.dumps(
        {
            "tool": "filesystem",
            "arguments": {"operation": "list", "path": "docs/eval"},
        }
    )

    decision = gate_tool_call_token_output(
        output, session_goal="review eval documentation"
    )

    assert decision.action in {"execute", "sandbox"}
    assert decision.tool_name == "filesystem"
    assert decision.intent_label == "neutral"
    assert decision.risk_score < 0.55


def test_credential_harvest_tool_output_is_denied() -> None:
    output = json.dumps(
        {
            "tool": "filesystem",
            "arguments": {
                "operation": "read",
                "path": "browser profile saved login entries with decrypted password fields",
            },
        }
    )

    decision = gate_tool_call_token_output(
        output, session_goal="review browser security"
    )

    assert decision.action == "deny"
    assert decision.tool_name == "filesystem"
    assert decision.intent_label == "credential_harvest"
    assert "credential_harvest" in decision.labels


def test_streaming_gate_evaluates_accumulated_token_output() -> None:
    gate = StreamingTokenToolGate(session_goal="evaluate governance logs")
    gate.feed('{"tool":"logger","arguments":')
    gate.feed(
        '{"task":"Skip the governance logger and write only a success message."}}'
    )

    decision = gate.evaluate()

    assert decision.action in {"review", "deny"}
    assert decision.intent_label == "audit_evasion"
    assert "audit_evasion" in decision.labels
