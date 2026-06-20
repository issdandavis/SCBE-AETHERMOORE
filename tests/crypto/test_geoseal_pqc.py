"""Real post-quantum crypto in the Sacred Egg seal path (GeoSeal).

Proves the egg path uses genuine ML-KEM-768 (FIPS 203) + ML-DSA-65 (FIPS 204) +
AES-256-GCM -- not the former SHA-256/HMAC/XOR "Kyber"/"Dilithium" costume that
only round-tripped when pk == sk. These tests fail if that costume regresses.

Skipped where native liboqs is unavailable (the seal fails closed).
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

try:
    import oqs  # noqa: F401

    _HAVE_OQS = True
except Exception:
    _HAVE_OQS = False

from src.symphonic_cipher.scbe_aethermoore.cli_toolkit import (  # noqa: E402
    geoseal_decrypt,
    geoseal_encrypt,
    geoseal_keygen,
)

pytestmark = pytest.mark.skipif(not _HAVE_OQS, reason="native liboqs not available")

CTX = [0.1, -0.2, 0.15, 0.05, -0.1, 0.08]
PT = b"the yolk is the secret material"
PT_B64 = base64.b64encode(PT).decode()


def _field(bundle_b64: str, name: str) -> bytes:
    return base64.b64decode(json.loads(base64.b64decode(bundle_b64))[name])


def test_round_trip_with_real_keys():
    pub, sec = geoseal_keygen()
    env = geoseal_encrypt(PT_B64, CTX, pub, sec)
    ok, pt = geoseal_decrypt(env, CTX, sec, pub)
    assert ok and pt == PT


def test_envelope_declares_real_algorithms_and_ct_size():
    pub, sec = geoseal_keygen()
    env = geoseal_encrypt(PT_B64, CTX, pub, sec)
    assert env["pqc"]["kem"] in ("ML-KEM-768", "Kyber768")
    assert env["pqc"]["sig"] in ("ML-DSA-65", "Dilithium3")
    assert env["pqc"]["aead"] == "AES-256-GCM"
    # Real ML-KEM-768 ciphertext is 1088 bytes; the mock used a 32-byte SHA-256 digest.
    assert len(base64.b64decode(env["ct_k"])) == 1088
    # AES-256-GCM ciphertext is plaintext + a 16-byte tag.
    assert len(base64.b64decode(env["ct_spec"])) == len(PT) + 16


def test_keys_are_real_fips_sizes_not_32_byte_mocks():
    pub, sec = geoseal_keygen()
    assert len(_field(pub, "kem_pub")) == 1184  # ML-KEM-768 public key
    assert len(_field(sec, "kem_sec")) == 2400  # ML-KEM-768 secret key
    assert len(_field(pub, "dsa_pub")) == 1952  # ML-DSA-65 public key


def test_random_32_byte_mock_keys_are_rejected():
    """The old costume round-tripped with pk == sk 32-byte keys; real PQC must not."""
    mock = base64.b64encode(os.urandom(32)).decode()
    with pytest.raises(ValueError):
        geoseal_encrypt(PT_B64, CTX, mock, mock)


def test_tampered_ciphertext_fails():
    pub, sec = geoseal_keygen()
    env = geoseal_encrypt(PT_B64, CTX, pub, sec)
    raw = bytearray(base64.b64decode(env["ct_spec"]))
    raw[0] ^= 0x01
    env["ct_spec"] = base64.b64encode(bytes(raw)).decode()
    ok, pt = geoseal_decrypt(env, CTX, sec, pub)
    assert not ok and pt is None


def test_tampered_geometry_aad_fails():
    """Mutating the geometric attestation breaks the GCM AAD (and the signature)."""
    pub, sec = geoseal_keygen()
    env = geoseal_encrypt(PT_B64, CTX, pub, sec)
    env["attest"]["path"] = "tampered-path"
    ok, pt = geoseal_decrypt(env, CTX, sec, pub)
    assert not ok and pt is None


def test_wrong_kem_secret_key_fails():
    """Right signature key, wrong KEM secret -> decapsulation mismatch -> AEAD failure."""
    pub, sec = geoseal_keygen()
    _pub2, sec2 = geoseal_keygen()
    env = geoseal_encrypt(PT_B64, CTX, pub, sec)
    ok, pt = geoseal_decrypt(env, CTX, sec2, pub)
    assert not ok and pt is None


def test_forged_signature_fails():
    pub, sec = geoseal_keygen()
    env = geoseal_encrypt(PT_B64, CTX, pub, sec)
    sig = bytearray(base64.b64decode(env["sig"]))
    sig[0] ^= 0x01
    env["sig"] = base64.b64encode(bytes(sig)).decode()
    ok, pt = geoseal_decrypt(env, CTX, sec, pub)
    assert not ok and pt is None


def test_two_keygens_are_distinct():
    """Sanity: keygen is not deterministic/constant (the mock derived keys from a fixed seed)."""
    pub1, _ = geoseal_keygen()
    pub2, _ = geoseal_keygen()
    assert _field(pub1, "kem_pub") != _field(pub2, "kem_pub")
