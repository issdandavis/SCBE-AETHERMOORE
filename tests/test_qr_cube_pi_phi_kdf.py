# tests/test_qr_cube_pi_phi_kdf.py
"""
Pytest contract tests for the Holographic QR Cube π^φ key derivation (kdf='pi_phi').

These tests enforce *security properties* and *engineering invariants*:
- Deterministic output for identical inputs
- Strong input sensitivity (d*, coherence, nonce, aad, cube_id, salt)
- Domain separation (changing "context"/"purpose" must change output)
- Numeric hygiene (reject NaN/Inf; optionally clamp negatives if you choose)
- Output shape/stability (bytes, correct length)

NOTE: This test suite intentionally FAILS until `derive_pi_phi_key` exists.

Expected function signature (recommended):

    def derive_pi_phi_key(
        *,
        d_star: float,
        coherence: float,
        cube_id: str,
        aad: bytes,
        nonce: bytes,
        salt: bytes = b"",
        out_len: int = 32,
        context: bytes = b"scbe:qr-cube:pi_phi:v1",
    ) -> bytes:
        ...

If your signature differs, edit `_call()` below.
"""

from __future__ import annotations

import math
import os
import pytest


# -----------------------------------------------------------------------------
# Resolver: find derive_pi_phi_key in your codebase
# -----------------------------------------------------------------------------

CANDIDATE_IMPORTS = [
    # If you create a dedicated module:
    "src.symphonic_cipher.scbe_aethermoore.qr_cube_kdf",
    "src.symphonic_cipher.scbe_aethermoore.pi_phi_kdf",
    # If you place it inside cymatic storage / QR cube implementation:
    "src.symphonic_cipher.scbe_aethermoore.cymatic_storage",
    # If you place it in a general constants/crypto module:
    "src.symphonic_cipher.scbe_aethermoore.constants",
    "src.crypto.qr_cube_kdf",
]


def _resolve_kdf():
    last_err = None
    for mod in CANDIDATE_IMPORTS:
        try:
            m = __import__(mod, fromlist=["derive_pi_phi_key"])
            fn = getattr(m, "derive_pi_phi_key", None)
            if callable(fn):
                return fn, mod
        except Exception as e:  # noqa: BLE001 - intentional: we want the last import error
            last_err = e

    raise AssertionError(
        "derive_pi_phi_key(...) not found.\n"
        "Implement it in one of these modules (or update CANDIDATE_IMPORTS):\n"
        f"  - " + "\n  - ".join(CANDIDATE_IMPORTS) + "\n\n"
        f"Last import error: {repr(last_err)}"
    )


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def derive_pi_phi_key():
    fn, _mod = _resolve_kdf()
    return fn


def _call(
    fn,
    *,
    d_star: float,
    coherence: float,
    cube_id: str,
    aad: bytes,
    nonce: bytes,
    salt: bytes = b"",
    out_len: int = 32,
    context: bytes = b"scbe:qr-cube:pi_phi:v1",
) -> bytes:
    """
    Adapter for your final signature.
    If you implement a different signature, modify this one function only.
    """
    return fn(
        d_star=d_star,
        coherence=coherence,
        cube_id=cube_id,
        aad=aad,
        nonce=nonce,
        salt=salt,
        out_len=out_len,
        context=context,
    )


def _rand_bytes(n: int) -> bytes:
    return os.urandom(n)


# -----------------------------------------------------------------------------
# Core tests
# -----------------------------------------------------------------------------

class TestPiPhiKDFContract:
    def test_returns_bytes_and_expected_length(self, derive_pi_phi_key):
        key = _call(
            derive_pi_phi_key,
            d_star=0.25,
            coherence=0.9,
            cube_id="cube-001",
            aad=b"aad:header-hash",
            nonce=b"\x01" * 12,
            salt=b"\x02" * 32,
            out_len=32,
        )
        assert isinstance(key, (bytes, bytearray))
        assert len(key) == 32

    def test_deterministic_same_inputs(self, derive_pi_phi_key):
        params = dict(
            d_star=0.25,
            coherence=0.9,
            cube_id="cube-001",
            aad=b"aad:header-hash",
            nonce=b"\x01" * 12,
            salt=b"\x02" * 32,
            out_len=32,
            context=b"scbe:qr-cube:pi_phi:v1",
        )
        k1 = _call(derive_pi_phi_key, **params)
        k2 = _call(derive_pi_phi_key, **params)
        assert k1 == k2

    def test_changing_d_star_changes_key(self, derive_pi_phi_key):
        base = dict(
            coherence=0.9,
            cube_id="cube-001",
            aad=b"aad:header-hash",
            nonce=b"\x01" * 12,
            salt=b"\x02" * 32,
            out_len=32,
        )
        k1 = _call(derive_pi_phi_key, d_star=0.25, **base)
        k2 = _call(derive_pi_phi_key, d_star=0.35, **base)
        assert k1 != k2

    def test_changing_coherence_changes_key(self, derive_pi_phi_key):
        base = dict(
            d_star=0.25,
            cube_id="cube-001",
            aad=b"aad:header-hash",
            nonce=b"\x01" * 12,
            salt=b"\x02" * 32,
            out_len=32,
        )
        k1 = _call(derive_pi_phi_key, coherence=0.90, **base)
        k2 = _call(derive_pi_phi_key, coherence=0.91, **base)
        assert k1 != k2

    def test_changing_cube_id_changes_key(self, derive_pi_phi_key):
        base = dict(
            d_star=0.25,
            coherence=0.9,
            aad=b"aad:header-hash",
            nonce=b"\x01" * 12,
            salt=b"\x02" * 32,
            out_len=32,
        )
        k1 = _call(derive_pi_phi_key, cube_id="cube-001", **base)
        k2 = _call(derive_pi_phi_key, cube_id="cube-002", **base)
        assert k1 != k2

    def test_changing_aad_changes_key(self, derive_pi_phi_key):
        base = dict(
            d_star=0.25,
            coherence=0.9,
            cube_id="cube-001",
            nonce=b"\x01" * 12,
            salt=b"\x02" * 32,
            out_len=32,
        )
        k1 = _call(derive_pi_phi_key, aad=b"aad:header-hash", **base)
        k2 = _call(derive_pi_phi_key, aad=b"aad:header-hash:mutated", **base)
        assert k1 != k2

    def test_changing_nonce_changes_key(self, derive_pi_phi_key):
        base = dict(
            d_star=0.25,
            coherence=0.9,
            cube_id="cube-001",
            aad=b"aad:header-hash",
            salt=b"\x02" * 32,
            out_len=32,
        )
        k1 = _call(derive_pi_phi_key, nonce=b"\x01" * 12, **base)
        k2 = _call(derive_pi_phi_key, nonce=b"\x03" * 12, **base)
        assert k1 != k2

    def test_changing_salt_changes_key(self, derive_pi_phi_key):
        base = dict(
            d_star=0.25,
            coherence=0.9,
            cube_id="cube-001",
            aad=b"aad:header-hash",
            nonce=b"\x01" * 12,
            out_len=32,
        )
        k1 = _call(derive_pi_phi_key, salt=b"\x02" * 32, **base)
        k2 = _call(derive_pi_phi_key, salt=b"\x04" * 32, **base)
        assert k1 != k2

    def test_domain_separation_context_changes_key(self, derive_pi_phi_key):
        base = dict(
            d_star=0.25,
            coherence=0.9,
            cube_id="cube-001",
            aad=b"aad:header-hash",
            nonce=b"\x01" * 12,
            salt=b"\x02" * 32,
            out_len=32,
        )
        k1 = _call(derive_pi_phi_key, context=b"scbe:qr-cube:pi_phi:v1", **base)
        k2 = _call(derive_pi_phi_key, context=b"scbe:sacred-egg:pi_phi:v1", **base)
        assert k1 != k2

    def test_out_len_controls_output_size(self, derive_pi_phi_key):
        base = dict(
            d_star=0.25,
            coherence=0.9,
            cube_id="cube-001",
            aad=b"aad:header-hash",
            nonce=b"\x01" * 12,
            salt=b"\x02" * 32,
        )
        k16 = _call(derive_pi_phi_key, out_len=16, **base)
        k32 = _call(derive_pi_phi_key, out_len=32, **base)
        k64 = _call(derive_pi_phi_key, out_len=64, **base)
        assert len(k16) == 16
        assert len(k32) == 32
        assert len(k64) == 64
        # if HKDF-expand-like, prefix property should hold
        assert k32[:16] == k16
        assert k64[:32] == k32

    # -------------------------------------------------------------------------
    # Numeric hygiene: NaN/Inf must be rejected (security-critical)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_rejects_non_finite_d_star(self, derive_pi_phi_key, bad):
        with pytest.raises((ValueError, AssertionError), match="d_star|finite|nan|inf"):
            _call(
                derive_pi_phi_key,
                d_star=bad,
                coherence=0.9,
                cube_id="cube-001",
                aad=b"aad",
                nonce=b"\x01" * 12,
                salt=b"\x02" * 32,
                out_len=32,
            )

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_rejects_non_finite_coherence(self, derive_pi_phi_key, bad):
        with pytest.raises((ValueError, AssertionError), match="coherence|finite|nan|inf"):
            _call(
                derive_pi_phi_key,
                d_star=0.25,
                coherence=bad,
                cube_id="cube-001",
                aad=b"aad",
                nonce=b"\x01" * 12,
                salt=b"\x02" * 32,
                out_len=32,
            )

    def test_coherence_range_policy(self, derive_pi_phi_key):
        """
        Decide your policy:
          - Either clamp coherence into [0,1], OR
          - Reject out-of-range values.
        This test enforces *reject* by default (safer).
        If you clamp, update the assertion accordingly.
        """
        with pytest.raises((ValueError, AssertionError), match="coherence|range|0..1"):
            _call(
                derive_pi_phi_key,
                d_star=0.25,
                coherence=1.5,
                cube_id="cube-001",
                aad=b"aad",
                nonce=b"\x01" * 12,
                salt=b"\x02" * 32,
                out_len=32,
            )

    # -------------------------------------------------------------------------
    # Optional: sanity check the underlying scalar π^(φ*d*) behavior
    # (This does NOT assume you return the scalar; it just enforces the math
    # helper you *should* use internally.)
    # -------------------------------------------------------------------------

    def test_pi_phi_scalar_monotonicity_sanity(self):
        """
        Pure math: π^(φ*d*) increases with d* if φ>0.
        If you maintain a helper like pi_phi_scalar(d_star), it should obey this.
        """
        pi = math.pi
        phi = (1 + 5**0.5) / 2

        def scalar(d):  # reference expectation
            return pi ** (phi * d)

        assert scalar(0.1) < scalar(0.2) < scalar(0.3)


# -----------------------------------------------------------------------------
# Fuzz-ish: basic avalanche expectation (not statistical, just smoke)
# -----------------------------------------------------------------------------

class TestPiPhiKDFAvalancheSmoke:
    def test_small_bitflip_in_aad_changes_key(self, derive_pi_phi_key):
        aad = bytearray(b"aad:header-hash")
        aad2 = bytearray(aad)
        aad2[-1] ^= 0x01  # flip 1 bit

        base = dict(
            d_star=0.25,
            coherence=0.9,
            cube_id="cube-001",
            nonce=b"\x01" * 12,
            salt=b"\x02" * 32,
            out_len=32,
        )
        k1 = _call(derive_pi_phi_key, aad=bytes(aad), **base)
        k2 = _call(derive_pi_phi_key, aad=bytes(aad2), **base)
        assert k1 != k2

    def test_randomized_inputs_are_unlikely_to_collide(self, derive_pi_phi_key):
        """
        Not a proof, just a smoke test that obvious collisions aren't happening.
        """
        seen = set()
        for i in range(25):
            key = _call(
                derive_pi_phi_key,
                d_star=0.01 * (i + 1),
                coherence=0.5 + 0.01 * i,
                cube_id=f"cube-{i:03d}",
                aad=_rand_bytes(32),
                nonce=_rand_bytes(12),
                salt=_rand_bytes(32),
                out_len=32,
            )
            assert key not in seen
            seen.add(key)
