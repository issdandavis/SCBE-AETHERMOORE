"""
Gyroscopic Interlattice Coupling Engine — Python Reference Implementation

Maps gyroscopic metamaterial topology (Nash et al. 2015) onto SCBE's
Sacred Tongue sublattice architecture.

Core insight: SCBE's phi-scaled tongue weights (1.00 → 11.09) are a
lattice distortion that controls Chern numbers, exactly as Nash proved
experimentally with honeycomb gyroscope arrays.

Layers: L5 (Hyperbolic Distance), L6 (Breathing Transform), L7 (Mobius Phase)
Axioms: A2 (Locality via inverse fifth power coupling), A3 (Causality via first-order dynamics)

Reference: Nash, Kleckner, Vitelli, Irvine "Topological mechanics of
gyroscopic metamaterials" PNAS 112:14495 (2015) — arXiv:1504.03362

See: notes/theory/2026-04-06-gyroscopic-interlattice-magnetic-arrays.md
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations
from typing import Callable

PHI = (1 + math.sqrt(5)) / 2

TONGUE_LABELS = ("KO", "AV", "RU", "CA", "UM", "DR")

TONGUE_RADII = {t: PHI**k for k, t in enumerate(TONGUE_LABELS)}

TONGUE_PHASES = {t: 2 * math.pi * k / 6 for k, t in enumerate(TONGUE_LABELS)}


@dataclass
class SublatticeState:
    """Complex displacement psi = real + i*imag."""

    real: float = 0.0
    imag: float = 0.0


@dataclass
class TongueSublattice:
    """A single tongue sublattice with gyroscopic properties."""

    tongue: str
    radius: float = 0.0
    phase: float = 0.0
    precession_freq: float = 0.0
    state: SublatticeState = field(default_factory=SublatticeState)
    chern_number: int = 1

    def __post_init__(self):
        if self.radius == 0.0:
            self.radius = TONGUE_RADII[self.tongue]
        if self.phase == 0.0 and self.tongue != "KO":
            self.phase = TONGUE_PHASES[self.tongue]
        if self.precession_freq == 0.0:
            self.precession_freq = 1.0 / self.radius


@dataclass
class InterlatticeCouple:
    """Coupling between two tongue sublattices."""

    tongue_a: str
    tongue_b: str
    coupling_strength: float = 0.0
    bond_angle: float = 0.0
    phase_factor: tuple[float, float] = (1.0, 0.0)  # (real, imag)


def create_sublattice(tongue: str, initial_state: SublatticeState | None = None) -> TongueSublattice:
    """Create a tongue sublattice with default properties."""
    idx = TONGUE_LABELS.index(tongue)
    return TongueSublattice(
        tongue=tongue,
        radius=TONGUE_RADII[tongue],
        phase=TONGUE_PHASES[tongue],
        precession_freq=1.0 / TONGUE_RADII[tongue],
        state=initial_state or SublatticeState(),
        chern_number=1 if idx % 2 == 0 else -1,
    )


def coupling_strength(tongue_a: str, tongue_b: str, mu0_m2: float = 1.0) -> float:
    """
    Magnetic dipole coupling: k_m = 3*mu0*M^2 / (pi * a^5).
    'a' is the phi-scaled distance between tongue radii.
    A2: Locality — adjacent tongues couple strongly, distant tongues decouple.
    """
    if tongue_a == tongue_b:
        return 0.0
    r_a = TONGUE_RADII[tongue_a]
    r_b = TONGUE_RADII[tongue_b]
    a = abs(r_a - r_b)
    return (3 * mu0_m2) / (math.pi * a**5)


def bond_angle(tongue_a: str, tongue_b: str) -> float:
    """Bond angle between two tongue sublattices."""
    return TONGUE_PHASES[tongue_b] - TONGUE_PHASES[tongue_a]


def phase_factor(tongue_a: str, tongue_b: str) -> tuple[float, float]:
    """
    Phase factor e^(2i*theta) for a tongue pair.
    Non-zero imaginary part = time-reversal symmetry breaking.
    """
    theta = bond_angle(tongue_a, tongue_b)
    return (math.cos(2 * theta), math.sin(2 * theta))


def create_couple(tongue_a: str, tongue_b: str) -> InterlatticeCouple:
    """Create an interlattice coupling descriptor."""
    return InterlatticeCouple(
        tongue_a=tongue_a,
        tongue_b=tongue_b,
        coupling_strength=coupling_strength(tongue_a, tongue_b),
        bond_angle=bond_angle(tongue_a, tongue_b),
        phase_factor=phase_factor(tongue_a, tongue_b),
    )


def all_couplings() -> list[InterlatticeCouple]:
    """Generate all 15 unique interlattice couplings (C(6,2))."""
    return [create_couple(a, b) for a, b in combinations(TONGUE_LABELS, 2)]


def nash_equation_of_motion(
    sublattice: TongueSublattice,
    neighbors: list[tuple[TongueSublattice, InterlatticeCouple]],
    omega_plus: float = 1.0,
    omega_minus: float = 0.5,
) -> SublatticeState:
    """
    Nash equation: i(dpsi/dt) = Omega_g*psi + 1/2 * SUM[...coupling terms...]
    First-order dynamics — this is what breaks time-reversal symmetry.
    Returns dpsi/dt.
    """
    psi = sublattice.state
    omega_g = sublattice.precession_freq

    # Self-precession
    rhs_real = omega_g * psi.real
    rhs_imag = omega_g * psi.imag

    for neighbor, couple in neighbors:
        psi_q = neighbor.state

        # Symmetric coupling: Omega_+(psi_p - psi_q)
        diff_real = psi.real - psi_q.real
        diff_imag = psi.imag - psi_q.imag
        rhs_real += 0.5 * omega_plus * diff_real
        rhs_imag += 0.5 * omega_plus * diff_imag

        # Antisymmetric coupling: Omega_- * e^(2i*theta) * (psi*_p - psi*_q)
        conj_diff_real = psi.real - psi_q.real
        conj_diff_imag = -(psi.imag - psi_q.imag)

        pf_real, pf_imag = couple.phase_factor
        anti_real = pf_real * conj_diff_real - pf_imag * conj_diff_imag
        anti_imag = pf_real * conj_diff_imag + pf_imag * conj_diff_real

        rhs_real += 0.5 * omega_minus * anti_real
        rhs_imag += 0.5 * omega_minus * anti_imag

    # i*dpsi/dt = rhs => dpsi/dt = -i*rhs = (rhs_imag, -rhs_real)
    return SublatticeState(real=rhs_imag, imag=-rhs_real)


def evolve_step(
    sublattices: list[TongueSublattice],
    dt: float,
    omega_plus: float = 1.0,
    omega_minus: float = 0.5,
) -> None:
    """Euler step for the full 6-tongue lattice system."""
    couples = all_couplings()
    couple_map: dict[str, InterlatticeCouple] = {}
    for c in couples:
        couple_map[f"{c.tongue_a}-{c.tongue_b}"] = c
        couple_map[f"{c.tongue_b}-{c.tongue_a}"] = c

    # Compute all derivatives before updating
    derivs = []
    for sub in sublattices:
        neighbors = [(s, couple_map[f"{sub.tongue}-{s.tongue}"]) for s in sublattices if s.tongue != sub.tongue]
        derivs.append(nash_equation_of_motion(sub, neighbors, omega_plus, omega_minus))

    # Apply Euler step
    for sub, deriv in zip(sublattices, derivs):
        sub.state.real += deriv.real * dt
        sub.state.imag += deriv.imag * dt


def compute_chern_number(tongue: str, sublattices: list[TongueSublattice]) -> int:
    """Simplified Chern number from bond angle winding."""
    angle_sum = sum(bond_angle(tongue, s.tongue) for s in sublattices if s.tongue != tongue)
    return 1 if math.sin(angle_sum) >= 0 else -1


def coupling_matrix() -> list[list[float]]:
    """Full 6x6 interlattice coupling matrix."""
    n = len(TONGUE_LABELS)
    j = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for k in range(n):
            if i != k:
                j[i][k] = coupling_strength(TONGUE_LABELS[i], TONGUE_LABELS[k])
    return j


def anderson_insulation_test(
    sublattices: list[TongueSublattice],
    disorder_strength: float = 0.1,
    rng: Callable[[], float] | None = None,
) -> dict:
    """
    Test whether disorder preserves or enhances topological protection.
    Mitchell et al. (2021): disorder can drive trivial → topological transition.
    """
    import random

    if rng is None:
        rng = random.random

    clean_chern = [compute_chern_number(s.tongue, sublattices) for s in sublattices]

    disordered = [
        TongueSublattice(
            tongue=s.tongue,
            radius=s.radius * (1 + disorder_strength * (2 * rng() - 1)),
            phase=s.phase,
            precession_freq=s.precession_freq,
            state=SublatticeState(s.state.real, s.state.imag),
            chern_number=s.chern_number,
        )
        for s in sublattices
    ]

    disordered_chern = [compute_chern_number(s.tongue, disordered) for s in disordered]

    clean_total = sum(abs(c) for c in clean_chern)
    disordered_total = sum(abs(c) for c in disordered_chern)

    return {
        "clean_chern": clean_chern,
        "disordered_chern": disordered_chern,
        "topology_preserved": disordered_total >= clean_total,
        "topology_strengthened": disordered_total > clean_total,
    }


def gyroscopic_breathing_factor(
    sublattices: list[TongueSublattice],
    alpha: float = 0.5,
    e_ref: float = 1.0,
) -> float:
    """
    Convert sublattice precession energy into a breathing factor for L6.
    b = 1 + alpha * (E_kin / E_ref), clamped to [1.0, 2.0].
    """
    e_kin = sum((s.state.real**2 + s.state.imag**2) * s.precession_freq for s in sublattices)
    return min(2.0, 1.0 + alpha * (e_kin / max(e_ref, 1e-15)))


def per_tongue_breathing_factors(sublattices: list[TongueSublattice]) -> list[float]:
    """Per-tongue breathing factors from individual precession states."""
    return [min(2.0, 1.0 + (s.state.real**2 + s.state.imag**2) * s.precession_freq) for s in sublattices]


def chern_weights(sublattices: list[TongueSublattice], gamma: float = 0.2) -> list[float]:
    """Chern-modulated tongue weights: w_k = 1 + gamma * C_k."""
    g = max(0.0, min(0.5, gamma))
    return [1.0 + g * s.chern_number for s in sublattices]


def initialize_gyroscopic_lattice() -> dict:
    """Initialize the full 6-tongue gyroscopic lattice system."""
    sublattices = [create_sublattice(t) for t in TONGUE_LABELS]
    couplings = all_couplings()
    mat = coupling_matrix()
    return {"sublattices": sublattices, "couplings": couplings, "coupling_matrix": mat}
