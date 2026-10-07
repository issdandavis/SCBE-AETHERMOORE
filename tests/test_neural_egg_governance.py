"""Security regressions for measured neural evidence before Egg key use."""

import base64
import copy
import math
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from symphonic_cipher.scbe_aethermoore.ai_brain.detection import detect_phase_distance
from symphonic_cipher.scbe_aethermoore.ai_brain.egg_governance import NeuralEggGate, NeuralEvidence, NeuralGatePolicy
from symphonic_cipher.scbe_aethermoore.ai_brain.multiscale_spectrum import (
    analyze_trajectory,
    participation_ratio,
    spectral_entropy,
)
from symphonic_cipher.scbe_aethermoore.ai_brain.unified_state import (
    TrajectoryPoint,
    hyperbolic_distance_safe,
    safe_poincare_embed,
)
from symphonic_cipher.scbe_aethermoore import sacred_egg_integrator as eggs


def test_small_distance_and_embedding_are_not_rounded_to_zero():
    assert hyperbolic_distance_safe([0.0], [1e-12]) == pytest.approx(2e-12, rel=1e-12, abs=0)
    assert safe_poincare_embed([1e-12]) == [5e-13]


def test_distance_at_representable_boundary():
    r = math.nextafter(1.0, 0.0)
    assert hyperbolic_distance_safe([0.0], [r]) == pytest.approx(2 * math.atanh(r))


@pytest.mark.parametrize("u,v", [([], []), ([0], [0, 0]), ([1], [0]), ([2], [2]), ([math.nan], [0]), ([math.inf], [0])])
def test_invalid_geometry_is_rejected(u, v):
    with pytest.raises(ValueError):
        hyperbolic_distance_safe(u, v)


def test_distance_agrees_with_acosh_away_from_cancellation():
    rng = np.random.default_rng(71)
    for _ in range(40):
        u, v = rng.normal(0, 0.08, (2, 21))
        expected = math.acosh(1 + 2 * sum((u - v) ** 2) / ((1 - sum(u**2)) * (1 - sum(v**2))))
        assert hyperbolic_distance_safe(u.tolist(), v.tolist()) == pytest.approx(expected)


def test_phase_score_is_invariant_under_full_rotations():
    def score(phase):
        state = [0.0] * 21
        state[16] = phase
        return detect_phase_distance([TrajectoryPoint(0, state, [0.0] * 21, 0.0)], 0).score

    assert score(math.pi) == pytest.approx(score(5 * math.pi))
    assert score(math.pi) == pytest.approx(score(-3 * math.pi))


@pytest.mark.parametrize("scale", [1e-120, 1e-10, 1.0, 1e100])
def test_spectral_ratios_do_not_depend_on_units(scale):
    eigenvalues = np.array([4.0, 2.0, 1.0, 0.0])
    assert participation_ratio(scale * eigenvalues) == pytest.approx(49 / 21)
    assert spectral_entropy(scale * eigenvalues) == pytest.approx(spectral_entropy(eigenvalues))


def test_multiscale_report_is_invariant_under_rescaling():
    trajectory = np.random.default_rng(23).normal(0, 1, (24, 21))
    baseline = analyze_trajectory(trajectory)
    small = analyze_trajectory(trajectory * 1e-7)
    assert small.anomaly_score == pytest.approx(baseline.anomaly_score)
    assert participation_ratio(np.zeros(21)) == 0
    assert spectral_entropy(np.zeros(21)) == 0


@pytest.fixture
def states():
    """Synthetic composition fixture, not a real-world false-positive benchmark."""
    rng = np.random.default_rng(17)
    rows = []
    for i in range(12):
        s = [0.0] * 21
        t = 0.02 * i
        s[0], s[17], s[6], s[7] = 0.5 + t, 0.5 - t, t, -t
        for j in (8, 9, 10, 11, 18, 19, 20):
            s[j] = 0.001 * rng.random()
        rows.append(s)
    return rows


@pytest.fixture
def request_data():
    egg = eggs.SacredEgg("test-egg", "KO", "diamond", {}, {"ct_spec": base64.b64encode(b"x" * 23).decode()})
    return eggs.neural_hatch_request(egg, [0.0] * 6, "KO")


@pytest.fixture(scope="module")
def signers():
    from crypto.pqc_liboqs import LIBOQS_AVAILABLE, PURE_PQC_AVAILABLE, MLDSA65

    if not (LIBOQS_AVAILABLE or PURE_PQC_AVAILABLE):
        pytest.skip("Real ML-DSA backend required; do not substitute demo signatures")
    return {f"witness-{i}": MLDSA65() for i in range(3)}


@pytest.fixture
def setup_gate(states, signers):
    claims, reports = set(), []

    def claim(audience, nonce, expires):
        # Test-only store. Production supplies atomic challenge issuance/consumption
        # shared by all workers, with TTL and unknown-challenge rejection.
        key = (audience, nonce)
        if key in claims:
            return False
        claims.add(key)
        return True

    policy = NeuralGatePolicy("neural-test", states[0], max_hyperbolic_distance=2)
    gate = NeuralEggGate(
        policy, {k: s.public_key for k, s in signers.items()}, claim, clock=lambda: 100, audit=reports.append
    )
    return gate, claims, reports


def signed(gate, request_data, states, signers, **changes):
    evidence = NeuralEvidence("test-challenge-0123456789", 100.0, states, tuple(float(i) for i in range(88, 100)))
    evidence = replace(evidence, **changes)
    message = gate.signing_message(request_data, evidence)
    return replace(evidence, signatures={name: signer.sign(message) for name, signer in signers.items()})


def test_authenticated_balanced_window_passes_real_sensors(setup_gate, request_data, states, signers):
    gate, _, reports = setup_gate
    before = copy.deepcopy(states)
    report = gate.evaluate(request_data, signed(gate, request_data, states, signers))
    assert report.allowed
    assert len(report.sensors.detections) == 5
    assert len(report.transitions) == 11
    assert all(v.valence_valid for v in report.transitions)
    assert states == before
    assert reports == [report]


@pytest.mark.parametrize("field", ["current_context", "egg", "ritual_mode", "path_history", "agent_tongue"])
def test_signatures_bind_complete_hatch_request(setup_gate, request_data, states, signers, field):
    gate, claims, _ = setup_gate
    evidence = signed(gate, request_data, states, signers)
    if field == "egg":
        request_data["egg"]["hatch_condition"]["min_tongues"] = 0
    else:
        request_data[field] = {
            "current_context": [0.1] * 6,
            "ritual_mode": "triadic",
            "path_history": [{"ring": "core"}],
            "agent_tongue": "DR",
        }[field]
    assert gate.evaluate(request_data, evidence).decision == "DENY"
    assert not claims


def test_measurement_tampering_and_incomplete_quorum_fail(setup_gate, request_data, states, signers):
    gate, _, _ = setup_gate
    evidence = signed(gate, request_data, states, signers)
    altered = copy.deepcopy(states)
    altered[-1][6] += 0.1
    assert not gate.evaluate(request_data, replace(evidence, states=altered)).allowed
    assert not gate.evaluate(
        request_data, replace(evidence, signatures=dict(list(evidence.signatures.items())[:2]))
    ).allowed


def test_duplicate_witness_keys_cannot_inflate_quorum(states):
    with pytest.raises(ValueError, match="distinct"):
        NeuralEggGate(
            NeuralGatePolicy("a", states[0], 2), {"a": b"same", "b": b"same", "c": b"same"}, lambda *args: True
        )


@pytest.mark.parametrize("failure", ["stale", "reordered", "nan", "dimension", "saturation", "empty"])
def test_invalid_measurements_do_not_reach_verifier(states, request_data, failure):
    policy = NeuralGatePolicy("a", states[0], 2, min_witnesses=1)
    verifier = Mock(side_effect=AssertionError("must not verify malformed evidence"))
    gate = NeuralEggGate(policy, {"a": b"key"}, Mock(), verify_signature=verifier, clock=lambda: 100)
    evidence = NeuralEvidence("test-challenge-0123456789", 100, states, tuple(range(88, 100)))
    if failure == "stale":
        evidence = replace(evidence, timestamps=tuple(range(12)))
    elif failure == "reordered":
        evidence = replace(evidence, timestamps=tuple(reversed(evidence.timestamps)))
    elif failure == "empty":
        evidence = replace(evidence, states=())
    else:
        states[0] = {"nan": [math.nan] * 21, "dimension": [0.0] * 20, "saturation": [100.0] * 21}[failure]
        evidence = replace(evidence, states=states)
    assert not gate.evaluate(request_data, evidence).allowed
    verifier.assert_not_called()


def test_replay_and_policy_substitution_fail(setup_gate, request_data, states, signers):
    gate, _, _ = setup_gate
    evidence = signed(gate, request_data, states, signers)
    assert gate.evaluate(request_data, evidence).allowed
    assert gate.evaluate(request_data, evidence).reasons == ("replayed_or_unknown_challenge",)
    other = NeuralEggGate(
        replace(gate.policy, audience="another-session"),
        {k: s.public_key for k, s in signers.items()},
        lambda *args: True,
        clock=lambda: 100,
    )
    assert other.evaluate(request_data, evidence).reasons == ("witness_quorum",)


def test_opposing_channel_signs_are_not_cancelled(setup_gate, request_data, states, signers):
    gate, _, _ = setup_gate
    for i, state in enumerate(states):
        state[6] = state[7] = 0.02 * i
        state[0] = state[17] = 0.5 - 0.02 * i
    report = gate.evaluate(request_data, signed(gate, request_data, states, signers))
    assert not report.allowed
    assert "valence:channel_imbalance" in report.reasons
    assert report.transitions[-1].micro_census.total_charge == 0
    assert report.transitions[-1].micro_census.charge_imbalance == 1


def test_static_window_is_not_authorization(setup_gate, request_data, states, signers):
    gate, _, _ = setup_gate
    report = gate.evaluate(request_data, signed(gate, request_data, [states[0]] * 12, signers))
    assert not report.allowed
    assert "valence:static" in report.reasons
    assert "sensor:six_tonic" in report.reasons


def test_default_verifier_never_falls_back_to_demo(monkeypatch, setup_gate, request_data, states, signers):
    import crypto.pqc_liboqs as pqc

    gate, _, _ = setup_gate
    evidence = signed(gate, request_data, states, signers)
    monkeypatch.setattr(pqc, "LIBOQS_AVAILABLE", False)
    monkeypatch.setattr(pqc, "PURE_PQC_AVAILABLE", False)
    monkeypatch.setenv("SCBE_ALLOW_INSECURE_PQC", "1")
    assert gate.evaluate(request_data, evidence).decision == "DENY"


def test_gate_runs_before_any_geoseal_decryption(monkeypatch, setup_gate, request_data, states, signers):
    gate, _, reports = setup_gate
    # GeoSeal is an explicit test double: tests integration order, not encryption.
    # Gate witnesses above use real ML-DSA.
    toolkit = SimpleNamespace(
        ConcentricRingPolicy=lambda: SimpleNamespace(classify=lambda r: {"ring": "core"}),
        project_to_cube=lambda *a, **k: [0.0] * 6,
        project_to_sphere=lambda *a: [0.0] * 3,
        healpix_id=lambda *a: 0,
        morton_id=lambda *a: 0,
        potentials=lambda *a: (0, 0),
        classify=lambda *a: "interior",
        geoseal_decrypt=Mock(return_value=(True, b"payload")),
    )
    monkeypatch.setattr(eggs, "_cli_toolkit", lambda: toolkit)
    xt = SimpleNamespace(tok=SimpleNamespace(encode_bytes=lambda tongue, data: list(data)))
    integrator = eggs.SacredEggIntegrator(xt, neural_gate=gate)
    egg = eggs.SacredEgg(**request_data["egg"])
    egg.yolk_ct["attest"] = {}
    request_data = eggs.neural_hatch_request(egg, [0.0] * 6, "KO")
    rejected = integrator.hatch_egg(egg, [0.0] * 6, "KO", "secret", "public")
    assert not rejected.success and rejected.reason == "sealed"
    toolkit.geoseal_decrypt.assert_not_called()
    evidence = signed(gate, request_data, states, signers)
    allowed = integrator.hatch_egg(egg, [0.0] * 6, "KO", "secret", "public", neural_evidence=evidence)
    assert allowed.success
    assert len(rejected.tokens) == len(allowed.tokens)
    assert len(reports) == 2
    assert toolkit.geoseal_decrypt.call_count == 1


def test_distance_bound_uses_receiver_computed_metric(setup_gate, request_data, states, signers):
    original, _, _ = setup_gate
    policy = replace(original.policy, max_hyperbolic_distance=0.01)
    gate = NeuralEggGate(policy, {k: s.public_key for k, s in signers.items()}, lambda *args: True, clock=lambda: 100)
    report = gate.evaluate(request_data, signed(gate, request_data, states, signers))
    assert report.decision == "QUARANTINE"
    assert report.max_distance > 0.01
    assert "reference_distance" in report.reasons


def test_single_sensor_flag_cannot_be_averaged_away(monkeypatch, setup_gate, request_data, states, signers):
    from symphonic_cipher.scbe_aethermoore.ai_brain import egg_governance as gate_module
    from symphonic_cipher.scbe_aethermoore.ai_brain.detection import CombinedAssessment, DetectionResult

    gate, _, _ = setup_gate
    assessment = CombinedAssessment(
        [DetectionResult("phase_distance", 0.7, True, ["wrong_tongue"])],
        combined_score=0.476,
        decision="ALLOW",
        any_flagged=True,
        flag_count=1,
    )
    monkeypatch.setattr(gate_module, "run_combined_detection", lambda *args: assessment)
    report = gate.evaluate(request_data, signed(gate, request_data, states, signers))
    assert report.decision == "QUARANTINE"
    assert "sensor:phase_distance" in report.reasons


def test_replay_store_failure_denies_before_sensor_work(monkeypatch, setup_gate, request_data, states, signers):
    from symphonic_cipher.scbe_aethermoore.ai_brain import egg_governance as gate_module

    original, _, _ = setup_gate
    gate = NeuralEggGate(
        original.policy,
        {k: s.public_key for k, s in signers.items()},
        Mock(side_effect=ConnectionError("replay store unavailable")),
        clock=lambda: 100,
    )
    sensor = Mock()
    monkeypatch.setattr(gate_module, "run_combined_detection", sensor)
    report = gate.evaluate(request_data, signed(gate, request_data, states, signers))
    assert report.decision == "DENY"
    sensor.assert_not_called()
