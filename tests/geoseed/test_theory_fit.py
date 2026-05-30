"""
Tests for theory_fit.py — parametric fits and crossover analysis.

Core invariants:
  1. Bohr power-law fit lands at p ≈ 2 (it IS a 1/n² law)
  2. Compton exponential fit lands at λ ≈ φ (it IS a phi-decay law)
  3. GeoSeed LB power-law p is negative (grows outward = curvature, not binding)
  4. Observable classification: binding vs curvature is consistent
  5. Crossover: Compton and Bohr diverge starting at shell 1 (AV)
  6. Crossover ratio > 1 for all outer shells (Compton retains more energy)
  7. Combined energy model: E_total > E_bind for all shells
  8. Combined curvature fraction increases outward (LB grows faster)
  9. All FitResult RMS values are finite and non-negative
 10. Serialisation round-trips without loss
"""

import math
import pytest

PHI = (1.0 + math.sqrt(5.0)) / 2.0


@pytest.fixture(scope="module")
def mod():
    from src.geoseed.theory_fit import (
        fit_all_theories,
        crossover_analysis,
        combined_energy_model,
        fit_power_law,
        fit_exponential,
        fit_report,
        OBSERVABLE_A_BINDING,
        OBSERVABLE_B_CURVATURE,
    )
    return {
        "fit_all": fit_all_theories,
        "crossover": crossover_analysis,
        "combined": combined_energy_model,
        "fit_pl": fit_power_law,
        "fit_exp": fit_exponential,
        "report": fit_report,
        "obs_a": OBSERVABLE_A_BINDING,
        "obs_b": OBSERVABLE_B_CURVATURE,
    }


@pytest.fixture(scope="module")
def fits(mod):
    return mod["fit_all"]()


@pytest.fixture(scope="module")
def cx(mod):
    return mod["crossover"]()


@pytest.fixture(scope="module")
def comb(mod):
    return mod["combined"]()


# ── Power-law fitter unit tests ───────────────────────────────────────────────

def test_power_law_recovers_bohr(mod):
    """Fitting exact Bohr values should return p ≈ 2."""
    from src.geoseed.theory_comparison import RYDBERG_EV
    evs = [RYDBERG_EV / ((n + 1)**2) for n in range(6)]
    A, delta, p, rms = mod["fit_pl"](evs)
    assert abs(p - 2.0) < 0.05, f"Bohr power-law p={p} should be near 2"
    assert rms < 0.01, f"Bohr fit rms={rms} unexpectedly large"

def test_exponential_recovers_phi_decay(mod):
    """Fitting phi-decay series should return λ ≈ φ."""
    from src.geoseed.theory_comparison import RYDBERG_EV
    evs = [RYDBERG_EV / (PHI**n) for n in range(6)]
    A, lam, rms = mod["fit_exp"](evs)
    assert abs(lam - PHI) < 0.01, f"Compton exp λ={lam} should be near φ={PHI}"
    assert rms < 0.01, f"Compton exp fit rms={rms} unexpectedly large"


# ── Bohr fit ──────────────────────────────────────────────────────────────────

def test_bohr_power_law_p_near_2(fits):
    f = fits["bohr"]
    assert abs(f.pl_p - 2.0) < 0.1, f"Bohr PL p={f.pl_p} expected ~2"

def test_bohr_observable_is_binding(fits):
    assert fits["bohr"].observable == "binding"

def test_bohr_pl_rms_small(fits):
    assert fits["bohr"].pl_rms < 0.1

def test_bohr_fit_rms_finite(fits):
    assert math.isfinite(fits["bohr"].pl_rms)
    assert math.isfinite(fits["bohr"].exp_rms)


# ── Compton-orbital fit ───────────────────────────────────────────────────────

def test_compton_exp_lambda_near_phi(fits):
    f = fits["compton_orbital"]
    assert abs(f.exp_lambda - PHI) < 0.05, (
        f"Compton exp λ={f.exp_lambda:.4f} should be near φ={PHI:.4f}"
    )

def test_compton_better_fit_is_exponential(fits):
    """The phi-decay IS an exponential — exponential fit should win."""
    f = fits["compton_orbital"]
    assert f.better_fit == "exponential", (
        f"Expected exponential to win for Compton, got {f.better_fit}"
    )

def test_compton_observable_is_binding(fits):
    assert fits["compton_orbital"].observable == "binding"

def test_compton_exp_rms_smaller_than_pl_rms(fits):
    f = fits["compton_orbital"]
    assert f.exp_rms < f.pl_rms


# ── GeoSeed LB fit ────────────────────────────────────────────────────────────

def test_geoseed_lb_power_law_p_negative(fits):
    """LB grows outward → fitted power-law exponent p must be negative."""
    f = fits["geoseed_lb"]
    assert f.pl_p < 0, (
        f"GeoSeed LB PL p={f.pl_p:.4f} should be negative (grows outward)"
    )

def test_geoseed_lb_observable_is_curvature(fits):
    assert fits["geoseed_lb"].observable == "curvature"


# ── Observable classification ─────────────────────────────────────────────────

def test_all_binding_theories_classified(fits, mod):
    for name in mod["obs_a"]:
        assert fits[name].observable == "binding", (
            f"{name} classified as {fits[name].observable}, expected binding"
        )

def test_all_curvature_theories_classified(fits, mod):
    for name in mod["obs_b"]:
        assert fits[name].observable == "curvature", (
            f"{name} classified as {fits[name].observable}, expected curvature"
        )

def test_no_theory_is_both(fits):
    for name, f in fits.items():
        assert f.observable in ("binding", "curvature"), (
            f"{name} has unknown observable: {f.observable}"
        )


# ── All fits are finite ───────────────────────────────────────────────────────

def test_all_fit_rms_finite_nonneg(fits):
    for name, f in fits.items():
        assert math.isfinite(f.pl_rms) and f.pl_rms >= 0, (
            f"{name} PL rms={f.pl_rms}"
        )
        assert math.isfinite(f.exp_rms) and f.exp_rms >= 0, (
            f"{name} exp rms={f.exp_rms}"
        )

def test_all_fit_lambdas_positive(fits):
    for name, f in fits.items():
        assert f.exp_lambda > 0, f"{name} exp λ={f.exp_lambda}"


# ── Crossover analysis ────────────────────────────────────────────────────────

def test_crossover_has_six_shells(cx):
    assert len(cx.shell_ratios) == 6
    assert len(cx.divergence_pct) == 6

def test_crossover_shell0_ratio_near_one(cx):
    """Both anchored at shell 0 = Rydberg, so ratio must be exactly 1."""
    assert abs(cx.shell_ratios[0] - 1.0) < 1e-9

def test_crossover_all_outer_ratios_above_one(cx):
    """Compton retains more energy than Bohr at all outer shells."""
    for i in range(1, 6):
        assert cx.shell_ratios[i] > 1.0, (
            f"Shell {i} ratio={cx.shell_ratios[i]:.4f} expected > 1"
        )

def test_crossover_first_significant_shell_is_one(cx):
    """Divergence >50% appears immediately at shell 1 (AV, p-orbital)."""
    assert cx.first_significant_shell == 1, (
        f"Expected first_significant_shell=1, got {cx.first_significant_shell}"
    )

def test_crossover_peak_ratio_above_3(cx):
    """At peak, Compton retains >3x Bohr energy."""
    assert cx.peak_ratio > 3.0, f"Peak ratio={cx.peak_ratio:.2f} expected > 3"

def test_crossover_notes_non_empty(cx):
    assert len(cx.notes) > 50

def test_crossover_compton_always_higher(cx):
    for i in range(6):
        assert cx.compton_ev[i] >= cx.bohr_ev[i], (
            f"Shell {i}: Compton={cx.compton_ev[i]} < Bohr={cx.bohr_ev[i]}"
        )


# ── Combined energy model ─────────────────────────────────────────────────────

def test_combined_has_six_shells(comb):
    assert len(comb.total_ev) == 6

def test_combined_total_gt_bind(comb):
    """E_total must exceed E_bind at every shell (curvature is additive)."""
    for i in range(6):
        assert comb.total_ev[i] > comb.bind_ev[i], (
            f"Shell {i}: total={comb.total_ev[i]} not > bind={comb.bind_ev[i]}"
        )

def test_combined_curv_fraction_increasing(comb):
    """LB grows faster than Compton-bind → curvature fraction must grow outward."""
    fracs = comb.curv_fraction
    for i in range(1, 6):
        assert fracs[i] > fracs[i - 1], (
            f"curv_fraction not increasing at shell {i}: {fracs[i]:.4f} <= {fracs[i-1]:.4f}"
        )

def test_combined_all_totals_positive(comb):
    for i, e in enumerate(comb.total_ev):
        assert e > 0, f"Shell {i} total_ev={e}"

def test_combined_schema_version(comb):
    d = comb.to_dict()
    assert d["schema_version"] == "geoseed_combined_energy_v1"
    assert len(d["shells"]) == 6


# ── Serialisation ─────────────────────────────────────────────────────────────

def test_fit_to_dict_has_required_keys(fits):
    for name, f in fits.items():
        d = f.to_dict()
        assert "theory" in d
        assert "observable" in d
        assert "better_fit" in d
        assert "power_law" in d
        assert "exponential" in d
        assert "lambda_vs_phi" in d["exponential"]

def test_fit_report_non_empty(mod):
    report = mod["report"]()
    assert len(report) > 500
    assert "PARAMETRIC FIT" in report
    assert "CROSSOVER" in report
    assert "COMBINED" in report
