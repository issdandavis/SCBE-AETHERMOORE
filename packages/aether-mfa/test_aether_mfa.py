"""Tests for Aether MFA: RFC interop vectors + push-approval attack cases."""

import base64
import time

import pytest

import aether_mfa as mfa

# RFC 4226 Appendix D test vectors: secret = ASCII "12345678901234567890".
_RFC4226_SECRET = base64.b32encode(b"12345678901234567890").decode("ascii")
_RFC4226_HOTP = [
    "755224",
    "287082",
    "359152",
    "969429",
    "338314",
    "254676",
    "287922",
    "162583",
    "399871",
    "520489",
]


def test_hotp_matches_rfc4226_vectors():
    # Interoperability proof: our codes equal the standard -> any authenticator app will agree.
    for counter, expected in enumerate(_RFC4226_HOTP):
        assert mfa.hotp(_RFC4226_SECRET, counter) == expected


def test_totp_matches_rfc6238_vector():
    # RFC 6238 SHA1 vector at T=59s -> 8-digit 94287082.
    assert mfa.totp(_RFC4226_SECRET, at=59, period=30, digits=8) == "94287082"


def test_verify_totp_accepts_current_and_drift_window():
    secret = mfa.generate_secret()
    now = 1_000_000.0
    assert mfa.verify_totp(secret, mfa.totp(secret, at=now), at=now)
    # code from the previous period still accepted within window=1
    assert mfa.verify_totp(secret, mfa.totp(secret, at=now - 30), at=now, window=1)
    # two periods out is rejected at window=1
    assert not mfa.verify_totp(secret, mfa.totp(secret, at=now - 90), at=now, window=1)


def test_verify_totp_rejects_wrong_code():
    secret = mfa.generate_secret()
    assert not mfa.verify_totp(secret, "000000", at=1_000_000.0)


def test_provisioning_uri_is_otpauth():
    uri = mfa.provisioning_uri(
        "JBSWY3DPEHPK3PXP", account="issac@example.com", issuer="SCBE"
    )
    assert uri.startswith("otpauth://totp/SCBE:issac%40example.com?")
    assert "secret=JBSWY3DPEHPK3PXP" in uri


# ---- push approval ---------------------------------------------------- #


def _enrolled():
    verifier = mfa.PushVerifier(ttl_seconds=120)
    device_id, private_bytes, device = mfa.enroll_device(label="phone")
    verifier.register_device(device)
    return verifier, device_id, private_bytes


def test_push_happy_path_approves_bound_action():
    verifier, device_id, private_bytes = _enrolled()
    ch = verifier.create_challenge(
        device_id, action="publish dataset scbe-train", at=1000.0
    )
    sig = mfa.approve(ch, private_bytes, entered_match_number=ch.match_number)
    verdict = verifier.verify_approval(ch.challenge_id, sig, ch.match_number, at=1001.0)
    assert verdict.allow
    assert verdict.action == "publish dataset scbe-train"


def test_push_rejects_wrong_match_number():
    verifier, device_id, private_bytes = _enrolled()
    ch = verifier.create_challenge(device_id, action="spend $500", at=1000.0)
    wrong = "99" if ch.match_number != "99" else "00"
    # Device refuses to sign a number the human didn't actually see.
    with pytest.raises(ValueError):
        mfa.approve(ch, private_bytes, entered_match_number=wrong)


def test_push_rejects_expired_challenge():
    verifier, device_id, private_bytes = _enrolled()
    ch = verifier.create_challenge(device_id, action="delete prod", at=1000.0)
    sig = mfa.approve(ch, private_bytes, entered_match_number=ch.match_number)
    verdict = verifier.verify_approval(
        ch.challenge_id, sig, ch.match_number, at=1000.0 + 200
    )
    assert not verdict.allow
    assert verdict.reason == "challenge expired"


def test_push_is_single_use_no_replay():
    verifier, device_id, private_bytes = _enrolled()
    ch = verifier.create_challenge(device_id, action="rotate key", at=1000.0)
    sig = mfa.approve(ch, private_bytes, entered_match_number=ch.match_number)
    first = verifier.verify_approval(ch.challenge_id, sig, ch.match_number, at=1001.0)
    assert first.allow
    # Replaying the exact same signature must fail -- challenge was consumed.
    replay = verifier.verify_approval(ch.challenge_id, sig, ch.match_number, at=1002.0)
    assert not replay.allow
    assert replay.reason == "challenge already consumed"


def test_push_signature_is_action_bound():
    # Pin the headline property in ISOLATION: only `action` changes, everything else is held fixed.
    # Sign a challenge, then tamper ONLY the action server-side and re-verify the SAME signature.
    # If `action` were dropped from signing_payload(), this would (wrongly) still pass -> this guards it.
    verifier, device_id, private_bytes = _enrolled()
    ch = verifier.create_challenge(device_id, action="read logs", at=1000.0)
    sig = mfa.approve(ch, private_bytes, entered_match_number=ch.match_number)
    # sanity: the untampered signature verifies (proves the failure below is action, not something else)
    assert verifier.verify_approval(
        ch.challenge_id, sig, ch.match_number, at=1001.0
    ).allow

    ch2 = verifier.create_challenge(device_id, action="read logs", at=1000.0)
    sig2 = mfa.approve(ch2, private_bytes, entered_match_number=ch2.match_number)
    ch2.action = "delete logs"  # mutate ONLY the action; id/nonce/match unchanged
    verdict = verifier.verify_approval(
        ch2.challenge_id, sig2, ch2.match_number, at=1001.0
    )
    assert not verdict.allow
    assert verdict.reason == "invalid signature"


def test_push_signature_is_nonce_bound():
    # Same isolation discipline for the nonce: mutate ONLY the nonce, re-verify the same signature.
    verifier, device_id, private_bytes = _enrolled()
    ch = verifier.create_challenge(device_id, action="read logs", at=1000.0)
    sig = mfa.approve(ch, private_bytes, entered_match_number=ch.match_number)
    ch.nonce = "deadbeef" * 4  # mutate ONLY the nonce
    verdict = verifier.verify_approval(ch.challenge_id, sig, ch.match_number, at=1001.0)
    assert not verdict.allow
    assert verdict.reason == "invalid signature"


def test_push_rejects_forged_signature():
    verifier, device_id, _ = _enrolled()
    ch = verifier.create_challenge(device_id, action="approve wire", at=1000.0)
    # An attacker with a different key cannot approve.
    _, attacker_priv, _ = mfa.enroll_device()
    forged = mfa.approve(ch, attacker_priv, entered_match_number=ch.match_number)
    verdict = verifier.verify_approval(
        ch.challenge_id, forged, ch.match_number, at=1001.0
    )
    assert not verdict.allow
    assert verdict.reason == "invalid signature"


def test_unknown_device_cannot_get_challenge():
    verifier = mfa.PushVerifier()
    with pytest.raises(KeyError):
        verifier.create_challenge("nope", action="x", at=time.time())
