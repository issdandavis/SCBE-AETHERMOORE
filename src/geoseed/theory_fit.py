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

def _nelder_mead(f, x0: List[float], tol: float = 1e-9,
                 max_iter: int = 5000) -> List[float]:
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
        simplex = [best] + [
            [best[j] + delta * (simplex[i][j] - best[j]) for j in range(n)]
            for i in range(1, n + 1)
        ]
        scores = [score(pt) for pt in simplex]

    return simplex[0]


# ── Fit functions ─────────────────────────────────────────────────────────────

def _power_law(n: int, A: float, delta: float, p: float) -> float:
    """E = A / (n + delta)^p"""
    base = n + delta
    if base <= 0:
        return float("inf")
    return A / (base ** p)


def _exponential(n: int, A: float, lam: float) -> float:
    """E = A * lambda^{-n}"""
    if lam <= 0:
        return float("inf")
    return A * (lam ** (-n))


def fit_power_law(energies: List[float], ns: Optional[List[int]] = None
                  ) -> Tuple[float, float, float, float]:
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


def fit_exponential(energies: List[float], ns: Optional[List[int]] = None
                    ) -> Tuple[float, float, float]:
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
    better_fit: str   # "power_law" or "exponential"
    observable: str   # "binding" or "curvature"
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
            pl_A=pl_A, pl_delta=pl_delta, pl_p=pl_p, pl_rms=pl_rms,
            exp_A=exp_A, exp_lambda=exp_lam, exp_rms=exp_rms,
            better_fit=better,
            observable=obs,
            notes=" | ".join(notes_parts),
        )

    return fit_results


# ── Crossover analysis ────────────────────────────────────────────────────────

@dataclass
class CrossoverAnalysis:
    """Where Bohr and Compton-orbital diverge from the same anchor point."""
    shell_ratios: List[float]        # compton_ev[n] / bohr_ev[n] per shell
    divergence_pct: List[float]      # (compton - bohr) / bohr * 100
    first_significant_shell: int     # first shell where |ratio - 1| > 0.5 (50%)
    peak_divergence_shell: int       # shell with maximum ratio
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
    from src.geoseed.theory_comparison import (
        theory_compton_orbital, theory_bohr
    )

    compton = theory_compton_orbital()
    bohr = theory_bohr()

    c_evs = compton.energies_ev()
    b_evs = bohr.energies_ev()

    ratios = [c / b for c, b in zip(c_evs, b_evs)]
    div_pct = [(r - 1.0) * 100 for r in ratios]

    first_sig = next(
        (i for i, r in enumerate(ratios) if abs(r - 1.0) > 0.5),
        len(ratios) - 1
    )
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
    bind_ev: List[float]      # Compton-orbital
    curv_ev: List[float]      # GeoSeed-LB
    total_ev: List[float]     # sum
    bohr_ev: List[float]      # reference
    curv_fraction: List[float]  # E_curv / E_total per shell

    def to_dict(self) -> dict:
        tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
        return {
            "schema_version": "geoseed_combined_energy_v1",
            "description": "E_total = E_bind(Compton) + E_curv(GeoSeed-LB)",
            "shells": [
                {
                    "shell": i, "tongue": tongues[i],
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
    from src.geoseed.theory_comparison import (
        theory_compton_orbital, theory_geoseed_lb, theory_bohr,
        RYDBERG_EV
    )

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
    lines.append(
        f"  {'Shell':<10}  {'E_bind':<12}  {'E_curv':<12}  "
        f"{'E_total':<12}  {'E_Bohr':<12}  {'curv%':<8}"
    )
    lines.append("  " + "-" * 68)
    for i, t in enumerate(tongues):
        lines.append(
            f"  {t:<10}  {comb.bind_ev[i]:>12.4f}  {comb.curv_ev[i]:>12.4f}  "
            f"{comb.total_ev[i]:>12.4f}  {comb.bohr_ev[i]:>12.4f}  "
            f"{comb.curv_fraction[i]*100:>6.1f}%"
        )
    lines.append("=" * 72)
    return "\n".join(lines)


def main():
    import json
    print(fit_report())
    fits = fit_all_theories()
    cx = crossover_analysis()
    comb = combined_energy_model()
    summary = {
        "schema_version": "geoseed_theory_fit_v1",
        "phi": PHI,
        "fits": {k: v.to_dict() for k, v in fits.items()},
        "crossover": cx.to_dict(),
        "combined_energy": comb.to_dict(),
    }
    print()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
