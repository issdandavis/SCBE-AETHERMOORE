"""View-dependent token envelope for SCBE interop overlays.

The envelope keeps the visible dual-frame token separate from the canonical
machine payload. Frame resolution is allowed only when the payload hash,
visual constraints, tongue pairing, and formation route are explicit.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_PHASE_INDEX = {tongue: index for index, tongue in enumerate(TONGUES)}
HODGE_DUAL_PAIRS = {
    frozenset(("KO", "DR")),
    frozenset(("AV", "UM")),
    frozenset(("RU", "CA")),
}
FORMATION_TYPES = ("scatter", "hexagonal_ring", "tetrahedral", "ring")

ROLE_BY_TONGUE = {
    "KO": "control_flow",
    "AV": "transport_context",
    "RU": "binding_entropy",
    "CA": "compute_transform",
    "UM": "security_redaction",
    "DR": "structure_verification",
}

DEFAULT_VISUAL_CONSTRAINTS = {
    "rotation_degrees": 180.0,
    "complementarity_min": 0.72,
    "stroke_density_delta_min": 0.25,
    "decode_margin_min": 0.18,
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _pair_key(a: str, b: str) -> frozenset[str]:
    return frozenset((a.upper(), b.upper()))


@dataclass(frozen=True)
class ViewFrame:
    """One readable frame of a view-dependent token surface."""

    active_tongue: str
    role: str
    schema_ref: str

    def __post_init__(self) -> None:
        tongue = self.active_tongue.upper()
        if tongue not in TONGUES:
            raise ValueError(f"unknown tongue: {self.active_tongue}")
        if not self.role:
            raise ValueError("frame role is required")
        if not self.schema_ref:
            raise ValueError("frame schema_ref is required")
        object.__setattr__(self, "active_tongue", tongue)


@dataclass(frozen=True)
class PayloadRef:
    """Reference to an authoritative machine-readable payload/schema."""

    format: str
    schema: str
    sha256: str

    def __post_init__(self) -> None:
        if not self.format or not self.schema:
            raise ValueError("payload format and schema are required")
        if len(self.sha256) != 64 or any(ch not in "0123456789abcdef" for ch in self.sha256.lower()):
            raise ValueError("payload sha256 must be a 64-character hex digest")
        object.__setattr__(self, "sha256", self.sha256.lower())


@dataclass(frozen=True)
class DecisionRecord:
    """Fail-closed decision record for overlay evaluation."""

    decision: str
    reasons: tuple[str, ...]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ViewTokenEnvelope:
    """Deterministic dual-frame token overlay envelope."""

    token_id: str
    surface_type: str
    frames: dict[str, ViewFrame]
    payload_refs: tuple[PayloadRef, ...]
    canonical_payload_sha256: str
    visual_constraints: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_VISUAL_CONSTRAINTS))
    formation: str = "hexagonal_ring"
    state21: tuple[float, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "scbe_view_dependent_token_v1",
            "token_id": self.token_id,
            "surface_type": self.surface_type,
            "frames": {key: asdict(frame) for key, frame in sorted(self.frames.items())},
            "payload_refs": [asdict(ref) for ref in self.payload_refs],
            "canonical_payload_sha256": self.canonical_payload_sha256,
            "visual_constraints": dict(sorted(self.visual_constraints.items())),
            "formation": self.formation,
            "state21": list(self.state21),
        }


def recommend_formation(
    frame_a: ViewFrame,
    frame_b: ViewFrame,
    payload_refs: tuple[PayloadRef, ...],
    *,
    critical: bool = False,
) -> str:
    """Choose a HYDRA formation route from tongue pair and payload criticality."""

    formats = {ref.format.lower() for ref in payload_refs}
    schemas = " ".join(ref.schema.lower() for ref in payload_refs)
    if critical or formats.intersection({"xtce", "ccsds", "dtn"}) or "command" in schemas:
        return "ring"
    if _pair_key(frame_a.active_tongue, frame_b.active_tongue) == frozenset(("KO", "DR")):
        return "tetrahedral"
    if _pair_key(frame_a.active_tongue, frame_b.active_tongue) in HODGE_DUAL_PAIRS:
        return "hexagonal_ring"
    return "scatter"


def build_state21(
    frame_a: ViewFrame,
    frame_b: ViewFrame,
    visual_constraints: Mapping[str, float],
    formation: str,
) -> tuple[float, ...]:
    """Pack a compact 21D routing vector for this overlay.

    This is governance metadata, not an embedding replacement. Values are
    bounded to stable small ranges for deterministic tests and audit logs.
    """

    pair_is_hodge = 1.0 if _pair_key(frame_a.active_tongue, frame_b.active_tongue) in HODGE_DUAL_PAIRS else 0.0
    complementarity = float(visual_constraints.get("complementarity_min", 0.0))
    density_delta = float(visual_constraints.get("stroke_density_delta_min", 0.0))
    decode_margin = float(visual_constraints.get("decode_margin_min", 0.0))
    rotation = float(visual_constraints.get("rotation_degrees", 0.0)) / 360.0
    formation_index = FORMATION_TYPES.index(formation) / max(1, len(FORMATION_TYPES) - 1)

    values = [0.0] * 21
    values[0] = 1.0
    values[1] = pair_is_hodge
    values[2] = 1.0 if frame_a.schema_ref and frame_b.schema_ref else 0.0
    values[3] = complementarity
    values[4] = density_delta
    values[5] = decode_margin
    values[6 + TONGUE_PHASE_INDEX[frame_a.active_tongue]] = 1.0
    values[12] = rotation
    values[13] = formation_index
    values[14] = 1.0 if frame_a.role != frame_b.role else 0.0
    values[15] = 1.0 if frame_a.schema_ref != frame_b.schema_ref else 0.0
    values[16] = 0.2 if formation != "ring" else 0.4
    values[17] = 0.0 if pair_is_hodge else 0.35
    values[18] = min(1.0, complementarity + decode_margin)
    values[19] = 0.0
    values[20] = 1.0 if formation in FORMATION_TYPES else 0.0
    return tuple(round(float(value), 6) for value in values)


def create_view_token_envelope(
    canonical_payload: Mapping[str, Any],
    frame_a: ViewFrame,
    frame_b: ViewFrame,
    *,
    surface_type: str = "yin_yang_rot180",
    payload_formats: tuple[str, ...] = ("json", "protobuf", "sysmlv2"),
    visual_constraints: Mapping[str, float] | None = None,
    formation: str | None = None,
    critical: bool = False,
) -> ViewTokenEnvelope:
    """Create a deterministic dual-frame overlay envelope."""

    constraints = {**DEFAULT_VISUAL_CONSTRAINTS, **dict(visual_constraints or {})}
    payload_hash = _sha256_json(canonical_payload)
    refs = tuple(
        PayloadRef(format=fmt, schema=f"scbe.interop.{fmt}.ViewTokenPayload", sha256=payload_hash)
        for fmt in payload_formats
    )
    active_formation = formation or recommend_formation(frame_a, frame_b, refs, critical=critical)
    if active_formation not in FORMATION_TYPES:
        raise ValueError(f"unknown formation: {active_formation}")
    state21 = build_state21(frame_a, frame_b, constraints, active_formation)
    identity_payload = {
        "surface_type": surface_type,
        "frames": {"A": asdict(frame_a), "B": asdict(frame_b)},
        "payload_refs": [asdict(ref) for ref in refs],
        "canonical_payload_sha256": payload_hash,
        "formation": active_formation,
        "visual_constraints": constraints,
        "state21": state21,
    }
    token_id = f"sha256:{_sha256_json(identity_payload)}"
    return ViewTokenEnvelope(
        token_id=token_id,
        surface_type=surface_type,
        frames={"A": frame_a, "B": frame_b},
        payload_refs=refs,
        canonical_payload_sha256=payload_hash,
        visual_constraints={key: float(value) for key, value in constraints.items()},
        formation=active_formation,
        state21=state21,
    )


def resolve_frame(envelope: ViewTokenEnvelope, frame_id: str) -> tuple[dict[str, Any] | None, DecisionRecord]:
    """Resolve a frame reading or fail closed."""

    reasons: list[str] = []
    if frame_id not in envelope.frames:
        return None, DecisionRecord("QUARANTINE", ("unknown_frame",), 1.0)
    if envelope.formation not in FORMATION_TYPES:
        reasons.append("unknown_formation")
    if len(envelope.payload_refs) == 0:
        reasons.append("missing_payload_refs")
    frame_a = envelope.frames.get("A")
    frame_b = envelope.frames.get("B")
    if frame_a is None or frame_b is None:
        reasons.append("missing_dual_frame")
    elif frame_a.active_tongue == frame_b.active_tongue:
        reasons.append("same_tongue_frames")
    elif frame_a.role == frame_b.role:
        reasons.append("same_role_frames")
    if float(envelope.visual_constraints.get("rotation_degrees", 0.0)) != 180.0:
        reasons.append("invalid_rotation")
    if float(envelope.visual_constraints.get("complementarity_min", 0.0)) < 0.72:
        reasons.append("low_complementarity")
    if float(envelope.visual_constraints.get("stroke_density_delta_min", 0.0)) < 0.25:
        reasons.append("low_density_delta")
    if float(envelope.visual_constraints.get("decode_margin_min", 0.0)) < 0.18:
        reasons.append("low_decode_margin")

    if reasons:
        return None, DecisionRecord("QUARANTINE", tuple(reasons), 0.95)

    frame = envelope.frames[frame_id]
    return (
        {
            "frame": frame_id,
            "active_tongue": frame.active_tongue,
            "role": frame.role,
            "schema_ref": frame.schema_ref,
            "canonical_payload_sha256": envelope.canonical_payload_sha256,
            "formation": envelope.formation,
            "token_id": envelope.token_id,
        },
        DecisionRecord("ALLOW", ("frame_resolved",), 0.91),
    )


def assess_overlay_worth(envelope: ViewTokenEnvelope) -> DecisionRecord:
    """Score whether this overlay is worth carrying forward experimentally."""

    a, decision_a = resolve_frame(envelope, "A")
    b, decision_b = resolve_frame(envelope, "B")
    reasons: list[str] = []
    score = 0.0

    if decision_a.decision == "ALLOW" and decision_b.decision == "ALLOW" and a and b:
        score += 0.35
    else:
        reasons.extend([*decision_a.reasons, *decision_b.reasons])
    if a and b and a["canonical_payload_sha256"] == b["canonical_payload_sha256"]:
        score += 0.20
    else:
        reasons.append("payload_identity_not_shared")
    frame_a = envelope.frames.get("A")
    frame_b = envelope.frames.get("B")
    if frame_a and frame_b and _pair_key(frame_a.active_tongue, frame_b.active_tongue) in HODGE_DUAL_PAIRS:
        score += 0.20
    else:
        reasons.append("non_hodge_tongue_pair")
    if envelope.formation in {"tetrahedral", "hexagonal_ring", "ring"}:
        score += 0.15
    else:
        reasons.append("weak_formation_route")
    if len(envelope.state21) == 21:
        score += 0.10
    else:
        reasons.append("missing_state21")

    if score >= 0.85:
        return DecisionRecord("ALLOW", ("worth_test_pass",), round(score, 6))
    if score >= 0.55:
        return DecisionRecord("QUARANTINE", tuple(dict.fromkeys(reasons or ["worth_test_partial"])), round(score, 6))
    return DecisionRecord("DENY", tuple(dict.fromkeys(reasons or ["worth_test_fail"])), round(score, 6))

