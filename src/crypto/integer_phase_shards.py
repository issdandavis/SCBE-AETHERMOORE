"""Exact-integer research scaffold for phase-labelled key shards.

This module does not define a new encryption algorithm.  Security comes from
the entropy sources, SHA-3/HKDF, and the independently random owner share.  The
integer transforms are reversible structure for audit, routing, and domain
separation; they do not create entropy.

The proposed ``2.75`` scale is represented exactly as ``11/4``.  Every
remainder is carried into the next integer and the terminal remainder is kept,
so no floating-point value or rounding is involved.  Thirty-degree phase steps
are multiplication by a formal twelfth root of unity in
``Z[zeta] / (zeta**4 - zeta**2 + 1)``.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
from typing import Sequence

DOMAIN = b"SCBE/INTEGER-PHASE-SHARDS/v1"
SOURCE_COUNT = 4
SOURCE_BYTES = 32
KEY_BYTES = 32
SCALE_NUMERATOR = 11
SCALE_DENOMINATOR = 4
PHASE_ORDER = 12


@dataclass(frozen=True)
class CarryEncoding:
    """Integer stream plus the remainder required for exact reversal."""

    values: tuple[int, ...]
    terminal_remainder: int


@dataclass(frozen=True)
class CeremonyReceipt:
    """Public commitments for a conditioning ceremony; contains no raw key.

    Hash commitments can confirm guesses about weak inputs.  Publish this
    receipt only when every source meets the ceremony's min-entropy contract.
    """

    schema: str
    source_ids: tuple[str, ...]
    source_commitments: tuple[str, ...]
    context_sha3_256: str
    ceremony_nonce: str
    transform_commitment: str
    scale_numerator: int
    scale_denominator: int
    phase_step: int
    phase_order: int


@dataclass(frozen=True)
class NodeKey:
    """Secret tree-node key with public-safe routing metadata."""

    key: bytes
    path: tuple[int, ...]
    epoch: int
    phase_step: int
    z_commitment: str
    fresh_entropy_mixed: bool


@dataclass(frozen=True)
class PrimedAnchorWitness:
    """Keyed witness measured from a caller-selected integer origin.

    ``anchor`` is "primed" by the caller; it need not be a prime number.
    Signed corrections act like declared range, wind, or calibration terms.
    """

    schema: str
    anchor: int
    corrections: tuple[int, ...]
    scaled_residual: CarryEncoding
    residual_sign: int
    context_sha3_256: str
    tag: str


def carry_scale(
    values: Sequence[int],
    *,
    initial_remainder: int = 0,
    numerator: int = SCALE_NUMERATOR,
    denominator: int = SCALE_DENOMINATOR,
) -> CarryEncoding:
    """Apply an exact rational scale while carrying every remainder forward.

    For each input integer ``x_i``::

        n_i = numerator * x_i + c_i
        y_i, c_(i+1) = divmod(n_i, denominator)

    Keeping ``c_final`` makes the transform exactly reversible.
    """

    _validate_ratio(numerator, denominator)
    if not _plain_int(initial_remainder) or not 0 <= initial_remainder < denominator:
        raise ValueError("initial remainder is outside the carry range")

    carry = initial_remainder
    encoded: list[int] = []
    for value in values:
        if not _plain_int(value) or value < 0:
            raise ValueError("carry inputs must be nonnegative integers")
        encoded_value, carry = divmod(numerator * value + carry, denominator)
        encoded.append(encoded_value)
    return CarryEncoding(tuple(encoded), carry)


def carry_unscale(
    encoded: CarryEncoding,
    *,
    numerator: int = SCALE_NUMERATOR,
    denominator: int = SCALE_DENOMINATOR,
    expected_initial_remainder: int | None = 0,
) -> tuple[tuple[int, ...], int]:
    """Reverse :func:`carry_scale` from the retained terminal remainder."""

    _validate_ratio(numerator, denominator)
    if not _plain_int(encoded.terminal_remainder) or not 0 <= encoded.terminal_remainder < denominator:
        raise ValueError("terminal remainder is outside the carry range")

    carry = encoded.terminal_remainder
    decoded: list[int] = []
    for value in reversed(encoded.values):
        if not _plain_int(value) or value < 0:
            raise ValueError("encoded carry values must be nonnegative integers")
        combined = denominator * value + carry
        prior_remainder = combined % numerator
        if prior_remainder >= denominator:
            raise ValueError("stream is not a valid carried-rational encoding")
        decoded.append((combined - prior_remainder) // numerator)
        carry = prior_remainder

    decoded.reverse()
    if expected_initial_remainder is not None and carry != expected_initial_remainder:
        raise ValueError("initial remainder does not match the expected stream origin")
    return tuple(decoded), carry


def rotate_phase30(coefficients: Sequence[int], steps: int = 1) -> tuple[int, int, int, int]:
    """Rotate exact cyclotomic coefficients by ``steps * 30`` degrees.

    A value ``a0 + a1*zeta + a2*zeta**2 + a3*zeta**3`` is represented by four
    integers.  Since ``zeta**4 = zeta**2 - 1``, multiplication by ``zeta`` is::

        (a0, a1, a2, a3) -> (-a3, a0, a1 + a3, a2)

    The twelfth application is exactly the identity, with no trigonometry.
    """

    if len(coefficients) != 4 or any(not _plain_int(value) for value in coefficients):
        raise ValueError("phase state must contain exactly four integers")
    if not _plain_int(steps):
        raise ValueError("phase steps must be an integer")

    state = tuple(coefficients)
    for _ in range(steps % PHASE_ORDER):
        a0, a1, a2, a3 = state
        state = (-a3, a0, a1 + a3, a2)
    return state


def create_primed_anchor_witness(
    integrity_key: bytes,
    *,
    anchor: int,
    observed_value: int,
    corrections: Sequence[int],
    context: bytes,
) -> PrimedAnchorWitness:
    """Authenticate an exact integer observation relative to a selected anchor.

    The residual is ``observed - (anchor + sum(corrections))``.  Its magnitude
    is stretched through the reversible 11/4 carry transform; its direction is
    retained separately.  HMAC supplies adversarial integrity.  The arithmetic
    transform itself is only a coordinate representation.
    """

    integrity_key = _require_bytes("integrity key", integrity_key, exact=KEY_BYTES)
    context = _require_bytes("context", context, minimum=1)
    if not _plain_int(anchor) or not _plain_int(observed_value):
        raise ValueError("anchor and observed value must be integers")
    correction_tuple = tuple(corrections)
    if any(not _plain_int(value) for value in correction_tuple):
        raise ValueError("corrections must contain only integers")

    residual = observed_value - (anchor + sum(correction_tuple))
    residual_sign = (residual > 0) - (residual < 0)
    scaled_residual = carry_scale((abs(residual),))
    context_hash = hashlib.sha3_256(context).digest()
    message = _primed_anchor_message(
        anchor=anchor,
        corrections=correction_tuple,
        scaled_residual=scaled_residual,
        residual_sign=residual_sign,
        context_hash=context_hash,
    )
    tag = hmac.new(integrity_key, DOMAIN + b"/primed-anchor/" + message, hashlib.sha256).hexdigest()
    return PrimedAnchorWitness(
        schema="scbe.primed-anchor-witness.v1",
        anchor=anchor,
        corrections=correction_tuple,
        scaled_residual=scaled_residual,
        residual_sign=residual_sign,
        context_sha3_256=context_hash.hex(),
        tag=tag,
    )


def verify_primed_anchor_witness(
    integrity_key: bytes,
    witness: PrimedAnchorWitness,
    *,
    context: bytes,
    expected_value: int | None = None,
) -> int:
    """Verify a primed-anchor witness and return its reconstructed integer."""

    integrity_key = _require_bytes("integrity key", integrity_key, exact=KEY_BYTES)
    context = _require_bytes("context", context, minimum=1)
    if not isinstance(witness, PrimedAnchorWitness):
        raise TypeError("witness must be a PrimedAnchorWitness")
    if witness.schema != "scbe.primed-anchor-witness.v1":
        raise ValueError("unsupported primed-anchor witness schema")
    if not _plain_int(witness.anchor) or any(not _plain_int(value) for value in witness.corrections):
        raise ValueError("witness coordinates must be integers")
    if not _plain_int(witness.residual_sign) or witness.residual_sign not in (-1, 0, 1):
        raise ValueError("invalid residual direction")
    if not isinstance(witness.scaled_residual, CarryEncoding):
        raise TypeError("scaled residual must be a CarryEncoding")
    if len(witness.scaled_residual.values) != 1:
        raise ValueError("primed-anchor residual must contain one carried value")
    scaled_value = witness.scaled_residual.values[0]
    terminal_remainder = witness.scaled_residual.terminal_remainder
    if not _plain_int(scaled_value) or scaled_value < 0:
        raise ValueError("primed-anchor carried value must be a nonnegative integer")
    if not _plain_int(terminal_remainder) or not 0 <= terminal_remainder < SCALE_DENOMINATOR:
        raise ValueError("primed-anchor terminal remainder is invalid")
    if not isinstance(witness.tag, str) or len(witness.tag) != 64:
        raise ValueError("primed-anchor authentication tag is malformed")
    try:
        bytes.fromhex(witness.tag)
    except ValueError as error:
        raise ValueError("primed-anchor authentication tag is malformed") from error

    context_hash = hashlib.sha3_256(context).digest()
    if witness.context_sha3_256 != context_hash.hex():
        raise ValueError("primed-anchor context changed")
    message = _primed_anchor_message(
        anchor=witness.anchor,
        corrections=witness.corrections,
        scaled_residual=witness.scaled_residual,
        residual_sign=witness.residual_sign,
        context_hash=context_hash,
    )
    expected_tag = hmac.new(integrity_key, DOMAIN + b"/primed-anchor/" + message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(witness.tag, expected_tag):
        raise ValueError("primed-anchor authentication failed")

    magnitudes, initial_remainder = carry_unscale(witness.scaled_residual)
    if initial_remainder != 0:
        raise ValueError("primed-anchor residual has an invalid carry origin")
    magnitude = magnitudes[0]
    if (magnitude == 0) != (witness.residual_sign == 0):
        raise ValueError("residual direction and magnitude disagree")
    reconstructed = witness.anchor + sum(witness.corrections) + witness.residual_sign * magnitude
    if expected_value is not None:
        if not _plain_int(expected_value):
            raise ValueError("expected value must be an integer")
        if reconstructed != expected_value:
            raise ValueError("primed-anchor value does not match the required target")
    return reconstructed


def condition_four_sources(
    samples: Sequence[bytes],
    *,
    source_ids: Sequence[str],
    context: bytes,
    ceremony_nonce: bytes,
    phase_step: int = 1,
) -> tuple[bytes, CeremonyReceipt]:
    """Condition four fixed-width source samples into one 256-bit root key.

    The complete raw samples are included in HKDF input before any derived key
    is returned.  The reversible integer transform is included as additional
    domain-bound material and cannot reduce the raw-source contribution.

    Callers must assess source independence and min-entropy.  Four API calls
    backed by one operating-system generator are one source, not four.
    Fixed-width passwords, counters, decimal seeds, and other guessable values
    are not entropy samples and make the public commitments a guessing oracle.
    """

    normalized = _validate_sources(samples, source_ids)
    context = _require_bytes("context", context, minimum=1)
    ceremony_nonce = _require_bytes("ceremony nonce", ceremony_nonce, minimum=16)
    if not _plain_int(phase_step):
        raise ValueError("phase step must be an integer")
    phase_step %= PHASE_ORDER

    context_hash = hashlib.sha3_256(context).digest()
    source_frames = b"".join(
        _frame(source_id.encode("utf-8")) + _frame(sample)
        for source_id, sample in zip(source_ids, normalized, strict=True)
    )
    source_commitments = tuple(
        hashlib.sha3_256(
            DOMAIN
            + b"/source-commit/"
            + ceremony_nonce
            + index.to_bytes(2, "big")
            + _frame(source_id.encode("utf-8"))
            + sample
        ).hexdigest()
        for index, (source_id, sample) in enumerate(zip(source_ids, normalized, strict=True))
    )

    integers = tuple(int.from_bytes(sample, "big") for sample in normalized)
    carried = carry_scale(integers)
    rotated = rotate_phase30(carried.values, phase_step)

    # The Z coordinate is pseudorandomly derived from all raw sources.  It is
    # structure, not an additional claim of independent entropy.
    z_bytes = hashlib.shake_256(DOMAIN + b"/z-coordinate/" + ceremony_nonce + context_hash + source_frames).digest(
        KEY_BYTES
    )
    transform = (
        b"".join(_encode_signed_integer(value) for value in rotated)
        + carried.terminal_remainder.to_bytes(1, "big")
        + _frame(z_bytes)
        + phase_step.to_bytes(1, "big")
    )

    salt = hashlib.sha3_256(DOMAIN + b"/extract-salt/" + ceremony_nonce + context_hash).digest()
    pseudorandom_key = _hkdf_extract(salt, _frame(source_frames) + _frame(transform))
    root_key = _hkdf_expand(
        pseudorandom_key,
        DOMAIN + b"/root/" + context_hash + ceremony_nonce,
        KEY_BYTES,
    )
    receipt = CeremonyReceipt(
        schema="scbe.integer-phase-shards.ceremony.v1",
        source_ids=tuple(source_ids),
        source_commitments=source_commitments,
        context_sha3_256=context_hash.hex(),
        ceremony_nonce=ceremony_nonce.hex(),
        transform_commitment=hashlib.sha3_256(transform).hexdigest(),
        scale_numerator=SCALE_NUMERATOR,
        scale_denominator=SCALE_DENOMINATOR,
        phase_step=phase_step,
        phase_order=PHASE_ORDER,
    )
    return root_key, receipt


def derive_node_key(
    parent_key: bytes,
    *,
    path: Sequence[int],
    epoch: int,
    context: bytes,
    fresh_entropy: bytes | None = None,
) -> NodeKey:
    """Derive one binary-tree node and its exact 30-degree phase label.

    Supplying fresh independent entropy creates a ratchet step.  Without it,
    this is deterministic hierarchy derivation and compromise of ``parent_key``
    reveals the child.
    """

    parent_key = _require_bytes("parent key", parent_key, exact=KEY_BYTES)
    context = _require_bytes("context", context, minimum=1)
    if not _plain_int(epoch) or epoch < 0:
        raise ValueError("epoch must be a nonnegative integer")
    path_tuple = tuple(path)
    if not path_tuple or any(not _plain_int(branch) or branch not in (0, 1) for branch in path_tuple):
        raise ValueError("path must contain one or more binary branch integers")
    if fresh_entropy is None:
        fresh = b""
    else:
        fresh = _require_bytes("fresh entropy", fresh_entropy, minimum=KEY_BYTES)

    context_hash = hashlib.sha3_256(context).digest()
    path_bytes = bytes(path_tuple)
    metadata = epoch.to_bytes(8, "big") + _frame(path_bytes) + context_hash + bytes([1 if fresh else 0])
    salt = hashlib.sha3_256(DOMAIN + b"/node-salt/" + metadata).digest()
    pseudorandom_key = _hkdf_extract(salt, parent_key + _frame(fresh))
    phase_step = int.from_bytes(_hkdf_expand(pseudorandom_key, DOMAIN + b"/phase/" + metadata, 2), "big") % PHASE_ORDER
    z_secret = _hkdf_expand(pseudorandom_key, DOMAIN + b"/z/" + metadata, KEY_BYTES)
    node_key = _hkdf_expand(
        pseudorandom_key,
        DOMAIN + b"/node/" + metadata + phase_step.to_bytes(1, "big"),
        KEY_BYTES,
    )
    return NodeKey(
        key=node_key,
        path=path_tuple,
        epoch=epoch,
        phase_step=phase_step,
        z_commitment=hashlib.sha3_256(z_secret).hexdigest(),
        fresh_entropy_mixed=bool(fresh),
    )


def split_two_of_two(root_key: bytes, owner_random: bytes) -> tuple[bytes, bytes]:
    """Split a key into owner and service shares using a one-time XOR mask."""

    root_key = _require_bytes("root key", root_key, exact=KEY_BYTES)
    owner_random = _require_bytes("owner random share", owner_random, exact=KEY_BYTES)
    service_share = bytes(left ^ right for left, right in zip(root_key, owner_random, strict=True))
    return owner_random, service_share


def join_two_of_two(owner_share: bytes, service_share: bytes) -> bytes:
    """Reconstruct a two-of-two split; authenticate authorization separately."""

    owner_share = _require_bytes("owner share", owner_share, exact=KEY_BYTES)
    service_share = _require_bytes("service share", service_share, exact=KEY_BYTES)
    return bytes(left ^ right for left, right in zip(owner_share, service_share, strict=True))


def _hkdf_extract(salt: bytes, input_key_material: bytes) -> bytes:
    return hmac.new(salt, input_key_material, hashlib.sha256).digest()


def _hkdf_expand(pseudorandom_key: bytes, info: bytes, length: int) -> bytes:
    if not _plain_int(length) or not 0 < length <= 255 * hashlib.sha256().digest_size:
        raise ValueError("invalid HKDF output length")
    blocks: list[bytes] = []
    previous = b""
    for counter in range(1, (length + hashlib.sha256().digest_size - 1) // hashlib.sha256().digest_size + 1):
        previous = hmac.new(pseudorandom_key, previous + info + bytes([counter]), hashlib.sha256).digest()
        blocks.append(previous)
    return b"".join(blocks)[:length]


def _validate_ratio(numerator: int, denominator: int) -> None:
    if not _plain_int(numerator) or not _plain_int(denominator):
        raise ValueError("ratio components must be integers")
    if denominator <= 0 or numerator < denominator:
        raise ValueError("ratio must satisfy numerator >= denominator > 0")


def _validate_sources(samples: Sequence[bytes], source_ids: Sequence[str]) -> tuple[bytes, ...]:
    if len(samples) != SOURCE_COUNT or len(source_ids) != SOURCE_COUNT:
        raise ValueError(f"exactly {SOURCE_COUNT} source samples and identifiers are required")
    if len(set(source_ids)) != SOURCE_COUNT or any(not isinstance(item, str) or not item for item in source_ids):
        raise ValueError("source identifiers must be unique nonempty strings")
    return tuple(_require_bytes("source sample", sample, exact=SOURCE_BYTES) for sample in samples)


def _require_bytes(name: str, value: bytes, *, exact: int | None = None, minimum: int | None = None) -> bytes:
    if not isinstance(value, bytes):
        raise TypeError(f"{name} must be bytes")
    if exact is not None and len(value) != exact:
        raise ValueError(f"{name} must be exactly {exact} bytes")
    if minimum is not None and len(value) < minimum:
        raise ValueError(f"{name} must contain at least {minimum} bytes")
    return value


def _frame(value: bytes) -> bytes:
    if len(value) >= 1 << 32:
        raise ValueError("framed value is too long")
    return len(value).to_bytes(4, "big") + value


def _encode_signed_integer(value: int) -> bytes:
    if not _plain_int(value):
        raise TypeError("integer encoding requires a plain integer")
    sign = b"\x00" if value >= 0 else b"\x01"
    magnitude = abs(value)
    encoded = magnitude.to_bytes(max(1, (magnitude.bit_length() + 7) // 8), "big")
    return sign + _frame(encoded)


def _primed_anchor_message(
    *,
    anchor: int,
    corrections: tuple[int, ...],
    scaled_residual: CarryEncoding,
    residual_sign: int,
    context_hash: bytes,
) -> bytes:
    if len(corrections) >= 1 << 32:
        raise ValueError("too many correction coordinates")
    return (
        _encode_signed_integer(anchor)
        + len(corrections).to_bytes(4, "big")
        + b"".join(_encode_signed_integer(value) for value in corrections)
        + residual_sign.to_bytes(1, "big", signed=True)
        + _encode_signed_integer(scaled_residual.values[0])
        + scaled_residual.terminal_remainder.to_bytes(1, "big")
        + SCALE_NUMERATOR.to_bytes(2, "big")
        + SCALE_DENOMINATOR.to_bytes(2, "big")
        + context_hash
    )


def _plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
