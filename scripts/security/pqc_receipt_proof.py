"""PQC receipt proof — Claim 12 enablement evidence, end-to-end on real liboqs.

Builds a governance-decision receipt shaped exactly like patent Claim 12:
sign the decision identifier + score + timestamp with ML-DSA-65 (FIPS 204),
encapsulate a session key with ML-KEM-768 (FIPS 203), bundle a structured
receipt, and have a downstream verifier check the signature before "executing."

It does not just run the primitives — it proves the receipt REJECTS tampering:
  - flip a field of the signed payload  -> signature verification must FAIL
  - flip a byte of the KEM ciphertext   -> recovered session key must DIFFER

Every check is asserted; the script exits non-zero if any check fails, so it is
usable as reproducible evidence (and as a regression test) rather than a demo
that prints "ok" while doing nothing.

HONEST SCOPE: the ML-DSA signing path is production code (agents/agent_bus_signing.py
Signer, used by the agent bus). The ML-KEM ciphertext is bundled here directly via
src/crypto/pqc_liboqs.MLKEM768 because the RWP v3 seal path (rwp_v3.py encrypt) has
the KEM wiring stubbed (ml_kem_ct is hardcoded to None). This script therefore
proves the claim is ENABLED by the codebase's real primitives; wiring the KEM into
the production seal path is a separate fix (see report).

Run:  PYTHONPATH=. python scripts/security/pqc_receipt_proof.py
"""

from __future__ import annotations

import base64
import hashlib
import json
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from agents.agent_bus_signing import ALG_MLDSA65, EventSigner  # noqa: E402
from src.crypto.pqc_liboqs import (  # noqa: E402
    MLKEM768,
    get_pqc_backend,
    get_pqc_proof_tier,
    is_liboqs_available,
)

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    mark = "✓" if ok else "✗"
    print(f"  [{mark}] {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def main() -> int:
    # Force UTF-8 so the ✓/✗ glyphs survive a cp1252 console or piped subprocess.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    print("\n  PQC RECEIPT PROOF — Claim 12 (ML-DSA-65 sign + ML-KEM-768 encapsulate)\n")
    print(f"  backend : {get_pqc_backend()}")
    print(f"  tier    : {get_pqc_proof_tier()} (1=native liboqs, 2=pure-python, 3=stub)\n")

    # Tier-1 (real liboqs) is the only configuration that proves enablement.
    check("real liboqs is active (not a stub)", is_liboqs_available() and get_pqc_proof_tier() == 1, get_pqc_backend())

    # ---- 1. The decision payload the gate would emit ---------------------- #
    action = "execute_code: rm -rf /tmp/scratch"
    payload = {
        "audit_id": hashlib.sha256(action.encode()).hexdigest()[:16],
        "decision": "ALLOW",
        "score": 0.07,
        "signals": ["policy:clean", "geoseal:none"],
        "timestamp": "2026-06-10T00:00:00Z",
    }

    # ---- 2. Sign it with ML-DSA-65 (production Signer) -------------------- #
    with tempfile.TemporaryDirectory() as tmp:
        signer = EventSigner("aether-gate", key_dir=Path(tmp))
        ok_init = signer.initialize()
        check("ML-DSA-65 signer initialized", ok_init and signer.algorithm == ALG_MLDSA65, signer.algorithm)
        sig_b64, pk_b64, alg = signer.sign(payload)
        check(
            "receipt signed with ML-DSA-65",
            alg == ALG_MLDSA65 and bool(sig_b64),
            f"sig {len(base64.b64decode(sig_b64))} bytes",
        )

        # ---- 3. Downstream verifier checks the signature ----------------- #
        verified = EventSigner.verify(payload, sig_b64, pk_b64, alg)
        check("downstream verify accepts genuine receipt", verified is True)

        # ---- 4. TAMPER: flip the decision -> signature must FAIL ---------- #
        forged = dict(payload, decision="DENY", score=0.99)
        tampered_rejected = EventSigner.verify(forged, sig_b64, pk_b64, alg) is False
        check("tampered receipt is REJECTED (sig fails)", tampered_rejected)

    # ---- 5. Encapsulate a session key with ML-KEM-768 -------------------- #
    kem = MLKEM768()
    ct, ss_sender = kem.encapsulate(kem.public_key)
    ss_receiver = kem.decapsulate(ct)
    check(
        "ML-KEM-768 session key encapsulated + recovered",
        ss_sender == ss_receiver,
        f"shared secret {len(ss_sender)} bytes",
    )

    # ---- 6. TAMPER: flip a ciphertext byte -> recovered key must DIFFER -- #
    bad = bytearray(ct)
    bad[0] ^= 0x01
    ss_bad = kem.decapsulate(bytes(bad))
    check("tampered KEM ciphertext yields a DIFFERENT key", ss_bad != ss_receiver)

    # ---- 7. Assemble the structured Claim-12 receipt --------------------- #
    receipt = {
        **payload,
        "pqc": {
            "sig_alg": "ML-DSA-65",
            "kem_alg": "ML-KEM-768",
            "signature_b64": sig_b64,
            "signer_pubkey_b64": pk_b64,
            "kem_ciphertext_b64": base64.b64encode(ct).decode(),
        },
    }
    print("\n  sample structured receipt (truncated):")
    shown = dict(receipt)
    shown["pqc"] = {k: (v[:24] + "…" if isinstance(v, str) and len(v) > 24 else v) for k, v in receipt["pqc"].items()}
    print("    " + json.dumps(shown, indent=2).replace("\n", "\n    "))

    print()
    if FAILURES:
        print(f"  RESULT: ✗ {len(FAILURES)} check(s) FAILED: {', '.join(FAILURES)}\n")
        return 1
    print("  RESULT: ✓ all checks passed — Claim 12 receipt is real on liboqs, and rejects tampering.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
