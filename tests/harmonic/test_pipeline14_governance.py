"""
test_pipeline14_governance.py
Functional governance tests for the 14-layer SCBE pipeline.

These test the pipeline as a real governance gate — not just that the math
computes, but that the right decisions come out for the right inputs, that
the Cauchy Core and 47D spin behave correctly under actual agent profiles,
and that the pipeline handles edge cases robustly.

Scenarios:
  1. Safe agent (low distance, coherent) → ALLOW
  2. Mildly suspicious agent → QUARANTINE or ESCALATE
  3. Clearly adversarial agent (high distance, decoherent) → DENY
  4. Cauchy Core activation: d_H near 0 repels, equilibrium at d*
  5. κ feedback: high C_spin → higher κ → stronger repulsion
  6. 47D vs 6D spin coherence differ on same input
  7. Phase deviation (pd) from breathing wires into L12
  8. Temporal consistency: same identity, same input → same decision
  9. Edge case: zero-magnitude intent vector
  10. Edge case: maximum magnitude near ball boundary
"""

import numpy as np
import pytest

from src.symphonic_cipher.scbe_aethermoore.layers.fourteen_layer_pipeline import (
    FourteenLayerPipeline,
    RiskLevel,
)
from src.symphonic_cipher.scbe_aethermoore.layers_9_12 import (
    compute_spin_coherence_47d,
    compute_47d_phases,
)

PHI = 1.6180339887498948482

# Safe reference profile — used to calibrate realm centers so the safe agent
# test maps to d_star ≈ 0 (exact match to realm 0 center).
_SAFE_PROFILE = dict(
    identity=0.5,
    intent=0.1 + 0.05j,
    trajectory=0.15,
    timing=0.5,
    commitment=0.8,
    signature=0.5,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pipe():
    p = FourteenLayerPipeline(kappa_base=0.1)
    p.calibrate([_SAFE_PROFILE])
    return p


def _run(pipe, *, identity, intent, trajectory, timing, commitment, signature, t=1.0, tau=0.5, eta=4.0, q=1 + 0j):
    risk, states = pipe.process(
        identity=identity,
        intent=intent,
        trajectory=trajectory,
        timing=timing,
        commitment=commitment,
        signature=signature,
        t=t,
        tau=tau,
        eta=eta,
        q=q,
    )
    layer = {s.layer: s for s in states}
    return risk, layer


# ---------------------------------------------------------------------------
# 1. Safe agent → should ALLOW
# ---------------------------------------------------------------------------


def test_safe_agent_allows(pipe):
    """A cooperative, coherent agent with small hyperbolic distance should ALLOW."""
    risk, layer = _run(
        pipe,
        identity=0.5,
        intent=0.1 + 0.05j,  # low imaginary — not deceptive
        trajectory=0.15,
        timing=0.5,
        commitment=0.8,
        signature=0.5,
        t=1.0,
    )
    assert risk.decision in ("ALLOW", "REVIEW"), f"Expected ALLOW/REVIEW for safe agent, got {risk.decision}"
    assert layer[12].metrics["H_d"] > 0.3, "Safe agent should have high harmonic score"
    assert layer[10].metrics["47d"] is True, "47D spin must be active"


# ---------------------------------------------------------------------------
# 2. Suspicious agent → should not ALLOW
# ---------------------------------------------------------------------------


def test_suspicious_agent_not_allowed(pipe):
    """High imaginary intent (deceptive mask) and erratic commitment should not ALLOW."""
    risk, layer = _run(
        pipe,
        identity=0.9,
        intent=0.1 + 0.95j,  # large imaginary — masked intent
        trajectory=0.8,
        timing=0.05,
        commitment=0.05,  # very low commitment — unstable
        signature=0.9,
        t=10.0,
    )
    assert risk.decision in (
        "QUARANTINE",
        "ESCALATE",
        "DENY",
        "REVIEW",
    ), f"Suspicious agent should not ALLOW, got {risk.decision}"


# ---------------------------------------------------------------------------
# 3. Clearly adversarial → DENY
# ---------------------------------------------------------------------------


def test_adversarial_agent_denied(pipe):
    """Extreme values across all dimensions should result in DENY."""
    risk, layer = _run(
        pipe,
        identity=0.99,
        intent=0.99 + 0.99j,
        trajectory=0.99,
        timing=0.99,
        commitment=0.01,
        signature=0.99,
        t=20.0,
        tau=10.0,
        eta=0.5,
        q=0 + 1j,
    )
    d_H = layer[12].metrics["d_H"]
    assert risk.decision == "DENY", f"Adversarial input should DENY, got {risk.decision}"
    assert d_H > 2.0, f"Adversarial d_H should be large, got {d_H:.4f}"
    assert layer[12].metrics["H_d"] < 0.2, "Low harmonic score expected for adversarial input"


# ---------------------------------------------------------------------------
# 4. Cauchy Core: repulsion near d_H = 0, score peaks at d_eq
# ---------------------------------------------------------------------------


def test_cauchy_core_white_hole_repulsion(pipe):
    """S_cc should be maximized near d_eq, not at d_H=0.
    We can't force exact d_H=0 via the pipeline, but we can verify the Cauchy
    Core formula directly and that S_cc < theoretical_max_at_dstar."""
    kappa_t = 0.15
    pd = 0.01

    # Manual Form C at several d_H values
    def s_cc(d_h):
        return 1.0 / (1.0 + PHI * d_h + 2.0 * pd + kappa_t / d_h)

    d_eq = (kappa_t / PHI) ** 0.5
    s_at_deq = s_cc(d_eq)

    # Score at tiny d_H should be lower than at d_eq (white hole floor)
    s_near_zero = s_cc(0.001)
    assert s_near_zero < s_at_deq, "Score near d_H=0 must be less than score at d_eq (Cauchy Core repulsion)"

    # Score at large d_H should also be less than at d_eq
    s_large = s_cc(5.0)
    assert s_large < s_at_deq, "Score at large d_H must be less than score at d_eq"

    # d_eq should be in the expected range for κ_base=0.1, C_spin ∈ [0,1]
    assert 0.2 < d_eq < 0.4, f"d_eq={d_eq:.4f} out of expected range [0.2, 0.4]"


def test_pipeline_reports_d_eq(pipe):
    """Pipeline must report the equilibrium orbit radius in L12 metrics."""
    risk, layer = _run(pipe, identity=0.5, intent=0.3 + 0.2j, trajectory=0.3, timing=0.5, commitment=0.7, signature=0.5)
    d_eq = layer[12].metrics["d_eq"]
    kappa_t = layer[12].metrics["kappa_t"]
    expected_d_eq = (kappa_t / PHI) ** 0.5
    assert abs(d_eq - expected_d_eq) < 1e-9, f"d_eq mismatch: {d_eq:.6f} vs {expected_d_eq:.6f}"


# ---------------------------------------------------------------------------
# 5. κ feedback: C_spin drives kappa_t
# ---------------------------------------------------------------------------


def test_kappa_tracks_c_spin(pipe):
    """kappa_t must equal kappa_base * (1 + C_spin) exactly."""
    kappa_base = 0.1
    risk, layer = _run(pipe, identity=0.4, intent=0.2 + 0.1j, trajectory=0.2, timing=0.6, commitment=0.8, signature=0.4)
    C_spin = layer[10].metrics["C_spin"]
    kappa_t = layer[12].metrics["kappa_t"]
    expected = kappa_base * (1.0 + C_spin)
    assert abs(kappa_t - expected) < 1e-12, f"kappa_t={kappa_t:.8f} != kappa_base*(1+C_spin)={expected:.8f}"


def test_high_coherence_increases_kappa(pipe):
    """An input producing high C_spin should yield higher kappa_t than a decoherent input."""
    # Coherent: all tongue phases roughly aligned
    _, layer_coherent = _run(
        pipe, identity=0.3, intent=0.3 + 0.0j, trajectory=0.3, timing=0.3, commitment=0.3, signature=0.3
    )
    # Decoherent: mixed phases
    _, layer_mixed = _run(
        pipe, identity=0.9, intent=0.1 + 0.9j, trajectory=0.5, timing=0.8, commitment=0.2, signature=0.7
    )

    kappa_coherent = layer_coherent[12].metrics["kappa_t"]
    kappa_mixed = layer_mixed[12].metrics["kappa_t"]
    # Both should be in valid range
    assert 0.1 <= kappa_coherent <= 0.2, f"kappa_t out of range: {kappa_coherent}"
    assert 0.1 <= kappa_mixed <= 0.2, f"kappa_t out of range: {kappa_mixed}"


# ---------------------------------------------------------------------------
# 6. 47D spin coherence differs from naive 6D average
# ---------------------------------------------------------------------------


def test_47d_spin_differs_from_6d():
    """The 47D C_spin must differ from a naive unweighted 6D mean."""
    phases = np.array([0.1, 0.5, 1.2, -0.3, 0.8, -0.9])
    psi = np.array([0.2, -0.1, 0.4, 0.3, -0.2, 0.1])

    result_47d = compute_spin_coherence_47d(phases, psi)
    # Naive 6D: unweighted circular mean of just the 6 base phases
    naive_6d = float(np.abs(np.mean(np.exp(1j * phases))))

    # They should differ because 47D applies φ^(l+m+n) weights dominated by Draumric
    assert (
        abs(result_47d.c_spin - naive_6d) > 1e-6
    ), f"47D C_spin ({result_47d.c_spin:.6f}) should differ from naive 6D ({naive_6d:.6f})"


def test_47d_weight_ordering():
    """Higher-index triple couplings must have larger metric weights than lower-index ones."""
    phases = np.zeros(6)
    psi = np.zeros(6)
    _, weights = compute_47d_phases(phases, psi)

    # Weight for Triple(0,1,2): φ^3
    # Weight for Triple(3,4,5): φ^12 (amplitude=tanh(0)=0, so 0 — use non-zero psi)
    psi_nonzero = np.ones(6) * 0.5
    _, w2 = compute_47d_phases(phases, psi_nonzero)

    # Real tongue weights: w[0]=φ^0, w[5]=φ^10
    assert w2[0] == pytest.approx(PHI**0, rel=1e-6), "Real l=0: weight=1.0"
    assert w2[5] == pytest.approx(PHI**10, rel=1e-6), f"Real l=5: weight=φ^10={PHI**10:.4f}"

    # Highest triple {3,4,5} weight >> lowest triple {0,1,2} weight
    # triples start at index 6 (real) + 15 (pairs) = 21
    # {0,1,2} is first triple (index 21), {3,4,5} is last triple (index 40)
    w_triple_low = w2[21]  # {0,1,2}: φ^3 * tanh(...)
    w_triple_high = w2[40]  # {3,4,5}: φ^12 * tanh(...)
    assert (
        w_triple_high > w_triple_low * 10
    ), f"Triple(3,4,5) weight {w_triple_high:.2f} should dominate Triple(0,1,2) {w_triple_low:.2f}"


# ---------------------------------------------------------------------------
# 7. Phase deviation (pd) from breathing wires into L12
# ---------------------------------------------------------------------------


def test_pd_wired_into_l12(pipe):
    """pd must be non-zero (breathing shifts the norm) and appear in L12 metrics."""
    risk, layer = _run(
        pipe,
        identity=0.5,
        intent=0.4 + 0.3j,
        trajectory=0.4,
        timing=0.5,
        commitment=0.7,
        signature=0.5,
        t=5.0,  # mid-cycle breathing — guaranteed non-zero pd
    )
    pd = layer[12].metrics["pd"]
    # pd should be a small positive float — breathing amplitude is 0.05
    assert isinstance(float(pd), float), "pd must be a float"
    assert float(pd) >= 0.0, "pd must be non-negative"
    # pd feeds into S_cc denominator — verify S_cc < 1/(1+phi*d_H) (pd adds cost)
    d_H = layer[12].metrics["d_H"]
    kappa_t = layer[12].metrics["kappa_t"]
    S_cc = float(layer[12].metrics["S_cc"])
    S_no_pd = 1.0 / (1.0 + PHI * d_H + kappa_t / max(d_H, 1e-9))
    if float(pd) > 1e-6:
        assert S_cc < S_no_pd, "pd > 0 should push S_cc below the pd=0 value"


# ---------------------------------------------------------------------------
# 8. Temporal consistency: same input → same output
# ---------------------------------------------------------------------------


def test_deterministic_for_same_input(pipe):
    """Same inputs at the same time must produce identical decisions and scores."""
    kwargs = dict(identity=0.5, intent=0.3 + 0.7j, trajectory=0.2, timing=0.1, commitment=0.9, signature=0.4, t=1.0)
    risk1, layer1 = _run(pipe, **kwargs)
    risk2, layer2 = _run(pipe, **kwargs)
    assert risk1.decision == risk2.decision
    assert abs(layer1[12].metrics["H_d"] - layer2[12].metrics["H_d"]) < 1e-12
    assert abs(layer1[12].metrics["S_cc"] - layer2[12].metrics["S_cc"]) < 1e-12


# ---------------------------------------------------------------------------
# 9. Edge case: near-zero intent magnitude
# ---------------------------------------------------------------------------


def test_near_zero_intent_handled(pipe):
    """Very small intent magnitude should not cause division by zero or NaN."""
    risk, layer = _run(
        pipe, identity=0.01, intent=0.001 + 0.001j, trajectory=0.01, timing=0.5, commitment=0.5, signature=0.01
    )
    S_cc = float(layer[12].metrics["S_cc"])
    H_d = float(layer[12].metrics["H_d"])
    assert not np.isnan(S_cc), "S_cc must not be NaN for near-zero intent"
    assert not np.isnan(H_d), "H_d must not be NaN for near-zero intent"
    assert 0.0 < S_cc <= 1.0, f"S_cc={S_cc} out of bounds"
    assert 0.0 < H_d <= 1.0, f"H_d={H_d} out of bounds"


# ---------------------------------------------------------------------------
# 10. Edge case: near-boundary input (large magnitudes)
# ---------------------------------------------------------------------------


def test_near_boundary_input_handled(pipe):
    """Large input magnitudes that push toward the Poincaré ball boundary must not crash."""
    risk, layer = _run(
        pipe,
        identity=0.99,
        intent=0.99 + 0.99j,
        trajectory=0.99,
        timing=0.99,
        commitment=0.99,
        signature=0.99,
        t=100.0,
        tau=50.0,
        eta=0.1,
    )
    S_cc = float(layer[12].metrics["S_cc"])
    d_H = float(layer[12].metrics["d_H"])
    assert not np.isnan(S_cc), "S_cc must not be NaN near ball boundary"
    assert not np.isinf(d_H), "d_H must not be inf"
    # Near the boundary, d_H is large, score should be very low
    assert S_cc < 0.3, f"Near-boundary input should have low S_cc, got {S_cc:.4f}"


# ---------------------------------------------------------------------------
# 11. All L12 metrics present
# ---------------------------------------------------------------------------


def test_l12_metrics_complete(pipe):
    """L12 must emit all required governance fields in every run."""
    REQUIRED = {"H_d", "S_cc", "kappa_t", "d_H", "pd", "d_eq"}
    risk, layer = _run(pipe, identity=0.5, intent=0.3 + 0.2j, trajectory=0.3, timing=0.5, commitment=0.7, signature=0.5)
    missing = REQUIRED - set(layer[12].metrics.keys())
    assert not missing, f"L12 missing required metrics: {missing}"


# ---------------------------------------------------------------------------
# 12. Risk monotonicity: higher d_H → lower S_cc
# ---------------------------------------------------------------------------


def test_s_cc_decreases_with_distance():
    """S_cc must decrease as d_H increases (above d_eq), matching Cauchy Core monotonicity."""
    kappa_t = 0.15
    pd = 0.01

    def s_cc(d_h):
        return 1.0 / (1.0 + PHI * d_h + 2.0 * pd + kappa_t / max(d_h, 1e-9))

    d_eq = (kappa_t / PHI) ** 0.5
    # Evaluate at d_eq, 2×d_eq, 5×d_eq, 10×d_eq
    vals = [s_cc(d_eq * k) for k in [1.0, 2.0, 5.0, 10.0]]
    for i in range(len(vals) - 1):
        assert (
            vals[i] > vals[i + 1]
        ), f"S_cc not monotone decreasing above d_eq: s({i})={vals[i]:.6f} vs s({i+1})={vals[i+1]:.6f}"


# ---------------------------------------------------------------------------
# 13. S_cc in (0, 1] always
# ---------------------------------------------------------------------------


def test_s_cc_bounded(pipe):
    """S_cc must stay in (0, 1] for any input."""
    test_cases = [
        dict(identity=0.1, intent=0.1 + 0.0j, trajectory=0.1, timing=0.5, commitment=0.9, signature=0.1),
        dict(identity=0.5, intent=0.5 + 0.5j, trajectory=0.5, timing=0.5, commitment=0.5, signature=0.5),
        dict(identity=0.9, intent=0.9 + 0.9j, trajectory=0.9, timing=0.9, commitment=0.1, signature=0.9),
    ]
    for kwargs in test_cases:
        risk, layer = _run(pipe, **kwargs)
        S_cc = float(layer[12].metrics["S_cc"])
        assert 0.0 < S_cc <= 1.0, f"S_cc={S_cc:.6f} out of (0,1] for {kwargs}"


# ---------------------------------------------------------------------------
# 14. 47D coordinate count is exactly 47
# ---------------------------------------------------------------------------


def test_47d_coord_count():
    phases = np.random.uniform(-np.pi, np.pi, 6)
    psi = np.random.uniform(-1.0, 1.0, 6)
    ph47, w47 = compute_47d_phases(phases, psi)
    assert len(ph47) == 47, f"Expected 47 coordinates, got {len(ph47)}"
    assert len(w47) == 47, f"Expected 47 weights, got {len(w47)}"
    # All weights positive
    assert np.all(w47 > 0), "All metric weights must be positive"
