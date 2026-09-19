#!/usr/bin/env python3
"""Fail-fast native liboqs smoke test for release/security gates.

This script is intentionally stricter than the normal test suite. The normal
suite may use Tier 2/Tier 3 fallbacks so developers can run tests without a C
toolchain. This smoke test proves the final security lane is actually using the
native liboqs backend.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _die(message: str) -> None:
    print(f"native-liboqs-smoke: FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def _first_enabled(enabled: Iterable[str], candidates: Iterable[str]) -> str:
    enabled_set = set(enabled)
    for candidate in candidates:
        if candidate in enabled_set:
            return candidate
    _die(f"none of {list(candidates)} are enabled")
    raise RuntimeError("unreachable after _die")


def _kem_roundtrip(oqs_module, algorithm: str) -> None:
    kem = oqs_module.KeyEncapsulation(algorithm)
    public_key = kem.generate_keypair()
    ciphertext, shared_secret_a = kem.encap_secret(public_key)
    shared_secret_b = kem.decap_secret(ciphertext)

    if shared_secret_a != shared_secret_b:
        _die(f"{algorithm} KEM shared secrets did not match")


def _signature_roundtrip(oqs_module, algorithm: str) -> None:
    message = b"SCBE native liboqs security gate"
    signer = oqs_module.Signature(algorithm)
    public_key = signer.generate_keypair()
    signature = signer.sign(message)
    verified = signer.verify(message, signature, public_key)

    if not verified:
        _die(f"{algorithm} signature did not verify")
    if signer.verify(message + b"tampered", signature, public_key):
        _die(f"{algorithm} accepted a tampered message")


def main() -> int:
    if os.getenv("SCBE_ALLOW_MOCK_PQC") or os.getenv("SCBE_ALLOW_INSECURE_PQC"):
        _die("Mock/insecure opt-ins are forbidden in the native security lane")
    if os.getenv("SCBE_FORCE_SKIP_LIBOQS", "").strip().lower() in {"1", "true", "yes"}:
        _die("SCBE_FORCE_SKIP_LIBOQS is set; native security lane must not skip liboqs")

    try:
        import oqs
    except (Exception, SystemExit) as exc:  # liboqs-python may raise SystemExit while bootstrapping.
        _die(f"could not import oqs: {exc!r}")

    kem_algorithm = _first_enabled(
        oqs.get_enabled_kem_mechanisms(),
        ("ML-KEM-768",),
    )
    signature_algorithm = _first_enabled(
        oqs.get_enabled_sig_mechanisms(),
        ("ML-DSA-65",),
    )

    _kem_roundtrip(oqs, kem_algorithm)
    _signature_roundtrip(oqs, signature_algorithm)

    from src.crypto import pqc_liboqs

    status = pqc_liboqs.get_pqc_governance_status()
    if pqc_liboqs.get_pqc_proof_tier() != 1:
        _die(f"SCBE PQC wrapper is not Tier 1 native: {status}")
    if not pqc_liboqs.is_liboqs_available():
        _die(f"SCBE PQC wrapper reports liboqs unavailable: {status}")
    if not status.get("quantum_resistant"):
        _die(f"SCBE PQC governance status is not quantum resistant: {status}")

    # Exercise both shipped legacy-wrapper locations with the real library.
    # A round-trip or rejected tamper remains a smoke check, not a CMVP claim.
    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    for index, tree in enumerate(("src/symphonic_cipher", "symphonic_cipher")):
        name = f"native_legacy_pqc_{index}"
        spec = importlib.util.spec_from_file_location(name, root / tree / "scbe_aethermoore/pqc/pqc_core.py")
        wrapper = importlib.util.module_from_spec(spec)
        sys.modules[name] = wrapper
        spec.loader.exec_module(wrapper)
        if wrapper.get_backend() != wrapper.PQCBackend.LIBOQS:
            _die(f"{tree}: real backend unavailable")
        keys = wrapper.Kyber768.generate_keypair()
        sealed = wrapper.Kyber768.encapsulate(keys.public_key)
        if wrapper.Kyber768.decapsulate(keys.secret_key, sealed.ciphertext) != sealed.shared_secret:
            _die(f"{tree}: KEM mismatch")
        keys = wrapper.Dilithium3.generate_keypair()
        signature = wrapper.Dilithium3.sign(keys.secret_key, b"native fixture")
        if not wrapper.Dilithium3.verify(keys.public_key, b"native fixture", signature):
            _die(f"{tree}: signature roundtrip failed")
        if wrapper.Dilithium3.verify(keys.public_key, b"tampered fixture", signature):
            _die(f"{tree}: modified message accepted")

        spec = importlib.util.spec_from_file_location(
            f"native_spiral_signatures_{index}", root / tree / "scbe_aethermoore/spiral_seal/signatures.py"
        )
        signing = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(signing)
        signing_status = signing.get_pqc_sig_status()
        if signing_status["backend"] != "liboqs" or signing_status["algorithm"] != "ML-DSA-65":
            _die(f"{tree}: legacy signing API did not select native ML-DSA-65")
        sk, pk = signing.dilithium_keygen()
        _, wrong_pk = signing.dilithium_keygen()
        signed = signing.dilithium_sign(sk, b"native fixture")
        if not signing.dilithium_verify(pk, b"native fixture", signed):
            _die(f"{tree}: legacy signing API failed its roundtrip")
        for test_pk, message, candidate in (
            (pk, b"changed", signed),
            (wrong_pk, b"native fixture", signed),
            (pk, b"native fixture", signed[:-1]),
            (pk, b"native fixture", b"FALLBACK_SIG:" + b"x" * 32),
        ):
            if signing.dilithium_verify(test_pk, message, candidate):
                _die(f"{tree}: legacy signing API accepted invalid authentication")
        print(f"legacy_signing_{index}=ML-DSA-65 verified; wrong key/message/truncation/forgery rejected")

    print("SCBE_LIBOQS_PASS=1")
    print("native-liboqs-smoke: PASS")
    print(f"oqs_module={getattr(oqs, '__file__', 'unknown')}")
    print(f"oqs_version={getattr(oqs, '__version__', 'unknown')}")
    print(f"kem_algorithm={kem_algorithm}")
    print(f"signature_algorithm={signature_algorithm}")
    print(f"scbe_backend={status['backend']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
