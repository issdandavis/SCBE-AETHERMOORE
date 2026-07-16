import copy

import numpy as np
import pytest

from python.scbe.material_flow import (
    MaterialPolicy,
    pulse_fill,
    receipt_sha256,
    verify_pulse_receipt,
)


def test_voltage_pulses_until_open_space_fills_then_counts_area():
    materials = np.ones((5, 5), dtype=np.int64)
    seeds = np.zeros((5, 5), dtype=bool)
    seeds[2, 2] = True
    result = pulse_fill(materials, seeds, MaterialPolicy.from_materials([1]))
    assert result.fixed_point is True
    assert result.total_area == 25
    assert result.area_by_material == {1: 25}
    assert np.all(result.voltage == 1.0)
    assert verify_pulse_receipt(result.receipt)


def test_one_pulse_is_one_graph_step_not_a_global_fill():
    materials = np.ones((5, 5), dtype=np.int64)
    seeds = np.zeros((5, 5), dtype=bool)
    seeds[2, 2] = True
    result = pulse_fill(
        materials,
        seeds,
        MaterialPolicy.from_materials([1]),
        max_pulses=1,
    )
    assert result.fixed_point is False
    assert result.total_area == 5


def test_material_bands_control_which_relationships_conduct():
    materials = np.array([[1, 2, 3, 2, 1]], dtype=np.int64)
    seeds = np.array([[True, False, False, False, False]])
    policy = MaterialPolicy.from_materials([1, 2, 3], allowed_transitions=[(1, 2), (2, 3)])
    result = pulse_fill(materials, seeds, policy)
    assert result.filled.tolist() == [[True, True, True, False, False]]
    assert result.area_by_material == {1: 1, 2: 1, 3: 1}


def test_nonconductive_seed_fails_closed():
    with pytest.raises(ValueError, match="conductive material"):
        pulse_fill(
            np.array([[0, 1]]),
            np.array([[True, False]]),
            MaterialPolicy.from_materials([1]),
        )


def test_receipt_detects_count_or_phase_tampering():
    result = pulse_fill(
        np.ones((3, 3), dtype=np.int64),
        np.array([[True, False, False], [False, False, False], [False, False, False]]),
        MaterialPolicy.from_materials([1]),
    )
    baseline = receipt_sha256(result.receipt)
    tampered = copy.deepcopy(result.receipt)
    tampered["pulses"][1]["total_area"] += 1
    assert verify_pulse_receipt(tampered) is False
    assert receipt_sha256(tampered) != baseline
