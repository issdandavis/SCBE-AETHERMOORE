from __future__ import annotations

import pytest

from src.physics_sim.mission_body import (
    CargoManifest,
    CrewLoopAssumptions,
    ElectrodynamicTether,
    build_cargo_tug_budget,
    build_crew_loop_budget,
    build_earth_mars_body_budget,
    edt_delta_v_time_s,
    edt_thrust_n,
    rocket_equation_propellant_kg,
)


def test_earth_mars_body_budget_uses_trusted_hohmann_transfer() -> None:
    budget = build_earth_mars_body_budget(dry_mass_kg=20_000.0)

    assert budget.transfer["delta_v_total_m_s"] == pytest.approx(5596.04, abs=0.1)
    assert budget.transfer["transfer_time_days"] == pytest.approx(258.92, abs=0.01)
    assert budget.crew_loop.mission_days == pytest.approx(budget.transfer["transfer_time_days"])


def test_rocket_equation_reference_propellant_fractions_match_expected_scale() -> None:
    delta_v = 5596.037242959428

    chemical = rocket_equation_propellant_kg(20_000.0, delta_v, 450.0)
    nuclear = rocket_equation_propellant_kg(20_000.0, delta_v, 900.0)
    electric = rocket_equation_propellant_kg(20_000.0, delta_v, 3000.0)

    assert chemical["wet_mass_fraction_propellant"] == pytest.approx(0.718, abs=0.002)
    assert nuclear["wet_mass_fraction_propellant"] == pytest.approx(0.469, abs=0.002)
    assert electric["wet_mass_fraction_propellant"] == pytest.approx(0.173, abs=0.002)


def test_dual_water_budget_keeps_life_water_separate_from_work_water_propellant() -> None:
    budget = build_earth_mars_body_budget(dry_mass_kg=20_000.0)
    by_name = {option.name: option for option in budget.propulsion_options}

    assert budget.crew_loop.personal_water_makeup_kg > 0.0
    assert by_name["steam_water_reference"].propellant_kind == "work_water"
    assert by_name["steam_water_reference"].work_water_spent_kg == pytest.approx(
        by_name["steam_water_reference"].propellant_kg
    )
    assert by_name["chemical_h2_o2_reference"].work_water_spent_kg == 0.0


def test_crew_loop_rejects_invalid_closure_fractions() -> None:
    with pytest.raises(ValueError, match="food_closure_fraction"):
        build_crew_loop_budget(10.0, CrewLoopAssumptions(food_closure_fraction=1.5))

    with pytest.raises(ValueError, match="crew_size"):
        build_crew_loop_budget(10.0, CrewLoopAssumptions(crew_size=0))


# ---------------------------------------------------------------------------- #
#  Cargo-only (crewless tug) mode                                              #
# ---------------------------------------------------------------------------- #
def test_cargo_manifest_payload_and_dry_mass_account_correctly() -> None:
    m = CargoManifest(bus_dry_mass_kg=1_500.0, metal_feedstock_kg=200.0, debris_capture_hardware_kg=300.0)
    # property, not tautology: dry mass must equal bus + the SUM of every payload account
    assert m.payload_kg == pytest.approx(500.0)
    assert m.dry_mass_kg == pytest.approx(2_000.0)


def test_edt_thrust_is_field_odd_reverses_with_B() -> None:
    # An electrodynamic force F = I*L*B is linear in B, so flipping B flips the thrust.
    # That field-oddness is what makes the tether a steerable, propellantless Δv source.
    forward = ElectrodynamicTether(length_m=10_000.0, current_a=5.0, b_field_t=25e-6)
    reversed_field = ElectrodynamicTether(length_m=10_000.0, current_a=5.0, b_field_t=-25e-6)
    assert edt_thrust_n(forward) == pytest.approx(-edt_thrust_n(reversed_field))
    assert edt_thrust_n(forward) > 0.0 > edt_thrust_n(reversed_field)


def test_edt_trades_time_for_propellant_at_equal_delta_v() -> None:
    budget = build_cargo_tug_budget(
        alt_start_km=800.0,
        alt_end_km=300.0,
        manifest=CargoManifest(bus_dry_mass_kg=1_500.0, debris_capture_hardware_kg=550.0),
        tether=ElectrodynamicTether(length_m=10_000.0, current_a=5.0),
    )
    delta_v = budget.transfer["delta_v_total_m_s"]
    dry_mass = budget.manifest.dry_mass_kg

    # Independent recompute of the tether's time cost from impulse = Δv*m / F.
    expected_seconds = edt_delta_v_time_s(delta_v, dry_mass, budget.tether_thrust_n)
    assert budget.edt_only_thrust_days == pytest.approx(expected_seconds / 86400.0)

    # The propellant options pay the SAME Δv in mass; every one must spend > 0 propellant,
    # while the tether spends none. That contrast is the cargo-mode thesis.
    assert all(opt.propellant_kg > 0.0 for opt in budget.propellant_options)
    assert budget.edt_only_thrust_days > 0.0


def test_cargo_deorbit_harvests_power_boost_spends_same_magnitude() -> None:
    common = dict(
        alt_start_km=800.0,
        alt_end_km=300.0,
        manifest=CargoManifest(bus_dry_mass_kg=1_500.0, debris_capture_hardware_kg=550.0),
    )
    deorbit = build_cargo_tug_budget(tether=ElectrodynamicTether(mode="deorbit"), **common)
    boost = build_cargo_tug_budget(tether=ElectrodynamicTether(mode="boost"), **common)
    # Same hardware -> same |power|; the difference is only WHO pays (label/interpretation).
    assert deorbit.edt_electrical_power_w == pytest.approx(boost.edt_electrical_power_w)
    assert deorbit.tether_mode == "deorbit"
    assert boost.tether_mode == "boost"
    assert "harvest" in deorbit.interpretation["edt_rule"]
