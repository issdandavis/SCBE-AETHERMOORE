"""Tests for the keyed trichromatic state chain and multi-sign orientation.

EVERY TEST HERE MUST BE ABLE TO FAIL. The code under test replaces a forgery check whose
"attacker" drew its forged values from a fixed-seed RNG, so the check had no failing input at
all. The corrective discipline: each negative test tampers with exactly one thing and asserts
rejection, and a positive control asserts the untampered case still passes -- so a suite that
rejected everything would be caught too.
"""

from __future__ import annotations

import pytest

from src.crypto.h_lwe import hkdf_sha256
from src.governance.orientation import (
    Orientation,
    all_orientations,
    antipodal_pairs,
    label_space_bits,
)
from src.governance.trichromatic_state_chain import (
    GENESIS_PREV_TAG,
    MASTER_KEY_BYTES,
    TAG_BYTES,
    TONGUES,
    ChainEntry,
    TrichromaticStateChain,
    canonicalize,
    chain_from_entries,
    derive_tongue_keys,
    generate_master_key,
    state_digest,
)

MASTER = bytes(range(32))
OTHER_MASTER = bytes(range(1, 33))
SESSION = "session-alpha"

SAMPLE_STATE = {
    "tongues": [["KO", [0.11, 0.22, 0.33]], ["AV", [0.44, 0.55, 0.66]]],
    "bridges": {"KO-AV": [0.1, 0.2, 0.3]},
}


def _chain(master: bytes = MASTER, session: str = SESSION) -> TrichromaticStateChain:
    return TrichromaticStateChain(master_key=master, session_id=session)


# ---------------------------------------------------------------------------
# Positive control -- if this fails, every negative test below is meaningless
# ---------------------------------------------------------------------------


def test_untampered_chain_verifies():
    chain = _chain()
    for i in range(4):
        chain.append({"step": i, **SAMPLE_STATE})
    ok, reason = chain.verify_chain()
    assert ok, reason
    assert reason == "ok"


def test_first_entry_links_to_genesis():
    chain = _chain()
    entry = chain.append(SAMPLE_STATE)
    assert entry.prev_tag == GENESIS_PREV_TAG
    assert entry.counter == 1


def test_tag_is_256_bit():
    chain = _chain()
    entry = chain.append(SAMPLE_STATE)
    assert len(entry.tag) == TAG_BYTES == 32
    assert TAG_BYTES * 8 == 256


# ---------------------------------------------------------------------------
# The HKDF this all rests on -- cross-checked against an independent implementation
# ---------------------------------------------------------------------------


def test_repo_hkdf_matches_reference_implementation():
    """SCBE's hand-rolled HKDF must equal pyca/cryptography's, or the derivation is wrong."""
    hkdf_mod = pytest.importorskip("cryptography.hazmat.primitives.kdf.hkdf")
    hashes = pytest.importorskip("cryptography.hazmat.primitives.hashes")

    for salt, info, length in [
        (b"", b"", 32),
        (b"salt-value", b"info-value", 32),
        (b"s", b"i", 64),
        (b"\x00" * 32, b"scbe", 48),
    ]:
        reference = hkdf_mod.HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info).derive(MASTER)
        assert hkdf_sha256(MASTER, salt=salt, info=info, length=length) == reference, (salt, info, length)


# ---------------------------------------------------------------------------
# Tampering -- one thing changed per test
# ---------------------------------------------------------------------------


def test_modified_state_is_rejected():
    chain = _chain()
    entry = chain.append(SAMPLE_STATE)
    assert chain.verify_state(entry, SAMPLE_STATE)

    tampered = {**SAMPLE_STATE, "bridges": {"KO-AV": [0.1, 0.2, 0.30000001]}}
    assert not chain.verify_state(entry, tampered)


def test_every_single_bit_flip_in_the_tag_is_rejected():
    """Exhaustive: all 256 single-bit flips must fail. No sampling, no luck."""
    chain = _chain()
    entry = chain.append(SAMPLE_STATE)
    assert chain.verify_entry(entry, expected_prev_tag=entry.prev_tag, expected_counter=entry.counter)

    accepted = []
    for bit in range(TAG_BYTES * 8):
        mutated = bytearray(entry.tag)
        mutated[bit // 8] ^= 1 << (bit % 8)
        forged = ChainEntry(
            counter=entry.counter,
            nonce=entry.nonce,
            digest=entry.digest,
            prev_tag=entry.prev_tag,
            tag=bytes(mutated),
            tongue=entry.tongue,
            orientation=entry.orientation,
        )
        if chain.verify_entry(forged, expected_prev_tag=entry.prev_tag, expected_counter=entry.counter):
            accepted.append(bit)
    assert accepted == [], f"forged tags accepted at bit positions {accepted}"


def test_modified_digest_is_rejected():
    chain = _chain()
    entry = chain.append(SAMPLE_STATE)
    forged = ChainEntry(
        counter=entry.counter,
        nonce=entry.nonce,
        digest=state_digest({"different": "state"}),
        prev_tag=entry.prev_tag,
        tag=entry.tag,
        tongue=entry.tongue,
        orientation=entry.orientation,
    )
    assert not chain.verify_entry(forged, expected_prev_tag=entry.prev_tag, expected_counter=entry.counter)


def test_modified_nonce_is_rejected():
    chain = _chain()
    entry = chain.append(SAMPLE_STATE)
    forged = ChainEntry(
        counter=entry.counter,
        nonce=b"\xff" * len(entry.nonce),
        digest=entry.digest,
        prev_tag=entry.prev_tag,
        tag=entry.tag,
        tongue=entry.tongue,
        orientation=entry.orientation,
    )
    assert not chain.verify_entry(forged, expected_prev_tag=entry.prev_tag, expected_counter=entry.counter)


# ---------------------------------------------------------------------------
# Replay and reordering
# ---------------------------------------------------------------------------


def test_replaying_an_earlier_entry_is_rejected():
    """The whole point of the counter + prev-tag chain."""
    chain = _chain()
    first = chain.append({"step": 1})
    chain.append({"step": 2})
    third = chain.append({"step": 3})

    # An attacker replays entry 1 in position 3. Its tag is genuine; its position is not.
    replayed = list(chain.entries)
    replayed[2] = first
    ok, reason = chain.verify_chain(replayed)
    assert not ok
    assert "counter" in reason or "link" in reason or "tag" in reason

    # Sanity: the untouched chain still verifies, so the rejection above was about the replay.
    ok_clean, _ = chain.verify_chain()
    assert ok_clean
    assert third.counter == 3


def test_reordering_two_entries_is_rejected():
    chain = _chain()
    for i in range(3):
        chain.append({"step": i})
    swapped = list(chain.entries)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    ok, reason = chain.verify_chain(swapped)
    assert not ok, reason


def test_truncating_the_chain_head_still_verifies_prefix():
    """A prefix is a valid chain; only tampering breaks it. Guards against over-rejection."""
    chain = _chain()
    for i in range(5):
        chain.append({"step": i})
    ok, reason = chain.verify_chain(list(chain.entries)[:3])
    assert ok, reason


def test_dropping_a_middle_entry_is_rejected():
    chain = _chain()
    for i in range(4):
        chain.append({"step": i})
    gapped = [e for e in chain.entries if e.counter != 2]
    ok, reason = chain.verify_chain(gapped)
    assert not ok, reason


# ---------------------------------------------------------------------------
# Key and session binding
# ---------------------------------------------------------------------------


def test_wrong_master_key_rejects():
    chain = _chain()
    entry = chain.append(SAMPLE_STATE)
    attacker = _chain(master=OTHER_MASTER)
    assert not attacker.verify_entry(entry, expected_prev_tag=entry.prev_tag, expected_counter=entry.counter)


def test_wrong_session_id_rejects():
    chain = _chain()
    entry = chain.append(SAMPLE_STATE)
    other_session = _chain(session="session-beta")
    assert not other_session.verify_entry(entry, expected_prev_tag=entry.prev_tag, expected_counter=entry.counter)


def test_tag_minted_under_one_tongue_does_not_verify_as_another():
    chain = _chain()
    entry = chain.append(SAMPLE_STATE, tongue="KO")
    assert chain.verify_entry(entry, expected_prev_tag=entry.prev_tag, expected_counter=entry.counter)

    relabelled = ChainEntry(
        counter=entry.counter,
        nonce=entry.nonce,
        digest=entry.digest,
        prev_tag=entry.prev_tag,
        tag=entry.tag,
        tongue="AV",
        orientation=entry.orientation,
    )
    assert not chain.verify_entry(relabelled, expected_prev_tag=entry.prev_tag, expected_counter=entry.counter)


def test_six_tongue_keys_are_distinct():
    keys = derive_tongue_keys(MASTER, SESSION)
    assert set(keys) == set(TONGUES)
    assert len(set(keys.values())) == len(TONGUES)
    assert all(len(k) == MASTER_KEY_BYTES for k in keys.values())


def test_tongue_keys_differ_across_sessions():
    a = derive_tongue_keys(MASTER, "session-a")
    b = derive_tongue_keys(MASTER, "session-b")
    assert all(a[t] != b[t] for t in TONGUES)


def test_master_key_length_is_enforced():
    with pytest.raises(ValueError):
        TrichromaticStateChain(master_key=b"short", session_id=SESSION)
    with pytest.raises(ValueError):
        TrichromaticStateChain(master_key=MASTER, session_id="")


def test_generate_master_key_is_right_size_and_not_constant():
    keys = {generate_master_key() for _ in range(8)}
    assert all(len(k) == MASTER_KEY_BYTES for k in keys)
    assert len(keys) == 8


# ---------------------------------------------------------------------------
# Canonical encoding -- the concatenation-ambiguity trap
# ---------------------------------------------------------------------------


def test_field_splitting_cannot_be_shifted():
    """('ab','c') and ('a','bc') must not produce the same authenticated message."""
    chain = _chain()
    e1 = chain.append({"x": "ab", "y": "c"}, nonce=b"\x01" * 16)
    chain2 = _chain()
    e2 = chain2.append({"x": "a", "y": "bc"}, nonce=b"\x01" * 16)
    assert e1.digest != e2.digest
    assert e1.tag != e2.tag


def test_canonicalization_is_key_order_independent():
    assert canonicalize({"a": 1, "b": 2}) == canonicalize({"b": 2, "a": 1})
    assert state_digest({"a": 1, "b": 2}) == state_digest({"b": 2, "a": 1})


def test_round_trip_through_dict_preserves_verification():
    chain = _chain()
    for i in range(3):
        chain.append({"step": i}, orientation="+-+")
    shipped = [e.to_dict() for e in chain.entries]
    rebuilt = chain_from_entries(MASTER, SESSION, shipped)
    ok, reason = chain.verify_chain(rebuilt)
    assert ok, reason


# ---------------------------------------------------------------------------
# Multi-sign orientation
# ---------------------------------------------------------------------------


def test_orientation_changes_the_tag_but_not_the_value():
    """Issac's point exactly: discrete up/down, no value change."""
    a = _chain()
    b = _chain()
    fixed_nonce = b"\x07" * 16
    up = a.append(SAMPLE_STATE, orientation="+++", nonce=fixed_nonce)
    down = b.append(SAMPLE_STATE, orientation="---", nonce=fixed_nonce)

    assert up.digest == down.digest, "the VALUE must be identical -- orientation is not in the digest"
    assert up.tag != down.tag, "the TAG must differ -- orientation is bound under it"


def test_single_sign_flip_changes_the_tag():
    a = _chain()
    b = _chain()
    n = b"\x09" * 16
    t1 = a.append(SAMPLE_STATE, orientation="+-+", nonce=n).tag
    t2 = b.append(SAMPLE_STATE, orientation="++-", nonce=n).tag
    assert t1 != t2


def test_orientation_is_validated_not_silently_accepted():
    chain = _chain()
    with pytest.raises(ValueError):
        chain.append(SAMPLE_STATE, orientation="+x-")
    with pytest.raises(ValueError):
        Orientation.parse("")


def test_issacs_six_triples_are_three_antipodal_pairs():
    listed = ["+-+", "+++", "---", "-+-", "++-", "--+"]
    orients = [Orientation.parse(s) for s in listed]
    pairs = {frozenset((o.canonical, o.negate().canonical)) for o in orients}
    assert pairs == {
        frozenset(("+-+", "-+-")),
        frozenset(("+++", "---")),
        frozenset(("++-", "--+")),
    }
    assert len(pairs) == 3


def test_pure_and_trit_counts():
    assert len(all_orientations(3, allow_zero=False)) == 8
    assert len(all_orientations(3, allow_zero=True)) == 27
    assert len(all_orientations(6, allow_zero=False)) == 64
    assert len(all_orientations(6, allow_zero=True)) == 729


def test_antipodal_pairs_partition_the_pure_set():
    pairs = antipodal_pairs(3)
    assert len(pairs) == 4
    flat = [o.canonical for pair in pairs for o in pair]
    assert len(flat) == len(set(flat)) == 8
    assert set(flat) == {o.canonical for o in all_orientations(3, allow_zero=False)}


def test_negate_is_an_involution():
    for o in all_orientations(3, allow_zero=True):
        assert o.negate().negate() == o


def test_flat_orientation_is_its_own_antipode():
    flat = Orientation.flat(3)
    assert flat.canonical == "000"
    assert flat.negate() == flat
    assert not flat.is_pure()


def test_orientation_maps_to_tongues_at_arity_six():
    o = Orientation.parse("+-0+-0")
    assert o.as_tongue_map() == {"KO": 1, "AV": -1, "RU": 0, "CA": 1, "UM": -1, "DR": 0}
    with pytest.raises(ValueError):
        Orientation.parse("+-+").as_tongue_map()


def test_agreement_counts_matching_axes():
    assert Orientation.parse("+-+").agreement(Orientation.parse("+-+")) == 3
    assert Orientation.parse("+-+").agreement(Orientation.parse("-+-")) == 0
    assert Orientation.parse("+-+").agreement(Orientation.parse("++-")) == 1


# ---------------------------------------------------------------------------
# Honest accounting -- the report must refuse the overstatements
# ---------------------------------------------------------------------------


def test_security_report_refuses_to_multiply_key_entropy():
    r = TrichromaticStateChain.security_report()
    assert r["security_bits"] == 256
    assert r["tag_bits"] == 256
    assert r["derived_keys"] == len(TONGUES) + 1
    assert r["derived_keys_add_entropy"] is False
    assert r["naive_sum_is_false"] is True
    assert r["claimed_security_bits_if_naively_summed"] == 7 * 256
    assert r["security_bits"] != r["claimed_security_bits_if_naively_summed"]


def test_security_report_calls_detection_dimensions_dimensions():
    r = TrichromaticStateChain.security_report(detection_dimensions=63)
    assert r["detection_dimensions"] == 63
    assert r["detection_dimensions_are_entropy"] is False
    assert r["security_bits"] == 256
    # the old claim was 63 * 8 = 504 "bits of state"; it must not appear as security
    assert r["security_bits"] != 63 * 8


def test_security_report_does_not_bank_orientation_as_security():
    r = TrichromaticStateChain.security_report(orientation_arity=6)
    assert r["orientation_states"] == 729
    assert r["orientation_adds_security_bits"] is False
    assert r["security_bits"] == 256
    assert label_space_bits(6, allow_zero=True) == pytest.approx(9.5098, abs=1e-3)


def test_defensible_claim_string_is_the_agreed_wording():
    r = TrichromaticStateChain.security_report(detection_dimensions=63)
    assert r["defensible_claim"] == (
        "63-dimensional trichromatic detection overlay with a 256-bit authenticated, " "replay-resistant state chain"
    )


def test_forgery_probability_is_the_tag_bound():
    r = TrichromaticStateChain.security_report()
    assert r["forgery_probability_per_attempt"] == 2.0**-256
    assert r["replay_resistant"] is True
