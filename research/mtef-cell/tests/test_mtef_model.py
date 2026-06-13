import pytest

from src.mtef_model import (
    PrototypePowerBudget,
    average_power_from_energy,
    capacitor_energy_j,
    faraday_voltage_estimate,
    mechanical_power_from_stroke,
    net_gain_ratio,
)


def test_mechanical_power_from_stroke():
    assert mechanical_power_from_stroke(10, 0.1, 2) == pytest.approx(2.0)


def test_capacitor_energy():
    assert capacitor_energy_j(1.0, 2.0) == pytest.approx(2.0)


def test_average_power():
    assert average_power_from_energy(10, 5) == pytest.approx(2.0)


def test_faraday_voltage_estimate():
    assert faraday_voltage_estimate(100, 0.01, 0.5) == pytest.approx(2.0)


def test_power_budget():
    budget = PrototypePowerBudget(
        mechanical_input_w=100,
        em_efficiency=0.02,
        teng_efficiency=0.005,
        pmic_efficiency=0.8,
    )
    assert budget.em_output_w == pytest.approx(2.0)
    assert budget.teng_output_w == pytest.approx(0.5)
    assert budget.combined_after_power_management_w == pytest.approx(2.0)


def test_net_gain_ratio():
    assert net_gain_ratio(3.0, 2.0, 1.0) == pytest.approx(1.5)


def test_invalid_efficiency():
    with pytest.raises(ValueError):
        PrototypePowerBudget(100, 1.2, 0.1)
