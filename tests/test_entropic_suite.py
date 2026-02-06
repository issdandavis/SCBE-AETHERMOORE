# pytest: tests/test_entropic_suite.py
"""
@file: test_entropic_suite.py
@module: tests/entropic
@layer: Layer 12
@component: Entropic Escape Velocity CI Suite
@version: 3.2.4

Lightweight CI-friendly test suite for the entropic escape velocity inequality.

Tests:
1. Parameter sweep against inequality gate: k > 2C/sqrt(N0)
2. Numeric stability across orders of magnitude (N0 = 1e2..1e16)
3. Discrete-time Euler simulation confirming threshold behavior

All 4 CI robustness fixes applied:
- Headless matplotlib backend (Agg)
- Artifact path relative to __file__, not os.getcwd()
- Euler integrator (tests actual discretization, not analytical identity)
- Floating-point tolerance (>= 0 instead of > 0 near boundaries)
"""

import os
import math
import numpy as np
import pytest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ART_DIR = os.path.join(os.path.dirname(__file__), "test_artifacts")
os.makedirs(ART_DIR, exist_ok=True)


def escape_condition(k, C, N0):
    """
    Entropic escape velocity gate.

    Returns True if expansion rate k exceeds the threshold 2C/sqrt(N0),
    meaning the keyspace grows faster than search can explore it.
    """
    return k > (2.0 * C) / math.sqrt(N0)


def simulate_discrete_euler(N0, k, dt, steps):
    """
    Euler-method discrete growth: N_{t+1} = N_t * (1 + k*dt).

    Uses Euler instead of exact exp(k*dt) so that the log-slope is not
    analytically constant -- this makes the dW/dt check meaningful as a
    test of discretization behavior.
    """
    N = np.empty(steps + 1, dtype=float)
    N[0] = N0
    for i in range(steps):
        N[i + 1] = N[i] * (1.0 + k * dt)
    return N


# =============================================================================
# TEST 1: Parameter Sweep Against Inequality Gate
# =============================================================================


@pytest.mark.parametrize("N0,C,k,expect_escape", [
    (1e4, 0.5, 0.0029, False),   # below: threshold = 2*0.5/sqrt(1e4) = 0.01
    (1e4, 0.5, 0.0100, False),   # at threshold: strict > means NOT escaped
    (1e4, 0.5, 0.0200, True),    # above threshold
])
def test_entropic_escape_param_sweep(N0, C, k, expect_escape):
    """Sweep k below/at/above the escape velocity threshold."""
    assert escape_condition(k, C, N0) == expect_escape


# =============================================================================
# TEST 2: Numeric Stability Across Orders of Magnitude
# =============================================================================


@pytest.mark.parametrize("N0", [1e2, 1e4, 1e8, 1e16])
def test_numeric_stability_across_N0(N0):
    """
    Verify finite values, monotonicity, and well-conditioned log-space
    across 14 orders of magnitude for N0.
    """
    C = 0.5
    k = (2 * C) / math.sqrt(N0) * 1.5  # deliberately above threshold
    t = np.linspace(0.0, 10.0, 200)
    N = N0 * np.exp(k * t)

    # Finite values
    assert np.isfinite(N).all(), "Non-finite values in N(t)"

    # Monotonicity with floating-point tolerance (>= 0, not > 0)
    assert np.all(np.diff(N) >= 0), "N(t) should be non-decreasing when k > 0"
    assert N[-1] > N[0], "N(t) must grow over the interval"

    # Well-conditioned log space
    W = np.log(N)
    assert np.isfinite(W).all(), "Non-finite values in log N(t)"

    # dW/dt should be approximately k
    dW = np.gradient(W, t)
    assert np.allclose(dW, k, rtol=1e-3, atol=1e-6), "dW/dt should be ~k"

    # Save CI artifact plot
    fig = plt.figure()
    plt.title(f"Numeric Stability N0={N0:g}")
    plt.xlabel("t")
    plt.ylabel("N(t)")
    plt.plot(t, N)
    fn = os.path.join(ART_DIR, f"stability_N0_{int(math.log10(N0))}dex.png")
    plt.savefig(fn, dpi=120, bbox_inches="tight")
    plt.close(fig)


# =============================================================================
# TEST 3: Discrete-Time Euler Simulation Confirms Threshold Behavior
# =============================================================================


def test_discrete_time_simulation_confirms_threshold_behavior():
    """
    Run Euler-discretized growth above and below the escape threshold.

    With Euler (not exact exp), mean dW/dt = log(1+k*dt)/dt, not exactly k.
    This makes the threshold check a genuine test of discretization behavior.
    """
    N0 = 1e6
    C = 0.25
    thresh = (2 * C) / math.sqrt(N0)

    k_above = thresh * 1.2
    k_below = thresh * 0.8
    dt = 0.1
    steps = 400

    N_above = simulate_discrete_euler(N0, k_above, dt, steps)
    N_below = simulate_discrete_euler(N0, k_below, dt, steps)

    W_above = np.log(N_above)
    W_below = np.log(N_below)

    dWdt_above = np.diff(W_above) / dt
    dWdt_below = np.diff(W_below) / dt

    # Finite values
    assert np.isfinite(dWdt_above).all() and np.isfinite(dWdt_below).all()

    # With Euler, mean dW/dt is near log(1+k*dt)/dt, not exactly k
    assert np.mean(dWdt_above) > thresh, "Above-threshold run should exceed gate"
    assert np.mean(dWdt_below) < thresh, "Below-threshold run should not exceed gate"

    # Save CI artifact plot
    t = np.arange(steps + 1) * dt
    fig = plt.figure(figsize=(8, 6))
    plt.subplot(2, 1, 1)
    plt.plot(t, N_above, label=f"k_above={k_above:.4g}")
    plt.plot(t, N_below, label=f"k_below={k_below:.4g}")
    plt.ylabel("N(t)")
    plt.legend()

    plt.subplot(2, 1, 2)
    tm = t[1:]
    plt.plot(tm, dWdt_above, label="dW/dt (above)")
    plt.plot(tm, dWdt_below, label="dW/dt (below)")
    plt.axhline(thresh, linestyle="--", label="threshold 2C/\u221aN0")
    plt.xlabel("t")
    plt.ylabel("dW/dt")
    plt.legend()

    fn = os.path.join(ART_DIR, "discrete_sim_thresholds.png")
    plt.savefig(fn, dpi=120, bbox_inches="tight")
    plt.close(fig)
