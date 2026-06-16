"""Real-PQC behavior tests for dual_lattice — green must mean *working*, not faked.

These assert the properties the old placeholder violated:
  - a real ML-DSA-65 signature round-trips,
  - tampering the signed vector is rejected,
  - a forged signature is rejected,
  - the signer never exposes a secret key (the old verify checked against it),
  - the non-secure Kyber lattice-embedding is fail-closed.

They require a real PQC backend (liboqs); without it ``MLDSA65`` fail-closes, so
the tests skip rather than validate a stub.
"""

import dataclasses
import os

import pytest

pytest.importorskip("oqs", reason="real ML-DSA-65 requires liboqs (oqs)")

from src.crypto.dual_lattice import DilithiumTongueSigner, KyberTongueEncryptor, LatticeVector


def _make_vector(tongues):
    kwargs = {}
    for field in dataclasses.fields(LatticeVector):
        name = field.name
        if name == "tongues":
            kwargs[name] = tongues
        elif name in ("time", "intent", "phase", "flux"):
            kwargs[name] = 0.5
        elif field.default is not dataclasses.MISSING:
            kwargs[name] = field.default
        elif getattr(field, "default_factory", dataclasses.MISSING) is not dataclasses.MISSING:
            kwargs[name] = field.default_factory()
        else:
            kwargs[name] = 0.0
    return LatticeVector(**kwargs)


def test_dilithium_real_sign_verify_roundtrip():
    signer = DilithiumTongueSigner()
    vector = _make_vector([0.9, 0.1, 0.0, 0.0, 0.0, 0.0])
    sig = signer.sign(vector)
    # a real ML-DSA-65 signature is ~3.3 KB, not a 64-byte SHA hash
    assert len(sig["signature"]) > 1000
    assert signer.verify(vector, sig) is True


def test_dilithium_tamper_is_rejected():
    signer = DilithiumTongueSigner()
    original = _make_vector([0.9, 0.1, 0.0, 0.0, 0.0, 0.0])
    tampered = _make_vector([0.1, 0.9, 0.0, 0.0, 0.0, 0.0])
    sig = signer.sign(original)
    assert signer.verify(tampered, sig) is False


def test_dilithium_forged_signature_is_rejected():
    signer = DilithiumTongueSigner()
    vector = _make_vector([0.9, 0.1, 0.0, 0.0, 0.0, 0.0])
    sig = signer.sign(vector)
    forged = dict(sig)
    forged["signature"] = b"\x00" * len(sig["signature"])
    assert signer.verify(vector, forged) is False


def test_dilithium_does_not_expose_secret_key():
    # the old placeholder verified against self.secret_key; the real signer must not expose one
    signer = DilithiumTongueSigner()
    assert not hasattr(signer, "secret_key")


def test_kyber_embedding_is_fail_closed():
    os.environ.pop("SCBE_ALLOW_INSECURE_PQC", None)
    with pytest.raises(RuntimeError):
        KyberTongueEncryptor()
