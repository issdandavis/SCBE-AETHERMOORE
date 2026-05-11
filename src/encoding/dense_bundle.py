"""Dense data bundle: one input, many parallel encodings.

Per the bit/float/trit theory note (notes/theory/2026-04-05-training-pair-taxonomy.md):
    "same byte, different intent polarity (+1/0/-1) -> 24x encoding density.
     Trit = intent layer (same code, different purpose)."

A `DenseBundle` packages five lossless views of the same payload:
    - binary       bit string ('010101...')
    - hex          base-16 string
    - base64       transport-safe ASCII
    - ternary      balanced ternary (Issac's symphonic_cipher.trinary)
    - intent       per-byte polarity overlay (+1 / 0 / -1)

The first four are lossless byte-level encodings of the same payload.
The fifth is an intent-layer overlay (one trit per byte) — the same code,
different purpose. Bundles round-trip: decode any of the four byte
views and you get the same bytes back.

For routing: `route_lane_for_bundle` picks a swarm lane hint from
the encoding form. Hex bundles -> byte/binary analysis lane.
Ternary bundles -> governance / intent lane. And so on.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Sequence

from src.symphonic_cipher.scbe_aethermoore.trinary import (
    BalancedTernary,
    Trit,
)

# Canonical lane keys the swarm router already understands. The bus
# can dispatch on these without needing a new lane vocabulary.
LANE_BINARY_ANALYSIS = "binary_analysis"
LANE_GOVERNANCE_INTENT = "governance_intent"
LANE_TRANSPORT_OPAQUE = "transport_opaque"
LANE_TEXT_DEFAULT = "text_default"


def _bytes_to_balanced_ternary(payload: bytes) -> BalancedTernary:
    """Encode raw bytes as one big-int balanced ternary number.

    Reversible via :func:`_balanced_ternary_to_bytes`. The byte length
    is recovered from the bundle's `byte_length` field, not from the
    BT representation itself (BT has no inherent length).
    """
    if not payload:
        return BalancedTernary([])
    n = int.from_bytes(payload, "big", signed=False)
    return BalancedTernary.from_int(n)


def _balanced_ternary_to_bytes(bt: BalancedTernary, byte_length: int) -> bytes:
    if byte_length == 0:
        return b""
    n = bt.to_int()
    if n < 0:
        raise ValueError("dense bundle balanced ternary decoded to a negative int")
    return n.to_bytes(byte_length, "big", signed=False)


def _bytes_to_intent(payload: bytes) -> list[Trit]:
    """Map each byte to an intent polarity: +1 / 0 / -1.

    Mapping is deterministic but coarse on purpose:
        byte == 0           -> Trit.ZERO   (null)
        byte & 0x80 == 0    -> Trit.PLUS    (low ASCII / structural)
        byte & 0x80 != 0    -> Trit.MINUS    (high-bit / payload)

    The intent overlay is NOT used to recover the bytes. It's a
    parallel signal — same code, different purpose.
    """
    out: list[Trit] = []
    for b in payload:
        if b == 0:
            out.append(Trit.ZERO)
        elif b & 0x80:
            out.append(Trit.MINUS)
        else:
            out.append(Trit.PLUS)
    return out


@dataclass(frozen=True)
class DenseBundle:
    """One payload, four lossless encodings, one intent overlay."""

    byte_length: int
    binary: str
    hex: str
    base64: str
    ternary: str
    intent: tuple[int, ...] = field(default_factory=tuple)

    @classmethod
    def from_bytes(cls, payload: bytes) -> "DenseBundle":
        bt = _bytes_to_balanced_ternary(payload)
        return cls(
            byte_length=len(payload),
            binary="".join(f"{b:08b}" for b in payload),
            hex=payload.hex(),
            base64=base64.b64encode(payload).decode("ascii"),
            ternary=str(bt),
            intent=tuple(int(t) for t in _bytes_to_intent(payload)),
        )

    @classmethod
    def from_text(cls, text: str, encoding: str = "utf-8") -> "DenseBundle":
        return cls.from_bytes(text.encode(encoding))

    def to_bytes(self, view: str = "hex") -> bytes:
        """Decode any of the four byte views back to bytes.

        `view` must be one of: "hex", "binary", "base64", "ternary".
        Each view is independently lossless and produces the same
        bytes.
        """
        if view == "hex":
            return bytes.fromhex(self.hex)
        if view == "binary":
            if len(self.binary) % 8 != 0:
                raise ValueError("binary view length is not a multiple of 8")
            return bytes(int(self.binary[i : i + 8], 2) for i in range(0, len(self.binary), 8))
        if view == "base64":
            return base64.b64decode(self.base64.encode("ascii"))
        if view == "ternary":
            from src.symphonic_cipher.scbe_aethermoore.trinary import parse_bt

            bt = parse_bt(self.ternary)
            return _balanced_ternary_to_bytes(bt, self.byte_length)
        raise ValueError(f"unknown view: {view!r}")

    def to_text(self, view: str = "hex", encoding: str = "utf-8") -> str:
        return self.to_bytes(view).decode(encoding)

    def density_ratio(self) -> float:
        """Total characters across the four byte views, divided by raw byte length.

        Pure observability metric. The intent overlay is excluded
        because it's not a byte view.
        """
        if self.byte_length == 0:
            return 0.0
        total_chars = len(self.binary) + len(self.hex) + len(self.base64) + len(self.ternary)
        return total_chars / self.byte_length

    def to_dict(self) -> dict:
        return {
            "byte_length": self.byte_length,
            "binary": self.binary,
            "hex": self.hex,
            "base64": self.base64,
            "ternary": self.ternary,
            "intent": list(self.intent),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DenseBundle":
        return cls(
            byte_length=int(d["byte_length"]),
            binary=str(d["binary"]),
            hex=str(d["hex"]),
            base64=str(d["base64"]),
            ternary=str(d["ternary"]),
            intent=tuple(int(x) for x in d.get("intent", ())),
        )


def route_lane_for_bundle(view_hint: str, bundle: DenseBundle | None = None) -> str:
    """Pick a swarm-bus lane key from the encoding form.

    The bus dispatches on the lane key returned here. `bundle` is
    accepted but currently unused — kept in the signature so future
    routing rules can inspect bundle properties (intent profile,
    density ratio) without breaking callers.

    Mapping rationale:
        - "hex" / "binary" -> byte-level analysis (low-level decoders,
          binary parsers, format inspectors)
        - "ternary" -> governance / intent (the BT view IS Issac's
          intent-layer encoding; route to the agent that reads intent)
        - "base64" -> transport / opaque payload (deserializer, blob
          handler, content-type sniffer)
        - anything else -> default text lane
    """
    if view_hint in ("hex", "binary"):
        return LANE_BINARY_ANALYSIS
    if view_hint == "ternary":
        return LANE_GOVERNANCE_INTENT
    if view_hint == "base64":
        return LANE_TRANSPORT_OPAQUE
    return LANE_TEXT_DEFAULT


def bundle_intent_profile(bundle: DenseBundle) -> dict[str, float]:
    """Summarize the intent overlay as a 3-bucket histogram.

    Useful for the swarm bus to decide which intent lane gets a
    bundle: heavy NEG (high-bit) -> binary/payload lane, heavy POS
    (low-ASCII) -> text lane, ZERO-rich -> null/governance lane.
    """
    if not bundle.intent:
        return {"neg": 0.0, "zero": 0.0, "pos": 0.0}
    n = len(bundle.intent)
    neg = sum(1 for x in bundle.intent if x < 0)
    zero = sum(1 for x in bundle.intent if x == 0)
    pos = sum(1 for x in bundle.intent if x > 0)
    return {"neg": neg / n, "zero": zero / n, "pos": pos / n}


def encode_for_route(payload: bytes | str, view: str = "hex") -> tuple[DenseBundle, str]:
    """One-shot helper for the swarm bus.

    Returns `(bundle, lane_key)` so the bus can both ship the bundle
    AND know which lane it's heading to.
    """
    if isinstance(payload, str):
        bundle = DenseBundle.from_text(payload)
    else:
        bundle = DenseBundle.from_bytes(payload)
    return bundle, route_lane_for_bundle(view, bundle)


def equivalent_views(payload: bytes | Sequence[int]) -> tuple[bytes, bytes, bytes, bytes]:
    """Return all four lossless byte views of the same payload.

    Convenience for tests and for SFT augmentation pipelines that
    want every parallel form of the same input.
    """
    if not isinstance(payload, (bytes, bytearray)):
        payload = bytes(payload)
    bundle = DenseBundle.from_bytes(bytes(payload))
    return (
        bundle.to_bytes("hex"),
        bundle.to_bytes("binary"),
        bundle.to_bytes("base64"),
        bundle.to_bytes("ternary"),
    )
