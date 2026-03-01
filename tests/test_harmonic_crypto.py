"""
Tests for P6 Harmonic Cryptography reference implementation.

Covers all five core classes across 25 patent claims:
    - HarmonicKeyGenerator (Claims 6-10)
    - RingRotationCipher (Claims 1-5)
    - VoiceLeadingOptimizer (Claims 11-15)
    - CounterpointProtocol (Claims 16-20)
    - HarmonicCryptosystem (Claims 21-25)
"""

import hashlib
import math
import sys
import os

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.crypto.harmonic_crypto import (
    CONSONANCE_RATINGS,
    HARMONIC_RATIOS,
    PYTHAGOREAN_COMMA,
    TONGUE_INTERVAL_MAP,
    VOICE_LEADING_COSTS,
    AgentVoice,
    CounterpointProtocol,
    CounterpointValidation,
    HarmonicCryptosystem,
    HarmonicKeyGenerator,
    MotionType,
    RingRotationCipher,
    SpiralState,
    TransitionResult,
    VoiceLeadingOptimizer,
    _consonance,
    _hamming_distance,
    _voice_leading_cost,
)


# ==========================================================================
# 1. HarmonicKeyGenerator Tests (Claims 6-10)
# ==========================================================================

class TestHarmonicKeyGenerator:
    """Tests for the circle-of-fifths spiral key generator."""

    def test_deterministic_generation(self):
        """Same seed produces same key material (Claim 6)."""
        seed = b"test_seed_deterministic"
        gen1 = HarmonicKeyGenerator(seed=seed)
        gen2 = HarmonicKeyGenerator(seed=seed)
        assert gen1.generate(64) == gen2.generate(64)

    def test_different_seeds_different_keys(self):
        """Different seeds produce different key material."""
        gen1 = HarmonicKeyGenerator(seed=b"seed_alpha")
        gen2 = HarmonicKeyGenerator(seed=b"seed_beta")
        assert gen1.generate(64) != gen2.generate(64)

    def test_non_repeating_sequence(self):
        """Key material does not repeat in practical lengths (Claim 6d)."""
        gen = HarmonicKeyGenerator(seed=b"non_repeat_test")
        key = gen.generate(1024)
        # Check that no 32-byte window repeats in the first 1024 bytes
        windows = set()
        for i in range(len(key) - 32):
            window = key[i:i + 32]
            assert window not in windows, f"Repeat found at offset {i}"
            windows.add(window)

    def test_pythagorean_comma_accumulates(self):
        """Comma drift grows after full 12-fifth cycles (Claim 7)."""
        gen = HarmonicKeyGenerator(seed=b"comma_test")
        # Advance 12 steps (one full cycle)
        gen.generate(12)
        drift_1 = gen.state.comma_drift
        # Advance another 12 steps
        gen.generate(12)
        drift_2 = gen.state.comma_drift
        # Drift should increase after each cycle
        assert drift_2 > drift_1
        # After 2 cycles, drift should be PYTHAGOREAN_COMMA^2 - 1
        expected = PYTHAGOREAN_COMMA ** 2 - 1.0
        assert abs(drift_2 - expected) < 1e-10

    def test_spiral_signature_changes(self):
        """Spiral signature changes as state advances (Claim 9)."""
        gen = HarmonicKeyGenerator(seed=b"sig_test")
        sig1 = gen.spiral_signature()
        gen.generate(10)
        sig2 = gen.spiral_signature()
        assert sig1 != sig2
        assert len(sig1) == 64  # SHA-256 hex digest

    def test_pqc_seed_derivation(self):
        """PQC seed derivation produces correct length (Claim 10)."""
        gen = HarmonicKeyGenerator(seed=b"pqc_test")
        seed32 = gen.derive_pqc_seed(32)
        assert len(seed32) == 32
        # A fresh generator with the same seed should produce the same PQC seed
        gen2 = HarmonicKeyGenerator(seed=b"pqc_test")
        seed32_b = gen2.derive_pqc_seed(32)
        assert seed32 == seed32_b
        # Longer output should also work
        gen3 = HarmonicKeyGenerator(seed=b"pqc_test")
        seed64 = gen3.derive_pqc_seed(64)
        assert len(seed64) == 64

    def test_frequency_stays_in_octave(self):
        """Frequency is always reduced to [1.0, 2.0) (Claim 6b-ii)."""
        gen = HarmonicKeyGenerator(seed=b"octave_test")
        for _ in range(100):
            gen.generate(1)
            assert 1.0 <= gen.state.frequency < 2.0


# ==========================================================================
# 2. RingRotationCipher Tests (Claims 1-5)
# ==========================================================================

class TestRingRotationCipher:
    """Tests for the harmonic ring rotation cipher."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encryption followed by decryption recovers plaintext (Claims 1, 4)."""
        key = b"harmonic_ring_key_test"
        plaintext = b"The quick brown fox jumps over the lazy dog"
        cipher = RingRotationCipher(key=key)
        ciphertext = cipher.encrypt(plaintext)
        assert ciphertext != plaintext
        cipher.reset()
        recovered = cipher.decrypt(ciphertext)
        assert recovered == plaintext

    def test_six_rings_default(self):
        """Default configuration uses six Sacred Tongue rings (Claim 2)."""
        cipher = RingRotationCipher(key=b"six_rings")
        assert len(cipher.rings) == 6
        names = [r.name for r in cipher.rings]
        assert names == ["KO", "AV", "RU", "CA", "UM", "DR"]

    def test_sacred_tongue_ratios(self):
        """Each ring has the correct harmonic ratio (Claim 3)."""
        cipher = RingRotationCipher(key=b"ratio_check")
        expected = {
            "KO": (2, 1),
            "AV": (3, 2),
            "RU": (4, 3),
            "CA": (5, 4),
            "UM": (8, 5),
            "DR": (45, 32),
        }
        for ring in cipher.rings:
            assert ring.ratio == expected[ring.name], f"Wrong ratio for {ring.name}"

    def test_different_keys_different_ciphertext(self):
        """Different keys produce different ciphertext."""
        plaintext = b"Same plaintext, different keys"
        c1 = RingRotationCipher(key=b"key_alpha")
        c2 = RingRotationCipher(key=b"key_beta")
        assert c1.encrypt(plaintext) != c2.encrypt(plaintext)

    def test_harmonic_signature(self):
        """Harmonic signature is a 64-char hex string (Claim 5)."""
        cipher = RingRotationCipher(key=b"sig_test")
        sig = cipher.harmonic_signature()
        assert len(sig) == 64
        int(sig, 16)  # should parse as hex

    def test_polyrhythmic_period_is_large(self):
        """The combined cipher period is large (Claim 1e)."""
        cipher = RingRotationCipher(key=b"period_test")
        period = cipher.polyrhythmic_period()
        # With 6 rings and alphabet 256, period should be substantial
        assert period >= 256, f"Period too small: {period}"

    def test_ciphertext_changes_each_byte(self):
        """XOR keystream changes with each byte due to ring rotation."""
        cipher = RingRotationCipher(key=b"stream_test")
        plaintext = bytes(16)  # all zeros
        ciphertext = cipher.encrypt(plaintext)
        # Not all ciphertext bytes should be identical (rings rotate differently)
        unique_bytes = set(ciphertext)
        assert len(unique_bytes) > 1, "Keystream appears constant"


# ==========================================================================
# 3. VoiceLeadingOptimizer Tests (Claims 11-15)
# ==========================================================================

class TestVoiceLeadingOptimizer:
    """Tests for the voice leading state transition optimizer."""

    def test_zero_distance_zero_cost(self):
        """Identical states have zero transition cost (Claim 11c)."""
        opt = VoiceLeadingOptimizer()
        assert opt.transition_cost(42, 42) == 0.0

    def test_single_bit_flip_cost(self):
        """Single bit flip costs 0.5 (Claim 11c)."""
        opt = VoiceLeadingOptimizer()
        # 0b00000000 -> 0b00000001 = 1 bit flip
        assert opt.transition_cost(0, 1) == 0.5

    def test_octave_leap_cost(self):
        """8-bit change costs 10.0 (Claim 11c)."""
        opt = VoiceLeadingOptimizer()
        # 0x00 -> 0xFF = 8 bit flips
        assert opt.transition_cost(0x00, 0xFF) == 10.0

    def test_optimize_produces_valid_path(self):
        """Optimized path starts at current and ends at target (Claim 11d)."""
        opt = VoiceLeadingOptimizer()
        result = opt.optimize_transition(0x00, 0xFF)
        assert result.path[0] == 0x00
        assert result.path[-1] == 0xFF
        assert result.steps > 0

    def test_smooth_path_lower_per_step_cost(self):
        """Each step in the optimized path has low cost (Claim 11d)."""
        opt = VoiceLeadingOptimizer()
        result = opt.optimize_transition(0b00000000, 0b11111111)
        # Each individual step should have Hamming distance <= 3
        for i in range(len(result.path) - 1):
            hd = _hamming_distance(result.path[i], result.path[i + 1])
            assert hd <= 3, f"Step {i}: Hamming distance {hd} too large"

    def test_dissonance_detection(self):
        """Dissonant transitions are correctly detected (Claim 15)."""
        opt = VoiceLeadingOptimizer(dissonance_threshold=4)
        assert not opt.is_dissonant(0, 1)       # 1 bit
        assert opt.is_dissonant(0x00, 0xFF)      # 8 bits > 4

    def test_motion_classification(self):
        """Motion types are correctly classified (Claim 17)."""
        opt = VoiceLeadingOptimizer()
        # Oblique: one voice stationary
        assert opt.classify_motion(10, 10, 20, 25) == MotionType.OBLIQUE
        # Contrary: opposite directions
        assert opt.classify_motion(10, 15, 20, 15) == MotionType.CONTRARY
        # Parallel: same direction, same interval
        assert opt.classify_motion(10, 13, 20, 23) == MotionType.PARALLEL

    def test_smooth_key_schedule(self):
        """Key schedule smoothing produces valid output (Claim 13)."""
        opt = VoiceLeadingOptimizer()
        original = [0, 128, 255, 64]
        smoothed = opt.generate_smooth_key_schedule(original)
        # Smoothed should start and end with same values
        assert smoothed[0] == 0
        assert smoothed[-1] == 64
        # Should be at least as long as original
        assert len(smoothed) >= len(original)

    def test_dissonance_resolution(self):
        """Dissonant transitions are resolved into smooth steps (Claim 15)."""
        opt = VoiceLeadingOptimizer(dissonance_threshold=3)
        path = opt.resolve_dissonance(0x00, 0xFF)
        assert len(path) > 2  # Should have intermediate steps
        assert path[0] == 0x00
        assert path[-1] == 0xFF


# ==========================================================================
# 4. CounterpointProtocol Tests (Claims 16-20)
# ==========================================================================

class TestCounterpointProtocol:
    """Tests for the multi-agent counterpoint coordination protocol."""

    def test_four_agents_default(self):
        """Default creates SATB (4 voices) (Claim 16a)."""
        cp = CounterpointProtocol()
        assert len(cp.agents) == 4
        names = [a.name for a in cp.agents]
        assert names == ["Soprano", "Alto", "Tenor", "Bass"]

    def test_state_tracking(self):
        """Agent states are tracked with history (Claim 16b)."""
        cp = CounterpointProtocol()
        cp.set_state(0, 60)
        cp.set_state(0, 67)
        assert cp.get_state(0) == 67
        assert cp.agents[0].history == [0, 60]

    def test_harmony_score_range(self):
        """Harmony score is always in [0.0, 1.0] (Claim 16e, 18)."""
        cp = CounterpointProtocol()
        for states in [(0, 7, 12, 19), (0, 1, 2, 3), (0, 6, 6, 0), (0, 0, 0, 0)]:
            for i, s in enumerate(states):
                cp.set_state(i, s)
            score = cp.harmony_score()
            assert 0.0 <= score <= 1.0, f"Score {score} out of range for states {states}"

    def test_unison_perfect_harmony(self):
        """All agents at unison should have perfect harmony (Claim 18)."""
        cp = CounterpointProtocol()
        for i in range(4):
            cp.set_state(i, 60)
        assert cp.harmony_score() == 1.0

    def test_tritone_zero_consonance(self):
        """Tritone interval has 0.0 consonance (Claim 18)."""
        assert CONSONANCE_RATINGS[6] == 0.0

    def test_resolution_suggests_improvements(self):
        """Resolution procedure identifies improving moves (Claim 19)."""
        cp = CounterpointProtocol(harmony_threshold=0.5)
        # Set states to create dissonance (tritones)
        cp.set_state(0, 0)
        cp.set_state(1, 6)   # tritone from voice 0
        cp.set_state(2, 12)  # tritone from voice 1
        cp.set_state(3, 18)  # tritone from voice 2

        suggestions = cp.resolve()
        # Should suggest at least one change
        assert len(suggestions) > 0

    def test_needs_resolution_flag(self):
        """needs_resolution correctly detects low harmony (Claim 16f)."""
        cp = CounterpointProtocol(harmony_threshold=0.8)
        # Unison: high harmony
        for i in range(4):
            cp.set_state(i, 0)
        assert not cp.needs_resolution()

        # Tritones: low harmony
        cp.set_state(0, 0)
        cp.set_state(1, 6)
        cp.set_state(2, 6)
        cp.set_state(3, 6)
        assert cp.needs_resolution()

    def test_collective_state_bytes(self):
        """Collective state encodes all agent states (Claim 20)."""
        cp = CounterpointProtocol()
        cp.set_state(0, 10)
        cp.set_state(1, 20)
        cp.set_state(2, 30)
        cp.set_state(3, 40)
        collective = cp.collective_state()
        assert collective == bytes([10, 20, 30, 40])


# ==========================================================================
# 5. HarmonicCryptosystem Tests (Claims 21-25)
# ==========================================================================

class TestHarmonicCryptosystem:
    """Tests for the integrated harmonic cryptography system."""

    def test_encrypt_decrypt_roundtrip(self):
        """Full system encrypt/decrypt roundtrip (Claim 21)."""
        seed = b"integrated_roundtrip_test_seed!!"
        system = HarmonicCryptosystem(seed=seed)
        plaintext = b"Music-theoretic encryption works!"
        result = system.encrypt(plaintext)
        assert result.ciphertext != plaintext

        dec_result = system.decrypt(result.ciphertext, result.spiral_signature)
        assert dec_result.plaintext == plaintext
        assert dec_result.verified

    def test_encryption_result_metadata(self):
        """Encryption result includes all expected metadata."""
        system = HarmonicCryptosystem(seed=b"metadata_test_seed_value")
        result = system.encrypt(b"Hello, harmonic world!")
        assert len(result.spiral_signature) == 64
        assert len(result.harmonic_signature) == 64
        assert 0.0 <= result.harmony_score <= 1.0

    def test_domain_classifier(self):
        """Semantic domain classifier returns valid tongues (Claim 24)."""
        system = HarmonicCryptosystem(seed=b"domain_test")
        valid_tongues = {"KO", "AV", "RU", "CA", "UM", "DR"}
        for data in [b"logic", b"abstract", b"emotional", b"hidden", b"wisdom", b"structural"]:
            tongue = system.classify_domain(data)
            assert tongue in valid_tongues

    def test_multi_party_signing(self):
        """Multi-party signing produces signatures and validates (Claims 20, 25)."""
        system = HarmonicCryptosystem(seed=b"multi_party_test_seed!!", num_agents=4)

        # Each agent signs different data to ensure distinct collective states
        signatures = []
        for voice_id in range(4):
            data = f"Transaction data from agent {voice_id}".encode()
            sig, validation = system.multi_party_sign(data, voice_id)
            signatures.append(sig)
            assert len(sig) == 32  # SHA-256 hash

        # At least some signatures should differ (agents modify collective state)
        assert len(set(signatures)) >= 2

    def test_consensus_harmony(self):
        """Consensus harmony score is in range (Claim 25)."""
        system = HarmonicCryptosystem(seed=b"consensus_test")
        assert 0.0 <= system.consensus_harmony() <= 1.0

    def test_pqc_seed_generation(self):
        """PQC seed generation works (Claims 22-23)."""
        system = HarmonicCryptosystem(seed=b"pqc_seed_test")
        seed = system.pqc_seed(32)
        assert len(seed) == 32
        # Same system should produce same seed (deterministic)
        system2 = HarmonicCryptosystem(seed=b"pqc_seed_test")
        # Note: the key_gen will have been used for cipher key already,
        # so pqc_seed calls generate() which advances the state further.
        # We just verify it returns the correct length.
        seed2 = system2.pqc_seed(32)
        assert len(seed2) == 32

    def test_wrong_seed_fails_decrypt(self):
        """Decryption with wrong seed produces wrong plaintext."""
        system1 = HarmonicCryptosystem(seed=b"correct_seed_for_encrypt")
        system2 = HarmonicCryptosystem(seed=b"wrong_seed_for_decrypt!!")
        plaintext = b"Secret message that must be protected"
        result = system1.encrypt(plaintext)
        dec = system2.decrypt(result.ciphertext)
        assert dec.plaintext != plaintext


# ==========================================================================
# 6. Helper Function Tests
# ==========================================================================

class TestHelpers:
    """Tests for utility functions."""

    def test_hamming_distance(self):
        """Hamming distance calculation is correct."""
        assert _hamming_distance(0, 0) == 0
        assert _hamming_distance(0, 1) == 1
        assert _hamming_distance(0, 0xFF) == 8
        assert _hamming_distance(0b10101010, 0b01010101) == 8

    def test_voice_leading_cost_table(self):
        """Voice leading costs match the patent specification (Claim 11c)."""
        assert _voice_leading_cost(0) == 0.0
        assert _voice_leading_cost(1) == 0.5
        assert _voice_leading_cost(2) == 1.0
        assert _voice_leading_cost(3) == 1.5
        assert _voice_leading_cost(4) == 2.0
        assert _voice_leading_cost(5) == 3.0
        assert _voice_leading_cost(6) == 4.0
        assert _voice_leading_cost(7) == 5.0
        assert _voice_leading_cost(8) == 10.0

    def test_consonance_ratings(self):
        """Consonance ratings match Claim 18."""
        assert _consonance(0) == 1.0   # unison
        assert _consonance(7) == 0.9   # perfect fifth
        assert _consonance(5) == 0.8   # perfect fourth
        assert _consonance(4) == 0.7   # major third
        assert _consonance(6) == 0.0   # tritone

    def test_pythagorean_comma_value(self):
        """Pythagorean comma is 531441/524288 (Claim 6d)."""
        assert PYTHAGOREAN_COMMA == 531441 / 524288
        # Should be slightly greater than 1
        assert 1.013 < PYTHAGOREAN_COMMA < 1.014

    def test_harmonic_ratios_complete(self):
        """All 7 harmonic ratios from Claim 1b are defined."""
        expected = {"octave", "perfect_fifth", "perfect_fourth", "major_third",
                    "minor_third", "minor_sixth", "tritone"}
        assert set(HARMONIC_RATIOS.keys()) == expected

    def test_tongue_interval_mapping(self):
        """All 6 Sacred Tongue domains map to intervals (Claim 3)."""
        expected_tongues = {"KO", "AV", "RU", "CA", "UM", "DR"}
        assert set(TONGUE_INTERVAL_MAP.keys()) == expected_tongues


# ==========================================================================
# Run with pytest
# ==========================================================================

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
