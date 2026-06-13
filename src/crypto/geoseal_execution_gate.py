"""AMSI-style execution gate for GeoSeal command execution.

The gate is intentionally small and conservative:

parse -> scan -> decide -> optional execute -> optional sealed audit

It is not a sandbox. It is a pre-execution policy layer that catches obvious
dangerous command shapes before GeoSeal launches a subprocess.
"""

from __future__ import annotations

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
    shell32.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
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


def scan_command(command: str, *, claimed_paths: Optional[Sequence[str]] = None) -> ExecGateDecision:
    """Parse and scan a command without executing it."""

    findings: list[GateFinding] = []
    argv, parse_findings = _parse_command(command)
    findings.extend(parse_findings)
    command_l = command.lower()

    if any(marker in command for marker in ("|", "&&", "||", ";")):
        findings.append(
            GateFinding(
                "shell-metachar",
                "DENY",
                "shell chaining and pipe metacharacters are blocked by geoseal exec",
                evidence=command,
            )
        )

    deny_patterns: list[tuple[str, str, str]] = [
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
        (r"\b(?:remove-item|ri|rm)\b.*(?:\s|^)-recurse\b", "destructive-remove-item", "recursive PowerShell delete"),
        (r"\binvoke-expression\b|\biex\b", "powershell-iex", "dynamic PowerShell execution"),
        (r"\bcurl\b.*\|\s*(sh|bash|powershell|pwsh|iex)\b", "curl-pipe-exec", "download-to-exec chain"),
        (r"\bwget\b.*\|\s*(sh|bash|powershell|pwsh|iex)\b", "wget-pipe-exec", "download-to-exec chain"),
        (r"config[/\\]connector_oauth", "connector-secret-path", "connector OAuth secret path"),
        (r"\.env(\.|$|\s)", "env-secret-path", "environment secret file path"),
    ]
    for pattern, rule, message in deny_patterns:
        if re.search(pattern, command_l):
            findings.append(GateFinding(rule, "DENY", message, evidence=pattern))

    if argv:
        executable = Path(argv[0]).name.lower()
        if executable in {"powershell", "powershell.exe", "pwsh", "pwsh.exe"}:
            if any(arg.lower() in {"-encodedcommand", "-enc"} for arg in argv[1:]):
                findings.append(GateFinding("encoded-powershell", "DENY", "encoded PowerShell commands are blocked"))
        if executable in {"python", "python.exe", "py", "node", "node.exe"} and "-c" in argv[1:]:
            findings.append(
                GateFinding(
                    "inline-interpreter",
                    "QUARANTINE",
                    "inline interpreter execution requires explicit allowance",
                    evidence=argv[0],
                )
            )

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
        allowed=tier != "DENY",
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
    allowed_by_threshold = decision.allowed and TIER_RANK[decision.tier] <= TIER_RANK[max_tier]
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
