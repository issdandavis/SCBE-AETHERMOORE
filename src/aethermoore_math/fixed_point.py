"""
Q16.16 Fixed-Point Arithmetic
=============================
Deterministic math that produces identical results on all platforms.
Essential for distributed consensus where all nodes must agree.

Format: 16 bits integer + 16 bits fraction
Range: -32768.0 to 32767.99998 (approximately)
Precision: 1/65536 ≈ 0.0000153
"""

from dataclasses import dataclass
from typing import Union
import struct

Q16_16_SCALE = 2**16  # 65536
Q16_16_MAX = (2**31 - 1)
Q16_16_MIN = -(2**31)


@dataclass
class Q16_16:
    """
    Q16.16 fixed-point number.

    Usage:
        >>> a = Q16_16.from_float(3.14159)
        >>> b = Q16_16.from_float(2.71828)
        >>> c = a + b
        >>> c.to_float()  # 5.85987...
    """
    raw: int

    @classmethod
    def from_float(cls, f: float) -> 'Q16_16':
        """Convert float to Q16.16."""
        raw = int(f * Q16_16_SCALE)
        # Clamp to valid range
        raw = max(Q16_16_MIN, min(Q16_16_MAX, raw))
        return cls(raw)

    @classmethod
    def from_int(cls, i: int) -> 'Q16_16':
        """Convert integer to Q16.16."""
        return cls(i << 16)

    @classmethod
    def from_bytes(cls, b: bytes) -> 'Q16_16':
        """Deserialize from 4 bytes (big-endian)."""
        return cls(struct.unpack('>i', b)[0])

    def to_float(self) -> float:
        """Convert to float."""
        return self.raw / Q16_16_SCALE

    def to_int(self) -> int:
        """Convert to integer (truncates)."""
        return self.raw >> 16

    def to_bytes(self) -> bytes:
        """Serialize to 4 bytes (big-endian)."""
        return struct.pack('>i', self.raw)

    def __add__(self, other: 'Q16_16') -> 'Q16_16':
        """Addition."""
        return Q16_16(self.raw + other.raw)

    def __sub__(self, other: 'Q16_16') -> 'Q16_16':
        """Subtraction."""
        return Q16_16(self.raw - other.raw)

    def __mul__(self, other: 'Q16_16') -> 'Q16_16':
        """Multiplication (with proper scaling)."""
        # Multiply, then shift back to maintain scale
        result = (self.raw * other.raw) >> 16
        return Q16_16(result)

    def __truediv__(self, other: 'Q16_16') -> 'Q16_16':
        """Division (with proper scaling)."""
        if other.raw == 0:
            raise ZeroDivisionError("Q16_16 division by zero")
        # Shift numerator up before dividing to maintain precision
        result = (self.raw << 16) // other.raw
        return Q16_16(result)

    def __neg__(self) -> 'Q16_16':
        """Negation."""
        return Q16_16(-self.raw)

    def __abs__(self) -> 'Q16_16':
        """Absolute value."""
        return Q16_16(abs(self.raw))

    def __eq__(self, other: object) -> bool:
        """Equality (exact bit comparison)."""
        if isinstance(other, Q16_16):
            return self.raw == other.raw
        return False

    def __lt__(self, other: 'Q16_16') -> bool:
        """Less than."""
        return self.raw < other.raw

    def __le__(self, other: 'Q16_16') -> bool:
        """Less than or equal."""
        return self.raw <= other.raw

    def __gt__(self, other: 'Q16_16') -> bool:
        """Greater than."""
        return self.raw > other.raw

    def __ge__(self, other: 'Q16_16') -> bool:
        """Greater than or equal."""
        return self.raw >= other.raw

    def __repr__(self) -> str:
        return f"Q16_16({self.to_float():.6f})"

    def __hash__(self) -> int:
        return hash(self.raw)


# Common constants in Q16.16
Q16_ZERO = Q16_16(0)
Q16_ONE = Q16_16(Q16_16_SCALE)
Q16_HALF = Q16_16(Q16_16_SCALE // 2)
Q16_PI = Q16_16.from_float(3.14159265358979)
Q16_E = Q16_16.from_float(2.71828182845905)


def q16_sqrt(x: Q16_16) -> Q16_16:
    """
    Integer square root for Q16.16.
    Uses Newton-Raphson iteration.
    """
    if x.raw <= 0:
        return Q16_ZERO

    # Initial guess
    n = x.raw << 16  # Scale up for precision
    guess = n

    # Newton-Raphson: x_new = (x + n/x) / 2
    for _ in range(16):
        new_guess = (guess + n // guess) >> 1
        if new_guess >= guess:
            break
        guess = new_guess

    return Q16_16(guess)


def q16_sin(x: Q16_16) -> Q16_16:
    """
    Sine using Taylor series (5 terms).
    Input assumed to be in radians.
    """
    # Reduce to [-π, π]
    pi = Q16_PI
    two_pi = pi + pi

    while x > pi:
        x = x - two_pi
    while x < -pi:
        x = x + two_pi

    # Taylor: sin(x) = x - x³/3! + x⁵/5! - x⁷/7! + ...
    x2 = x * x
    x3 = x2 * x
    x5 = x3 * x2
    x7 = x5 * x2

    fact3 = Q16_16.from_float(6.0)
    fact5 = Q16_16.from_float(120.0)
    fact7 = Q16_16.from_float(5040.0)

    result = x - (x3 / fact3) + (x5 / fact5) - (x7 / fact7)
    return result
