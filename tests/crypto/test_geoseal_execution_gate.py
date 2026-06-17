from __future__ import annotations

import json
import sys
from pathlib import Path

from src.crypto.geoseal_execution_gate import (
    execute_governed_command,
    scan_command,
    simulate_command,
)
from src.crypto.sealed_memory_packets import unseal_memory_packet


def test_scan_blocks_shell_chaining_before_execution() -> None:
    decision = scan_command("python -c \"print('ok')\" && python -c \"print('bad')\"")

    assert decision.tier == "DENY"
    assert not decision.allowed
    assert any(finding.rule == "shell-metachar" for finding in decision.findings)


def test_recursive_force_rm_is_denied_in_any_flag_form() -> None:
    # Security regression: the destructive-rm rule used the literal `\brm\s+-rf\b`,
    # which ONLY matched `rm -rf` and silently ALLOWED every other spelling of the same
    # recursive-force delete: `rm -fr`, `rm -r -f`, `rm --recursive --force`, flag
    # bundles, and capital -R. Lock that the rule now requires a recursive flag AND a
    # force flag in any order/form.
    for cmd in (
        "rm -rf /tmp/x",
        "rm -fr /tmp/x",
        "rm -r -f /tmp/x",
        "rm -f -r /tmp/x",
        "rm --recursive --force /tmp/x",
        "rm --force --recursive /tmp/x",
        "rm -rfv /tmp/x",
        "rm -vrf /tmp/x",
        "rm -R -f /tmp/x",
        "rm --recursive -f /tmp/x",
        "rm -r --force /tmp/x",
    ):
        decision = scan_command(cmd)
        assert decision.tier == "DENY", cmd
        assert not decision.allowed, cmd
        assert any(f.rule == "destructive-rm" for f in decision.findings), cmd


def test_non_recursive_rm_is_not_flagged_as_destructive() -> None:
    # The broadened rule must not over-block: plain delete, force-only, and
    # recursive-only each lack the other required flag and must NOT be flagged.
    for cmd in (
        "rm /tmp/x",
        "rm -f /tmp/x",
        "rm -r /tmp/x",
        "rm -i /tmp/x",
        "ls -rf",
    ):
        decision = scan_command(cmd)
        assert not any(f.rule == "destructive-rm" for f in decision.findings), cmd


def test_recursive_powershell_delete_is_denied() -> None:
    # Security regression: the deny rule used `\b-recurse`, but \b never matches
    # between a space and a hyphen, so the rule was dead and `Remove-Item -Recurse
    # -Force` (plus the `rm`/`ri` aliases) were silently ALLOWED. Lock the fix.
    for cmd in (
        "Remove-Item -Recurse -Force C:\\Users",
        "remove-item -recurse -force C:/Users",
        "rm -Recurse -Force ./build",
        "ri -Recurse ./dist",
    ):
        decision = scan_command(cmd)
        assert decision.tier == "DENY", cmd
        assert not decision.allowed, cmd
        assert any(f.rule == "destructive-remove-item" for f in decision.findings), cmd


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


# ── inline-payload logic detection (catches dangerous CODE inside `-c`) ──
# These are scan-only: the dangerous payload is analysed, never executed.


def test_inline_python_destructive_payload_is_denied() -> None:
    # The dangerous logic lives inside the -c string; no rm/Remove-Item command
    # SHAPE matches. The gate must look inside the payload and DENY it.
    for code in (
        "shutil.rmtree('build')",
        "os.system('whatever')",
        "os.remove('x')",
        "__import__('os').system('y')",
        "eval('1+1')",
        "import socket",
    ):
        decision = scan_command(f'{sys.executable} -c "{code}"')
        assert decision.tier == "DENY", code
        assert not decision.allowed, code
        assert any(f.rule.startswith("inline-danger") for f in decision.findings), code


def test_benign_inline_python_payload_stays_quarantine() -> None:
    decision = scan_command(f'{sys.executable} -c "print(2 + 2)"')
    assert decision.tier == "QUARANTINE"
    assert decision.allowed
    assert not any(f.rule.startswith("inline-danger") for f in decision.findings)


def test_inline_node_child_process_is_denied() -> None:
    decision = scan_command("node -c \"require('child_process').execSync('id')\"")
    assert decision.tier == "DENY"
    assert any(f.rule == "inline-danger-node" for f in decision.findings)


# ── simulate_command: pre-flight dry-run that NEVER executes ──


def test_simulate_allows_a_good_command() -> None:
    sim = simulate_command(f"{sys.executable} --version", max_tier="ALLOW")
    assert sim.would_run
    assert sim.decision.tier == "ALLOW"
    assert sim.blocked_reason is None
    assert sim.summary.startswith("WOULD RUN")


def test_simulate_blocks_a_destructive_command() -> None:
    sim = simulate_command("rm -rf /tmp/x", max_tier="QUARANTINE")
    assert not sim.would_run
    assert sim.decision.tier == "DENY"
    assert sim.blocked_reason == "gate denied"
    assert sim.summary.startswith("BLOCKED")


def test_simulate_never_invokes_subprocess(monkeypatch) -> None:
    # Hard proof of the safety contract: even for a command that WOULD run,
    # simulate_command must not launch a subprocess.
    import src.crypto.geoseal_execution_gate as gate

    def _boom(*args, **kwargs):  # pragma: no cover - must never be called
        raise AssertionError("simulate_command must not execute a subprocess")

    monkeypatch.setattr(gate.subprocess, "run", _boom)
    sim = gate.simulate_command(f'{sys.executable} -c "print(1)"', max_tier="QUARANTINE")
    assert sim.would_run  # would run at QUARANTINE — but subprocess.run was never called
