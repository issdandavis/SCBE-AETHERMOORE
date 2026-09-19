"""Dual-trit polarity field with a SHAKE256 security boundary.

The balanced-ternary field is a canonical, reversible representation.  It does
not claim independent collision resistance or extra entropy.  Security of the
commitment is inherited from SHAKE256 over a domain-separated transcript.

For every byte ``b`` the centered coordinate is ``2*b - 255``.  This gives 256
exact cells arranged as 128 shells with a negative and positive pole around an
explicit neutral cell.  Byte complementation is sign inversion:

    centered(255 - b) == -centered(b)

Six balanced trits are sufficient because their representable range is
[-364, 364].  The second rail is the exact trit-wise inverse of the first.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from functools import lru_cache
from typing import Final, Iterable, Sequence

from src.symphonic_cipher.scbe_aethermoore.trinary import BalancedTernary, Trit

SCHEMA: Final[str] = "scbe.dual-trit-polarity-commitment.v1"
DOMAIN: Final[bytes] = b"SCBE-DUAL-TRIT-POLARITY-COMMITMENT-v1"
FIELD_MAGIC: Final[bytes] = b"DTPF\x01"
TRIT_WIDTH: Final[int] = 6
DEFAULT_OUTPUT_BYTES: Final[int] = 64
MIN_OUTPUT_BYTES: Final[int] = 32
MAX_OUTPUT_BYTES: Final[int] = 64

_TRIT_TO_SYMBOL: Final[dict[int, int]] = {-1: 0, 0: 1, 1: 2}
_SYMBOL_TO_TRIT: Final[dict[int, Trit]] = {
    0: Trit.MINUS,
    1: Trit.ZERO,
    2: Trit.PLUS,
}
_ZERO_CELL: Final[bytes] = bytes((1, 1))


@dataclass(frozen=True)
class PolarityCell:
    """One byte's exact location in the centered dual-polarity field."""

    byte: int
    centered: int
    shell_index: int
    polarity: int
    positive_rail: tuple[int, ...]
    negative_rail: tuple[int, ...]

    @property
    def shell(self) -> int:
        """One-based radial shell, retained as the public field vocabulary."""

        return self.shell_index

    def __post_init__(self) -> None:
        if not 0 <= self.byte <= 255:
            raise ValueError("byte must be in 0..255")
        if self.centered != 2 * self.byte - 255:
            raise ValueError("centered coordinate does not match byte")
        if self.centered == 0 or self.centered % 2 == 0:
            raise ValueError("byte cells must occupy nonzero odd coordinates")
        if self.shell_index != (abs(self.centered) + 1) // 2:
            raise ValueError("shell does not match centered coordinate")
        if self.polarity != (-1 if self.centered < 0 else 1):
            raise ValueError("polarity does not match centered coordinate")
        if len(self.positive_rail) != TRIT_WIDTH:
            raise ValueError("positive rail has the wrong width")
        if self.negative_rail != tuple(-value for value in self.positive_rail):
            raise ValueError("negative rail must be the exact inverse")
        if any(value not in (-1, 0, 1) for value in self.positive_rail):
            raise ValueError("rails may contain only balanced trits")


@dataclass(frozen=True)
class DualTritCommitment:
    """Root and six directional receipts for one canonical polarity field."""

    root: bytes
    center: bytes
    directions: tuple[bytes, ...]
    payload_length: int
    output_bytes: int = DEFAULT_OUTPUT_BYTES
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("unsupported commitment schema")
        _validate_output_bytes(self.output_bytes)
        if len(self.root) != self.output_bytes or len(self.center) != self.output_bytes:
            raise ValueError("root and center digest lengths must match output_bytes")
        if len(self.directions) != TRIT_WIDTH:
            raise ValueError("one directional digest is required per trit axis")
        if any(len(value) != self.output_bytes for value in self.directions):
            raise ValueError("direction digest length mismatch")
        if self.payload_length < 0:
            raise ValueError("payload length cannot be negative")

    def verify(self, payload: bytes, *, context: bytes = b"") -> bool:
        candidate = commit_dual_trit_field(
            payload,
            context=context,
            output_bytes=self.output_bytes,
        )
        return hmac.compare_digest(self.root, candidate.root)

    def to_hex(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "payload_length": self.payload_length,
            "output_bytes": self.output_bytes,
            "root": self.root.hex(),
            "center": self.center.hex(),
            "directions": [value.hex() for value in self.directions],
        }


def _validate_output_bytes(output_bytes: int) -> None:
    if not MIN_OUTPUT_BYTES <= output_bytes <= MAX_OUTPUT_BYTES:
        raise ValueError(
            f"output_bytes must be in {MIN_OUTPUT_BYTES}..{MAX_OUTPUT_BYTES}"
        )


def _length_prefix(value: bytes) -> bytes:
    return len(value).to_bytes(8, "big") + value


def _transcript(label: bytes, *parts: bytes) -> bytes:
    return b"".join(
        (
            _length_prefix(DOMAIN),
            _length_prefix(label),
            *(_length_prefix(part) for part in parts),
        )
    )


def _shake(label: bytes, *parts: bytes, output_bytes: int) -> bytes:
    _validate_output_bytes(output_bytes)
    return hashlib.shake_256(_transcript(label, *parts)).digest(output_bytes)


def _fixed_width_trits(value: int) -> tuple[int, ...]:
    trits = tuple(trit.value for trit in BalancedTernary.from_int(value).trits_msb)
    if len(trits) > TRIT_WIDTH:
        raise ValueError("value exceeds the six-trit field")
    return (0,) * (TRIT_WIDTH - len(trits)) + trits


@lru_cache(maxsize=256)
def polarity_cell(byte: int) -> PolarityCell:
    """Map a byte bijectively to one shell and one of two polarities."""

    if not isinstance(byte, int) or isinstance(byte, bool) or not 0 <= byte <= 255:
        raise ValueError("byte must be an integer in 0..255")
    centered = 2 * byte - 255
    positive = _fixed_width_trits(centered)
    return PolarityCell(
        byte=byte,
        centered=centered,
        shell_index=(abs(centered) + 1) // 2,
        polarity=-1 if centered < 0 else 1,
        positive_rail=positive,
        negative_rail=tuple(-value for value in positive),
    )


def _rail_symbols(rail: Sequence[int]) -> bytes:
    try:
        return bytes(_TRIT_TO_SYMBOL[value] for value in rail)
    except KeyError as exc:
        raise ValueError("rail contains a non-trit value") from exc


@lru_cache(maxsize=256)
def _encoded_cell(byte: int) -> bytes:
    cell = polarity_cell(byte)
    return _rail_symbols(cell.positive_rail) + _rail_symbols(cell.negative_rail)


def encode_dual_trit_field(payload: bytes) -> bytes:
    """Encode bytes into a canonical, reversible dual-trit field."""

    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")
    encoded = bytearray(FIELD_MAGIC)
    encoded.extend(len(payload).to_bytes(8, "big"))
    encoded.extend(_ZERO_CELL)
    for byte in payload:
        encoded.extend(_encoded_cell(byte))
    return bytes(encoded)


def _decode_rail(symbols: Iterable[int]) -> tuple[int, ...]:
    try:
        return tuple(_SYMBOL_TO_TRIT[symbol].value for symbol in symbols)
    except KeyError as exc:
        raise ValueError("field contains an invalid trit symbol") from exc


def decode_dual_trit_field(field: bytes) -> bytes:
    """Decode a field and reject noncanonical or non-inverse rails."""

    if not isinstance(field, bytes):
        raise TypeError("field must be bytes")
    minimum = len(FIELD_MAGIC) + 8 + len(_ZERO_CELL)
    if len(field) < minimum or not field.startswith(FIELD_MAGIC):
        raise ValueError("invalid dual-trit field header")
    offset = len(FIELD_MAGIC)
    payload_length = int.from_bytes(field[offset : offset + 8], "big")
    offset += 8
    if field[offset : offset + 2] != _ZERO_CELL:
        raise ValueError("neutral center cell is not canonical")
    offset += 2
    expected_length = minimum + payload_length * TRIT_WIDTH * 2
    if len(field) != expected_length:
        raise ValueError("dual-trit field length does not match its header")

    decoded = bytearray()
    for _ in range(payload_length):
        positive = _decode_rail(field[offset : offset + TRIT_WIDTH])
        offset += TRIT_WIDTH
        negative = _decode_rail(field[offset : offset + TRIT_WIDTH])
        offset += TRIT_WIDTH
        if negative != tuple(-value for value in positive):
            raise ValueError("dual rails are not exact inverses")
        centered = BalancedTernary.from_trits(
            tuple(Trit(value) for value in positive),
            msb_first=True,
        ).to_int()
        if centered == 0 or centered % 2 == 0 or not -255 <= centered <= 255:
            raise ValueError("field contains a non-byte centered coordinate")
        byte = (centered + 255) // 2
        if polarity_cell(byte).positive_rail != positive:
            raise ValueError("field uses a noncanonical trit representation")
        decoded.append(byte)
    return bytes(decoded)


def _direction_stream(cells: Sequence[PolarityCell], axis: int) -> bytes:
    if not 0 <= axis < TRIT_WIDTH:
        raise ValueError("axis is outside the six-trit field")
    stream = bytearray()
    for cell in cells:
        stream.append(_TRIT_TO_SYMBOL[cell.positive_rail[axis]])
        stream.append(_TRIT_TO_SYMBOL[cell.negative_rail[axis]])
    return bytes(stream)


def commit_dual_trit_field(
    payload: bytes,
    *,
    context: bytes = b"",
    output_bytes: int = DEFAULT_OUTPUT_BYTES,
) -> DualTritCommitment:
    """Commit to a payload and its six radial trit views with SHAKE256."""

    if not isinstance(payload, bytes) or not isinstance(context, bytes):
        raise TypeError("payload and context must be bytes")
    _validate_output_bytes(output_bytes)
    cells = tuple(polarity_cell(byte) for byte in payload)
    field = encode_dual_trit_field(payload)
    length = len(payload).to_bytes(8, "big")
    center = _shake(b"center", context, field, output_bytes=output_bytes)
    directions = tuple(
        _shake(
            b"direction-" + bytes((axis,)),
            context,
            length,
            _direction_stream(cells, axis),
            output_bytes=output_bytes,
        )
        for axis in range(TRIT_WIDTH)
    )
    root = _shake(
        b"root",
        context,
        length,
        center,
        b"".join(directions),
        output_bytes=output_bytes,
    )
    return DualTritCommitment(
        root=root,
        center=center,
        directions=directions,
        payload_length=len(payload),
        output_bytes=output_bytes,
    )


def dual_trit_root(
    payload: bytes,
    *,
    context: bytes = b"",
    output_bytes: int = DEFAULT_OUTPUT_BYTES,
) -> bytes:
    """Commit once to the canonical field without radial evidence receipts.

    This is exactly the ``center`` digest in :func:``commit_dual_trit_field``.
    It is the production-oriented form when callers need only integrity and
    domain separation. The full commitment is an auditable multi-view receipt,
    not a stronger hash.
    """

    if not isinstance(payload, bytes) or not isinstance(context, bytes):
        raise TypeError("payload and context must be bytes")
    return _shake(
        b"center",
        context,
        encode_dual_trit_field(payload),
        output_bytes=output_bytes,
    )


def direct_shake256_commitment(
    payload: bytes,
    *,
    context: bytes = b"",
    output_bytes: int = DEFAULT_OUTPUT_BYTES,
) -> bytes:
    """Standardized primitive control using the same domain framing."""

    if not isinstance(payload, bytes) or not isinstance(context, bytes):
        raise TypeError("payload and context must be bytes")
    return _shake(b"direct-control", context, payload, output_bytes=output_bytes)


__all__ = [
    "DualTritCommitment",
    "PolarityCell",
    "commit_dual_trit_field",
    "decode_dual_trit_field",
    "direct_shake256_commitment",
    "dual_trit_root",
    "encode_dual_trit_field",
    "polarity_cell",
]
