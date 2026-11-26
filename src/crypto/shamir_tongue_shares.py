"""Shamir key recovery with one Sacred Tongue carrier per share.

This module implements the multi-party *recovery* mechanism described in the
SCBE paper.  It does not implement distributed threshold decryption or general
multi-party computation: callers reconstruct the secret in one process before
using it.

Security boundary
-----------------

* Shamir sharing is performed byte-by-byte over GF(2^8), using fresh operating-
  system randomness for every polynomial coefficient.
* Tongue encoding is a reversible, typed transport.  It adds no secret entropy.
* The share frame checksum detects corruption, not a malicious party capable of
  rewriting a share and its checksum.  With more than the threshold number of
  shares, reconstruction also rejects mutually inconsistent shares.
* Authenticate stored share files (for example, with an AEAD envelope or a
  signature) when malicious share substitution is in scope.

The binary frame is versioned and binds the threshold, total share count, share
index, assigned tongue, secret length, and a random share-set identifier.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import struct
from dataclasses import dataclass
from typing import Final, Sequence

from .sacred_tongues import SACRED_TONGUE_TOKENIZER, TONGUES, SacredTongueTokenizer

SCHEMA_VERSION: Final[str] = "scbe_shamir_tongue_share_v1"
DEFAULT_TONGUE_CODES: Final[tuple[str, ...]] = tuple(TONGUES)
MAX_SECRET_BYTES: Final[int] = 1 << 20

_FRAME_MAGIC: Final[bytes] = b"STS1"
_FRAME_VERSION: Final[int] = 1
_SET_ID_BYTES: Final[int] = 16
_DIGEST_BYTES: Final[int] = 16
_DIGEST_PERSON: Final[bytes] = b"SCBESH1"
_HEADER: Final[struct.Struct] = struct.Struct(">4sBBBB2sI16s")
_MAX_FRAME_BYTES: Final[int] = _HEADER.size + MAX_SECRET_BYTES + _DIGEST_BYTES
_TEXT_HEADER: Final[str] = "SCBE-SHAMIR-TONGUE-V1"


@dataclass(frozen=True, slots=True)
class SacredTongueShare:
    """A single Shamir share encoded as tokens from one Sacred Tongue."""

    tongue_code: str
    tokens: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.tongue_code not in TONGUES:
            raise ValueError(f"unknown Sacred Tongue: {self.tongue_code!r}")

        # Accept any finite sequence at the API boundary but retain an immutable
        # tuple so a caller cannot mutate a validated share behind our back.
        tokens = tuple(self.tokens)
        object.__setattr__(self, "tokens", tokens)
        if not tokens:
            raise ValueError("share token sequence cannot be empty")
        if len(tokens) > _MAX_FRAME_BYTES:
            raise ValueError("share exceeds the maximum supported frame size")
        if any(not isinstance(token, str) or not token for token in tokens):
            raise TypeError("share tokens must be non-empty strings")

    def to_text(self) -> str:
        """Serialize this share as a portable, human-inspectable text record."""
        return f"{_TEXT_HEADER} tongue={self.tongue_code}\n{' '.join(self.tokens)}\n"

    @classmethod
    def from_text(cls, text: str) -> "SacredTongueShare":
        """Parse the strict text representation produced by :meth:`to_text`."""
        if not isinstance(text, str):
            raise TypeError("share text must be a string")
        lines = text.splitlines()
        if len(lines) < 2:
            raise ValueError("share text is missing its header or token payload")

        prefix = f"{_TEXT_HEADER} tongue="
        if not lines[0].startswith(prefix):
            raise ValueError("unsupported share text header")
        tongue_code = lines[0][len(prefix) :]
        if not tongue_code or any(character.isspace() for character in tongue_code):
            raise ValueError("invalid tongue code in share text header")

        tokens = tuple(" ".join(lines[1:]).split())
        return cls(tongue_code=tongue_code, tokens=tokens)


@dataclass(frozen=True, slots=True)
class ShareMetadata:
    """Public metadata bound into a decoded share frame."""

    schema_version: str
    threshold: int
    share_count: int
    share_index: int
    tongue_code: str
    secret_length: int
    set_id_hex: str


@dataclass(frozen=True, slots=True)
class _DecodedShare:
    metadata: ShareMetadata
    set_id: bytes
    payload: bytes


def _gf_mul(left: int, right: int) -> int:
    """Multiply two field elements in GF(2^8) with the AES polynomial."""
    product = 0
    multiplicand = left
    multiplier = right
    for _ in range(8):
        if multiplier & 1:
            product ^= multiplicand
        high_bit = multiplicand & 0x80
        multiplicand = (multiplicand << 1) & 0xFF
        if high_bit:
            multiplicand ^= 0x1B  # x^8 + x^4 + x^3 + x + 1
        multiplier >>= 1
    return product


def _gf_pow(value: int, exponent: int) -> int:
    result = 1
    base = value
    while exponent:
        if exponent & 1:
            result = _gf_mul(result, base)
        base = _gf_mul(base, base)
        exponent >>= 1
    return result


def _gf_inverse(value: int) -> int:
    if value == 0:
        raise ZeroDivisionError("zero has no multiplicative inverse in GF(2^8)")
    # Every non-zero element a in GF(256) satisfies a^255 = 1.
    return _gf_pow(value, 254)


def _evaluate_polynomial(coefficients: Sequence[int], x_coordinate: int) -> int:
    value = 0
    for coefficient in reversed(coefficients):
        value = _gf_mul(value, x_coordinate) ^ coefficient
    return value


def _lagrange_weights(x_coordinates: Sequence[int], target: int) -> tuple[int, ...]:
    weights: list[int] = []
    for index, x_i in enumerate(x_coordinates):
        numerator = 1
        denominator = 1
        for other_index, x_j in enumerate(x_coordinates):
            if index == other_index:
                continue
            numerator = _gf_mul(numerator, target ^ x_j)
            denominator = _gf_mul(denominator, x_i ^ x_j)
        weights.append(_gf_mul(numerator, _gf_inverse(denominator)))
    return tuple(weights)


def _interpolate_payload(points: Sequence[tuple[int, bytes]], target: int) -> bytes:
    x_coordinates = tuple(point[0] for point in points)
    weights = _lagrange_weights(x_coordinates, target)
    payload_length = len(points[0][1])
    output = bytearray(payload_length)
    for offset in range(payload_length):
        value = 0
        for weight, (_, payload) in zip(weights, points, strict=True):
            value ^= _gf_mul(weight, payload[offset])
        output[offset] = value
    return bytes(output)


def _frame_digest(body: bytes) -> bytes:
    # This is an unkeyed corruption checksum, deliberately not called a MAC.
    return hashlib.blake2s(body, digest_size=_DIGEST_BYTES, person=_DIGEST_PERSON).digest()


def _build_frame(
    *,
    threshold: int,
    share_count: int,
    share_index: int,
    tongue_code: str,
    secret_length: int,
    set_id: bytes,
    payload: bytes,
) -> bytes:
    header = _HEADER.pack(
        _FRAME_MAGIC,
        _FRAME_VERSION,
        threshold,
        share_count,
        share_index,
        tongue_code.encode("ascii"),
        secret_length,
        set_id,
    )
    body = header + payload
    return body + _frame_digest(body)


def _decode_share(
    share: SacredTongueShare,
    tokenizer: SacredTongueTokenizer,
) -> _DecodedShare:
    try:
        frame = tokenizer.decode_tokens(share.tongue_code, list(share.tokens))
    except (KeyError, ValueError) as error:
        raise ValueError(f"invalid {share.tongue_code} share token payload") from error

    minimum_size = _HEADER.size + _DIGEST_BYTES
    if len(frame) < minimum_size:
        raise ValueError("share frame is truncated")
    if len(frame) > _MAX_FRAME_BYTES:
        raise ValueError("share frame exceeds the maximum supported size")

    body = frame[:-_DIGEST_BYTES]
    supplied_digest = frame[-_DIGEST_BYTES:]
    if not hmac.compare_digest(supplied_digest, _frame_digest(body)):
        raise ValueError("share frame checksum mismatch")

    try:
        (
            magic,
            version,
            threshold,
            share_count,
            share_index,
            bound_tongue,
            secret_length,
            set_id,
        ) = _HEADER.unpack(body[: _HEADER.size])
        bound_tongue_code = bound_tongue.decode("ascii")
    except (UnicodeDecodeError, struct.error) as error:
        raise ValueError("share frame header is malformed") from error

    if magic != _FRAME_MAGIC or version != _FRAME_VERSION:
        raise ValueError("unsupported share frame version")
    if not 2 <= threshold <= share_count <= len(TONGUES):
        raise ValueError("share frame has invalid threshold metadata")
    if not 1 <= share_index <= share_count:
        raise ValueError("share frame has invalid share index")
    if bound_tongue_code != share.tongue_code:
        raise ValueError("share frame is bound to a different Sacred Tongue")
    if not 1 <= secret_length <= MAX_SECRET_BYTES:
        raise ValueError("share frame has invalid secret length")

    payload = body[_HEADER.size :]
    if len(payload) != secret_length:
        raise ValueError("share payload length does not match its header")

    metadata = ShareMetadata(
        schema_version=SCHEMA_VERSION,
        threshold=threshold,
        share_count=share_count,
        share_index=share_index,
        tongue_code=share.tongue_code,
        secret_length=secret_length,
        set_id_hex=set_id.hex(),
    )
    return _DecodedShare(metadata=metadata, set_id=set_id, payload=payload)


def split_secret(
    secret: bytes,
    threshold: int,
    tongue_codes: Sequence[str] = DEFAULT_TONGUE_CODES,
    *,
    tokenizer: SacredTongueTokenizer = SACRED_TONGUE_TOKENIZER,
) -> tuple[SacredTongueShare, ...]:
    """Split ``secret`` into uniquely tongued Shamir shares.

    Args:
        secret: Secret bytes to protect.  Keys should be uniformly random.
        threshold: Minimum number of shares required for recovery.
        tongue_codes: Distinct Sacred Tongues, one per generated share.
        tokenizer: Byte/token codec; exposed for compatible profile injection.

    Returns:
        An immutable tuple of encoded shares in the requested tongue order.
    """
    if not isinstance(secret, bytes):
        raise TypeError("secret must be bytes")
    if not 1 <= len(secret) <= MAX_SECRET_BYTES:
        raise ValueError(f"secret length must be between 1 and {MAX_SECRET_BYTES} bytes")
    if not isinstance(threshold, int) or isinstance(threshold, bool):
        raise TypeError("threshold must be an integer")

    codes = tuple(tongue_codes)
    share_count = len(codes)
    if not 2 <= threshold <= share_count <= len(TONGUES):
        raise ValueError("require 2 <= threshold <= share count <= number of Sacred Tongues")
    if len(set(codes)) != share_count:
        raise ValueError("each share must use a different Sacred Tongue")
    unknown_codes = [code for code in codes if code not in TONGUES]
    if unknown_codes:
        raise ValueError(f"unknown Sacred Tongue(s): {unknown_codes!r}")

    set_id = secrets.token_bytes(_SET_ID_BYTES)
    payloads = [bytearray(len(secret)) for _ in codes]
    # Draw coefficient columns in a few large OS-RNG reads instead of making an
    # operating-system call for every secret byte.  Each byte is still an
    # independent, uniformly random field element.
    random_coefficients = [bytearray(secrets.token_bytes(len(secret))) for _ in range(threshold - 1)]
    try:
        for offset, secret_byte in enumerate(secret):
            coefficients = (
                secret_byte,
                *(column[offset] for column in random_coefficients),
            )
            for share_offset in range(share_count):
                payloads[share_offset][offset] = _evaluate_polynomial(
                    coefficients,
                    share_offset + 1,
                )
    finally:
        # Best-effort cleanup of the mutable coefficient buffers.  Python does
        # not promise elimination of every interpreter/runtime copy.
        for column in random_coefficients:
            column[:] = bytes(len(column))

    shares: list[SacredTongueShare] = []
    for share_offset, (tongue_code, payload) in enumerate(zip(codes, payloads, strict=True)):
        frame = _build_frame(
            threshold=threshold,
            share_count=share_count,
            share_index=share_offset + 1,
            tongue_code=tongue_code,
            secret_length=len(secret),
            set_id=set_id,
            payload=bytes(payload),
        )
        shares.append(
            SacredTongueShare(
                tongue_code=tongue_code,
                tokens=tuple(tokenizer.encode_bytes(tongue_code, frame)),
            )
        )
    return tuple(shares)


def inspect_share(
    share: SacredTongueShare,
    *,
    tokenizer: SacredTongueTokenizer = SACRED_TONGUE_TOKENIZER,
) -> ShareMetadata:
    """Validate one share and return only its public metadata."""
    if not isinstance(share, SacredTongueShare):
        raise TypeError("share must be a SacredTongueShare")
    return _decode_share(share, tokenizer).metadata


def recover_secret(
    shares: Sequence[SacredTongueShare],
    *,
    tokenizer: SacredTongueTokenizer = SACRED_TONGUE_TOKENIZER,
) -> bytes:
    """Recover a secret from a threshold-consistent set of Tongue shares.

    When more than the required number of shares are supplied, every additional
    share must agree with the polynomial fixed by the first threshold shares.
    The function fails closed on mismatch; it does not attempt error correction
    or decide which participant supplied a bad share.
    """
    supplied_shares = tuple(shares)
    if not supplied_shares:
        raise ValueError("at least one share is required")
    if any(not isinstance(share, SacredTongueShare) for share in supplied_shares):
        raise TypeError("all shares must be SacredTongueShare instances")

    decoded = sorted(
        (_decode_share(share, tokenizer) for share in supplied_shares),
        key=lambda item: item.metadata.share_index,
    )
    reference = decoded[0]
    expected = (
        reference.metadata.threshold,
        reference.metadata.share_count,
        reference.metadata.secret_length,
        reference.set_id,
    )
    for item in decoded[1:]:
        actual = (
            item.metadata.threshold,
            item.metadata.share_count,
            item.metadata.secret_length,
            item.set_id,
        )
        if actual != expected:
            raise ValueError("shares do not belong to the same share set")

    threshold = reference.metadata.threshold
    if len(decoded) < threshold:
        raise ValueError(f"need at least {threshold} shares, received {len(decoded)}")
    if len(decoded) > reference.metadata.share_count:
        raise ValueError("received more shares than the frame declares")

    indexes = [item.metadata.share_index for item in decoded]
    if len(set(indexes)) != len(indexes):
        raise ValueError("duplicate share index")
    tongues = [item.metadata.tongue_code for item in decoded]
    if len(set(tongues)) != len(tongues):
        raise ValueError("duplicate Sacred Tongue carrier")

    basis = decoded[:threshold]
    basis_points = [(item.metadata.share_index, item.payload) for item in basis]
    for extra in decoded[threshold:]:
        expected_payload = _interpolate_payload(basis_points, extra.metadata.share_index)
        if not hmac.compare_digest(expected_payload, extra.payload):
            raise ValueError("supplied shares are not mutually consistent")

    return _interpolate_payload(basis_points, 0)


__all__ = [
    "DEFAULT_TONGUE_CODES",
    "MAX_SECRET_BYTES",
    "SCHEMA_VERSION",
    "SacredTongueShare",
    "ShareMetadata",
    "inspect_share",
    "recover_secret",
    "split_secret",
]
