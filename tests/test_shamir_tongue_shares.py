from __future__ import annotations

from itertools import combinations

import pytest

from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER
from src.crypto.shamir_tongue_shares import (
    DEFAULT_TONGUE_CODES,
    SCHEMA_VERSION,
    SacredTongueShare,
    _gf_inverse,
    _gf_mul,
    inspect_share,
    recover_secret,
    split_secret,
)


def test_gf256_known_aes_field_vectors() -> None:
    assert _gf_mul(0x57, 0x83) == 0xC1
    assert _gf_mul(0x03, _gf_inverse(0x03)) == 1


def test_three_of_six_recovers_from_every_threshold_combination() -> None:
    secret = bytes(range(32))
    shares = split_secret(secret, threshold=3)

    assert tuple(share.tongue_code for share in shares) == DEFAULT_TONGUE_CODES
    assert len({share.tongue_code for share in shares}) == 6
    assert recover_secret(shares) == secret
    for selected in combinations(shares, 3):
        assert recover_secret(selected) == secret


def test_two_shares_do_not_recover_a_three_share_secret() -> None:
    shares = split_secret(b"owner-recovery-key", threshold=3)
    with pytest.raises(ValueError, match="need at least 3"):
        recover_secret(shares[:2])


def test_public_metadata_is_bound_into_each_share() -> None:
    shares = split_secret(b"structured-secret", threshold=4)
    metadata = [inspect_share(share) for share in shares]

    assert {item.schema_version for item in metadata} == {SCHEMA_VERSION}
    assert {item.threshold for item in metadata} == {4}
    assert {item.share_count for item in metadata} == {6}
    assert [item.share_index for item in metadata] == [1, 2, 3, 4, 5, 6]
    assert [item.tongue_code for item in metadata] == list(DEFAULT_TONGUE_CODES)
    assert len({item.set_id_hex for item in metadata}) == 1


def test_text_serialization_round_trips_without_changing_tokens() -> None:
    original = split_secret(b"portable-share", threshold=2, tongue_codes=("ko", "dr"))[0]
    restored = SacredTongueShare.from_text(original.to_text())
    assert restored == original


def test_valid_token_tampering_is_detected_by_frame_checksum() -> None:
    share = split_secret(b"checksum-target", threshold=2, tongue_codes=("av", "ru"))[0]
    tokens = list(share.tokens)
    replacement_byte = (SACRED_TONGUE_TOKENIZER.token_to_byte["av"][tokens[-1]] + 1) % 256
    tokens[-1] = SACRED_TONGUE_TOKENIZER.byte_to_token["av"][replacement_byte]
    tampered = SacredTongueShare("av", tuple(tokens))

    with pytest.raises(ValueError, match="checksum mismatch"):
        inspect_share(tampered)


def test_shares_from_different_sets_are_rejected() -> None:
    first = split_secret(b"same-length-secret", threshold=2, tongue_codes=("ko", "av"))
    second = split_secret(b"different-secret!", threshold=2, tongue_codes=("ru", "ca"))

    with pytest.raises(ValueError, match="same share set"):
        recover_secret((first[0], second[1]))


def test_duplicate_share_cannot_satisfy_threshold() -> None:
    shares = split_secret(b"no-duplicate-votes", threshold=2, tongue_codes=("um", "dr"))
    with pytest.raises(ValueError, match="duplicate share index"):
        recover_secret((shares[0], shares[0]))


@pytest.mark.parametrize(
    ("threshold", "tongues", "message"),
    [
        (1, ("ko", "av"), "require 2"),
        (3, ("ko", "av"), "require 2"),
        (2, ("ko", "ko"), "different Sacred Tongue"),
        (2, ("ko", "zz"), "unknown Sacred Tongue"),
    ],
)
def test_invalid_split_configuration_fails_closed(
    threshold: int,
    tongues: tuple[str, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        split_secret(b"secret", threshold=threshold, tongue_codes=tongues)


def test_empty_or_non_byte_secret_is_rejected() -> None:
    with pytest.raises(ValueError, match="secret length"):
        split_secret(b"", threshold=2, tongue_codes=("ko", "av"))
    with pytest.raises(TypeError, match="secret must be bytes"):
        split_secret("not-bytes", threshold=2, tongue_codes=("ko", "av"))  # type: ignore[arg-type]
