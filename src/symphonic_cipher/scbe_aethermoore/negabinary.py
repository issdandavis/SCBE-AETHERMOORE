"""
Negabinary (Base -2) Encoding System

Negabinary uses digits {0, 1} with base -2.
Every integer has a unique representation with NO sign bit.

    value = sum(d_i * (-2)^i)  where d_i in {0, 1}

Examples:
     0 = 0         (empty)
     1 = 1         (1 * (-2)^0)
    -1 = 11        (1*1 + 1*(-2) = 1 - 2 = -1)
     2 = 110       (0*1 + 1*(-2) + 1*4 = -2 + 4 = 2)
    -2 = 10        (0*1 + 1*(-2) = -2)
     3 = 111       (1 + -2 + 4 = 3)
    -3 = 1101      (1 + 0 + 4 + -8 = -3)

Key properties:
    - No sign bit needed — negatives emerge naturally
    - Polarity alternates per bit position (even=positive, odd=negative)
    - Useful for Sacred Tongue encoding where polarity is inherent

Integration with Sacred Tongues:
    Even-position bits  = positive polarity (KO, CA)
    Odd-position bits   = negative polarity (AV, DR)
    Mixed patterns      = balanced tongues (RU, UM)

@module negabinary
@layer Layer 9 (Spectral), Layer 12 (Entropy)
@version 1.0.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# NegaBinary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NegaBinary:
    """Negabinary (base -2) number.

    Stored as a tuple of bits (0 or 1), LSB first internally.
    Display is MSB-first.
    """
    _bits: Tuple[int, ...]  # LSB first, each 0 or 1

    @staticmethod
    def from_int(n: int) -> NegaBinary:
        """Convert integer to negabinary representation."""
        if n == 0:
            return NegaBinary((0,))

        bits: List[int] = []
        value = n
        while value != 0:
            remainder = value % -2
            value //= -2
            if remainder < 0:
                remainder += 2
                value += 1
            bits.append(remainder)

        return NegaBinary(tuple(bits))

    def to_int(self) -> int:
        """Convert negabinary back to integer."""
        result = 0
        for i, b in enumerate(self._bits):
            if b:
                result += (-2) ** i
        return result

    @staticmethod
    def from_bits(bits: Sequence[int], msb_first: bool = True) -> NegaBinary:
        """Create from a bit sequence."""
        if msb_first:
            return NegaBinary(tuple(reversed(bits)))
        return NegaBinary(tuple(bits))

    @property
    def bits_msb(self) -> Tuple[int, ...]:
        """Bits in MSB-first order (human-readable)."""
        return tuple(reversed(self._bits))

    @property
    def bits_lsb(self) -> Tuple[int, ...]:
        """Bits in LSB-first order."""
        return self._bits

    @property
    def width(self) -> int:
        """Number of bits."""
        return len(self._bits)

    def __repr__(self) -> str:
        return f"NB({''.join(str(b) for b in self.bits_msb)})"

    def __str__(self) -> str:
        return "".join(str(b) for b in self.bits_msb)

    # ── Arithmetic ──

    def negate(self) -> NegaBinary:
        """Negate: return NegaBinary(-self.to_int()).

        In negabinary, negation is non-trivial — we convert through int.
        """
        return NegaBinary.from_int(-self.to_int())

    def __neg__(self) -> NegaBinary:
        return self.negate()

    def __add__(self, other: NegaBinary) -> NegaBinary:
        return _nb_add(self, other)

    def __sub__(self, other: NegaBinary) -> NegaBinary:
        return _nb_add(self, other.negate())

    def __mul__(self, other: NegaBinary) -> NegaBinary:
        return _nb_mul(self, other)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NegaBinary):
            return NotImplemented
        return self.to_int() == other.to_int()

    def __hash__(self) -> int:
        return hash(self.to_int())

    # ── Polarity Analysis ──

    def polarity_profile(self) -> Dict[str, int]:
        """Analyze bit-position polarity.

        Even positions contribute positive weight ((-2)^0=1, (-2)^2=4, ...)
        Odd positions contribute negative weight ((-2)^1=-2, (-2)^3=-8, ...)
        """
        positive_bits = sum(1 for i, b in enumerate(self._bits) if b == 1 and i % 2 == 0)
        negative_bits = sum(1 for i, b in enumerate(self._bits) if b == 1 and i % 2 == 1)
        positive_weight = sum((-2) ** i for i, b in enumerate(self._bits) if b == 1 and i % 2 == 0)
        negative_weight = sum((-2) ** i for i, b in enumerate(self._bits) if b == 1 and i % 2 == 1)
        return {
            "positive_bits": positive_bits,
            "negative_bits": negative_bits,
            "positive_weight": positive_weight,
            "negative_weight": negative_weight,
            "polarity": "positive" if positive_bits > negative_bits
                        else ("negative" if negative_bits > positive_bits else "balanced"),
        }

    def bit_entropy(self) -> float:
        """Shannon entropy of the bit distribution."""
        ones = sum(self._bits)
        zeros = len(self._bits) - ones
        n = len(self._bits)
        if n == 0:
            return 0.0
        entropy = 0.0
        for c in [zeros, ones]:
            if c > 0:
                p = c / n
                entropy -= p * math.log2(p)
        return entropy

    # ── Tongue Polarity ──

    def tongue_polarity(self) -> str:
        """Map the number's polarity to a Sacred Tongue affinity.

        Positive-dominant -> KO (control, assertive)
        Negative-dominant -> AV (voice, receptive)
        Balanced          -> RU (root, grounded)
        """
        profile = self.polarity_profile()
        return {
            "positive": "KO",
            "negative": "AV",
            "balanced": "RU",
        }[profile["polarity"]]

    def tongue_encoding(self) -> List[str]:
        """Encode each bit position as a tongue based on polarity.

        Even positions (positive weight): KO
        Odd positions (negative weight):  AV
        Zero bits:                         UM (silence/universal)
        """
        tongues = []
        for i, b in enumerate(self._bits):
            if b == 0:
                tongues.append("UM")
            elif i % 2 == 0:
                tongues.append("KO")
            else:
                tongues.append("AV")
        return tongues


# ---------------------------------------------------------------------------
# Negabinary Addition
# ---------------------------------------------------------------------------

def _nb_add(a: NegaBinary, b: NegaBinary) -> NegaBinary:
    """Add two negabinary numbers.

    Carry propagation in base -2:
        sum = a_i + b_i + carry
        If sum in {0, 1}: digit = sum, carry = 0
        If sum == 2:       digit = 0, carry = -1  (because 2 = 0 + (-1)*(-2))
        If sum == -1:      digit = 1, carry = 1   (because -1 = 1 + 1*(-2))
        If sum == 3:       digit = 1, carry = -1
        If sum == -2:      digit = 0, carry = 1   (because -2 = 0 + 1*(-2))
    """
    max_len = max(len(a._bits), len(b._bits))
    a_bits = a._bits + (0,) * (max_len - len(a._bits))
    b_bits = b._bits + (0,) * (max_len - len(b._bits))

    result: List[int] = []
    carry = 0

    for i in range(max_len):
        s = a_bits[i] + b_bits[i] + carry
        if s == 0:
            result.append(0); carry = 0
        elif s == 1:
            result.append(1); carry = 0
        elif s == 2:
            result.append(0); carry = -1
        elif s == -1:
            result.append(1); carry = 1
        elif s == 3:
            result.append(1); carry = -1
        elif s == -2:
            result.append(0); carry = 1
        else:
            # Shouldn't happen, but safety
            result.append(s % 2)
            carry = -(s // 2)

    # Carry can need up to 2 more positions to resolve
    while carry != 0:
        s = carry
        if s == 0:
            break
        elif s == 1:
            result.append(1); carry = 0
        elif s == -1:
            result.append(1); carry = 1
        elif s == 2:
            result.append(0); carry = -1
        elif s == -2:
            result.append(0); carry = 1
        else:
            result.append(abs(s) % 2)
            carry = -(s // -2) if s > 0 else ((-s) // 2)
            if carry == s:  # prevent infinite loop
                break

    # Strip leading zeros
    while len(result) > 1 and result[-1] == 0:
        result.pop()

    return NegaBinary(tuple(result))


def _nb_mul(a: NegaBinary, b: NegaBinary) -> NegaBinary:
    """Multiply two negabinary numbers via shift-and-add."""
    result = NegaBinary.from_int(0)

    for i, bit in enumerate(b._bits):
        if bit == 0:
            continue
        # Shift a left by i positions (multiply by (-2)^i)
        shifted_bits = (0,) * i + a._bits
        shifted = NegaBinary(shifted_bits)
        result = result + shifted

    return result


# ---------------------------------------------------------------------------
# Gate Stability Analysis: Binary vs Ternary
# ---------------------------------------------------------------------------

@dataclass
class GateStabilityReport:
    """Compare binary (2-gate) vs ternary (3-gate) stability for a value range."""
    values: List[int]
    binary_total_bits: int
    ternary_total_trits: int
    negabinary_total_bits: int
    binary_avg_entropy: float
    ternary_avg_entropy: float
    negabinary_avg_entropy: float
    stability_recommendation: str


def analyze_gate_stability(values: Sequence[int]) -> GateStabilityReport:
    """Compare 2-gate (binary/negabinary) vs 3-gate (balanced ternary) stability.

    For a set of values, measures:
    - Total representation width (bits/trits needed)
    - Average entropy (information density)
    - Stability recommendation

    Ternary is more stable when values cluster around zero (governance decisions).
    Binary is more efficient for large positive-only ranges.
    Negabinary handles mixed polarity without sign overhead.
    """
    from .trinary import BalancedTernary

    total_binary = 0
    total_ternary = 0
    total_negabinary = 0
    entropy_binary = 0.0
    entropy_ternary = 0.0
    entropy_negabinary = 0.0
    n = len(values)

    for v in values:
        # Standard binary width
        if v == 0:
            total_binary += 1
        else:
            total_binary += abs(v).bit_length() + (1 if v < 0 else 0)  # +1 for sign

        bt = BalancedTernary.from_int(v)
        total_ternary += bt.width
        entropy_ternary += bt.information_density()

        nb = NegaBinary.from_int(v)
        total_negabinary += nb.width
        entropy_negabinary += nb.bit_entropy()

    avg_entropy_binary = 1.0  # Standard binary always max entropy per definition
    avg_entropy_ternary = entropy_ternary / n if n > 0 else 0.0
    avg_entropy_negabinary = entropy_negabinary / n if n > 0 else 0.0

    # Stability heuristic:
    # - If values are small/mixed-sign: ternary wins (compact, no sign bit)
    # - If values span wide positive range: binary wins (natural fit)
    # - If values are mixed polarity: negabinary wins (no sign overhead)
    has_negative = any(v < 0 for v in values)
    max_abs = max(abs(v) for v in values) if values else 0

    if max_abs <= 40 and has_negative:
        rec = "TERNARY: small mixed-sign range, 3-gate offers compact encoding + governance mapping"
    elif has_negative and total_negabinary < total_binary:
        rec = "NEGABINARY: mixed polarity, signless encoding saves bits"
    elif total_ternary < total_negabinary:
        rec = "TERNARY: fewer trits than negabinary bits, 3-gate more efficient"
    else:
        rec = "BINARY: large positive range, standard 2-gate is most natural"

    return GateStabilityReport(
        values=list(values),
        binary_total_bits=total_binary,
        ternary_total_trits=total_ternary,
        negabinary_total_bits=total_negabinary,
        binary_avg_entropy=avg_entropy_binary,
        ternary_avg_entropy=avg_entropy_ternary,
        negabinary_avg_entropy=avg_entropy_negabinary,
        stability_recommendation=rec,
    )


# ---------------------------------------------------------------------------
# Cross-conversion
# ---------------------------------------------------------------------------

def negabinary_to_balanced_ternary(nb: NegaBinary) -> "BalancedTernary":
    """Convert negabinary to balanced ternary (through integer)."""
    from .trinary import BalancedTernary
    return BalancedTernary.from_int(nb.to_int())


def balanced_ternary_to_negabinary(bt: "BalancedTernary") -> NegaBinary:
    """Convert balanced ternary to negabinary (through integer)."""
    return NegaBinary.from_int(bt.to_int())
