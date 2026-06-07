"""Prime-coded IR for CA opcode programs.

This is the coding-family bridge:

    equivalent command -> CA opcode row -> prime id -> target language lens

The prime code is deliberately tied to the existing 64-op CA table, not to
surface token ids. Python, C, Haskell, Rust, TypeScript, Julia, Go, and Zig
language lenses can therefore share the same command identity when they resolve
to the same CA row.

Order matters, so programs are represented as an ordered prime tape, not a
single product. A product can be useful as a compact fingerprint, but it is not
the executable representation because multiplication is commutative.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Sequence

from .ca_opcode_table import OP_TABLE


@dataclass(frozen=True)
class PrimeOpRow:
    """One reversible CA opcode <-> prime row."""

    op_id: int
    op_hex: str
    op_name: str
    prime: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "op_id": self.op_id,
            "op_hex": self.op_hex,
            "op_name": self.op_name,
            "prime": self.prime,
        }


def first_primes(count: int) -> list[int]:
    """Return the first `count` prime numbers."""
    if count < 0:
        raise ValueError("count must be non-negative")
    primes: list[int] = []
    candidate = 2
    while len(primes) < count:
        if all(candidate % p for p in primes if p * p <= candidate):
            primes.append(candidate)
        candidate += 1 if candidate == 2 else 2
    return primes


@lru_cache(maxsize=1)
def prime_table() -> tuple[PrimeOpRow, ...]:
    """Return the canonical 64-row opcode -> prime table."""
    op_ids = sorted(OP_TABLE)
    primes = first_primes(len(op_ids))
    return tuple(
        PrimeOpRow(
            op_id=op_id,
            op_hex=f"0x{op_id:02X}",
            op_name=OP_TABLE[op_id].name,
            prime=primes[i],
        )
        for i, op_id in enumerate(op_ids)
    )


def _by_op_id() -> dict[int, PrimeOpRow]:
    return {row.op_id: row for row in prime_table()}


def _by_prime() -> dict[int, PrimeOpRow]:
    return {row.prime: row for row in prime_table()}


def _by_name() -> dict[str, PrimeOpRow]:
    return {row.op_name.lower(): row for row in prime_table()}


def prime_for_opcode(op_id: int) -> int:
    """Map a CA opcode id to its canonical prime."""
    try:
        return _by_op_id()[int(op_id)].prime
    except KeyError as exc:
        raise ValueError(f"unknown CA opcode: {op_id}") from exc


def opcode_for_prime(prime: int) -> int:
    """Map a canonical prime back to its CA opcode id."""
    try:
        return _by_prime()[int(prime)].op_id
    except KeyError as exc:
        raise ValueError(f"unknown CA opcode prime: {prime}") from exc


def prime_for_op_name(name: str) -> int:
    """Map a CA opcode name to its canonical prime."""
    key = name.strip().lower()
    try:
        return _by_name()[key].prime
    except KeyError as exc:
        raise ValueError(f"unknown CA op name: {name!r}") from exc


def op_name_for_prime(prime: int) -> str:
    """Map a canonical prime back to its CA opcode name."""
    return _by_prime()[int(prime)].op_name


def encode_opcodes_to_primes(opcodes: Sequence[int]) -> list[int]:
    """Encode an ordered CA opcode sequence as an ordered prime tape."""
    return [prime_for_opcode(op_id) for op_id in opcodes]


def decode_primes_to_opcodes(primes: Sequence[int]) -> list[int]:
    """Decode an ordered prime tape back into CA opcodes."""
    return [opcode_for_prime(prime) for prime in primes]


def parse_prime_sequence(spec: str) -> list[int]:
    """Parse comma/space-separated prime ids."""
    out: list[int] = []
    for raw in spec.replace(",", " ").split():
        token = raw.strip()
        if token:
            out.append(int(token, 10))
    if not out:
        raise ValueError("prime sequence is empty")
    return out


def prime_plan_from_ops(op_names: Sequence[str]) -> dict[str, Any]:
    """Build a prime-coded plan from CA op names."""
    rows = [_by_name()[name.strip().lower()] for name in op_names]
    return {
        "schema": "scbe_prime_code_ir_v1",
        "encoding": "ordered_prime_tape",
        "order_preserving": True,
        "ops": [row.op_name for row in rows],
        "opcodes": [row.op_id for row in rows],
        "hex_sequence": [row.op_hex for row in rows],
        "prime_sequence": [row.prime for row in rows],
        "prime_tape": " ".join(str(row.prime) for row in rows),
    }


def audit_language_prime_equivalence() -> dict[str, Any]:
    """Verify every multilingual lexicon row resolves to the same prime identity."""
    from src.ca_lexicon import (
        EXTENDED_TONGUE_NAMES,
        LEXICON,
        TONGUE_NAMES,
        TONGUE_PARENT,
    )

    problems: list[str] = []
    rows: list[dict[str, Any]] = []
    by_id = _by_op_id()
    for op_id in sorted(LEXICON):
        entry = LEXICON[op_id]
        if op_id not in by_id:
            problems.append(f"lexicon op 0x{op_id:02X} missing from prime table")
            continue
        prime_row = by_id[op_id]
        if entry.name != prime_row.op_name:
            problems.append(
                f"0x{op_id:02X}: name mismatch {entry.name!r} != {prime_row.op_name!r}"
            )
        missing_lenses = [tongue for tongue in TONGUE_NAMES if tongue not in entry.code]
        if missing_lenses:
            problems.append(
                f"0x{op_id:02X} {entry.name}: missing lenses {missing_lenses}"
            )
        rows.append(
            {
                "op_id": op_id,
                "op_hex": prime_row.op_hex,
                "op_name": entry.name,
                "prime": prime_row.prime,
                "language_lenses": sorted(
                    tongue for tongue in TONGUE_NAMES if tongue in entry.code
                ),
                "extended_lenses": {
                    tongue: {"inherits_from": TONGUE_PARENT[tongue]}
                    for tongue in EXTENDED_TONGUE_NAMES
                },
            }
        )

    return {
        "schema": "scbe_prime_code_ir_equivalence_audit_v1",
        "ok": not problems,
        "row_count": len(rows),
        "problems": problems,
        "sample_rows": rows[:8],
    }
