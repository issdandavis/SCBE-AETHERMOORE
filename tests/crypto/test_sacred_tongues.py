"""
Unit tests for Sacred Tongue Tokenizer
=======================================
Tests bijectivity, encoding/decoding, spectral fingerprints, and section API.

Target: 95%+ coverage
"""

import pytest
import secrets
from src.crypto.sacred_tongues import (
    SacredTongueTokenizer,
    SACRED_TONGUE_TOKENIZER,
    TONGUES,
    SECTION_TONGUES,
    KOR_AELIN,
    AVALI,
    RUNETHIC,
    CASSISIVADAN,
    UMBROTH,
    DRAUMRIC,
)


class TestTongueSpecification:
    """Tests for TongueSpec dataclass and tongue definitions."""

    def test_all_tongues_have_16_prefixes(self):
        """Each tongue must have exactly 16 prefixes."""
        for code, spec in TONGUES.items():
            assert len(spec.prefixes) == 16, f"{code} has {len(spec.prefixes)} prefixes"

    def test_all_tongues_have_16_suffixes(self):
        """Each tongue must have exactly 16 suffixes."""
        for code, spec in TONGUES.items():
            assert len(spec.suffixes) == 16, f"{code} has {len(spec.suffixes)} suffixes"

    def test_all_tongues_have_unique_codes(self):
        """Tongue codes must be unique."""
        codes = [spec.code for spec in TONGUES.values()]
        assert len(codes) == len(set(codes)), "Duplicate tongue codes found"

    def test_all_tongues_have_harmonic_frequencies(self):
        """Each tongue must have a harmonic frequency for Layer 9."""
        for code, spec in TONGUES.items():
            assert spec.harmonic_frequency > 0, f"{code} missing harmonic frequency"

    def test_harmonic_frequencies_are_unique(self):
        """Harmonic frequencies must be unique per tongue."""
        frequencies = [spec.harmonic_frequency for spec in TONGUES.values()]
        assert len(frequencies) == len(set(frequencies)), "Duplicate harmonic frequencies"

    def test_tongue_domains_are_defined(self):
        """Each tongue must have a domain string."""
        for code, spec in TONGUES.items():
            assert spec.domain, f"{code} missing domain"


class TestBijectivity:
    """Tests for bijective encoding: every byte has unique token, every token maps back."""

    @pytest.mark.parametrize("tongue_code", ["ko", "av", "ru", "ca", "um", "dr"])
    def test_all_256_bytes_roundtrip(self, tongue_code: str):
        """All 256 bytes must round-trip correctly for each tongue."""
        tokenizer = SacredTongueTokenizer()
        for b in range(256):
            data = bytes([b])
            tokens = tokenizer.encode_bytes(tongue_code, data)
            decoded = tokenizer.decode_tokens(tongue_code, tokens)
            assert decoded == data, f"Byte {b} failed roundtrip in {tongue_code}"

    @pytest.mark.parametrize("tongue_code", ["ko", "av", "ru", "ca", "um", "dr"])
    def test_unique_tokens_per_tongue(self, tongue_code: str):
        """Each tongue must have 256 unique tokens."""
        tokenizer = SacredTongueTokenizer()
        all_tokens = set()
        for b in range(256):
            tokens = tokenizer.encode_bytes(tongue_code, bytes([b]))
            assert len(tokens) == 1
            all_tokens.add(tokens[0])
        assert len(all_tokens) == 256, f"{tongue_code} has {len(all_tokens)} unique tokens"

    @pytest.mark.parametrize("tongue_code", ["ko", "av", "ru", "ca", "um", "dr"])
    def test_token_format_has_apostrophe(self, tongue_code: str):
        """All tokens must have prefix'suffix format with apostrophe."""
        tokenizer = SacredTongueTokenizer()
        for b in range(256):
            tokens = tokenizer.encode_bytes(tongue_code, bytes([b]))
            token = tokens[0]
            assert "'" in token, f"Token {token} missing apostrophe"
            parts = token.split("'")
            assert len(parts) == 2, f"Token {token} has wrong format"


class TestEncodeDecode:
    """Tests for encoding and decoding operations."""

    def test_empty_bytes_returns_empty_list(self):
        """Empty input should return empty token list."""
        tokenizer = SacredTongueTokenizer()
        tokens = tokenizer.encode_bytes("ko", b"")
        assert tokens == []

    def test_single_byte_encoding(self):
        """Single byte should encode to single token."""
        tokenizer = SacredTongueTokenizer()
        tokens = tokenizer.encode_bytes("ko", b"\x00")
        assert len(tokens) == 1
        assert tokens[0] == "kor'ah"  # Kor'aelin: prefix[0]'suffix[0]

    def test_multi_byte_encoding(self):
        """Multiple bytes should encode to multiple tokens."""
        tokenizer = SacredTongueTokenizer()
        data = b"\x00\x01\x02"
        tokens = tokenizer.encode_bytes("ko", data)
        assert len(tokens) == 3

    def test_random_data_roundtrip(self):
        """Random data should roundtrip correctly."""
        tokenizer = SacredTongueTokenizer()
        for _ in range(100):
            data = secrets.token_bytes(32)
            for tongue_code in TONGUES.keys():
                tokens = tokenizer.encode_bytes(tongue_code, data)
                decoded = tokenizer.decode_tokens(tongue_code, tokens)
                assert decoded == data

    def test_invalid_tongue_raises_error(self):
        """Unknown tongue code should raise KeyError."""
        tokenizer = SacredTongueTokenizer()
        with pytest.raises(KeyError):
            tokenizer.encode_bytes("invalid", b"test")

    def test_invalid_token_raises_error(self):
        """Invalid token should raise ValueError."""
        tokenizer = SacredTongueTokenizer()
        with pytest.raises(ValueError):
            tokenizer.decode_tokens("ko", ["invalid'token"])

    def test_cross_tongue_tokens_fail(self):
        """Tokens from one tongue should fail decoding in another."""
        tokenizer = SacredTongueTokenizer()
        # Encode with Kor'aelin
        tokens = tokenizer.encode_bytes("ko", b"\x00")
        # Avali has different prefixes/suffixes
        with pytest.raises(ValueError):
            tokenizer.decode_tokens("av", tokens)


class TestSectionAPI:
    """Tests for RWP v3.0 section encoding/decoding."""

    def test_all_sections_have_tongue_mapping(self):
        """All RWP sections must map to a tongue."""
        expected_sections = ["aad", "salt", "nonce", "ct", "tag", "redact"]
        for section in expected_sections:
            assert section in SECTION_TONGUES

    def test_section_encoding_uses_correct_tongue(self):
        """Each section should use its canonical tongue."""
        tokenizer = SacredTongueTokenizer()
        data = b"\x00"

        # aad → Avali (av)
        tokens = tokenizer.encode_section("aad", data)
        av_tokens = tokenizer.encode_bytes("av", data)
        assert tokens == av_tokens

        # salt → Runethic (ru)
        tokens = tokenizer.encode_section("salt", data)
        ru_tokens = tokenizer.encode_bytes("ru", data)
        assert tokens == ru_tokens

        # nonce → Kor'aelin (ko)
        tokens = tokenizer.encode_section("nonce", data)
        ko_tokens = tokenizer.encode_bytes("ko", data)
        assert tokens == ko_tokens

        # ct → Cassisivadan (ca)
        tokens = tokenizer.encode_section("ct", data)
        ca_tokens = tokenizer.encode_bytes("ca", data)
        assert tokens == ca_tokens

        # tag → Draumric (dr)
        tokens = tokenizer.encode_section("tag", data)
        dr_tokens = tokenizer.encode_bytes("dr", data)
        assert tokens == dr_tokens

        # redact → Umbroth (um)
        tokens = tokenizer.encode_section("redact", data)
        um_tokens = tokenizer.encode_bytes("um", data)
        assert tokens == um_tokens

    def test_section_roundtrip(self):
        """Section encode/decode should roundtrip."""
        tokenizer = SacredTongueTokenizer()
        data = secrets.token_bytes(64)

        for section in SECTION_TONGUES.keys():
            tokens = tokenizer.encode_section(section, data)
            decoded = tokenizer.decode_section(section, tokens)
            assert decoded == data, f"Section {section} failed roundtrip"

    def test_invalid_section_raises_error(self):
        """Unknown section should raise ValueError."""
        tokenizer = SacredTongueTokenizer()
        with pytest.raises(ValueError):
            tokenizer.encode_section("invalid_section", b"test")


class TestSpectralFingerprint:
    """Tests for Layer 9 spectral coherence validation."""

    def test_harmonic_fingerprint_is_positive(self):
        """Harmonic fingerprint should be positive for any input."""
        tokenizer = SacredTongueTokenizer()
        data = secrets.token_bytes(16)
        for tongue_code in TONGUES.keys():
            tokens = tokenizer.encode_bytes(tongue_code, data)
            fingerprint = tokenizer.compute_harmonic_fingerprint(tongue_code, tokens)
            assert fingerprint >= 0

    def test_different_data_different_fingerprint(self):
        """Different data should produce different fingerprints."""
        tokenizer = SacredTongueTokenizer()
        tokens1 = tokenizer.encode_bytes("ko", b"hello")
        tokens2 = tokenizer.encode_bytes("ko", b"world")
        fp1 = tokenizer.compute_harmonic_fingerprint("ko", tokens1)
        fp2 = tokenizer.compute_harmonic_fingerprint("ko", tokens2)
        assert fp1 != fp2

    def test_section_integrity_valid_tokens(self):
        """Valid tokens should pass integrity check."""
        tokenizer = SacredTongueTokenizer()
        data = secrets.token_bytes(16)
        for section in SECTION_TONGUES.keys():
            tokens = tokenizer.encode_section(section, data)
            assert tokenizer.validate_section_integrity(section, tokens)

    def test_section_integrity_invalid_tokens(self):
        """Invalid tokens should fail integrity check."""
        tokenizer = SacredTongueTokenizer()
        # Use Kor'aelin tokens for AAD section (should use Avali)
        ko_tokens = tokenizer.encode_bytes("ko", b"\x00")
        assert not tokenizer.validate_section_integrity("aad", ko_tokens)


class TestSingleton:
    """Tests for the global tokenizer instance."""

    def test_singleton_is_initialized(self):
        """Global tokenizer should be ready to use."""
        assert SACRED_TONGUE_TOKENIZER is not None

    def test_singleton_has_all_tongues(self):
        """Global tokenizer should have all 6 tongues."""
        assert len(SACRED_TONGUE_TOKENIZER.tongues) == 6

    def test_singleton_encoding_works(self):
        """Global tokenizer should encode correctly."""
        tokens = SACRED_TONGUE_TOKENIZER.encode_bytes("ko", b"test")
        assert len(tokens) == 4


class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_max_byte_value(self):
        """Byte value 255 should encode correctly."""
        tokenizer = SacredTongueTokenizer()
        for tongue_code in TONGUES.keys():
            tokens = tokenizer.encode_bytes(tongue_code, b"\xff")
            decoded = tokenizer.decode_tokens(tongue_code, tokens)
            assert decoded == b"\xff"

    def test_all_same_bytes(self):
        """Repeated bytes should produce repeated tokens."""
        tokenizer = SacredTongueTokenizer()
        data = b"\x00" * 10
        tokens = tokenizer.encode_bytes("ko", data)
        assert len(set(tokens)) == 1  # All same token

    def test_large_data(self):
        """Large data should encode correctly."""
        tokenizer = SacredTongueTokenizer()
        data = secrets.token_bytes(1024)
        tokens = tokenizer.encode_bytes("ko", data)
        assert len(tokens) == 1024
        decoded = tokenizer.decode_tokens("ko", tokens)
        assert decoded == data
