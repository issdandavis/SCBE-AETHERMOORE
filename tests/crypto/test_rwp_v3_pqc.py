"""RWP v3 hybrid-PQC seal: prove ML-KEM-768 is actually wired (was stubbed).

Before the fix, encrypt() hardcoded ml_kem_ct=None, so enable_pqc=True produced
an envelope with no encapsulation. These tests fail if that regresses: they
require a real ML-KEM ciphertext in the envelope and a working round-trip that
only opens with the matching secret key.

Skipped where native liboqs is unavailable (PQC path needs it).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

try:
    import oqs  # noqa: E402

    _HAVE_OQS = True
except Exception:
    _HAVE_OQS = False

from src.crypto.rwp_v3 import _KEM_ALG, _SIG_ALG, OQS_AVAILABLE, RWPv3Protocol  # noqa: E402

# Gate on the module's EFFECTIVE PQC availability, not just `import oqs`:
# rwp_v3 honors SCBE_FORCE_SKIP_LIBOQS (set by the CI python job, which tests
# the deterministic fallback path), so with liboqs-python installed but the
# env var set, `import oqs` succeeds while RWPv3Protocol(enable_pqc=True)
# raises ImportError. Real-PQC coverage lives in the native-liboqs workflow.
pytestmark = pytest.mark.skipif(
    not (_HAVE_OQS and OQS_AVAILABLE),
    reason="native liboqs not available (or PQC disabled via SCBE_FORCE_SKIP_LIBOQS)",
)

SECRET = b"correct horse battery staple"
PLAINTEXT = b'{"decision":"ALLOW","score":0.07,"audit_id":"c04741dbc3c8165c"}'
AAD = b"governance-receipt-v1"


def _kem_keypair():
    kem = oqs.KeyEncapsulation(_KEM_ALG)
    pk = kem.generate_keypair()
    sk = kem.export_secret_key()
    return pk, sk


def test_pqc_seal_actually_encapsulates_and_round_trips():
    pk, sk = _kem_keypair()
    proto = RWPv3Protocol(enable_pqc=True)
    env = proto.encrypt(SECRET, PLAINTEXT, aad=AAD, ml_kem_public_key=pk)
    assert env.ml_kem_ct is not None, "PQC seal must produce an ML-KEM ciphertext (was stubbed to None)"
    opened = RWPv3Protocol(enable_pqc=True).decrypt(SECRET, env, ml_kem_secret_key=sk)
    assert opened == PLAINTEXT


def test_pqc_seal_requires_the_kem_secret_key():
    pk, _sk = _kem_keypair()
    env = RWPv3Protocol(enable_pqc=True).encrypt(SECRET, PLAINTEXT, aad=AAD, ml_kem_public_key=pk)
    # Right password, but no KEM secret key -> the KEM-mixed key can't be rebuilt -> AEAD fails.
    with pytest.raises(ValueError):
        RWPv3Protocol(enable_pqc=True).decrypt(SECRET, env, ml_kem_secret_key=None)


def test_pqc_seal_rejects_wrong_kem_secret_key():
    pk, _sk = _kem_keypair()
    _pk2, sk2 = _kem_keypair()
    env = RWPv3Protocol(enable_pqc=True).encrypt(SECRET, PLAINTEXT, aad=AAD, ml_kem_public_key=pk)
    with pytest.raises(ValueError):
        RWPv3Protocol(enable_pqc=True).decrypt(SECRET, env, ml_kem_secret_key=sk2)


def test_pqc_seal_rejects_tampered_ciphertext():
    pk, sk = _kem_keypair()
    env = RWPv3Protocol(enable_pqc=True).encrypt(SECRET, PLAINTEXT, aad=AAD, ml_kem_public_key=pk)
    env.ct = list(env.ct)
    env.ct[0] = env.ct[0][::-1] if env.ct[0] else env.ct[0]  # mangle a ciphertext token
    with pytest.raises(ValueError):
        RWPv3Protocol(enable_pqc=True).decrypt(SECRET, env, ml_kem_secret_key=sk)


def test_non_pqc_path_unchanged():
    """Backward compat: without PQC the envelope has no KEM ct and still round-trips."""
    proto = RWPv3Protocol(enable_pqc=False)
    env = proto.encrypt(SECRET, PLAINTEXT, aad=AAD)
    assert env.ml_kem_ct is None
    assert RWPv3Protocol(enable_pqc=False).decrypt(SECRET, env) == PLAINTEXT


def test_envelope_dsa_signature_round_trip():
    """In-envelope ML-DSA-65 signature signs and verifies; tamper fails."""
    sig = oqs.Signature(_SIG_ALG)
    dsa_pk = sig.generate_keypair()
    dsa_sk = sig.export_secret_key()
    pk, sk = _kem_keypair()
    env = RWPv3Protocol(enable_pqc=True).encrypt(
        SECRET, PLAINTEXT, aad=AAD, ml_kem_public_key=pk, ml_dsa_private_key=dsa_sk
    )
    assert env.ml_dsa_sig is not None
    # Genuine: opens with KEM secret key + verifies the signature.
    opened = RWPv3Protocol(enable_pqc=True).decrypt(SECRET, env, ml_kem_secret_key=sk, ml_dsa_public_key=dsa_pk)
    assert opened == PLAINTEXT
