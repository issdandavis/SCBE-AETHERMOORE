"""Decision-composition regressions, not threat-detector accuracy measurements."""

import importlib
import json
from pathlib import Path
import sys
from types import ModuleType

import numpy as np
import pytest


@pytest.fixture(scope="module", params=["src/symphonic_cipher", "symphonic_cipher"])
def full(request):
    directory = Path(__file__).resolve().parents[2] / request.param / "scbe_aethermoore"
    alias = "_full_policy_" + request.param.replace("/", "_")
    package = ModuleType(alias)
    package.__path__ = [str(directory)]
    sys.modules[alias] = package
    module = importlib.import_module(alias + ".full_system")
    assert Path(module.__file__).resolve() == directory / "full_system.py"
    return module


def assessment(full, decision):
    # Real bounded L12 -> L13 computation: not a fabricated risk label.
    layers = importlib.import_module(full.__package__ + ".layers.fourteen_layer_pipeline")
    distance = {"ALLOW": 0.0, "REVIEW": 1.0, "DENY": 3.0, "SNAP": 100.0}[decision]
    value = layers.layer_13_decision(0.0, layers.layer_12_harmonic_scaling(distance), 1.0, 0, 1.0, 2.0)
    assert value.decision == decision
    return value


def decide(system, risk, **overrides):
    values = dict(
        risk_assessment=risk,
        entropy_zone="OPTIMAL",
        entropy_rate=1.0,
        manifold_divergence=0.0,
        topology_valid=True,
        tau_flow=1.0,
        q_fidelity=1.0,
        is_cold_start=False,
    )
    values.update(overrides)
    return system._compute_final_decision(**values)


@pytest.mark.parametrize("cold", [True, False])
@pytest.mark.parametrize("mode", ["NORMAL", "HEIGHTENED", "LOCKDOWN", "LEARNING"])
@pytest.mark.parametrize(
    "layer,expected", [("ALLOW", "ALLOW"), ("REVIEW", "QUARANTINE"), ("DENY", "DENY"), ("SNAP", "SNAP")]
)
def test_l12_l13_outcomes_survive_every_mode_and_bootstrap(full, cold, mode, layer, expected):
    system = full.SCBEFullSystem(mode=full.GovernanceMode[mode])
    if mode == "LOCKDOWN" and layer != "SNAP":
        expected = "DENY"
    decision, confidence, _ = decide(system, assessment(full, layer), is_cold_start=cold)
    assert decision.value == expected
    assert np.isfinite(confidence) and 0 <= confidence <= 1


@pytest.mark.parametrize("cold", [True, False])
@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"topology_valid": False}, "SNAP"),
        ({"tau_flow": 0.0}, "DENY"),
        ({"manifold_divergence": 1000.0}, "SNAP"),
        ({"q_fidelity": float("nan")}, "DENY"),
        ({"q_fidelity": 1.01}, "DENY"),
        ({"entropy_rate": float("inf")}, "DENY"),
        ({"manifold_divergence": -1.0}, "DENY"),
        ({"tau_flow": float("nan")}, "DENY"),
        ({"entropy_zone": "unknown"}, "DENY"),
        ({"topology_valid": "yes"}, "DENY"),
    ],
)
def test_allow_does_not_override_other_failed_or_invalid_checks(full, cold, changes, expected):
    decision, confidence, _ = decide(full.SCBEFullSystem(), assessment(full, "ALLOW"), is_cold_start=cold, **changes)
    assert decision.value == expected
    assert np.isfinite(confidence)


@pytest.mark.parametrize(
    "field,value",
    [
        ("decision", "UNKNOWN"),
        ("decision", None),
        ("raw_risk", float("nan")),
        ("scaled_risk", float("inf")),
        ("coherence", -0.1),
        ("raw_risk", True),
        ("level", "LOW"),
    ],
)
def test_malformed_layer_evidence_cannot_allow(full, field, value):
    risk = assessment(full, "ALLOW")
    setattr(risk, field, value)
    assert decide(full.SCBEFullSystem(), risk, is_cold_start=True)[0].value == "DENY"


def test_high_risk_cannot_claim_allow(full):
    risk = assessment(full, "DENY")
    risk.decision = "ALLOW"
    assert decide(full.SCBEFullSystem(), risk)[0].value == "DENY"


def test_invalid_configuration_cannot_disable_divergence_guard(full):
    system = full.SCBEFullSystem(epsilon=float("nan"))
    assert decide(system, assessment(full, "ALLOW"))[0].value == "DENY"


@pytest.mark.parametrize("mode", ["NORMAL", "HEIGHTENED", "LEARNING"])
def test_secondary_checks_can_escalate_review(full, mode):
    system = full.SCBEFullSystem(mode=full.GovernanceMode[mode])
    decision, _, _ = decide(
        system, assessment(full, "REVIEW"), q_fidelity=0.5, entropy_zone="NEGENTROPY", entropy_rate=0.0
    )
    assert decision.value == "DENY"


def set_pipeline_outcome(monkeypatch, system, full, decision):
    original = system.pipeline.process

    def process(**kwargs):
        _actual, states = original(**kwargs)
        return assessment(full, decision), states

    monkeypatch.setattr(system.pipeline, "process", process)


@pytest.mark.parametrize("outcome", ["REVIEW", "DENY", "SNAP"])
def test_refused_initial_request_cannot_install_reference(full, monkeypatch, outcome):
    system = full.SCBEFullSystem(secret_key=b"test-only" * 4)
    set_pipeline_outcome(monkeypatch, system, full, outcome)
    result = system.evaluate_intent("fixture-user", "fixture-intent", timestamp=1.0)
    assert result.decision.value == {"REVIEW": "QUARANTINE", "DENY": "DENY", "SNAP": "SNAP"}[outcome]
    assert system.state.reference_state is None
    assert system.state.reference_embedding is None
    assert system.state.total_allows == 0


@pytest.mark.parametrize("outcome", ["REVIEW", "DENY", "SNAP"])
def test_refused_request_preserves_approved_reference(full, monkeypatch, outcome):
    system = full.SCBEFullSystem(secret_key=b"test-only" * 4)
    set_pipeline_outcome(monkeypatch, system, full, "ALLOW")
    approved = system.evaluate_intent("fixture-user", "fixture-intent", timestamp=1.0)
    assert approved.decision.value == "ALLOW", approved.explanation
    before = system.state.reference_state
    embedding = system.state.reference_embedding.copy()
    set_pipeline_outcome(monkeypatch, system, full, outcome)
    refused = system.evaluate_intent("fixture-user", "other-intent", timestamp=1.01)
    assert refused.decision.value != "ALLOW"
    assert system.state.reference_state is before
    assert np.array_equal(system.state.reference_embedding, embedding)
    assert system.state.total_allows == 1


def test_audit_authenticates_final_refusal_not_only_pipeline_allow(full, monkeypatch):
    system = full.SCBEFullSystem(secret_key=b"test-only" * 4, mode=full.GovernanceMode.LOCKDOWN)
    set_pipeline_outcome(monkeypatch, system, full, "ALLOW")
    result = system.evaluate_intent("fixture-user", "fixture-intent", timestamp=1.0)
    assert result.decision.value == "DENY"
    data, nonce, tag = system.state.audit_chain[-1]
    audit = json.loads(data)
    assert audit["schema"] == "scbe.full-system-decision.v2"
    assert audit["pipeline_decision"] == "ALLOW"
    assert audit["decision"] == result.decision.value
    assert system.verify_audit_chain()
    audit["decision"] = "ALLOW"
    system.state.audit_chain[-1] = (json.dumps(audit).encode(), nonce, tag)
    assert not system.verify_audit_chain()


def test_versioned_audit_can_continue_an_existing_opaque_chain(full):
    system = full.SCBEFullSystem(secret_key=b"test-only" * 4)
    old_data, old_nonce = b"legacy|entry|ALLOW", b"fixture-nonce"
    old_tag = full.hmac_chain_tag(old_data, old_nonce, system.state.audit_iv, system.state.secret_key)
    system.state.audit_chain.append((old_data, old_nonce, old_tag))
    system.evaluate_intent("user", "read-document", timestamp=1.0)
    assert len(system.state.audit_chain) == 2
    assert system.state.audit_chain[0] == (old_data, old_nonce, old_tag)
    assert system.verify_audit_chain()


def test_real_public_pipeline_never_softens_its_layer_outcome(full):
    rank = {"ALLOW": 0, "REVIEW": 1, "QUARANTINE": 1, "DENY": 2, "SNAP": 3}
    system = full.SCBEFullSystem(secret_key=b"test-only" * 4)
    for timestamp in (1.0, 1.1, 2.0):
        result = system.evaluate_intent("user", "read-document", timestamp=timestamp)
        assert rank[result.decision.value] >= rank[result.risk_assessment.decision]


def test_repeated_layer_denials_escalate_mode_without_creating_a_baseline(full, monkeypatch):
    system = full.SCBEFullSystem(secret_key=b"test-only" * 4)
    set_pipeline_outcome(monkeypatch, system, full, "DENY")
    for i in range(5):
        result = system.evaluate_intent("user", "read-document", timestamp=1.0 + i / 100)
        assert result.decision.value in ("DENY", "SNAP")
    assert system.state.mode == full.GovernanceMode.LOCKDOWN
    assert system.state.reference_state is None
