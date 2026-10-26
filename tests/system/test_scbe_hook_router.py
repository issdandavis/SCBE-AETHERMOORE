import json
from pathlib import Path
import re
import uuid

from scripts.system import scbe_hook_router


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "src").mkdir()
    return tmp_path


def test_session_start_writes_state_and_context(tmp_path):
    root = _repo(tmp_path)

    code, output, use_stdout = scbe_hook_router.handle_event("SessionStart", {"cwd": str(root)}, root)

    assert code == 0
    assert use_stdout is True
    assert "additionalContext" in output
    assert "SCBE_HOOK_BRIDGE" in output["additionalContext"]
    assert (root / ".scbe" / "session" / "state.json").exists()
    assert (root / ".scbe" / "ops" / "tool_receipts.jsonl").exists()


def test_pre_tool_use_blocks_destructive_shell(tmp_path):
    root = _repo(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "functions.shell_command",
        "tool_input": {"command": "git reset --hard HEAD"},
        "cwd": str(root),
    }

    code, output, use_stdout = scbe_hook_router.handle_event("PreToolUse", payload, root)

    assert code == 2
    assert use_stdout is False
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "destructive git operation" in output["systemMessage"]


def test_pre_tool_use_allows_read_only_command(tmp_path):
    root = _repo(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "functions.shell_command",
        "tool_input": {"command": "git status --short"},
        "cwd": str(root),
    }

    code, output, use_stdout = scbe_hook_router.handle_event("PreToolUse", payload, root)

    assert code == 0
    assert use_stdout is True
    assert output["continue"] is True


def test_receipts_scrub_secret_values(tmp_path):
    root = _repo(tmp_path)
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_name": "example",
        "tool_input": {"api_key": "sk-testsecretvalue1234567890", "safe": "value"},
    }

    code, _output, _use_stdout = scbe_hook_router.handle_event("PostToolUse", payload, root)

    assert code == 0
    receipt_line = (root / ".scbe" / "ops" / "tool_receipts.jsonl").read_text(encoding="utf-8").strip()
    receipt = json.loads(receipt_line)
    assert receipt["tool_input"]["api_key"] == "<redacted>"
    assert receipt["metadata"]["scbe"]["native_payload"]["tool_input"]["api_key"] == "<redacted>"
    assert "sk-testsecret" not in receipt_line


def test_receipt_uses_agenthook_envelope_and_normalized_shell_fields(tmp_path):
    root = _repo(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": "session-1",
        "correlation_id": "run-1",
        "tool_name": "functions.exec_command",
        "tool_input": {"cmd": "git status --short"},
        "cwd": str(root),
    }

    code, _output, _use_stdout = scbe_hook_router.handle_event("PreToolUse", payload, root)

    assert code == 0
    receipt = json.loads(
        (root / ".scbe" / "ops" / "tool_receipts.jsonl").read_text(encoding="utf-8").strip()
    )
    assert receipt["schema_version"] == 1
    uuid.UUID(receipt["event_id"])
    assert receipt["event_type"] == "PreToolUse"
    assert receipt["source"] == "scbe-hook-router"
    assert receipt["evidence_phase"] == "pre_commit"
    assert receipt["session_id"] == "session-1"
    assert receipt["correlation_id"] == "run-1"
    assert receipt["tool_name"] == "functions.exec_command"
    assert receipt["tool_input"] == {"cmd": "git status --short"}
    assert receipt["action"] == "execute"
    assert receipt["resource_kind"] == "shell"
    assert re.fullmatch(r"[0-9a-f]{64}", receipt["resource"]["command_sha256"])
    assert receipt["metadata"]["scbe"]["decision"] == "allow"
    assert receipt["metadata"]["scbe"]["tool_context"]["capability"] == "read"
    assert receipt["metadata"]["scbe"]["tool_context"]["geometry_authority"] == "telemetry_only"


def test_enforced_time_bounded_tool_requires_active_lease(tmp_path):
    root = _repo(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": "session-1",
        "tool_name": "functions.exec_command",
        "tool_input": {"cmd": "kaggle kernels list --mine"},
        "cwd": str(root),
        "scbe_context": {
            "permission_mode": "cloud-dispatch",
            "enforce_capability_window": True,
        },
    }

    code, output, use_stdout = scbe_hook_router.handle_event("PreToolUse", payload, root)

    assert code == 2
    assert use_stdout is False
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "hold_for_active_lease" in output["systemMessage"]


def test_enforced_time_bounded_tool_allows_active_matching_lease(tmp_path):
    root = _repo(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": "session-1",
        "tool_name": "functions.exec_command",
        "tool_input": {"cmd": "kaggle kernels list --mine"},
        "cwd": str(root),
        "scbe_context": {
            "permission_mode": "cloud-dispatch",
            "enforce_capability_window": True,
            "lease": {
                "not_before": "2026-01-01T00:00:00Z",
                "expires_at": "2027-01-01T00:00:00Z",
                "capabilities": ["network_or_cloud"],
            },
        },
    }

    code, output, use_stdout = scbe_hook_router.handle_event("PreToolUse", payload, root)

    assert code == 0
    assert use_stdout is True
    assert output["continue"] is True


def test_hash_chain_detects_tampering(tmp_path):
    root = _repo(tmp_path)
    log = root / ".scbe" / "ops" / "tool_receipts.jsonl"
    scbe_hook_router.handle_event("SessionStart", {"cwd": str(root)}, root)
    scbe_hook_router.handle_event("PostToolUse", {"tool_name": "read", "tool_input": {}}, root)

    report = scbe_hook_router.verify_receipt_chain(log)
    assert report["valid"] is True
    assert report["events"] == 2

    rows = log.read_text(encoding="utf-8").splitlines()
    changed = json.loads(rows[0])
    changed["metadata"]["scbe"]["decision"] = "deny"
    rows[0] = json.dumps(changed, sort_keys=True)
    log.write_text("\n".join(rows) + "\n", encoding="utf-8")

    tampered = scbe_hook_router.verify_receipt_chain(log)
    assert tampered["valid"] is False
    assert any("event hash mismatch" in error for error in tampered["errors"])


def test_stop_maps_to_agenthook_session_end(tmp_path):
    root = _repo(tmp_path)

    scbe_hook_router.handle_event("Stop", {}, root)

    receipt = json.loads(
        (root / ".scbe" / "ops" / "tool_receipts.jsonl").read_text(encoding="utf-8").strip()
    )
    assert receipt["event_type"] == "SessionEnd"
    assert receipt["metadata"]["scbe"]["native_event"] == "Stop"
    assert receipt["evidence_phase"] == "post_hoc"


def test_user_prompt_adds_route_context(tmp_path):
    root = _repo(tmp_path)
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "user_prompt": "publish and deploy this release",
    }

    code, output, use_stdout = scbe_hook_router.handle_event("UserPromptSubmit", payload, root)

    assert code == 0
    assert use_stdout is True
    assert "release-risk" in output["additionalContext"]


def test_precompact_and_stop_write_session_receipts(tmp_path):
    root = _repo(tmp_path)

    compact_code, compact_output, _ = scbe_hook_router.handle_event("PreCompact", {}, root)
    stop_code, stop_output, _ = scbe_hook_router.handle_event("Stop", {}, root)

    assert compact_code == 0
    assert "compact_state.json" in compact_output["additionalContext"]
    assert stop_code == 0
    assert stop_output["decision"] == "approve"
    assert (root / ".scbe" / "session" / "compact_state.json").exists()
    assert (root / ".scbe" / "session" / "final_receipt.json").exists()
