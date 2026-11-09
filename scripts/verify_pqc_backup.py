#!/usr/bin/env python3
"""Assert the post-quantum backend is real (Tier 1 native liboqs, or Tier 2
pure-Python kyber-py/dilithium-py) — never the Tier-3 SHA-256/HMAC simulation.

Run in CI and at service startup. Exits non-zero if the active backend is not
quantum-resistant, so a deployment can never silently ship the insecure stub.

    python scripts/verify_pqc_backup.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from src.crypto import pqc_liboqs as P  # noqa: E402


def main() -> int:
    st = P.get_pqc_governance_status()
    tier, backend, qr = st["tier"], st["backend"], st["quantum_resistant"]
    print(f"PQC tier={tier}  backend={backend}  quantum_resistant={qr}")

    if not qr or tier >= 3:
        print("FAIL: no quantum-resistant PQC backend. Install one of:")
        print("  Tier 1: liboqs-python + the liboqs C library")
        print("  Tier 2: pip install kyber-py==1.2.0 dilithium-py==1.5.1")
        return 1

    # Prove the active backend actually signs/verifies and does a KEM round trip.
    dsa = P.MLDSA65()
    msg = b"pqc-backup-selftest"
    sig = dsa.sign(msg)
    if not P.MLDSA65.verify_with_public_key(dsa.public_key, msg, sig):
        print("FAIL: ML-DSA-65 valid signature did not verify")
        return 1
    if P.MLDSA65.verify_with_public_key(dsa.public_key, msg + b"!", sig):
        print("FAIL: ML-DSA-65 accepted a tampered message")
        return 1

    kem = P.MLKEM768()
    ct, ss_sender = kem.encapsulate(kem.public_key)
    if kem.decapsulate(ct) != ss_sender:
        print("FAIL: ML-KEM-768 shared secrets did not match")
        return 1

    print("OK: quantum-resistant PQC backend verified (sign/verify + KEM round trip).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
