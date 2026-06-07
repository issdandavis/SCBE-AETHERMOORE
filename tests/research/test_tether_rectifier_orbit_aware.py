from __future__ import annotations

import math

import pytest

from scripts.research.tether_rectifier_null_harness import (
    HarnessParams,
    run_electromagnetic_piston_channel,
    run_null_battery,
)
from scripts.sim_tether_rectifier import (
    SimParams,
    TetherRectifierSim,
    electrodynamic_tether_terms,
    nonreciprocal_grip_lift_torque,
)
from src.physics_sim.orbital import MU_EARTH, RADIUS_EARTH, circular_velocity


def test_orbit_aware_tether_reports_real_vbl_and_ilb_terms() -> None:
    altitude_m = 400_000.0
    speed = circular_velocity(RADIUS_EARTH + altitude_m, MU_EARTH)
    params = SimParams(
        length_m=1000.0,
        linear_density=0.5,
        b_field_t=25e-6,
        orbital_speed=speed,
        current_a=10.0,
        orbit_altitude_m=altitude_m,
    )
    frame = TetherRectifierSim(params).step_once()

    assert frame["orbit_model"] == "leo_uniform_perpendicular_field_order_of_magnitude"
    assert frame["orbital_speed_m_s"] == pytest.approx(speed)
    assert frame["motional_emf_v"] == pytest.approx(speed * 25e-6 * 1000.0)
    assert frame["motional_emf_signed_v"] == pytest.approx(speed * 25e-6 * 1000.0)
    assert frame["lorentz_force_n"] == pytest.approx(10.0 * 1000.0 * 25e-6)
    assert frame["lorentz_force_signed_n"] == pytest.approx(10.0 * 1000.0 * 25e-6)
    assert frame["specific_lorentz_force_m_s2"] == pytest.approx(0.25 / 500.0)
    assert frame["specific_lorentz_force_signed_m_s2"] == pytest.approx(0.25 / 500.0)


def test_orbit_aware_fields_are_absent_in_desk_proxy_mode() -> None:
    frame = TetherRectifierSim(SimParams()).step_once()

    assert "motional_emf_v" not in frame
    assert "lorentz_force_n" not in frame


def test_nonreciprocal_rectifier_has_no_zero_velocity_bias() -> None:
    y = [0.0, 0.002, -0.002, 0.002, 0.0]
    v = [0.0] * len(y)

    assert nonreciprocal_grip_lift_torque(y, v, dx=0.25, gain=0.35, orientation_sign=1.0) == pytest.approx(0.0)


def test_nonreciprocal_rectifier_direction_flips_with_velocity_and_orientation() -> None:
    y = [0.0, 0.001, 0.003, 0.002, 0.0]
    v = [0.0, 0.02, 0.03, 0.01, 0.0]

    forward = nonreciprocal_grip_lift_torque(y, v, dx=0.25, gain=0.35, orientation_sign=1.0)
    time_reversed = nonreciprocal_grip_lift_torque(y, [-value for value in v], dx=0.25, gain=0.35, orientation_sign=1.0)
    orientation_reversed = nonreciprocal_grip_lift_torque(y, v, dx=0.25, gain=0.35, orientation_sign=-1.0)

    assert forward != 0.0
    assert time_reversed == pytest.approx(-forward)
    assert orientation_reversed == pytest.approx(-forward)


def test_mechanical_rectifier_is_amplitude_even_not_field_odd() -> None:
    y = [0.0, 0.001, 0.003, 0.002, 0.0]
    v = [0.0, 0.02, 0.03, 0.01, 0.0]

    forward = nonreciprocal_grip_lift_torque(y, v, dx=0.25, gain=0.35)
    amplitude_flipped = nonreciprocal_grip_lift_torque(
        [-value for value in y], [-value for value in v], dx=0.25, gain=0.35
    )

    assert amplitude_flipped == pytest.approx(forward)


def test_electrodynamic_channel_is_field_odd_with_positive_magnitudes() -> None:
    positive = electrodynamic_tether_terms(
        orbital_speed_m_s=7672.598648,
        b_field_t=25e-6,
        tether_length_m=1000.0,
        current_a=10.0,
        tether_mass_kg=500.0,
    )
    negative = electrodynamic_tether_terms(
        orbital_speed_m_s=7672.598648,
        b_field_t=-25e-6,
        tether_length_m=1000.0,
        current_a=10.0,
        tether_mass_kg=500.0,
    )

    assert positive["motional_emf_v"] == pytest.approx(negative["motional_emf_v"])
    assert positive["lorentz_force_n"] == pytest.approx(negative["lorentz_force_n"])
    assert negative["motional_emf_signed_v"] == pytest.approx(-positive["motional_emf_signed_v"])
    assert negative["lorentz_force_signed_n"] == pytest.approx(-positive["lorentz_force_signed_n"])


def test_rectifier_null_harness_splits_mechanical_and_edt_channels() -> None:
    report = run_null_battery(HarnessParams(nodes=48, steps=160, null_trials=40, seed=7))

    mechanical = report["mechanical_channel"]
    electrodynamic = report["electrodynamic_channel"]
    piston = report["electromagnetic_piston_channel"]

    assert report["verdict"] == "TETHER_THREE_CHANNEL_MODEL_VALIDATED_FOR_PROXY"
    assert mechanical["verdict"] == "MECHANICAL_FLUX_SURVIVES_PHASE_NULL"
    assert mechanical["effect_ratio_abs_vs_null95"] > 1.0
    assert mechanical["amplitude_flip_same_ratio"] == pytest.approx(1.0)
    assert mechanical["time_reverse_opposite_ratio"] == pytest.approx(1.0)
    assert electrodynamic["verdict"] == "EDT_SIGNED_TERMS_FIELD_ODD"
    assert electrodynamic["emf_field_flip_opposite_ratio"] == pytest.approx(1.0)
    assert electrodynamic["force_field_flip_opposite_ratio"] == pytest.approx(1.0)
    assert piston["verdict"] == "COMMUTATED_PISTON_BEATS_NULL_AND_IS_FIELD_ODD"
    assert piston["naive_ratio_abs_vs_null95"] < 1.0
    assert piston["commutated_ratio_abs_vs_null95"] > 1.0
    assert abs(piston["mistimed_mean_force_n"]) < piston["timing_jitter_null_abs_p95_n"]
    assert abs(piston["mistimed_mean_force_n"]) < 0.25 * abs(piston["commutated_mean_force_n"])
    assert piston["field_flip_opposite_ratio"] == pytest.approx(1.0)


def test_commutated_piston_beats_null_while_naive_traveling_current_fails() -> None:
    report = run_electromagnetic_piston_channel(
        HarnessParams(piston_coils=48, piston_steps=240, null_trials=60, seed=19)
    )

    assert abs(report["naive_traveling_current_mean_force_n"]) < report["random_sign_null_abs_p95_n"]
    assert abs(report["commutated_mean_force_n"]) > report["random_sign_null_abs_p95_n"]
    assert abs(report["mistimed_mean_force_n"]) < report["timing_jitter_null_abs_p95_n"]
    assert abs(report["mistimed_mean_force_n"]) < 0.25 * abs(report["commutated_mean_force_n"])
    assert report["commutated_b_reversed_mean_force_n"] == pytest.approx(-report["commutated_mean_force_n"])


def test_commutated_piston_timing_sweep_tracks_cosine_shape() -> None:
    report = run_electromagnetic_piston_channel(
        HarnessParams(piston_coils=48, piston_steps=240, null_trials=60, seed=19)
    )
    sweep = report["timing_sweep"]
    forces = sweep["forces_n"]
    force_0 = forces[f"{0.0:.12g}"]

    assert force_0 == pytest.approx(report["commutated_mean_force_n"])
    assert forces[f"{math.pi / 2.0:.12g}"] == pytest.approx(0.0, abs=report["timing_jitter_null_abs_p95_n"])
    assert forces[f"{math.pi:.12g}"] == pytest.approx(-force_0)
    assert sweep["cos_fit_max_abs_resid_n"] < 0.01 * abs(force_0)

    ordered = [forces[f"{offset:.12g}"] for offset in sweep["offsets_rad"]]
    assert ordered == sorted(ordered, reverse=True)
