#!/usr/bin/env python3
"""Fuse antivirus, EDR, SIEM, and runtime alerts into one SCBE decision.

This is the bridge layer: keep existing AV/EDR tools in place, normalize their
alerts, optionally inspect the referenced artifact without executing it, then
emit one governance receipt for agents, CI, and operators.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.antivirus_membrane import scan_text_for_threats
from src.scbe_math_reference import harm_score_from_wall, harmonic_wall_eff, omega_gate

SCHEMA_VERSION = "scbe_av_signal_fusion_v1"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "security" / "av_signal_fusion"

SEVERITY_WEIGHTS = {
    "CRITICAL": 1.0,
    "HIGH": 0.78,
    "MEDIUM": 0.52,
    "LOW": 0.24,
    "INFO": 0.08,
    "UNKNOWN": 0.18,
}

STRICTNESS = {"ALLOW": 0, "QUARANTINE": 1, "DENY": 2}


@dataclass(frozen=True)
class NormalizedAlert:
    provider: str
    severity: str
    category: str
    title: str
    description: str = ""
    artifact_path: str = ""
    artifact_sha256: str = ""
    raw_id: str = ""


@dataclass(frozen=True)
class FusionMetrics:
    external_risk: float
    semantic_risk: float
    artifact_risk: float
    event_risk: float
    coherence: float
    d_star: float
    h_eff: float
    harm_score: float
    omega: float


@dataclass
class FusionReport:
    schema: str
    created_at_utc: str
    alert_count: int
    providers: list[str]
    decision: str
    metrics: FusionMetrics
    alerts: list[NormalizedAlert] = field(default_factory=list)
    artifact_report: dict[str, Any] | None = None
    event_report: dict[str, Any] | None = None
    recommended_actions: list[str] = field(default_factory=list)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def public_path(path: Path) -> str:
    raw = str(path.resolve())
    replacements = {
        str(REPO_ROOT): "%REPO%",
        str(Path.home()): "%USERPROFILE%",
    }
    out = raw
    for source, replacement in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        out = out.replace(source, replacement)
    return out


def load_artifact_triage():
    script = REPO_ROOT / "scripts" / "security" / "artifact_triage.py"
    spec = importlib.util.spec_from_file_location("_scbe_artifact_triage_for_fusion", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load artifact triage script: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_security_event_layers():
    script = REPO_ROOT / "scripts" / "security" / "security_event_layers.py"
    spec = importlib.util.spec_from_file_location("_scbe_security_event_layers_for_fusion", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load security event layers script: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_signal_input(path: Path) -> list[Any]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and isinstance(parsed.get("value"), list):
            return list(parsed["value"])
        return [parsed]
    except json.JSONDecodeError:
        rows: list[Any] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rows.append(json.loads(stripped))
            except json.JSONDecodeError:
                rows.append(stripped)
        return rows


def normalize_severity(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if raw in {"CRITICAL", "SEVERE", "FATAL"}:
        return "CRITICAL"
    if raw in {"HIGH", "ERROR", "ALERT", "EMERGENCY"}:
        return "HIGH"
    if raw in {"MEDIUM", "MODERATE", "WARNING", "WARN"}:
        return "MEDIUM"
    if raw in {"LOW", "NOTICE"}:
        return "LOW"
    if raw in {"INFO", "INFORMATIONAL", "DEBUG"}:
        return "INFO"
    try:
        level = int(float(raw))
    except ValueError:
        return "UNKNOWN"
    if level >= 14:
        return "CRITICAL"
    if level >= 10:
        return "HIGH"
    if level >= 6:
        return "MEDIUM"
    if level >= 3:
        return "LOW"
    return "INFO"


def detect_provider(raw: Any, fallback: str = "generic") -> str:
    if isinstance(raw, str):
        lower = raw.lower()
        if " found" in lower:
            return "clamav"
        if "rule=" in lower or lower.startswith("rule "):
            return "yara"
        return fallback
    keys = {str(k).lower() for k in raw.keys()}
    if {"detectionSource".lower(), "machineId".lower()} & keys or "incidentid" in keys:
        return "microsoft_defender"
    if "rule" in keys and isinstance(raw.get("rule"), dict) and "level" in raw.get("rule", {}):
        return "wazuh"
    if "priority" in keys and "output" in keys and "rule" in keys:
        return "falco"
    if "signature" in keys or "clamav" in str(raw).lower():
        return "clamav"
    if "sigma" in keys or "logsource" in keys:
        return "sigma"
    if "yara_rule" in keys or "matches" in keys:
        return "yara"
    return fallback


def _first_text(raw: dict[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = raw.get(key)
        if value is not None and value != "":
            return str(value)
    return ""


def _defender_artifact(raw: dict[str, Any]) -> tuple[str, str]:
    for ev in raw.get("evidence", []) or []:
        if not isinstance(ev, dict):
            continue
        file_name = str(ev.get("fileName") or "")
        file_path = str(ev.get("filePath") or "")
        sha256 = str(ev.get("sha256") or "")
        if file_name or file_path or sha256:
            return str(Path(file_path) / file_name) if file_path and file_name else file_name or file_path, sha256
    return "", ""


def normalize_alert(raw: Any, *, provider_hint: str = "generic") -> NormalizedAlert:
    provider = detect_provider(raw, provider_hint)
    if isinstance(raw, str):
        title = raw[:240]
        severity = "HIGH" if re.search(r"\b(found|malware|trojan|blocked)\b", raw, re.I) else "INFO"
        path = raw.split(":", 1)[0] if ":" in raw else ""
        category = "signature_match" if provider in {"clamav", "yara"} else "text_alert"
        return NormalizedAlert(provider, severity, category, title, artifact_path=path)

    severity = normalize_severity(
        raw.get("severity")
        or raw.get("priority")
        or raw.get("level")
        or (raw.get("rule") or {}).get("level")
        or raw.get("risk")
    )
    title = _first_text(raw, ("title", "name", "rule", "signature", "threatName", "description"))
    if isinstance(raw.get("rule"), dict):
        title = str(raw["rule"].get("description") or raw["rule"].get("id") or title)
    description = _first_text(raw, ("description", "output", "message", "full_log", "alert"))
    category = _first_text(raw, ("category", "type", "source", "detectionSource", "event_type")) or provider
    artifact_path = _first_text(
        raw, ("artifact_path", "file_path", "filePath", "path", "target", "filename", "fileName")
    )
    artifact_sha256 = _first_text(raw, ("sha256", "artifact_sha256", "hash"))
    if provider == "microsoft_defender":
        defender_path, defender_sha = _defender_artifact(raw)
        artifact_path = artifact_path or defender_path
        artifact_sha256 = artifact_sha256 or defender_sha
    raw_id = _first_text(raw, ("id", "alert_id", "rule_id", "incidentId"))
    return NormalizedAlert(provider, severity, category, title, description, artifact_path, artifact_sha256, raw_id)


def external_risk(alerts: list[NormalizedAlert]) -> float:
    if not alerts:
        return 0.0
    weights = [SEVERITY_WEIGHTS.get(alert.severity, SEVERITY_WEIGHTS["UNKNOWN"]) for alert in alerts]
    # Consensus grows with independent alerts, but caps before becoming absolute.
    return round(clamp01(1.0 - math.exp(-sum(weights) / 1.6)), 4)


def semantic_risk(alerts: list[NormalizedAlert]) -> float:
    text = "\n".join(f"{a.provider} {a.severity} {a.category} {a.title} {a.description}" for a in alerts)
    return scan_text_for_threats(text).risk_score


def artifact_signal(artifact: Path | None, alerts: list[NormalizedAlert]) -> tuple[float, dict[str, Any] | None]:
    candidates: list[Path] = []
    if artifact is not None:
        candidates.append(artifact)
    for alert in alerts:
        if alert.artifact_path:
            p = Path(alert.artifact_path)
            if not p.is_absolute():
                p = REPO_ROOT / p
            candidates.append(p)
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            triage = load_artifact_triage()
            report = triage.triage_artifact(candidate)
            payload = triage.report_to_dict(report)
            return round(clamp01(float(payload["risk_score"]) / 80.0), 4), payload
    return 0.0, None


def event_signal(raw_items: list[Any]) -> tuple[float, dict[str, Any] | None]:
    if not raw_items:
        return 0.0, None
    layers = load_security_event_layers()
    report = layers.classify_events(raw_items)
    payload = layers.report_to_dict(report)
    return round(clamp01(float(payload["risk_score"]) / 90.0), 4), payload


def decision_from_signals(
    metrics: FusionMetrics,
    alerts: list[NormalizedAlert],
    artifact_report: dict[str, Any] | None,
    event_report: dict[str, Any] | None,
) -> str:
    if artifact_report and artifact_report.get("decision") == "DENY":
        return "DENY"
    if event_report and event_report.get("decision") == "DENY":
        return "DENY"
    if any(alert.severity == "CRITICAL" for alert in alerts):
        return "DENY"
    if metrics.omega <= 0.40:
        return "DENY"
    if artifact_report and artifact_report.get("decision") == "QUARANTINE":
        return "QUARANTINE"
    if event_report and event_report.get("decision") == "QUARANTINE":
        return "QUARANTINE"
    if any(alert.severity == "HIGH" for alert in alerts):
        return "QUARANTINE"
    if metrics.external_risk >= 0.45 or metrics.semantic_risk >= 0.25 or metrics.event_risk >= 0.25:
        return "QUARANTINE"
    return "ALLOW"


def recommended_actions(
    decision: str,
    alerts: list[NormalizedAlert],
    artifact_report: dict[str, Any] | None,
    event_report: dict[str, Any] | None,
) -> list[str]:
    actions = [
        "Preserve this fusion receipt with the upstream AV/EDR alert IDs.",
        "Do not execute referenced artifacts unless a sandboxed analysis step is explicitly approved.",
    ]
    if decision == "DENY":
        actions.append(
            "Block agent execution, CI promotion, and customer-facing deploy until a human clears the event."
        )
    elif decision == "QUARANTINE":
        actions.append("Route the task to isolated review and require provenance before merge or execution.")
    else:
        actions.append("Allow the workflow but keep the receipt attached to the agent/job record.")
    if any(a.provider in {"falco", "wazuh"} for a in alerts):
        actions.append(
            "If this came from runtime telemetry, compare against expected service behavior before suppressing."
        )
    if artifact_report:
        actions.extend(artifact_report.get("recommended_next_steps", [])[:3])
    if event_report:
        actions.extend(event_report.get("recommended_actions", [])[:3])
    return list(dict.fromkeys(actions))


def fuse_signals(raw_items: list[Any], *, artifact: Path | None = None, provider_hint: str = "generic") -> FusionReport:
    alerts = [normalize_alert(item, provider_hint=provider_hint) for item in raw_items]
    ext = external_risk(alerts)
    sem = semantic_risk(alerts)
    art, artifact_report = artifact_signal(artifact, alerts)
    evt, event_report = event_signal(raw_items)
    blended = clamp01((0.38 * ext) + (0.22 * sem) + (0.20 * art) + (0.20 * evt))
    coherence = round(clamp01(1.0 - blended), 4)
    d_star = round(0.95 * math.sqrt(blended), 4)
    x_factor = 1.0 + min(1.5, len(alerts) * 0.08)
    h_eff = harmonic_wall_eff(d_star, x_factor)
    harm = harm_score_from_wall(h_eff)
    omega = omega_gate(
        pqc_valid=1.0,
        harm_score=harm,
        drift_factor=coherence,
        triadic_stable=clamp01(1.0 - art * 0.45),
        spectral_score=clamp01(1.0 - sem * 0.60),
    )
    metrics = FusionMetrics(
        external_risk=ext,
        semantic_risk=round(sem, 4),
        artifact_risk=art,
        event_risk=evt,
        coherence=coherence,
        d_star=d_star,
        h_eff=round(h_eff, 6),
        harm_score=round(harm, 6),
        omega=round(omega, 6),
    )
    decision = decision_from_signals(metrics, alerts, artifact_report, event_report)
    return FusionReport(
        schema=SCHEMA_VERSION,
        created_at_utc=now_utc(),
        alert_count=len(alerts),
        providers=sorted({alert.provider for alert in alerts}),
        decision=decision,
        metrics=metrics,
        alerts=alerts,
        artifact_report=artifact_report,
        event_report=event_report,
        recommended_actions=recommended_actions(decision, alerts, artifact_report, event_report),
    )


def report_to_dict(report: FusionReport) -> dict[str, Any]:
    return {
        "schema": report.schema,
        "created_at_utc": report.created_at_utc,
        "alert_count": report.alert_count,
        "providers": report.providers,
        "decision": report.decision,
        "metrics": asdict(report.metrics),
        "alerts": [asdict(alert) for alert in report.alerts],
        "artifact_report": report.artifact_report,
        "event_report": report.event_report,
        "recommended_actions": report.recommended_actions,
    }


def report_id(payload: dict[str, Any]) -> str:
    stable = json.dumps(
        {
            "providers": payload.get("providers"),
            "decision": payload.get("decision"),
            "alerts": payload.get("alerts"),
            "artifact_sha256": (payload.get("artifact_report") or {}).get("artifact_sha256"),
            "event_controls": (payload.get("event_report") or {}).get("controls"),
        },
        sort_keys=True,
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()[:16]


def exit_code(decision: str) -> int:
    if decision == "DENY":
        return 2
    if decision == "QUARANTINE":
        return 1
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="JSON, JSONL, or log file containing AV/EDR alerts")
    parser.add_argument("--artifact", type=Path, default=None, help="Optional local artifact to triage with the alerts")
    parser.add_argument("--provider", default="generic", help="Provider hint when the input cannot be detected")
    parser.add_argument("--json", action="store_true", help="Print full JSON receipt")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = fuse_signals(read_signal_input(args.input), artifact=args.artifact, provider_hint=args.provider)
    payload = report_to_dict(report)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"{report_id(payload)}.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            f"[av-signal-fusion] {report.decision} alerts={report.alert_count} "
            f"providers={','.join(report.providers) or 'none'} omega={report.metrics.omega} "
            f"coherence={report.metrics.coherence} report={public_path(out_path)}"
        )
    return exit_code(report.decision)


if __name__ == "__main__":
    raise SystemExit(main())
