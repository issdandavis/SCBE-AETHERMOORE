"""Frequency/power checks that the former first-half-FFT ratio could not pass."""

import numpy as np
import pytest

from src.scbe_14layer_reference import layer_9_spectral_coherence as coherence


def cosine(bin_index, count=256):
    return np.cos(2 * np.pi * bin_index * np.arange(count) / count)


@pytest.mark.parametrize("count", [255, 256])
def test_separates_interior_low_and_high_frequencies(count):
    assert coherence(cosine(4, count)) > 0.99
    assert coherence(cosine(100, count)) < 0.01


def test_mixture_measures_power_not_amplitude():
    assert coherence(cosine(4) + 2 * cosine(100)) == pytest.approx(1 / 5, abs=1e-7)


def test_cutoff_is_in_cycles_per_sample_and_counts_both_signs():
    assert coherence(cosine(64)) < 0.01
    assert coherence(cosine(64), low_frequency_cutoff=0.3) > 0.99
    for direction in (-1, 1):
        assert coherence(np.exp(direction * 2j * np.pi * 4 * np.arange(256) / 256)) > 0.99


def test_amplitude_scaling_is_stable_and_missing_differs_from_silence():
    mixed = cosine(4) + 2 * cosine(100)
    for amplitude in (1e-250, 1, 1e250):
        assert coherence(amplitude * mixed) == pytest.approx(0.2, abs=1e-7)
    assert coherence(None) == coherence(np.array([])) == 0.5
    assert coherence(np.zeros(16)) == 0
    assert coherence(np.ones(16)) > 0.99
    assert coherence(np.array([2])) > 0.99


@pytest.mark.parametrize("signal", [np.array([np.nan]), np.array([np.inf]), np.ones((2, 3))])
def test_invalid_measurements_rejected(signal):
    with pytest.raises(ValueError):
        coherence(signal)


@pytest.mark.parametrize("cutoff", [0, -0.1, 0.6, np.nan])
def test_invalid_cutoffs_rejected(cutoff):
    with pytest.raises(ValueError):
        coherence(cosine(4), low_frequency_cutoff=cutoff)


@pytest.mark.parametrize("eps", [-1, np.nan, np.inf])
def test_invalid_epsilon_rejected(eps):
    with pytest.raises(ValueError):
        coherence(cosine(4), eps)
