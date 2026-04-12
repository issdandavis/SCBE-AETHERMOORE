"""
SCBE Inter-Lattice Binder

This module implements a recursive integer functional that couples two integer vectors
(K and S) into a single integer value. The resulting scalar can be used within
SCBE-AETHERMOORE's governance and safety pipeline to detect drift, disagreement and
witness states across post-quantum cryptographic systems.

Example usage:

    K = [1, 2, 3]
    S = [1, 3, 4]
    value = inter_lattice_binder(K, S)
    print(value)

The binder uses a ternary witness to classify the difference between
corresponding elements of K and S (positive difference, neutral, negative difference)
and applies a quadratic recursive mixing to accumulate a scalar value.
"""

from typing import Sequence


def ternary_witness(k: int, s: int, threshold: int) -> int:
    """Return +1 if k - s > threshold, -1 if k - s < -threshold, otherwise 0."""
    diff = k - s
    if diff > threshold:
        return 1
    elif diff < -threshold:
        return -1
    return 0


def inter_lattice_binder(K: Sequence[int], S: Sequence[int], *,
                         modulus: int = 2**64, threshold: int = 1,
                         seed: int = 0) -> int:
    """
    Combine two integer vectors K and S into a single integer value.

    :param K: Sequence of integers (e.g., a KEM-side state vector).
    :param S: Sequence of integers (e.g., a DSA-side state vector).
    :param modulus: Modulus to reduce the accumulator by (default 2**64).
    :param threshold: Threshold for ternary witness classification.
    :param seed: Starting seed value for the recursion.
    :return: An integer representing the combined state.
    :raises ValueError: If the sequences are not the same length.
    """
    if len(K) != len(S):
        raise ValueError("K and S must have the same length.")
    r = seed
    for k, s in zip(K, S):
        tau = ternary_witness(k, s, threshold)
        # Quadratic recursive mixer:
        r = (r * r + k * s + (k - s) ** 2 + tau) % modulus
    return r


def drift_measure(K0: Sequence[int], S0: Sequence[int],
                  K1: Sequence[int], S1: Sequence[int], *,
                  modulus: int = 2**64, threshold: int = 1,
                  seed: int = 0) -> int:
    """
    Compute the change in binder value between two states.

    This can be used to detect drift in the underlying vectors over time.

    :param K0, S0: Original vectors.
    :param K1, S1: New vectors.
    :return: The difference (mod modulus) between the two binder outputs.
    """
    h0 = inter_lattice_binder(K0, S0, modulus=modulus,
                              threshold=threshold, seed=seed)
    h1 = inter_lattice_binder(K1, S1, modulus=modulus,
                              threshold=threshold, seed=seed)
    return (h1 - h0) % modulus
