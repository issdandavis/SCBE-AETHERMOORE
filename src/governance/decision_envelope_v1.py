"""
Decision Envelope v1 (protobuf-first governance contract).

This module implements:
1) Dynamic protobuf message classes for DecisionEnvelopeV1.
2) Deterministic canonical protobuf bytes for signing.
3) HMAC-SHA256 signing/verification (dev placeholder for ML-DSA).
4) Deterministic MMR leaf hash canonicalization.
5) JSON / JSON-LD projection with signed protobuf hash reference.
6) Resource-aware envelope check: "given state, is action inside envelope?"
"""

from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import json
import math
from datetime import datetime, timezone
from typing import Any, Callable

from google.protobuf import descriptor_pb2
from google.protobuf import descriptor_pool
from google.protobuf import json_format
from google.protobuf import message_factory

try:
    from src.scbe_governance_math import PHI
except Exception:  # noqa: BLE001
    PHI = 1.618033988749895


ENVELOPE_VERSION_V1 = "decision-envelope.v1"

MMR_REQUIRED_FIELDS_V1: tuple[str, ...] = (
    "identity.envelope_id",
    "identity.version",
    "identity.mission_id",
    "identity.swarm_id",
    "authority.issuer",
    "authority.key_id",
    "authority.valid_from_ms",
    "authority.valid_until_ms",
    "scope.agent_allowlist",
    "scope.capability_allowlist",
    "scope.target_allowlist",
    "constraints.mission_phase_allowlist",
    "constraints.resources.power_min",
    "constraints.resources.bandwidth_min",
    "constraints.resources.thermal_max",
    "constraints.max_risk_tier",
    "rules",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _build_file_descriptor() -> descriptor_pb2.FileDescriptorProto:
    fd = descriptor_pb2.FileDescriptorProto()
    fd.name = "decision_envelope_v1.proto"
    fd.package = "scbe.governance.v1"
    fd.syntax = "proto3"

    def add_enum(name: str, values: list[tuple[str, int]]) -> None:
        enum = fd.enum_type.add()
        enum.name = name
        for value_name, number in values:
            v = enum.value.add()
            v.name = value_name
            v.number = number

    def add_message(name: str) -> descriptor_pb2.DescriptorProto:
        msg = fd.message_type.add()
        msg.name = name
        return msg

    def add_field(
        msg: descriptor_pb2.DescriptorProto,
        *,
        name: str,
        number: int,
        field_type: int,
        label: int = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type_name: str | None = None,
    ) -> None:
        field = msg.field.add()
        field.name = name
        field.number = number
        field.type = field_type
        field.label = label
        if type_name:
            field.type_name = type_name

    add_enum(
        "BoundaryBehavior",
        [
            ("BOUNDARY_UNSPECIFIED", 0),
            ("AUTO_ALLOW", 1),
            ("QUARANTINE", 2),
            ("DENY", 3),
        ],
    )
    add_enum(
        "RiskTier",
        [
            ("RISK_UNSPECIFIED", 0),
            ("LOW", 1),
            ("MEDIUM", 2),
            ("HIGH", 3),
            ("CRITICAL", 4),
        ],
    )

    identity = add_message("Identity")
    add_field(identity, name="envelope_id", number=1, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    add_field(identity, name="version", number=2, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    add_field(identity, name="mission_id", number=3, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    add_field(identity, name="swarm_id", number=4, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING)

    authority = add_message("Authority")
    add_field(authority, name="issuer", number=1, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    add_field(authority, name="key_id", number=2, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    add_field(authority, name="valid_from_ms", number=3, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT64)
    add_field(authority, name="valid_until_ms", number=4, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT64)
    add_field(authority, name="issued_at_ms", number=5, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT64)
    add_field(authority, name="signature", number=6, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_BYTES)
    add_field(authority, name="signed_payload_hash", number=7, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_BYTES)

    scope = add_message("Scope")
    add_field(
        scope,
        name="agent_allowlist",
        number=1,
        field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED,
    )
    add_field(
        scope,
        name="capability_allowlist",
        number=2,
        field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED,
    )
    add_field(
        scope,
        name="target_allowlist",
        number=3,
        field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED,
    )

    resources = add_message("ResourceConstraints")
    add_field(resources, name="power_min", number=1, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE)
    add_field(resources, name="bandwidth_min", number=2, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE)
    add_field(resources, name="thermal_max", number=3, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE)

    constraints = add_message("Constraints")
    add_field(
        constraints,
        name="mission_phase_allowlist",
        number=1,
        field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED,
    )
    add_field(
        constraints,
        name="resources",
        number=2,
        field_type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".scbe.governance.v1.ResourceConstraints",
    )
    add_field(
        constraints,
        name="max_risk_tier",
        number=3,
        field_type=descriptor_pb2.FieldDescriptorProto.TYPE_ENUM,
        type_name=".scbe.governance.v1.RiskTier",
    )

    recovery = add_message("RecoveryPath")
    add_field(recovery, name="path_id", number=1, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    add_field(recovery, name="playbook_ref", number=2, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    add_field(recovery, name="quorum_min", number=3, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT32)
    add_field(recovery, name="human_ack_required", number=4, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_BOOL)

    rule = add_message("Rule")
    add_field(rule, name="capability", number=1, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    add_field(rule, name="target", number=2, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    add_field(
        rule,
        name="boundary",
        number=3,
        field_type=descriptor_pb2.FieldDescriptorProto.TYPE_ENUM,
        type_name=".scbe.governance.v1.BoundaryBehavior",
    )
    add_field(
        rule,
        name="recovery",
        number=4,
        field_type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".scbe.governance.v1.RecoveryPath",
    )

    audit = add_message("AuditHooks")
    add_field(
        audit,
        name="mmr_fields",
        number=1,
        field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED,
    )
    add_field(audit, name="mmr_leaf_hash", number=2, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_BYTES)

    envelope = add_message("DecisionEnvelopeV1")
    add_field(
        envelope,
        name="identity",
        number=1,
        field_type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".scbe.governance.v1.Identity",
    )
    add_field(
        envelope,
        name="authority",
        number=2,
        field_type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".scbe.governance.v1.Authority",
    )
    add_field(
        envelope,
        name="scope",
        number=3,
        field_type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".scbe.governance.v1.Scope",
    )
    add_field(
        envelope,
        name="constraints",
        number=4,
        field_type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".scbe.governance.v1.Constraints",
    )
    add_field(
        envelope,
        name="rules",
        number=5,
        field_type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".scbe.governance.v1.Rule",
        label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED,
    )
    add_field(
        envelope,
        name="audit",
        number=6,
        field_type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".scbe.governance.v1.AuditHooks",
    )

    action = add_message("ActionState")
    add_field(action, name="mission_phase", number=1, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    add_field(action, name="agent_id", number=2, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    add_field(action, name="capability", number=3, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    add_field(action, name="target", number=4, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    add_field(
        action,
        name="risk_tier",
        number=5,
        field_type=descriptor_pb2.FieldDescriptorProto.TYPE_ENUM,
        type_name=".scbe.governance.v1.RiskTier",
    )
    add_field(action, name="power", number=6, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE)
    add_field(action, name="bandwidth", number=7, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE)
    add_field(action, name="thermal", number=8, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE)

    evaluation = add_message("EvaluationResult")
    add_field(evaluation, name="in_envelope", number=1, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_BOOL)
    add_field(
        evaluation,
        name="boundary",
        number=2,
        field_type=descriptor_pb2.FieldDescriptorProto.TYPE_ENUM,
        type_name=".scbe.governance.v1.BoundaryBehavior",
    )
    add_field(evaluation, name="reason", number=3, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    add_field(evaluation, name="recovery_path_id", number=4, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    add_field(evaluation, name="mmr_leaf_hash", number=5, field_type=descriptor_pb2.FieldDescriptorProto.TYPE_BYTES)

    return fd


_POOL = descriptor_pool.Default()
_FILE_DESCRIPTOR = _build_file_descriptor()
try:
    _POOL.Add(_FILE_DESCRIPTOR)
except Exception:  # noqa: BLE001
    # Already added in this interpreter.
    pass


DecisionEnvelopeV1 = message_factory.GetMessageClass(
    _POOL.FindMessageTypeByName("scbe.governance.v1.DecisionEnvelopeV1")
)
ActionState = message_factory.GetMessageClass(
    _POOL.FindMessageTypeByName("scbe.governance.v1.ActionState")
)
EvaluationResult = message_factory.GetMessageClass(
    _POOL.FindMessageTypeByName("scbe.governance.v1.EvaluationResult")
)

_BOUNDARY_ENUM = _POOL.FindEnumTypeByName("scbe.governance.v1.BoundaryBehavior")
_RISK_ENUM = _POOL.FindEnumTypeByName("scbe.governance.v1.RiskTier")

BOUNDARY_UNSPECIFIED = _BOUNDARY_ENUM.values_by_name["BOUNDARY_UNSPECIFIED"].number
AUTO_ALLOW = _BOUNDARY_ENUM.values_by_name["AUTO_ALLOW"].number
QUARANTINE = _BOUNDARY_ENUM.values_by_name["QUARANTINE"].number
DENY = _BOUNDARY_ENUM.values_by_name["DENY"].number

RISK_UNSPECIFIED = _RISK_ENUM.values_by_name["RISK_UNSPECIFIED"].number
LOW = _RISK_ENUM.values_by_name["LOW"].number
MEDIUM = _RISK_ENUM.values_by_name["MEDIUM"].number
HIGH = _RISK_ENUM.values_by_name["HIGH"].number
CRITICAL = _RISK_ENUM.values_by_name["CRITICAL"].number

BOUNDARY_NAME = {v.number: v.name for v in _BOUNDARY_ENUM.values}
RISK_NAME = {v.number: v.name for v in _RISK_ENUM.values}


def boundary_name(value: int) -> str:
    return BOUNDARY_NAME.get(int(value), "BOUNDARY_UNSPECIFIED")


def risk_name(value: int) -> str:
    return RISK_NAME.get(int(value), "RISK_UNSPECIFIED")


def _sorted_unique(values: list[str]) -> list[str]:
    return sorted({str(x).strip() for x in values if str(x).strip()})


def _copy_envelope(envelope: Any) -> Any:
    out = DecisionEnvelopeV1()
    out.CopyFrom(envelope)
    return out


def _canonical_rule_dict(rule: Any) -> dict[str, Any]:
    return {
        "capability": str(rule.capability),
        "target": str(rule.target),
        "boundary": boundary_name(int(rule.boundary)),
        "recovery": {
            "path_id": str(rule.recovery.path_id),
            "playbook_ref": str(rule.recovery.playbook_ref),
            "quorum_min": int(rule.recovery.quorum_min),
            "human_ack_required": bool(rule.recovery.human_ack_required),
        },
    }


def canonical_signing_bytes(envelope: Any) -> bytes:
    """
    Deterministic protobuf bytes used for signing.

    Canonicalization rules:
    - protobuf deterministic serialization enabled
    - authority.signature stripped
    - audit.mmr_leaf_hash stripped
    """
    env = _copy_envelope(envelope)
    env.authority.signature = b""
    env.authority.signed_payload_hash = b""
    env.audit.mmr_leaf_hash = b""
    return env.SerializeToString(deterministic=True)


def signed_payload_hash(envelope: Any) -> bytes:
    return hashlib.sha256(canonical_signing_bytes(envelope)).digest()


def compute_mmr_leaf_payload(
    envelope: Any,
    mmr_fields: tuple[str, ...] = MMR_REQUIRED_FIELDS_V1,
) -> bytes:
    """
    Deterministic JSON payload for MMR leaf hashing.

    Canonicalization rules:
    - sorted keys
    - compact separators
    - sorted/unique allowlists
    - rules sorted by capability,target,boundary,recovery.path_id
    - signature excluded (policy artifact, not transport signature)
    """
    rules = [_canonical_rule_dict(rule) for rule in envelope.rules]
    rules.sort(
        key=lambda r: (
            r["capability"],
            r["target"],
            r["boundary"],
            r["recovery"]["path_id"],
        )
    )

    obj = {
        "mmr_fields": list(mmr_fields),
        "identity": {
            "envelope_id": str(envelope.identity.envelope_id),
            "version": str(envelope.identity.version),
            "mission_id": str(envelope.identity.mission_id),
            "swarm_id": str(envelope.identity.swarm_id),
        },
        "authority": {
            "issuer": str(envelope.authority.issuer),
            "key_id": str(envelope.authority.key_id),
            "valid_from_ms": int(envelope.authority.valid_from_ms),
            "valid_until_ms": int(envelope.authority.valid_until_ms),
        },
        "scope": {
            "agent_allowlist": _sorted_unique(list(envelope.scope.agent_allowlist)),
            "capability_allowlist": _sorted_unique(list(envelope.scope.capability_allowlist)),
            "target_allowlist": _sorted_unique(list(envelope.scope.target_allowlist)),
        },
        "constraints": {
            "mission_phase_allowlist": _sorted_unique(
                list(envelope.constraints.mission_phase_allowlist)
            ),
            "resources": {
                "power_min": float(envelope.constraints.resources.power_min),
                "bandwidth_min": float(envelope.constraints.resources.bandwidth_min),
                "thermal_max": float(envelope.constraints.resources.thermal_max),
            },
            "max_risk_tier": risk_name(int(envelope.constraints.max_risk_tier)),
        },
        "rules": rules,
    }

    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def mmr_leaf_hash(envelope: Any, mmr_fields: tuple[str, ...] = MMR_REQUIRED_FIELDS_V1) -> bytes:
    return hashlib.sha256(compute_mmr_leaf_payload(envelope, mmr_fields=mmr_fields)).digest()


def validate_envelope_schema(envelope: Any) -> list[str]:
    errors: list[str] = []

    if not str(envelope.identity.envelope_id).strip():
        errors.append("identity.envelope_id is required")
    if str(envelope.identity.version).strip() != ENVELOPE_VERSION_V1:
        errors.append(f"identity.version must be '{ENVELOPE_VERSION_V1}'")
    if not str(envelope.identity.mission_id).strip():
        errors.append("identity.mission_id is required")
    if not str(envelope.identity.swarm_id).strip():
        errors.append("identity.swarm_id is required")

    if not str(envelope.authority.issuer).strip():
        errors.append("authority.issuer is required")
    if not str(envelope.authority.key_id).strip():
        errors.append("authority.key_id is required")
    if int(envelope.authority.valid_until_ms) <= int(envelope.authority.valid_from_ms):
        errors.append("authority validity window is invalid")

    if len(envelope.scope.agent_allowlist) == 0:
        errors.append("scope.agent_allowlist must be non-empty")
    if len(envelope.scope.capability_allowlist) == 0:
        errors.append("scope.capability_allowlist must be non-empty")
    if len(envelope.scope.target_allowlist) == 0:
        errors.append("scope.target_allowlist must be non-empty")

    if len(envelope.constraints.mission_phase_allowlist) == 0:
        errors.append("constraints.mission_phase_allowlist must be non-empty")
    if int(envelope.constraints.max_risk_tier) == RISK_UNSPECIFIED:
        errors.append("constraints.max_risk_tier must be set")

    if len(envelope.rules) == 0:
        errors.append("rules must contain at least one rule")
    for idx, rule in enumerate(envelope.rules):
        prefix = f"rules[{idx}]"
        if not str(rule.capability).strip():
            errors.append(f"{prefix}.capability is required")
        if not str(rule.target).strip():
            errors.append(f"{prefix}.target is required")
        if int(rule.boundary) == BOUNDARY_UNSPECIFIED:
            errors.append(f"{prefix}.boundary must be set")
        if int(rule.boundary) in (QUARANTINE, DENY):
            if not str(rule.recovery.path_id).strip():
                errors.append(f"{prefix}.recovery.path_id required for boundary={boundary_name(int(rule.boundary))}")
            if not str(rule.recovery.playbook_ref).strip():
                errors.append(
                    f"{prefix}.recovery.playbook_ref required for boundary={boundary_name(int(rule.boundary))}"
                )
        if int(rule.boundary) == QUARANTINE and int(rule.recovery.quorum_min) <= 0:
            errors.append(f"{prefix}.recovery.quorum_min must be > 0 for QUARANTINE")

    fields = list(envelope.audit.mmr_fields)
    if fields:
        missing = [f for f in MMR_REQUIRED_FIELDS_V1 if f not in fields]
        if missing:
            errors.append(f"audit.mmr_fields missing required fields: {', '.join(missing)}")

    return errors


def sign_envelope_hmac(envelope: Any, signing_key: bytes | str, *, set_mmr_hook: bool = True) -> Any:
    """
    Sign envelope with deterministic protobuf payload hash.

    Dev placeholder signature:
      HMAC-SHA256(signing_key, signed_payload_hash)
    """
    key = signing_key.encode("utf-8") if isinstance(signing_key, str) else bytes(signing_key)
    env = _copy_envelope(envelope)
    if int(env.authority.issued_at_ms) == 0:
        env.authority.issued_at_ms = _now_ms()

    if set_mmr_hook and len(env.audit.mmr_fields) == 0:
        env.audit.mmr_fields.extend(MMR_REQUIRED_FIELDS_V1)

    payload_hash = signed_payload_hash(env)
    env.authority.signed_payload_hash = payload_hash
    env.authority.signature = hmac.new(key, payload_hash, hashlib.sha256).digest()

    if set_mmr_hook:
        env.audit.mmr_leaf_hash = mmr_leaf_hash(env, mmr_fields=tuple(env.audit.mmr_fields))
    return env


def verify_envelope_hmac(
    envelope: Any,
    key_lookup: Callable[[str, str], bytes | str | None],
    *,
    now_ms: int | None = None,
) -> tuple[bool, str]:
    errors = validate_envelope_schema(envelope)
    if errors:
        return False, "; ".join(errors)

    current_ms = int(now_ms if now_ms is not None else _now_ms())
    if current_ms < int(envelope.authority.valid_from_ms):
        return False, "envelope not yet valid"
    if current_ms > int(envelope.authority.valid_until_ms):
        return False, "envelope expired"

    key = key_lookup(str(envelope.authority.issuer), str(envelope.authority.key_id))
    if key is None:
        return False, "no signing key available for issuer/key_id"
    key_bytes = key.encode("utf-8") if isinstance(key, str) else bytes(key)

    expected_payload_hash = signed_payload_hash(envelope)
    if bytes(envelope.authority.signed_payload_hash) != expected_payload_hash:
        return False, "signed_payload_hash mismatch"

    expected_sig = hmac.new(key_bytes, expected_payload_hash, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_sig, bytes(envelope.authority.signature)):
        return False, "signature mismatch"

    if len(envelope.audit.mmr_fields) > 0 and bytes(envelope.audit.mmr_leaf_hash):
        expected_mmr = mmr_leaf_hash(envelope, mmr_fields=tuple(envelope.audit.mmr_fields))
        if bytes(envelope.audit.mmr_leaf_hash) != expected_mmr:
            return False, "mmr_leaf_hash mismatch"

    return True, "ok"


def envelope_to_json_projection(
    envelope: Any,
    *,
    include_jsonld: bool = False,
    include_proto_payload: bool = True,
) -> dict[str, Any]:
    """
    JSON projection with canonical protobuf reference.

    Round-trip guarantee path:
      include_proto_payload=True -> _canonical.proto_b64 present.
    """
    env_dict = json_format.MessageToDict(
        envelope,
        preserving_proto_field_name=True,
        use_integers_for_enums=False,
    )

    proto_bytes = envelope.SerializeToString(deterministic=True)
    canonical = {
        "proto_sha256": hashlib.sha256(proto_bytes).hexdigest(),
        "signed_payload_sha256": bytes(envelope.authority.signed_payload_hash).hex(),
        "generated_at": _utc_now_iso(),
    }
    if include_proto_payload:
        canonical["proto_b64"] = base64.b64encode(proto_bytes).decode("ascii")
    env_dict["_canonical"] = canonical

    if include_jsonld:
        env_dict["@context"] = {
            "@vocab": "https://scbe.dev/schema/decision-envelope/v1#",
            "envelope_id": "identity.envelope_id",
            "mission_id": "identity.mission_id",
            "swarm_id": "identity.swarm_id",
            "issuer": "authority.issuer",
            "key_id": "authority.key_id",
            "mmr_leaf_hash": "audit.mmr_leaf_hash",
        }
        env_dict["@type"] = "DecisionEnvelopeV1"

    return env_dict


def json_projection_to_envelope(payload: dict[str, Any]) -> Any:
    data = copy.deepcopy(payload)
    canonical = data.pop("_canonical", {}) if isinstance(data, dict) else {}
    data.pop("@context", None)
    data.pop("@type", None)

    proto_b64 = canonical.get("proto_b64")
    if isinstance(proto_b64, str) and proto_b64.strip():
        raw = base64.b64decode(proto_b64.encode("ascii"))
        env = DecisionEnvelopeV1()
        env.ParseFromString(raw)
        expected_hash = canonical.get("proto_sha256")
        if expected_hash:
            actual = hashlib.sha256(raw).hexdigest()
            if actual != expected_hash:
                raise ValueError("proto_sha256 mismatch in JSON projection")
        return env

    env = DecisionEnvelopeV1()
    json_format.ParseDict(data, env, ignore_unknown_fields=True)
    return env


def harmonic_wall_cost_from_resources(
    *,
    power: float,
    bandwidth: float,
    thermal: float,
    power_min: float,
    bandwidth_min: float,
    thermal_max: float,
    realm_scale: float = 1.0,
) -> float:
    """
    Scarcity-adjusted harmonic wall cost.

    d* is derived strictly from envelope constraints and current resources:
      scarcity = max(power_min/power, bandwidth_min/bandwidth, thermal/thermal_max, 1)
      d* = scarcity - 1
      H = R * pi^(phi * d*)
    """
    eps = 1e-9
    ratios = [1.0]
    if power_min > 0:
        ratios.append(float(power_min) / max(float(power), eps))
    if bandwidth_min > 0:
        ratios.append(float(bandwidth_min) / max(float(bandwidth), eps))
    if thermal_max > 0:
        ratios.append(float(thermal) / max(float(thermal_max), eps))
    scarcity = max(ratios)
    d_star = max(0.0, scarcity - 1.0)
    return float(realm_scale) * (math.pi ** (PHI * d_star))


def _in_allowlist(value: str, items: list[str]) -> bool:
    return str(value) in {str(x) for x in items}


def _find_rule(envelope: Any, capability: str, target: str) -> Any | None:
    for rule in envelope.rules:
        cap_match = (str(rule.capability) == capability) or (str(rule.capability) == "*")
        tgt_match = (str(rule.target) == target) or (str(rule.target) == "*")
        if cap_match and tgt_match:
            return rule
    return None


def evaluate_action_inside_envelope(
    envelope: Any,
    action: Any,
    key_lookup: Callable[[str, str], bytes | str | None],
    *,
    now_ms: int | None = None,
    realm_scale: float = 1.0,
) -> Any:
    """
    Envelope-only check:
      "given state, is action inside the envelope?"

    Policy is not invented here; it is read from signed envelope fields.
    """
    out = EvaluationResult()
    out.in_envelope = False
    out.boundary = DENY
    out.reason = "denied"
    out.recovery_path_id = ""
    out.mmr_leaf_hash = mmr_leaf_hash(envelope)

    ok, reason = verify_envelope_hmac(envelope, key_lookup, now_ms=now_ms)
    if not ok:
        out.reason = f"invalid_envelope:{reason}"
        return out

    if not _in_allowlist(str(action.agent_id), list(envelope.scope.agent_allowlist)):
        out.reason = "agent_out_of_scope"
        return out
    if not _in_allowlist(str(action.capability), list(envelope.scope.capability_allowlist)):
        out.reason = "capability_out_of_scope"
        return out
    if not _in_allowlist(str(action.target), list(envelope.scope.target_allowlist)):
        out.reason = "target_out_of_scope"
        return out

    if not _in_allowlist(
        str(action.mission_phase),
        list(envelope.constraints.mission_phase_allowlist),
    ):
        out.reason = "mission_phase_blocked"
        return out

    if int(action.risk_tier) > int(envelope.constraints.max_risk_tier):
        out.reason = "risk_tier_above_max"
        return out

    c = envelope.constraints.resources
    if float(action.power) < float(c.power_min):
        out.reason = "power_below_floor"
        return out
    if float(action.bandwidth) < float(c.bandwidth_min):
        out.reason = "bandwidth_below_floor"
        return out
    if float(c.thermal_max) > 0 and float(action.thermal) > float(c.thermal_max):
        out.reason = "thermal_above_limit"
        return out

    rule = _find_rule(envelope, str(action.capability), str(action.target))
    if rule is None:
        out.reason = "no_policy_rule"
        return out

    _ = harmonic_wall_cost_from_resources(
        power=float(action.power),
        bandwidth=float(action.bandwidth),
        thermal=float(action.thermal),
        power_min=float(c.power_min),
        bandwidth_min=float(c.bandwidth_min),
        thermal_max=float(c.thermal_max),
        realm_scale=realm_scale,
    )

    boundary = int(rule.boundary)
    out.boundary = boundary
    if boundary == AUTO_ALLOW:
        out.in_envelope = True
        out.reason = "inside:auto_allow"
        return out
    if boundary == QUARANTINE:
        out.in_envelope = True
        out.reason = "inside:quarantine"
        out.recovery_path_id = str(rule.recovery.path_id)
        return out

    out.in_envelope = False
    out.reason = "inside:deny"
    out.recovery_path_id = str(rule.recovery.path_id)
    return out


def make_envelope_v1(
    *,
    envelope_id: str,
    mission_id: str,
    swarm_id: str,
    issuer: str,
    key_id: str,
    valid_from_ms: int,
    valid_until_ms: int,
    agent_allowlist: list[str],
    capability_allowlist: list[str],
    target_allowlist: list[str],
    mission_phase_allowlist: list[str],
    max_risk_tier: int,
    power_min: float,
    bandwidth_min: float,
    thermal_max: float,
    rules: list[dict[str, Any]],
) -> Any:
    env = DecisionEnvelopeV1()

    env.identity.envelope_id = str(envelope_id)
    env.identity.version = ENVELOPE_VERSION_V1
    env.identity.mission_id = str(mission_id)
    env.identity.swarm_id = str(swarm_id)

    env.authority.issuer = str(issuer)
    env.authority.key_id = str(key_id)
    env.authority.valid_from_ms = int(valid_from_ms)
    env.authority.valid_until_ms = int(valid_until_ms)

    env.scope.agent_allowlist.extend(agent_allowlist)
    env.scope.capability_allowlist.extend(capability_allowlist)
    env.scope.target_allowlist.extend(target_allowlist)

    env.constraints.mission_phase_allowlist.extend(mission_phase_allowlist)
    env.constraints.max_risk_tier = int(max_risk_tier)
    env.constraints.resources.power_min = float(power_min)
    env.constraints.resources.bandwidth_min = float(bandwidth_min)
    env.constraints.resources.thermal_max = float(thermal_max)

    for item in rules:
        rule = env.rules.add()
        rule.capability = str(item.get("capability", ""))
        rule.target = str(item.get("target", ""))
        rule.boundary = int(item.get("boundary", BOUNDARY_UNSPECIFIED))
        recovery = item.get("recovery", {}) or {}
        rule.recovery.path_id = str(recovery.get("path_id", ""))
        rule.recovery.playbook_ref = str(recovery.get("playbook_ref", ""))
        rule.recovery.quorum_min = int(recovery.get("quorum_min", 0))
        rule.recovery.human_ack_required = bool(recovery.get("human_ack_required", False))

    return env
