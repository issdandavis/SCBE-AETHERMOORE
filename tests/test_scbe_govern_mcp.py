"""scbe-govern MCP server: the governed desktop-action plane (allowlist + destructive screen + L13 +
confirm + sealed receipts) exposed as MCP tools, with a pluggable executor seam for a real driver.

The load-bearing tests: the gate's decisions are honored through the server surface, a destructive
command is REFUSED, the seal chain stays intact, and the executor seam delegates an ALLOWED action to
the configured executor while the governance is unchanged.
"""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location("scbe_govern_mcp", ROOT / "src" / "mcp" / "scbe_govern_mcp.py")
M = importlib.util.module_from_spec(_spec)
sys.modules["scbe_govern_mcp"] = M
_spec.loader.exec_module(M)


def test_safe_action_allowed_and_sealed():
    r = M._govern_action("open_app", {"app": "terminal"})
    assert r["decision"] == "ALLOWED"
    assert r["seal"] and len(r["seal"]) == 64  # sha-256 hex


def test_destructive_command_is_refused():
    r = M._govern_action("run_allowed_command", {"command": "delete every file on the drive"})
    assert r["decision"] == "REFUSED"
    assert "next" in r and "performed" in r["next"]


def test_guarded_needs_confirm_then_allows():
    assert M._govern_action("save_file", {"path": "x", "content": "y"})["decision"] == "NEEDS_CONFIRM"
    assert M._govern_action("save_file", {"path": "x", "content": "y"}, confirm="approved")["decision"] == "ALLOWED"


def test_denied_and_unknown():
    assert M._govern_action("shutdown", {})["decision"] == "DENIED"
    assert M._govern_action("no_such_action")["decision"] == "NO_ACTION"


def test_audit_log_chain_holds():
    log = M._audit_log()
    assert log["chain_ok"] is True
    assert log["hops"] >= 1


def test_executor_seam_delegates_allowed_actions(monkeypatch):
    # the seam where a real driver (Cua) wires in: an ALLOWED action is delegated to executor(name, params)
    # while the allowlist/destructive/seal governance is unchanged.
    calls = []

    def fake_executor(name, params):
        calls.append((name, params))
        return "performed:%s" % name

    monkeypatch.setattr(M, "_load_executor", lambda: fake_executor)
    reg = M._build_registry()  # a fresh registry wired to the fake executor
    rec = reg.invoke("open_app", {"app": "terminal"})
    assert rec["decision"] == "ALLOWED" and rec["result"] == "performed:open_app"
    assert calls == [("open_app", {"app": "terminal"})]
    # the destructive screen STILL fires even with a real executor (governance is in front of the hands)
    blocked = reg.invoke("run_allowed_command", {"command": "format the disk and wipe everything"})
    assert blocked["decision"] == "REFUSED"


def test_load_executor_none_and_bad(monkeypatch):
    monkeypatch.delenv("SCBE_DESKTOP_EXECUTOR", raising=False)
    assert M._load_executor() is None
    monkeypatch.setenv("SCBE_DESKTOP_EXECUTOR", "no.such.module:nope")
    with pytest.raises(SystemExit):
        M._load_executor()


def test_all_tool_outputs_are_valid_json():
    for payload in (
        M.list_governed_actions(),
        M.govern_action("open_app", {"app": "terminal"}),
        M.action_channels("open_app"),
        M.audit_log(),
    ):
        json.loads(payload)


def test_registration_surface():
    assert M._HAVE_MCP is True
    tools = {t.name for t in asyncio.run(M.mcp.list_tools())}
    assert tools == {"list_governed_actions", "govern_action", "action_channels", "audit_log"}
    resources = {str(r.uri) for r in asyncio.run(M.mcp.list_resources())}
    assert resources == {"scbe://governed-actions"}


def test_self_test_passes():
    assert M._self_test() == 0
