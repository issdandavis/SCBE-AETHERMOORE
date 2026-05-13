#!/usr/bin/env python3
"""Traditional security controls for non-artifact events.

This layer evaluates events such as model prompts/outputs, shell commands,
dependency installs, network calls, environment/config access, and runtime
process telemetry. It emits a deterministic ALLOW/QUARANTINE/DENY receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.antivirus_membrane import scan_text_for_threats

SCHEMA_VERSION = "scbe_security_event_layers_v1"
DEFAULT_POLICY_PATH = REPO_ROOT / "config" / "security" / "security_event_policy.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "security" / "security_events"


@dataclass(frozen=True)
class EventHit:
    control: str
    severity: str
    weight: int
    message: str


@dataclass(frozen=True)
class NormalizedSecurityEvent:
    event_type: str
    actor: str
    action: str
    target: str
    text: str
    metadata: dict[str, Any]


@dataclass
class SecurityEventReport:
    schema: str
    created_at_utc: str
    event_count: int
    decision: str
    risk_score: int
    normalized_events: list[NormalizedSecurityEvent] = field(default_factory=list)
    controls: list[EventHit] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_policy(path: Path = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_events(path: Path) -> list[Any]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and isinstance(parsed.get("events"), list):
            return list(parsed["events"])
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
                rows.append({"event_type": "log", "text": stripped})
        return rows


def _first(raw: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = raw.get(key)
        if value is not None and value != "":
            return str(value)
    return ""


def normalize_event(raw: Any) -> NormalizedSecurityEvent:
    if isinstance(raw, str):
        return NormalizedSecurityEvent("log", "", "", "", raw, {})
    event_type = _first(raw, ("event_type", "type", "kind", "category", "source")) or "generic"
    actor = _first(raw, ("actor", "agent", "user", "provider", "model"))
    action = _first(raw, ("action", "command", "method", "operation", "finish_reason", "decision"))
    target = _first(raw, ("target", "url", "host", "path", "file", "endpoint"))
    text = _first(raw, ("text", "prompt", "output", "content", "message", "body", "description", "command"))
    metadata = {str(k): v for k, v in raw.items() if k not in {"text", "prompt", "output", "content", "message", "body"}}
    return NormalizedSecurityEvent(event_type, actor, action, target, text, metadata)


def host_from_target(target: str) -> str:
    if not target:
        return ""
    parsed = urlsplit(target if "://" in target else f"//{target}")
    return (parsed.hostname or "").lower()


def classify_events(raw_events: list[Any], policy_path: Path = DEFAULT_POLICY_PATH) -> SecurityEventReport:
    policy = load_policy(policy_path)
    events = [normalize_event(raw) for raw in raw_events]
    controls: list[EventHit] = []
    trusted_hosts = {str(host).lower() for host in policy.get("trusted_hosts", [])}
    blocked_hosts = {str(host).lower() for host in policy.get("blocked_hosts", [])}
    dangerous_commands = [str(item).lower() for item in policy.get("dangerous_commands", [])]
    install_commands = [str(item).lower() for item in policy.get("install_commands", [])]
    sensitive_paths = [str(item).lower().replace("\\", "/") for item in policy.get("sensitive_paths", [])]
    secret_markers = [str(item).upper() for item in policy.get("secret_env_markers", [])]

    for event in events:
        lower_text = event.text.lower()
        lower_action = event.action.lower()
        lower_target = event.target.lower().replace("\\", "/")
        combined = " ".join([lower_text, lower_action, lower_target])
        scan = scan_text_for_threats(event.text)
        if scan.risk_score >= 0.85:
            controls.append(EventHit("semantic_text_malicious", "CRITICAL", 35, "Prompt/output/log text matched malicious semantic controls."))
        elif scan.risk_score >= 0.55:
            controls.append(EventHit("semantic_text_suspicious", "HIGH", 22, "Prompt/output/log text matched suspicious semantic controls."))
        elif scan.risk_score >= 0.25:
            controls.append(EventHit("semantic_text_caution", "MEDIUM", 10, "Prompt/output/log text matched caution semantic controls."))

        if any(pattern in combined for pattern in dangerous_commands):
            controls.append(EventHit("dangerous_command", "CRITICAL", 42, "Command contains a known dangerous execution pattern."))
        if re.search(r"\b(subprocess|os\.system|child_process|exec|eval)\b", combined):
            controls.append(EventHit("dynamic_execution_event", "HIGH", 18, "Event invokes dynamic command/code execution."))
        if any(command in combined for command in install_commands):
            controls.append(EventHit("dependency_install_event", "MEDIUM", 10, "Event installs or runs dependency tooling."))
        if re.search(r"--registry\s+https?://(?!registry\.npmjs\.org)|--index-url\s+https?://(?!pypi\.org)", combined):
            controls.append(EventHit("non_default_package_registry", "HIGH", 24, "Dependency install uses a non-default package registry."))
        if re.search(r"\b(--force|--legacy-peer-deps|--ignore-scripts|--trusted-host)\b", combined):
            controls.append(EventHit("dependency_guardrail_override", "MEDIUM", 12, "Dependency command disables or weakens normal guardrails."))

        host = host_from_target(event.target)
        if host and host in blocked_hosts:
            controls.append(EventHit("blocked_host", "CRITICAL", 45, f"Target host is explicitly blocked: {host}"))
        elif host and host not in trusted_hosts and not host.endswith(".github.com"):
            controls.append(EventHit("untrusted_network_target", "MEDIUM", 10, f"Target host is not in the trusted host policy: {host}"))

        if any(marker in combined.upper() for marker in secret_markers):
            controls.append(EventHit("secret_env_reference", "HIGH", 20, "Event references secret-looking environment material."))
        if any(path in lower_target or path in combined for path in sensitive_paths):
            controls.append(EventHit("sensitive_path_reference", "HIGH", 18, "Event references sensitive config/key material."))
        if event.event_type.lower() in {"governed_output", "model_io", "chat"}:
            decision = str(event.metadata.get("decision") or event.action).upper()
            finish = str(event.metadata.get("finish_reason") or "").lower()
            if decision == "DENY" or finish == "content_filter":
                controls.append(EventHit("governed_output_block", "CRITICAL", 40, "Governed-output surface blocked unsafe model/input behavior."))
            elif decision in {"QUARANTINE", "ESCALATE"}:
                controls.append(EventHit("governed_output_intervention", "HIGH", 18, "Governed-output surface required intervention."))

    score = max(0, sum(hit.weight for hit in controls))
    critical = any(hit.severity == "CRITICAL" for hit in controls)
    high_count = sum(1 for hit in controls if hit.severity == "HIGH")
    if critical or score >= 45:
        decision = "DENY"
    elif high_count or score >= 18:
        decision = "QUARANTINE"
    else:
        decision = "ALLOW"

    actions = ["Attach this event receipt to the agent job, request, or CI run."]
    if decision == "DENY":
        actions.append("Block the action before command execution, model response release, merge, or deploy.")
    elif decision == "QUARANTINE":
        actions.append("Route the event to isolated review and require explicit operator approval.")
    else:
        actions.append("Allow the event and keep the receipt for replay/training.")
    if any(hit.control == "dependency_install_event" for hit in controls):
        actions.append("Run lockfile/audit verification before trusting installed code.")
    if any(hit.control == "governed_output_block" for hit in controls):
        actions.append("Keep the refusal/intervention output; do not leak the raw unsafe model text.")

    return SecurityEventReport(
        schema=SCHEMA_VERSION,
        created_at_utc=now_utc(),
        event_count=len(events),
        decision=decision,
        risk_score=score,
        normalized_events=events,
        controls=controls,
        recommended_actions=list(dict.fromkeys(actions)),
    )


def report_to_dict(report: SecurityEventReport) -> dict[str, Any]:
    return {
        "schema": report.schema,
        "created_at_utc": report.created_at_utc,
        "event_count": report.event_count,
        "decision": report.decision,
        "risk_score": report.risk_score,
        "normalized_events": [asdict(event) for event in report.normalized_events],
        "controls": [asdict(hit) for hit in report.controls],
        "recommended_actions": report.recommended_actions,
    }


def report_id(payload: dict[str, Any]) -> str:
    stable = json.dumps(
        {
            "decision": payload.get("decision"),
            "events": payload.get("normalized_events"),
            "controls": payload.get("controls"),
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
    parser.add_argument("--input", type=Path, required=True, help="JSON, JSONL, or log file containing security events")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH)
    parser.add_argument("--json", action="store_true", help="Print full JSON report")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = classify_events(read_events(args.input), policy_path=args.policy)
    payload = report_to_dict(report)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"{report_id(payload)}.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            f"[security-events] {report.decision} events={report.event_count} "
            f"score={report.risk_score} controls={len(report.controls)}"
            f" report={out_path}"
        )
    return exit_code(report.decision)


if __name__ == "__main__":
    raise SystemExit(main())
