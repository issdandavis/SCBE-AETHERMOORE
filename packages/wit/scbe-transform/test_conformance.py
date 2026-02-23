"""
scbe:transform — Conformance Test Suite
=========================================

Tests for the scbe:transform WIT interface reference implementation.
"""

from __future__ import annotations

import math

import pytest

from reference_impl import (
    Encoding,
    GovernanceDecision,
    Harmonics,
    Pipeline,
    Tongue,
    TongueEncoder,
    TongueToken,
    TransformError,
    TrustRing,
)


# ---------------------------------------------------------------------------
#  Tongue Encoder Tests
# ---------------------------------------------------------------------------

class TestTongueEncoder:
    def test_encode_single_byte(self):
        tokens = TongueEncoder.encode(Tongue.KORAELIN, b"\x42")
        assert len(tokens) == 1
        assert tokens[0].tongue == Tongue.KORAELIN
        assert tokens[0].prefix_index == 4
        assert tokens[0].suffix_index == 2

    def test_encode_decode_roundtrip(self):
        data = b"Hello, SCBE!"
        for tongue in Tongue:
            tokens = TongueEncoder.encode(tongue, data)
            decoded = TongueEncoder.decode(tokens)
            assert decoded == data, f"Roundtrip failed for {tongue}"

    def test_encode_empty(self):
        tokens = TongueEncoder.encode(Tongue.AVALI, b"")
        assert tokens == []

    def test_encode_all_bytes(self):
        data = bytes(range(256))
        tokens = TongueEncoder.encode(Tongue.RUNETHIC, data)
        assert len(tokens) == 256
        decoded = TongueEncoder.decode(tokens)
        assert decoded == data

    def test_translate_preserves_data(self):
        data = b"governance decision"
        tokens_ko = TongueEncoder.encode(Tongue.KORAELIN, data)
        tokens_av = TongueEncoder.translate(tokens_ko, Tongue.AVALI)
        decoded = TongueEncoder.decode(tokens_av)
        assert decoded == data

    def test_translate_changes_tongue(self):
        data = b"\x42"
        tokens_ko = TongueEncoder.encode(Tongue.KORAELIN, data)
        tokens_ru = TongueEncoder.translate(tokens_ko, Tongue.RUNETHIC)
        assert tokens_ko[0].tongue == Tongue.KORAELIN
        assert tokens_ru[0].tongue == Tongue.RUNETHIC
        assert tokens_ko[0].text != tokens_ru[0].text

    def test_blend_interleaves(self):
        data1 = b"\x01"
        data2 = b"\x02"
        t1 = TongueEncoder.encode(Tongue.KORAELIN, data1)
        t2 = TongueEncoder.encode(Tongue.AVALI, data2)
        blended = TongueEncoder.blend([t1, t2])
        assert len(blended) == 2
        assert blended[0].tongue == Tongue.KORAELIN
        assert blended[1].tongue == Tongue.AVALI

    def test_blend_empty(self):
        assert TongueEncoder.blend([]) == []

    def test_token_text_format(self):
        token = TongueEncoder.encode(Tongue.KORAELIN, b"\x00")[0]
        # prefix[0] + suffix[0] = "kor" + "in" = "korin"
        assert token.text == "korin"


# ---------------------------------------------------------------------------
#  Encoding Tests (Trinary / Negabinary)
# ---------------------------------------------------------------------------

class TestEncoding:
    def test_balanced_ternary_zero(self):
        assert Encoding.to_balanced_ternary(0) == [0]

    def test_balanced_ternary_positive(self):
        trits = Encoding.to_balanced_ternary(42)
        decoded = Encoding.from_balanced_ternary(trits)
        assert decoded == 42

    def test_balanced_ternary_negative(self):
        trits = Encoding.to_balanced_ternary(-17)
        decoded = Encoding.from_balanced_ternary(trits)
        assert decoded == -17

    def test_balanced_ternary_roundtrip_range(self):
        for n in range(-100, 101):
            trits = Encoding.to_balanced_ternary(n)
            assert all(t in (-1, 0, 1) for t in trits)
            assert Encoding.from_balanced_ternary(trits) == n

    def test_governance_trit_allow(self):
        trit = Encoding.pack_governance_trit(GovernanceDecision.ALLOW)
        assert trit == 1
        assert Encoding.unpack_governance_trit(trit) == GovernanceDecision.ALLOW

    def test_governance_trit_quarantine(self):
        trit = Encoding.pack_governance_trit(GovernanceDecision.QUARANTINE)
        assert trit == 0
        assert Encoding.unpack_governance_trit(trit) == GovernanceDecision.QUARANTINE

    def test_governance_trit_deny(self):
        trit = Encoding.pack_governance_trit(GovernanceDecision.DENY)
        assert trit == -1
        assert Encoding.unpack_governance_trit(trit) == GovernanceDecision.DENY

    def test_negabinary_zero(self):
        assert Encoding.to_negabinary(0) == [0]

    def test_negabinary_positive(self):
        bits = Encoding.to_negabinary(42)
        decoded = Encoding.from_negabinary(bits)
        assert decoded == 42

    def test_negabinary_negative(self):
        bits = Encoding.to_negabinary(-7)
        decoded = Encoding.from_negabinary(bits)
        assert decoded == -7

    def test_negabinary_roundtrip_range(self):
        for n in range(-100, 101):
            bits = Encoding.to_negabinary(n)
            assert all(b in (0, 1) for b in bits)
            assert Encoding.from_negabinary(bits) == n


# ---------------------------------------------------------------------------
#  Harmonics Tests
# ---------------------------------------------------------------------------

class TestHarmonics:
    def test_harmonic_wall_zero_distance(self):
        # H(0, 0, 0) = 1 / (1 + 0 + 0) = 1.0
        assert Harmonics.harmonic_wall(0, 0, 0) == 1.0

    def test_harmonic_wall_high_distance(self):
        # H(10, 0.3, 0.5) = 1 / (1 + 10 + 0.6) = 1/11.6 ≈ 0.0862
        result = Harmonics.harmonic_wall(10, 0.3, 0.5)
        assert abs(result - 1 / 11.6) < 0.001

    def test_harmonic_wall_always_positive(self):
        for d in [0, 0.5, 1, 2, 5, 10]:
            for r in [0, 0.1, 0.3, 0.5, 0.9]:
                result = Harmonics.harmonic_wall(d, r, 0.5)
                assert result > 0

    def test_harmonic_wall_monotone_decreasing(self):
        prev = Harmonics.harmonic_wall(0, 0.3, 0.5)
        for d in [0.5, 1, 2, 5, 10]:
            curr = Harmonics.harmonic_wall(d, 0.3, 0.5)
            assert curr < prev
            prev = curr

    def test_poincare_distance_same_point(self):
        d = Harmonics.poincare_distance(0.5, 0.5)
        assert abs(d) < 1e-10

    def test_poincare_distance_symmetric(self):
        d1 = Harmonics.poincare_distance(0.3, 0.7)
        d2 = Harmonics.poincare_distance(0.7, 0.3)
        assert abs(d1 - d2) < 1e-10

    def test_poincare_distance_boundary_infinite(self):
        d = Harmonics.poincare_distance(0.5, 1.0)
        assert d == float("inf")

    def test_poincare_distance_positive(self):
        d = Harmonics.poincare_distance(0.2, 0.8)
        assert d > 0

    def test_classify_trust_ring_core(self):
        assert Harmonics.classify_trust_ring(0.0) == TrustRing.CORE
        assert Harmonics.classify_trust_ring(0.15) == TrustRing.CORE
        assert Harmonics.classify_trust_ring(0.29) == TrustRing.CORE

    def test_classify_trust_ring_inner(self):
        assert Harmonics.classify_trust_ring(0.3) == TrustRing.INNER
        assert Harmonics.classify_trust_ring(0.5) == TrustRing.INNER
        assert Harmonics.classify_trust_ring(0.69) == TrustRing.INNER

    def test_classify_trust_ring_outer(self):
        assert Harmonics.classify_trust_ring(0.7) == TrustRing.OUTER
        assert Harmonics.classify_trust_ring(0.8) == TrustRing.OUTER
        assert Harmonics.classify_trust_ring(0.89) == TrustRing.OUTER

    def test_classify_trust_ring_wall(self):
        assert Harmonics.classify_trust_ring(0.9) == TrustRing.WALL
        assert Harmonics.classify_trust_ring(0.95) == TrustRing.WALL
        assert Harmonics.classify_trust_ring(0.99) == TrustRing.WALL

    def test_harmonic_cost_identity(self):
        # R^(0^2) = R^0 = 1
        assert Harmonics.harmonic_cost(0, 0.5) == 1.0

    def test_harmonic_cost_unit_distance(self):
        # R^(1^2) = R
        assert abs(Harmonics.harmonic_cost(1, 0.5) - 0.5) < 1e-10


# ---------------------------------------------------------------------------
#  Pipeline Tests
# ---------------------------------------------------------------------------

class TestPipeline:
    def test_transform_chain_single(self):
        result = Pipeline.transform_chain(b"hello", ["uppercase"])
        assert result == b"HELLO"

    def test_transform_chain_multiple(self):
        result = Pipeline.transform_chain(b"Hello", ["lowercase", "reverse"])
        assert result == b"olleh"

    def test_transform_chain_empty(self):
        result = Pipeline.transform_chain(b"data", [])
        assert result == b"data"

    def test_transform_chain_unknown(self):
        with pytest.raises(TransformError):
            Pipeline.transform_chain(b"data", ["nonexistent"])

    def test_validate_non_empty(self):
        assert Pipeline.validate(b"data", "non-empty") is True
        assert Pipeline.validate(b"", "non-empty") is False

    def test_validate_utf8(self):
        assert Pipeline.validate(b"hello", "utf8") is True
        assert Pipeline.validate(b"\xff\xfe", "utf8") is False

    def test_validate_min_length(self):
        assert Pipeline.validate(b"hello", "min-length:3") is True
        assert Pipeline.validate(b"hi", "min-length:3") is False

    def test_validate_unknown_schema(self):
        with pytest.raises(TransformError):
            Pipeline.validate(b"data", "unknown-schema")
