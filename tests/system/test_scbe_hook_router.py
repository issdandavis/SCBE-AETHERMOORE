import json
from pathlib import Path

from scripts.system import scbe_hook_router


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "src").mkdir()
    return tmp_path


def test_session_start_writes_state_and_context(tmp_path):
    root = _repo(tmp_path)

    code, output, use_stdout = scbe_hook_router.handle_event(
        "SessionStart", {"cwd": str(root)}, root
    )

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

    code, output, use_stdout = scbe_hook_router.handle_event(
        "PreToolUse", payload, root
    )

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

    code, output, use_stdout = scbe_hook_router.handle_event(
        "PreToolUse", payload, root
    )

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

    code, _output, _use_stdout = scbe_hook_router.handle_event(
        "PostToolUse", payload, root
    )

    assert code == 0
    receipt_line = (
        (root / ".scbe" / "ops" / "tool_receipts.jsonl")
        .read_text(encoding="utf-8")
        .strip()
    )
    receipt = json.loads(receipt_line)
    assert receipt["payload"]["tool_input"]["api_key"] == "<redacted>"
    assert "sk-testsecret" not in receipt_line


def test_user_prompt_adds_route_context(tmp_path):
    root = _repo(tmp_path)
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "user_prompt": "publish and deploy this release",
    }

    code, output, use_stdout = scbe_hook_router.handle_event(
        "UserPromptSubmit", payload, root
    )

    assert code == 0
    assert use_stdout is True
    assert "release-risk" in output["additionalContext"]


def test_precompact_and_stop_write_session_receipts(tmp_path):
    root = _repo(tmp_path)

    compact_code, compact_output, _ = scbe_hook_router.handle_event(
        "PreCompact", {}, root
    )
    stop_code, stop_output, _ = scbe_hook_router.handle_event("Stop", {}, root)

    assert compact_code == 0
    assert "compact_state.json" in compact_output["additionalContext"]
    assert stop_code == 0
    assert stop_output["decision"] == "approve"
    assert (root / ".scbe" / "session" / "compact_state.json").exists()
    assert (root / ".scbe" / "session" / "final_receipt.json").exists()
