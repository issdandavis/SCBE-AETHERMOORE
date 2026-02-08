"""
Dual Ternary Full Negative State Flux Tests
============================================

@file test_dual_ternary_full_flux.py
@layer Layer 9, Layer 10, Layer 14
@component Full negative state flux + spectral signature verification

Every position can be -1/0/1 (full 3x3 = 9-state space), giving richer
spectral signatures than binary {0,1}. This validates:
- Complete state space coverage (9 states)
- Closure under all transitions
- Spectral signature sensitivity to sign bias
- Deterministic transition behavior
- FFT DC component diagnostics for Layer 9/14 style checks
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Ternary state model
# ---------------------------------------------------------------------------

STATES = (-1, 0, 1)


def all_states() -> List[Tuple[int, int]]:
    """Generate all 9 dual-ternary states: (primary, mirror)."""
    return [(p, m) for p in STATES for m in STATES]


def clip_ternary(x: int) -> int:
    """Clip an integer to the ternary range [-1, 0, 1]."""
    return max(-1, min(1, int(x)))


def transition(
    state: Tuple[int, int], action: Tuple[int, int]
) -> Tuple[int, int]:
    """
    Apply an action (delta_primary, delta_mirror) to a dual-ternary state.

    Both components are clipped to [-1, 1] after addition.
    """
    p, m = state
    dp, dm = action
    return (clip_ternary(p + dp), clip_ternary(m + dm))


def spectral_signature(seq: List[Tuple[int, int]]) -> np.ndarray:
    """
    Compute a minimal 2-channel FFT signature over a dual-ternary sequence.

    Returns a 2 x T complex array where each row is the FFT of one channel
    (primary stream, mirror stream).
    """
    p = np.array([s[0] for s in seq], dtype=float)
    m = np.array([s[1] for s in seq], dtype=float)
    return np.fft.fft(np.vstack([p, m]), axis=1)


def energy(sig: np.ndarray) -> float:
    """Total spectral energy (sum of |coeff|^2)."""
    return float(np.sum(np.abs(sig) ** 2))


# ---------------------------------------------------------------------------
# Tests: state space
# ---------------------------------------------------------------------------

class TestStateSpace:
    """Verify the full 9-state dual-ternary space."""

    def test_full_state_space_is_9(self):
        """All 9 states exist including all-negative corners."""
        s = all_states()
        assert len(s) == 9
        assert (-1, -1) in s
        assert (-1, 0) in s
        assert (-1, 1) in s
        assert (0, -1) in s
        assert (0, 0) in s
        assert (0, 1) in s
        assert (1, -1) in s
        assert (1, 0) in s
        assert (1, 1) in s

    def test_no_duplicates(self):
        """State space has no duplicate entries."""
        s = all_states()
        assert len(s) == len(set(s))

    def test_symmetry_under_negation(self):
        """For every state (p, m), the negation (-p, -m) also exists."""
        s = set(all_states())
        for p, m in list(s):
            assert (-p, -m) in s


# ---------------------------------------------------------------------------
# Tests: transitions
# ---------------------------------------------------------------------------

class TestTransitions:
    """Verify that transitions are closed and correct."""

    def test_transitions_closed_under_full_negative_flux(self):
        """Every (state, action) pair produces a valid state."""
        s = all_states()
        actions = all_states()  # actions also in {-1,0,1}^2
        for st in s:
            for act in actions:
                nxt = transition(st, act)
                assert nxt in s, (
                    f"transition({st}, {act}) = {nxt} is not in state space"
                )

    def test_identity_action(self):
        """Action (0, 0) leaves state unchanged."""
        for st in all_states():
            assert transition(st, (0, 0)) == st

    def test_saturation_at_boundary(self):
        """Repeated positive actions saturate at (1, 1)."""
        st = (0, 0)
        for _ in range(10):
            st = transition(st, (1, 1))
        assert st == (1, 1)

    def test_saturation_at_negative_boundary(self):
        """Repeated negative actions saturate at (-1, -1)."""
        st = (0, 0)
        for _ in range(10):
            st = transition(st, (-1, -1))
        assert st == (-1, -1)

    def test_oscillation(self):
        """Alternating +1/-1 actions produce oscillation, not drift."""
        st = (0, 0)
        history = [st]
        for i in range(20):
            act = (1, -1) if i % 2 == 0 else (-1, 1)
            st = transition(st, act)
            history.append(st)
        # Should not end up at a corner — oscillates
        assert st != (1, 1)
        assert st != (-1, -1)

    def test_clip_ternary_range(self):
        """clip_ternary maps arbitrary integers to {-1, 0, 1}."""
        assert clip_ternary(-100) == -1
        assert clip_ternary(-1) == -1
        assert clip_ternary(0) == 0
        assert clip_ternary(1) == 1
        assert clip_ternary(999) == 1


# ---------------------------------------------------------------------------
# Tests: spectral signatures
# ---------------------------------------------------------------------------

class TestSpectralSignatures:
    """Verify spectral diagnostics for dual-ternary streams."""

    def test_spectral_signature_shape(self):
        """Signature has shape (2, T) for a length-T sequence."""
        seq = [(0, 0)] * 16
        sig = spectral_signature(seq)
        assert sig.shape == (2, 16)

    def test_constant_stream_dc_only(self):
        """A constant stream has all energy in DC component."""
        seq = [(1, 1)] * 64
        sig = spectral_signature(seq)
        # DC component should carry all energy
        dc_energy = float(np.sum(np.abs(sig[:, 0]) ** 2))
        total = energy(sig)
        assert dc_energy / total > 0.99

    def test_alternating_stream_no_dc(self):
        """A perfectly alternating stream has zero DC component."""
        seq = [(-1, 1), (1, -1)] * 32
        sig = spectral_signature(seq)
        # DC component should be near zero (sum of each channel = 0)
        dc_mag = float(np.sum(np.abs(sig[:, 0])))
        assert dc_mag < 1e-10

    def test_spectral_signature_changes_with_sign_bias(self):
        """Biased (all-positive) stream has much larger DC than balanced."""
        seq_bal = [(-1, 1), (1, -1)] * 32
        seq_pos = [(1, 1)] * 64

        sig_bal = spectral_signature(seq_bal)
        sig_pos = spectral_signature(seq_pos)

        dc_bal = abs(sig_bal[:, 0]).sum()
        dc_pos = abs(sig_pos[:, 0]).sum()
        assert dc_pos > dc_bal * 5

    def test_spectral_energy_monotonic_with_amplitude(self):
        """Higher-amplitude states produce more spectral energy."""
        seq_zero = [(0, 0)] * 64
        seq_half = [(1, 0)] * 64
        seq_full = [(1, 1)] * 64

        e_zero = energy(spectral_signature(seq_zero))
        e_half = energy(spectral_signature(seq_half))
        e_full = energy(spectral_signature(seq_full))

        assert e_zero < e_half < e_full

    def test_random_sequence_nonzero_energy(self):
        """A random ternary sequence has nonzero spectral energy."""
        rng = np.random.default_rng(42)
        seq = [
            (int(rng.integers(-1, 2)), int(rng.integers(-1, 2)))
            for _ in range(64)
        ]
        e = energy(spectral_signature(seq))
        assert e > 0.0

    def test_mirror_symmetry_in_spectrum(self):
        """Swapping primary/mirror channels swaps spectrum rows."""
        rng = np.random.default_rng(99)
        seq = [
            (int(rng.integers(-1, 2)), int(rng.integers(-1, 2)))
            for _ in range(32)
        ]
        seq_swap = [(m, p) for p, m in seq]

        sig = spectral_signature(seq)
        sig_swap = spectral_signature(seq_swap)

        # Row 0 of sig should match row 1 of sig_swap and vice versa
        assert np.allclose(sig[0], sig_swap[1])
        assert np.allclose(sig[1], sig_swap[0])


# ---------------------------------------------------------------------------
# Tests: trajectory analysis
# ---------------------------------------------------------------------------

class TestTrajectoryAnalysis:
    """Verify trajectory-level properties of dual-ternary streams."""

    def test_trajectory_from_actions(self):
        """A sequence of actions produces a reproducible trajectory."""
        actions = [(1, 0), (0, 1), (-1, -1), (1, 1), (0, -1)]
        st = (0, 0)
        trajectory = [st]
        for act in actions:
            st = transition(st, act)
            trajectory.append(st)

        expected = [(0, 0), (1, 0), (1, 1), (0, 0), (1, 1), (1, 0)]
        assert trajectory == expected

    def test_all_negative_trajectory_valid(self):
        """A trajectory staying in the negative quadrant is valid."""
        st = (-1, -1)
        trajectory = [st]
        # Only apply actions that keep us negative
        for _ in range(10):
            st = transition(st, (-1, -1))
            trajectory.append(st)
            assert st == (-1, -1)

    def test_trajectory_spectral_drift_detection(self):
        """
        A trajectory that drifts from balanced to biased shows
        increasing DC component in a sliding spectral window.
        """
        # Build a sequence that starts balanced, then drifts positive
        seq: List[Tuple[int, int]] = []
        for i in range(128):
            if i < 64:
                # Balanced: alternate
                seq.append((-1, 1) if i % 2 == 0 else (1, -1))
            else:
                # Biased: all positive
                seq.append((1, 1))

        # Compute DC in first half vs second half
        sig_first = spectral_signature(seq[:64])
        sig_second = spectral_signature(seq[64:])

        dc_first = float(np.sum(np.abs(sig_first[:, 0])))
        dc_second = float(np.sum(np.abs(sig_second[:, 0])))

        # Second half (biased) should have much larger DC
        assert dc_second > dc_first * 10
