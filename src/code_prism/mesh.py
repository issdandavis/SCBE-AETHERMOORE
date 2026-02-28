from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import ast
import hashlib
import json
import math
import re
from typing import Dict, List, Sequence, Tuple

from .builder import CodePrismBuilder
from .matrix import InteroperabilityMatrix
from .validator import ValidationIssue

TONGUE_ORDER = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_PHASE = {
    "KO": 0.0,
    "AV": math.pi / 3.0,
    "RU": (2.0 * math.pi) / 3.0,
    "CA": math.pi,
    "UM": (4.0 * math.pi) / 3.0,
    "DR": (5.0 * math.pi) / 3.0,
}
TONGUE_WEIGHT = {
    "KO": 1.000,
    "AV": 1.618,
    "RU": 2.618,
    "CA": 4.236,
    "UM": 6.854,
    "DR": 11.090,
}
MAX_TONGUE_WEIGHT = max(TONGUE_WEIGHT.values())


@dataclass
class DecisionRecord:
    action: str
    reason: str
    confidence: float
    timestamp_utc: str
    signature: str


@dataclass
class MeshArtifact:
    source_language: str
    target_system: str
    target_language: str
    code: str
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    metadata: Dict[str, object] = field(default_factory=dict)
    state_vector: List[float] = field(default_factory=list)
    decision_record: DecisionRecord | None = None
    gate_report: Dict[str, bool] = field(default_factory=dict)
    mesh_overlay_230_hex: str = ""
    mesh_overlay_230_bits: int = 230


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_hex(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _normalize_tongue_combo(combo: str | None) -> str:
    if not combo:
        return "KO+CA"
    parts = [token.strip().upper() for token in str(combo).split("+")]
    clean = [token for token in parts if token in TONGUE_ORDER]
    if not clean:
        return "KO+CA"
    seen = set()
    ordered = []
    for token in clean:
        if token in seen:
            continue
        ordered.append(token)
        seen.add(token)
    return "+".join(ordered)


def _detect_deferred_constructs(
    source_code: str,
    source_language: str,
    deferred_constructs: Sequence[str],
) -> List[str]:
    deferred = set(token.lower() for token in deferred_constructs)
    hits = set()
    lang = source_language.lower()

    if lang == "python":
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            # Syntax failures are handled by validation; keep deferred scan best-effort.
            return []

        for node in ast.walk(tree):
            if "classes" in deferred and isinstance(node, ast.ClassDef):
                hits.add("classes")
            if "decorators" in deferred:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.decorator_list:
                    hits.add("decorators")
            if "async_await" in deferred and isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith)):
                hits.add("async_await")
            if "reflection" in deferred and isinstance(node, ast.Call):
                fn = node.func
                if isinstance(fn, ast.Name) and fn.id in {"eval", "exec", "getattr", "setattr", "delattr", "__import__"}:
                    hits.add("reflection")
        return sorted(hits)

    if lang in {"typescript", "ts"}:
        checks = {
            "classes": r"\bclass\s+[A-Za-z_][A-Za-z0-9_]*",
            "generics": r"<\s*[A-Za-z_][A-Za-z0-9_]*(\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*\s*>",
            "decorators": r"@[A-Za-z_][A-Za-z0-9_]*",
            "async_await": r"\b(async|await)\b",
            "reflection": r"\b(eval|Function)\s*\(",
        }
        for key, pattern in checks.items():
            if key in deferred and re.search(pattern, source_code):
                hits.add(key)
        return sorted(hits)

    return []


def _lang_axis(matrix: InteroperabilityMatrix, lang: str) -> float:
    ordered = sorted(matrix.languages)
    if not ordered:
        return 0.0
    if lang.lower() not in ordered:
        return -1.0
    if len(ordered) == 1:
        return 0.0
    idx = ordered.index(lang.lower())
    return -1.0 + 2.0 * (idx / (len(ordered) - 1))


def _profile_axis(label: str) -> Tuple[float, float, float]:
    digest = hashlib.sha256(label.encode("utf-8")).digest()
    coords = []
    for i in range(3):
        raw = int.from_bytes(digest[i * 2:(i * 2) + 2], "big")
        coords.append(-1.0 + 2.0 * (raw / 65535.0))
    return coords[0], coords[1], coords[2]


def _risk_profile_scalar(profile: str) -> float:
    name = str(profile or "").strip().lower()
    if name == "strict":
        return 1.0
    if name == "standard":
        return 0.0
    if name == "permissive":
        return -1.0
    return 0.0


def _clamp_unit(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


def _build_state_vector(
    matrix: InteroperabilityMatrix,
    *,
    source_language: str,
    target_language: str,
    target_system: str,
    action: str,
    function_count: int,
    issue_count: int,
    deferred_count: int,
    route_allowed: bool,
    tongue_combo: str,
    risk_profile: str,
) -> List[float]:
    trust_axis = {"ALLOW": 1.0, "QUARANTINE": 0.0, "DENY": -1.0}.get(action, -1.0)
    route_axis = 1.0 if route_allowed else -1.0
    validation_axis = 1.0 if issue_count == 0 else max(-1.0, 1.0 - (0.35 * issue_count))
    fn_axis = math.tanh(function_count / 8.0)
    issue_axis = -math.tanh(issue_count / 4.0)
    deferred_axis = 1.0 if deferred_count == 0 else -math.tanh(deferred_count / 2.0)

    tongues = [token for token in tongue_combo.split("+") if token in TONGUE_ORDER]
    phases = [TONGUE_PHASE[token] for token in tongues] or [0.0]
    weights = [TONGUE_WEIGHT[token] for token in tongues] or [1.0]
    phase_mean = sum(phases) / len(phases)
    phase_sin = math.sin(phase_mean)
    phase_cos = math.cos(phase_mean)
    weight_axis = (2.0 * (sum(weights) / len(weights) / MAX_TONGUE_WEIGHT)) - 1.0

    profile_x, profile_y, profile_z = _profile_axis(f"{target_system}:{target_language}")
    fanout = len(matrix.transpilers.get(source_language.lower(), set()))
    fanout_axis = -1.0 + min(1.0, fanout / 4.0) * 2.0
    risk_axis = _risk_profile_scalar(risk_profile)
    subset_margin = 1.0 if deferred_count == 0 else -1.0

    meta_hash = hashlib.sha256(
        f"{source_language}|{target_language}|{target_system}|{tongue_combo}|{function_count}|{issue_count}|{deferred_count}".encode(
            "utf-8"
        )
    ).hexdigest()
    meta_a = -1.0 + 2.0 * (int(meta_hash[0:2], 16) / 255.0)
    meta_c = -1.0 + 2.0 * (int(meta_hash[4:6], 16) / 255.0)

    vector = [
        trust_axis,
        route_axis,
        validation_axis,
        _lang_axis(matrix, source_language),
        _lang_axis(matrix, target_language),
        _clamp_unit((_lang_axis(matrix, source_language) + _lang_axis(matrix, target_language)) / 2.0),
        fn_axis,
        issue_axis,
        deferred_axis,
        phase_sin,
        phase_cos,
        _clamp_unit(weight_axis),
        profile_x,
        profile_y,
        profile_z,
        _clamp_unit(fanout_axis),
        risk_axis,
        subset_margin,
        meta_a,
        {"ALLOW": 1.0, "QUARANTINE": 0.0, "DENY": -1.0}.get(action, -1.0),
        meta_c,
    ]
    return [_clamp_unit(v) for v in vector]


def _int_to_bits(value: int, width: int) -> str:
    return format(max(0, min(value, (1 << width) - 1)), f"0{width}b")


def _signed4_bits(value: float) -> str:
    q = int(round(_clamp_unit(value) * 7.0))
    q = max(-8, min(7, q))
    return format(q & 0xF, "04b")


def _overlay_230_bits(
    *,
    state_vector: Sequence[float],
    tongue_combo: str,
    action: str,
    route_allowed: bool,
    issue_count: int,
    deferred_count: int,
    artifact_digest_hex: str,
) -> str:
    # 84 bits: 21 dims * 4-bit signed quantization
    bits_state = "".join(_signed4_bits(v) for v in state_vector[:21])

    # 18 bits: 6 tongues * 3 bits presence/weight bucket
    active = set(token for token in tongue_combo.split("+") if token in TONGUE_ORDER)
    tongue_bits = []
    for token in TONGUE_ORDER:
        if token not in active:
            tongue_bits.append("000")
            continue
        bucket = int(round((TONGUE_WEIGHT[token] / MAX_TONGUE_WEIGHT) * 7.0))
        tongue_bits.append(_int_to_bits(bucket, 3))
    bits_tongue = "".join(tongue_bits)

    # 24 bits: T_micro/T_task/T_stage/T_life proxy from digest.
    bits_time = _int_to_bits(int(artifact_digest_hex[0:6], 16), 24)

    # 24 bits: I/P/D/q proxies.
    intent = max(0, min(63, int(round((abs(state_vector[6]) + 0.01) * 50))))
    pressure = max(0, min(63, deferred_count * 16 + issue_count * 8))
    depth = max(0, min(63, int(round((abs(state_vector[17]) + 0.01) * 50))))
    q_ratio = max(0, min(63, int(round((abs(state_vector[9]) + abs(state_vector[10])) * 20))))
    bits_intent = _int_to_bits(intent, 6) + _int_to_bits(pressure, 6) + _int_to_bits(depth, 6) + _int_to_bits(q_ratio, 6)

    # 24 bits: M4 model block (x/y/z proxies from 13-15).
    mx = max(0, min(255, int(round((state_vector[12] + 1.0) * 127.5))))
    my = max(0, min(255, int(round((state_vector[13] + 1.0) * 127.5))))
    mz = max(0, min(255, int(round((state_vector[14] + 1.0) * 127.5))))
    bits_m4 = _int_to_bits(mx, 8) + _int_to_bits(my, 8) + _int_to_bits(mz, 8)

    # 16 bits: gate flags and rollout state.
    action_bits = {"ALLOW": "01", "QUARANTINE": "10", "DENY": "11"}.get(action, "00")
    gate_flags = (
        ("1" if route_allowed else "0")
        + ("1" if issue_count == 0 else "0")
        + ("1" if deferred_count == 0 else "0")
        + action_bits
        + "00000000000"
    )

    # 32 bits: integrity digest prefix.
    bits_digest = _int_to_bits(int(artifact_digest_hex[0:8], 16), 32)

    # 8 bits: nonce shard.
    bits_nonce = _int_to_bits(int(artifact_digest_hex[8:10], 16), 8)

    bits = bits_state + bits_tongue + bits_time + bits_intent + bits_m4 + gate_flags + bits_digest + bits_nonce
    if len(bits) != 230:
        raise ValueError(f"mesh overlay must be 230 bits, got {len(bits)}")
    return bits


def _bits_to_hex(bits: str) -> str:
    pad = (4 - (len(bits) % 4)) % 4
    padded = bits + ("0" * pad)
    return format(int(padded, 2), f"0{len(padded) // 4}x")


def _decision_record(
    *,
    action: str,
    reason: str,
    confidence: float,
    payload: Dict[str, object],
) -> DecisionRecord:
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    signature = _sha256_hex(
        {
            "action": action,
            "reason": reason,
            "confidence": round(confidence, 4),
            "timestamp_utc": timestamp_utc,
            "payload_hash": _sha256_hex(payload),
        }
    )
    return DecisionRecord(
        action=action,
        reason=reason,
        confidence=round(confidence, 4),
        timestamp_utc=timestamp_utc,
        signature=signature,
    )


class CodeMeshBuilder:
    """Code Prism orchestration + native-system routing + fail-closed gates."""

    def __init__(self) -> None:
        self.prism = CodePrismBuilder()
        self.matrix = self.prism.matrix

    def translate_to_native(
        self,
        *,
        source_code: str,
        source_language: str,
        target_systems: Sequence[str],
        module_name: str = "prism_module",
        tongue_combo: str | None = None,
    ) -> Dict[str, MeshArtifact]:
        source = source_language.lower().strip()
        deferred_constructs = self.matrix.safe_subset.get("deferred_constructs", [])
        deferred_hits = _detect_deferred_constructs(source_code, source, deferred_constructs)

        allow_requires_clean = bool(self.matrix.governance.get("allow_requires_clean_validation", True))
        quarantine_on_deferred = bool(self.matrix.governance.get("quarantine_on_deferred_constructs", True))
        default_action = str(self.matrix.governance.get("default_action", "QUARANTINE")).upper()
        artifacts: Dict[str, MeshArtifact] = {}

        for system_raw in target_systems:
            target_system = str(system_raw).strip()
            system_key = target_system.lower()
            target_language = self.matrix.resolve_native_language(system_key)
            effective_combo = _normalize_tongue_combo(tongue_combo or self.matrix.default_tongue_combo(system_key))
            profile = self.matrix.native_systems.get(system_key, {})
            risk_profile = str(profile.get("risk_profile", "standard"))

            if not target_language:
                action = "DENY"
                reason = f"Unknown target system/language '{target_system}'."
                state = _build_state_vector(
                    self.matrix,
                    source_language=source,
                    target_language="unknown",
                    target_system=target_system,
                    action=action,
                    function_count=0,
                    issue_count=1,
                    deferred_count=len(deferred_hits),
                    route_allowed=False,
                    tongue_combo=effective_combo,
                    risk_profile=risk_profile,
                )
                digest = _sha256_hex({"target_system": target_system, "source": source, "reason": reason})
                bits = _overlay_230_bits(
                    state_vector=state,
                    tongue_combo=effective_combo,
                    action=action,
                    route_allowed=False,
                    issue_count=1,
                    deferred_count=len(deferred_hits),
                    artifact_digest_hex=digest,
                )
                record = _decision_record(
                    action=action,
                    reason=reason,
                    confidence=0.98,
                    payload={"target_system": target_system, "source_language": source, "digest": digest},
                )
                artifacts[target_system] = MeshArtifact(
                    source_language=source,
                    target_system=target_system,
                    target_language="unknown",
                    code="",
                    valid=False,
                    issues=[ValidationIssue(code="unknown_native_target", message=reason)],
                    metadata={"tongue_combo": effective_combo, "route_allowed": False},
                    state_vector=state,
                    decision_record=record,
                    gate_report={
                        "G0_spec": True,
                        "G1_route": False,
                        "G2_validation_clean": False,
                        "G3_deferred_safe": len(deferred_hits) == 0,
                    },
                    mesh_overlay_230_hex=_bits_to_hex(bits),
                    mesh_overlay_230_bits=230,
                )
                continue

            prism_artifact = self.prism.translate(
                source_code=source_code,
                source_language=source,
                target_languages=[target_language],
                module_name=module_name,
                tongue_combo=effective_combo,
            )[target_language]

            route_allowed = bool(prism_artifact.metadata.get("route_allowed", False))
            issue_count = len(prism_artifact.issues)
            deferred_count = len(deferred_hits)
            function_count = int(prism_artifact.metadata.get("function_count", 0))

            g0_spec = True
            g1_route = route_allowed
            g2_validation = issue_count == 0
            g3_deferred = deferred_count == 0

            action = default_action
            reason = "Insufficient evidence to allow."
            confidence = 0.75

            if not g1_route:
                action = "DENY"
                reason = f"Route '{source} -> {target_language}' denied by interoperability matrix."
                confidence = 0.98
            elif quarantine_on_deferred and not g3_deferred:
                action = "QUARANTINE"
                reason = f"Deferred constructs require review: {', '.join(deferred_hits)}."
                confidence = 0.89
            elif allow_requires_clean and not g2_validation:
                action = "QUARANTINE"
                reason = f"Generated code has validation issues ({issue_count})."
                confidence = 0.84
            else:
                action = "ALLOW"
                reason = "Route and validation gates passed."
                confidence = 0.92

            state = _build_state_vector(
                self.matrix,
                source_language=source,
                target_language=target_language,
                target_system=target_system,
                action=action,
                function_count=function_count,
                issue_count=issue_count,
                deferred_count=deferred_count,
                route_allowed=route_allowed,
                tongue_combo=effective_combo,
                risk_profile=risk_profile,
            )

            digest = _sha256_hex(
                {
                    "source_language": source,
                    "target_system": target_system,
                    "target_language": target_language,
                    "code": prism_artifact.code,
                    "issues": [issue.code for issue in prism_artifact.issues],
                    "deferred_hits": deferred_hits,
                    "tongue_combo": effective_combo,
                }
            )
            bits = _overlay_230_bits(
                state_vector=state,
                tongue_combo=effective_combo,
                action=action,
                route_allowed=route_allowed,
                issue_count=issue_count,
                deferred_count=deferred_count,
                artifact_digest_hex=digest,
            )
            decision = _decision_record(
                action=action,
                reason=reason,
                confidence=confidence,
                payload={
                    "target_system": target_system,
                    "target_language": target_language,
                    "digest": digest,
                    "gate_report": {
                        "G0_spec": g0_spec,
                        "G1_route": g1_route,
                        "G2_validation_clean": g2_validation,
                        "G3_deferred_safe": g3_deferred,
                    },
                },
            )

            artifacts[target_system] = MeshArtifact(
                source_language=source,
                target_system=target_system,
                target_language=target_language,
                code=prism_artifact.code,
                valid=action == "ALLOW",
                issues=prism_artifact.issues,
                metadata={
                    **prism_artifact.metadata,
                    "tongue_combo": effective_combo,
                    "deferred_construct_hits": deferred_hits,
                    "artifact_digest": digest,
                    "mesh_mode": "native_system_routing",
                },
                state_vector=state,
                decision_record=decision,
                gate_report={
                    "G0_spec": g0_spec,
                    "G1_route": g1_route,
                    "G2_validation_clean": g2_validation,
                    "G3_deferred_safe": g3_deferred,
                },
                mesh_overlay_230_hex=_bits_to_hex(bits),
                mesh_overlay_230_bits=230,
            )

        return artifacts
