import math

import numpy as np

from experiments.signed_multiplane_encoding_demo import (
    SignedBit,
    build_signed_codebook,
    build_ternary_codebook,
    capacity_bits,
    decode_nearest,
    min_pairwise_distance,
    roundtrip_accuracy,
    signed_states,
    ternary_states,
    to_unit_interval_signed,
)


def test_state_counts_and_capacity_ordering():
    # Baseline binary two-plane has 4 states.
    binary_states = 4
    assert len(ternary_states()) == 9
    assert len(signed_states()) == 16
    assert capacity_bits(16) > capacity_bits(9) > capacity_bits(binary_states)


def test_signed_mapping_stays_inside_unit_interval():
    neg_one = SignedBit(1, -1)
    neg_zero = SignedBit(0, -1)
    pos_zero = SignedBit(0, 1)
    pos_one = SignedBit(1, 1)

    x1 = to_unit_interval_signed(neg_one)
    x2 = to_unit_interval_signed(neg_zero)
    x3 = to_unit_interval_signed(pos_zero)
    x4 = to_unit_interval_signed(pos_one)

    assert 0.0 <= x1 <= 1.0
    assert 0.0 <= x2 <= 1.0
    assert 0.0 <= x3 <= 1.0
    assert 0.0 <= x4 <= 1.0

    # Keep signed zeros distinct in unit interval.
    assert x2 < 0.5 < x3
    assert math.isclose(x1, 0.0)
    assert math.isclose(x4, 1.0)


def test_signed_codebook_roundtrip_exact_without_noise():
    codebook = build_signed_codebook()
    for state, vec in codebook.items():
        decoded = decode_nearest(vec, codebook)
        assert decoded == state


def test_positive_codebook_separation():
    signed = build_signed_codebook()
    ternary = build_ternary_codebook()
    assert min_pairwise_distance(signed) > 0.0
    assert min_pairwise_distance(ternary) > 0.0


def test_noisy_roundtrip_still_high_accuracy():
    signed = build_signed_codebook()
    ternary = build_ternary_codebook()

    acc_signed = roundtrip_accuracy(signed, noise_std=0.03, seed=11)
    acc_ternary = roundtrip_accuracy(ternary, noise_std=0.03, seed=11)

    # Deterministic geometry should decode robustly under moderate noise.
    assert acc_signed >= 0.8
    assert acc_ternary >= 0.8
