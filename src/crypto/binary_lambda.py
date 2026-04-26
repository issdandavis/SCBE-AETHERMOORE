"""Binary Lambda Calculus time-placement helpers.

This module implements the small, deterministic part we need for SCBE:
Tromp-style Binary Lambda Calculus (BLC) syntax over De Bruijn indices.

It is not a full lambda evaluator. It is a transport/analysis lane that
answers: "what role does this bit span play in the computation over time?"

Encoding used:
- lambda abstraction: 00 <body>
- application:        01 <function> <argument>
- variable index n:   1 repeated n times, then 0  (n >= 1)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


TermKind = Literal["var", "lam", "app"]
PlacementRole = Literal["binder", "branch", "reference"]


@dataclass(frozen=True)
class BLCTerm:
    """Lambda term in De Bruijn form."""

    kind: TermKind
    index: int | None = None
    body: "BLCTerm | None" = None
    fn: "BLCTerm | None" = None
    arg: "BLCTerm | None" = None

    @staticmethod
    def var(index: int) -> "BLCTerm":
        if index < 1:
            raise ValueError("BLC variable indices are 1-based De Bruijn indices")
        return BLCTerm(kind="var", index=index)

    @staticmethod
    def lam(body: "BLCTerm") -> "BLCTerm":
        return BLCTerm(kind="lam", body=body)

    @staticmethod
    def app(fn: "BLCTerm", arg: "BLCTerm") -> "BLCTerm":
        return BLCTerm(kind="app", fn=fn, arg=arg)

    def to_source(self) -> str:
        """Human-readable De Bruijn source form."""
        if self.kind == "var":
            return str(self.index)
        if self.kind == "lam":
            return f"(lambda {self.body.to_source()})"
        if self.kind == "app":
            return f"({self.fn.to_source()} {self.arg.to_source()})"
        raise ValueError(f"Unsupported term kind: {self.kind}")


@dataclass(frozen=True)
class BLCPlacement:
    """One structural span in a BLC bitstring."""

    start: int
    end: int
    bits: str
    role: PlacementRole
    depth: int
    meaning: str


def encode_blc(term: BLCTerm) -> str:
    """Encode a De Bruijn lambda term as BLC bits."""
    if term.kind == "var":
        assert term.index is not None
        return "1" * term.index + "0"
    if term.kind == "lam":
        assert term.body is not None
        return "00" + encode_blc(term.body)
    if term.kind == "app":
        assert term.fn is not None and term.arg is not None
        return "01" + encode_blc(term.fn) + encode_blc(term.arg)
    raise ValueError(f"Unsupported term kind: {term.kind}")


def decode_blc(bits: str) -> BLCTerm:
    """Decode a complete BLC bitstring into a term."""
    term, pos = _decode_at(_clean_bits(bits), 0)
    if pos != len(_clean_bits(bits)):
        raise ValueError(f"Trailing bits after BLC term at offset {pos}")
    return term


def placements(bits: str) -> list[BLCPlacement]:
    """Return time-placement spans for a complete BLC bitstring."""
    clean = _clean_bits(bits)
    out: list[BLCPlacement] = []
    _, pos = _decode_at(clean, 0, depth=0, out=out)
    if pos != len(clean):
        raise ValueError(f"Trailing bits after BLC term at offset {pos}")
    return out


def blc_to_surfaces(term: BLCTerm) -> dict[str, object]:
    """Project one term into BLC, binary, hex, and placement metadata."""
    bits = encode_blc(term)
    padded = bits + ("0" * ((8 - len(bits) % 8) % 8))
    raw = int(padded or "0", 2).to_bytes(max(1, len(padded) // 8), "big")
    return {
        "de_bruijn": term.to_source(),
        "blc_bits": bits,
        "bit_length": len(bits),
        "byte_padded_bits": padded,
        "hex": raw.hex(".").upper(),
        "binary": " ".join(padded[i : i + 8] for i in range(0, len(padded), 8)),
        "placements": [p.__dict__ for p in placements(bits)],
        "round_trip": decode_blc(bits).to_source() == term.to_source(),
    }


def _clean_bits(bits: str) -> str:
    clean = "".join(ch for ch in bits if ch in "01")
    if not clean:
        raise ValueError("BLC bitstring is empty")
    return clean


def _decode_at(
    bits: str,
    pos: int,
    *,
    depth: int = 0,
    out: list[BLCPlacement] | None = None,
) -> tuple[BLCTerm, int]:
    if pos >= len(bits):
        raise ValueError("Unexpected end of BLC bitstring")

    if bits.startswith("00", pos):
        start = pos
        if out is not None:
            out.append(BLCPlacement(start, start + 2, "00", "binder", depth, "lambda abstraction opens a new time scope"))
        body, end = _decode_at(bits, pos + 2, depth=depth + 1, out=out)
        return BLCTerm.lam(body), end

    if bits.startswith("01", pos):
        start = pos
        if out is not None:
            out.append(BLCPlacement(start, start + 2, "01", "branch", depth, "application schedules function then argument"))
        fn, after_fn = _decode_at(bits, pos + 2, depth=depth, out=out)
        arg, end = _decode_at(bits, after_fn, depth=depth, out=out)
        return BLCTerm.app(fn, arg), end

    if bits[pos] == "1":
        start = pos
        while pos < len(bits) and bits[pos] == "1":
            pos += 1
        if pos >= len(bits) or bits[pos] != "0":
            raise ValueError("Unterminated BLC variable reference")
        index = pos - start
        end = pos + 1
        if out is not None:
            out.append(
                BLCPlacement(
                    start,
                    end,
                    bits[start:end],
                    "reference",
                    depth,
                    f"De Bruijn variable reference to binder {index} level(s) out",
                )
            )
        return BLCTerm.var(index), end

    raise ValueError(f"Invalid BLC prefix at offset {pos}")

