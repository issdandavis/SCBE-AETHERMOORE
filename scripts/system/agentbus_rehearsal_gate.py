#!/usr/bin/env python3
"""Mission rehearsal gate for SCBE agent-bus rounds.

This is a preflight-style validator for agent-bus packets and mirror-room
rounds. It borrows the safe parts of autonomy training practice: simulation
before live action, operational envelopes, telemetry, abort rules, and
independent holdout checks. It does not execute providers.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_TASK_TYPES = {"coding", "review", "research", "governance", "training", "general"}
VALID_PRIVACY = {"local_only", "remote_ok"}
LOCAL_PROVIDERS = {"offline", "ollama"}
REMOTE_PROVIDERS = {"openai", "anthropic", "claude", "xai", "grok", "huggingface"}


@dataclass(frozen=True)
class GateCheck:
    name: str
    ok: bool
    severity: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "severity": self.severity,
            "detail": self.detail,
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _add(checks: list[GateCheck], name: str, ok: bool, detail: str, severity: str = "error") -> None:
    checks.append(GateCheck(name=name, ok=ok, severity=severity, detail=detail))


def _round_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Accept either a raw latest_round packet or an agentbus run summary."""
    if payload.get("version") == "mirror-room-agent-bus-round-v1":
        return payload
    if isinstance(payload.get("latest_round"), dict):
        return payload["latest_round"]
    if isinstance(payload.get("round"), dict):
        return payload["round"]
    return payload


def _selected_estimate(round_packet: dict[str, Any]) -> float:
    budget = _as_dict(round_packet.get("budget"))
    try:
        return float(budget.get("selected_estimated_cents", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _budget_limit(round_packet: dict[str, Any], override: float | None = None) -> float:
    if override is not None:
        return override
    budget = _as_dict(round_packet.get("budget"))
    try:
        return float(budget.get("per_round_cents", 0.0))
    except (TypeError, ValueError):
        return 0.0


def evaluate_rehearsal_gate(
    payload: dict[str, Any],
    *,
    strict: bool = False,
    require_remote_telemetry: bool = True,
    budget_cents: float | None = None,
) -> dict[str, Any]:
    """Evaluate an agent-bus round for dispatch readiness."""
    round_packet = _round_from_payload(payload)
    checks: list[GateCheck] = []

    task = _as_dict(round_packet.get("task"))
    task_type = str(task.get("type", "")).strip()
    task_chars = int(task.get("chars", 0) or 0)
    selected_provider = str(round_packet.get("selected_provider", "")).strip()
    primary_bus = _as_list(round_packet.get("primary_bus"))
    secondary_bus = _as_list(round_packet.get("secondary_bus"))
    tertiary_bus = _as_list(round_packet.get("tertiary_bus"))
    mirror_room = _as_dict(round_packet.get("mirror_room"))
    operation_shape = _as_dict(round_packet.get("operation_shape"))

    privacy = str(round_packet.get("privacy") or payload.get("privacy") or "").strip()
    if not privacy:
        if selected_provider in LOCAL_PROVIDERS:
            privacy = "local_only"
        elif selected_provider:
            privacy = "remote_ok"

    _add(checks, "task_present", task_chars > 0, f"task chars={task_chars}")
    _add(checks, "task_type_valid", task_type in VALID_TASK_TYPES, f"task_type={task_type or '<missing>'}")
    _add(checks, "provider_selected", bool(selected_provider), f"selected_provider={selected_provider or '<missing>'}")
    _add(
        checks,
        "primary_lane_present",
        any(_as_dict(row).get("role") == "play" for row in primary_bus),
        f"primary_bus_count={len(primary_bus)}",
    )
    _add(
        checks,
        "selected_provider_is_primary",
        any(_as_dict(row).get("provider") == selected_provider for row in primary_bus),
        f"selected_provider={selected_provider}",
    )
    _add(
        checks,
        "watcher_or_rest_lane_present",
        bool(secondary_bus or tertiary_bus),
        f"secondary_bus_count={len(secondary_bus)}, tertiary_bus_count={len(tertiary_bus)}",
        severity="warning",
    )
    _add(
        checks,
        "anti_amplification_policy_present",
        "watchers do not respond" in str(mirror_room.get("anti_amplification", "")),
        "watchers must observe only unless promoted in a later round",
    )

    budget_limit = _budget_limit(round_packet, budget_cents)
    selected_estimate = _selected_estimate(round_packet)
    _add(
        checks,
        "budget_within_limit",
        selected_estimate <= budget_limit,
        f"selected_estimated_cents={selected_estimate}, budget_cents={budget_limit}",
    )

    _add(
        checks,
        "privacy_mode_known",
        privacy in VALID_PRIVACY,
        f"privacy={privacy or '<inferred missing>'}",
        severity="warning" if not strict else "error",
    )
    if privacy == "local_only":
        _add(
            checks,
            "local_only_blocks_remote_provider",
            selected_provider in LOCAL_PROVIDERS or selected_provider not in REMOTE_PROVIDERS,
            f"selected_provider={selected_provider}",
        )

    if operation_shape:
        _add(
            checks,
            "operation_shape_consensus_safe",
            operation_shape.get("floating_point_policy") == "forbidden for consensus signatures",
            "consensus signatures must not depend on floating-point math",
        )
        _add(
            checks,
            "operation_shape_has_binary_and_hex",
            bool(operation_shape.get("signature_binary")) and bool(operation_shape.get("signature_hex")),
            "operation shape should expose deterministic binary and hex signatures",
        )
    else:
        _add(
            checks,
            "operation_shape_present",
            not strict,
            "operation shape missing; allowed in non-strict dry-run only",
            severity="warning" if not strict else "error",
        )

    telemetry = _as_dict(round_packet.get("telemetry") or payload.get("telemetry"))
    abort_rule = str(round_packet.get("abort_condition") or payload.get("abort_condition") or "").strip()
    live_remote = privacy == "remote_ok" and selected_provider not in LOCAL_PROVIDERS
    if strict or (require_remote_telemetry and live_remote):
        _add(
            checks,
            "telemetry_sink_present",
            bool(telemetry.get("sink") or telemetry.get("path")),
            "remote/live rounds need a telemetry sink or artifact path",
        )
        _add(
            checks,
            "abort_condition_present",
            bool(abort_rule),
            "remote/live rounds need an explicit abort condition",
        )
    else:
        _add(
            checks,
            "telemetry_optional_for_local_rehearsal",
            True,
            "local rehearsal can rely on watcher and tracker artifacts",
            severity="info",
        )

    failure_count = sum(1 for check in checks if not check.ok and check.severity == "error")
    warning_count = sum(1 for check in checks if not check.ok and check.severity == "warning")
    status = "pass" if failure_count == 0 else "fail"
    if status == "pass" and warning_count:
        status = "pass_with_warnings"

    return {
        "schema_version": "scbe_agentbus_rehearsal_gate_v1",
        "generated_at_utc": _utc_now(),
        "status": status,
        "failure_count": failure_count,
        "warning_count": warning_count,
        "selected_provider": selected_provider,
        "privacy": privacy or None,
        "checks": [check.to_dict() for check in checks],
        "advantage": {
            "training_pattern": "simulation_or_rehearsal_before_live_dispatch",
            "operator_value": "catches missing mission envelope data before provider calls",
            "dataset_value": "turns each bus round into labeled pass/fail training records",
        },
    }


def _read_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate an agent-bus mission rehearsal gate")
    parser.add_argument("--round", dest="round_path", required=True, help="Path to latest_round.json or run summary")
    parser.add_argument("--output", default="", help="Optional JSON output path")
    parser.add_argument("--strict", action="store_true", help="Require operation shape, telemetry, and abort rules")
    parser.add_argument("--budget-cents", type=float, default=None, help="Override budget limit for evaluation")
    args = parser.parse_args()

    report = evaluate_rehearsal_gate(
        _read_json(Path(args.round_path)),
        strict=args.strict,
        budget_cents=args.budget_cents,
    )
    text = json.dumps(report, indent=2, ensure_ascii=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["failure_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
