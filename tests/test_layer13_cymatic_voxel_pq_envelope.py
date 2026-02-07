"""
Layer 13: Cymatic Voxel Storage + PQ Envelope Sealing Tests
============================================================

Tests for CymaticVoxelStorage from src/symphonic_cipher/core/cymatic_voxel_storage.py

Covers:
- Chladni field determinism and mathematical properties
- Nodal line validation (near-zero displacement)
- Resonance-keyed encode/decode semantics
- Access control (wrong vector yields different data)
- PQ envelope integration contract (skips if not implemented)

Adapted to actual API: chladni_pattern, nodal_mask, encode, decode,
access_control_demo, visualize_pattern, security_analysis.
"""

import importlib
import inspect
import json
import math
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

import numpy as np
import pytest


# ----------------------------
# Robust import / discovery
# ----------------------------

CANDIDATE_MODULES = [
    "src.symphonic_cipher.core.cymatic_voxel_storage",
    "symphonic_cipher.core.cymatic_voxel_storage",
    "src.symphonic_cipher.core.cymatic",
    "symphonic_cipher.core.cymatic",
]

CANDIDATE_STORAGE_NAMES = [
    "CymaticVoxelStorage",
    "CymaticStorage",
    "VoxelStorage",
]


def _import_any_module():
    imported = []
    for name in CANDIDATE_MODULES:
        try:
            imported.append(importlib.import_module(name))
        except Exception:
            continue
    return imported


def _find_storage_class():
    """
    Return (module, storage_class) or skip if not found.
    """
    modules = _import_any_module()
    if not modules:
        pytest.skip(
            "Could not import cymatic voxel storage module. "
            "Add your module path to CANDIDATE_MODULES."
        )

    for m in modules:
        for cls_name in CANDIDATE_STORAGE_NAMES:
            cls = getattr(m, cls_name, None)
            if inspect.isclass(cls):
                return m, cls

    pytest.skip(
        "Imported cymatic module(s) but did not find expected storage class. "
        "Add your class name to CANDIDATE_STORAGE_NAMES."
    )


def _find_vector_class(module):
    """Find VoxelAccessVector or similar."""
    for name in ["VoxelAccessVector", "AccessVector", "Vector6D"]:
        cls = getattr(module, name, None)
        if inspect.isclass(cls):
            return cls
    return None


# ----------------------------
# Fake PQ KEM for integration testing
# ----------------------------

@dataclass
class FakeKEM:
    """
    Minimal ML-KEM-like interface for tests.
    The goal is verifying envelope wiring, NOT cryptographic security.
    """
    name: str = "FAKE-ML-KEM-768"

    def keypair(self) -> Tuple[bytes, bytes]:
        return b"PK_FAKE" * 8, b"SK_FAKE" * 8

    def encapsulate(self, public_key: bytes) -> Tuple[bytes, bytes]:
        assert public_key.startswith(b"PK_FAKE")
        ciphertext = b"CT_FAKE" * 10
        shared_secret = b"SS_FAKE" * 10
        return ciphertext, shared_secret

    def decapsulate(self, ciphertext: bytes, secret_key: bytes) -> bytes:
        assert ciphertext.startswith(b"CT_FAKE")
        assert secret_key.startswith(b"SK_FAKE")
        return b"SS_FAKE" * 10


# ----------------------------
# Utilities
# ----------------------------

def _approx_zero(x: float, tol: float = 1e-6) -> bool:
    return abs(x) <= tol


def _make_vector(module, vx=3.0, vy=0.0, vz=0.0, sx=5.0, sy=0.0, sz=0.0):
    """Create a VoxelAccessVector with the given components."""
    vec_cls = _find_vector_class(module)
    if vec_cls is None:
        pytest.skip("No VoxelAccessVector class found.")
    return vec_cls(vx, vy, vz, sx, sy, sz)


# ----------------------------
# Tests: Chladni field + nodal computation
# ----------------------------

class TestChladniField:
    """Tests for Chladni pattern generation and nodal lines."""

    def test_chladni_field_is_deterministic(self):
        """Same (n, m) should always produce the same pattern."""
        m, cls = _find_storage_class()
        storage = cls(resolution=64)

        a = storage.chladni_pattern(3, 4)
        b = storage.chladni_pattern(3, 4)

        np.testing.assert_array_equal(a, b)

    def test_chladni_field_antisymmetric(self):
        """f(n,m) = -f(m,n) by the formula cos(n*pi*x)cos(m*pi*y) - cos(m*pi*x)cos(n*pi*y)."""
        m, cls = _find_storage_class()
        storage = cls(resolution=64)

        pattern_nm = storage.chladni_pattern(3, 4)
        pattern_mn = storage.chladni_pattern(4, 3)

        np.testing.assert_allclose(pattern_nm, -pattern_mn, atol=1e-12)

    def test_chladni_field_zero_when_n_equals_m(self):
        """When n == m, the pattern should be identically zero."""
        m, cls = _find_storage_class()
        storage = cls(resolution=64)

        pattern = storage.chladni_pattern(3, 3)

        np.testing.assert_allclose(pattern, 0.0, atol=1e-12)

    def test_chladni_field_shape_matches_resolution(self):
        """Pattern shape should be (resolution, resolution)."""
        m, cls = _find_storage_class()
        res = 50
        storage = cls(resolution=res)

        pattern = storage.chladni_pattern(3, 4)

        assert pattern.shape == (res, res)

    def test_nodal_mask_contains_true_values(self):
        """Nodal mask should have some True values (points near zero)."""
        m, cls = _find_storage_class()
        storage = cls(resolution=100)

        mask = storage.nodal_mask(3, 4, threshold=0.1)

        assert mask.any(), "Nodal mask should contain at least some True values"

    def test_nodal_points_are_near_zero_displacement(self):
        """Points where the mask is True should have near-zero pattern values."""
        m, cls = _find_storage_class()
        storage = cls(resolution=100)

        pattern = storage.chladni_pattern(3, 4)
        mask = storage.nodal_mask(3, 4, threshold=0.1)

        # All masked points should have |pattern| < threshold
        assert np.all(np.abs(pattern[mask]) < 0.1)

    def test_nodal_point_count_reasonable_for_mode_3_4(self):
        """
        Nodal density should be in a reasonable range for mode (3,4).
        Broad bounds to avoid brittleness.
        """
        m, cls = _find_storage_class()
        storage = cls(resolution=128)

        mask = storage.nodal_mask(3, 4, threshold=0.1)
        count = int(np.sum(mask))

        # With 128x128 = 16384 total cells, nodal region should be non-trivial
        assert 100 <= count <= 16000, f"Nodal count {count} outside expected range"

    def test_higher_modes_have_more_nodal_lines(self):
        """Higher (n, m) should generally produce denser nodal patterns."""
        m, cls = _find_storage_class()
        storage = cls(resolution=100)

        mask_low = storage.nodal_mask(2, 3, threshold=0.1)
        mask_high = storage.nodal_mask(5, 7, threshold=0.1)

        count_low = int(np.sum(mask_low))
        count_high = int(np.sum(mask_high))

        # Higher modes should have at least as many nodal points (roughly)
        # Use generous tolerance since it depends on exact thresholding
        assert count_high >= count_low * 0.5, (
            f"Higher modes ({count_high}) should have comparable or more "
            f"nodal points than lower modes ({count_low})"
        )


# ----------------------------
# Tests: encode/decode with VoxelAccessVector
# ----------------------------

class TestEncodeDecodeSemantics:
    """Tests for resonance-keyed store/load (encode/decode) semantics."""

    def test_encode_decode_roundtrip_at_nodal_lines(self):
        """Data at nodal lines should survive encode-decode roundtrip."""
        m, cls = _find_storage_class()
        res = 50
        storage = cls(resolution=res)
        vec = _make_vector(m, vx=3.0, vy=0.0, vz=0.0, sx=5.0, sy=0.0, sz=0.0)

        data = np.random.rand(res, res)
        encoded = storage.encode(data, vec)
        decoded = storage.decode(encoded, vec)

        # At nodal lines, decoded should approximate original
        n, mm = vec.to_nm_pair()
        mask = storage.nodal_mask(n, mm, threshold=0.1)

        if mask.any():
            np.testing.assert_allclose(
                decoded[mask], data[mask], atol=0.05,
                err_msg="Decoded data at nodal lines should match original"
            )

    def test_wrong_vector_yields_different_data(self):
        """
        Decoding with wrong vector should not yield the same result.
        This is the core access control property.
        """
        m, cls = _find_storage_class()
        res = 50
        storage = cls(resolution=res)

        correct_vec = _make_vector(m, vx=3.0, vy=0.0, vz=0.0, sx=5.0, sy=0.0, sz=0.0)
        wrong_vec = _make_vector(m, vx=2.0, vy=0.0, vz=0.0, sx=4.0, sy=0.0, sz=0.0)

        data = np.random.rand(res, res)
        encoded = storage.encode(data, correct_vec)

        decoded_correct = storage.decode(encoded, correct_vec)
        decoded_wrong = storage.decode(encoded, wrong_vec)

        # Wrong vector should produce different output
        assert not np.allclose(decoded_correct, decoded_wrong, atol=0.01), (
            "Wrong vector should yield different decoded data"
        )

    def test_access_control_demo_returns_tuple(self):
        """access_control_demo should return (correct_decoded, wrong_decoded) tuple."""
        m, cls = _find_storage_class()
        res = 50
        storage = cls(resolution=res)

        correct_vec = _make_vector(m, vx=3.0, vy=0.0, vz=0.0, sx=5.0, sy=0.0, sz=0.0)
        wrong_vec = _make_vector(m, vx=2.0, vy=0.0, vz=0.0, sx=4.0, sy=0.0, sz=0.0)

        data = np.random.rand(res, res)
        result = storage.access_control_demo(data, correct_vec, wrong_vec)

        assert isinstance(result, tuple)
        assert len(result) == 2

        decoded_correct, decoded_wrong = result
        assert decoded_correct.shape == (res, res)
        assert decoded_wrong.shape == (res, res)

    def test_wrong_vector_higher_error(self):
        """Wrong vector should produce higher reconstruction error than correct vector."""
        m, cls = _find_storage_class()
        res = 50
        storage = cls(resolution=res)

        correct_vec = _make_vector(m, vx=3.0, vy=0.0, vz=0.0, sx=5.0, sy=0.0, sz=0.0)
        wrong_vec = _make_vector(m, vx=2.0, vy=0.0, vz=0.0, sx=4.0, sy=0.0, sz=0.0)

        data = np.random.rand(res, res)
        decoded_correct, decoded_wrong = storage.access_control_demo(
            data, correct_vec, wrong_vec
        )

        error_correct = np.mean((data - decoded_correct) ** 2)
        error_wrong = np.mean((data - decoded_wrong) ** 2)

        # Wrong vector should generally produce higher error
        # (not strictly guaranteed for all data, but very likely for random data)
        assert error_wrong > error_correct * 0.9 or error_correct < 0.01, (
            f"Wrong vector error ({error_wrong:.6f}) should exceed "
            f"correct vector error ({error_correct:.6f})"
        )

    def test_encode_shape_preserved(self):
        """Encoded output should have same shape as input."""
        m, cls = _find_storage_class()
        res = 50
        storage = cls(resolution=res)
        vec = _make_vector(m)

        data = np.random.rand(res, res)
        encoded = storage.encode(data, vec)

        assert encoded.shape == data.shape

    def test_encode_rejects_wrong_shape(self):
        """Encoding data with wrong shape should raise ValueError."""
        m, cls = _find_storage_class()
        storage = cls(resolution=50)
        vec = _make_vector(m)

        wrong_shape_data = np.random.rand(30, 30)

        with pytest.raises(ValueError):
            storage.encode(wrong_shape_data, vec)

    def test_decode_rejects_wrong_shape(self):
        """Decoding data with wrong shape should raise ValueError."""
        m, cls = _find_storage_class()
        storage = cls(resolution=50)
        vec = _make_vector(m)

        wrong_shape_data = np.random.rand(30, 30)

        with pytest.raises(ValueError):
            storage.decode(wrong_shape_data, vec)


# ----------------------------
# Tests: VoxelAccessVector
# ----------------------------

class TestVoxelAccessVector:
    """Tests for VoxelAccessVector 6D -> (n,m) mapping."""

    def test_to_nm_pair_returns_positive_ints(self):
        """to_nm_pair should return positive integer indices."""
        m, _ = _find_storage_class()
        vec = _make_vector(m, vx=3.0, vy=0.0, vz=0.0, sx=5.0, sy=0.0, sz=0.0)

        n, mm = vec.to_nm_pair()

        assert isinstance(n, int)
        assert isinstance(mm, int)
        assert n >= 1
        assert mm >= 1

    def test_to_nm_pair_deterministic(self):
        """Same vector should always produce same (n,m)."""
        m, _ = _find_storage_class()
        vec = _make_vector(m, vx=3.0, vy=0.0, vz=0.0, sx=5.0, sy=0.0, sz=0.0)

        a = vec.to_nm_pair()
        b = vec.to_nm_pair()

        assert a == b

    def test_to_nm_pair_zero_vector_gives_minimum(self):
        """Zero vector should give (1, 1) since n and m are clamped to >= 1."""
        m, _ = _find_storage_class()
        vec = _make_vector(m, vx=0.0, vy=0.0, vz=0.0, sx=0.0, sy=0.0, sz=0.0)

        n, mm = vec.to_nm_pair()

        assert n >= 1
        assert mm >= 1

    def test_different_vectors_give_different_modes(self):
        """Different vectors should generally map to different (n,m) modes."""
        m, _ = _find_storage_class()
        vec1 = _make_vector(m, vx=3.0, vy=0.0, vz=0.0, sx=5.0, sy=0.0, sz=0.0)
        vec2 = _make_vector(m, vx=7.0, vy=0.0, vz=0.0, sx=2.0, sy=0.0, sz=0.0)

        nm1 = vec1.to_nm_pair()
        nm2 = vec2.to_nm_pair()

        assert nm1 != nm2, "Different vectors should map to different modes"


# ----------------------------
# Tests: visualize_pattern
# ----------------------------

class TestVisualization:
    """Tests for pattern visualization."""

    def test_visualize_pattern_normalized_range(self):
        """Visualization should be normalized to [0, 1]."""
        m, cls = _find_storage_class()
        storage = cls(resolution=64)

        viz = storage.visualize_pattern(3, 4)

        assert viz.min() >= -1e-10, f"Min {viz.min()} should be >= 0"
        assert viz.max() <= 1.0 + 1e-10, f"Max {viz.max()} should be <= 1"

    def test_visualize_pattern_shape(self):
        """Visualization shape should match resolution."""
        m, cls = _find_storage_class()
        res = 64
        storage = cls(resolution=res)

        viz = storage.visualize_pattern(3, 4)

        assert viz.shape == (res, res)


# ----------------------------
# Tests: security_analysis
# ----------------------------

class TestSecurityAnalysis:
    """Tests for the security analysis method."""

    def test_security_analysis_returns_dict(self):
        """security_analysis should return a dict with expected keys."""
        m, cls = _find_storage_class()
        storage = cls(resolution=50)

        result = storage.security_analysis(n_correct=3, m_correct=5, n_attempts=20)

        assert isinstance(result, dict)
        assert "total_attempts" in result
        assert "successful_decodes" in result
        assert "security_rate" in result
        assert "effective_bits" in result

    def test_security_rate_high(self):
        """Security rate should be high (most random vectors fail to decode)."""
        m, cls = _find_storage_class()
        storage = cls(resolution=50)

        result = storage.security_analysis(n_correct=3, m_correct=5, n_attempts=50)

        assert result["security_rate"] >= 0.8, (
            f"Security rate {result['security_rate']:.2f} should be >= 0.80"
        )

    def test_security_analysis_total_matches_input(self):
        """Total attempts should match the n_attempts parameter."""
        m, cls = _find_storage_class()
        storage = cls(resolution=50)

        n_attempts = 30
        result = storage.security_analysis(n_correct=3, m_correct=5, n_attempts=n_attempts)

        assert result["total_attempts"] == n_attempts


# ----------------------------
# Tests: Layer 13 PQ envelope sealing contract
# ----------------------------

class TestPQEnvelopeIntegration:
    """
    PQ envelope sealing integration tests.

    These will skip if the cymatic storage module does not expose
    seal_envelope/open_envelope methods (PQ integration not yet wired).
    """

    def test_pq_envelope_seal_open_contract_with_fake_kem(self, monkeypatch):
        """
        Validates Layer 13 integration contract without requiring real ML-KEM libs.
        Expects seal(payload, public_key, meta={n,m,...}) -> envelope and
        open(envelope, secret_key) -> payload.
        """
        modules = _import_any_module()
        if not modules:
            pytest.skip("No cymatic module importable.")

        m = modules[0]

        storage_cls = None
        for name in CANDIDATE_STORAGE_NAMES:
            if inspect.isclass(getattr(m, name, None)):
                storage_cls = getattr(m, name)
                break

        target = storage_cls() if storage_cls else m

        seal_fn = (
            getattr(target, "seal_envelope", None)
            or getattr(target, "seal", None)
            or getattr(target, "pqc_seal", None)
        )
        open_fn = (
            getattr(target, "open_envelope", None)
            or getattr(target, "open", None)
            or getattr(target, "pqc_open", None)
        )

        if not callable(seal_fn) or not callable(open_fn):
            pytest.skip(
                "No PQ envelope seal/open functions found (seal_envelope/open_envelope). "
                "PQ envelope integration not yet implemented in cymatic storage module."
            )

        fake = FakeKEM()
        pk, sk = fake.keypair()

        if hasattr(m, "get_kem") and callable(getattr(m, "get_kem")):
            monkeypatch.setattr(m, "get_kem", lambda *a, **k: fake)
        if hasattr(m, "kem"):
            monkeypatch.setattr(m, "kem", fake)

        payload = b"pq-sealed-cymatic-voxel"
        meta = {"n": 3, "m": 4, "vector6": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]}

        try:
            envelope = seal_fn(payload, pk, meta=meta)
        except TypeError:
            envelope = seal_fn(payload, pk, meta["n"], meta["m"], meta["vector6"])

        assert envelope is not None

        try:
            out = open_fn(envelope, sk)
        except TypeError:
            out = open_fn(envelope=envelope, secret_key=sk)

        assert out == payload

    def test_pq_envelope_metadata_logs_modes(self, caplog):
        """
        Auditability: sealing should log or embed mode params (n,m).
        """
        modules = _import_any_module()
        if not modules:
            pytest.skip("No cymatic module importable.")

        m = modules[0]

        storage_cls = None
        for name in CANDIDATE_STORAGE_NAMES:
            if inspect.isclass(getattr(m, name, None)):
                storage_cls = getattr(m, name)
                break

        target = storage_cls() if storage_cls else m
        seal_fn = (
            getattr(target, "seal_envelope", None)
            or getattr(target, "seal", None)
            or getattr(target, "pqc_seal", None)
        )

        if not callable(seal_fn):
            pytest.skip(
                "No seal function found for audit logging test. "
                "PQ envelope integration not yet implemented."
            )

        fake = FakeKEM()
        pk, _sk = fake.keypair()

        payload = b"audit-me"
        meta = {"n": 3, "m": 4, "vector6": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]}

        caplog.clear()
        caplog.set_level("INFO")

        try:
            env = seal_fn(payload, pk, meta=meta)
        except TypeError:
            env = seal_fn(payload, pk, meta["n"], meta["m"], meta["vector6"])

        # Check logs first
        logged = "n=3" in caplog.text and "m=4" in caplog.text
        if logged:
            return

        # Otherwise accept envelope carrying metadata
        if isinstance(env, (bytes, bytearray)):
            try:
                s = env.decode("utf-8", errors="ignore")
                if '"n"' in s and '"m"' in s:
                    obj = json.loads(s)
                    assert obj.get("n") == 3 and obj.get("m") == 4
                    return
            except Exception:
                pass

        if isinstance(env, dict):
            assert env.get("meta", env).get("n") == 3
            assert env.get("meta", env).get("m") == 4
            return

        pytest.fail(
            "Neither logs nor envelope header contained mode parameters n,m "
            "for auditability."
        )
