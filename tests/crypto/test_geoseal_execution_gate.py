from __future__ import annotations

import json
import sys
from pathlib import Path

from src.crypto.geoseal_execution_gate import (
    execute_governed_command,
    scan_command,
)
from src.crypto.sealed_memory_packets import unseal_memory_packet


def test_scan_blocks_shell_chaining_before_execution() -> None:
    decision = scan_command("python -c \"print('ok')\" && python -c \"print('bad')\"")

    assert decision.tier == "DENY"
    assert not decision.allowed
    assert any(finding.rule == "shell-metachar" for finding in decision.findings)


def test_inline_interpreter_is_quarantine_not_deny() -> None:
    decision = scan_command(f"{sys.executable} -c \"print('ok')\"")

    assert decision.tier == "QUARANTINE"
    assert decision.allowed
    assert any(finding.rule == "inline-interpreter" for finding in decision.findings)


def test_exec_allows_quarantine_when_threshold_permits() -> None:
    result = execute_governed_command(
        f"{sys.executable} -c \"print('gate-ok')\"",
        max_tier="QUARANTINE",
        audit_log=None,
    )

    assert result.ran
    assert result.returncode == 0
    assert "gate-ok" in result.stdout


def test_exec_blocks_quarantine_when_threshold_is_allow() -> None:
    result = execute_governed_command(
        f"{sys.executable} -c \"print('gate-ok')\"",
        max_tier="ALLOW",
        audit_log=None,
    )

    assert not result.ran
    assert result.error == "tier QUARANTINE exceeds max ALLOW"


def test_exec_writes_sealed_audit_when_secret_available(tmp_path: Path) -> None:
    audit_log = tmp_path / "exec_audit.jsonl"
    result = execute_governed_command(
        f"{sys.executable} -c \"print('sealed-audit')\"",
        max_tier="QUARANTINE",
        audit_log=audit_log,
        audit_secret="unit-test-secret",
    )

    assert result.ran
    assert result.audit_written
    packet = json.loads(audit_log.read_text(encoding="utf-8").splitlines()[0])
    opened = unseal_memory_packet("unit-test-secret", packet)
    payload = json.loads(opened["text"])

    assert payload["version"] == "geoseal-exec-audit-v1"
    assert payload["result"]["returncode"] == 0
    assert payload["decision"]["tier"] == "QUARANTINE"


def test_path_claim_boundary_blocks_out_of_scope_path() -> None:
    decision = scan_command("python scripts/other_lane/tool.py", claimed_paths=["src/geoseal_cli.py"])

    assert decision.tier == "DENY"
    assert any(finding.rule == "unclaimed-path" for finding in decision.findings)


def test_runtime_resolver_rewrites_python_alias_to_sys_executable() -> None:
    from src.crypto.geoseal_execution_gate import _resolve_runtime

    resolved, note = _resolve_runtime(["python", "-c", "print(1)"])
    assert resolved[0] == sys.executable
    assert resolved[1:] == ["-c", "print(1)"]
    assert note is not None and "python alias" in note


def test_runtime_resolver_uses_shutil_which_for_other_executables() -> None:
    import shutil
    from src.crypto.geoseal_execution_gate import _resolve_runtime

    # `cmd` exists on Windows; on POSIX `sh` is a stable proxy.
    probe = "cmd" if sys.platform == "win32" else "sh"
    if shutil.which(probe) is None:  # pragma: no cover — environment guard
        return
    resolved, note = _resolve_runtime([probe, "/?"])
    assert Path(resolved[0]).is_absolute()
    assert resolved[0].lower().endswith(probe + (".exe" if sys.platform == "win32" else ""))


def test_runtime_resolver_passes_through_absolute_paths() -> None:
    from src.crypto.geoseal_execution_gate import _resolve_runtime

    resolved, note = _resolve_runtime([sys.executable, "-c", "print(1)"])
    assert resolved[0] == sys.executable
    assert note is None  # nothing was rewritten


def test_exec_runs_bare_python_alias_after_resolution() -> None:
    """The CLI passes 'python' as argv[0]; the resolver must rewrite it
    so subprocess.run does not raise FileNotFoundError on Windows."""
    result = execute_governed_command(
        "python -c \"print('resolved-ok')\"",
        max_tier="QUARANTINE",
        audit_log=None,
    )

    assert result.ran, f"expected ran=True, got error={result.error!r}"
    assert "resolved-ok" in result.stdout
