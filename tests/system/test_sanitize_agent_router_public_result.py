from scripts.system.sanitize_agent_router_public_result import REDACTED_TAIL, sanitize_result


def test_sanitizes_sensitive_stderr_tail() -> None:
    result = {
        "ok": True,
        "stderr_tail": "No SCBE_API_KEYS configured and HF_TOKEN missing",
        "result": {"text": "offline run accepted"},
    }

    sanitized = sanitize_result(result)

    assert sanitized["stderr_tail"] == REDACTED_TAIL
    assert sanitized["result"]["text"] == "offline run accepted"
    assert sanitized["public_sanitized"] is True


def test_leaves_normal_tail_for_public_diagnostics() -> None:
    result = {"ok": False, "stderr_tail": "agentbus_pipe failed in CI"}

    sanitized = sanitize_result(result)

    assert sanitized["stderr_tail"] == "agentbus_pipe failed in CI"


def test_sanitizes_credential_shaped_nested_keys() -> None:
    result = {"result": {"token": "abc123", "safe": "visible"}}

    sanitized = sanitize_result(result)

    assert sanitized["result"]["token"] == REDACTED_TAIL
    assert sanitized["result"]["safe"] == "visible"
