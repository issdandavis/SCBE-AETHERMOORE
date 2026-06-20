"""AMSI-style execution gate for GeoSeal command execution.

The gate is intentionally small and conservative:

parse -> scan -> decide -> optional execute -> optional sealed audit

It is not a sandbox. It is a pre-execution policy layer that catches obvious
dangerous command shapes before GeoSeal launches a subprocess.
"""

from __future__ import annotations

import ast
import hashlib
import ctypes
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from src.crypto.sealed_memory_packets import seal_memory_packet

TIER_RANK = {"ALLOW": 0, "QUARANTINE": 1, "ESCALATE": 2, "DENY": 3}
DEFAULT_EXEC_AUDIT_LOG = Path(".scbe/geoseal_exec_audit.sealed.jsonl")
DEFAULT_AUDIT_SECRET_ENV = "GEOSEAL_EXEC_AUDIT_SECRET"


@dataclass(frozen=True)
class GateFinding:
    """One execution-policy finding from command parsing or scanning."""

    rule: str
    tier: str
    message: str
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExecGateDecision:
    """Pre-execution gate verdict."""

    command_sha256: str
    tier: str
    allowed: bool
    argv: list[str] = field(default_factory=list)
    findings: list[GateFinding] = field(default_factory=list)
    parser_ok: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_sha256": self.command_sha256,
            "tier": self.tier,
            "allowed": self.allowed,
            "argv": self.argv,
            "parser_ok": self.parser_ok,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(frozen=True)
class ExecGateResult:
    """Execution result with the gate decision attached."""

    decision: ExecGateDecision
    ran: bool
    returncode: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    error: Optional[str] = None
    audit_written: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.to_dict(),
            "ran": self.ran,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "audit_written": self.audit_written,
        }


@dataclass(frozen=True)
class ExecGateSimulation:
    """Dry-run preview: what execute_governed_command WOULD do, without running.

    Pure analysis (parse + policy scan). NEVER launches a subprocess, so it is
    safe to call from a live terminal as a pre-flight check before any real run.
    """

    decision: ExecGateDecision
    would_run: bool
    max_tier: str
    resolved_argv: list[str] = field(default_factory=list)
    runtime_note: Optional[str] = None
    blocked_reason: Optional[str] = None
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.to_dict(),
            "would_run": self.would_run,
            "max_tier": self.max_tier,
            "resolved_argv": self.resolved_argv,
            "runtime_note": self.runtime_note,
            "blocked_reason": self.blocked_reason,
            "summary": self.summary,
        }


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _max_tier(findings: Iterable[GateFinding]) -> str:
    tier = "ALLOW"
    for finding in findings:
        if TIER_RANK[finding.tier] > TIER_RANK[tier]:
            tier = finding.tier
    return tier


def _parse_command(command: str) -> tuple[list[str], list[GateFinding]]:
    if not command.strip():
        return [], [GateFinding("empty-command", "DENY", "command is empty")]
    try:
        if os.name == "nt":
            return _windows_command_line_to_argv(command), []
        return shlex.split(command), []
    except ValueError as exc:
        return [], [GateFinding("parse-error", "DENY", f"command parse failed: {exc}")]


def _windows_command_line_to_argv(command: str) -> list[str]:
    """Parse Windows command text the same way CreateProcess callers expect."""

    argc = ctypes.c_int()
    shell32 = ctypes.windll.shell32
    kernel32 = ctypes.windll.kernel32
    shell32.CommandLineToArgvW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    shell32.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    argv_ptr = shell32.CommandLineToArgvW(command, ctypes.byref(argc))
    if not argv_ptr:
        raise ValueError("CommandLineToArgvW failed")
    try:
        return [argv_ptr[i] for i in range(argc.value)]
    finally:
        kernel32.LocalFree(argv_ptr)


# ── inline-payload inspection ────────────────────────────────────────────────
# scan_command catches dangerous command SHAPES. For `python -c "<code>"` and
# `node -c "<code>"` the dangerous logic lives INSIDE the payload string, which
# no command-shape regex can see (e.g. `python -c "import shutil; shutil.rmtree(p)"`
# matches no rm/Remove-Item pattern). These helpers parse that payload and DENY it
# when it destroys files, spawns processes, evaluates dynamically, or reaches for
# raw OS/socket/registry access — closing the inline-interpreter smuggling gap.
_PY_DANGER_DOTTED = {
    ("shutil", "rmtree"),
    ("os", "system"),
    ("os", "remove"),
    ("os", "unlink"),
    ("os", "rmdir"),
    ("os", "removedirs"),
    ("os", "popen"),
    ("os", "kill"),
    ("os", "execv"),
    ("subprocess", "run"),
    ("subprocess", "call"),
    ("subprocess", "Popen"),
    ("subprocess", "check_call"),
    ("subprocess", "check_output"),
}
_PY_DANGER_NAMES = {"eval", "exec", "compile", "__import__"}
_PY_DANGER_MODULES = {"ctypes", "socket", "winreg", "pty"}

_NODE_DANGER = [
    (r"child_process", "spawns child processes"),
    (r"\bfs\.(rm|rmdir|rmSync|rmdirSync|unlink|unlinkSync)\b", "deletes files"),
    (r"\bexecSync\b|\bspawnSync\b|\bexec\s*\(", "executes shell/process"),
]


def _inline_payload(argv: Sequence[str]) -> Optional[str]:
    """The string after a `-c` flag, if present."""
    for i in range(1, len(argv) - 1):
        if argv[i] == "-c":
            return argv[i + 1]
    return None


def _scan_python_payload(code: str) -> list[GateFinding]:
    """AST-scan an inline python payload for destructive / dynamic operations."""
    findings: list[GateFinding] = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return findings  # unparseable — the interpreter-level QUARANTINE still applies
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name):
                pair = (fn.value.id, fn.attr)
                if pair in _PY_DANGER_DOTTED:
                    findings.append(
                        GateFinding(
                            "inline-danger-call",
                            "DENY",
                            f"inline python calls {pair[0]}.{pair[1]}()",
                            evidence=f"{pair[0]}.{pair[1]}",
                        )
                    )
            elif isinstance(fn, ast.Name) and fn.id in _PY_DANGER_NAMES:
                findings.append(
                    GateFinding(
                        "inline-danger-call",
                        "DENY",
                        f"inline python calls {fn.id}()",
                        evidence=fn.id,
                    )
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _PY_DANGER_MODULES:
                    findings.append(
                        GateFinding(
                            "inline-danger-import",
                            "DENY",
                            f"inline python imports {root}",
                            evidence=root,
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in _PY_DANGER_MODULES:
                findings.append(
                    GateFinding(
                        "inline-danger-import",
                        "DENY",
                        f"inline python imports {root}",
                        evidence=root,
                    )
                )
    return findings


def _scan_node_payload(code: str) -> list[GateFinding]:
    """Regex-scan an inline node payload for destructive / process operations."""
    findings: list[GateFinding] = []
    for pattern, message in _NODE_DANGER:
        if re.search(pattern, code):
            findings.append(
                GateFinding(
                    "inline-danger-node",
                    "DENY",
                    f"inline node {message}",
                    evidence=pattern,
                )
            )
    return findings


def scan_command(
    command: str,
    *,
    claimed_paths: Optional[Sequence[str]] = None,
    shell_context: bool = False,
) -> ExecGateDecision:
    """Parse and scan a command without executing it.

    Args:
        command: The raw command string to inspect (never executed).
        claimed_paths: Optional declared path scope; touching paths outside it
            is flagged as ``unclaimed-path``.
        shell_context: When True, the command is expected to run *through* a
            shell (e.g. ``scbe run`` -> PowerShell), so the blanket pipe/chain
            metacharacter DENY is relaxed. The dangerous-pattern denies
            (recursive delete, curl|sh, encoded PowerShell, secret paths) and
            the ``curl|sh`` download-to-exec rule still apply regardless.

    Returns:
        An ``ExecGateDecision`` with the resolved tier and findings.
    """
    findings: list[GateFinding] = []
    argv, parse_findings = _parse_command(command)
    findings.extend(parse_findings)
    command_l = command.lower()

    # A2: the structural shell-metachar block is relaxed in shell_context (the
    # caller intentionally routes through a shell); dangerous-pattern denies
    # below are unconditional.
    if not shell_context and any(marker in command for marker in ("|", "&&", "||", ";")):
        findings.append(
            GateFinding(
                "shell-metachar",
                "DENY",
                "shell chaining and pipe metacharacters are blocked by geoseal exec",
                evidence=command,
            )
        )

    deny_patterns: list[tuple[str, str, str]] = [
        (
            r"\bwsl(?:\.exe)?\b.*(?:\s|^)--shutdown\b",
            "wsl-shutdown",
            "WSL VM shutdown command",
        ),
        (
            r"\b(?:shutdown|restart-computer|stop-computer|poweroff|reboot)\b",
            "system-power-state",
            "host power-state command",
        ),
        (
            r"\bpowercfg\b.*\b(?:hibernate|standby|sleep|h(?:ibernate)?\s+(?:on|off)|-h\s+(?:on|off))\b",
            "powercfg-state-change",
            "host sleep/hibernate configuration change",
        ),
        (
            r"\b(?:bcdedit|diskpart|format|manage-bde|reagentc)\b",
            "system-disk-boot-tool",
            "boot/disk/system configuration tool",
        ),
        (
            r"\b(?:disable-netadapter|restart-netadapter|enable-netadapter|netsh)\b",
            "network-adapter-control",
            "network adapter or stack control",
        ),
        (
            r"\bdocker\b\s+system\s+prune\b.*(?:\s-a\b|\s--all\b)",
            "docker-system-prune-all",
            "global Docker prune-all command",
        ),
        (
            r"\btaskkill\b.*(?:\s/f\b|\s/t\b).*(?:\s/im\s+\*|\s/pid\s+0\b|python\.exe|node\.exe|code\.exe)",
            "broad-taskkill",
            "broad forced process kill",
        ),
        (
            r"\bstop-process\b.*(?:-force|\s-id\s+0\b|-name\s+\*|python|node|code)",
            "broad-stop-process",
            "broad forced PowerShell process kill",
        ),
        (
            r"\b(?:stress|stress-ng|sysbench)\b|\bwhile\s+(?:true\b|\(\s*\$true\s*\))",
            "host-stress-loop",
            "host stress or unbounded loop command",
        ),
        # destructive-rm must catch recursive+force in ANY flag form/order, not just the
        # literal "-rf". The old `\brm\s+-rf\b` ALLOWED `rm -fr`, `rm -r -f`, and
        # `rm --recursive --force` (a real bypass — confirmed via scan_command). Require
        # an `rm` token plus a recursive flag AND a force flag anywhere after it: bundled
        # (-rf/-fr/-vrf), split (-r -f), or long (--recursive/--force). The `\s-` (not \b)
        # before each flag avoids the same boundary trap that disabled -recurse below.
        # Plain `rm`, `rm -f`, and `rm -r` stay ALLOWED (each lookahead needs the other).
        (
            r"\brm\b(?=.*(?:\s-[a-z]*r[a-z]*\b|\s--recursive\b))(?=.*(?:\s-[a-z]*f[a-z]*\b|\s--force\b))",
            "destructive-rm",
            "recursive force delete",
        ),
        # The leading boundary before "-recurse" must NOT be \b — \b never matches
        # between a space and a hyphen, so `\b-recurse` silently disabled this rule and
        # `Remove-Item -Recurse -Force` (and the `rm`/`ri` aliases) were ALLOWED.
        (
            r"\b(?:remove-item|ri|rm)\b.*(?:\s|^)-recurse\b",
            "destructive-remove-item",
            "recursive PowerShell delete",
        ),
        (
            r"\binvoke-expression\b|\biex\b",
            "powershell-iex",
            "dynamic PowerShell execution",
        ),
        (
            r"\bcurl\b.*\|\s*(sh|bash|powershell|pwsh|iex)\b",
            "curl-pipe-exec",
            "download-to-exec chain",
        ),
        (
            r"\bwget\b.*\|\s*(sh|bash|powershell|pwsh|iex)\b",
            "wget-pipe-exec",
            "download-to-exec chain",
        ),
        (
            r"config[/\\]connector_oauth",
            "connector-secret-path",
            "connector OAuth secret path",
        ),
        (r"\.env(\.|$|\s)", "env-secret-path", "environment secret file path"),
    ]
    for pattern, rule, message in deny_patterns:
        if re.search(pattern, command_l):
            findings.append(GateFinding(rule, "DENY", message, evidence=pattern))

    if argv:
        executable = Path(argv[0]).name.lower()
        if executable in {"powershell", "powershell.exe", "pwsh", "pwsh.exe"}:
            if any(arg.lower() in {"-encodedcommand", "-enc"} for arg in argv[1:]):
                findings.append(
                    GateFinding(
                        "encoded-powershell",
                        "DENY",
                        "encoded PowerShell commands are blocked",
                    )
                )
        if executable in {"python", "python.exe", "py", "node", "node.exe"} and "-c" in argv[1:]:
            findings.append(
                GateFinding(
                    "inline-interpreter",
                    "QUARANTINE",
                    "inline interpreter execution requires explicit allowance",
                    evidence=argv[0],
                )
            )
            # Look INSIDE the -c payload: dangerous logic there is DENY, not just QUARANTINE.
            payload = _inline_payload(argv)
            if payload:
                if executable.startswith("node"):
                    findings.extend(_scan_node_payload(payload))
                else:
                    findings.extend(_scan_python_payload(payload))

    if claimed_paths:
        normalized_claims = [Path(path).as_posix().lower().strip("/") for path in claimed_paths]
        touched = [token.strip("\"'").replace("\\", "/").lower() for token in argv if "/" in token or "\\" in token]
        for token in touched:
            if normalized_claims and not any(token.startswith(claim) or claim in token for claim in normalized_claims):
                findings.append(
                    GateFinding(
                        "unclaimed-path",
                        "DENY",
                        "command touches a path outside its declared scope",
                        evidence=token,
                    )
                )

    tier = _max_tier(findings)
    return ExecGateDecision(
        command_sha256=_sha256_text(command),
        tier=tier,
        allowed=tier == "ALLOW",
        argv=argv,
        findings=findings,
        parser_ok=not any(finding.rule == "parse-error" for finding in findings),
    )


def _resolve_audit_secret(
    *, audit_secret: Optional[str], audit_secret_env: str = DEFAULT_AUDIT_SECRET_ENV
) -> Optional[str]:
    return audit_secret or os.environ.get(audit_secret_env)


def append_sealed_exec_audit(
    record: Mapping[str, Any],
    *,
    audit_log: Path = DEFAULT_EXEC_AUDIT_LOG,
    audit_secret: Optional[str] = None,
    audit_secret_env: str = DEFAULT_AUDIT_SECRET_ENV,
) -> bool:
    """Append a sealed execution audit record when a secret is available."""

    secret = _resolve_audit_secret(audit_secret=audit_secret, audit_secret_env=audit_secret_env)
    if not secret:
        return False
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    packet = seal_memory_packet(
        secret,
        json.dumps(record, sort_keys=True, separators=(",", ":")),
        label="geoseal-exec-audit",
        metadata={
            "kind": "geoseal_exec_audit",
            "command_sha256": record.get("decision", {}).get("command_sha256"),
            "tier": record.get("decision", {}).get("tier"),
            "ts": record.get("timestamp"),
        },
    )
    with audit_log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(packet, sort_keys=True) + "\n")
    return True


# Bare interpreter names that should resolve to the running interpreter when
# present (avoids Windows CreateProcess "file not found" failures when `python`
# is on PATH only via the App Execution Alias shim, etc.).
_PYTHON_ALIASES = {"python", "python3", "py", "python.exe", "py.exe"}


def _resolve_runtime(argv: Sequence[str]) -> tuple[list[str], Optional[str]]:
    """Resolve argv[0] to an absolute executable path.

    For Python aliases we prefer `sys.executable` so the gate runs the same
    interpreter the user is already in. For everything else we fall back to
    `shutil.which`. Returns the (possibly rewritten) argv plus a one-line
    note for diagnostics.
    """
    if not argv:
        return list(argv), None
    head = argv[0]
    head_name = Path(head).name.lower()

    # Already an absolute or relative path that exists — leave it alone.
    if os.path.sep in head or (os.altsep and os.altsep in head):
        if Path(head).exists():
            return list(argv), None

    if head_name in _PYTHON_ALIASES:
        return [sys.executable, *argv[1:]], f"runtime: python alias ->{sys.executable}"

    resolved = shutil.which(head)
    if resolved:
        return [resolved, *argv[1:]], f"runtime: {head} ->{resolved}"
    return list(argv), None


def execute_governed_command(
    command: str,
    *,
    cwd: Optional[Path | str] = None,
    timeout: float = 30.0,
    max_tier: str = "ALLOW",
    claimed_paths: Optional[Sequence[str]] = None,
    audit_log: Optional[Path] = DEFAULT_EXEC_AUDIT_LOG,
    audit_secret: Optional[str] = None,
    audit_secret_env: str = DEFAULT_AUDIT_SECRET_ENV,
) -> ExecGateResult:
    """Gate and run a command as a subprocess without shell expansion."""

    if max_tier not in TIER_RANK:
        raise ValueError(f"unknown max_tier: {max_tier}")
    decision = scan_command(command, claimed_paths=claimed_paths)
    allowed_by_threshold = decision.tier != "DENY" and TIER_RANK[decision.tier] <= TIER_RANK[max_tier]
    started = time.time()
    resolved_argv, runtime_note = _resolve_runtime(decision.argv)

    if allowed_by_threshold:
        try:
            proc = subprocess.run(
                resolved_argv,
                cwd=str(cwd) if cwd is not None else None,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
            result = ExecGateResult(
                decision=decision,
                ran=True,
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration_ms=(time.time() - started) * 1000.0,
            )
        except subprocess.TimeoutExpired:
            result = ExecGateResult(
                decision=decision,
                ran=False,
                duration_ms=(time.time() - started) * 1000.0,
                error="timeout",
            )
        except FileNotFoundError as exc:
            result = ExecGateResult(
                decision=decision,
                ran=False,
                duration_ms=(time.time() - started) * 1000.0,
                error=f"runtime not found: {exc}",
            )
        except Exception as exc:  # pragma: no cover - defensive
            result = ExecGateResult(
                decision=decision,
                ran=False,
                duration_ms=(time.time() - started) * 1000.0,
                error=f"{type(exc).__name__}: {exc}",
            )
    else:
        reason = "gate denied" if decision.tier == "DENY" else f"tier {decision.tier} exceeds max {max_tier}"
        result = ExecGateResult(
            decision=decision,
            ran=False,
            duration_ms=(time.time() - started) * 1000.0,
            error=reason,
        )

    if audit_log is not None:
        record = {
            "version": "geoseal-exec-audit-v1",
            "timestamp": time.time(),
            "command": command,
            "max_tier": max_tier,
            "result": result.to_dict(),
            "decision": decision.to_dict(),
        }
        audit_written = append_sealed_exec_audit(
            record,
            audit_log=audit_log,
            audit_secret=audit_secret,
            audit_secret_env=audit_secret_env,
        )
        if audit_written != result.audit_written:
            result = ExecGateResult(
                decision=result.decision,
                ran=result.ran,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=result.duration_ms,
                error=result.error,
                audit_written=audit_written,
            )
    return result


def simulate_command(
    command: str,
    *,
    max_tier: str = "ALLOW",
    claimed_paths: Optional[Sequence[str]] = None,
) -> ExecGateSimulation:
    """Pre-flight dry-run: report what execute_governed_command WOULD do.

    Parses, scans, and resolves the runtime exactly like the real path, then
    reports whether the command WOULD run at ``max_tier`` and why it would be
    blocked otherwise. It NEVER launches a subprocess, so it is safe to run in a
    live terminal — preview here, then do real execution in a sandbox.
    """

    if max_tier not in TIER_RANK:
        raise ValueError(f"unknown max_tier: {max_tier}")
    decision = scan_command(command, claimed_paths=claimed_paths)
    would_run = decision.tier != "DENY" and TIER_RANK[decision.tier] <= TIER_RANK[max_tier]
    resolved_argv, runtime_note = _resolve_runtime(decision.argv)
    blocked_reason: Optional[str] = None
    if not would_run:
        blocked_reason = "gate denied" if decision.tier == "DENY" else f"tier {decision.tier} exceeds max {max_tier}"
    rules = ", ".join(sorted({f.rule for f in decision.findings})) or "none"
    verb = "WOULD RUN" if would_run else "BLOCKED"
    shown = " ".join(resolved_argv) if resolved_argv else command
    summary = f"{verb} [{decision.tier}] {shown}  (findings: {rules})"
    return ExecGateSimulation(
        decision=decision,
        would_run=would_run,
        max_tier=max_tier,
        resolved_argv=resolved_argv,
        runtime_note=runtime_note,
        blocked_reason=blocked_reason,
        summary=summary,
    )
