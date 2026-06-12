"""Focused tests for PQC governance status reporting."""

import builtins

import pytest

from src.crypto import pqc_liboqs
from src.crypto.pqc_liboqs import MLDSA65, MLDSAKeyPair


def test_load_oqs_module_handles_system_exit(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "oqs":
            raise SystemExit("liboqs bootstrap failed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert pqc_liboqs._load_oqs_module() is None


def test_get_pqc_proof_tier_native(monkeypatch):
    monkeypatch.setattr(pqc_liboqs, "LIBOQS_AVAILABLE", True)
    monkeypatch.setattr(pqc_liboqs, "PURE_PQC_AVAILABLE", False)
    assert pqc_liboqs.get_pqc_proof_tier() == 1
    assert "liboqs" in pqc_liboqs.get_pqc_backend()


def test_get_pqc_proof_tier_pure_python(monkeypatch):
    monkeypatch.setattr(pqc_liboqs, "LIBOQS_AVAILABLE", False)
    monkeypatch.setattr(pqc_liboqs, "PURE_PQC_AVAILABLE", True)
    assert pqc_liboqs.get_pqc_proof_tier() == 2
    assert pqc_liboqs.get_pqc_backend() == "pure-python (kyber-py/dilithium-py)"


def test_get_pqc_proof_tier_stub(monkeypatch):
    monkeypatch.setattr(pqc_liboqs, "LIBOQS_AVAILABLE", False)
    monkeypatch.setattr(pqc_liboqs, "PURE_PQC_AVAILABLE", False)
    assert pqc_liboqs.get_pqc_proof_tier() == 3
    assert pqc_liboqs.get_pqc_backend() == "stub (SHA-256/HMAC simulation)"


def test_get_pqc_governance_status_exposes_quantum_resistance(monkeypatch):
    monkeypatch.setattr(pqc_liboqs, "LIBOQS_AVAILABLE", False)
    monkeypatch.setattr(pqc_liboqs, "PURE_PQC_AVAILABLE", True)

    status = pqc_liboqs.get_pqc_governance_status()

    assert status["tier"] == 2
    assert status["proof"] == "pure_python_quantum_resistant"
    assert status["quantum_resistant"] is True
    assert status["backend"] == "pure-python (kyber-py/dilithium-py)"


def test_mldsa65_from_keypair_loaded_key_signs_and_verifies():
    """Regression: a key loaded via from_keypair must bind into the signing
    object so sign() uses THAT key.

    The old from_keypair built ``oqs.Signature(alg)`` without ``secret_key=``,
    so the liboqs object signed with no/throwaway key and the signature failed
    to verify against the loaded public key — silently breaking persisted /
    cross-process identities. This is the exact failure that broke reaction-state
    receipt signing after a process restart.
    """
    if pqc_liboqs.get_pqc_proof_tier() == 3:
        pytest.skip("simulation tier has no real keypair to round-trip")

    # Generate an identity and capture its key material (as if persisted to disk).
    original = MLDSA65()
    pk, sk = original.public_key, original.secret_key
    message = b"reaction-state packet payload"

    # Rehydrate from the captured key pair (the persisted-identity load path).
    loaded = MLDSA65.from_keypair(MLDSAKeyPair(public_key=pk, secret_key=sk))
    signature = loaded.sign(message)

    # The loaded key must self-verify...
    assert loaded.verify(message, signature) is True
    # ...and verify under a fresh verifier holding only the public key.
    verifier = MLDSA65.from_keypair(MLDSAKeyPair(public_key=pk, secret_key=sk))
    assert verifier.verify(message, signature) is True
    # Tamper is still caught.
    assert loaded.verify(message + b"x", signature) is False


def test_oqs_import_keeps_stdout_clean():
    """Regression: liboqs-python prints an informational banner to STDOUT on
    import ("liboqs-python faulthandler is disabled"). Consumers sign lazily
    from CLIs whose stdout is a machine-readable JSON contract (e.g.
    ``scbe react balance --json``), so the loader must route the banner to
    stderr. A fresh interpreter is required because oqs may already be in
    sys.modules here."""
    import subprocess
    import sys

    probe = (
        "import sys; sys.path.insert(0, '.'); " "from src.crypto.pqc_liboqs import _load_oqs_module; _load_oqs_module()"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "", f"oqs import leaked onto stdout: {result.stdout!r}"
