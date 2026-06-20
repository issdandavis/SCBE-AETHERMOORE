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
    assert budget.clears_additive_gate is False


def test_net_gain_ratio():
    assert net_gain_ratio(3.0, 2.0, 1.0) == pytest.approx(1.5)


def test_additive_gate_pass_packet():
    budget = PrototypePowerBudget(
        mechanical_input_w=100,
        em_efficiency=0.02,
        teng_efficiency=0.012,
        pmic_efficiency=0.9,
    )
    packet = budget.decision_packet()
    assert packet["schema_version"] == "mtef_additive_gate_v1"
    assert packet["combined_after_power_management_w"] == pytest.approx(2.88)
    assert packet["stronger_individual_w"] == pytest.approx(2.0)
    assert packet["additive_gain_ratio"] == pytest.approx(1.44)
    assert packet["clears_additive_gate"] is True
    assert packet["minimum_practical_gain_ratio"] == pytest.approx(1.2)
    assert packet["clears_practical_margin"] is True


def test_additive_gate_fail_packet_after_power_management_loss():
    budget = PrototypePowerBudget(
        mechanical_input_w=100,
        em_efficiency=0.02,
        teng_efficiency=0.005,
        pmic_efficiency=0.75,
    )
    packet = budget.decision_packet()
    assert packet["combined_after_power_management_w"] == pytest.approx(1.875)
    assert packet["stronger_individual_w"] == pytest.approx(2.0)
    assert packet["additive_gain_ratio"] == pytest.approx(0.9375)
    assert packet["clears_additive_gate"] is False
    assert packet["clears_practical_margin"] is False


def test_additive_gate_can_pass_but_fail_practical_margin():
    budget = PrototypePowerBudget(
        mechanical_input_w=100,
        em_efficiency=0.02,
        teng_efficiency=0.004,
        pmic_efficiency=0.85,
    )
    assert budget.clears_additive_gate is True
    assert budget.additive_gain_ratio == pytest.approx(1.02)
    assert budget.clears_margin_gate(1.2) is False


def test_margin_gate_requires_real_margin():
    budget = PrototypePowerBudget(100, 0.02, 0.012, 0.9)
    with pytest.raises(ValueError):
        budget.clears_margin_gate(1.0)


def test_invalid_efficiency():
    with pytest.raises(ValueError):
        PrototypePowerBudget(100, 1.2, 0.1)
