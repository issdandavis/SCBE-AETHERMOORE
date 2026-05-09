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


def main() -> int:
    if os.getenv("SCBE_FORCE_SKIP_LIBOQS", "").strip().lower() in {"1", "true", "yes"}:
        _die("SCBE_FORCE_SKIP_LIBOQS is set; native security lane must not skip liboqs")

    try:
        import oqs
    except BaseException as exc:  # liboqs-python may raise SystemExit while bootstrapping.
        _die(f"could not import oqs: {exc!r}")

    kem_algorithm = _first_enabled(
        oqs.get_enabled_kem_mechanisms(),
        ("ML-KEM-768", "Kyber768"),
    )
    signature_algorithm = _first_enabled(
        oqs.get_enabled_sig_mechanisms(),
        ("ML-DSA-65", "Dilithium3"),
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

    print("native-liboqs-smoke: PASS")
    print(f"oqs_module={getattr(oqs, '__file__', 'unknown')}")
    print(f"oqs_version={getattr(oqs, '__version__', 'unknown')}")
    print(f"kem_algorithm={kem_algorithm}")
    print(f"signature_algorithm={signature_algorithm}")
    print(f"scbe_backend={status['backend']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
