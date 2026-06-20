"""Real ML-DSA-65 authority signatures for decision envelopes — green must mean working.

Asserts the asymmetric properties HMAC cannot give: verification with the PUBLIC key
only, a forged signature rejected, a tampered payload rejected, and a wrong key rejected.
Requires a real PQC backend (liboqs); skips otherwise.
"""

from __future__ import annotations

import pytest

try:
    import google.protobuf

    assert hasattr(google.protobuf, "__version__")
except ImportError:
    pytest.skip("google.protobuf not installed", allow_module_level=True)

pytest.importorskip("oqs", reason="real ML-DSA-65 requires liboqs (oqs)")

from src.crypto.pqc_liboqs import MLDSA65, MLDSAKeyPair
from src.governance.decision_envelope_v1 import (
    AUTO_ALLOW,
    HIGH,
    make_envelope_v1,
    sign_envelope_mldsa,
    verify_envelope_mldsa,
)

NOW_MS = 1_700_000_000_000


def _mk_env():
    return make_envelope_v1(
        envelope_id="env-mldsa-001",
        mission_id="mars-sol-48",
        swarm_id="swarm-a",
        issuer="ground-control",
        key_id="k-mldsa-01",
        valid_from_ms=NOW_MS - 1_000,
        valid_until_ms=NOW_MS + 60_000,
        agent_allowlist=["agent-1"],
        capability_allowlist=["nav.move"],
        target_allowlist=["site-A"],
        mission_phase_allowlist=["SURFACE_OPS"],
        max_risk_tier=HIGH,
        power_min=40.0,
        bandwidth_min=10.0,
        thermal_max=85.0,
        rules=[{"capability": "nav.move", "target": "site-A", "boundary": AUTO_ALLOW}],
    )


def _keypair():
    dsa = MLDSA65()
    return MLDSAKeyPair(public_key=dsa.public_key, secret_key=dsa.secret_key)


def test_mldsa_envelope_roundtrips_with_public_key_only():
    kp = _keypair()
    signed = sign_envelope_mldsa(_mk_env(), kp)
    # real ML-DSA-65 signature, not a 32-byte HMAC tag
    assert len(bytes(signed.authority.signature)) > 1000
    ok, reason = verify_envelope_mldsa(signed, lambda i, k: kp.public_key, now_ms=NOW_MS)
    assert ok, reason


def test_mldsa_envelope_rejects_forged_signature():
    kp = _keypair()
    signed = sign_envelope_mldsa(_mk_env(), kp)
    signed.authority.signature = b"\x00" * len(bytes(signed.authority.signature))
    ok, reason = verify_envelope_mldsa(signed, lambda i, k: kp.public_key, now_ms=NOW_MS)
    assert not ok


def test_mldsa_envelope_rejects_tampered_payload():
    kp = _keypair()
    signed = sign_envelope_mldsa(_mk_env(), kp)
    # mutate a signed field after signing -> signed_payload_hash no longer matches
    signed.identity.mission_id = "tampered-mission"
    ok, reason = verify_envelope_mldsa(signed, lambda i, k: kp.public_key, now_ms=NOW_MS)
    assert not ok


def test_mldsa_envelope_rejects_wrong_public_key():
    kp = _keypair()
    other = _keypair()
    signed = sign_envelope_mldsa(_mk_env(), kp)
    ok, reason = verify_envelope_mldsa(signed, lambda i, k: other.public_key, now_ms=NOW_MS)
    assert not ok
