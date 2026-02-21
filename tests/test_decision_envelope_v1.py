from __future__ import annotations

import hashlib

from src.governance.decision_envelope_v1 import AUTO_ALLOW
from src.governance.decision_envelope_v1 import CRITICAL
from src.governance.decision_envelope_v1 import DENY
from src.governance.decision_envelope_v1 import HIGH
from src.governance.decision_envelope_v1 import LOW
from src.governance.decision_envelope_v1 import QUARANTINE
from src.governance.decision_envelope_v1 import ActionState
from src.governance.decision_envelope_v1 import ENVELOPE_VERSION_V1
from src.governance.decision_envelope_v1 import MMR_REQUIRED_FIELDS_V1
from src.governance.decision_envelope_v1 import boundary_name
from src.governance.decision_envelope_v1 import canonical_signing_bytes
from src.governance.decision_envelope_v1 import envelope_to_json_projection
from src.governance.decision_envelope_v1 import evaluate_action_inside_envelope
from src.governance.decision_envelope_v1 import harmonic_wall_cost_from_resources
from src.governance.decision_envelope_v1 import json_projection_to_envelope
from src.governance.decision_envelope_v1 import make_envelope_v1
from src.governance.decision_envelope_v1 import mmr_leaf_hash
from src.governance.decision_envelope_v1 import sign_envelope_hmac
from src.governance.decision_envelope_v1 import validate_envelope_schema
from src.governance.decision_envelope_v1 import verify_envelope_hmac


def _mk_env(now_ms: int):
    return make_envelope_v1(
        envelope_id="env-001",
        mission_id="mars-sol-48",
        swarm_id="swarm-a",
        issuer="ground-control",
        key_id="k-main-01",
        valid_from_ms=now_ms - 1_000,
        valid_until_ms=now_ms + 60_000,
        agent_allowlist=["agent-1", "agent-2"],
        capability_allowlist=["nav.move", "sample.collect"],
        target_allowlist=["site-A", "site-B"],
        mission_phase_allowlist=["SURFACE_OPS"],
        max_risk_tier=HIGH,
        power_min=40.0,
        bandwidth_min=10.0,
        thermal_max=85.0,
        rules=[
            {"capability": "nav.move", "target": "site-A", "boundary": AUTO_ALLOW},
            {
                "capability": "sample.collect",
                "target": "site-B",
                "boundary": QUARANTINE,
                "recovery": {
                    "path_id": "recovery-q-01",
                    "playbook_ref": "playbooks/recovery_q01.yaml",
                    "quorum_min": 4,
                    "human_ack_required": True,
                },
            },
            {
                "capability": "sample.collect",
                "target": "site-A",
                "boundary": DENY,
                "recovery": {
                    "path_id": "recovery-d-01",
                    "playbook_ref": "playbooks/recovery_d01.yaml",
                    "quorum_min": 6,
                    "human_ack_required": True,
                },
            },
        ],
    )


def _key_lookup(issuer: str, key_id: str):
    if issuer == "ground-control" and key_id == "k-main-01":
        return b"unit-test-signing-key"
    return None


def test_schema_minimal_v1_required_fields() -> None:
    now_ms = 1_700_000_000_000
    env = _mk_env(now_ms)
    env.identity.version = ENVELOPE_VERSION_V1
    errors = validate_envelope_schema(env)
    assert errors == []


def test_sign_verify_and_deterministic_canonical_bytes() -> None:
    now_ms = 1_700_000_000_000
    env = _mk_env(now_ms)
    signed = sign_envelope_hmac(env, b"unit-test-signing-key")

    ok, reason = verify_envelope_hmac(signed, _key_lookup, now_ms=now_ms)
    assert ok, reason

    b1 = canonical_signing_bytes(signed)
    b2 = canonical_signing_bytes(signed)
    assert b1 == b2
    assert hashlib.sha256(b1).digest() == bytes(signed.authority.signed_payload_hash)


def test_json_projection_round_trips_to_same_signed_proto_bytes() -> None:
    now_ms = 1_700_000_000_000
    env = _mk_env(now_ms)
    signed = sign_envelope_hmac(env, b"unit-test-signing-key")

    original_proto = signed.SerializeToString(deterministic=True)
    projection = envelope_to_json_projection(
        signed, include_jsonld=True, include_proto_payload=True
    )
    restored = json_projection_to_envelope(projection)
    restored_proto = restored.SerializeToString(deterministic=True)

    assert original_proto == restored_proto
    assert projection["_canonical"]["proto_sha256"] == hashlib.sha256(original_proto).hexdigest()


def test_quarantine_boundary_requires_recovery_metadata() -> None:
    now_ms = 1_700_000_000_000
    env = _mk_env(now_ms)
    env.rules[1].recovery.path_id = ""
    env.rules[1].recovery.playbook_ref = ""
    env.rules[1].recovery.quorum_min = 0
    errors = validate_envelope_schema(env)
    assert any("rules[1].recovery.path_id" in e for e in errors)
    assert any("rules[1].recovery.playbook_ref" in e for e in errors)
    assert any("rules[1].recovery.quorum_min" in e for e in errors)


def test_mmr_leaf_hash_deterministic_with_canonicalization() -> None:
    now_ms = 1_700_000_000_000
    env1 = _mk_env(now_ms)
    env2 = _mk_env(now_ms)

    # Different insertion order in lists should collapse under canonical MMR payload.
    env2.scope.agent_allowlist[:] = ["agent-2", "agent-1"]
    env2.scope.capability_allowlist[:] = ["sample.collect", "nav.move"]
    env2.scope.target_allowlist[:] = ["site-B", "site-A"]

    signed1 = sign_envelope_hmac(env1, b"unit-test-signing-key")
    signed2 = sign_envelope_hmac(env2, b"unit-test-signing-key")

    h1 = mmr_leaf_hash(signed1, mmr_fields=MMR_REQUIRED_FIELDS_V1)
    h2 = mmr_leaf_hash(signed2, mmr_fields=MMR_REQUIRED_FIELDS_V1)
    assert h1 == h2


def test_resource_aware_math_is_envelope_bound_not_policy_inventing() -> None:
    now_ms = 1_700_000_000_000
    signed = sign_envelope_hmac(_mk_env(now_ms), b"unit-test-signing-key")

    action = ActionState()
    action.mission_phase = "SURFACE_OPS"
    action.agent_id = "agent-1"
    action.capability = "nav.move"
    action.target = "site-A"
    action.risk_tier = LOW
    action.power = 55.0
    action.bandwidth = 12.0
    action.thermal = 70.0

    result = evaluate_action_inside_envelope(
        signed,
        action,
        _key_lookup,
        now_ms=now_ms,
    )
    assert result.in_envelope is True
    assert boundary_name(result.boundary) == "AUTO_ALLOW"
    assert result.reason == "inside:auto_allow"

    action.power = 10.0
    low_power = evaluate_action_inside_envelope(
        signed,
        action,
        _key_lookup,
        now_ms=now_ms,
    )
    assert low_power.in_envelope is False
    assert low_power.reason == "power_below_floor"


def test_quarantine_action_inside_envelope_with_recovery_path() -> None:
    now_ms = 1_700_000_000_000
    signed = sign_envelope_hmac(_mk_env(now_ms), b"unit-test-signing-key")

    action = ActionState()
    action.mission_phase = "SURFACE_OPS"
    action.agent_id = "agent-2"
    action.capability = "sample.collect"
    action.target = "site-B"
    action.risk_tier = HIGH
    action.power = 60.0
    action.bandwidth = 15.0
    action.thermal = 72.0

    result = evaluate_action_inside_envelope(
        signed,
        action,
        _key_lookup,
        now_ms=now_ms,
    )
    assert result.in_envelope is True
    assert boundary_name(result.boundary) == "QUARANTINE"
    assert result.reason == "inside:quarantine"
    assert result.recovery_path_id == "recovery-q-01"


def test_max_risk_tier_gate_enforced_from_envelope() -> None:
    now_ms = 1_700_000_000_000
    signed = sign_envelope_hmac(_mk_env(now_ms), b"unit-test-signing-key")

    action = ActionState()
    action.mission_phase = "SURFACE_OPS"
    action.agent_id = "agent-1"
    action.capability = "nav.move"
    action.target = "site-A"
    action.risk_tier = CRITICAL
    action.power = 60.0
    action.bandwidth = 15.0
    action.thermal = 70.0

    result = evaluate_action_inside_envelope(
        signed,
        action,
        _key_lookup,
        now_ms=now_ms,
    )
    assert result.in_envelope is False
    assert result.reason == "risk_tier_above_max"


def test_harmonic_wall_cost_monotonic_with_resource_scarcity() -> None:
    low_scarcity = harmonic_wall_cost_from_resources(
        power=80.0,
        bandwidth=20.0,
        thermal=40.0,
        power_min=40.0,
        bandwidth_min=10.0,
        thermal_max=85.0,
    )
    high_scarcity = harmonic_wall_cost_from_resources(
        power=20.0,
        bandwidth=5.0,
        thermal=95.0,
        power_min=40.0,
        bandwidth_min=10.0,
        thermal_max=85.0,
    )
    assert high_scarcity > low_scarcity

