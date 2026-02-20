from __future__ import annotations

from copy import deepcopy

import pytest

from src.security.decision_envelope_predicate import (
    evaluate_action_dict_inside_envelope,
)


def _envelope() -> dict:
    return {
        "schema_version": "decision-envelope/v1",
        "projection_of": "scbe.decision_envelope.v1.DecisionEnvelopeV1",
        "envelope_id": "de-001",
        "issued_at_utc": "2026-02-20T05:00:00Z",
        "identity": {"mission_id": "m1", "swarm_id": "s1"},
        "authority": {
            "issuer": "ground-control",
            "key_id": "k1",
            "valid_from_utc": "2026-02-20T05:00:00Z",
            "valid_until_utc": "2026-02-20T06:00:00Z",
            "signature": {
                "algorithm": "ML-DSA-65",
                "value_b64": "ZmFrZS1zaWduYXR1cmU=",
                "signed_protobuf_sha256": "a" * 64,
            },
        },
        "scope": {
            "agent_allowlist": ["agent-1"],
            "capability_allowlist": ["browser.navigate"],
            "target_allowlist": [{"kind": "host", "id": "docs.example.internal"}],
        },
        "constraints": {
            "mission_phase_allowlist": ["PLAN", "DRAFT"],
            "resource_floors": {
                "power_mw_min": 10000.0,
                "bandwidth_kbps_min": 2000.0,
                "thermal_headroom_c_min": 8.0,
            },
            "max_risk_tier": "DELIBERATION",
            "harmonic_wall": {
                "scarcity_limit": 0.35,
                "base": 2.0,
                "alpha": 1.5,
            },
        },
        "boundary": {"behavior": "AUTO_ALLOW", "reason": "inside-envelope"},
        "quorum": {
            "n": 6,
            "f_max": 1,
            "quorum_min": 3,
            "quorum_policy": 4,
            "approvals_observed": 4,
            "approver_ids": ["a", "b", "c", "d"],
            "vote_set_sha256": "b" * 64,
        },
        "harmonic_wall": {
            "d_star": 0.2,
            "coherence": 0.8,
            "scarcity_score": 0.0,
            "harmonic_cost": 1.0,
            "threshold": 1.35,
            "inside_boundary": True,
        },
        "audit": {
            "canonicalization": "PROTOBUF_DETERMINISTIC_V1",
            "signed_protobuf_sha256": "c" * 64,
            "mmr_leaf_sha256": "d" * 64,
            "mmr_prev_root_sha256": "e" * 64,
            "mmr_leaf_index": 1,
            "hash_fields": ["identity", "scope", "constraints", "boundary"],
        },
    }


def _action() -> dict:
    return {
        "mission_phase": "PLAN",
        "agent_id": "agent-1",
        "capability_id": "browser.navigate",
        "target": {"kind": "host", "id": "docs.example.internal"},
        "risk_tier": "DELIBERATION",
        "resources": {
            "power_mw": 12000.0,
            "bandwidth_kbps": 2500.0,
            "thermal_headroom_c": 12.0,
        },
    }


def test_action_inside_envelope_returns_true() -> None:
    res = evaluate_action_dict_inside_envelope(_action(), _envelope())
    assert res.inside_boundary is True
    assert res.violations == ()
    assert res.scarcity_score == pytest.approx(0.0)
    assert res.harmonic_cost == pytest.approx(1.0)


def test_resource_floor_violation_returns_outside() -> None:
    action = _action()
    action["resources"]["thermal_headroom_c"] = 4.0
    res = evaluate_action_dict_inside_envelope(action, _envelope())
    assert res.inside_boundary is False
    assert any(v.startswith("resource_floor_thermal_below:") for v in res.violations)


def test_risk_tier_above_max_returns_outside() -> None:
    action = _action()
    action["risk_tier"] = "CRITICAL"
    res = evaluate_action_dict_inside_envelope(action, _envelope())
    assert res.inside_boundary is False
    assert any(v.startswith("risk_tier_exceeds_max:") for v in res.violations)


def test_missing_recovery_for_quarantine_raises() -> None:
    env = _envelope()
    env["boundary"] = {"behavior": "QUARANTINE", "reason": "manual-review-required"}
    with pytest.raises(ValueError):
        evaluate_action_dict_inside_envelope(_action(), env)


def test_target_outside_allowlist_returns_outside() -> None:
    action = deepcopy(_action())
    action["target"] = {"kind": "host", "id": "forbidden.example.internal"}
    res = evaluate_action_dict_inside_envelope(action, _envelope())
    assert res.inside_boundary is False
    assert any(v.startswith("target_not_allowed:") for v in res.violations)

