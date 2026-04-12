"""Phi-phase oscillator — one variable knob that rotates phi between
its growth phase (phi) and its bound phase (1/phi) via a phase angle theta.

The recurrence:

    x_n = phi^cos(theta_n) * x_{n-1}  -  x_{n-2}

is a parametric oscillator (Mathieu/Chebyshev family). The companion matrix
for x_n = a*x_{n-1} - x_{n-2} has eigenvalues (a +- sqrt(a^2 - 4))/2. With
a = phi^cos(theta) in [1/phi, phi] ~= [0.618, 1.618], a^2 in [0.382, 2.618],
so a^2 - 4 < 0 always -> complex conjugate eigenvalues with |lambda| = 1.

Translation: the system is *exactly* on the stability boundary for every
value of theta. Neutrally stable. Bounded forever, never blows up, never
decays to zero. Phase angle controls the oscillation frequency, not the
amplitude. That is what makes this the right shape for a yin-yang knob:
both phases coexist, neither wins.
"""

import math

PHI = (1 + 5**0.5) / 2


def phi_eff(theta: float) -> float:
    """Phase-modulated phi.

    theta = 0     -> cos = +1  -> phi_eff = phi   ~= 1.618 (growth phase)
    theta = pi/2  -> cos =  0  -> phi_eff = 1.000        (neutral pivot)
    theta = pi    -> cos = -1  -> phi_eff = 1/phi ~= 0.618 (bound phase)
    """
    return PHI ** math.cos(theta)


def step(x_prev: float, x_prev2: float, theta: float) -> float:
    """One yin-yang step. Bounded for every theta."""
    return phi_eff(theta) * x_prev - x_prev2


def run(x0: float, x1: float, theta_fn, n_steps: int):
    """Run the recurrence with theta driven by theta_fn(step_index, history)."""
    history = [x0, x1]
    for i in range(2, n_steps):
        theta = theta_fn(i, history)
        history.append(step(history[-1], history[-2], theta))
    return history


# --- Offset-spin equivalence for progradial allowances --------------------
#
# Six Sacred Tongues, one engine. Each tongue reads the same phi_phase
# oscillator from a different position on the circle, spaced by the
# golden angle (2*pi / phi^2 ~= 137.508 degrees). Golden-angle spacing is
# the unique rotation that guarantees no two tongues ever land on top of
# each other for the longest possible run -- it's why sunflower seeds
# pack without overlap. Each tongue gets maximum forward-rotation
# allowance (progradial room) while staying mathematically equivalent
# to every other tongue: same eigenvalue, same amplitude, same engine,
# only the phase position differs.

GOLDEN_ANGLE = 2 * math.pi / (PHI**2)  # ~= 2.3998 rad ~= 137.508 deg

TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")  # Kor'aelin..Draumric


def tongue_offset(tongue_index: int) -> float:
    """Phase offset for tongue l, spaced by the golden angle."""
    return (tongue_index * GOLDEN_ANGLE) % (2 * math.pi)


def tongue_theta(base_theta: float, tongue_index: int) -> float:
    """Compose the base theta with the tongue's golden-angle offset."""
    return (base_theta + tongue_offset(tongue_index)) % (2 * math.pi)


def run_six_tongues(x0: float, x1: float, base_theta_fn, n_steps: int):
    """Run six parallel phi_phase oscillators, one per Sacred Tongue.

    All six share the same engine and the same base driver; they only
    differ in their golden-angle phase offset. Returns a dict of
    {tongue_name: history}.
    """
    out = {t: [x0, x1] for t in TONGUES}
    for i in range(2, n_steps):
        base = base_theta_fn(i, out)
        for l, tongue in enumerate(TONGUES):
            theta_l = tongue_theta(base, l)
            hist = out[tongue]
            hist.append(step(hist[-1], hist[-2], theta_l))
    return out
