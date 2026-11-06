"""Cross-profile checks for the four formerly implicit SCBE layer contracts."""

from __future__ import annotations

import importlib
import math

import numpy as np
import pytest

PROFILE_MODULES = (
    "src.symphonic_cipher.scbe_aethermoore.layers.fourteen_layer_pipeline",
    "symphonic_cipher.scbe_aethermoore.layers.fourteen_layer_pipeline",
)


@pytest.mark.parametrize("module_name", PROFILE_MODULES)
def test_l02_legacy_view_and_canonical_active_view_are_bijective(module_name):
    module = importlib.import_module(module_name)
    complex_values = np.array([1 + 2j, 3 + 4j])
    legacy = module.layer_2_realify(complex_values)
    canonical = module.layer_2_realify(complex_values, order=module.L02_CANONICAL_ORDER)
    assert np.array_equal(legacy, [1, 2, 3, 4])
    assert np.array_equal(canonical, [1, 3, 2, 4])
    restored = module.convert_realification(
        canonical,
        source=module.L02_CANONICAL_ORDER,
        target=module.RealificationOrder.INTERLEAVED,
    )
    assert np.array_equal(restored, legacy)
    assert np.linalg.norm(canonical) == pytest.approx(np.linalg.norm(legacy))


@pytest.mark.parametrize("module_name", PROFILE_MODULES)
def test_l07_conjugated_shift_matches_canonical_order(module_name):
    module = importlib.import_module(module_name)
    point = np.array([0.17, -0.11, 0.04, 0.02])
    shift = np.array([0.08, 0.03, -0.01, 0.0])
    phase = 0.71
    rotation = module.first_plane_rotation(len(point), phase)
    expected = module.mobius_addition(shift, rotation @ point)
    actual = module.layer_7_phase(
        point,
        phase,
        shift,
        composition_order=module.L07_CANONICAL_ORDER,
    )
    assert np.allclose(actual, expected, atol=1e-12)

    native_shift = module.adapt_mobius_shift(
        shift,
        rotation,
        source=module.L07_CANONICAL_ORDER,
        target=module.L07_FULL_NATIVE_ORDER,
    )
    native = module.layer_7_phase(point, phase, native_shift)
    assert np.allclose(native, expected, atol=1e-12)


@pytest.mark.parametrize("module_name", PROFILE_MODULES)
def test_l09_status_prevents_sentinel_collision(module_name):
    module = importlib.import_module(module_name)
    assert module.layer_9_spectral_observation(None, sample_rate=8).status.value == "MISSING"
    silent = module.layer_9_spectral_observation(np.zeros(8), sample_rate=8)
    assert silent.status.value == "SILENT"
    assert silent.score == 0.0
    short = module.layer_9_spectral_observation(np.array([1.0, -1.0]), sample_rate=8)
    assert short.status.value == "TOO_SHORT"
    assert short.score is None and short.decision_value() == 0.5
    observed = module.layer_9_spectral_observation(np.array([1.0, 0.5, -0.5, -1.0]), sample_rate=8)
    assert observed.status.value == "OBSERVED"
    assert observed.sample_rate_hz == 8 and observed.cutoff_hz == 2


@pytest.mark.parametrize("module_name", PROFILE_MODULES)
def test_full_pipeline_emits_all_four_contract_receipts(module_name):
    module = importlib.import_module(module_name)
    pipeline = module.FourteenLayerPipeline()
    if hasattr(pipeline, "calibrate"):
        pipeline.calibrate(
            [
                {
                    "identity": 0.2,
                    "intent": 0.3 + 0.2j,
                    "trajectory": 0.7,
                    "timing": 120.0,
                    "commitment": 0.8,
                    "signature": 0.9,
                }
            ]
        )
    _, states = pipeline.process(
        identity=0.2,
        intent=0.3 + 0.2j,
        trajectory=0.7,
        timing=120.0,
        commitment=0.8,
        signature=0.9,
        t=4.0,
        tau=0.8,
        eta=0.2,
        q=complex(math.cos(0.2), math.sin(0.2)),
        phase_angle=0.4,
        translation=np.array([0.02] * 12),
    )
    by_layer = {state.layer: state for state in states}
    assert by_layer[2].metrics["coordinate_order"] == "BLOCK_REAL_THEN_IMAG"
    assert by_layer[7].metrics["composition_order"] == "ROTATE_THEN_TRANSLATE"
    assert by_layer[9].metrics["observation_status"] == "OBSERVED"
    assert by_layer[14].metrics["telemetry_kind"] == "L14B_VERDICT_SONIFICATION_OUTPUT"
    assert by_layer[14].metrics["execution_order"] == "POST_L13"


def test_reference_profile_declares_canonical_contracts():
    reference = importlib.import_module("src.scbe_14layer_reference")
    result = reference.scbe_14layer_pipeline(
        np.linspace(0.1, 1.2, 12),
        telemetry_signal=np.sin(np.linspace(0, 4 * np.pi, 32)),
        audio_frame=np.sin(np.linspace(0, 2 * np.pi, 32)),
    )
    contracts = result["layer_contracts"]
    assert contracts["L02_coordinate_order"] == "BLOCK_REAL_THEN_IMAG"
    assert contracts["L07_composition_order"] == "ROTATE_THEN_TRANSLATE"
    assert contracts["L09_observation_status"] == "OBSERVED"
    assert contracts["L14_telemetry_kind"] == "L14A_AUDIO_COHERENCE_INPUT"
    assert contracts["L14_execution_order"] == "PRE_L13"


def test_l14_typed_split_rejects_role_substitution_and_cycles():
    contracts = importlib.import_module("src.symphonic_cipher.scbe_aethermoore.layer_contracts")
    assert contracts.TelemetryEnvelope.coherence(0.7).samples is None
    assert contracts.TelemetryEnvelope.sonification([0.1, -0.2]).scalar is None
    assert contracts.validate_l14_dependency_order(12, 13, 14)
    with pytest.raises(ValueError):
        contracts.TelemetryEnvelope(contracts.TelemetryKind.AUDIO_COHERENCE_INPUT, scalar=0.7, samples=(0.1,))
    with pytest.raises(ValueError):
        contracts.validate_l14_dependency_order(14, 13, 12)
