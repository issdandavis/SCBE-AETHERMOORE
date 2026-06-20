"""
@file theory_fit.py
@module geoseed/theory_fit
@component ElectronTheoryFit

Parametric curve-fitting over the 6 GeoSeed shells to answer:

  (A) Which family — power-law or exponential — best describes each theory?
  (B) Where exactly do Bohr and Compton-orbital diverge significantly?
  (C) What is the clean split between Observable A (binding) and Observable B
      (curvature / manifold support cost)?

Two generalized families are fitted for every theory:
  Power-law:    E_n = A / (n + delta)^p
  Exponential:  E_n = A * lambda^{-n}

Bohr should land at  p ≈ 2,  lambda ≈ n² / φ⁰ → different curve.
Compton should land at lambda ≈ φ  (golden ratio).
GeoSeed LB grows outward → fit reveals it as p = -2 (cost, not binding).

Observable classification:
  A (binding):   theories whose fitted slope matches Bohr's 1/n² family
                 (compton_orbital, bohr, pilot_wave)
  B (curvature): theories that grow or stay flat outward
                 (geoseed_lb, harmonic)

Combined energy model:
  E_total(n) = E_bind(n) + E_curv(n)

where E_bind uses the Compton-orbital model and E_curv uses GeoSeed-LB.
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

PHI = (1.0 + math.sqrt(5.0)) / 2.0

# ── Minimal curve fitting (no scipy required) via Nelder-Mead ─────────────────
# This way the module works with stdlib only.


def _nelder_mead(f, x0: List[float], tol: float = 1e-9, max_iter: int = 5000) -> List[float]:
    """Nelder-Mead simplex minimizer (stdlib only)."""
    n = len(x0)
    alpha, beta, gamma, delta = 1.0, 0.5, 2.0, 0.5

    simplex = [list(x0)]
    for i in range(n):
        pt = list(x0)
        pt[i] *= 1.05 if pt[i] != 0 else 0.05
        simplex.append(pt)

    def score(pt):
        try:
            return f(pt)
        except Exception:
            return float("inf")

    scores = [score(pt) for pt in simplex]

    for _ in range(max_iter):
        order = sorted(range(n + 1), key=lambda i: scores[i])
        simplex = [simplex[i] for i in order]
        scores = [scores[i] for i in order]

        if scores[-1] - scores[0] < tol:
            break

        centroid = [sum(simplex[i][j] for i in range(n)) / n for j in range(n)]

        # Reflect
        worst = simplex[-1]
        r = [centroid[j] + alpha * (centroid[j] - worst[j]) for j in range(n)]
        sr = score(r)

        if scores[0] <= sr < scores[-2]:
            simplex[-1] = r
            scores[-1] = sr
            continue

        if sr < scores[0]:
            # Expand
            e = [centroid[j] + gamma * (r[j] - centroid[j]) for j in range(n)]
            se = score(e)
            if se < sr:
                simplex[-1] = e
                scores[-1] = se
            else:
                simplex[-1] = r
                scores[-1] = sr
            continue

        # Contract
        c = [centroid[j] + beta * (worst[j] - centroid[j]) for j in range(n)]
        sc = score(c)
        if sc < scores[-1]:
            simplex[-1] = c
            scores[-1] = sc
            continue

        # Shrink
        best = simplex[0]
        simplex = [best] + [[best[j] + delta * (simplex[i][j] - best[j]) for j in range(n)] for i in range(1, n + 1)]
        scores = [score(pt) for pt in simplex]

    return simplex[0]


# ── Fit functions ─────────────────────────────────────────────────────────────


def _power_law(n: int, A: float, delta: float, p: float) -> float:
    """E = A / (n + delta)^p"""
    base = n + delta
    if base <= 0:
        return float("inf")
    return A / (base**p)


def _exponential(n: int, A: float, lam: float) -> float:
    """E = A * lambda^{-n}"""
    if lam <= 0:
        return float("inf")
    return A * (lam ** (-n))


def fit_power_law(energies: List[float], ns: Optional[List[int]] = None) -> Tuple[float, float, float, float]:
    """
    Fit E_n = A / (n + delta)^p to the given energy list.
    Returns (A, delta, p, residual_rms).
    ns defaults to 0..5 (GeoSeed shell indices).
    """
    if ns is None:
        ns = list(range(len(energies)))
    n_pts = len(ns)

    def residual(params):
        A, delta, p = params
        total = 0.0
        for i, n in enumerate(ns):
            pred = _power_law(n, A, delta, p)
            if not math.isfinite(pred):
                return 1e18
            total += (pred - energies[i]) ** 2
        return total / n_pts

    x0 = [energies[0], 1.0, 2.0]
    params = _nelder_mead(residual, x0)
    A, delta, p = params
    rms = math.sqrt(residual(params))
    return A, delta, p, rms


def fit_exponential(energies: List[float], ns: Optional[List[int]] = None) -> Tuple[float, float, float]:
    """
    Fit E_n = A * lambda^{-n} to the given energy list.
    Returns (A, lambda, residual_rms).
    """
    if ns is None:
        ns = list(range(len(energies)))
    n_pts = len(ns)

    def residual(params):
        A, lam = params
        total = 0.0
        for i, n in enumerate(ns):
            pred = _exponential(n, A, lam)
            if not math.isfinite(pred):
                return 1e18
            total += (pred - energies[i]) ** 2
        return total / n_pts

    x0 = [energies[0], PHI]
    params = _nelder_mead(residual, x0)
    A, lam = params
    rms = math.sqrt(residual(params))
    return A, lam, rms


# ── FitResult ─────────────────────────────────────────────────────────────────


@dataclass
class FitResult:
    theory_name: str
    # Power-law fit
    pl_A: float
    pl_delta: float
    pl_p: float
    pl_rms: float
    # Exponential fit
    exp_A: float
    exp_lambda: float
    exp_rms: float
    # Diagnosis
    better_fit: str  # "power_law" or "exponential"
    observable: str  # "binding" or "curvature"
    notes: str = ""

    def predicted_power_law(self, n: int) -> float:
        return _power_law(n, self.pl_A, self.pl_delta, self.pl_p)

    def predicted_exponential(self, n: int) -> float:
        return _exponential(n, self.exp_A, self.exp_lambda)

    def to_dict(self) -> dict:
        return {
            "theory": self.theory_name,
            "observable": self.observable,
            "better_fit": self.better_fit,
            "power_law": {
                "A": round(self.pl_A, 6),
                "delta": round(self.pl_delta, 6),
                "p": round(self.pl_p, 6),
                "rms": round(self.pl_rms, 6),
                "formula": f"E = {self.pl_A:.4f} / (n + {self.pl_delta:.4f})^{self.pl_p:.4f}",
            },
            "exponential": {
                "A": round(self.exp_A, 6),
                "lambda": round(self.exp_lambda, 6),
                "rms": round(self.exp_rms, 6),
                "formula": f"E = {self.exp_A:.4f} * {self.exp_lambda:.4f}^(-n)",
                "lambda_vs_phi": round(self.exp_lambda / PHI, 6),
            },
            "notes": self.notes,
        }


# ── Classification ────────────────────────────────────────────────────────────

# Theories that model binding energy (decay outward, similar slope to Bohr)
OBSERVABLE_A_BINDING = {"bohr", "compton_orbital", "pilot_wave"}
# Theories that model curvature / manifold support cost (grow or stay flat outward)
OBSERVABLE_B_CURVATURE = {"geoseed_lb", "harmonic", "de_broglie"}


def _classify_observable(name: str, pl_p: float) -> str:
    if name in OBSERVABLE_A_BINDING:
        return "binding"
    if name in OBSERVABLE_B_CURVATURE:
        return "curvature"
    # Fallback: negative p = grows outward = curvature
    return "binding" if pl_p > 0 else "curvature"


def fit_all_theories() -> Dict[str, FitResult]:
    """Run parametric fits for all theories and return FitResult per theory."""
    from src.geoseed.theory_comparison import run_all

    results = run_all()
    fit_results: Dict[str, FitResult] = {}

    for name, theory in results.items():
        evs = theory.energies_ev()

        pl_A, pl_delta, pl_p, pl_rms = fit_power_law(evs)
        exp_A, exp_lam, exp_rms = fit_exponential(evs)

        better = "power_law" if pl_rms <= exp_rms else "exponential"
        obs = _classify_observable(name, pl_p)

        notes_parts = []
        if name == "compton_orbital":
            notes_parts.append(f"exp λ={exp_lam:.4f} vs φ={PHI:.4f}  (ratio {exp_lam/PHI:.4f})")
        if name == "bohr":
            notes_parts.append(f"power-law p={pl_p:.4f} (expected p≈2 for 1/n²)")
        if name == "geoseed_lb":
            notes_parts.append(f"power-law p={pl_p:.4f} — negative = grows outward = curvature cost")

        fit_results[name] = FitResult(
            theory_name=name,
            pl_A=pl_A,
            pl_delta=pl_delta,
            pl_p=pl_p,
            pl_rms=pl_rms,
            exp_A=exp_A,
            exp_lambda=exp_lam,
            exp_rms=exp_rms,
            better_fit=better,
            observable=obs,
            notes=" | ".join(notes_parts),
        )

    return fit_results


# ── Crossover analysis ────────────────────────────────────────────────────────


@dataclass
class CrossoverAnalysis:
    """Where Bohr and Compton-orbital diverge from the same anchor point."""

    shell_ratios: List[float]  # compton_ev[n] / bohr_ev[n] per shell
    divergence_pct: List[float]  # (compton - bohr) / bohr * 100
    first_significant_shell: int  # first shell where |ratio - 1| > 0.5 (50%)
    peak_divergence_shell: int  # shell with maximum ratio
    peak_ratio: float
    compton_ev: List[float]
    bohr_ev: List[float]
    notes: str

    def to_dict(self) -> dict:
        return {
            "shell_ratios": [round(r, 4) for r in self.shell_ratios],
            "divergence_pct": [round(d, 1) for d in self.divergence_pct],
            "first_significant_shell": self.first_significant_shell,
            "peak_divergence_shell": self.peak_divergence_shell,
            "peak_ratio": round(self.peak_ratio, 4),
            "compton_ev": [round(e, 4) for e in self.compton_ev],
            "bohr_ev": [round(e, 4) for e in self.bohr_ev],
            "notes": self.notes,
        }


def crossover_analysis() -> CrossoverAnalysis:
    """
    Compute where Compton-orbital diverges from Bohr across 6 shells.
    Both are anchored at KO (shell 0) = Rydberg energy.

    The crossover point is where the ratio compton/bohr becomes large enough
    to be experimentally distinguishable (here: >50% divergence threshold).
    """
    from src.geoseed.theory_comparison import theory_compton_orbital, theory_bohr

    compton = theory_compton_orbital()
    bohr = theory_bohr()

    c_evs = compton.energies_ev()
    b_evs = bohr.energies_ev()

    ratios = [c / b for c, b in zip(c_evs, b_evs)]
    div_pct = [(r - 1.0) * 100 for r in ratios]

    first_sig = next((i for i, r in enumerate(ratios) if abs(r - 1.0) > 0.5), len(ratios) - 1)
    peak_shell = max(range(6), key=lambda i: ratios[i])
    peak_ratio = ratios[peak_shell]

    tongue_names = ["KO(s)", "AV(p)", "RU(d)", "CA(f)", "UM(g)", "DR(h)"]
    notes = (
        f"First shell where Compton differs >50% from Bohr: "
        f"{tongue_names[first_sig]} (shell {first_sig}).  "
        f"Peak divergence at {tongue_names[peak_shell]}: "
        f"Compton={c_evs[peak_shell]:.3f} eV vs Bohr={b_evs[peak_shell]:.3f} eV "
        f"({peak_ratio:.2f}x).  "
        f"Compton-orbital retains ~{c_evs[-1]/b_evs[-1]:.1f}x more energy at the DR shell."
    )

    return CrossoverAnalysis(
        shell_ratios=ratios,
        divergence_pct=div_pct,
        first_significant_shell=first_sig,
        peak_divergence_shell=peak_shell,
        peak_ratio=peak_ratio,
        compton_ev=c_evs,
        bohr_ev=b_evs,
        notes=notes,
    )


# ── Combined energy model ──────────────────────────────────────────────────────


@dataclass
class CombinedEnergy:
    """
    E_total(n) = E_bind(n) + E_curv(n)

    E_bind uses Compton-orbital (best non-Bohr binding candidate)
    E_curv uses GeoSeed-LB (hyperbolic curvature / manifold support cost)

    Both normalised so their KO values sum to twice the Rydberg energy.
    Alternatively, normalise E_curv separately so that it represents a
    fractional overhead on E_bind.
    """

    shell_indices: List[int]
    bind_ev: List[float]  # Compton-orbital
    curv_ev: List[float]  # GeoSeed-LB
    total_ev: List[float]  # sum
    bohr_ev: List[float]  # reference
    curv_fraction: List[float]  # E_curv / E_total per shell

    def to_dict(self) -> dict:
        tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
        return {
            "schema_version": "geoseed_combined_energy_v1",
            "description": "E_total = E_bind(Compton) + E_curv(GeoSeed-LB)",
            "shells": [
                {
                    "shell": i,
                    "tongue": tongues[i],
                    "bind_ev": round(self.bind_ev[i], 4),
                    "curv_ev": round(self.curv_ev[i], 4),
                    "total_ev": round(self.total_ev[i], 4),
                    "bohr_ref_ev": round(self.bohr_ev[i], 4),
                    "curv_fraction": round(self.curv_fraction[i], 4),
                }
                for i in range(6)
            ],
        }


def combined_energy_model(curv_scale: float = 0.1) -> CombinedEnergy:
    """
    Build the combined E_total = E_bind + E_curv model.

    curv_scale: weight to apply to the GeoSeed-LB curvature term.
    Default 0.1 makes the curvature term a 10% overhead at the ground shell —
    small enough to not dominate binding but measurable at outer shells.
    """
    from src.geoseed.theory_comparison import theory_compton_orbital, theory_geoseed_lb, theory_bohr

    bind = theory_compton_orbital().energies_ev()
    lb = theory_geoseed_lb().energies_ev()
    bohr = theory_bohr().energies_ev()

    # Scale curvature so that curv(KO) = curv_scale * bind(KO)
    curv_anchor = lb[0]
    bind_anchor = bind[0]
    curv = [lb[i] * (curv_scale * bind_anchor / curv_anchor) for i in range(6)]

    total = [bind[i] + curv[i] for i in range(6)]
    fracs = [curv[i] / total[i] for i in range(6)]

    return CombinedEnergy(
        shell_indices=list(range(6)),
        bind_ev=bind,
        curv_ev=curv,
        total_ev=total,
        bohr_ev=bohr,
        curv_fraction=fracs,
    )


# ── ASCII summary ─────────────────────────────────────────────────────────────


def fit_report() -> str:
    fits = fit_all_theories()
    cx = crossover_analysis()
    comb = combined_energy_model()

    tongues = ["KO(s)", "AV(p)", "RU(d)", "CA(f)", "UM(g)", "DR(h)"]
    lines = []
    lines.append("=" * 72)
    lines.append("  PARAMETRIC FIT RESULTS")
    lines.append("=" * 72)
    lines.append("")
    lines.append(
        f"  {'Theory':<20}  {'Obs':<10}  {'Better fit':<12}  "
        f"{'PL p':<8}  {'Exp λ':<8}  {'PL rms':<10}  {'Exp rms':<10}"
    )
    lines.append("  " + "-" * 70)
    for name, f in fits.items():
        lines.append(
            f"  {name:<20}  {f.observable:<10}  {f.better_fit:<12}  "
            f"{f.pl_p:<8.3f}  {f.exp_lambda:<8.4f}  {f.pl_rms:<10.4f}  {f.exp_rms:<10.4f}"
        )
        if f.notes:
            lines.append(f"    ↳ {f.notes}")
    lines.append("")

    lines.append("=" * 72)
    lines.append("  CROSSOVER ANALYSIS: Compton vs Bohr")
    lines.append("=" * 72)
    lines.append("")
    lines.append("  Shell     Compton(eV)   Bohr(eV)   Ratio   Δ%")
    lines.append("  " + "-" * 55)
    for i, t in enumerate(tongues):
        lines.append(
            f"  {t:<10}  {cx.compton_ev[i]:>10.3f}  {cx.bohr_ev[i]:>10.3f}"
            f"   {cx.shell_ratios[i]:>5.2f}   {cx.divergence_pct[i]:>+7.1f}%"
        )
    lines.append("")
    lines.append(f"  {cx.notes}")
    lines.append("")

    lines.append("=" * 72)
    lines.append("  COMBINED ENERGY MODEL  E_total = E_bind + E_curv")
    lines.append("  (Compton binding + 10%-scaled GeoSeed-LB curvature)")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"  {'Shell':<10}  {'E_bind':<12}  {'E_curv':<12}  " f"{'E_total':<12}  {'E_Bohr':<12}  {'curv%':<8}")
    lines.append("  " + "-" * 68)
    for i, t in enumerate(tongues):
        lines.append(
            f"  {t:<10}  {comb.bind_ev[i]:>12.4f}  {comb.curv_ev[i]:>12.4f}  "
            f"{comb.total_ev[i]:>12.4f}  {comb.bohr_ev[i]:>12.4f}  "
            f"{comb.curv_fraction[i]*100:>6.1f}%"
        )
    lines.append("=" * 72)
    return "\n".join(lines)


# ── Independent dual fit ──────────────────────────────────────────────────────


@dataclass
class DualFitResult:
    """
    Fit E_bind and E_curv with fully independent parameters.
    E_bind = A / (n + delta_b)^p
    E_curv = B * (n + delta_c)^q    (positive q = grows outward)
    """

    # Binding fit
    bind_A: float
    bind_delta: float
    bind_p: float
    bind_rms: float
    # Curvature fit
    curv_B: float
    curv_delta: float
    curv_q: float
    curv_rms: float
    # Dual check
    p_near_2: bool  # bind exponent converges to 2
    q_near_2: bool  # curv exponent converges to 2
    product_constant: bool  # I(l) = E_bind(l) * E_curv(l) is flat
    product_values: List[float]
    product_cv: float  # coefficient of variation (std/mean), near 0 = flat

    def predicted_bind(self, n: int) -> float:
        return _power_law(n, self.bind_A, self.bind_delta, self.bind_p)

    def predicted_curv(self, n: int) -> float:
        base = n + self.curv_delta
        if base <= 0:
            return 0.0
        return self.curv_B * (base**self.curv_q)

    def to_dict(self) -> dict:
        return {
            "schema_version": "geoseed_dual_fit_v1",
            "binding": {
                "formula": f"E_bind = {self.bind_A:.4f} / (n + {self.bind_delta:.4f})^{self.bind_p:.4f}",
                "A": round(self.bind_A, 6),
                "delta": round(self.bind_delta, 6),
                "p": round(self.bind_p, 6),
                "rms": round(self.bind_rms, 6),
                "p_near_2": self.p_near_2,
            },
            "curvature": {
                "formula": f"E_curv = {self.curv_B:.4f} * (n + {self.curv_delta:.4f})^{self.curv_q:.4f}",
                "B": round(self.curv_B, 6),
                "delta": round(self.curv_delta, 6),
                "q": round(self.curv_q, 6),
                "rms": round(self.curv_rms, 6),
                "q_near_2": self.q_near_2,
            },
            "product_invariant": {
                "constant": self.product_constant,
                "values": [round(v, 4) for v in self.product_values],
                "cv": round(self.product_cv, 6),
            },
        }


def _fit_growth_law(energies: List[float], ns: Optional[List[int]] = None) -> Tuple[float, float, float, float]:
    """
    Fit E_n = B * (n + delta)^q  (positive exponent, grows outward).
    Returns (B, delta, q, rms).
    """
    if ns is None:
        ns = list(range(len(energies)))
    n_pts = len(ns)

    def residual(params):
        B, delta, q = params
        total = 0.0
        for i, n in enumerate(ns):
            base = n + delta
            if base <= 0 or B <= 0:
                return 1e18
            pred = B * (base**q)
            if not math.isfinite(pred):
                return 1e18
            total += (pred - energies[i]) ** 2
        return total / n_pts

    x0 = [energies[0], 1.0, 2.0]
    params = _nelder_mead(residual, x0)
    B, delta, q = params
    rms = math.sqrt(residual(params))
    return B, delta, q, rms


def independent_dual_fit() -> DualFitResult:
    """
    Fit E_bind (Bohr = measured hydrogen) and E_curv (GeoSeed LB) with
    completely independent prefactors and exponents.

    Checks whether the exponents converge to ±2 without being told to,
    and whether I(l) = E_bind(l) * E_curv(l) is flat across shells.
    """
    from src.geoseed.theory_comparison import HYDROGEN_MEASURED_EV, theory_geoseed_lb

    bind_evs = HYDROGEN_MEASURED_EV  # measured hydrogen — source of truth
    curv_evs = theory_geoseed_lb().energies_ev()

    # Fit binding (decay law)
    b_A, b_delta, b_p, b_rms = fit_power_law(bind_evs)
    # Fit curvature (growth law)
    c_B, c_delta, c_q, c_rms = _fit_growth_law(curv_evs)

    # Product invariant
    product = [_power_law(n, b_A, b_delta, b_p) * (c_B * max(n + c_delta, 1e-10) ** c_q) for n in range(6)]
    mean_p = sum(product) / len(product)
    var_p = sum((v - mean_p) ** 2 for v in product) / len(product)
    cv = math.sqrt(var_p) / mean_p if mean_p > 0 else float("inf")

    return DualFitResult(
        bind_A=b_A,
        bind_delta=b_delta,
        bind_p=b_p,
        bind_rms=b_rms,
        curv_B=c_B,
        curv_delta=c_delta,
        curv_q=c_q,
        curv_rms=c_rms,
        p_near_2=abs(b_p - 2.0) < 0.15,
        q_near_2=abs(c_q - 2.0) < 0.15,
        product_constant=cv < 0.05,
        product_values=product,
        product_cv=cv,
    )


# ── Product invariant ─────────────────────────────────────────────────────────


@dataclass
class ProductInvariant:
    """
    I(l) = E_bind(l) * E_curv(l) per shell.
    Measures how flat the product is — flatness = dual law is structural.
    """

    shell_values: List[float]  # I(l) per shell
    mean: float
    std: float
    cv: float  # coefficient of variation: std/mean
    is_flat: bool  # cv < 0.02 (2% variation)
    bohr_evs: List[float]
    lb_evs: List[float]
    rydberg_sq: float  # theoretical prediction: I = RYDBERG²

    def to_dict(self) -> dict:
        return {
            "schema_version": "geoseed_product_invariant_v1",
            "description": "I(l) = E_bind(l) * E_curv(l) — tests dual-law flatness",
            "shells": [
                {
                    "shell": i,
                    "tongue": ["KO", "AV", "RU", "CA", "UM", "DR"][i],
                    "bind_ev": round(self.bohr_evs[i], 6),
                    "curv_ev": round(self.lb_evs[i], 6),
                    "product": round(self.shell_values[i], 6),
                    "deviation_from_mean_pct": round((self.shell_values[i] - self.mean) / self.mean * 100, 4),
                }
                for i in range(6)
            ],
            "mean": round(self.mean, 6),
            "std": round(self.std, 6),
            "cv": round(self.cv, 9),
            "is_flat": self.is_flat,
            "rydberg_sq": round(self.rydberg_sq, 6),
            "product_equals_rydberg_sq": abs(self.mean - self.rydberg_sq) < 1.0,
        }


def compute_product_invariant() -> ProductInvariant:
    """
    Compute I(l) = E_bind(l) * E_curv(l) for the Bohr and GeoSeed-LB pair.
    Both use the same anchor (RYDBERG_EV), so the product should equal
    RYDBERG_EV² = 185.11 eV² exactly.
    """
    from src.geoseed.theory_comparison import theory_bohr, theory_geoseed_lb, RYDBERG_EV

    bind_evs = theory_bohr().energies_ev()
    curv_evs = theory_geoseed_lb().energies_ev()

    products = [bind_evs[i] * curv_evs[i] for i in range(6)]
    mean_v = sum(products) / 6
    std_v = math.sqrt(sum((v - mean_v) ** 2 for v in products) / 6)
    cv = std_v / mean_v if mean_v > 0 else float("inf")

    return ProductInvariant(
        shell_values=products,
        mean=mean_v,
        std=std_v,
        cv=cv,
        is_flat=cv < 1e-6,  # exact by construction if both normalised the same
        bohr_evs=bind_evs,
        lb_evs=curv_evs,
        rydberg_sq=RYDBERG_EV**2,
    )


# ── Weighted-sum fit ──────────────────────────────────────────────────────────


@dataclass
class WeightedSumFit:
    """
    Fits E_target = α * E_bind + β * E_curv  (linear)
    and  log(E_target) = α' * log(E_bind) + β' * log(E_curv)  (log-additive / geometric)
    to find the best combination weights.
    """

    target: str  # what we're fitting against (e.g. "measured_hydrogen")
    # Linear fit
    alpha_lin: float
    beta_lin: float
    lin_rms: float
    # Log-additive fit
    alpha_log: float
    beta_log: float
    log_rms: float  # rms in log space
    log_rms_ev: float  # rms back in eV space
    # Which form wins?
    better_form: str  # "linear" or "log_additive"
    # Predictions
    linear_predictions: List[float]
    logadd_predictions: List[float]
    target_evs: List[float]

    def to_dict(self) -> dict:
        return {
            "schema_version": "geoseed_weighted_sum_v1",
            "target": self.target,
            "linear": {
                "formula": f"E = {self.alpha_lin:.4f}*E_bind + {self.beta_lin:.4f}*E_curv",
                "alpha": round(self.alpha_lin, 6),
                "beta": round(self.beta_lin, 6),
                "rms_ev": round(self.lin_rms, 6),
            },
            "log_additive": {
                "formula": (f"log(E) = {self.alpha_log:.4f}*log(E_bind) + " f"{self.beta_log:.4f}*log(E_curv)"),
                "alpha": round(self.alpha_log, 6),
                "beta": round(self.beta_log, 6),
                "rms_log": round(self.log_rms, 6),
                "rms_ev": round(self.log_rms_ev, 6),
            },
            "better_form": self.better_form,
            "shells": [
                {
                    "shell": i,
                    "tongue": ["KO", "AV", "RU", "CA", "UM", "DR"][i],
                    "target_ev": round(self.target_evs[i], 6),
                    "linear_pred_ev": round(self.linear_predictions[i], 6),
                    "logadd_pred_ev": round(self.logadd_predictions[i], 6),
                }
                for i in range(6)
            ],
        }


def weighted_sum_fit(target: str = "measured_hydrogen") -> WeightedSumFit:
    """
    Fit E_total = α·E_bind + β·E_curv  (Compton bind + GeoSeed LB curv)
    to the measured hydrogen energies.  Also fit log-additive form.

    This tests whether the decomposition is physically useful or just convenient.
    """
    from src.geoseed.theory_comparison import theory_compton_orbital, theory_geoseed_lb, HYDROGEN_MEASURED_EV

    bind_evs = theory_compton_orbital().energies_ev()
    curv_evs = theory_geoseed_lb().energies_ev()
    target_evs = HYDROGEN_MEASURED_EV

    # ── Linear fit: E = α*bind + β*curv ──────────────────────────────
    def lin_residual(params):
        alpha, beta = params
        total = sum((alpha * bind_evs[i] + beta * curv_evs[i] - target_evs[i]) ** 2 for i in range(6))
        return total / 6

    lin_params = _nelder_mead(lin_residual, [1.0, 0.0])
    al, bl = lin_params
    lin_rms = math.sqrt(lin_residual(lin_params))
    lin_preds = [al * bind_evs[i] + bl * curv_evs[i] for i in range(6)]

    # ── Log-additive fit: log(E) = α*log(Ebind) + β*log(Ecurv) ──────
    log_bind = [math.log(e) for e in bind_evs]
    log_curv = [math.log(e) for e in curv_evs]
    log_target = [math.log(e) for e in target_evs]

    def log_residual(params):
        alpha, beta = params
        total = sum((alpha * log_bind[i] + beta * log_curv[i] - log_target[i]) ** 2 for i in range(6))
        return total / 6

    log_params = _nelder_mead(log_residual, [0.5, 0.5])
    alo, blo = log_params
    log_rms = math.sqrt(log_residual(log_params))
    logadd_preds = [math.exp(alo * log_bind[i] + blo * log_curv[i]) for i in range(6)]
    log_rms_ev = math.sqrt(sum((logadd_preds[i] - target_evs[i]) ** 2 for i in range(6)) / 6)

    better = "linear" if lin_rms <= log_rms_ev else "log_additive"

    return WeightedSumFit(
        target=target,
        alpha_lin=al,
        beta_lin=bl,
        lin_rms=lin_rms,
        alpha_log=alo,
        beta_log=blo,
        log_rms=log_rms,
        log_rms_ev=log_rms_ev,
        better_form=better,
        linear_predictions=lin_preds,
        logadd_predictions=logadd_preds,
        target_evs=list(target_evs),
    )


# ── Extended report ───────────────────────────────────────────────────────────


def duality_report() -> str:
    """Full report: independent dual fit + product invariant + weighted sum."""
    dual = independent_dual_fit()
    inv = compute_product_invariant()
    ws = weighted_sum_fit()
    tongues = ["KO(s)", "AV(p)", "RU(d)", "CA(f)", "UM(g)", "DR(h)"]

    lines = []
    lines.append("=" * 72)
    lines.append("  INDEPENDENT DUAL FIT (free prefactors + exponents)")
    lines.append("  Binding fit against measured hydrogen; Curvature fit against GeoSeed-LB")
    lines.append("=" * 72)
    lines.append(
        f"  E_bind = {dual.bind_A:.4f} / (n + {dual.bind_delta:.4f})^{dual.bind_p:.4f}"
        f"   rms={dual.bind_rms:.6f}  p_near_2={dual.p_near_2}"
    )
    lines.append(
        f"  E_curv = {dual.curv_B:.4f} * (n + {dual.curv_delta:.4f})^{dual.curv_q:.4f}"
        f"   rms={dual.curv_rms:.6f}  q_near_2={dual.q_near_2}"
    )
    lines.append(f"  Product CV = {dual.product_cv:.6f}  (near 0 = flat invariant)")
    lines.append("")

    lines.append("=" * 72)
    lines.append("  PRODUCT INVARIANT  I(l) = E_bind(l) × E_curv(l)")
    lines.append("  Using Bohr (measured hydrogen) × GeoSeed-LB (same anchor)")
    lines.append("=" * 72)
    lines.append(f"  Rydberg² = {inv.rydberg_sq:.6f} eV²")
    lines.append(f"  Product mean = {inv.mean:.6f} eV²   std = {inv.std:.6f}   CV = {inv.cv:.2e}")
    lines.append(f"  Is flat (CV < 1e-6): {inv.is_flat}")
    lines.append("")
    lines.append(f"  {'Shell':<10}  {'E_bind':>12}  {'E_curv':>12}  {'I(l)':>14}  {'Δ from mean':>12}")
    lines.append("  " + "-" * 64)
    for i, t in enumerate(tongues):
        delta = (inv.shell_values[i] - inv.mean) / inv.mean * 100
        lines.append(
            f"  {t:<10}  {inv.bohr_evs[i]:>12.4f}  {inv.lb_evs[i]:>12.4f}"
            f"  {inv.shell_values[i]:>14.6f}  {delta:>+10.4f}%"
        )
    lines.append("")

    lines.append("=" * 72)
    lines.append("  WEIGHTED-SUM FIT  E_total = α·E_bind + β·E_curv")
    lines.append("  (fitting against measured hydrogen; bind=Compton, curv=GeoSeed-LB)")
    lines.append("=" * 72)
    lines.append(f"  Linear:      α={ws.alpha_lin:.6f}  β={ws.beta_lin:.6f}  rms={ws.lin_rms:.6f} eV")
    lines.append(f"  Log-additive: α={ws.alpha_log:.6f}  β={ws.beta_log:.6f}  " f"rms={ws.log_rms_ev:.6f} eV")
    lines.append(f"  Better form: {ws.better_form}")
    lines.append("")
    lines.append(f"  {'Shell':<10}  {'Target':>10}  {'Linear':>10}  {'LogAdd':>10}  " f"{'LinErr':>10}  {'LogErr':>10}")
    lines.append("  " + "-" * 64)
    for i, t in enumerate(tongues):
        lines.append(
            f"  {t:<10}  {ws.target_evs[i]:>10.4f}  {ws.linear_predictions[i]:>10.4f}"
            f"  {ws.logadd_predictions[i]:>10.4f}"
            f"  {ws.linear_predictions[i]-ws.target_evs[i]:>+10.4f}"
            f"  {ws.logadd_predictions[i]-ws.target_evs[i]:>+10.4f}"
        )
    lines.append("=" * 72)
    return "\n".join(lines)


def main():
    import json

    print(fit_report())
    print()
    print(duality_report())
    fits = fit_all_theories()
    cx = crossover_analysis()
    comb = combined_energy_model()
    dual = independent_dual_fit()
    inv = compute_product_invariant()
    ws = weighted_sum_fit()
    summary = {
        "schema_version": "geoseed_theory_fit_v1",
        "phi": PHI,
        "fits": {k: v.to_dict() for k, v in fits.items()},
        "crossover": cx.to_dict(),
        "combined_energy": comb.to_dict(),
        "dual_fit": dual.to_dict(),
        "product_invariant": inv.to_dict(),
        "weighted_sum": ws.to_dict(),
    }
    print()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
