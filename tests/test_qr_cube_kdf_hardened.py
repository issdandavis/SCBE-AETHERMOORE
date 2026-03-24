"""Hardened tests for Holographic QR Cube π^φ KDF.

Fills gaps not covered by the existing test_qr_cube_pi_phi_kdf.py:
  - Direct _pi_phi_scalar() unit tests
  - HKDF structural properties
  - Edge cases (boundary coherence, negative d*, empty inputs)
  - Cross-formula verification (scalar embedded in key derivation)
  - Ternary trit classification (H_wall / H_score / H_exp)
  - Large output length (multi-block HKDF-Expand)
  - Commit field collision resistance
"""

from __future__ import annotations

import math

import pytest

from src.symphonic_cipher.scbe_aethermoore.qr_cube_kdf import (
    PI,
    PHI,
    _commit_field,
    _hkdf_expand,
    _hkdf_extract,
    _pi_phi_scalar,
    derive_pi_phi_key,
)


# =========================================================================== #
#  _pi_phi_scalar() unit tests
# =========================================================================== #


class TestPiPhiScalar:
    def test_at_zero_returns_one(self):
        assert _pi_phi_scalar(0.0) == pytest.approx(1.0, abs=1e-15)

    def test_at_one_matches_formula(self):
        expected = PI ** PHI  # ~5.047
        assert _pi_phi_scalar(1.0) == pytest.approx(expected, rel=1e-14)

    def test_at_two_matches_formula(self):
        expected = PI ** (2 * PHI)  # ~25.47
        assert _pi_phi_scalar(2.0) == pytest.approx(expected, rel=1e-14)

    def test_negative_d_star_gives_value_less_than_one(self):
        # π^(φ·(-1)) = π^(-φ) < 1
        result = _pi_phi_scalar(-1.0)
        assert 0 < result < 1.0

    def test_negative_d_star_is_reciprocal_of_positive(self):
        pos = _pi_phi_scalar(1.5)
        neg = _pi_phi_scalar(-1.5)
        assert pos * neg == pytest.approx(1.0, rel=1e-14)

    def test_strictly_monotonic(self):
        values = [_pi_phi_scalar(d) for d in [-2, -1, 0, 0.5, 1, 2, 3]]
        for a, b in zip(values, values[1:]):
            assert b > a

    def test_growth_rate_is_super_exponential(self):
        # ratio at d=2 vs d=1 should equal π^φ
        r1 = _pi_phi_scalar(2.0) / _pi_phi_scalar(1.0)
        r2 = _pi_phi_scalar(3.0) / _pi_phi_scalar(2.0)
        expected_ratio = PI ** PHI
        assert r1 == pytest.approx(expected_ratio, rel=1e-13)
        assert r2 == pytest.approx(expected_ratio, rel=1e-13)

    def test_very_large_d_star_overflows(self):
        # Python raises OverflowError for huge exponents — acceptable behavior
        with pytest.raises(OverflowError):
            _pi_phi_scalar(1000.0)


# =========================================================================== #
#  HKDF structural properties
# =========================================================================== #


class TestHKDFProperties:
    def test_extract_with_empty_salt_uses_zero_salt(self):
        ikm = b"test-ikm"
        prk_empty = _hkdf_extract(b"", ikm)
        prk_zero = _hkdf_extract(b"\x00" * 32, ikm)
        assert prk_empty == prk_zero

    def test_extract_output_is_32_bytes(self):
        prk = _hkdf_extract(b"salt", b"ikm")
        assert len(prk) == 32

    def test_expand_prefix_property(self):
        """HKDF-Expand: shorter output is a prefix of longer output."""
        prk = _hkdf_extract(b"salt", b"ikm")
        info = b"context"
        k16 = _hkdf_expand(prk, info, 16)
        k32 = _hkdf_expand(prk, info, 32)
        k64 = _hkdf_expand(prk, info, 64)
        assert k32[:16] == k16
        assert k64[:32] == k32

    def test_expand_different_info_produces_different_output(self):
        prk = _hkdf_extract(b"salt", b"ikm")
        k1 = _hkdf_expand(prk, b"info-a", 32)
        k2 = _hkdf_expand(prk, b"info-b", 32)
        assert k1 != k2

    def test_expand_can_produce_large_output(self):
        """Multi-block HKDF-Expand (> 32 bytes requires multiple HMAC rounds)."""
        prk = _hkdf_extract(b"salt", b"ikm")
        k256 = _hkdf_expand(prk, b"info", 256)
        assert len(k256) == 256
        # First 32 bytes should match single-block output
        k32 = _hkdf_expand(prk, b"info", 32)
        assert k256[:32] == k32


# =========================================================================== #
#  _commit_field collision resistance
# =========================================================================== #


class TestCommitField:
    def test_different_domains_produce_different_hashes(self):
        data = b"same-data"
        c1 = _commit_field(b"domain-a:", data)
        c2 = _commit_field(b"domain-b:", data)
        assert c1 != c2

    def test_different_data_same_domain_produce_different_hashes(self):
        c1 = _commit_field(b"domain:", b"data-a")
        c2 = _commit_field(b"domain:", b"data-b")
        assert c1 != c2

    def test_boundary_ambiguity_prevented(self):
        """The length prefix prevents domain||data boundary confusion."""
        # "domain:" + "AB" vs "domain:A" + "B" — should differ
        c1 = _commit_field(b"dom", b"AB")
        c2 = _commit_field(b"domA", b"B")
        assert c1 != c2


# =========================================================================== #
#  derive_pi_phi_key: edge cases
# =========================================================================== #


class TestKDFEdgeCases:
    BASE = dict(
        cube_id="cube-edge",
        aad=b"aad",
        nonce=b"\x01" * 12,
        salt=b"\x02" * 32,
        out_len=32,
    )

    def test_coherence_zero_is_accepted(self):
        key = derive_pi_phi_key(d_star=0.5, coherence=0.0, **self.BASE)
        assert isinstance(key, bytes) and len(key) == 32

    def test_coherence_one_is_accepted(self):
        key = derive_pi_phi_key(d_star=0.5, coherence=1.0, **self.BASE)
        assert isinstance(key, bytes) and len(key) == 32

    def test_coherence_boundary_values_produce_different_keys(self):
        k0 = derive_pi_phi_key(d_star=0.5, coherence=0.0, **self.BASE)
        k1 = derive_pi_phi_key(d_star=0.5, coherence=1.0, **self.BASE)
        assert k0 != k1

    def test_negative_d_star_is_accepted(self):
        key = derive_pi_phi_key(d_star=-2.0, coherence=0.5, **self.BASE)
        assert isinstance(key, bytes) and len(key) == 32

    def test_d_star_zero_is_accepted(self):
        key = derive_pi_phi_key(d_star=0.0, coherence=0.5, **self.BASE)
        assert isinstance(key, bytes) and len(key) == 32

    def test_very_small_d_star_produces_valid_key(self):
        key = derive_pi_phi_key(d_star=1e-15, coherence=0.5, **self.BASE)
        assert isinstance(key, bytes) and len(key) == 32

    def test_empty_salt_is_accepted(self):
        key = derive_pi_phi_key(
            d_star=0.25, coherence=0.5, cube_id="c", aad=b"a", nonce=b"\x01" * 12,
            salt=b"", out_len=32,
        )
        assert isinstance(key, bytes) and len(key) == 32

    def test_empty_aad_is_accepted(self):
        key = derive_pi_phi_key(
            d_star=0.25, coherence=0.5, cube_id="c", aad=b"", nonce=b"\x01" * 12,
            salt=b"\x02" * 32, out_len=32,
        )
        assert isinstance(key, bytes) and len(key) == 32

    def test_out_len_64_multi_block(self):
        key = derive_pi_phi_key(
            d_star=0.25, coherence=0.5, cube_id="cube-edge",
            aad=b"aad", nonce=b"\x01" * 12, salt=b"\x02" * 32, out_len=64,
        )
        assert len(key) == 64

    def test_out_len_1_single_byte(self):
        key = derive_pi_phi_key(
            d_star=0.25, coherence=0.5, cube_id="cube-edge",
            aad=b"aad", nonce=b"\x01" * 12, salt=b"\x02" * 32, out_len=1,
        )
        assert len(key) == 1

    def test_rejects_coherence_negative(self):
        with pytest.raises(ValueError, match="coherence"):
            derive_pi_phi_key(d_star=0.25, coherence=-0.01, **self.BASE)

    def test_rejects_coherence_above_one(self):
        with pytest.raises(ValueError, match="coherence"):
            derive_pi_phi_key(d_star=0.25, coherence=1.001, **self.BASE)


# =========================================================================== #
#  Cross-formula: scalar is correctly embedded in the KDF
# =========================================================================== #


class TestCrossFormula:
    """Verify the scalar cost feeds into the key by comparing d*=0 vs d*≠0."""

    def test_d_star_zero_and_nonzero_produce_different_keys(self):
        base = dict(
            coherence=0.5, cube_id="c", aad=b"a", nonce=b"\x01" * 12,
            salt=b"\x02" * 32, out_len=32,
        )
        k0 = derive_pi_phi_key(d_star=0.0, **base)
        k1 = derive_pi_phi_key(d_star=1.0, **base)
        assert k0 != k1

    def test_small_d_star_change_is_detectable(self):
        """Even 1e-10 shift in d* must produce a different key (input sensitivity)."""
        base = dict(
            coherence=0.5, cube_id="c", aad=b"a", nonce=b"\x01" * 12,
            salt=b"\x02" * 32, out_len=32,
        )
        k1 = derive_pi_phi_key(d_star=0.5, **base)
        k2 = derive_pi_phi_key(d_star=0.5 + 1e-10, **base)
        assert k1 != k2

    def test_symmetric_d_star_values_produce_different_keys(self):
        """d*=+1 and d*=-1 must produce different keys (cost is different)."""
        base = dict(
            coherence=0.5, cube_id="c", aad=b"a", nonce=b"\x01" * 12,
            salt=b"\x02" * 32, out_len=32,
        )
        kp = derive_pi_phi_key(d_star=1.0, **base)
        kn = derive_pi_phi_key(d_star=-1.0, **base)
        assert kp != kn


# =========================================================================== #
#  Ternary trit classification (H_wall / H_score / H_exp)
# =========================================================================== #


def _h_wall(d_star: float, R: float = 1.0) -> float:
    """H_wall = R · π^(φ · d*) — unbounded attack cost."""
    return R * (PI ** (PHI * d_star))


def _h_score(d_star: float, pd: float = 0.0) -> float:
    """H_score = 1/(1 + d* + 2·pd) — bounded safety score ∈ (0, 1]."""
    return 1.0 / (1.0 + d_star + 2.0 * pd)


def _h_exp(d_star: float) -> float:
    """H_exp = exp(d*) — steep amplifier."""
    return math.exp(d_star)


def _score_trit(score: float) -> int:
    if score > 0.67:
        return +1
    if score < 0.33:
        return -1
    return 0


def _wall_trit(wall: float) -> int:
    if wall < 1.5:
        return +1
    if wall > 1.9:
        return -1
    return 0


def _exp_trit(exp_val: float) -> int:
    if exp_val < 2.0:
        return +1
    if exp_val > 10.0:
        return -1
    return 0


class TestTernaryTritSurface:
    """Verify the 3-trit decision surface from L12_HARMONIC_SCALING_CANON."""

    def test_safe_center_all_positive_trits(self):
        # d*=0.2 → H_wall ≈ 1.42 (<1.5), H_score ≈ 0.83 (>0.67), H_exp ≈ 1.22 (<2.0)
        d_star = 0.2
        assert _score_trit(_h_score(d_star)) == +1
        assert _wall_trit(_h_wall(d_star)) == +1
        assert _exp_trit(_h_exp(d_star)) == +1

    def test_adversarial_all_negative_trits(self):
        d_star = 3.0
        assert _score_trit(_h_score(d_star)) == -1
        assert _wall_trit(_h_wall(d_star)) == -1
        assert _exp_trit(_h_exp(d_star)) == -1

    def test_transition_zone_has_neutral_trit(self):
        d_star = 1.0
        trits = (
            _score_trit(_h_score(d_star)),
            _wall_trit(_h_wall(d_star)),
            _exp_trit(_h_exp(d_star)),
        )
        assert 0 in trits

    def test_phase_incoherent_attacker_breaks_correlation(self):
        """Small d* + high pd → H_score drops while wall/exp stay safe."""
        d_star = 0.2  # H_wall ≈ 1.42 (<1.5 → trit +1)
        pd = 2.0      # H_score = 1/(1+0.2+4.0) ≈ 0.19 → trit -1

        t_score = _score_trit(_h_score(d_star, pd=pd))
        t_wall = _wall_trit(_h_wall(d_star))
        t_exp = _exp_trit(_h_exp(d_star))

        assert t_wall == +1
        assert t_exp == +1
        assert t_score in (0, -1)
        assert t_score != t_wall  # disagreement = detection signal

    def test_disagreement_metric_for_phase_attack(self):
        d_star = 0.2
        pd = 2.0
        trits = (
            _score_trit(_h_score(d_star, pd=pd)),
            _wall_trit(_h_wall(d_star)),
            _exp_trit(_h_exp(d_star)),
        )
        disagreement = len(set(trits)) - 1  # 0 = unanimous, 1-2 = split
        assert disagreement >= 1

    def test_h_wall_uses_pi_phi_scalar(self):
        """H_wall at R=1 must equal _pi_phi_scalar."""
        for d in [0.0, 0.5, 1.0, 2.0, -1.0]:
            assert _h_wall(d, R=1.0) == pytest.approx(_pi_phi_scalar(d), rel=1e-14)

    def test_h_score_bounded_zero_to_one(self):
        for d in [0.0, 0.5, 1.0, 5.0, 100.0]:
            s = _h_score(d)
            assert 0 < s <= 1.0

    def test_h_score_decreases_with_distance(self):
        assert _h_score(0.0) > _h_score(0.5) > _h_score(1.0) > _h_score(5.0)

    def test_h_score_decreases_with_phase_deviation(self):
        assert _h_score(0.5, pd=0.0) > _h_score(0.5, pd=0.5) > _h_score(0.5, pd=2.0)


# =========================================================================== #
#  Constants
# =========================================================================== #


class TestConstants:
    def test_phi_is_golden_ratio(self):
        expected = (1 + math.sqrt(5)) / 2
        assert PHI == pytest.approx(expected, abs=1e-15)

    def test_pi_is_math_pi(self):
        assert PI == math.pi
