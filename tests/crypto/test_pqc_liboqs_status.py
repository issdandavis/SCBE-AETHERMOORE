"""Focused tests for PQC governance status reporting."""

import builtins

from src.crypto import pqc_liboqs


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
