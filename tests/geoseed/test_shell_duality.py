"""
Tests for shell_duality.py — reciprocal dual-law structure.

Core invariants under test:
  1. I(k) = A² exactly for all shells (algebraic identity)
  2. Geometric center = A = Rydberg for all shells
  3. Coupling ratio = 1/k^4 for all shells
  4. At KO (k=1): bind = curv = A  (perfectly balanced)
  5. Angle at KO = 45°; grows monotonically outward toward 90°
  6. Binding fraction falls outward; curvature fraction rises
  7. Baseline perturbation: invariant flat, exponents near 2
  8. Rescaled anchor: invariant flat (different A², same structure)
  9. Non-hydrogen anchor: structure preserved
 10. Noisy k: invariant approximately flat (CV < 0.05)
 11. ShellStateField: balance point at KO, crossover at KO
 12. Hyperbola constant = A²
 13. Serialisation round-trips cleanly
"""

import math
import pytest

PHI = (1.0 + math.sqrt(5.0)) / 2.0


@pytest.fixture(scope="module")
def rydberg():
    from src.geoseed.theory_comparison import RYDBERG_EV

    return RYDBERG_EV


@pytest.fixture(scope="module")
def dual(rydberg):
    from src.geoseed.shell_duality import build_shell_duality

    return build_shell_duality()


@pytest.fixture(scope="module")
def field_obj(dual):
    from src.geoseed.shell_duality import ShellStateField

    return ShellStateField(dual)


@pytest.fixture(scope="module")
def pert():
    from src.geoseed.shell_duality import run_perturbation_tests

    return run_perturbation_tests()


# ── ShellDuality invariant ────────────────────────────────────────────────────


def test_invariant_equals_a_squared(dual, rydberg):
    """I(k) = A² exactly for all shells."""
    a2 = rydberg**2
    for k in range(1, 7):
        assert abs(dual.invariant(k) - a2) < 1e-9, f"k={k}: I={dual.invariant(k):.9f} ≠ A²={a2:.9f}"


def test_invariant_cv_zero(dual):
    """Product must be perfectly flat."""
    assert dual.invariant_cv() < 1e-12


def test_is_invariant_flat(dual):
    assert dual.is_invariant_flat()


def test_geometric_center_equals_rydberg(dual, rydberg):
    """GM(k) = sqrt(I(k)) = A = Rydberg for all shells."""
    for k in range(1, 7):
        gm = dual.geometric_center(k)
        assert abs(gm - rydberg) < 1e-9, f"k={k}: geometric_center={gm:.9f} ≠ Rydberg={rydberg:.9f}"


def test_coupling_ratio_is_one_over_k4(dual):
    """R(k) = E_bind/E_curv = 1/k^4."""
    for k in range(1, 7):
        expected = 1.0 / (k**4)
        actual = dual.coupling_ratio(k)
        assert abs(actual - expected) < 1e-12, f"k={k}: ratio={actual:.12f} ≠ 1/k^4={expected:.12f}"


# ── Shell balance ─────────────────────────────────────────────────────────────


def test_ko_shell_is_balanced(dual, rydberg):
    """At KO (k=1): E_bind = E_curv = A."""
    assert abs(dual.bind(1) - rydberg) < 1e-9
    assert abs(dual.curv(1) - rydberg) < 1e-9


def test_outer_shells_curv_dominates(dual):
    """For k > 1, curvature must exceed binding."""
    for k in range(2, 7):
        assert dual.curv(k) > dual.bind(k), f"k={k}: curv={dual.curv(k):.4f} not > bind={dual.bind(k):.4f}"


def test_bind_monotone_decreasing(dual):
    """Binding falls outward."""
    for k in range(1, 6):
        assert dual.bind(k) > dual.bind(k + 1)


def test_curv_monotone_increasing(dual):
    """Curvature rises outward."""
    for k in range(1, 6):
        assert dual.curv(k) < dual.curv(k + 1)


# ── Shell state angles ────────────────────────────────────────────────────────


def test_ko_angle_is_45_deg(dual):
    """At KO (k=1): bind=curv → angle = 45°."""
    angle = math.degrees(dual.relation_angle(1))
    assert abs(angle - 45.0) < 1e-6, f"KO angle={angle:.6f}° ≠ 45°"


def test_angles_monotone_increasing(dual):
    """Shell angle grows outward as curvature dominates."""
    angles = [math.degrees(dual.relation_angle(k)) for k in range(1, 7)]
    for i in range(1, 6):
        assert angles[i] > angles[i - 1], f"angle not increasing at k={i + 1}: {angles[i]:.2f} <= {angles[i - 1]:.2f}"


def test_angles_approach_90(dual):
    """DR shell (k=6) should be near 90°."""
    angle = math.degrees(dual.relation_angle(6))
    assert angle > 85.0, f"DR angle={angle:.2f}° should be near 90°"


# ── Bind/curv fractions ───────────────────────────────────────────────────────


def test_ko_fractions_equal(dual):
    """At KO: bind_fraction = curv_fraction = 0.5."""
    assert abs(dual.bind_fraction(1) - 0.5) < 1e-9
    assert abs(dual.curv_fraction(1) - 0.5) < 1e-9


def test_bind_fraction_decreases_outward(dual):
    for k in range(1, 6):
        assert dual.bind_fraction(k) > dual.bind_fraction(k + 1)


def test_curv_fraction_increases_outward(dual):
    for k in range(1, 6):
        assert dual.curv_fraction(k) < dual.curv_fraction(k + 1)


def test_fractions_sum_to_one(dual):
    for k in range(1, 7):
        total = dual.bind_fraction(k) + dual.curv_fraction(k)
        assert abs(total - 1.0) < 1e-12


# ── Perturbation tests ────────────────────────────────────────────────────────


def test_pert_has_seven_scenarios(pert):
    assert len(pert.scenarios) == 7


def test_pert_exact_baseline_flat(pert):
    base = next(s for s in pert.scenarios if s.name == "exact_baseline")
    assert base.invariant_cv < 1e-9


def test_pert_rescaled_anchor_flat(pert):
    """Rescaling A still gives a flat invariant (different A², same structure)."""
    s = next(s for s in pert.scenarios if s.name == "rescaled_anchor")
    assert s.invariant_survived, f"rescaled_anchor CV={s.invariant_cv:.6f}"


def test_pert_non_hydrogen_anchor_flat(pert):
    s = next(s for s in pert.scenarios if s.name == "non_hydrogen_anchor")
    assert s.invariant_survived, f"non_hydrogen_anchor CV={s.invariant_cv:.6f}"


def test_pert_noisy_k_approximately_flat(pert):
    """Gaussian noise σ=0.1 on k should keep CV < 0.05."""
    s = next(s for s in pert.scenarios if s.name == "noisy_k_sigma01")
    assert s.invariant_cv < 0.05, f"noisy_k CV={s.invariant_cv:.4f}"


def test_pert_offset_indexing_flat(pert):
    s = next(s for s in pert.scenarios if s.name == "offset_indexing")
    assert s.invariant_survived


def test_pert_half_integer_flat(pert):
    s = next(s for s in pert.scenarios if s.name == "half_integer_k")
    assert s.invariant_survived


def test_pert_large_anchor_flat(pert):
    s = next(s for s in pert.scenarios if s.name == "large_anchor")
    assert s.invariant_survived


def test_pert_baseline_exponents_near_2(pert):
    base = next(s for s in pert.scenarios if s.name == "exact_baseline")
    assert base.exponents_survived, f"p={base.bind_exponent:.3f}, q={base.curv_exponent:.3f} — not near 2"


def test_pert_to_dict(pert):
    d = pert.to_dict()
    assert d["schema_version"] == "geoseed_perturbation_test_v1"
    assert len(d["scenarios"]) == 7


# ── ShellStateField ───────────────────────────────────────────────────────────


def test_field_balance_at_ko(field_obj):
    """Balance point must be at KO (k=1)."""
    bal_k, diff = field_obj.balance_point()
    assert bal_k == 1, f"Balance at k={bal_k}, expected k=1"
    assert diff < 1e-9


def test_field_crossover_at_ko(field_obj):
    """Exact crossover (bind=curv) happens at k=1."""
    cx_k, cx_e = field_obj.crossover_shell()
    assert cx_k == 1


def test_field_hyperbola_constant_equals_a_sq(field_obj, rydberg):
    assert abs(field_obj.hyperbola_constant() - rydberg**2) < 1e-9


def test_field_all_outer_shells_curv_dominant(field_obj):
    states = field_obj.states()
    for i in range(1, 6):
        bind, curv = states[i]
        assert curv > bind, f"Shell {i + 1} not curv-dominant: bind={bind}, curv={curv}"


def test_field_to_dict(field_obj, rydberg):
    d = field_obj.to_dict()
    assert d["schema_version"] == "geoseed_shell_state_field_v1"
    assert abs(d["hyperbola_constant_ev2"] - rydberg**2) < 1e-6
    assert d["balance_shell_k"] == 1
    assert len(d["trajectory"]) == 6


# ── Custom anchor ─────────────────────────────────────────────────────────────


def test_custom_anchor_preserves_structure():
    """The dual structure works for any positive anchor A."""
    from src.geoseed.shell_duality import build_shell_duality

    for A in [1.0, 5.5, 100.0, 0.01]:
        d = build_shell_duality(anchor_ev=A)
        for k in range(1, 7):
            assert abs(d.invariant(k) - A**2) < 1e-9, f"A={A}, k={k}: I={d.invariant(k):.9f} ≠ A²={A**2:.9f}"


def test_custom_anchor_geometric_center_equals_a():
    from src.geoseed.shell_duality import build_shell_duality

    A = 7.77
    d = build_shell_duality(anchor_ev=A)
    for k in range(1, 7):
        gm = d.geometric_center(k)
        assert abs(gm - A) < 1e-9


# ── Serialisation ─────────────────────────────────────────────────────────────


def test_dual_to_dict_schema(dual):
    d = dual.to_dict()
    assert d["schema_version"] == "geoseed_shell_duality_v1"
    assert d["is_invariant_flat"] is True
    assert len(d["shells"]) == 6


def test_dual_to_dict_ko_balanced(dual):
    d = dual.to_dict()
    ko = d["shells"][0]
    assert ko["k"] == 1 and ko["tongue"] == "KO"
    assert abs(ko["bind_ev"] - ko["curv_ev"]) < 1e-9
    assert abs(ko["relation_angle_deg"] - 45.0) < 1e-4


def test_duality_field_report_non_empty():
    from src.geoseed.shell_duality import duality_field_report

    report = duality_field_report()
    assert len(report) > 400
    assert "SHELL DUALITY FIELD" in report
    assert "PERTURBATION TEST" in report
    assert "geometric_center" in report or "Geometric center" in report


# ── RelationTerm ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def rel():
    from src.geoseed.shell_duality import build_relation_term

    return build_relation_term()


def test_rel_ko_coupling_is_one(rel):
    """At KO (k=1): ρ = 1²/φ⁰ = 1 exactly — ground-state resonance."""
    rho = rel.coupling_ratio(1)
    assert abs(rho - 1.0) < 1e-12, f"KO coupling ρ={rho} ≠ 1"


def test_rel_compton_ko_equals_rydberg(rel, rydberg):
    """KO Compton energy = A/φ⁰ = A = Rydberg."""
    assert abs(rel.compton_ev(1) - rydberg) < 1e-9


def test_rel_compton_phi_scaling(rel, rydberg):
    """Each successive Compton shell is 1/φ of the previous."""
    for k in range(1, 6):
        ratio = rel.compton_ev(k) / rel.compton_ev(k + 1)
        assert abs(ratio - PHI) < 1e-9, f"Compton k={k}→{k + 1} ratio {ratio} ≠ φ"


def test_rel_coupling_formula(rel):
    """ρ(k) = k²/φ^(k-1) exactly."""
    for k in range(1, 7):
        expected = (k * k) / (PHI ** (k - 1))
        actual = rel.coupling_ratio(k)
        assert abs(actual - expected) < 1e-12, f"k={k}: ρ={actual:.12f} ≠ k²/φ^(k-1)={expected:.12f}"


def test_rel_resonance_shell_is_ko(rel):
    """Ground state (k=1) is the resonance shell where ρ is closest to 1."""
    res_k, dev = rel.resonance_shell()
    assert res_k == 1, f"Resonance shell expected k=1, got k={res_k}"
    assert dev < 1e-12


def test_rel_peak_coupling_shell_is_4(rel):
    """Peak coupling (max ρ) is at k=4 (CA, f-orbital)."""
    peak_k, peak_rho = rel.peak_coupling_shell()
    assert peak_k == 4, f"Peak coupling expected k=4, got k={peak_k}"
    assert peak_rho > 3.5, f"Peak ρ={peak_rho} unexpectedly low"


def test_rel_peak_coupling_above_3(rel):
    """The peak coupling ratio must exceed 3 (crossover analysis agrees)."""
    _, peak_rho = rel.peak_coupling_shell()
    assert peak_rho > 3.0, f"Peak ρ={peak_rho:.4f}"


def test_rel_all_outer_coupling_above_one(rel):
    """For k > 1, Compton always exceeds the dual-law bind (ρ > 1)."""
    for k in range(2, 7):
        assert rel.coupling_ratio(k) > 1.0, f"k={k}: coupling ρ={rel.coupling_ratio(k):.4f} ≤ 1"


def test_rel_phase_angles_positive(rel):
    """All phase angles must be in (0°, 90°)."""
    for k in range(1, 7):
        angle = rel.phase_angle_deg(k)
        assert 0.0 < angle < 90.0, f"k={k}: phase={angle:.2f}°"


def test_rel_ko_phase_is_45(rel):
    """At KO (k=1): bind=compton → angle = 45°."""
    angle = rel.phase_angle_deg(1)
    assert abs(angle - 45.0) < 1e-6, f"KO phase={angle:.6f}° ≠ 45°"


def test_rel_to_dict_schema(rel):
    d = rel.to_dict()
    assert d["schema_version"] == "geoseed_relation_term_v1"
    assert d["resonance_shell_k"] == 1
    assert d["peak_coupling_shell_k"] == 4
    assert len(d["shells"]) == 6


def test_rel_to_dict_ko_deviation_zero(rel):
    d = rel.to_dict()
    ko = d["shells"][0]
    assert ko["k"] == 1
    assert abs(ko["coupling_rho"] - 1.0) < 1e-9
    assert abs(ko["deviation"]) < 1e-9


# ── Clean API ─────────────────────────────────────────────────────────────────


def test_compute_invariant_returns_product():
    from src.geoseed.shell_duality import compute_invariant

    assert abs(compute_invariant(5.0, 20.0) - 100.0) < 1e-12


def test_compute_invariant_rydberg_shells(rydberg):
    from src.geoseed.shell_duality import compute_invariant, shell_state_at

    for k in range(1, 7):
        b, c = shell_state_at(k)
        inv = compute_invariant(b, c)
        assert abs(inv - rydberg**2) < 1e-9, f"k={k}: compute_invariant={inv:.9f} ≠ Rydberg²"


def test_shell_state_at_ko_balanced(rydberg):
    from src.geoseed.shell_duality import shell_state_at

    b, c = shell_state_at(1)
    assert abs(b - rydberg) < 1e-9
    assert abs(c - rydberg) < 1e-9


def test_fit_binding_law_recovers_p2(rydberg):
    from src.geoseed.shell_duality import fit_binding_law

    shells = [float(k) for k in range(1, 7)]
    values = [rydberg / (k * k) for k in range(1, 7)]
    A, delta, p, rms = fit_binding_law(shells, values)
    assert abs(p - 2.0) < 0.05, f"fit_binding_law p={p:.4f} ≠ 2"
    assert rms < 0.01


def test_perturbation_sweep_returns_7(rydberg):
    from src.geoseed.shell_duality import perturbation_sweep

    pt = perturbation_sweep(seed=0)
    assert len(pt.scenarios) == 7
    assert pt.all_survived()


# ── export_duality_artifact ───────────────────────────────────────────────────


def test_export_artifact_creates_file(tmp_path, rydberg):
    from src.geoseed.shell_duality import export_duality_artifact
    import json

    out = str(tmp_path)
    path = export_duality_artifact(out_dir=out)
    assert path.endswith(".json")
    import os

    assert os.path.isfile(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["schema_version"] == "geoseed_shell_duality_artifact_v1"
    assert data["summary"]["is_invariant_flat"] is True
    assert data["summary"]["all_perturbations_survived"] is True
    assert abs(data["summary"]["A_squared_ev2"] - rydberg**2) < 1e-6
    assert data["summary"]["resonance_shell_k"] == 1
    assert data["summary"]["peak_coupling_shell_k"] == 4
    # all four sections present
    for key in ("duality", "field", "perturbation", "relation"):
        assert key in data, f"Missing section: {key}"
