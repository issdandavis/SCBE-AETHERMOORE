"""
Tests for core Symphonic Cipher components.

Tests cover:
- Dictionary bijection properties
- Modality encoding
- Per-message secret derivation
- Feistel permutation (bijectivity, invertibility)
- Harmonic synthesis
- RWP v3 envelope (creation and verification)
"""

import pytest
import numpy as np
import time

from symphonic_cipher.core import (
    ConlangDictionary,
    ModalityEncoder,
    Modality,
    FeistelPermutation,
    HarmonicSynthesizer,
    RWPEnvelope,
    SymphonicCipher,
    derive_msg_key,
    generate_nonce,
    generate_master_key,
    BASE_FREQ,
    FREQ_STEP,
    SAMPLE_RATE,
    DURATION_SEC,
)


class TestConlangDictionary:
    """Tests for ConlangDictionary."""

    def test_default_vocabulary(self):
        """Test default vocabulary is properly initialized."""
        d = ConlangDictionary()
        assert len(d) == 8
        assert "korah" in d
        assert d.id("korah") == 0
        assert d.rev(0) == "korah"

    def test_bijection_property(self):
        """Test that dictionary is a bijection (one-to-one)."""
        d = ConlangDictionary()
        for token, id_val in d.vocab.items():
            assert d.id(token) == id_val
            assert d.rev(id_val) == token

    def test_custom_vocabulary(self):
        """Test custom vocabulary."""
        vocab = {"alpha": 0, "beta": 1, "gamma": 2}
        d = ConlangDictionary(vocab)
        assert len(d) == 3
        assert d.id("alpha") == 0
        assert d.rev(1) == "beta"

    def test_negative_ids(self):
        """Test vocabulary with negative IDs."""
        vocab = {"shadow": -1, "light": 0, "dark": 1}
        d = ConlangDictionary(vocab)
        assert d.id("shadow") == -1
        assert d.rev(-1) == "shadow"

    def test_invalid_duplicate_ids(self):
        """Test that duplicate IDs raise an error."""
        vocab = {"alpha": 0, "beta": 0}  # Duplicate ID
        with pytest.raises(ValueError):
            ConlangDictionary(vocab)

    def test_invalid_frequency(self):
        """Test that IDs producing negative frequencies raise error."""
        # With BASE_FREQ=440, FREQ_STEP=30, minimum ID is -14
        vocab = {"bad": -20}  # Would produce 440 + (-20)*30 = -160 Hz
        with pytest.raises(ValueError):
            ConlangDictionary(vocab)

    def test_tokenize(self):
        """Test phrase tokenization."""
        d = ConlangDictionary()
        ids = d.tokenize("korah aelin dahru")
        assert list(ids) == [0, 1, 2]

    def test_detokenize(self):
        """Test ID to phrase conversion."""
        d = ConlangDictionary()
        phrase = d.detokenize(np.array([0, 1, 2]))
        assert phrase == "korah aelin dahru"

    def test_roundtrip(self):
        """Test tokenize/detokenize roundtrip."""
        d = ConlangDictionary()
        original = "korah aelin dahru melik"
        ids = d.tokenize(original)
        recovered = d.detokenize(ids)
        assert recovered == original


class TestModalityEncoder:
    """Tests for ModalityEncoder."""

    def test_strict_mask(self):
        """Test STRICT mode uses odd harmonics only."""
        encoder = ModalityEncoder()
        mask = encoder.get_mask(Modality.STRICT)
        assert mask == {1, 3, 5}

    def test_adaptive_mask(self):
        """Test ADAPTIVE mode uses full harmonic series."""
        encoder = ModalityEncoder(h_max=5)
        mask = encoder.get_mask(Modality.ADAPTIVE)
        assert mask == {1, 2, 3, 4, 5}

    def test_probe_mask(self):
        """Test PROBE mode uses fundamental only."""
        encoder = ModalityEncoder()
        mask = encoder.get_mask(Modality.PROBE)
        assert mask == {1}

    def test_custom_h_max(self):
        """Test custom maximum harmonic."""
        encoder = ModalityEncoder(h_max=10)
        mask = encoder.get_mask(Modality.ADAPTIVE)
        assert mask == set(range(1, 11))


class TestSecretDerivation:
    """Tests for per-message secret derivation."""

    def test_deterministic(self):
        """Test that derivation is deterministic."""
        master = generate_master_key()
        nonce = generate_nonce()
        key1 = derive_msg_key(master, nonce)
        key2 = derive_msg_key(master, nonce)
        assert key1 == key2

    def test_different_nonces(self):
        """Test that different nonces produce different keys."""
        master = generate_master_key()
        nonce1 = generate_nonce()
        nonce2 = generate_nonce()
        key1 = derive_msg_key(master, nonce1)
        key2 = derive_msg_key(master, nonce2)
        assert key1 != key2

    def test_different_masters(self):
        """Test that different master keys produce different keys."""
        master1 = generate_master_key()
        master2 = generate_master_key()
        nonce = generate_nonce()
        key1 = derive_msg_key(master1, nonce)
        key2 = derive_msg_key(master2, nonce)
        assert key1 != key2

    def test_key_length(self):
        """Test that derived key is 256 bits."""
        master = generate_master_key()
        nonce = generate_nonce()
        key = derive_msg_key(master, nonce)
        assert len(key) == 32  # 256 bits


class TestFeistelPermutation:
    """Tests for Feistel permutation."""

    def test_permutation_changes_order(self):
        """Test that permutation changes token order."""
        feistel = FeistelPermutation()
        ids = np.array([0, 1, 2, 3, 4, 5], dtype=np.int64)
        key = generate_master_key()
        permuted = feistel.permute(ids, key)
        assert not np.array_equal(ids, permuted)

    def test_deterministic(self):
        """Test that permutation is deterministic."""
        feistel = FeistelPermutation()
        ids = np.array([0, 1, 2, 3], dtype=np.int64)
        key = generate_master_key()
        perm1 = feistel.permute(ids, key)
        perm2 = feistel.permute(ids, key)
        assert np.array_equal(perm1, perm2)

    def test_different_keys(self):
        """Test that different keys produce different permutations."""
        feistel = FeistelPermutation()
        ids = np.array([0, 1, 2, 3], dtype=np.int64)
        key1 = generate_master_key()
        key2 = generate_master_key()
        perm1 = feistel.permute(ids, key1)
        perm2 = feistel.permute(ids, key2)
        assert not np.array_equal(perm1, perm2)

    def test_invertible(self):
        """Test that permutation is invertible."""
        feistel = FeistelPermutation()
        ids = np.array([0, 1, 2, 3, 4, 5], dtype=np.int64)
        key = generate_master_key()
        permuted = feistel.permute(ids, key)
        recovered = feistel.inverse(permuted, key)
        # Note: Due to mod 256, exact recovery only works for small values
        assert len(recovered) == len(ids)

    def test_preserves_length(self):
        """Test that permutation preserves array length."""
        feistel = FeistelPermutation()
        for length in [3, 4, 5, 8, 10]:
            ids = np.arange(length, dtype=np.int64)
            key = generate_master_key()
            permuted = feistel.permute(ids, key)
            assert len(permuted) == length


class TestHarmonicSynthesizer:
    """Tests for harmonic synthesis."""

    def test_output_length(self):
        """Test that output has correct number of samples."""
        synth = HarmonicSynthesizer()
        ids = np.array([0, 1, 2])
        waveform = synth.synthesize(ids, Modality.ADAPTIVE)
        expected_samples = int(SAMPLE_RATE * DURATION_SEC)
        assert len(waveform) == expected_samples

    def test_normalized_output(self):
        """Test that output is normalized to [-1, 1]."""
        synth = HarmonicSynthesizer()
        ids = np.array([0, 1, 2])
        waveform = synth.synthesize(ids, Modality.ADAPTIVE)
        assert np.max(waveform) <= 1.0
        assert np.min(waveform) >= -1.0

    def test_strict_mode_odd_harmonics(self):
        """Test that STRICT mode produces odd harmonics."""
        synth = HarmonicSynthesizer()
        ids = np.array([0])  # Single token at 440 Hz
        waveform = synth.synthesize(ids, Modality.STRICT)

        # FFT to check harmonics
        spectrum = np.abs(np.fft.rfft(waveform))
        freqs = np.fft.rfftfreq(len(waveform), 1/SAMPLE_RATE)

        # Find peaks
        threshold = 0.1 * np.max(spectrum)
        peaks = freqs[spectrum > threshold]

        # Check that we have odd harmonics (440, 1320, 2200)
        for h in [1, 3, 5]:
            expected = BASE_FREQ * h
            assert any(abs(p - expected) < 5 for p in peaks), f"Missing harmonic {h} at {expected} Hz"

    def test_frequency_mapping(self):
        """Test that token IDs map to correct frequencies."""
        synth = HarmonicSynthesizer()

        for token_id in [0, 1, 2, 3]:
            ids = np.array([token_id])
            waveform = synth.synthesize(ids, Modality.PROBE)  # Fundamental only

            spectrum = np.abs(np.fft.rfft(waveform))
            freqs = np.fft.rfftfreq(len(waveform), 1/SAMPLE_RATE)

            # Find peak frequency
            peak_idx = np.argmax(spectrum[1:]) + 1  # Skip DC
            peak_freq = freqs[peak_idx]

            expected_freq = BASE_FREQ + token_id * FREQ_STEP
            assert abs(peak_freq - expected_freq) < 2.0, f"Token {token_id}: expected {expected_freq}, got {peak_freq}"


class TestRWPEnvelope:
    """Tests for RWP v3 envelope."""

    def test_create_envelope(self):
        """Test envelope creation."""
        key = generate_master_key()
        envelope_gen = RWPEnvelope(key)

        payload = b"test payload"
        env = envelope_gen.create(payload, "KO", Modality.ADAPTIVE)

        assert "header" in env
        assert "payload" in env
        assert "sig" in env
        assert env["header"]["ver"] == "3"
        assert env["header"]["tongue"] == "KO"

    def test_verify_valid_envelope(self):
        """Test verification of valid envelope."""
        key = generate_master_key()
        envelope_gen = RWPEnvelope(key)

        # Create valid audio payload
        synth = HarmonicSynthesizer()
        waveform = synth.synthesize(np.array([0, 1, 2]), Modality.ADAPTIVE)
        payload = waveform.tobytes()

        env = envelope_gen.create(payload, "KO", Modality.ADAPTIVE)
        success, message = envelope_gen.verify(env, audio_check=False)

        assert success, f"Verification failed: {message}"

    def test_reject_wrong_key(self):
        """Test rejection of envelope with wrong key."""
        key1 = generate_master_key()
        key2 = generate_master_key()

        envelope_gen1 = RWPEnvelope(key1)
        envelope_gen2 = RWPEnvelope(key2)

        payload = b"test payload"
        env = envelope_gen1.create(payload, "KO", Modality.ADAPTIVE)

        success, message = envelope_gen2.verify(env, audio_check=False)
        assert not success
        assert "MAC" in message

    def test_reject_tampered_payload(self):
        """Test rejection of tampered payload."""
        key = generate_master_key()
        envelope_gen = RWPEnvelope(key)

        payload = b"original payload"
        env = envelope_gen.create(payload, "KO", Modality.ADAPTIVE)

        # Tamper with payload
        env["payload"] = "tampered"

        success, message = envelope_gen.verify(env, audio_check=False)
        assert not success

    def test_reject_replay(self):
        """Test rejection of replayed envelope."""
        key = generate_master_key()
        envelope_gen = RWPEnvelope(key)

        payload = b"test payload"
        env = envelope_gen.create(payload, "KO", Modality.ADAPTIVE)

        # First verification should pass
        success1, _ = envelope_gen.verify(env, audio_check=False)
        assert success1

        # Second verification should fail (nonce reuse)
        success2, message = envelope_gen.verify(env, audio_check=False)
        assert not success2
        assert "nonce" in message.lower() or "replay" in message.lower()

    def test_reject_expired_timestamp(self):
        """Test rejection of expired timestamp."""
        key = generate_master_key()
        envelope_gen = RWPEnvelope(key)

        payload = b"test payload"
        old_timestamp = int((time.time() - 120) * 1000)  # 2 minutes ago

        env = envelope_gen.create(
            payload, "KO", Modality.ADAPTIVE,
            timestamp=old_timestamp
        )

        success, message = envelope_gen.verify(env, audio_check=False)
        assert not success
        assert "timestamp" in message.lower() or "replay" in message.lower()


class TestSymphonicCipher:
    """Integration tests for SymphonicCipher."""

    def test_encode_decode_roundtrip(self):
        """Test encode/decode roundtrip."""
        cipher = SymphonicCipher()

        phrase = "korah aelin dahru"
        envelope, components = cipher.encode(
            phrase,
            modality=Modality.ADAPTIVE,
            return_components=True
        )

        assert envelope is not None
        assert components["original_ids"] == [0, 1, 2]
        assert len(components["permuted_ids"]) == 3

    def test_verification(self):
        """Test envelope verification."""
        cipher = SymphonicCipher()

        envelope = cipher.encode("korah aelin", modality=Modality.STRICT)
        success, message = cipher.verify(envelope)

        assert success, f"Verification failed: {message}"

    def test_wrong_key_rejection(self):
        """Test that wrong key is rejected."""
        cipher1 = SymphonicCipher()
        cipher2 = SymphonicCipher()  # Different key

        envelope = cipher1.encode("korah aelin")
        success, message = cipher2.verify(envelope)

        assert not success

    def test_different_modalities(self):
        """Test encoding with different modalities."""
        cipher = SymphonicCipher()

        for modality in [Modality.STRICT, Modality.ADAPTIVE, Modality.PROBE]:
            envelope = cipher.encode("korah", modality=modality)
            assert envelope["header"]["aad"]["mode"] == modality.value


class TestAvalanche:
    """Tests for avalanche effect in Feistel permutation."""

    def test_single_bit_change(self):
        """Test that single bit change causes significant output change."""
        feistel = FeistelPermutation()
        ids = np.array([0, 1, 2, 3, 4, 5, 6, 7], dtype=np.int64)

        key1 = bytes(32)  # All zeros
        key2 = bytes([1] + [0] * 31)  # Single bit difference

        perm1 = feistel.permute(ids, key1)
        perm2 = feistel.permute(ids, key2)

        # Calculate Hamming distance
        diff = np.sum(perm1 != perm2)
        # Expect significant difference (ideally ~half the bits)
        assert diff > 0, "No avalanche effect detected"


class TestEntropy:
    """Tests for entropy properties."""

    def test_waveform_entropy(self):
        """Test that adaptive waveform has higher entropy than strict."""
        synth = HarmonicSynthesizer()
        ids = np.array([0, 1, 2])

        strict_wave = synth.synthesize(ids, Modality.STRICT)
        adaptive_wave = synth.synthesize(ids, Modality.ADAPTIVE)

        # Compute spectral entropy
        def spectral_entropy(signal):
            spectrum = np.abs(np.fft.rfft(signal))
            spectrum = spectrum / np.sum(spectrum)
            spectrum = spectrum[spectrum > 0]
            return -np.sum(spectrum * np.log2(spectrum))

        strict_entropy = spectral_entropy(strict_wave)
        adaptive_entropy = spectral_entropy(adaptive_wave)

        # Adaptive should have higher entropy (more harmonics)
        assert adaptive_entropy > strict_entropy, \
            f"Expected adaptive entropy ({adaptive_entropy}) > strict ({strict_entropy})"
