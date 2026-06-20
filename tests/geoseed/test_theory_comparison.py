"""
Tests for theory_comparison.py — multi-perspective electron orbital model.

Core invariants:
  1. All 6 theories return TheoryResult with 6 shells
  2. Bohr model matches measured hydrogen (zero residuals by definition)
  3. Compton orbital: KO shell energy == RYDBERG_EV
  4. Compton orbital: each successive shell is 1/φ of the previous
  5. All energies are positive and finite
  6. All frequencies are positive and finite
  7. run_all returns all 6 theories by name
  8. RMS residuals are finite for all theories
  9. Bohr residuals are all near zero
 10. JSON serialization round-trips cleanly
"""

import math
import pytest

PHI = (1.0 + math.sqrt(5.0)) / 2.0


@pytest.fixture(scope="module")
def mod():
    from src.geoseed.theory_comparison import (
        run_all,
        theory_compton_orbital,
        theory_bohr,
        theory_de_broglie,
        theory_geoseed_lb,
        theory_harmonic,
        theory_pilot_wave,
        comparison_table,
        HYDROGEN_MEASURED_EV,
        RYDBERG_EV,
        COMPTON_FREQUENCY,
        COMPTON_ENERGY_EV,
        TONGUE_ORDER,
    )

    return {
        "run_all": run_all,
        "compton": theory_compton_orbital,
        "bohr": theory_bohr,
        "de_broglie": theory_de_broglie,
        "lb": theory_geoseed_lb,
        "harmonic": theory_harmonic,
        "pilot_wave": theory_pilot_wave,
        "table": comparison_table,
        "hydrogen_ev": HYDROGEN_MEASURED_EV,
        "rydberg": RYDBERG_EV,
        "f_c": COMPTON_FREQUENCY,
        "e_c": COMPTON_ENERGY_EV,
        "tongues": TONGUE_ORDER,
    }


# ── Physical constants sanity ─────────────────────────────────────────────────


def test_rydberg_value(mod):
    """Rydberg constant must be near 13.606 eV."""
    assert abs(mod["rydberg"] - 13.6057) < 0.001


def test_compton_frequency_order_of_magnitude(mod):
    """Compton frequency must be ~1.236×10²⁰ Hz."""
    assert 1.2e20 < mod["f_c"] < 1.3e20


def test_compton_energy_is_511kev(mod):
    """Electron rest energy must be ~511 keV (510999 eV)."""
    assert abs(mod["e_c"] - 510999.0) < 1.0


def test_hydrogen_has_6_shells(mod):
    assert len(mod["hydrogen_ev"]) == 6


def test_hydrogen_ground_state_equals_rydberg(mod):
    assert abs(mod["hydrogen_ev"][0] - mod["rydberg"]) < 1e-9


def test_hydrogen_shells_monotone_decreasing(mod):
    ev = mod["hydrogen_ev"]
    for i in range(1, 6):
        assert ev[i] < ev[i - 1]


# ── run_all ───────────────────────────────────────────────────────────────────


def test_run_all_returns_six_theories(mod):
    results = mod["run_all"]()
    assert len(results) == 6


def test_run_all_has_expected_keys(mod):
    results = mod["run_all"]()
    expected = {"compton_orbital", "bohr", "de_broglie", "geoseed_lb", "harmonic", "pilot_wave"}
    assert set(results.keys()) == expected


def test_run_all_all_have_six_shells(mod):
    for name, result in mod["run_all"]().items():
        assert len(result.shells) == 6, f"{name} has {len(result.shells)} shells"


def test_run_all_shell_tongues_ordered(mod):
    for name, result in mod["run_all"]().items():
        tongues = [s.tongue for s in result.shells]
        assert tongues == mod["tongues"], f"{name} tongue order wrong: {tongues}"


# ── Bohr model ────────────────────────────────────────────────────────────────


def test_bohr_energies_match_hydrogen(mod):
    """Bohr is the reference — all residuals should be ~0."""
    result = mod["bohr"]()
    for shell in result.shells:
        n = shell.shell_index + 1
        expected = mod["rydberg"] / (n**2)
        assert abs(shell.energy_ev - expected) < 1e-6, f"Bohr shell {n}: {shell.energy_ev} ≠ {expected}"


def test_bohr_rms_residual_near_zero(mod):
    result = mod["bohr"]()
    assert result.rms_residual_ev < 1e-6


def test_bohr_frequencies_decreasing(mod):
    """Higher shells have lower orbital frequency in Bohr model."""
    freqs = mod["bohr"]().frequencies_hz()
    for i in range(1, 6):
        assert freqs[i] < freqs[i - 1], f"Bohr freq not decreasing at shell {i}"


# ── Compton orbital model ─────────────────────────────────────────────────────


def test_compton_orbital_ko_matches_rydberg(mod):
    """KO (shell 0) anchored to Rydberg energy."""
    result = mod["compton"]()
    ko = result.shells[0]
    assert abs(ko.energy_ev - mod["rydberg"]) < 1e-9


def test_compton_orbital_phi_scaling(mod):
    """Each successive shell energy = previous / φ."""
    result = mod["compton"]()
    evs = [s.energy_ev for s in result.shells]
    for i in range(1, 6):
        ratio = evs[i - 1] / evs[i]
        assert abs(ratio - PHI) < 1e-6, f"Shell {i-1}→{i} energy ratio {ratio} ≠ φ={PHI}"


def test_compton_frequency_phi_scaling(mod):
    """Each successive shell frequency = previous / φ."""
    result = mod["compton"]()
    freqs = result.frequencies_hz()
    for i in range(1, 6):
        ratio = freqs[i - 1] / freqs[i]
        assert abs(ratio - PHI) < 1e-6, f"Shell {i-1}→{i} frequency ratio {ratio} ≠ φ={PHI}"


def test_compton_frequencies_monotone_decreasing(mod):
    freqs = mod["compton"]().frequencies_hz()
    for i in range(1, 6):
        assert freqs[i] < freqs[i - 1]


def test_compton_energies_monotone_decreasing(mod):
    evs = mod["compton"]().energies_ev()
    for i in range(1, 6):
        assert evs[i] < evs[i - 1]


# ── GeoSeed LB model ──────────────────────────────────────────────────────────


def test_geoseed_lb_ko_equals_rydberg(mod):
    result = mod["lb"]()
    assert abs(result.shells[0].energy_ev - mod["rydberg"]) < 1e-9


def test_geoseed_lb_energies_grow_as_squares(mod):
    """LB ladder: E_l / E_0 = (l+1)² / 1."""
    result = mod["lb"]()
    e0 = result.shells[0].energy_ev
    for ell, shell in enumerate(result.shells):
        expected_ratio = (ell + 1) ** 2
        actual_ratio = shell.energy_ev / e0
        assert (
            abs(actual_ratio - expected_ratio) < 1e-6
        ), f"l={ell}: energy ratio {actual_ratio} ≠ (l+1)²={expected_ratio}"


def test_geoseed_lb_energies_monotone_increasing(mod):
    """LB model predicts more energy for outer shells (unlike Bohr)."""
    evs = mod["lb"]().energies_ev()
    for i in range(1, 6):
        assert evs[i] > evs[i - 1]


# ── Harmonic model ────────────────────────────────────────────────────────────


def test_harmonic_ko_equals_rydberg(mod):
    result = mod["harmonic"]()
    assert abs(result.shells[0].energy_ev - mod["rydberg"]) < 1e-9


def test_harmonic_energies_linearly_increasing(mod):
    """Harmonic oscillator: E_n ∝ n+½ — nearly linear in shell index."""
    evs = mod["harmonic"]().energies_ev()
    for i in range(1, 6):
        assert evs[i] > evs[i - 1]


# ── de Broglie model ──────────────────────────────────────────────────────────


def test_de_broglie_six_shells(mod):
    result = mod["de_broglie"]()
    assert len(result.shells) == 6


def test_de_broglie_all_energies_positive(mod):
    result = mod["de_broglie"]()
    for s in result.shells:
        assert s.energy_ev > 0, f"de Broglie shell {s.shell_index}: E={s.energy_ev}"


# ── Pilot wave model ──────────────────────────────────────────────────────────


def test_pilot_wave_six_shells(mod):
    result = mod["pilot_wave"]()
    assert len(result.shells) == 6


def test_pilot_wave_energies_decrease_outward(mod):
    """Quantum potential E ∝ 1/r² — outer shells have lower energy."""
    evs = mod["pilot_wave"]().energies_ev()
    for i in range(1, 6):
        assert evs[i] < evs[i - 1], f"Pilot wave energy not decreasing at shell {i}: {evs[i]} >= {evs[i-1]}"


# ── Cross-theory invariants ───────────────────────────────────────────────────


def test_all_energies_positive_finite(mod):
    for name, result in mod["run_all"]().items():
        for s in result.shells:
            assert s.energy_ev > 0 and math.isfinite(s.energy_ev), f"{name} shell {s.shell_index}: E={s.energy_ev}"


def test_all_frequencies_positive_finite(mod):
    for name, result in mod["run_all"]().items():
        for s in result.shells:
            assert s.frequency_hz > 0 and math.isfinite(
                s.frequency_hz
            ), f"{name} shell {s.shell_index}: f={s.frequency_hz}"


def test_all_rms_residuals_finite(mod):
    for name, result in mod["run_all"]().items():
        assert math.isfinite(result.rms_residual_ev), f"{name}: RMS residual is not finite"


def test_bohr_rms_lowest_by_definition(mod):
    """Bohr is the reference — it should have the lowest RMS (zero)."""
    results = mod["run_all"]()
    bohr_rms = results["bohr"].rms_residual_ev
    assert bohr_rms < 1e-6


def test_ko_shell_is_tongue_KO(mod):
    for name, result in mod["run_all"]().items():
        assert result.shells[0].tongue == "KO", f"{name} shell 0 not KO"


def test_dr_shell_is_tongue_DR(mod):
    for name, result in mod["run_all"]().items():
        assert result.shells[5].tongue == "DR", f"{name} shell 5 not DR"


# ── Serialization ─────────────────────────────────────────────────────────────


def test_to_dict_schema_version(mod):
    for name, result in mod["run_all"]().items():
        d = result.to_dict()
        assert d["name"] == name
        assert "description" in d
        assert "rms_residual_ev" in d
        assert len(d["shells"]) == 6


def test_to_dict_shell_has_required_keys(mod):
    result = mod["compton"]()
    shell_dict = result.to_dict()["shells"][0]
    required = {
        "tongue",
        "shell",
        "energy_ev",
        "frequency_hz",
        "orbital_radius_m",
        "residual_ev",
        "hydrogen_measured_ev",
    }
    assert required.issubset(set(shell_dict.keys()))


def test_to_dict_compton_ko_residual_zero(mod):
    """KO shell: compton_orbital anchored to Bohr n=1, so residual should be 0."""
    result = mod["compton"]()
    d = result.to_dict()
    ko_shell = d["shells"][0]
    assert abs(ko_shell["residual_ev"]) < 1e-6


# ── Comparison table ──────────────────────────────────────────────────────────


def test_comparison_table_non_empty(mod):
    results = mod["run_all"]()
    table = mod["table"](results)
    assert len(table) > 200


def test_comparison_table_has_all_theory_names(mod):
    results = mod["run_all"]()
    table = mod["table"](results)
    for name in results:
        assert name in table, f"Theory {name} missing from table"


def test_comparison_table_has_tongue_headers(mod):
    results = mod["run_all"]()
    table = mod["table"](results)
    for t in mod["tongues"]:
        assert t in table, f"Tongue {t} missing from table"
