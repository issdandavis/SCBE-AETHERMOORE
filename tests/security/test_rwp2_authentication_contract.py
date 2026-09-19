"""Legacy shared-key envelope authentication and interpreter caller contracts."""

from dataclasses import replace
import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.spiralverse.rwp2_envelope import (
    EnvelopeFactory,
    OperationTier,
    ProtocolTongue,
    ReplayProtector,
    RWP2Envelope,
    SignatureEngine,
    TONGUE_KEYS,
)
from src.spiralverse.aethercode import AethercodeInterpreter, AetherContext, AetherVerse, LedgerHandler
from src.spiralverse.polyglot_alphabet import TongueID


@pytest.fixture
def keys():
    # Public test fixtures; never production keys.
    return {t: hashlib.sha256(b"rwp2-test-only:" + t.value.encode()).digest() for t in ProtocolTongue}


@pytest.mark.parametrize("keys", [None, {}, TONGUE_KEYS])
def test_missing_or_public_demo_keys_reject(keys):
    with pytest.raises(ValueError):
        SignatureEngine(keys)


@pytest.mark.parametrize("field,value", [("kid", "other"), ("version", "3"), ("tier", OperationTier.TIER_2)])
def test_security_metadata_is_bound(keys, field, value):
    engine = SignatureEngine(keys)
    signed = engine.sign(RWP2Envelope(payload=b"test"), set(ProtocolTongue))
    assert engine.verify(signed)[0]
    assert not engine.verify(replace(signed, **{field: value}))[0]


def test_delimiter_shift_does_not_preserve_authentication(keys):
    engine = SignatureEngine(keys)
    signed = engine.sign(RWP2Envelope(spelltext="a|b", payload=b"c"), {ProtocolTongue.KO})
    altered = replace(signed, spelltext="a", payload=b"b|c")
    assert not engine.verify(altered)[0]


def test_explicit_tongues_cannot_weaken_tier_or_be_empty(keys):
    engine = SignatureEngine(keys)
    signed = engine.sign(RWP2Envelope(tier=OperationTier.TIER_3), {ProtocolTongue.KO})
    assert not engine.verify(signed, set())[0]
    assert not engine.verify(signed, {ProtocolTongue.KO})[0]


def test_distinct_tongues_are_domain_separated(keys):
    # Even an accidentally reused key must not allow retagging as another tongue.
    shared = {t: keys[ProtocolTongue.KO] for t in ProtocolTongue}
    engine = SignatureEngine(shared)
    signed = engine.sign(RWP2Envelope(tier=OperationTier.TIER_2), {ProtocolTongue.KO})
    signed.signatures[ProtocolTongue.RU] = signed.signatures[ProtocolTongue.KO]
    assert not engine.verify(signed)[0]


def test_signing_without_requested_key_rejects(keys):
    engine = SignatureEngine({ProtocolTongue.KO: keys[ProtocolTongue.KO]})
    with pytest.raises(ValueError):
        engine.sign(RWP2Envelope(), {ProtocolTongue.RU})


def test_keys_are_copied_and_roundtrip_works(keys):
    engine = SignatureEngine(keys)
    signed = engine.sign(RWP2Envelope(payload=b"\x00\xff|", aad="a|b"), {ProtocolTongue.KO})
    keys[ProtocolTongue.KO] = b"x" * 32
    assert engine.verify(RWP2Envelope.from_json(signed.to_json()))[0]


def test_bad_mac_cannot_consume_a_valid_messages_nonce(keys):
    factory = EnvelopeFactory(keys=keys)
    signed = factory.create("TEST", b"test", ProtocolTongue.KO, OperationTier.TIER_1)
    assert not factory.validate(replace(signed, payload=b"tampered"))[0]
    assert factory.validate(signed)[0]
    assert not factory.validate(signed)[0]


def test_replay_cache_cannot_evict_live_receipts():
    replay = ReplayProtector(max_cache_size=1)
    first, second = RWP2Envelope(), RWP2Envelope()
    assert replay.is_valid(first)[0]
    assert not replay.is_valid(second)[0]
    assert not replay.is_valid(first)[0]


def test_ledger_never_verifies_without_message_and_key():
    handler = LedgerHandler()
    assert handler.execute(AetherVerse(TongueID.LEDGER, "test", "VERIFY nonsense"), AetherContext()) is False


def test_ledger_mac_roundtrip_and_wrong_message(keys):
    key = keys[ProtocolTongue.DR]
    handler = LedgerHandler(signing_key=key)
    ctx = AetherContext()
    signature = handler.execute(AetherVerse(TongueID.LEDGER, "test", 'SIGN "hello"'), ctx)
    assert signature == hmac.new(key, b"scbe:aether-ledger:v1\0hello", hashlib.sha256).hexdigest()
    request = json.dumps({"message": "hello", "mac": signature})
    assert handler.execute(AetherVerse(TongueID.LEDGER, "test", "VERIFY " + request), ctx) is True
    request = json.dumps({"message": "changed", "mac": signature})
    assert handler.execute(AetherVerse(TongueID.LEDGER, "test", "VERIFY " + request), ctx) is False


def test_interpreter_proof_requires_keys_and_verifies_with_matching_keys(keys):
    with pytest.raises(RuntimeError):
        AethercodeInterpreter(synthesize_audio=False).export_proof(AetherContext())
    interpreter = AethercodeInterpreter(synthesize_audio=False, signing_keys=keys)
    signed = interpreter.export_proof(AetherContext())
    assert SignatureEngine(keys).verify(signed)[0]


@pytest.mark.parametrize("tier", list(OperationTier))
def test_all_tiers_with_unicode_delimiters_and_binary_payload(keys, tier):
    factory = EnvelopeFactory(keys)
    signed = factory.create("TEST", b"\x00|\xff", ProtocolTongue.KO, tier, aad="unicode: \u03c6|\u96ea")
    restored = RWP2Envelope.from_json(signed.to_json())
    assert factory.validate(restored)[0]


@pytest.mark.parametrize(
    "field,value",
    [("nonce", "other"), ("timestamp_ms", 1), ("aad", "other"), ("spelltext", "other"), ("payload", b"other")],
)
def test_every_content_field_is_bound(keys, field, value):
    engine = SignatureEngine(keys)
    signed = engine.sign(RWP2Envelope(payload=b"original"), {ProtocolTongue.KO})
    assert not engine.verify(replace(signed, **{field: value}))[0]


@pytest.mark.parametrize("bad_tag", [None, b"x" * 64, "\u00e9" * 64, "x" * 64, ""])
def test_malformed_tags_return_false(keys, bad_tag):
    envelope = RWP2Envelope(signatures={ProtocolTongue.KO: bad_tag})
    assert not SignatureEngine(keys).verify(envelope)[0]


def test_concurrent_replay_has_one_winner(keys):
    factory = EnvelopeFactory(keys)
    signed = factory.create("TEST", b"test", ProtocolTongue.KO, OperationTier.TIER_1)
    with ThreadPoolExecutor(max_workers=4) as executor:
        verdicts = list(executor.map(lambda _: factory.validate(signed)[0], range(12)))
    assert sum(verdicts) == 1


def test_non_signing_interpreter_still_runs():
    context = AethercodeInterpreter(synthesize_audio=False).execute_source('a3f7c2e1:EMIT "Hello"')
    assert any("Hello" in line for line in context.output)
    assert not any("[ERROR]" in line for line in context.output)


def test_ledger_wrong_key_rejects(keys):
    signer = LedgerHandler(signing_key=keys[ProtocolTongue.DR])
    verifier = LedgerHandler(signing_key=keys[ProtocolTongue.KO])
    ctx = AetherContext()
    tag = signer.execute(AetherVerse(TongueID.LEDGER, "test", 'SIGN "hello"'), ctx)
    request = json.dumps({"message": "hello", "mac": tag})
    assert verifier.execute(AetherVerse(TongueID.LEDGER, "test", "VERIFY " + request), ctx) is False
