"""
Enemy-first extension gate.

Goal:
- Keep user extension onboarding low-friction.
- Push security friction onto hostile/malicious extensions.

This module composes:
1) content scan (agents.antivirus_membrane.scan_text_for_threats)
2) policy scoring (permissions + provenance)
3) domain-aware turnstile resolution (hydra.turnstile.resolve_turnstile)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Iterable
from urllib.parse import urlparse

from agents.antivirus_membrane import ThreatScan, scan_text_for_threats
from hydra.turnstile import TurnstileOutcome, resolve_turnstile


SAFE_SOURCE_DOMAINS = {
    "github.com",
    "raw.githubusercontent.com",
    "huggingface.co",
    "hf.co",
}

PERMISSION_RISK = {
    # low risk
    "read_dom": 0.02,
    "local_storage": 0.03,
    "model_inference": 0.03,
    "tool_execute": 0.04,
    # medium
    "network_fetch": 0.08,
    "write_dom": 0.10,
    "cookies": 0.12,
    "clipboard": 0.12,
    "tool_create": 0.14,
    # high
    "filesystem_read": 0.18,
    "filesystem_write": 0.22,
    "shell_access": 0.35,
    "exec_command": 0.35,
    "camera": 0.25,
    "microphone": 0.25,
    "geo": 0.15,
}


@dataclass(frozen=True)
class ExtensionManifest:
    name: str
    version: str
    source_url: str
    entrypoint: str
    requested_permissions: tuple[str, ...]
    sha256: str | None = None
    description: str = ""
    publisher: str = ""

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ExtensionManifest":
        perms = tuple(sorted(set(str(x).strip().lower() for x in data.get("requested_permissions", ()) if str(x).strip())))
        return ExtensionManifest(
            name=str(data.get("name", "")).strip(),
            version=str(data.get("version", "")).strip(),
            source_url=str(data.get("source_url", "")).strip(),
            entrypoint=str(data.get("entrypoint", "")).strip(),
            requested_permissions=perms,
            sha256=(str(data["sha256"]).strip() if data.get("sha256") else None),
            description=str(data.get("description", "")).strip(),
            publisher=str(data.get("publisher", "")).strip(),
        )


@dataclass(frozen=True)
class ExtensionGateResult:
    decision: str
    suspicion: float
    geometry_norm: float
    manifest_risk: float
    provenance_risk: float
    threat_scan: ThreatScan
    turnstile: TurnstileOutcome
    enabled_permissions: tuple[str, ...]
    blocked_permissions: tuple[str, ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "suspicion": self.suspicion,
            "geometry_norm": self.geometry_norm,
            "manifest_risk": self.manifest_risk,
            "provenance_risk": self.provenance_risk,
            "threat_scan": self.threat_scan.to_dict(),
            "turnstile": asdict(self.turnstile),
            "enabled_permissions": list(self.enabled_permissions),
            "blocked_permissions": list(self.blocked_permissions),
            "notes": list(self.notes),
        }


def _clamp01(x: float) -> float:
    return min(1.0, max(0.0, x))


def _domain(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _permission_risk(perms: Iterable[str]) -> tuple[float, tuple[str, ...]]:
    score = 0.0
    unknown = []
    for p in perms:
        if p in PERMISSION_RISK:
            score += PERMISSION_RISK[p]
        else:
            score += 0.10
            unknown.append(p)
    return _clamp01(score), tuple(sorted(unknown))


def _provenance_risk(manifest: ExtensionManifest) -> tuple[float, tuple[str, ...]]:
    notes = []
    risk = 0.0

    host = _domain(manifest.source_url)
    if not host:
        risk += 0.35
        notes.append("invalid source_url")
    elif host not in SAFE_SOURCE_DOMAINS:
        risk += 0.20
        notes.append(f"untrusted host: {host}")

    if not manifest.sha256:
        risk += 0.25
        notes.append("missing sha256 pin")
    elif len(manifest.sha256) != 64:
        risk += 0.20
        notes.append("invalid sha256 length")

    if not manifest.entrypoint:
        risk += 0.20
        notes.append("missing entrypoint")

    if not manifest.name or not manifest.version:
        risk += 0.15
        notes.append("missing manifest identity fields")

    return _clamp01(risk), tuple(notes)


def _base_decision(suspicion: float) -> str:
    if suspicion >= 0.85:
        return "DENY"
    if suspicion >= 0.60:
        return "ESCALATE"
    if suspicion >= 0.30:
        return "QUARANTINE"
    return "ALLOW"


def _permission_partition(
    perms: tuple[str, ...],
    suspicion: float,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if suspicion >= 0.60:
        # hostile profile: block all, quarantine object for analysis.
        return tuple(), perms

    enabled = []
    blocked = []
    for p in perms:
        risk = PERMISSION_RISK.get(p, 0.10)
        if suspicion < 0.30:
            # low suspicion: allow all known permissions except strongest execution channels
            if p in {"exec_command", "shell_access"}:
                blocked.append(p)
            else:
                enabled.append(p)
        else:
            # medium suspicion: conservative allowlist
            if risk <= 0.10 and p not in {"cookies", "clipboard"}:
                enabled.append(p)
            else:
                blocked.append(p)
    return tuple(sorted(enabled)), tuple(sorted(blocked))


def evaluate_extension_install(
    manifest: ExtensionManifest | dict[str, Any],
    *,
    preview_text: str = "",
    domain: str = "browser",
    previous_antibody_load: float = 0.0,
) -> ExtensionGateResult:
    """
    Evaluate extension installation using enemy-first gating.

    Domain:
    - browser: human review path available (HOLD)
    - antivirus: suspicious artifacts isolate/honeypot
    """
    if not isinstance(manifest, ExtensionManifest):
        manifest = ExtensionManifest.from_dict(manifest)

    scan_input = "\n".join(
        [
            manifest.name,
            manifest.version,
            manifest.source_url,
            manifest.entrypoint,
            manifest.description,
            preview_text,
            " ".join(manifest.requested_permissions),
        ]
    )
    scan = scan_text_for_threats(scan_input)

    perm_risk, unknown_perms = _permission_risk(manifest.requested_permissions)
    prov_risk, prov_notes = _provenance_risk(manifest)

    # Enemy-first combined suspicion: content threats dominate, then manifest/provenance.
    suspicion = _clamp01(0.55 * scan.risk_score + 0.25 * perm_risk + 0.20 * prov_risk)
    geometry_norm = _clamp01(0.20 + 0.75 * suspicion)
    decision = _base_decision(suspicion)

    turnstile = resolve_turnstile(
        decision=decision,
        domain=domain,
        suspicion=suspicion,
        geometry_norm=geometry_norm,
        previous_antibody_load=previous_antibody_load,
        quorum_ok=True,
    )

    enabled_permissions, blocked_permissions = _permission_partition(
        manifest.requested_permissions,
        suspicion=suspicion,
    )
    notes = list(scan.reasons)
    notes.extend(prov_notes)
    if unknown_perms:
        notes.append(f"unknown permissions={','.join(unknown_perms)}")

    if not blocked_permissions and turnstile.action == "ALLOW":
        notes.append("user extension enabled with low friction")
    elif turnstile.action in {"HOLD", "ISOLATE", "HONEYPOT", "STOP"}:
        notes.append("enemy friction elevated by turnstile")
    else:
        notes.append("extension degraded to reduced permission set")

    return ExtensionGateResult(
        decision=decision,
        suspicion=round(suspicion, 4),
        geometry_norm=round(geometry_norm, 4),
        manifest_risk=round(perm_risk, 4),
        provenance_risk=round(prov_risk, 4),
        threat_scan=scan,
        turnstile=turnstile,
        enabled_permissions=enabled_permissions,
        blocked_permissions=blocked_permissions,
        notes=tuple(notes),
    )
