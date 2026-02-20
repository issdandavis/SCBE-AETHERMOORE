#!/usr/bin/env python3
"""AetherAuth-inspired context-bound access gate for lightweight policy simulations."""

from __future__ import annotations

import argparse
import base64
import hmac
import hashlib
import json
import secrets
import time
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    from symphonic_cipher.geoseal_location_library import (
        GeoSealLocationDecision,
        DEFAULT_CORE_MAX as LOCATION_DEFAULT_CORE_MAX,
        DEFAULT_OUTER_MAX as LOCATION_DEFAULT_OUTER_MAX,
        evaluate_geoseal_location,
    )
except Exception:
    GeoSealLocationDecision = None  # type: ignore
    evaluate_geoseal_location = None  # type: ignore
    LOCATION_DEFAULT_CORE_MAX = 0.30
    LOCATION_DEFAULT_OUTER_MAX = 0.70


DEFAULT_CORE_MAX = 0.30
DEFAULT_OUTER_MAX = 0.70
DEFAULT_TRUSTED_RADIUS_KM = 50.0
DEFAULT_LOCATION_CORE_RADIUS_KM = 5.0
DEFAULT_LOCATION_OUTER_RADIUS_KM = 80.0


def _hex_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_context_vector(
    *,
    context_json: Optional[str] = None,
    context_vector: Optional[str] = None,
    time_ms: Optional[float] = None,
    cpu: Optional[float] = None,
    memory: Optional[float] = None,
    intent: Optional[float] = None,
    history: Optional[float] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> List[float]:
    values: List[float] = []

    if context_json:
        parsed = json.loads(context_json)
        if isinstance(parsed, list):
            values.extend([_coerce_float(v, 0.0) for v in parsed])
        elif isinstance(parsed, dict):
            ordered = [
                "time",
                "location",
                "cpu",
                "memory",
                "intent",
                "history",
                "latitude",
                "longitude",
            ]
            for key in ordered:
                candidate = parsed.get(key, 0.0)
                if key == "location":
                    if isinstance(candidate, dict):
                        values.append(_coerce_float(candidate.get("x", 0.0), 0.0))
                        values.append(_coerce_float(candidate.get("y", 0.0), 0.0))
                    elif isinstance(candidate, (int, float, str)):
                        values.append(_coerce_float(candidate, 0.0))
                else:
                    values.append(_coerce_float(candidate, 0.0))

    if context_vector:
        parsed = [v.strip() for v in context_vector.split(",") if v.strip()]
        values.extend([_coerce_float(v, 0.0) for v in parsed])

    if time_ms is not None:
        values.append(_coerce_float(time_ms, 0.0))
    if latitude is not None:
        values.append(_coerce_float(latitude, 0.0))
    if longitude is not None:
        values.append(_coerce_float(longitude, 0.0))
    if cpu is not None:
        values.append(_coerce_float(cpu, 0.0))
    if memory is not None:
        values.append(_coerce_float(memory, 0.0))
    if intent is not None:
        values.append(_coerce_float(intent, 0.0))
    if history is not None:
        values.append(_coerce_float(history, 0.0))

    if not values:
        # identity/time default vector
        now = time.time()
        values = [_coerce_float(now), 0.0, 0.0, 0.0, 0.0, 0.0]
    return values[:6]


def _normalize_value(value: float, scale: float = 1.0) -> float:
    return max(-1.0, min(1.0, float(value) / float(scale or 1.0)))


def _project_vector(values: List[float]) -> List[float]:
    # Keep into [-1, 1], then place on 6D trust manifold.
    # Using fixed scales protects against accidental giant values from logs.
    scales = [2_000_000.0, 180.0, 100.0, 256.0, 1.0, 4.0]
    normalized: List[float] = []
    for idx, value in enumerate(values):
        normalized.append(_normalize_value(value, scales[min(idx, len(scales) - 1)]))
    while len(normalized) < 6:
        normalized.append(0.0)
    return normalized[:6]


def _vector_radius(values: List[float]) -> float:
    if not values:
        return 1.0
    mag = sum(v * v for v in values) ** 0.5
    return min(1.0, max(0.0, mag))


def _distance_to_reference(current: List[float], reference: List[float]) -> float:
    if not current and not reference:
        return 0.0
    current = current[:6]
    reference = reference[:6]
    if len(reference) < 6:
        reference = reference + [0.0] * (6 - len(reference))
    if len(reference) > 6:
        reference = reference[:6]
    if len(current) < 6:
        current = current + [0.0] * (6 - len(current))
    if len(current) > 6:
        current = current[:6]

    return sum((a - b) ** 2 for a, b in zip(current, reference)) ** 0.5 / (6 ** 0.5)


def _ring_class(risk_radius: float, core_max: float, outer_max: float) -> str:
    if risk_radius <= core_max:
        return "core"
    if risk_radius <= outer_max:
        return "outer"
    return "blocked"


def _hmac_proof(secret: str, context: Dict[str, Any], action: str) -> str:
    payload = json.dumps({"action": action, "context": context}, sort_keys=True)
    digest = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def _verify_request_signature(
    secret: str | None,
    requested_action: str,
    context: Dict[str, Any],
    provided_signature: str | None,
) -> Tuple[bool, str]:
    if not secret:
        return True, "no_signature_config"
    if not provided_signature:
        return False, "missing_signature"
    expected = _hmac_proof(secret, context, requested_action)
    if not hmac.compare_digest(expected, provided_signature):
        return False, "signature_mismatch"
    return True, "signature_valid"


@dataclass
class AetherAuthDecision:
    requested_action: str
    ring: str
    decision: str
    risk_radius: float
    timestamp: str
    trust_score: float
    reason: str
    geoid: str
    location_ring: str
    noise: str
    drift: Dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_access(
    requested_action: str,
    context_vector: List[float],
    reference_vector: List[float],
    *,
    core_max: float,
    outer_max: float,
    request_time_ms: int,
    max_time_skew_ms: int,
    secret: Optional[str] = None,
    signature: Optional[str] = None,
    user_latitude: Optional[float] = None,
    user_longitude: Optional[float] = None,
    reference_latitude: Optional[float] = None,
    reference_longitude: Optional[float] = None,
    trusted_radius_km: float = DEFAULT_TRUSTED_RADIUS_KM,
    location_core_radius_km: float = DEFAULT_LOCATION_CORE_RADIUS_KM,
    location_outer_radius_km: float = DEFAULT_LOCATION_OUTER_RADIUS_KM,
    location_core_max: float = LOCATION_DEFAULT_CORE_MAX,
    location_outer_max: float = LOCATION_DEFAULT_OUTER_MAX,
    enforce_location: bool = False,
) -> AetherAuthDecision:
    now_ms = int(time.time() * 1000)
    context_time_ms = request_time_ms or now_ms
    stale_ms = abs(now_ms - context_time_ms)
    clock_drift = min(1.0, stale_ms / float(max(1, max_time_skew_ms)))

    projected = _project_vector(context_vector)
    reference = _project_vector(reference_vector)
    drift = _distance_to_reference(projected, reference)
    radius = _vector_radius(projected)

    base_risk = max(0.0, min(1.0, 0.6 * drift + 0.2 * radius + 0.2 * clock_drift))

    location_risk = 0.0
    location_ring = "missing"
    location_distance_km = None
    location_status = "not_evaluated"
    location_geoid = ""
    if evaluate_geoseal_location is not None:
        location_decision = evaluate_geoseal_location(
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            reference_latitude=reference_latitude,
            reference_longitude=reference_longitude,
            trusted_radius_km=trusted_radius_km,
            core_radius_km=location_core_radius_km,
            outer_radius_km=location_outer_radius_km,
            core_max=location_core_max,
            outer_max=location_outer_max,
        )
        location_risk = float(location_decision.risk_radius)
        location_ring = location_decision.ring
        location_distance_km = location_decision.distance_km
        location_status = location_decision.status
        location_geoid = location_decision.geoid
    elif user_latitude is not None and user_longitude is not None:
        location_status = "library_unavailable"

    if enforce_location and user_latitude is None and user_longitude is None:
        location_status = "blocked_missing_location"
        location_ring = "blocked"
        location_risk = 1.0

    if location_ring == "missing":
        location_ring = "blocked" if enforce_location else "outer"

    # Weighted blend keeps location in the trust pipeline without disabling current
    # behavior for non-location callers.
    risk = max(0.0, min(1.0, 0.7 * base_risk + 0.3 * location_risk))
    if location_ring == "blocked":
        risk = max(risk, 0.95)

    ring = _ring_class(risk, core_max=core_max, outer_max=outer_max)
    if ring == "core":
        decision = "ALLOW"
    elif ring == "outer":
        decision = "READ_ONLY"
    else:
        decision = "DENY"

    signature_ok, signature_state = _verify_request_signature(
        secret,
        requested_action,
        {
            "context_vector": projected,
            "reference_vector": reference,
            "requested_action": requested_action,
            "risk": risk,
        },
        signature,
    )

    if not signature_ok and decision != "DENY":
        decision = "READ_ONLY"
        ring = "outer"
        reason = f"signature_state={signature_state}"
    else:
        reason = f"signature_state={signature_state}"

    noisy = (
        secrets.token_hex(32) if decision == "DENY"
        else ""
    )

    trust = round(1.0 - risk, 4)
    return AetherAuthDecision(
        requested_action=requested_action,
        ring=ring,
        decision=decision,
        risk_radius=round(risk, 4),
        timestamp=datetime.now(timezone.utc).isoformat(),
        trust_score=trust,
        reason=reason,
        geoid=_hex_digest("::".join(f"{v:.4f}" for v in projected)),
        noise=noisy,
        drift={
            "projected_radius": round(radius, 6),
            "signature_clock_drift_ratio": round(clock_drift, 4),
            "context_distance": round(drift, 6),
            "context_time_ms": context_time_ms,
            "age_ms": stale_ms,
            "signature_state": signature_state,
            "location_ring": location_ring,
            "location_distance_km": location_distance_km,
            "location_risk": round(location_risk, 6),
            "location_status": location_status,
            "location_geoid": location_geoid or _hex_digest("::".join(f"{v:.4f}" for v in projected)),
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate AetherAuth-style context-bound access decisions")
    parser.add_argument("--action", default="read", help="Requested action name")
    parser.add_argument("--context-json", default="", help="JSON object/list with context fields")
    parser.add_argument("--context-vector", default="", help="Comma separated numeric context dimensions")
    parser.add_argument("--reference-vector", default="", help="Expected context/reference vector (comma separated)")
    parser.add_argument("--time-ms", type=int, default=None, help="Unix epoch milliseconds")
    parser.add_argument("--latitude", type=float, default=None, help="Optional location latitude")
    parser.add_argument("--longitude", type=float, default=None, help="Optional location longitude")
    parser.add_argument("--reference-latitude", type=float, default=None, help="Reference latitude for geospatial matching")
    parser.add_argument("--reference-longitude", type=float, default=None, help="Reference longitude for geospatial matching")
    parser.add_argument("--trusted-radius-km", type=float, default=DEFAULT_TRUSTED_RADIUS_KM, help="GeoSeal trusted radius in km")
    parser.add_argument("--location-core-radius-km", type=float, default=DEFAULT_LOCATION_CORE_RADIUS_KM, help="GeoSeal location core-radius in km")
    parser.add_argument("--location-outer-radius-km", type=float, default=DEFAULT_LOCATION_OUTER_RADIUS_KM, help="GeoSeal location outer-radius in km")
    parser.add_argument("--location-core-max", type=float, default=LOCATION_DEFAULT_CORE_MAX, help="Location core ring max risk")
    parser.add_argument("--location-outer-max", type=float, default=LOCATION_DEFAULT_OUTER_MAX, help="Location outer ring max risk")
    parser.add_argument("--enforce-location", action="store_true", help="Reject requests when location is missing/unusable")
    parser.add_argument("--cpu", type=float, default=None, help="CPU utilization / memory pressure metric")
    parser.add_argument("--memory", type=float, default=None, help="Memory pressure metric")
    parser.add_argument("--intent", type=float, default=None, help="Intent score (-1..1)")
    parser.add_argument("--history", type=float, default=None, help="History score")
    parser.add_argument("--core-max", type=float, default=DEFAULT_CORE_MAX, help="Core ring cutoff")
    parser.add_argument("--outer-max", type=float, default=DEFAULT_OUTER_MAX, help="Outer ring cutoff")
    parser.add_argument("--signature", default="", help="Expected request signature")
    parser.add_argument("--secret", default="", help="HMAC secret for request signature verification")
    parser.add_argument("--max-time-skew-ms", type=int, default=15 * 60 * 1000, help="Allowed clock skew in ms")
    parser.add_argument("--output", default="artifacts/aetherauth_decision.json", help="Decision JSON path")
    parser.add_argument("--summary", default="artifacts/aetherauth_decision.md", help="Decision summary path")
    return parser.parse_args()


def _write_summary(path: Path, decision: AetherAuthDecision) -> None:
    lines = [
        "# AetherAuth Decision",
        f"Generated: {decision.timestamp}",
        f"Action: {decision.requested_action}",
        f"Decision: {decision.decision}",
        f"Ring: {decision.ring}",
        f"Risk: {decision.risk_radius}",
        f"Trust: {decision.trust_score}",
        f"Reason: {decision.reason}",
        "",
        "## Drift",
        f"- projected_radius: {decision.drift['projected_radius']}",
        f"- context_distance: {decision.drift['context_distance']}",
        f"- signature_clock_drift_ratio: {decision.drift['signature_clock_drift_ratio']}",
        "",
        "## Access Rule",
    ]
    if decision.ring == "core":
        lines.append("- Full access expected.")
    elif decision.ring == "outer":
        lines.append("- Read-only / outer ring behavior.")
    else:
        lines.append("- Access denied; fail-to-noise mode active.")

    if decision.noise:
        lines.append("")
        lines.append(f"Noise: {decision.noise}")

    path = Path(path)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    reference_vector = _build_context_vector(context_vector=args.reference_vector) if args.reference_vector else [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    context_vector = _build_context_vector(
        context_json=args.context_json or None,
        context_vector=args.context_vector or None,
        time_ms=args.time_ms,
        cpu=args.cpu,
        memory=args.memory,
        intent=args.intent,
        history=args.history,
        latitude=args.latitude,
        longitude=args.longitude,
    )

    decision = evaluate_access(
        requested_action=args.action,
        context_vector=context_vector,
        reference_vector=reference_vector,
        core_max=args.core_max,
        outer_max=args.outer_max,
        request_time_ms=args.time_ms or int(time.time() * 1000),
        max_time_skew_ms=args.max_time_skew_ms,
        secret=args.secret or None,
        signature=args.signature or None,
        user_latitude=args.latitude,
        user_longitude=args.longitude,
        reference_latitude=args.reference_latitude,
        reference_longitude=args.reference_longitude,
        trusted_radius_km=args.trusted_radius_km,
        location_core_radius_km=args.location_core_radius_km,
        location_outer_radius_km=args.location_outer_radius_km,
        location_core_max=args.location_core_max,
        location_outer_max=args.location_outer_max,
        enforce_location=args.enforce_location,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(decision.to_json(), indent=2), encoding="utf-8")

    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    _write_summary(summary_path, decision)

    print("AetherAuth decision written to:", output_path)
    print("AetherAuth summary written to:", summary_path)
    print("Decision:", decision.decision, "ring=", decision.ring, "risk=", decision.risk_radius)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
