"""
Kernel-facing antivirus policy bridge for SCBE/PHDM.

This module is not a kernel driver. It is the deterministic policy engine that
maps kernel telemetry events to containment actions using the existing SCBE
threat membrane and HYDRA turnstile logic.

Security-as-cells model:
- HEALTHY: normal execution
- PRIMED: increased monitoring
- INFLAMED: friction increase / throttle
- NECROTIC: immediate isolation + honeypot lane

Expected integration:
- Linux: eBPF/Falco/sysmon-like event feed -> evaluate_kernel_event()
- Windows: ETW/minifilter event feed -> evaluate_kernel_event()
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Literal
import re

from agents.antivirus_membrane import ThreatScan, scan_text_for_threats
from hydra.turnstile import TurnstileOutcome, resolve_turnstile


KernelAction = Literal["ALLOW", "THROTTLE", "QUARANTINE", "KILL", "HONEYPOT"]


OPERATION_RISK = {
    "exec": 0.12,
    "open": 0.02,
    "write": 0.12,
    "delete": 0.14,
    "rename": 0.08,
    "network_connect": 0.08,
    "dns_query": 0.04,
    "module_load": 0.30,
    "process_inject": 0.38,
    "registry_write": 0.16,
}

SENSITIVE_TARGET_PATTERNS = (
    r"(?i)\\windows\\system32\\drivers\\",
    r"(?i)\\windows\\system32\\config\\",
    r"(?i)\\appdata\\roaming\\microsoft\\windows\\start menu\\programs\\startup",
    r"(?i)/etc/(ssh|sudoers|passwd|shadow)",
    r"(?i)/boot/",
    r"(?i)/usr/lib/modules/",
)

SUSPICIOUS_PARENT_CHILD = (
    ("winword.exe", "powershell"),
    ("excel.exe", "powershell"),
    ("outlook.exe", "powershell"),
    ("wscript.exe", "cmd.exe"),
    ("python", "bash"),
)


@dataclass(frozen=True)
class KernelEvent:
    host: str
    pid: int
    process_name: str
    operation: str
    target: str = ""
    command_line: str = ""
    parent_process: str = ""
    signer_trusted: bool = False
    hash_sha256: str | None = None
    geometry_norm: float = 0.0
    metadata: dict[str, Any] | None = None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "KernelEvent":
        return KernelEvent(
            host=str(data.get("host", "")).strip(),
            pid=int(data.get("pid", 0)),
            process_name=str(data.get("process_name", "")).strip().lower(),
            operation=str(data.get("operation", "")).strip().lower(),
            target=str(data.get("target", "")).strip(),
            command_line=str(data.get("command_line", "")).strip(),
            parent_process=str(data.get("parent_process", "")).strip().lower(),
            signer_trusted=bool(data.get("signer_trusted", False)),
            hash_sha256=(str(data["hash_sha256"]).strip().lower() if data.get("hash_sha256") else None),
            geometry_norm=float(data.get("geometry_norm", 0.0) or 0.0),
            metadata=(data.get("metadata") if isinstance(data.get("metadata"), dict) else None),
        )


@dataclass(frozen=True)
class KernelGateResult:
    decision: str
    suspicion: float
    integrity_risk: float
    geometry_norm: float
    cell_state: str
    threat_scan: ThreatScan
    turnstile: TurnstileOutcome
    kernel_action: KernelAction
    block_execution: bool
    isolate_process: bool
    quarantine_target: bool
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "suspicion": self.suspicion,
            "integrity_risk": self.integrity_risk,
            "geometry_norm": self.geometry_norm,
            "cell_state": self.cell_state,
            "threat_scan": self.threat_scan.to_dict(),
            "turnstile": asdict(self.turnstile),
            "kernel_action": self.kernel_action,
            "block_execution": self.block_execution,
            "isolate_process": self.isolate_process,
            "quarantine_target": self.quarantine_target,
            "notes": list(self.notes),
        }


def _clamp01(x: float) -> float:
    return min(1.0, max(0.0, x))


def _target_risk(target: str) -> tuple[float, tuple[str, ...]]:
    text = target or ""
    notes: list[str] = []
    risk = 0.0
    for pattern in SENSITIVE_TARGET_PATTERNS:
        if re.search(pattern, text):
            risk += 0.18
            notes.append(f"sensitive target match: {pattern}")
    return _clamp01(risk), tuple(notes)


def _integrity_risk(event: KernelEvent) -> tuple[float, tuple[str, ...]]:
    risk = OPERATION_RISK.get(event.operation, 0.10)
    notes: list[str] = []

    if event.operation not in OPERATION_RISK:
        notes.append(f"unknown operation: {event.operation}")

    if not event.signer_trusted:
        risk += 0.22
        notes.append("unsigned or untrusted signer")

    if not event.hash_sha256:
        risk += 0.16
        notes.append("missing sha256")
    elif len(event.hash_sha256) != 64:
        risk += 0.12
        notes.append("invalid sha256 length")

    target_risk, target_notes = _target_risk(event.target)
    risk += target_risk
    notes.extend(target_notes)

    parent = event.parent_process
    proc = event.process_name
    for p, c in SUSPICIOUS_PARENT_CHILD:
        if p in parent and c in proc:
            risk += 0.20
            notes.append(f"suspicious parent-child: {p}->{c}")

    return _clamp01(risk), tuple(notes)


def _base_decision(suspicion: float) -> str:
    if suspicion >= 0.85:
        return "DENY"
    if suspicion >= 0.60:
        return "ESCALATE"
    if suspicion >= 0.30:
        return "QUARANTINE"
    return "ALLOW"


def _map_kernel_action(turnstile: TurnstileOutcome) -> tuple[KernelAction, bool, bool, bool]:
    if turnstile.action == "ALLOW":
        return "ALLOW", False, False, False
    if turnstile.action == "HONEYPOT":
        return "HONEYPOT", True, True, True
    if turnstile.action == "ISOLATE":
        return "QUARANTINE", True, True, True
    if turnstile.action == "STOP":
        return "KILL", True, True, False
    # HOLD/PIVOT/DEGRADE map to throttled execution.
    return "THROTTLE", False, False, False


def _cell_state(antibody_load: float, membrane_stress: float, suspicion: float) -> str:
    signal = max(_clamp01(antibody_load), _clamp01(membrane_stress), _clamp01(suspicion))
    if signal >= 0.90:
        return "NECROTIC"
    if signal >= 0.70:
        return "INFLAMED"
    if signal >= 0.35:
        return "PRIMED"
    return "HEALTHY"


def evaluate_kernel_event(
    event: KernelEvent | dict[str, Any],
    *,
    previous_antibody_load: float = 0.0,
    extra_prompt_patterns: Iterable[str] = (),
    extra_malware_patterns: Iterable[str] = (),
) -> KernelGateResult:
    """
    Evaluate one kernel telemetry event through SCBE-style antivirus gating.
    """
    if not isinstance(event, KernelEvent):
        event = KernelEvent.from_dict(event)

    scan_input = "\n".join(
        [
            event.process_name,
            event.operation,
            event.target,
            event.command_line,
            event.parent_process,
            str(event.metadata or ""),
        ]
    )
    scan = scan_text_for_threats(
        scan_input,
        extra_prompt_patterns=extra_prompt_patterns,
        extra_malware_patterns=extra_malware_patterns,
    )

    integrity_risk, integrity_notes = _integrity_risk(event)
    observed_norm = _clamp01(event.geometry_norm)

    # Enemy-first blend: direct malicious content + binary integrity + geometry stress.
    suspicion = _clamp01(0.50 * scan.risk_score + 0.35 * integrity_risk + 0.15 * observed_norm)
    geometry_norm = _clamp01(max(observed_norm, 0.20 + 0.75 * suspicion))

    decision = _base_decision(suspicion)
    turnstile = resolve_turnstile(
        decision=decision,
        domain="antivirus",
        suspicion=suspicion,
        geometry_norm=geometry_norm,
        previous_antibody_load=previous_antibody_load,
        quorum_ok=True,
    )

    cell_state = _cell_state(
        antibody_load=turnstile.antibody_load,
        membrane_stress=turnstile.membrane_stress,
        suspicion=suspicion,
    )

    kernel_action, block_execution, isolate_process, quarantine_target = _map_kernel_action(turnstile)
    if cell_state == "NECROTIC":
        kernel_action = "HONEYPOT"
        block_execution = True
        isolate_process = True
        quarantine_target = True
    elif cell_state == "INFLAMED" and kernel_action == "ALLOW":
        kernel_action = "THROTTLE"

    notes = list(scan.reasons)
    notes.extend(integrity_notes)
    notes.append(f"immune cell state={cell_state}")
    if kernel_action == "ALLOW":
        notes.append("kernel path clear")
    else:
        notes.append("enemy friction elevated at kernel gate")

    return KernelGateResult(
        decision=decision,
        suspicion=round(suspicion, 4),
        integrity_risk=round(integrity_risk, 4),
        geometry_norm=round(geometry_norm, 4),
        cell_state=cell_state,
        threat_scan=scan,
        turnstile=turnstile,
        kernel_action=kernel_action,
        block_execution=block_execution,
        isolate_process=isolate_process,
        quarantine_target=quarantine_target,
        notes=tuple(notes),
    )
