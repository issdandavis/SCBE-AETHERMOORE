"""GeoSeal legitimacy trial for CLI/tool authority.

This layer answers a narrower question than the execution gate:

    "Should this actor get normal CLI/tool authority in this context?"

It does not execute commands. It packages situated context (time, coarse place,
workspace, host metrics, intent, and command shape) into a deterministic decision
that higher-level harnesses can use before opening broader tool access.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Mapping, Optional

from src.crypto.geoseal_execution_gate import GateFinding, TIER_RANK, scan_command

LegitimacyDecisionKind = Literal["ALLOW_CLI", "PROBE_ONLY", "ESCALATE", "DENY"]
LocationSource = Literal["user_confirmed", "network", "device", "simulated", "unknown"]
OriginKind = Literal["user", "agent", "workflow"]
NetworkState = Literal["offline", "local", "online", "unknown"]

_DECISION_RANK: dict[LegitimacyDecisionKind, int] = {
    "ALLOW_CLI": 0,
    "PROBE_ONLY": 1,
    "ESCALATE": 2,
    "DENY": 3,
}

_HIGH_RISK_TOOLS = {
    "terminal.shell.raw",
    "terminal.command.request",
    "fs.write",
    "fs.delete",
    "git.push",
    "deploy.publish",
    "hardware.actuate",
    "mobility.actuate",
}

_READ_ONLY_TOOLS = {
    "metrics.read",
    "time.read",
    "date.read",
    "location.read",
    "fs.list",
    "fs.read",
    "git.status",
}


@dataclass(frozen=True)
class LegitimacyFinding:
    """One mechanical legitimacy finding."""

    rule: str
    decision: LegitimacyDecisionKind
    message: str
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CoarseLocation:
    """Non-secret, low-precision operating context."""

    source: LocationSource = "unknown"
    label: str = "unknown"
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SystemMetrics:
    """Small host/workspace attestation subset for pre-command decisions."""

    host_id_hash: str
    platform: str
    cwd_hash: str
    process_id: int
    network_state: NetworkState = "unknown"
    workspace: Optional[str] = None
    workspace_hash: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IntentPacket:
    """Intent statement that the security matrix compares against context."""

    goal: str
    origin: OriginKind
    expected_tool: str
    expected_state: str = "unspecified"
    privacy: Literal["local_only", "hosted"] = "local_only"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GeoSealLegitimacyPacket:
    """Situated pre-authority packet."""

    request_id: str
    requested_at: str
    local_time: str
    timezone: str
    coarse_location: CoarseLocation
    system_metrics: SystemMetrics
    intent_packet: IntentPacket
    command: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "requested_at": self.requested_at,
            "local_time": self.local_time,
            "timezone": self.timezone,
            "coarse_location": self.coarse_location.to_dict(),
            "system_metrics": self.system_metrics.to_dict(),
            "intent_packet": self.intent_packet.to_dict(),
            "command": self.command,
        }


@dataclass(frozen=True)
class GeoSealLegitimacyDecision:
    """Result of the legitimacy trial."""

    request_id: str
    decision: LegitimacyDecisionKind
    allowed_cli: bool
    score: float
    packet_sha256: str
    findings: list[LegitimacyFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "geoseal-legitimacy-trial-v1",
            "request_id": self.request_id,
            "decision": self.decision,
            "allowed_cli": self.allowed_cli,
            "score": self.score,
            "packet_sha256": self.packet_sha256,
            "findings": [finding.to_dict() for finding in self.findings],
        }


def _sha256_json(payload: Mapping[str, Any]) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _max_decision(findings: list[LegitimacyFinding]) -> LegitimacyDecisionKind:
    decision: LegitimacyDecisionKind = "ALLOW_CLI"
    for finding in findings:
        if _DECISION_RANK[finding.decision] > _DECISION_RANK[decision]:
            decision = finding.decision
    return decision


def collect_system_metrics(
    *,
    workspace: Optional[Path] = None,
    network_state: NetworkState = "unknown",
) -> SystemMetrics:
    """Collect a minimal non-secret host/workspace attestation packet."""

    cwd = Path.cwd().resolve()
    resolved_workspace = workspace.resolve() if workspace is not None else None
    host_material = "|".join(
        [
            platform.node() or socket.gethostname() or "unknown-host",
            platform.system(),
            platform.machine(),
        ]
    )
    workspace_text = str(resolved_workspace) if resolved_workspace is not None else None
    return SystemMetrics(
        host_id_hash=_short_hash(host_material),
        platform=f"{platform.system()} {platform.release()} {platform.machine()}".strip(),
        cwd_hash=_short_hash(str(cwd)),
        process_id=os.getpid(),
        network_state=network_state,
        workspace=workspace_text,
        workspace_hash=_short_hash(workspace_text) if workspace_text else None,
    )


def build_legitimacy_packet(
    *,
    goal: str,
    expected_tool: str,
    origin: OriginKind = "user",
    expected_state: str = "unspecified",
    privacy: Literal["local_only", "hosted"] = "local_only",
    command: Optional[str] = None,
    workspace: Optional[Path] = None,
    location: Optional[CoarseLocation] = None,
    network_state: NetworkState = "unknown",
    request_id: Optional[str] = None,
) -> GeoSealLegitimacyPacket:
    """Build a current legitimacy packet for CLI/harness callers."""

    now = _now_iso()
    packet_id = request_id or _short_hash(f"{now}|{goal}|{expected_tool}|{command or ''}|{time.perf_counter_ns()}")
    return GeoSealLegitimacyPacket(
        request_id=packet_id,
        requested_at=now,
        local_time=datetime.now().astimezone().isoformat(timespec="seconds"),
        timezone=datetime.now().astimezone().tzname() or "unknown",
        coarse_location=location or CoarseLocation(),
        system_metrics=collect_system_metrics(workspace=workspace, network_state=network_state),
        intent_packet=IntentPacket(
            goal=goal,
            origin=origin,
            expected_tool=expected_tool,
            expected_state=expected_state,
            privacy=privacy,
        ),
        command=command,
    )


def _path_within_workspace(path_text: str, workspace_text: str) -> bool:
    try:
        path = Path(path_text).expanduser().resolve()
        workspace = Path(workspace_text).expanduser().resolve()
    except OSError:
        return False
    return path == workspace or workspace in path.parents


def evaluate_legitimacy(packet: GeoSealLegitimacyPacket) -> GeoSealLegitimacyDecision:
    """Evaluate a legitimacy packet into ALLOW_CLI/PROBE_ONLY/ESCALATE/DENY."""

    findings: list[LegitimacyFinding] = []
    intent = packet.intent_packet
    metrics = packet.system_metrics
    location = packet.coarse_location
    command = packet.command or ""

    if not intent.goal.strip():
        findings.append(LegitimacyFinding("missing-goal", "DENY", "intent goal is required"))

    if not intent.expected_tool.strip():
        findings.append(LegitimacyFinding("missing-tool", "DENY", "expected tool is required"))

    if metrics.workspace:
        if not Path(metrics.workspace).exists():
            findings.append(
                LegitimacyFinding("workspace-missing", "DENY", "declared workspace does not exist", metrics.workspace)
            )
    elif intent.expected_tool not in _READ_ONLY_TOOLS:
        findings.append(
            LegitimacyFinding(
                "workspace-unscoped",
                "PROBE_ONLY",
                "write/execute authority needs a declared workspace",
                intent.expected_tool,
            )
        )

    if location.source == "unknown" or location.confidence < 0.25:
        if intent.expected_tool not in _READ_ONLY_TOOLS:
            findings.append(
                LegitimacyFinding(
                    "weak-location-context",
                    "PROBE_ONLY",
                    "location/context confidence is weak; execution should stay probe-only",
                    f"{location.source}:{location.confidence}",
                )
            )
    elif location.confidence < 0.6 and intent.expected_tool in _HIGH_RISK_TOOLS:
        findings.append(
            LegitimacyFinding(
                "medium-location-context",
                "ESCALATE",
                "high-risk tool needs stronger location/context confidence",
                f"{location.source}:{location.confidence}",
            )
        )

    if intent.privacy == "local_only" and metrics.network_state == "online" and intent.expected_tool.startswith("llm."):
        findings.append(
            LegitimacyFinding(
                "privacy-route-mismatch",
                "ESCALATE",
                "local_only intent should not route to online LLM tools without approval",
                intent.expected_tool,
            )
        )

    if intent.origin in {"agent", "workflow"} and intent.expected_tool in _HIGH_RISK_TOOLS:
        findings.append(
            LegitimacyFinding(
                "non-user-high-risk",
                "ESCALATE",
                "agent/workflow high-risk authority requires explicit approval",
                f"{intent.origin}:{intent.expected_tool}",
            )
        )

    if command:
        exec_decision = scan_command(command, claimed_paths=[metrics.workspace] if metrics.workspace else None)
        if exec_decision.tier == "DENY":
            tier = "DENY"
        elif TIER_RANK[exec_decision.tier] >= TIER_RANK["ESCALATE"]:
            tier = "ESCALATE"
        elif TIER_RANK[exec_decision.tier] >= TIER_RANK["QUARANTINE"]:
            tier = "PROBE_ONLY"
        else:
            tier = "ALLOW_CLI"
        for finding in exec_decision.findings:
            assert isinstance(finding, GateFinding)
            findings.append(
                LegitimacyFinding(
                    f"exec-gate:{finding.rule}",
                    tier,
                    finding.message,
                    finding.evidence,
                )
            )

    decision = _max_decision(findings)
    score = max(0.0, round(1.0 - (_DECISION_RANK[decision] * 0.33) - (0.02 * max(0, len(findings) - 1)), 4))
    packet_dict = packet.to_dict()
    return GeoSealLegitimacyDecision(
        request_id=packet.request_id,
        decision=decision,
        allowed_cli=decision == "ALLOW_CLI",
        score=score,
        packet_sha256=_sha256_json(packet_dict),
        findings=findings,
    )


def run_legitimacy_trial(
    *,
    goal: str,
    expected_tool: str,
    origin: OriginKind = "user",
    expected_state: str = "unspecified",
    privacy: Literal["local_only", "hosted"] = "local_only",
    command: Optional[str] = None,
    workspace: Optional[Path] = None,
    location: Optional[CoarseLocation] = None,
    network_state: NetworkState = "unknown",
) -> dict[str, Any]:
    """Build and evaluate a legitimacy packet, returning JSON-friendly output."""

    packet = build_legitimacy_packet(
        goal=goal,
        expected_tool=expected_tool,
        origin=origin,
        expected_state=expected_state,
        privacy=privacy,
        command=command,
        workspace=workspace,
        location=location,
        network_state=network_state,
    )
    decision = evaluate_legitimacy(packet)
    return {
        "schema_version": "geoseal-legitimacy-result-v1",
        "packet": packet.to_dict(),
        "decision": decision.to_dict(),
    }
