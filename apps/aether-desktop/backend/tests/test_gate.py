from backend.gate import govern
from backend.models import OperationOrigin, OperationRequest, OperationWorkspace


def _req(op: str, workspace_root: str | None = None, dry_run: bool = False) -> OperationRequest:
    ws = OperationWorkspace(id="test", root=workspace_root) if workspace_root else None
    return OperationRequest(
        op=op,
        args={},
        request_id="test-req-001",
        origin=OperationOrigin(kind="app", id="test-app"),
        workspace=ws,
        privacy="local_only",
        dry_run=dry_run,
    )


def test_echo_op_is_allowed():
    decision = govern(_req("echo"))
    assert decision.decision == "ALLOW"
    assert decision.zone == "GREEN"


def test_llm_chat_is_allowed():
    decision = govern(_req("llm.chat"))
    assert decision.decision == "ALLOW"
    assert decision.zone == "GREEN"


def test_terminal_shell_raw_is_denied():
    decision = govern(_req("terminal.shell.raw"))
    assert decision.decision == "DENY"
    assert decision.zone == "RED"


def test_unknown_op_is_quarantined():
    decision = govern(_req("unknown.made.up.op"))
    assert decision.decision == "QUARANTINE"


def test_dry_run_echo_is_still_allowed():
    decision = govern(_req("echo", dry_run=True))
    assert decision.decision == "ALLOW"


def test_workspace_path_is_checked_when_provided(tmp_path):
    decision = govern(_req("fs.read", workspace_root=str(tmp_path)))
    assert decision.decision == "ALLOW"


def test_workspace_outside_cwd_is_probe_only(tmp_path):
    outside = str(tmp_path / "some" / "outside" / "path")
    decision = govern(_req("fs.write", workspace_root=outside))
    assert decision.decision in ("QUARANTINE", "DENY")
