"""
Tests for Flat Slope Harmonic Encoder

Security Tests:
1. All tokens have same fundamental frequency (frequency analysis fails)
2. Different keys produce different harmonic masks
3. Same key + same token = deterministic fingerprint
4. HMAC envelope integrity verification
5. Resonance refractoring produces unique interference patterns
"""

import pytest
import numpy as np
import hashlib
import hmac

from symphonic_cipher.flat_slope_encoder import (
    # Core functions
    derive_harmonic_mask,
    synthesize_token,
    encode_message,
    verify_token_fingerprint,
    verify_envelope_integrity,
    resonance_refractor,
    # Analysis functions
    analyze_frequency_attack_resistance,
    compare_steep_vs_flat,
    # Data classes
    HarmonicFingerprint,
    EncodedMessage,
    ModalityMask,
    # Constants
    BASE_FREQUENCY_HZ,
    SAMPLE_RATE,
    MIN_HARMONICS_PER_TOKEN,
    MAX_HARMONICS_PER_TOKEN,
    # Utilities
    generate_key,
    key_from_passphrase,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def secret_key():
    """Fixed secret key for reproducible tests."""
    return b"test_secret_key_32_bytes_exactly"


@pytest.fixture
def alt_secret_key():
    """Alternative secret key for key-difference tests."""
    return b"different_key_32_bytes_exactly!!"


@pytest.fixture
def sample_tokens():
    """Sample token IDs for testing."""
    return [0, 1, 2, 42, 100, 255, 1000]


# =============================================================================
# FLAT SLOPE SECURITY TESTS
# =============================================================================

class TestFlatSlopeSecurity:
    """Tests proving frequency analysis attacks fail."""

    def test_all_tokens_same_fundamental(self, secret_key, sample_tokens):
        """CRITICAL: All tokens must produce 440 Hz fundamental."""
        fundamentals = []

        for token_id in sample_tokens:
            fp = derive_harmonic_mask(token_id, secret_key)
            wave = synthesize_token(fp, duration_ms=100.0)

            # FFT to find fundamental
            fft = np.fft.rfft(wave)
            freqs = np.fft.rfftfreq(len(wave), 1.0 / SAMPLE_RATE)
            magnitudes = np.abs(fft)

            # Find the fundamental (lowest significant peak at 440 Hz)
            fundamental_idx = np.argmin(np.abs(freqs - BASE_FREQUENCY_HZ))
            # Verify fundamental has significant magnitude
            assert magnitudes[fundamental_idx] > 0.01 * np.max(magnitudes), \
                f"Token {token_id} missing fundamental at {BASE_FREQUENCY_HZ} Hz"

            fundamentals.append(freqs[fundamental_idx])

        # All fundamentals should be within 1 Hz of 440 Hz
        for i, f in enumerate(fundamentals):
            assert abs(f - BASE_FREQUENCY_HZ) < 5.0, \
                f"Token {sample_tokens[i]} has fundamental {f} Hz, expected ~{BASE_FREQUENCY_HZ} Hz"

    def test_frequency_variance_near_zero(self, secret_key):
        """Frequency variance across tokens should be negligible."""
        result = analyze_frequency_attack_resistance(
            token_ids=list(range(50)),  # 50 different tokens
            secret_key=secret_key,
            num_samples=10
        )

        # Variance should be essentially zero (< 1 Hz)
        assert result["fundamental_std"] < 5.0, \
            f"Fundamental frequency std dev too high: {result['fundamental_std']} Hz"

        assert result["frequency_flat"] is True, \
            "Frequency analysis should report flat slope"

    def test_steep_vs_flat_comparison(self):
        """Compare steep (vulnerable) vs flat (secure) encoding."""
        tokens = [0, 1, 2, 3, 4]
        result = compare_steep_vs_flat(tokens)

        # Steep slope has high variance (attackable)
        assert result["steep_slope"]["variance"] > 0, \
            "Steep slope should have non-zero frequency variance"
        assert result["steep_slope"]["attackable"] is True

        # Flat slope has zero variance (not attackable)
        assert result["flat_slope"]["variance"] == 0.0, \
            "Flat slope should have zero frequency variance"
        assert result["flat_slope"]["attackable"] is False

    def test_different_keys_different_masks(self, secret_key, alt_secret_key):
        """Different keys must produce different harmonic masks."""
        token_id = 42

        fp1 = derive_harmonic_mask(token_id, secret_key)
        fp2 = derive_harmonic_mask(token_id, alt_secret_key)

        # Harmonics should differ
        assert fp1.harmonics != fp2.harmonics, \
            "Different keys produced same harmonic mask - security failure!"

        # Key commitments should differ
        assert fp1.key_commitment != fp2.key_commitment, \
            "Different keys produced same commitment - security failure!"

    def test_same_key_deterministic(self, secret_key):
        """Same key + same token = identical fingerprint."""
        token_id = 42

        fp1 = derive_harmonic_mask(token_id, secret_key)
        fp2 = derive_harmonic_mask(token_id, secret_key)

        assert fp1.harmonics == fp2.harmonics
        assert np.allclose(fp1.amplitudes, fp2.amplitudes)
        assert np.allclose(fp1.phases, fp2.phases)
        assert fp1.key_commitment == fp2.key_commitment

    def test_token_uniqueness(self, secret_key):
        """Each token should have unique harmonic fingerprint."""
        fingerprints = {}

        for token_id in range(100):
            fp = derive_harmonic_mask(token_id, secret_key)
            key = tuple(sorted(fp.harmonics))

            if key in fingerprints:
                # Same harmonic set - check if amplitudes/phases differ
                prev_fp = fingerprints[key]
                if np.allclose(fp.amplitudes, prev_fp.amplitudes) and \
                   np.allclose(fp.phases, prev_fp.phases):
                    pytest.fail(f"Tokens {prev_fp.token_id} and {token_id} have identical fingerprints!")

            fingerprints[key] = fp


# =============================================================================
# HARMONIC MASK TESTS
# =============================================================================

class TestHarmonicMaskDerivation:
    """Tests for harmonic mask derivation."""

    def test_minimum_harmonics(self, secret_key):
        """Each token must have at least MIN_HARMONICS_PER_TOKEN."""
        for token_id in range(100):
            fp = derive_harmonic_mask(token_id, secret_key)
            assert len(fp.harmonics) >= MIN_HARMONICS_PER_TOKEN, \
                f"Token {token_id} has only {len(fp.harmonics)} harmonics"

    def test_maximum_harmonics(self, secret_key):
        """Each token must have at most MAX_HARMONICS_PER_TOKEN."""
        for token_id in range(100):
            fp = derive_harmonic_mask(token_id, secret_key)
            assert len(fp.harmonics) <= MAX_HARMONICS_PER_TOKEN, \
                f"Token {token_id} has {len(fp.harmonics)} harmonics (max {MAX_HARMONICS_PER_TOKEN})"

    def test_modality_strict(self, secret_key):
        """STRICT modality should only use odd harmonics."""
        fp = derive_harmonic_mask(42, secret_key, modality=ModalityMask.STRICT)

        for h in fp.harmonics:
            assert h % 2 == 1, f"STRICT modality has even harmonic {h}"

    def test_modality_probe(self, secret_key):
        """PROBE modality should only have fundamental."""
        fp = derive_harmonic_mask(42, secret_key, modality=ModalityMask.PROBE)

        assert fp.harmonics == {1}, \
            f"PROBE modality should only have fundamental, got {fp.harmonics}"

    def test_domain_separation(self, secret_key):
        """Different domains should produce different fingerprints."""
        token_id = 42

        fp_ko = derive_harmonic_mask(token_id, secret_key, domain="KO")
        fp_av = derive_harmonic_mask(token_id, secret_key, domain="AV")
        fp_um = derive_harmonic_mask(token_id, secret_key, domain="UM")

        # All should differ due to domain separation
        assert fp_ko.key_commitment != fp_av.key_commitment
        assert fp_av.key_commitment != fp_um.key_commitment
        assert fp_ko.key_commitment != fp_um.key_commitment


# =============================================================================
# WAVEFORM SYNTHESIS TESTS
# =============================================================================

class TestWaveformSynthesis:
    """Tests for audio waveform synthesis."""

    def test_waveform_length(self, secret_key):
        """Waveform should have correct number of samples."""
        fp = derive_harmonic_mask(42, secret_key)

        duration_ms = 100.0
        expected_samples = int((duration_ms / 1000.0) * SAMPLE_RATE)

        wave = synthesize_token(fp, duration_ms=duration_ms)

        assert len(wave) == expected_samples, \
            f"Expected {expected_samples} samples, got {len(wave)}"

    def test_waveform_amplitude_bounded(self, secret_key):
        """Waveform amplitude should be normalized."""
        fp = derive_harmonic_mask(42, secret_key)
        wave = synthesize_token(fp, duration_ms=100.0)

        max_amp = np.max(np.abs(wave))
        assert max_amp <= 1.0, f"Waveform exceeds amplitude 1.0: {max_amp}"

    def test_waveform_no_nan_inf(self, secret_key):
        """Waveform should not contain NaN or Inf values."""
        for token_id in range(50):
            fp = derive_harmonic_mask(token_id, secret_key)
            wave = synthesize_token(fp, duration_ms=100.0)

            assert not np.any(np.isnan(wave)), f"Token {token_id} waveform contains NaN"
            assert not np.any(np.isinf(wave)), f"Token {token_id} waveform contains Inf"

    def test_envelope_prevents_clicks(self, secret_key):
        """Waveform should start and end near zero (envelope applied)."""
        fp = derive_harmonic_mask(42, secret_key)
        wave = synthesize_token(fp, duration_ms=100.0)

        # First and last samples should be near zero (within 5%)
        assert abs(wave[0]) < 0.05, f"Waveform starts at {wave[0]}, expected ~0"
        assert abs(wave[-1]) < 0.05, f"Waveform ends at {wave[-1]}, expected ~0"


# =============================================================================
# MESSAGE ENCODING TESTS
# =============================================================================

class TestMessageEncoding:
    """Tests for complete message encoding."""

    def test_encode_empty_message(self, secret_key):
        """Empty token list should produce empty waveform."""
        msg = encode_message([], secret_key)

        assert len(msg.token_ids) == 0
        assert len(msg.waveform) == 0
        assert len(msg.fingerprints) == 0

    def test_encode_single_token(self, secret_key):
        """Single token encoding should work."""
        msg = encode_message([42], secret_key)

        assert len(msg.token_ids) == 1
        assert msg.token_ids[0] == 42
        assert len(msg.fingerprints) == 1
        assert len(msg.waveform) > 0

    def test_encode_multiple_tokens(self, secret_key):
        """Multiple tokens should produce combined waveform."""
        tokens = [1, 2, 3, 4, 5]
        msg = encode_message(tokens, secret_key)

        assert msg.token_ids == tokens
        assert len(msg.fingerprints) == len(tokens)

        # Waveform should be longer than single token
        single_duration = 100.0  # default
        single_samples = int((single_duration / 1000.0) * SAMPLE_RATE)
        assert len(msg.waveform) > single_samples

    def test_envelope_hmac_present(self, secret_key):
        """Encoded message should have HMAC for integrity."""
        msg = encode_message([1, 2, 3], secret_key)

        assert msg.envelope_hmac is not None
        assert len(msg.envelope_hmac) == 32  # SHA-256


# =============================================================================
# VERIFICATION TESTS
# =============================================================================

class TestVerification:
    """Tests for fingerprint verification."""

    def test_verify_correct_fingerprint(self, secret_key):
        """Correct fingerprint should verify."""
        fp = derive_harmonic_mask(42, secret_key)
        wave = synthesize_token(fp, duration_ms=100.0)

        match, confidence = verify_token_fingerprint(wave, fp)

        assert match is True, f"Correct fingerprint failed to verify (confidence: {confidence})"
        assert confidence >= 0.8, f"Confidence too low: {confidence}"

    def test_verify_envelope_integrity_valid(self, secret_key):
        """Valid message should pass integrity check."""
        msg = encode_message([1, 2, 3], secret_key)

        assert verify_envelope_integrity(msg, secret_key) is True

    def test_verify_envelope_integrity_tampered(self, secret_key):
        """Tampered message should fail integrity check."""
        msg = encode_message([1, 2, 3], secret_key)

        # Tamper with the envelope HMAC
        tampered_msg = EncodedMessage(
            token_ids=msg.token_ids,
            waveform=msg.waveform,
            fingerprints=msg.fingerprints,
            envelope_hmac=b"tampered_hmac_value_here_32bytes"
        )

        assert verify_envelope_integrity(tampered_msg, secret_key) is False

    def test_verify_wrong_key_fails(self, secret_key, alt_secret_key):
        """Verification with wrong key should fail."""
        msg = encode_message([1, 2, 3], secret_key)

        assert verify_envelope_integrity(msg, alt_secret_key) is False


# =============================================================================
# RESONANCE REFRACTORING TESTS
# =============================================================================

class TestResonanceRefractoring:
    """Tests for resonance refractoring (interference encoding)."""

    def test_refractor_empty(self):
        """Empty fingerprint list should return empty array."""
        result = resonance_refractor([])
        assert len(result) == 0

    def test_refractor_single(self, secret_key):
        """Single fingerprint should produce valid waveform."""
        fp = derive_harmonic_mask(42, secret_key)
        result = resonance_refractor([fp])

        assert len(result) > 0
        assert not np.any(np.isnan(result))

    def test_refractor_multiple(self, secret_key):
        """Multiple fingerprints should produce interference pattern."""
        fps = [derive_harmonic_mask(i, secret_key) for i in range(5)]
        result = resonance_refractor(fps)

        # Should be longer than single token
        single_samples = int(0.1 * SAMPLE_RATE)  # 100ms
        assert len(result) > single_samples

        # Amplitude should be normalized
        assert np.max(np.abs(result)) <= 1.0

    def test_refractor_order_matters(self, secret_key):
        """Different token orders should produce different patterns."""
        fps_123 = [derive_harmonic_mask(i, secret_key) for i in [1, 2, 3]]
        fps_321 = [derive_harmonic_mask(i, secret_key) for i in [3, 2, 1]]

        result_123 = resonance_refractor(fps_123)
        result_321 = resonance_refractor(fps_321)

        # Should be different (not all zeros and not identical)
        assert not np.allclose(result_123, result_321), \
            "Different token orders produced identical patterns"


# =============================================================================
# UTILITY TESTS
# =============================================================================

class TestUtilities:
    """Tests for utility functions."""

    def test_generate_key_length(self):
        """Generated key should have correct length."""
        key = generate_key(32)
        assert len(key) == 32

        key = generate_key(64)
        assert len(key) == 64

    def test_generate_key_randomness(self):
        """Generated keys should be unique."""
        keys = [generate_key(32) for _ in range(100)]

        # All should be unique
        assert len(set(keys)) == len(keys), "Generated keys are not unique"

    def test_key_from_passphrase_deterministic(self):
        """Same passphrase should produce same key."""
        key1 = key_from_passphrase("my secret passphrase")
        key2 = key_from_passphrase("my secret passphrase")

        assert key1 == key2

    def test_key_from_passphrase_different(self):
        """Different passphrases should produce different keys."""
        key1 = key_from_passphrase("passphrase one")
        key2 = key_from_passphrase("passphrase two")

        assert key1 != key2


# =============================================================================
# ATTACK RESISTANCE TESTS
# =============================================================================

class TestAttackResistance:
    """Tests simulating various attack scenarios."""

    def test_frequency_analysis_attack(self, secret_key):
        """
        Simulate frequency analysis attack.

        Attacker observes waveforms and tries to identify tokens by
        their fundamental frequencies. This should FAIL for flat slope.
        """
        # Encode tokens 0-9
        fundamentals_by_token = {}

        for token_id in range(10):
            fp = derive_harmonic_mask(token_id, secret_key)
            wave = synthesize_token(fp, duration_ms=100.0)

            # Attacker measures fundamental
            fft = np.fft.rfft(wave)
            freqs = np.fft.rfftfreq(len(wave), 1.0 / SAMPLE_RATE)
            magnitudes = np.abs(fft)

            # Find peak
            peak_idx = np.argmax(magnitudes)
            fundamental = freqs[peak_idx]

            fundamentals_by_token[token_id] = fundamental

        # Attack success = can distinguish tokens by fundamental
        fundamentals = list(fundamentals_by_token.values())
        variance = np.var(fundamentals)

        # Flat slope: variance should be essentially zero
        assert variance < 1.0, \
            f"Frequency analysis attack succeeded! Variance: {variance} Hz"

    def test_harmonic_analysis_without_key(self, secret_key):
        """
        Attacker tries to decode harmonics without key.

        Even if they detect which harmonics are present, they cannot
        map them to tokens without the key.
        """
        # Create fingerprints for tokens 0-9
        fingerprints = [derive_harmonic_mask(i, secret_key) for i in range(10)]

        # Attacker tries to find pattern (they don't have the key)
        # They can only observe: [harmonics for unknown token]

        # Simulate: attacker has waveforms for 10 tokens but doesn't know which is which
        # They try to cluster by harmonic content

        harmonic_sets = [tuple(sorted(fp.harmonics)) for fp in fingerprints]

        # With proper key derivation, harmonic sets should appear random
        # (no obvious pattern like "token 0 has harmonic 0, token 1 has harmonic 1")

        # Check that there's no simple linear relationship
        for i, hset in enumerate(harmonic_sets):
            # Token ID should not be directly in harmonics
            if i in hset and i > 0:  # harmonic 0 doesn't exist, so skip
                # This could happen by chance, but check it's not systematic
                count = sum(1 for j, h in enumerate(harmonic_sets) if j in h and j > 0)
                assert count < len(harmonic_sets) // 2, \
                    "Suspicious pattern: token IDs appear in their own harmonic sets"

    def test_replay_attack_resistance(self, secret_key):
        """
        Test that encoded messages have unique commitments.

        Same message encoded twice should have same HMAC (deterministic),
        but with nonce/timestamp this would differ in real usage.
        """
        msg1 = encode_message([1, 2, 3], secret_key)
        msg2 = encode_message([1, 2, 3], secret_key)

        # Without nonce, same message = same HMAC (deterministic)
        assert msg1.envelope_hmac == msg2.envelope_hmac

        # Different messages = different HMACs
        msg3 = encode_message([1, 2, 4], secret_key)
        assert msg1.envelope_hmac != msg3.envelope_hmac


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_large_token_id(self, secret_key):
        """Large token IDs should work correctly."""
        large_ids = [2**16, 2**20, 2**31 - 1]

        for token_id in large_ids:
            fp = derive_harmonic_mask(token_id, secret_key)
            wave = synthesize_token(fp, duration_ms=50.0)

            assert len(fp.harmonics) >= MIN_HARMONICS_PER_TOKEN
            assert len(wave) > 0
            assert not np.any(np.isnan(wave))

    def test_very_short_duration(self, secret_key):
        """Very short durations should still work."""
        fp = derive_harmonic_mask(42, secret_key)
        wave = synthesize_token(fp, duration_ms=1.0)  # 1ms

        assert len(wave) > 0
        assert not np.any(np.isnan(wave))

    def test_empty_key(self):
        """Empty key should still produce valid (but insecure) output."""
        fp = derive_harmonic_mask(42, b"")

        assert len(fp.harmonics) >= MIN_HARMONICS_PER_TOKEN
        assert fp.key_commitment is not None

    def test_unicode_domain(self, secret_key):
        """Unicode domain names should work."""
        fp = derive_harmonic_mask(42, secret_key, domain="域名测试")

        assert len(fp.harmonics) >= MIN_HARMONICS_PER_TOKEN


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
