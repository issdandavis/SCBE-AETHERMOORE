#!/usr/bin/env python3
"""Route IDE/Codespaces packets with Spiralverse governance overlays.

This extends the GitHub dual-tentacle model by adding:
1) Layer 5  - 6D vector matching for task->IDE selection.
2) Layer 9  - Resonance gate containment (resonant/dissonant routing).
3) Layer 11 - Roundtable-style multi-signature quorum checks.
4) Layer 12 - Spiralverse telemetry logs (tongue + frequency + distance).
5) Layer 14 - Signed route envelopes (RWP2 multi-tongue signatures).

Usage:
    python scripts/system/github_ide_mesh_router.py --task "ship firebase auth prototype" --mode 2d --require-codespaces
    python scripts/system/github_ide_mesh_router.py --task "integrate spiralverse" --mode auto --require-codespaces
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.system.github_dual_tentacle_router import (  # noqa: E402
    CROSSTALK_LOG,
    append_jsonl,
    lane_path,
)
from src.spiralverse import (  # noqa: E402
    OperationTier,
    Position6D,
    ProtocolTongue,
    RWP2Envelope,
    SignatureEngine,
    TIER_REQUIRED_TONGUES,
    build_spelltext,
    hyperbolic_distance_6d,
)
from src.symphonic_cipher.spiralverse.sdk import SpiralverseSDK  # noqa: E402

IDE_MATRIX_PATH = REPO_ROOT / "config" / "governance" / "ide_platform_matrix.json"
IDE_ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "agent_comm" / "ide_mesh"
IDE_DECISIONS = IDE_ARTIFACT_ROOT / "ide_decisions.jsonl"
IDE_TELEMETRY = IDE_ARTIFACT_ROOT / "telemetry.jsonl"

TONGUE_ORDER = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_FREQUENCIES = {
    "KO": 440.00,
    "AV": 329.63,
    "RU": 261.63,
    "CA": 493.88,
    "UM": 369.99,
    "DR": 220.00,
}
TONGUE_KEYWORDS = {
    "KO": ("route", "orchestrate", "control", "codespace", "build", "deploy", "workflow"),
    "AV": ("api", "webhook", "message", "sync", "integrate", "connector", "io"),
    "RU": ("policy", "governance", "rule", "constraint", "compliance", "gate"),
    "CA": ("compute", "algorithm", "logic", "math", "vector", "optimize"),
    "UM": ("security", "secret", "token", "auth", "encrypt", "pqc", "sign"),
    "DR": ("schema", "type", "contract", "ledger", "audit", "record"),
}
INTENT_TO_TONGUE = {
    "malicious_intent": "UM",
    "potential_attack": "UM",
    "code_generation": "KO",
    "documentation": "DR",
    "data_analysis": "CA",
    "debugging": "KO",
    "general_assistance": "AV",
    "unknown": "KO",
}


class GateStatus(str, Enum):
    RESONANT = "resonant"
    DISSONANT = "dissonant"
    QUARANTINED = "quarantined"


@dataclass
class PlatformDecision:
    profile_id: str
    label: str
    mode: str
    codespaces_integration: str
    github_integration: str
    score: int
    reason: list[str]
    lane: str
    vector_distance: float
    profile_vector: list[float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "label": self.label,
            "mode": self.mode,
            "codespaces_integration": self.codespaces_integration,
            "github_integration": self.github_integration,
            "score": self.score,
            "reason": self.reason,
            "lane": self.lane,
            "vector_distance": self.vector_distance,
            "profile_vector": self.profile_vector,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_matrix() -> dict[str, Any]:
    try:
        return json.loads(IDE_MATRIX_PATH.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"Failed to read IDE matrix: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid IDE matrix JSON: {exc}") from exc


def choose_lane(profile: dict[str, Any], task: str) -> str:
    t = task.lower()
    codespaces_mode = str(profile.get("codespaces_integration", "none")).lower()

    if codespaces_mode in {"native", "bridge"}:
        return "codespaces_lane"
    if any(k in t for k in ["webhook", "event", "workflow", "issue", "pull request", "pr"]):
        return "webhook_lane"
    return "cli_lane"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_tongue_vector(values: list[Any]) -> list[float]:
    vec = [_safe_float(v, 0.0) for v in values[:6]]
    while len(vec) < 6:
        vec.append(0.0)
    return [max(0.0, min(1.0, v)) for v in vec]


def _default_profile_vector(profile: dict[str, Any]) -> list[float]:
    profile_id = str(profile.get("id", "")).lower()
    mode = str(profile.get("mode", "")).lower()
    if "codespaces" in profile_id:
        return [0.92, 0.70, 0.58, 0.84, 0.54, 0.88]
    if "firebase" in profile_id:
        return [0.62, 0.78, 0.52, 0.70, 0.74, 0.66]
    if mode == "3d":
        return [0.66, 0.64, 0.90, 0.66, 0.70, 0.62]
    return [0.68, 0.70, 0.56, 0.68, 0.62, 0.64]


def _profile_vector(profile: dict[str, Any]) -> list[float]:
    vec = profile.get("tongue_vector")
    if isinstance(vec, list):
        return _normalize_tongue_vector(vec)
    return _default_profile_vector(profile)


def _infer_primary_tongue(intent: str, task: str) -> str:
    explicit = INTENT_TO_TONGUE.get(intent, "")
    if explicit:
        return explicit
    task_l = task.lower()
    counts: dict[str, int] = {}
    for tongue, keywords in TONGUE_KEYWORDS.items():
        counts[tongue] = sum(1 for k in keywords if k in task_l)
    winner = max(counts, key=counts.get) if counts else "KO"
    return winner if counts.get(winner, 0) > 0 else "KO"


def classify_task_to_vector(task: str, intent_tongue: str, confidence: float) -> list[float]:
    task_l = task.lower()
    digest = hashlib.sha256(task.encode("utf-8")).digest()

    # Stable baseline to avoid zero vectors even with low lexical overlap.
    baseline = [0.25 + 0.5 * (int.from_bytes(digest[i * 4 : (i + 1) * 4], "big") / 0xFFFFFFFF) for i in range(6)]
    scores = baseline[:]

    # Semantic boosts by tongue keywords.
    for i, tongue in enumerate(TONGUE_ORDER):
        for kw in TONGUE_KEYWORDS[tongue]:
            if kw in task_l:
                scores[i] += 0.12

    # Classifier confidence nudges the inferred primary tongue axis.
    try:
        idx = TONGUE_ORDER.index(intent_tongue)
    except ValueError:
        idx = 0
    scores[idx] += max(0.0, min(1.0, confidence)) * 0.25

    mx = max(scores) if scores else 1.0
    if mx <= 0:
        return [0.0] * 6
    normalized = [max(0.0, min(1.0, s / mx)) for s in scores]
    return normalized


def _vector_to_position(vec: list[float]) -> Position6D:
    v = _normalize_tongue_vector(vec)
    return Position6D(
        axiom=(v[0] * 2.0) - 1.0,
        flow=(v[1] * 2.0) - 1.0,
        glyph=(v[2] * 2.0) - 1.0,
        oracle=v[3],
        charm=(v[4] * 2.0) - 1.0,
        ledger=int(round(v[5] * 255.0)),
    )


def _vector_distance(task_vec: list[float], profile_vec: list[float]) -> float:
    a = _vector_to_position(task_vec)
    b = _vector_to_position(profile_vec)
    dist = hyperbolic_distance_6d(a, b)
    if dist == float("inf"):
        # Fallback for numerical edge cases.
        delta = [(x - y) for x, y in zip(_normalize_tongue_vector(task_vec), _normalize_tongue_vector(profile_vec))]
        return sum(d * d for d in delta) ** 0.5
    return float(dist)


def score_profile(
    profile: dict[str, Any],
    task: str,
    mode: str,
    prefer: str,
    require_codespaces: bool,
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    task_l = task.lower()
    prefer_l = prefer.lower().strip()

    profile_mode = str(profile.get("mode", "")).lower()
    profile_id = str(profile.get("id", "")).lower()
    profile_label = str(profile.get("label", "")).lower()
    codespaces_integration = str(profile.get("codespaces_integration", "none")).lower()

    if mode != "auto" and profile_mode == mode:
        score += 6
        reasons.append(f"mode match: {mode}")
    elif mode == "auto":
        score += 2
        reasons.append("auto mode baseline")

    if prefer_l and (prefer_l == profile_id or prefer_l in profile_label):
        score += 8
        reasons.append(f"preferred profile: {prefer}")

    for kw in profile.get("task_keywords", []):
        kw_l = str(kw).lower()
        if kw_l and kw_l in task_l:
            score += 2
            reasons.append(f"keyword: {kw_l}")

    if require_codespaces:
        if codespaces_integration == "native":
            score += 8
            reasons.append("codespaces integration: native (preferred)")
        elif codespaces_integration == "bridge":
            score += 4
            reasons.append("codespaces integration: bridge")
        else:
            score -= 10
            reasons.append("codespaces requirement not satisfied")
    elif codespaces_integration == "native":
        score += 1
        reasons.append("native codespaces bonus")

    if profile.get("firebase_like", False):
        if any(k in task_l for k in ["firebase", "backend", "hosting", "auth", "prototype"]):
            score += 3
            reasons.append("firebase-like fit")

    return score, reasons


def choose_platform(
    platforms: list[dict[str, Any]],
    task: str,
    mode: str,
    prefer: str,
    require_codespaces: bool,
    task_vector: list[float],
    default_profile: str,
) -> PlatformDecision:
    best_score = -10_000
    best_profile: dict[str, Any] | None = None
    best_reasons: list[str] = []
    best_distance = 9999.0
    best_profile_vec = [0.0] * 6

    for profile in platforms:
        score, reasons = score_profile(profile, task, mode, prefer, require_codespaces)
        profile_id = str(profile.get("id", ""))

        if require_codespaces and default_profile and profile_id == default_profile:
            score += 6
            reasons.append(f"default codespaces spine: {default_profile}")

        pvec = _profile_vector(profile)
        distance = _vector_distance(task_vector, pvec)

        # Layer 5 vector coupling: nearby profiles get bonus, far profiles get penalty.
        vector_bonus = int(round(max(-8.0, min(8.0, (1.6 - distance) * 5.0))))
        score += vector_bonus
        reasons.append(f"vector distance: {distance:.4f}")
        reasons.append(f"vector bonus: {vector_bonus:+d}")

        if score > best_score:
            best_score = score
            best_profile = profile
            best_reasons = reasons
            best_distance = distance
            best_profile_vec = pvec

    if best_profile is None:
        raise RuntimeError("IDE matrix has no profiles.")

    lane = choose_lane(best_profile, task)
    return PlatformDecision(
        profile_id=str(best_profile.get("id", "")),
        label=str(best_profile.get("label", "")),
        mode=str(best_profile.get("mode", "")),
        codespaces_integration=str(best_profile.get("codespaces_integration", "none")),
        github_integration=str(best_profile.get("github_integration", "none")),
        score=best_score,
        reason=best_reasons,
        lane=lane,
        vector_distance=float(best_distance),
        profile_vector=best_profile_vec,
    )


def evaluate_resonance(distance: float, confidence: float, require_codespaces: bool) -> tuple[GateStatus, float, float]:
    distance_component = 1.0 / (1.0 + max(0.0, distance))
    confidence_component = max(0.0, min(1.0, confidence))
    resonance_score = (0.55 * confidence_component) + (0.45 * distance_component)
    threshold = 0.50 if require_codespaces else 0.42
    status = GateStatus.RESONANT if resonance_score >= threshold else GateStatus.DISSONANT
    return status, resonance_score, threshold


def compute_required_tongues(
    intent_tongue: str,
    require_codespaces: bool,
    risk: str,
    confidence: float,
) -> tuple[set[ProtocolTongue], OperationTier]:
    base_tongue = ProtocolTongue.__members__.get(intent_tongue, ProtocolTongue.KO)

    # Roundtable tier escalation for high-risk/codespaces routes.
    if risk == "high" or (require_codespaces and confidence < 0.8):
        tier = OperationTier.TIER_4
    elif require_codespaces:
        tier = OperationTier.TIER_3
    elif confidence < 0.72:
        tier = OperationTier.TIER_2
    else:
        tier = OperationTier.TIER_1

    required = set(TIER_REQUIRED_TONGUES.get(tier, {ProtocolTongue.KO}))
    required.add(base_tongue)
    return required, tier


def sign_route_decision(
    task: str,
    mode: str,
    decision: PlatformDecision,
    required_tongues: set[ProtocolTongue],
    tier: OperationTier,
) -> dict[str, Any]:
    signer = SignatureEngine()
    payload_obj = {
        "task": task,
        "mode": mode,
        "profile_id": decision.profile_id,
        "lane": decision.lane,
        "vector_distance": round(decision.vector_distance, 6),
        "timestamp": utc_now(),
    }
    payload = json.dumps(payload_obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    spelltext = build_spelltext(
        command="ROUTE_IDE",
        origin=ProtocolTongue.KO,
        sequence=1,
        profile=decision.profile_id,
        lane=decision.lane,
    )
    envelope = RWP2Envelope(
        spelltext=spelltext,
        payload=payload,
        aad=f"mode={mode}",
        tier=tier,
    )
    signed = signer.sign(envelope, required_tongues)
    verified, results = signer.verify(signed, required_tongues)

    per_tongue = {tongue.value: bool(ok) for tongue, ok in results.items()}
    required_names = sorted(t.value for t in required_tongues)
    approved_count = sum(1 for ok in per_tongue.values() if ok)
    quorum_required = len(required_names)
    digest = hashlib.sha256(json.dumps(signed.to_dict(), sort_keys=True).encode("utf-8")).hexdigest()

    return {
        "verified": bool(verified),
        "tier": tier.value,
        "required_tongues": required_names,
        "per_tongue": per_tongue,
        "approved_count": approved_count,
        "quorum_required": quorum_required,
        "quorum_approved": approved_count >= quorum_required and verified,
        "route_signature_digest": digest,
        "envelope": signed.to_dict(),
    }


def log_telemetry(event: dict[str, Any], task: str = "", intent_tongue: str = "KO") -> None:
    payload = dict(event)
    payload["created_at"] = payload.get("created_at", utc_now())
    payload["task"] = payload.get("task", task)
    payload["tongue"] = payload.get("tongue", intent_tongue)
    payload["frequency_hz"] = payload.get("frequency_hz", TONGUE_FREQUENCIES.get(intent_tongue, 440.0))
    append_jsonl(IDE_TELEMETRY, payload)


def _fallback_decision(matrix: dict[str, Any], platforms: list[dict[str, Any]], task: str, task_vector: list[float]) -> PlatformDecision:
    fallback_id = (
        matrix.get("selection_policy", {}).get("default_profile")
        if isinstance(matrix.get("selection_policy"), dict)
        else None
    ) or "github_codespaces"

    fallback_profile = next((p for p in platforms if p.get("id") == fallback_id), platforms[0])
    pvec = _profile_vector(fallback_profile)
    return PlatformDecision(
        profile_id=str(fallback_profile.get("id", "")),
        label=str(fallback_profile.get("label", "")),
        mode=str(fallback_profile.get("mode", "")),
        codespaces_integration=str(fallback_profile.get("codespaces_integration", "none")),
        github_integration=str(fallback_profile.get("github_integration", "none")),
        score=0,
        reason=["fallback to default profile due dissonant gate"],
        lane=choose_lane(fallback_profile, task),
        vector_distance=_vector_distance(task_vector, pvec),
        profile_vector=pvec,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Pick IDE profile + route GitHub packet with Spiralverse governance.")
    parser.add_argument("--repo", default="SCBE-AETHERMOORE", help="Repo context label.")
    parser.add_argument("--sender", default="agent.ide-orchestrator", help="Sender label.")
    parser.add_argument("--event-type", default="ide_task", help="Event type label.")
    parser.add_argument("--task", required=True, help="Task summary used for profile scoring.")
    parser.add_argument("--mode", default="auto", choices=["auto", "2d", "3d"], help="Workspace mode.")
    parser.add_argument("--prefer", default="", help="Preferred IDE profile id or label.")
    parser.add_argument(
        "--require-codespaces",
        action="store_true",
        help="Require native/bridge Codespaces compatibility.",
    )
    parser.add_argument(
        "--risk",
        default="medium",
        choices=["low", "medium", "high"],
        help="Risk label for packet metadata.",
    )
    args = parser.parse_args()

    matrix = load_matrix()
    platforms = matrix.get("platforms", [])
    if not isinstance(platforms, list) or not platforms:
        raise RuntimeError("IDE matrix missing 'platforms' list.")

    sdk = SpiralverseSDK()
    intent_label, intent_confidence = sdk.classify_intent(args.task)
    intent_tongue = _infer_primary_tongue(intent_label, args.task)
    task_vector = classify_task_to_vector(args.task, intent_tongue, intent_confidence)

    log_telemetry(
        {
            "event": "intent_classified",
            "intent_label": intent_label,
            "intent_confidence": intent_confidence,
            "task_vector": task_vector,
        },
        task=args.task,
        intent_tongue=intent_tongue,
    )

    decision = choose_platform(
        platforms=platforms,
        task=args.task,
        mode=args.mode,
        prefer=args.prefer,
        require_codespaces=args.require_codespaces,
        task_vector=task_vector,
        default_profile=str(matrix.get("selection_policy", {}).get("default_profile", "github_codespaces")),
    )

    gate_status, resonance_score, gate_threshold = evaluate_resonance(
        decision.vector_distance,
        intent_confidence,
        args.require_codespaces,
    )

    if gate_status == GateStatus.DISSONANT:
        noise = hashlib.sha256(f"{args.task}|{utc_now()}".encode("utf-8")).hexdigest()[:24]
        append_jsonl(
            CROSSTALK_LOG,
            {
                "created_at": utc_now(),
                "event": "dissonant_route",
                "repo": args.repo,
                "task": args.task,
                "noise": noise,
                "proposed_profile": decision.profile_id,
            },
        )
        log_telemetry(
            {
                "event": "gate_dissonant",
                "resonance_score": resonance_score,
                "threshold": gate_threshold,
                "proposed_profile": decision.profile_id,
                "vector_distance": decision.vector_distance,
            },
            task=args.task,
            intent_tongue=intent_tongue,
        )

        if args.require_codespaces or args.risk == "high":
            raise RuntimeError("Dissonant routing denied by Spiralverse gate.")

        decision = _fallback_decision(matrix, platforms, args.task, task_vector)
        gate_status = GateStatus.QUARANTINED

    required_tongues, tier = compute_required_tongues(
        intent_tongue=intent_tongue,
        require_codespaces=args.require_codespaces,
        risk=args.risk,
        confidence=intent_confidence,
    )
    signature = sign_route_decision(
        task=args.task,
        mode=args.mode,
        decision=decision,
        required_tongues=required_tongues,
        tier=tier,
    )

    if args.require_codespaces and not signature["quorum_approved"]:
        raise RuntimeError("Roundtable quorum failed for codespaces-required route.")

    packet_id = f"ide-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    packet = {
        "packet_id": packet_id,
        "created_at": utc_now(),
        "sender": args.sender,
        "recipient_lane": decision.lane,
        "intent": "ide_workspace_selection",
        "status": "selected",
        "repo": args.repo,
        "event_type": args.event_type,
        "task": args.task,
        "payload": {
            "mode": args.mode,
            "prefer": args.prefer,
            "require_codespaces": args.require_codespaces,
            "selection_policy_version": matrix.get("version"),
            "decision": decision.to_dict(),
            "spiralverse": {
                "intent_label": intent_label,
                "intent_confidence": intent_confidence,
                "intent_tongue": intent_tongue,
                "task_vector": task_vector,
                "resonance": {
                    "status": gate_status.value,
                    "score": round(resonance_score, 6),
                    "threshold": round(gate_threshold, 6),
                },
                "roundtable": {
                    "required_tongues": signature["required_tongues"],
                    "tier": signature["tier"],
                    "per_tongue": signature["per_tongue"],
                    "quorum_required": signature["quorum_required"],
                    "approved_count": signature["approved_count"],
                    "quorum_approved": signature["quorum_approved"],
                    "signature_verified": signature["verified"],
                },
                "route_signature_digest": signature["route_signature_digest"],
            },
        },
        "next_action": f"Open {decision.profile_id} and execute task in {decision.lane}.",
        "risk": args.risk,
    }

    append_jsonl(lane_path(decision.lane), packet)
    append_jsonl(
        CROSSTALK_LOG,
        {
            "created_at": packet["created_at"],
            "packet_id": packet_id,
            "from": args.sender,
            "to": decision.lane,
            "repo": args.repo,
            "event_type": args.event_type,
            "task": args.task,
            "status": "selected",
            "risk": args.risk,
            "ide_profile": decision.profile_id,
            "ide_mode": decision.mode,
            "gate_status": gate_status.value,
            "route_signature_digest": signature["route_signature_digest"],
        },
    )

    IDE_ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    append_jsonl(IDE_DECISIONS, packet)
    log_telemetry(
        {
            "event": "route_selected",
            "packet_id": packet_id,
            "profile": decision.profile_id,
            "lane": decision.lane,
            "vector_distance": decision.vector_distance,
            "resonance_score": resonance_score,
            "gate_status": gate_status.value,
            "route_signature_digest": signature["route_signature_digest"],
        },
        task=args.task,
        intent_tongue=intent_tongue,
    )

    print(
        json.dumps(
            {
                "ok": True,
                "packet_id": packet_id,
                "lane": decision.lane,
                "profile": decision.profile_id,
                "mode": decision.mode,
                "decision_score": decision.score,
                "decision_reason": decision.reason,
                "vector_distance": round(decision.vector_distance, 6),
                "resonance": {
                    "status": gate_status.value,
                    "score": round(resonance_score, 6),
                    "threshold": round(gate_threshold, 6),
                },
                "roundtable": {
                    "required_tongues": signature["required_tongues"],
                    "tier": signature["tier"],
                    "quorum_approved": signature["quorum_approved"],
                    "signature_verified": signature["verified"],
                },
                "route_signature_digest": signature["route_signature_digest"],
                "decision_log": str(IDE_DECISIONS),
                "telemetry_log": str(IDE_TELEMETRY),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
