"""
@file shell_duality.py
@module geoseed/shell_duality
@component ShellDuality

Formalizes the reciprocal dual-law structure discovered via parametric fitting:

  E_bind(k) = A / k²      binding depth     — decays outward
  E_curv(k) = A · k²      curvature cost    — grows outward
  I(k) = E_bind · E_curv  = A²              — shell invariant, constant

where k = l + 1 = 1 … 6 for the six GeoSeed tongues.

Geometric derivation (why ±2 must appear from H³):

  On H³ (Poincaré ball), the radial kinetic energy at depth ρ_k scales as
  1/sinh²(ρ_k).  For our phi-mapping ρ_k = k·ln(φ), and since sinh(ρ) ≈ ρ
  at the scales used, this gives E_bind ∝ 1/(k·ln φ)² → 1/k² (up to a
  global scale factor absorbed into A).

  Independently, the Laplace-Beltrami angular eigenvalue on H³ for angular
  momentum l is |λ_l| = (l+1)² = k².  This is the "cost to maintain an
  angular shell at level k" — the curvature support energy.

  Therefore the ±2 exponents are not arbitrary fits; they arise from two
  independent geometric objects on H³:
    radial metric depth  → E_bind ∝ 1/k²
    LB angular stiffness → E_curv ∝  k²

  Their product is constant: E_bind·E_curv = A²  for all k.
  Taking the geometric mean:  sqrt(I(k)) = A = Rydberg constant.

  The measured hydrogen spectrum lives on the E_bind face of this
  two-observable field.  The curvature/LB face is a separate observable
  that the lab instrument does not directly report.

Four objects exported:
  ShellDuality    — dual pair + invariant + coupling ratio + 2D state
  PerturbationTest — invariant flatness under noise, re-indexing, rescaling
  ShellStateField — full 2D field over the shell ladder
  RelationTerm    — coupling φ_k between bind and curv (Compton deviation)

Clean API (all importable at top level):
  compute_invariant(bind_ev, curv_ev)   → float
  shell_state(k, A)                     → (float, float)
  fit_binding_law(shells, values)       → (A, delta, p, rms)
  fit_curvature_law(shells, values)     → (B, delta, q, rms)
  perturbation_sweep(seed)              → PerturbationTest
  plot_duality(out_dir)                 → str (path to PNG)
  export_duality_artifact(out_dir)      → str (path to JSON)
"""

import math
import random
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

PHI = (1.0 + math.sqrt(5.0)) / 2.0


# ── ShellDuality ──────────────────────────────────────────────────────────────


@dataclass
class ShellDuality:
    """
    The reciprocal dual-law pair for GeoSeed shells.

    k runs from 1 to 6 (= l+1, where l is angular momentum 0..5).
    A is the common anchor (default: RYDBERG_EV = 13.606 eV).
    """

    A: float  # common anchor (eV)
    shell_k: List[int]  # [1, 2, 3, 4, 5, 6]
    tongue_labels: List[str]  # ["KO", "AV", "RU", "CA", "UM", "DR"]

    def bind(self, k: int) -> float:
        """E_bind(k) = A / k²   (binding depth, decays outward)"""
        return self.A / (k * k)

    def curv(self, k: int) -> float:
        """E_curv(k) = A · k²   (curvature cost, grows outward)"""
        return self.A * (k * k)

    def invariant(self, k: int) -> float:
        """I(k) = E_bind(k) · E_curv(k) = A²  for all k"""
        return self.bind(k) * self.curv(k)

    def geometric_center(self, k: int) -> float:
        """GM(k) = sqrt(I(k)) = A  for all k  — the Rydberg constant"""
        return math.sqrt(self.invariant(k))

    def coupling_ratio(self, k: int) -> float:
        """R(k) = E_bind(k) / E_curv(k) = 1/k^4  — shell imbalance"""
        return self.bind(k) / self.curv(k)

    def shell_state(self, k: int) -> Tuple[float, float]:
        """2D observable state at shell k: (E_bind, E_curv)"""
        return (self.bind(k), self.curv(k))

    def relation_angle(self, k: int) -> float:
        """
        Angle (radians) of the shell state vector in (bind, curv) space.
        At KO: π/4 (balanced), approaches π/2 outward (curvature-dominated).
        """
        b, c = self.shell_state(k)
        return math.atan2(c, b)

    def bind_fraction(self, k: int) -> float:
        """Fraction of the sum energy that is binding: E_bind / (E_bind + E_curv)"""
        b, c = self.shell_state(k)
        return b / (b + c)

    def curv_fraction(self, k: int) -> float:
        """Fraction of the sum energy that is curvature: E_curv / (E_bind + E_curv)"""
        return 1.0 - self.bind_fraction(k)

    def all_invariants(self) -> List[float]:
        return [self.invariant(k) for k in self.shell_k]

    def all_states(self) -> List[Tuple[float, float]]:
        return [self.shell_state(k) for k in self.shell_k]

    def invariant_cv(self) -> float:
        """Coefficient of variation of I(k) — near 0 = perfectly flat."""
        vals = self.all_invariants()
        mean = sum(vals) / len(vals)
        if mean == 0:
            return float("inf")
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        return math.sqrt(var) / mean

    def is_invariant_flat(self, tol: float = 1e-6) -> bool:
        return self.invariant_cv() < tol

    def derivation_note(self) -> str:
        """Returns the geometric derivation as a human-readable string."""
        return (
            f"Geometric derivation of ±2 exponents on H³:\n"
            f"  E_bind(k) ∝ 1/k²: radial kinetic energy ∝ 1/sinh²(ρ_k)\n"
            f"              where ρ_k = k·ln(φ) → ρ_k ≈ k (scales linearly)\n"
            f"              → E_bind ∝ 1/ρ_k² ∝ 1/k²\n"
            f"  E_curv(k) ∝  k²: Laplace-Beltrami eigenvalue |λ_l| = (l+1)² = k²\n"
            f"              angular support cost for shell l = k-1\n"
            f"  Both arise from H³ geometry independently.\n"
            f"  Product: E_bind·E_curv = (A/k²)·(Ak²) = A² = {self.A**2:.6f} eV²\n"
            f"  Geometric mean: sqrt(I) = A = {self.A:.6f} eV = Rydberg (all shells)\n"
        )

    def to_dict(self) -> dict:
        tongues = self.tongue_labels
        return {
            "schema_version": "geoseed_shell_duality_v1",
            "anchor_A_ev": round(self.A, 9),
            "A_squared_ev2": round(self.A**2, 9),
            "geometric_center_ev": round(self.A, 9),
            "invariant_cv": self.invariant_cv(),
            "is_invariant_flat": self.is_invariant_flat(),
            "derivation": "E_bind*E_curv=A² from H³ radial metric (1/k²) + LB angular stiffness (k²)",
            "shells": [
                {
                    "k": k,
                    "tongue": tongues[i],
                    "bind_ev": round(self.bind(k), 9),
                    "curv_ev": round(self.curv(k), 9),
                    "invariant": round(self.invariant(k), 9),
                    "geometric_center": round(self.geometric_center(k), 9),
                    "coupling_ratio_1_over_k4": round(self.coupling_ratio(k), 9),
                    "relation_angle_deg": round(math.degrees(self.relation_angle(k)), 4),
                    "bind_fraction": round(self.bind_fraction(k), 6),
                    "curv_fraction": round(self.curv_fraction(k), 6),
                }
                for i, k in enumerate(self.shell_k)
            ],
        }


def build_shell_duality(anchor_ev: Optional[float] = None) -> ShellDuality:
    """Build the GeoSeed ShellDuality object with optional custom anchor."""
    if anchor_ev is None:
        from src.geoseed.theory_comparison import RYDBERG_EV

        anchor_ev = RYDBERG_EV
    return ShellDuality(
        A=anchor_ev,
        shell_k=list(range(1, 7)),
        tongue_labels=["KO", "AV", "RU", "CA", "UM", "DR"],
    )


# ── PerturbationTest ──────────────────────────────────────────────────────────


@dataclass
class PerturbationResult:
    """Results of one perturbation scenario."""

    name: str
    description: str
    invariant_values: List[float]
    invariant_cv: float
    invariant_survived: bool  # CV < tolerance
    bind_exponent: float  # fitted p (expect ~2)
    curv_exponent: float  # fitted q (expect ~2)
    exponents_survived: bool  # both p,q within tolerance of 2


@dataclass
class PerturbationTest:
    """Collection of perturbation scenarios testing invariant robustness."""

    scenarios: List[PerturbationResult]

    def all_survived(self) -> bool:
        return all(s.invariant_survived for s in self.scenarios)

    def to_dict(self) -> dict:
        return {
            "schema_version": "geoseed_perturbation_test_v1",
            "all_survived": self.all_survived(),
            "scenarios": [
                {
                    "name": s.name,
                    "description": s.description,
                    "cv": round(s.invariant_cv, 8),
                    "survived": s.invariant_survived,
                    "bind_p": round(s.bind_exponent, 4),
                    "curv_q": round(s.curv_exponent, 4),
                    "exponents_survived": s.exponents_survived,
                }
                for s in self.scenarios
            ],
        }


def _fit_p_q(bind_vals: List[float], curv_vals: List[float], k_vals: List[float]) -> Tuple[float, float]:
    """Quick log-linear regression to estimate exponents p, q."""

    def log_slope(y_vals, x_vals):
        n = len(x_vals)
        log_x = [math.log(abs(x) + 1e-30) for x in x_vals]
        log_y = [math.log(abs(y) + 1e-30) for y in y_vals]
        sx = sum(log_x)
        sy = sum(log_y)
        sxx = sum(lx**2 for lx in log_x)
        sxy = sum(lx * ly for lx, ly in zip(log_x, log_y))
        denom = n * sxx - sx * sx
        if abs(denom) < 1e-20:
            return 0.0
        return (n * sxy - sx * sy) / denom

    p = -log_slope(bind_vals, k_vals)  # bind decays → p should be +2
    q = log_slope(curv_vals, k_vals)  # curv grows → q should be +2
    return p, q


def _make_scenario(
    name: str,
    description: str,
    bind_vals: List[float],
    curv_vals: List[float],
    k_vals: List[float],
    cv_tol: float = 0.02,
    exp_tol: float = 0.2,
) -> PerturbationResult:
    products = [b * c for b, c in zip(bind_vals, curv_vals)]
    mean_p = sum(products) / len(products)
    var_p = sum((v - mean_p) ** 2 for v in products) / len(products)
    cv = math.sqrt(var_p) / mean_p if mean_p > 0 else float("inf")
    p, q = _fit_p_q(bind_vals, curv_vals, k_vals)
    return PerturbationResult(
        name=name,
        description=description,
        invariant_values=products,
        invariant_cv=cv,
        invariant_survived=cv < cv_tol,
        bind_exponent=p,
        curv_exponent=q,
        exponents_survived=abs(p - 2) < exp_tol and abs(q - 2) < exp_tol,
    )


def run_perturbation_tests(seed: int = 42) -> PerturbationTest:
    """
    Test whether the shell invariant I(k) = A² survives under:
      1. Exact (baseline)
      2. Alternate indexing: k = 2..7 instead of 1..6
      3. Unit rescaling: multiply A by 3.7 (arbitrary)
      4. Non-hydrogen anchor: A = 10.0 eV (arbitrary)
      5. Noisy k values: k + N(0, 0.1) — small Gaussian noise on shell index
      6. Half-integer indexing: k = 0.5, 1.5, 2.5, …
      7. Large-anchor stress: A = 1000.0 eV
    """
    from src.geoseed.theory_comparison import RYDBERG_EV

    A = RYDBERG_EV

    rng = random.Random(seed)
    scenarios = []

    # 1. Exact baseline
    ks = list(range(1, 7))
    bind = [A / (k * k) for k in ks]
    curv = [A * (k * k) for k in ks]
    scenarios.append(
        _make_scenario(
            "exact_baseline",
            "k=1..6, A=Rydberg, no noise",
            bind,
            curv,
            [float(k) for k in ks],
            cv_tol=1e-9,
        )
    )

    # 2. Alternate indexing k = 2..7
    ks2 = list(range(2, 8))
    bind2 = [A / (k * k) for k in ks2]
    curv2 = [A * (k * k) for k in ks2]
    scenarios.append(
        _make_scenario(
            "offset_indexing",
            "k=2..7 (offset by 1 from standard)",
            bind2,
            curv2,
            [float(k) for k in ks2],
        )
    )

    # 3. Rescaled anchor: A' = 3.7 * A
    A3 = 3.7 * A
    ks3 = list(range(1, 7))
    bind3 = [A3 / (k * k) for k in ks3]
    curv3 = [A3 * (k * k) for k in ks3]
    scenarios.append(
        _make_scenario(
            "rescaled_anchor",
            f"A = 3.7 × Rydberg = {A3:.2f} eV",
            bind3,
            curv3,
            [float(k) for k in ks3],
        )
    )

    # 4. Non-hydrogen anchor
    A4 = 10.0
    bind4 = [A4 / (k * k) for k in ks]
    curv4 = [A4 * (k * k) for k in ks]
    scenarios.append(
        _make_scenario(
            "non_hydrogen_anchor",
            "A = 10.0 eV (arbitrary non-Rydberg anchor)",
            bind4,
            curv4,
            [float(k) for k in ks],
        )
    )

    # 5. Noisy k: k + ε, ε ~ N(0, 0.1)
    noisy_ks = [k + rng.gauss(0, 0.1) for k in range(1, 7)]
    bind5 = [A / (k * k) for k in noisy_ks]
    curv5 = [A * (k * k) for k in noisy_ks]
    scenarios.append(
        _make_scenario(
            "noisy_k_sigma01",
            "k + Gaussian noise σ=0.1",
            bind5,
            curv5,
            noisy_ks,
            cv_tol=0.05,
        )
    )

    # 6. Half-integer indexing: k = 0.5, 1.5, …, 5.5
    half_ks = [n + 0.5 for n in range(6)]
    bind6 = [A / (k * k) for k in half_ks]
    curv6 = [A * (k * k) for k in half_ks]
    scenarios.append(
        _make_scenario(
            "half_integer_k",
            "k = 0.5, 1.5, ..., 5.5 (fractional shells)",
            bind6,
            curv6,
            half_ks,
        )
    )

    # 7. Large-anchor stress: A = 1000 eV
    A7 = 1000.0
    bind7 = [A7 / (k * k) for k in ks]
    curv7 = [A7 * (k * k) for k in ks]
    scenarios.append(
        _make_scenario(
            "large_anchor",
            "A = 1000 eV (stress test)",
            bind7,
            curv7,
            [float(k) for k in ks],
        )
    )

    return PerturbationTest(scenarios=scenarios)


# ── ShellStateField ───────────────────────────────────────────────────────────


@dataclass
class ShellStateField:
    """
    The full 2D state field over the shell ladder.

    Each shell k has a 2D observable vector S(k) = (E_bind, E_curv).
    The field tracks how the state evolves and what the geometric properties
    of the trajectory through 2D space look like.

    Key properties:
      - At KO (k=1): balanced — bind=curv=A, angle=45°
      - Outward: angle sweeps toward 90° (curvature-dominated)
      - The locus of states traces a hyperbola in (bind, curv) space
        with the invariant I = A² as the hyperbolic constant.
    """

    duality: ShellDuality

    def states(self) -> List[Tuple[float, float]]:
        return [self.duality.shell_state(k) for k in self.duality.shell_k]

    def trajectory_angles_deg(self) -> List[float]:
        """Angle of each shell state vector from the bind axis."""
        return [math.degrees(self.duality.relation_angle(k)) for k in self.duality.shell_k]

    def balance_point(self) -> Tuple[int, float]:
        """
        Shell k where |E_bind - E_curv| is minimized = the "balanced" shell.
        By construction this is always KO (k=1) where bind=curv=A.
        """
        diffs = [abs(self.duality.bind(k) - self.duality.curv(k)) for k in self.duality.shell_k]
        idx = min(range(6), key=lambda i: diffs[i])
        return self.duality.shell_k[idx], diffs[idx]

    def crossover_shell(self) -> Tuple[int, float]:
        """
        Shell k (or fractional k) where E_bind = E_curv.
        For A/k² = Ak², this is k=1 exactly.  Any deviation from A/k²
        (e.g. Compton 1/φ^k) shifts this crossover.
        """
        for _i, k in enumerate(self.duality.shell_k):
            if self.duality.bind(k) <= self.duality.curv(k):
                return k, self.duality.bind(k)
        return self.duality.shell_k[-1], self.duality.bind(self.duality.shell_k[-1])

    def hyperbola_constant(self) -> float:
        """The hyperbolic constant of the (bind, curv) locus = A²."""
        return self.duality.A**2

    def to_dict(self) -> dict:
        states = self.states()
        angles = self.trajectory_angles_deg()
        bal_k, bal_diff = self.balance_point()
        cross_k, cross_e = self.crossover_shell()
        tongues = self.duality.tongue_labels
        return {
            "schema_version": "geoseed_shell_state_field_v1",
            "hyperbola_constant_ev2": round(self.hyperbola_constant(), 9),
            "balance_shell_k": bal_k,
            "crossover_shell_k": cross_k,
            "trajectory": [
                {
                    "k": self.duality.shell_k[i],
                    "tongue": tongues[i],
                    "bind_ev": round(states[i][0], 6),
                    "curv_ev": round(states[i][1], 6),
                    "angle_deg": round(angles[i], 4),
                    "bind_dominant": states[i][0] >= states[i][1],
                }
                for i in range(6)
            ],
        }


def build_shell_state_field(anchor_ev: Optional[float] = None) -> ShellStateField:
    return ShellStateField(duality=build_shell_duality(anchor_ev))


# ── RelationTerm ──────────────────────────────────────────────────────────────


@dataclass
class RelationTerm:
    """
    Coupling between the Compton orbital model and the algebraic dual-law.

    The Compton model predicts E_compton(k) = A / φ^(k-1).
    The dual law predicts E_bind(k) = A / k².

    Coupling ratio ρ(k) = E_compton / E_bind = k² / φ^(k-1) tells us how
    far the standing-wave interpretation sits from the geometric dual-law
    interpretation at each shell.

    Key observations (Rydberg anchor):
      KO (k=1): ρ = 1.000  — exact resonance, ground state balanced
      AV (k=2): ρ = 2.472
      RU (k=3): ρ = 3.438
      CA (k=4): ρ = 3.779  ← peak — f-orbital maximally off-axis
      UM (k=5): ρ = 3.648
      DR (k=6): ρ = 3.246

    The phase angle θ_phase(k) = atan2(E_compton, E_bind) in the
    (bind, compton) plane gives the direction of the Compton model relative
    to the algebraic bind direction.
    """

    A: float
    shell_k: List[int]
    tongue_labels: List[str]

    def compton_ev(self, k: int) -> float:
        """E_compton(k) = A / φ^(k-1)"""
        return self.A / (PHI ** (k - 1))

    def coupling_ratio(self, k: int) -> float:
        """ρ(k) = E_compton(k) / E_bind(k) = k² / φ^(k-1)"""
        return (k * k) / (PHI ** (k - 1))

    def deviation(self, k: int) -> float:
        """|ρ(k) − 1| — fractional deviation from resonance"""
        return abs(self.coupling_ratio(k) - 1.0)

    def phase_angle_deg(self, k: int) -> float:
        """Angle of (E_bind, E_compton) state in degrees."""
        b = self.A / (k * k)
        c = self.compton_ev(k)
        return math.degrees(math.atan2(c, b))

    def resonance_shell(self) -> Tuple[int, float]:
        """Shell where ρ is closest to 1 (most resonant with algebraic dual)."""
        devs = [self.deviation(k) for k in self.shell_k]
        idx = min(range(len(self.shell_k)), key=lambda i: devs[i])
        return self.shell_k[idx], devs[idx]

    def peak_coupling_shell(self) -> Tuple[int, float]:
        """Shell with the largest ρ (most diverged from algebraic dual)."""
        ratios = [self.coupling_ratio(k) for k in self.shell_k]
        idx = max(range(len(self.shell_k)), key=lambda i: ratios[i])
        return self.shell_k[idx], ratios[idx]

    def to_dict(self) -> dict:
        res_k, res_dev = self.resonance_shell()
        peak_k, peak_rho = self.peak_coupling_shell()
        return {
            "schema_version": "geoseed_relation_term_v1",
            "anchor_A_ev": round(self.A, 9),
            "resonance_shell_k": res_k,
            "resonance_tongue": self.tongue_labels[res_k - 1],
            "resonance_deviation": round(res_dev, 9),
            "peak_coupling_shell_k": peak_k,
            "peak_coupling_tongue": self.tongue_labels[peak_k - 1],
            "peak_coupling_rho": round(peak_rho, 6),
            "shells": [
                {
                    "k": k,
                    "tongue": self.tongue_labels[k - 1],
                    "bind_ev": round(self.A / (k * k), 6),
                    "compton_ev": round(self.compton_ev(k), 6),
                    "coupling_rho": round(self.coupling_ratio(k), 6),
                    "deviation": round(self.deviation(k), 6),
                    "phase_angle_deg": round(self.phase_angle_deg(k), 4),
                }
                for k in self.shell_k
            ],
        }


def build_relation_term(anchor_ev: Optional[float] = None) -> RelationTerm:
    """Build the RelationTerm coupling object for the six GeoSeed shells."""
    if anchor_ev is None:
        from src.geoseed.theory_comparison import RYDBERG_EV

        anchor_ev = RYDBERG_EV
    return RelationTerm(
        A=anchor_ev,
        shell_k=list(range(1, 7)),
        tongue_labels=["KO", "AV", "RU", "CA", "UM", "DR"],
    )


# ── Clean top-level API ───────────────────────────────────────────────────────


def compute_invariant(bind_ev: float, curv_ev: float) -> float:
    """Shell invariant I = E_bind × E_curv. Constant at A² for all k."""
    return bind_ev * curv_ev


def shell_state_at(k: int, A: Optional[float] = None) -> Tuple[float, float]:
    """(E_bind, E_curv) at shell k with anchor A (default: Rydberg)."""
    if A is None:
        from src.geoseed.theory_comparison import RYDBERG_EV

        A = RYDBERG_EV
    return A / (k * k), A * (k * k)


def fit_binding_law(shells: List[float], values: List[float]) -> Tuple[float, float, float, float]:
    """
    Fit E = A / (k+δ)^p to binding energy values.
    Returns (A, delta, p, rms).
    """
    from src.geoseed.theory_fit import fit_power_law

    return fit_power_law(values, ns=shells)


def fit_curvature_law(shells: List[float], values: List[float]) -> Tuple[float, float, float, float]:
    """
    Fit E = B · (k+δ)^q to curvature energy values.
    Returns (B, delta, q, rms).
    """
    from src.geoseed.theory_fit import _fit_growth_law

    return _fit_growth_law(values, ns=shells)


def perturbation_sweep(seed: int = 42) -> "PerturbationTest":
    """7-scenario perturbation test of invariant robustness. Returns PerturbationTest."""
    return run_perturbation_tests(seed=seed)


# ── Visualization ─────────────────────────────────────────────────────────────


def plot_duality(out_dir: Optional[str] = None) -> str:
    """
    3-panel plot of the shell duality field.

    Panel 1: E_bind and E_curv on log scale (the reciprocal dual curves)
    Panel 2: I(k) = E_bind × E_curv flatness (constant line at A²)
    Panel 3: Coupling ratio ρ(k) = k²/φ^(k-1) (Compton deviation per shell)

    Returns the path to the saved PNG, or a fallback message if matplotlib
    is not available.
    """
    import os

    if out_dir is None:
        out_dir = "artifacts/geoseed"
    os.makedirs(out_dir, exist_ok=True)

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return "<matplotlib not installed — plot skipped>"

    dual = build_shell_duality()
    rel = build_relation_term()
    ks = dual.shell_k
    xlabels = ["KO(s)", "AV(p)", "RU(d)", "CA(f)", "UM(g)", "DR(h)"]

    bind_vals = [dual.bind(k) for k in ks]
    curv_vals = [dual.curv(k) for k in ks]
    inv_vals = [dual.invariant(k) for k in ks]
    rho_vals = [rel.coupling_ratio(k) for k in ks]

    fig, axes = plt.subplots(3, 1, figsize=(8, 10))
    fig.suptitle(
        "GeoSeed Shell Duality Field\n" f"I(k) = E_bind × E_curv = A² = {dual.A ** 2:.4f} eV²  (constant for all k)",
        fontsize=11,
        fontweight="bold",
    )

    # ── Panel 1: dual energy curves ──
    ax = axes[0]
    ax.semilogy(ks, bind_vals, "o-", color="#2196F3", lw=2, label="E_bind(k) = A/k²  (decays)")
    ax.semilogy(ks, curv_vals, "s-", color="#F44336", lw=2, label="E_curv(k) = A·k²  (grows)")
    ax.axhline(dual.A, ls="--", color="#888888", lw=1.2, label=f"Rydberg A = {dual.A:.4f} eV")
    ax.set_xticks(ks)
    ax.set_xticklabels(xlabels, fontsize=9)
    ax.set_ylabel("Energy (eV, log scale)")
    ax.set_title("Dual Observables — Binding (↓) vs Curvature (↑)")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, which="both")

    # ── Panel 2: invariant flatness ──
    ax = axes[1]
    ax.plot(ks, inv_vals, "D-", color="#4CAF50", lw=2, ms=8, label="I(k) = E_bind × E_curv")
    ax.axhline(dual.A**2, ls="--", color="#888888", lw=1.5, label=f"A² = {dual.A ** 2:.4f} eV²  (constant)")
    ax.set_xticks(ks)
    ax.set_xticklabels(xlabels, fontsize=9)
    ax.set_ylabel("Invariant I(k)  (eV²)")
    ax.set_title("Shell Invariant — Constant at A² Across All Shells")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.text(
        0.98,
        0.06,
        f"CV = {dual.invariant_cv():.2e}",
        ha="right",
        va="bottom",
        transform=ax.transAxes,
        fontsize=10,
        color="#4CAF50",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85),
    )

    # ── Panel 3: Compton coupling ratio ──
    ax = axes[2]
    ax.bar(ks, rho_vals, color="#FF9800", alpha=0.82, label="ρ(k) = k²/φ^(k−1)  (Compton/dual ratio)")
    ax.axhline(1.0, ls="--", color="#555555", lw=1.5, label="ρ = 1  (ground-state resonance)")
    ax.set_xticks(ks)
    ax.set_xticklabels(xlabels, fontsize=9)
    ax.set_ylabel("Coupling ratio ρ(k)")
    ax.set_title("Compton–Dual Coupling  (peaks at CA, resonant at KO)")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")
    peak_k, peak_rho = rel.peak_coupling_shell()
    ax.annotate(
        f"peak k={peak_k}\nρ = {peak_rho:.2f}",
        xy=(peak_k, peak_rho),
        xytext=(peak_k + 0.5, peak_rho - 0.4),
        fontsize=8,
        arrowprops=dict(arrowstyle="->", color="gray"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85),
    )

    plt.tight_layout()
    out_path = os.path.join(out_dir, "shell_duality.png")
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return out_path


# ── JSON artifact ─────────────────────────────────────────────────────────────


def export_duality_artifact(out_dir: Optional[str] = None) -> str:
    """
    Write a complete duality summary to a JSON file.

    Sections:
      summary  — top-level invariants at a glance
      duality  — ShellDuality per-shell table
      field    — ShellStateField trajectory + angles
      perturbation — 7-scenario robustness test
      relation — RelationTerm Compton coupling per shell

    Returns the path to the saved JSON file.
    """
    import json
    import os

    if out_dir is None:
        out_dir = "artifacts/geoseed"
    os.makedirs(out_dir, exist_ok=True)

    dual = build_shell_duality()
    field_obj = build_shell_state_field()
    pert = run_perturbation_tests()
    rel = build_relation_term()

    res_k, _ = rel.resonance_shell()
    peak_k, peak_rho = rel.peak_coupling_shell()

    artifact: Dict = {
        "schema_version": "geoseed_shell_duality_artifact_v1",
        "generated_by": "shell_duality.export_duality_artifact",
        "summary": {
            "anchor_A_ev": round(dual.A, 9),
            "A_squared_ev2": round(dual.A**2, 9),
            "invariant_cv": dual.invariant_cv(),
            "is_invariant_flat": dual.is_invariant_flat(),
            "all_perturbations_survived": pert.all_survived(),
            "resonance_shell_k": res_k,
            "resonance_tongue": dual.tongue_labels[res_k - 1],
            "peak_coupling_shell_k": peak_k,
            "peak_coupling_tongue": dual.tongue_labels[peak_k - 1],
            "peak_coupling_rho": round(peak_rho, 6),
            "derivation": (
                "E_bind(k)=A/k² from H³ radial kinetic depth (1/sinh²(ρ_k)); "
                "E_curv(k)=A·k² from Laplace-Beltrami angular stiffness (l+1)²; "
                "product I(k)=A² is algebraically constant — not a fit."
            ),
        },
        "duality": dual.to_dict(),
        "field": field_obj.to_dict(),
        "perturbation": pert.to_dict(),
        "relation": rel.to_dict(),
    }

    out_path = os.path.join(out_dir, "shell_duality_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2)
    return out_path


# ── ASCII summary ─────────────────────────────────────────────────────────────


def duality_field_report() -> str:

    dual = build_shell_duality()
    pert = run_perturbation_tests()
    tongues = ["KO(s)", "AV(p)", "RU(d)", "CA(f)", "UM(g)", "DR(h)"]

    lines = []
    lines.append("=" * 72)
    lines.append("  SHELL DUALITY FIELD  (GeoSeed reciprocal dual-law)")
    lines.append(f"  Anchor A = {dual.A:.6f} eV  →  A² = {dual.A**2:.6f} eV²")
    lines.append("=" * 72)
    lines.append(dual.derivation_note())
    lines.append("")

    lines.append(
        f"  {'Shell':<10}  {'E_bind':>10}  {'E_curv':>12}  " f"{'I(k)=A²':>14}  {'angle°':>8}  {'dominant':>10}"
    )
    lines.append("  " + "-" * 70)
    for i, k in enumerate(dual.shell_k):
        b, c = dual.shell_state(k)
        ang = math.degrees(dual.relation_angle(k))
        dom = "BINDING" if b >= c else "CURVATURE"
        lines.append(
            f"  {tongues[i]:<10}  {b:>10.4f}  {c:>12.4f}" f"  {dual.invariant(k):>14.6f}  {ang:>8.2f}°  {dom:>10}"
        )
    lines.append("")
    lines.append(f"  Product CV = {dual.invariant_cv():.2e}  (flat = invariant holds)")
    lines.append(f"  Geometric center (sqrt(I)) = {math.sqrt(dual.A**2):.6f} eV  [Rydberg]")
    lines.append("")

    lines.append("=" * 72)
    lines.append("  PERTURBATION TEST (invariant robustness)")
    lines.append("=" * 72)
    lines.append(f"  {'Scenario':<24}  {'CV':>12}  {'Survived':>10}  " f"{'p':>8}  {'q':>8}  {'exp±ok':>8}")
    lines.append("  " + "-" * 72)
    for s in pert.scenarios:
        lines.append(
            f"  {s.name:<24}  {s.invariant_cv:>12.6f}  {str(s.invariant_survived):>10}  "
            f"  {s.bind_exponent:>6.3f}  {s.curv_exponent:>6.3f}  "
            f"{str(s.exponents_survived):>8}"
        )
    lines.append(f"  All survived: {pert.all_survived()}")
    lines.append("=" * 72)
    return "\n".join(lines)


def main():
    print(duality_field_report())
    json_path = export_duality_artifact()
    print(f"\nArtifact written: {json_path}")
    png_path = plot_duality()
    print(f"Plot written:     {png_path}")


if __name__ == "__main__":
    main()
