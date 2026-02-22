import json
import math

from src.physics_sim.core import (
    C,
    VACUUM_PERMITTIVITY,
    electromagnetism,
    harsh_physics_mode,
    lambda_handler,
    thermodynamics,
)


def test_em_wave_and_capacitor_can_be_computed_together():
    params = {
        "em_frequency": 5e14,
        "plate_area": 0.01,
        "plate_separation": 0.001,
    }
    result = electromagnetism(params)

    expected_wavelength = C / params["em_frequency"]
    expected_capacitance = (
        VACUUM_PERMITTIVITY * params["plate_area"] / params["plate_separation"]
    )

    assert math.isclose(result["em_wavelength"], expected_wavelength, rel_tol=1e-12)
    assert math.isclose(result["capacitance"], expected_capacitance, rel_tol=1e-12)


def test_negative_kelvin_skips_maxwell_speed_outputs_instead_of_crashing():
    result = thermodynamics({"temperature": -10.0, "molecular_mass": 4.65e-26})

    assert "average_kinetic_energy" in result
    assert "rms_speed" not in result
    assert "average_speed" not in result
    assert "most_probable_speed" not in result


def test_harsh_physics_mode_blocks_superluminal_inputs():
    wrapped = harsh_physics_mode(
        "relativity",
        {"velocity": 1.01 * C, "proper_time": 1.0, "proper_length": 1.0},
    )

    assert wrapped["allowed"] is False
    assert any(v["code"] == "velocity_superluminal" for v in wrapped["hard_violations"])


def test_harsh_physics_mode_enforces_thrust_envelope():
    wrapped = harsh_physics_mode(
        "classical",
        {"thrust": 1.0e8, "vehicle_mass": 1000.0},
    )

    assert wrapped["allowed"] is False
    assert any(
        v["code"] == "thrust_envelope_exceeded" for v in wrapped["hard_violations"]
    )


def test_lambda_handler_returns_422_when_harsh_mode_rejects():
    response = lambda_handler(
        {
            "simulation_type": "thermodynamics",
            "parameters": {"temperature": -1.0, "molecular_mass": 4.65e-26},
            "harsh_physics_mode": True,
        }
    )
    body = json.loads(response["body"])

    assert response["statusCode"] == 422
    assert "hard_violations" in body
    assert any(v["code"] == "invalid_kelvin_temperature" for v in body["hard_violations"])
