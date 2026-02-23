import math

import numpy as np

from src.crypto.nonbinary_kernel import (
    KernelConfig,
    NonBinarySimplexKernel,
    generate_demo_signals,
)


def test_quaternary_probabilities_sum_to_one():
    k = NonBinarySimplexKernel(KernelConfig(k=4))
    step = k.step(v_t=0.55, d_t=0.70, i_t=0.30, dt=1.0, p_t=1.0)
    probs = step.StateVector.probs
    assert len(probs) == 4
    assert math.isclose(sum(probs), 1.0, rel_tol=0.0, abs_tol=1e-9)


def test_triadic_probabilities_sum_to_one():
    k = NonBinarySimplexKernel(KernelConfig(k=3))
    step = k.step(v_t=0.35, d_t=0.65, i_t=-0.40, dt=1.0, p_t=1.2)
    probs = step.StateVector.probs
    assert len(probs) == 3
    assert math.isclose(sum(probs), 1.0, rel_tol=0.0, abs_tol=1e-9)


def test_high_exposure_negative_intent_pushes_to_t3():
    k = NonBinarySimplexKernel(KernelConfig(k=4))
    # Build up adverse state.
    for _ in range(12):
        out = k.step(v_t=1.0, d_t=1.0, i_t=-0.9, dt=1.0, p_t=1.4)
    assert out.StateVector.tier == "T3"
    assert out.DecisionRecord.action == "DENY"


def test_positive_intent_can_recover_state():
    k = NonBinarySimplexKernel(KernelConfig(k=4))
    # Adverse phase.
    for _ in range(10):
        k.step(v_t=1.0, d_t=0.9, i_t=-0.8, dt=1.0, p_t=1.2)
    # Recovery phase.
    final = None
    for _ in range(16):
        final = k.step(v_t=0.20, d_t=0.45, i_t=0.9, dt=1.0, p_t=0.7)
    assert final is not None
    assert final.StateVector.tier in {"T1", "T2"}


def test_statevector_and_decisionrecord_contract_present():
    k = NonBinarySimplexKernel(KernelConfig(k=3))
    out = k.step(v_t=0.2, d_t=0.8, i_t=0.2, dt=0.5, p_t=1.0)
    assert out.StateVector is not None
    assert out.DecisionRecord is not None
    assert out.DecisionRecord.signature
    assert out.DecisionRecord.confidence >= 0.0
    assert out.DecisionRecord.confidence <= 1.0


def test_demo_signals_shape():
    sig = generate_demo_signals(steps=128)
    assert set(sig.keys()) == {"v", "d", "i", "p"}
    assert all(len(x) == 128 for x in sig.values())
    assert np.all(sig["v"] >= 0.0)
    assert np.all(sig["v"] <= 1.0)
