"""
Balanced Ternary (Trinary) Encoding System

Balanced ternary uses digits {-1, 0, +1} (written T, 0, 1) with base 3.
Every integer has a unique representation with NO sign bit needed.

    value = sum(d_i * 3^i)  where d_i in {-1, 0, +1}

Governance mapping:
    ALLOW      = +1  (positive affirmation)
    QUARANTINE =  0  (neutral / uncertain)
    DENY       = -1  (negative rejection)

This module provides:
    - Integer <-> balanced ternary conversion
    - Trit-level logic (Kleene 3-valued: AND, OR, NOT)
    - Balanced ternary arithmetic (add, negate, multiply)
    - Governance decision packing into trit-words
    - Integration with the existing Decision enum

@module trinary
@layer Layer 13 (Governance), Layer 9 (Spectral)
@version 1.0.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Trit
# ---------------------------------------------------------------------------

class Trit(IntEnum):
    """A single balanced ternary digit."""
    MINUS = -1  # T (negative)
    ZERO = 0
    PLUS = 1

    def __repr__(self) -> str:
        return {-1: "T", 0: "0", 1: "1"}[self.value]

    def __str__(self) -> str:
        return repr(self)


# Kleene 3-valued logic truth tables
# NOT: T->1, 0->0, 1->T
def trit_not(a: Trit) -> Trit:
    """Kleene NOT: negate the trit."""
    return Trit(-a.value)


def trit_and(a: Trit, b: Trit) -> Trit:
    """Kleene AND: min(a, b)."""
    return Trit(min(a.value, b.value))


def trit_or(a: Trit, b: Trit) -> Trit:
    """Kleene OR: max(a, b)."""
    return Trit(max(a.value, b.value))


def trit_consensus(a: Trit, b: Trit) -> Trit:
    """Consensus: agree if same, else uncertain (0)."""
    return a if a == b else Trit.ZERO


# ---------------------------------------------------------------------------
# Governance mapping
# ---------------------------------------------------------------------------

GOVERNANCE_MAP = {
    "ALLOW": Trit.PLUS,
    "QUARANTINE": Trit.ZERO,
    "REVIEW": Trit.ZERO,
    "DENY": Trit.MINUS,
    "SNAP": Trit.MINUS,
}

GOVERNANCE_REVERSE = {
    Trit.PLUS: "ALLOW",
    Trit.ZERO: "QUARANTINE",
    Trit.MINUS: "DENY",
}


def decision_to_trit(decision: str) -> Trit:
    """Map a governance decision string to a trit."""
    return GOVERNANCE_MAP.get(decision.upper(), Trit.ZERO)


def trit_to_decision(t: Trit) -> str:
    """Map a trit back to a governance decision string."""
    return GOVERNANCE_REVERSE[t]


# ---------------------------------------------------------------------------
# BalancedTernary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BalancedTernary:
    """Balanced ternary number: a sequence of trits (LSB first internally).

    External display is MSB-first (most significant trit on the left).
    """
    _trits: Tuple[Trit, ...]  # LSB first

    @staticmethod
    def from_int(n: int) -> BalancedTernary:
        """Convert an integer to balanced ternary."""
        if n == 0:
            return BalancedTernary((Trit.ZERO,))

        trits: List[Trit] = []
        value = n
        while value != 0:
            remainder = value % 3
            value //= 3
            if remainder == 2:
                # 2 in standard ternary = -1 in balanced, carry +1
                trits.append(Trit.MINUS)
                value += 1
            elif remainder == 0:
                trits.append(Trit.ZERO)
            else:  # remainder == 1
                trits.append(Trit.PLUS)

        return BalancedTernary(tuple(trits))

    def to_int(self) -> int:
        """Convert balanced ternary back to integer."""
        result = 0
        for i, t in enumerate(self._trits):
            result += t.value * (3 ** i)
        return result

    @staticmethod
    def from_trits(trits: Sequence[Trit], msb_first: bool = True) -> BalancedTernary:
        """Create from a trit sequence. Default MSB-first (human reading order)."""
        if msb_first:
            return BalancedTernary(tuple(reversed(trits)))
        return BalancedTernary(tuple(trits))

    @property
    def trits_msb(self) -> Tuple[Trit, ...]:
        """Return trits in MSB-first order (human-readable)."""
        return tuple(reversed(self._trits))

    @property
    def trits_lsb(self) -> Tuple[Trit, ...]:
        """Return trits in LSB-first order (computation order)."""
        return self._trits

    @property
    def width(self) -> int:
        """Number of trits."""
        return len(self._trits)

    def __repr__(self) -> str:
        chars = "".join({-1: "T", 0: "0", 1: "1"}[t.value] for t in self.trits_msb)
        return f"BT({chars})"

    def __str__(self) -> str:
        return "".join({-1: "T", 0: "0", 1: "1"}[t.value] for t in self.trits_msb)

    # ── Arithmetic ──

    def negate(self) -> BalancedTernary:
        """Negate: flip every trit."""
        return BalancedTernary(tuple(Trit(-t.value) for t in self._trits))

    def __neg__(self) -> BalancedTernary:
        return self.negate()

    def __add__(self, other: BalancedTernary) -> BalancedTernary:
        return _bt_add(self, other)

    def __sub__(self, other: BalancedTernary) -> BalancedTernary:
        return _bt_add(self, other.negate())

    def __mul__(self, other: BalancedTernary) -> BalancedTernary:
        return _bt_mul(self, other)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BalancedTernary):
            return NotImplemented
        return self.to_int() == other.to_int()

    def __hash__(self) -> int:
        return hash(self.to_int())

    # ── Trit-level operations ──

    def trit_not(self) -> BalancedTernary:
        """Apply Kleene NOT to each trit."""
        return BalancedTernary(tuple(Trit(-t.value) for t in self._trits))

    def trit_and(self, other: BalancedTernary) -> BalancedTernary:
        """Apply Kleene AND trit-by-trit."""
        a, b = _pad_equal(self, other)
        return BalancedTernary(tuple(
            Trit(min(at.value, bt.value)) for at, bt in zip(a._trits, b._trits)
        ))

    def trit_or(self, other: BalancedTernary) -> BalancedTernary:
        """Apply Kleene OR trit-by-trit."""
        a, b = _pad_equal(self, other)
        return BalancedTernary(tuple(
            Trit(max(at.value, bt.value)) for at, bt in zip(a._trits, b._trits)
        ))

    # ── Governance ──

    @staticmethod
    def pack_decisions(decisions: Sequence[str]) -> BalancedTernary:
        """Pack a sequence of governance decisions into a trit-word.

        Each decision maps to one trit: ALLOW=+1, QUARANTINE=0, DENY=-1.
        First decision becomes the MSB.
        """
        trits = [decision_to_trit(d) for d in decisions]
        return BalancedTernary.from_trits(trits, msb_first=True)

    def unpack_decisions(self) -> List[str]:
        """Unpack trit-word back to governance decisions (MSB-first)."""
        return [trit_to_decision(t) for t in self.trits_msb]

    def governance_summary(self) -> dict:
        """Summarize governance trit-word."""
        decisions = self.unpack_decisions()
        allow = sum(1 for d in decisions if d == "ALLOW")
        deny = sum(1 for d in decisions if d == "DENY")
        quarantine = sum(1 for d in decisions if d == "QUARANTINE")
        # Net governance score: simple vote tally (+1 per allow, -1 per deny)
        net = allow - deny
        return {
            "decisions": decisions,
            "allow": allow,
            "deny": deny,
            "quarantine": quarantine,
            "total": len(decisions),
            "net_score": net,
            "consensus": "ALLOW" if net > 0 else ("DENY" if net < 0 else "QUARANTINE"),
        }

    # ── Entropy ──

    def trit_entropy(self) -> float:
        """Shannon entropy of the trit distribution (bits)."""
        counts = [0, 0, 0]  # -1, 0, +1
        for t in self._trits:
            counts[t.value + 1] += 1
        n = len(self._trits)
        entropy = 0.0
        for c in counts:
            if c > 0:
                p = c / n
                entropy -= p * math.log2(p)
        return entropy

    def information_density(self) -> float:
        """Ratio of entropy to max possible (log2(3) per trit)."""
        max_entropy = math.log2(3)
        return self.trit_entropy() / max_entropy if self.width > 0 else 0.0


# ---------------------------------------------------------------------------
# Internal arithmetic helpers
# ---------------------------------------------------------------------------

def _pad_equal(a: BalancedTernary, b: BalancedTernary) -> Tuple[BalancedTernary, BalancedTernary]:
    """Zero-pad both numbers to equal width (LSB-first)."""
    max_len = max(len(a._trits), len(b._trits))
    at = a._trits + (Trit.ZERO,) * (max_len - len(a._trits))
    bt = b._trits + (Trit.ZERO,) * (max_len - len(b._trits))
    return BalancedTernary(at), BalancedTernary(bt)


def _bt_add(a: BalancedTernary, b: BalancedTernary) -> BalancedTernary:
    """Add two balanced ternary numbers with carry propagation."""
    a_padded, b_padded = _pad_equal(a, b)
    result: List[Trit] = []
    carry = 0

    for at, bt in zip(a_padded._trits, b_padded._trits):
        s = at.value + bt.value + carry
        # s ranges from -3 to +3
        if s >= 2:
            result.append(Trit(s - 3))
            carry = 1
        elif s <= -2:
            result.append(Trit(s + 3))
            carry = -1
        else:
            result.append(Trit(s))
            carry = 0

    if carry != 0:
        result.append(Trit(carry))

    # Strip leading zeros (from MSB end = end of list)
    while len(result) > 1 and result[-1] == Trit.ZERO:
        result.pop()

    return BalancedTernary(tuple(result))


def _bt_mul(a: BalancedTernary, b: BalancedTernary) -> BalancedTernary:
    """Multiply two balanced ternary numbers via shift-and-add."""
    result = BalancedTernary.from_int(0)

    for i, bt in enumerate(b._trits):
        if bt.value == 0:
            continue
        # Shift a left by i positions
        shifted_trits = (Trit.ZERO,) * i + a._trits
        shifted = BalancedTernary(shifted_trits)
        if bt.value == -1:
            shifted = shifted.negate()
        result = result + shifted

    return result


# ---------------------------------------------------------------------------
# Utility: parse string representation
# ---------------------------------------------------------------------------

def parse_bt(s: str) -> BalancedTernary:
    """Parse a balanced ternary string like 'T10T1' (MSB-first).

    T = -1, 0 = 0, 1 = +1.
    """
    trit_map = {"T": Trit.MINUS, "t": Trit.MINUS, "0": Trit.ZERO, "1": Trit.PLUS}
    trits = [trit_map[c] for c in s if c in trit_map]
    return BalancedTernary.from_trits(trits, msb_first=True)
