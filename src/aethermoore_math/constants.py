"""
AETHERMOORE Constants
=====================
Fundamental constants derived from physics and mathematics.
"""

import numpy as np

# ==============================================================================
# COX CONSTANT
# ==============================================================================
# Solution to transcendental equation: c = e^(π/c)
# This is the TAHS harmonic equilibrium point.
# Computed via Newton-Raphson to machine precision.

def _compute_cox_constant(tolerance: float = 1e-15, max_iter: int = 100) -> float:
    """Compute Cox constant via Newton-Raphson."""
    c = 3.0  # Initial guess
    for _ in range(max_iter):
        exp_term = np.exp(np.pi / c)
        f_c = c - exp_term
        f_prime = 1 + (np.pi / c**2) * exp_term
        c_new = c - f_c / f_prime
        if abs(c_new - c) < tolerance:
            return c_new
        c = c_new
    return c

COX_CONSTANT = _compute_cox_constant()  # ≈ 2.9260636404...

# ==============================================================================
# MARS FREQUENCY
# ==============================================================================
# Derived from Mars orbital period, octave-shifted to audible range.
# Provides grid-decoupled timing (not harmonic with 50/60 Hz).

MARS_ORBITAL_PERIOD_DAYS = 686.98
MARS_ORBITAL_PERIOD_SECONDS = MARS_ORBITAL_PERIOD_DAYS * 86400
MARS_OCTAVE = 33  # Shift to audible range

MARS_FREQUENCY_HZ = (1.0 / MARS_ORBITAL_PERIOD_SECONDS) * (2 ** MARS_OCTAVE)  # ≈ 144.72 Hz
MARS_TICK_MS = 1000.0 / MARS_FREQUENCY_HZ  # ≈ 6.91 ms per tick

# ==============================================================================
# Q16.16 FIXED-POINT
# ==============================================================================
# 16 bits integer + 16 bits fraction = deterministic math across platforms

Q16_16_SCALE = 2**16  # 65536

# ==============================================================================
# SWARM TIMING
# ==============================================================================
# Byzantine fault tolerance requires f < n/3 and 3 message rounds

BYZANTINE_ROUNDS = 3  # Minimum rounds for BFT consensus
MAX_NETWORK_LATENCY_MS = 50  # Worst-case propagation delay
