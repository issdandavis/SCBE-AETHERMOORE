"""
Dual ternary full-flux tests.
"""

from __future__ import annotations

import math
import random

from src.symphonic_cipher.scbe_aethermoore.ai_brain.dual_ternary import (
    DualTernaryState,
    DualTernarySystem,
    FULL_STATE_SPACE,
    compute_spectrum,
    compute_state_energy,
    encode_sequence,
    encode_to_dual_ternary,
    estimate_fractal_dimension,
    state_from_index,
    state_index,
    transition,
)


class TestFullStateSpace:
    def test_all_9_states_present(self):
        pairs = {(s.primary, s.mirror) for s in FULL_STATE_SPACE}
        expected = {(p, m) for p in [-1, 0, 1] for m in [-1, 0, 1]}
        assert len(FULL_STATE_SPACE) == 9
        assert pairs == expected

    def test_index_roundtrip(self):
        for i in range(9):
            s = state_from_index(i)
            assert state_index(s) == i

    def test_negation_symmetry_exists(self):
        states = {(s.primary, s.mirror) for s in FULL_STATE_SPACE}
        for p, m in list(states):
            assert (-p, -m) in states


class TestEnergyModel:
    def test_reference_energies(self):
        assert compute_state_energy(DualTernaryState(0, 0)).energy == 0
        assert compute_state_energy(DualTernaryState(1, 1)).energy == 3
        assert compute_state_energy(DualTernaryState(-1, -1)).energy == 3
        assert compute_state_energy(DualTernaryState(1, -1)).energy == 1

    def test_energy_symmetry_under_sign_flip(self):
        for s in FULL_STATE_SPACE:
            e1 = compute_state_energy(s).energy
            e2 = compute_state_energy(DualTernaryState(-s.primary, -s.mirror)).energy
            assert e1 == e2


class TestTransitions:
    def test_closed_under_actions(self):
        actions = [(p, m) for p in (-1, 0, 1) for m in (-1, 0, 1)]
        valid = {(s.primary, s.mirror) for s in FULL_STATE_SPACE}
        for st in FULL_STATE_SPACE:
            for dp, dm in actions:
                nxt = transition(st, dp, dm)
                assert (nxt.primary, nxt.mirror) in valid

    def test_boundary_saturation(self):
        s = DualTernaryState(0, 0)
        for _ in range(10):
            s = transition(s, 1, 1)
        assert (s.primary, s.mirror) == (1, 1)
        for _ in range(10):
            s = transition(s, -1, -1)
        assert (s.primary, s.mirror) == (-1, -1)


class TestEncodingAndSpectra:
    def test_encode_sequence_21d_to_11_pairs(self):
        seq = encode_sequence([0.5] * 21, threshold=0.33)
        assert len(seq) == 11

    def test_sign_bias_increases_dc_like_energy(self):
        seq_bal = [DualTernaryState(-1, 1), DualTernaryState(1, -1)] * 32
        seq_pos = [DualTernaryState(1, 1)] * 64
        sp_bal = compute_spectrum(seq_bal)
        sp_pos = compute_spectrum(seq_pos)
        dc_bal = sum(abs(v) for v in sp_bal.cross_correlation[:1])
        dc_pos = sum(abs(v) for v in sp_pos.cross_correlation[:1])
        assert dc_pos >= dc_bal
        assert sp_pos.phase_anomaly > sp_bal.phase_anomaly

    def test_fractal_dimension_base_is_two(self):
        fd = estimate_fractal_dimension(FULL_STATE_SPACE * 10)
        assert abs(fd.base_dimension - 2.0) < 1e-10
        assert fd.hausdorff_dimension >= 1.8


class TestDualTernarySystemLifecycle:
    def test_history_and_step_growth(self):
        sys = DualTernarySystem()
        sys.encode([0.5] * 21)
        sys.encode([0.2] * 21)
        assert sys.step == 2
        assert sys.history_length > 0

    def test_threat_score_increases_for_high_bias(self):
        sys_bal = DualTernarySystem()
        rng = random.Random(42)
        for _ in range(20):
            vals = [rng.gauss(0.0, 0.5) for _ in range(21)]
            sys_bal.encode(vals)
        bal = sys_bal.full_analysis()["threat_score"]

        sys_hot = DualTernarySystem()
        for _ in range(20):
            sys_hot.encode([5.0] * 21)
        hot = sys_hot.full_analysis()["threat_score"]
        assert hot > bal

    def test_tensor_histogram_counts(self):
        seq = FULL_STATE_SPACE * 3
        hist = DualTernarySystem.tensor_histogram(seq)
        assert sum(sum(row) for row in hist) == 27
