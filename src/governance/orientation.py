"""Multi-sign orientation: discrete up/down/flat per axis, with the VALUE left alone.

Issac: "multi sign as well the +-+/+++/---/-+-/++-/--+ etc ... this gives discrete up/down
without value change, its orientation ... in a mid dimensional space of priority by concurrent
tangential relationships."

WHAT THIS IS. An orientation is one sign per axis, drawn from ``{+, 0, -}``. It carries no
magnitude. Two states with identical values and different orientations are the same *reading*
facing different *ways* -- which is exactly what you want when the thing that changed is
direction of travel, not the number. This is the same primal/tangent split as
``loom/tongue_dual_carry.py``: the value is the primal, the orientation is the tangent, and
the tangent is where a perturbation would ENTER.

THE STRUCTURE IS A SIGNED LATTICE, NOT A LIST. Over 3 axes there are 2^3 = 8 pure orientations
and 3^3 = 27 once ``0`` is allowed. The pure ones close under negation into **four antipodal
pairs** -- the six Issac wrote are three of those four:

    +++ / ---        +-+ / -+-        ++- / --+        (+-- / -++ is the fourth)

``negate()`` is that antipode. It is an involution, and it reverses every axis at once without
touching a single value.

MID-DIMENSIONAL, ON PURPOSE. Arity is not fixed at 3. The natural width here is **6, one sign
per tongue** (KO AV RU CA UM DR), so an orientation says which tongues are rising, which are
falling, and which are flat -- concurrently. That is the "mid dimensional space of priority":
below the full continuous state, above a single scalar trend.

WHAT IT IS NOT. Orientation is a **label**, so it enlarges the space of distinguishable
readings; it does not add key entropy. 27 trit-triples is ~4.75 bits of label space and 0 bits
of security. See ``trichromatic_state_chain.security_report()`` -- the same discipline that
refuses to call 63 detection channels 504 bits of security refuses to bank orientation labels
as bits.

Consumed by ``src/governance/trichromatic_state_chain.py``, which binds the orientation under
the tag so flipping one sign changes the tag and nothing else.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Dict, Iterator, List, Sequence, Tuple

#: Canonical character for each sign. Matches the signature strings used across the substrate
#: (``loom/signed_flow.py``, ``loom/mixed_propagate.py``, ``loom/clifford_sig.py``) so a
#: signature written in one place reads the same in all of them.
SIGN_TO_CHAR: Dict[int, str] = {1: "+", 0: "0", -1: "-"}
CHAR_TO_SIGN: Dict[str, int] = {"+": 1, "0": 0, "-": -1}

#: The six governance tongues, in the order an arity-6 orientation indexes them.
TONGUE_AXES: Tuple[str, ...] = ("KO", "AV", "RU", "CA", "UM", "DR")


@dataclass(frozen=True)
class Orientation:
    """One sign per axis. Immutable, hashable, and comparable by value."""

    signs: Tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.signs:
            raise ValueError("orientation needs at least one axis")
        bad = [s for s in self.signs if s not in (-1, 0, 1)]
        if bad:
            raise ValueError(f"signs must each be -1, 0, or +1; got {bad}")

    # -- construction ------------------------------------------------------

    @classmethod
    def parse(cls, text: str) -> "Orientation":
        """Build from a signature string such as ``"+-+"`` or ``"+0-+-0"``.

        Args:
            text: One character per axis, each of ``+``, ``-`` or ``0``.

        Returns:
            The orientation.

        Raises:
            ValueError: If any character is not a sign.
        """
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("empty orientation string")
        try:
            return cls(tuple(CHAR_TO_SIGN[c] for c in cleaned))
        except KeyError as exc:
            raise ValueError(f"bad sign character {exc.args[0]!r} in {text!r}; expected + - or 0") from exc

    @classmethod
    def flat(cls, arity: int = 3) -> "Orientation":
        """The all-zero orientation -- every axis flat."""
        return cls(tuple(0 for _ in range(arity)))

    # -- presentation ------------------------------------------------------

    @property
    def canonical(self) -> str:
        """The signature string, e.g. ``"+-+"``."""
        return "".join(SIGN_TO_CHAR[s] for s in self.signs)

    @property
    def arity(self) -> int:
        """Number of axes."""
        return len(self.signs)

    def __str__(self) -> str:
        return self.canonical

    def as_tongue_map(self) -> Dict[str, int]:
        """Label an arity-6 orientation by tongue.

        Returns:
            Mapping of tongue code to its sign.

        Raises:
            ValueError: If the arity is not 6.
        """
        if self.arity != len(TONGUE_AXES):
            raise ValueError(f"tongue mapping needs arity {len(TONGUE_AXES)}, this orientation has {self.arity}")
        return dict(zip(TONGUE_AXES, self.signs))

    # -- algebra -----------------------------------------------------------

    def negate(self) -> "Orientation":
        """The antipode: every axis reversed at once. An involution."""
        return Orientation(tuple(-s for s in self.signs))

    def flip(self, axis: int) -> "Orientation":
        """Reverse a single axis.

        Args:
            axis: Zero-based axis index.

        Returns:
            A new orientation with that axis negated.
        """
        if not 0 <= axis < self.arity:
            raise IndexError(f"axis {axis} out of range for arity {self.arity}")
        signs = list(self.signs)
        signs[axis] = -signs[axis]
        return Orientation(tuple(signs))

    def is_pure(self) -> bool:
        """True when no axis is flat -- i.e. this is one of the ``2**arity`` sign vectors."""
        return 0 not in self.signs

    def agreement(self, other: "Orientation") -> int:
        """Count axes pointing the same way.

        Args:
            other: Orientation of the same arity.

        Returns:
            Number of matching axes.
        """
        if other.arity != self.arity:
            raise ValueError(f"arity mismatch: {self.arity} vs {other.arity}")
        return sum(1 for a, b in zip(self.signs, other.signs) if a == b)

    # -- binding -----------------------------------------------------------

    def encode(self) -> bytes:
        """Canonical bytes for binding under a MAC. ASCII signature, one byte per axis."""
        return self.canonical.encode("ascii")


# ---------------------------------------------------------------------------
# Enumeration
# ---------------------------------------------------------------------------


def all_orientations(arity: int = 3, *, allow_zero: bool = False) -> List[Orientation]:
    """Every orientation of a given arity, in canonical order.

    Args:
        arity: Number of axes.
        allow_zero: Include flat axes, giving ``3**arity`` instead of ``2**arity``.

    Returns:
        All orientations, ordered ``+`` before ``0`` before ``-`` on each axis.
    """
    if arity < 1:
        raise ValueError("arity must be >= 1")
    alphabet = (1, 0, -1) if allow_zero else (1, -1)
    return [Orientation(combo) for combo in itertools.product(alphabet, repeat=arity)]


def antipodal_pairs(arity: int = 3) -> List[Tuple[Orientation, Orientation]]:
    """The pure orientations grouped into antipodal pairs.

    Args:
        arity: Number of axes.

    Returns:
        ``2**(arity-1)`` pairs, each ``(o, o.negate())``, with no orientation repeated.
    """
    seen: set = set()
    pairs: List[Tuple[Orientation, Orientation]] = []
    for o in all_orientations(arity, allow_zero=False):
        if o in seen:
            continue
        anti = o.negate()
        seen.add(o)
        seen.add(anti)
        pairs.append((o, anti))
    return pairs


def label_space_bits(arity: int = 3, *, allow_zero: bool = True) -> float:
    """How many bits of LABEL space a given orientation family spans.

    This is deliberately named ``label_space_bits`` and not ``entropy`` or ``security_bits``.
    Distinguishing more readings is not the same as resisting forgery: an attacker who can
    read the state can read its orientation too.

    Args:
        arity: Number of axes.
        allow_zero: Whether flat axes are permitted.

    Returns:
        ``log2(3**arity)`` or ``log2(2**arity)``.
    """
    base = 3 if allow_zero else 2
    return math.log2(base**arity)


def iter_signatures(signatures: Sequence[str]) -> Iterator[Orientation]:
    """Parse a sequence of signature strings.

    Args:
        signatures: Strings like ``["+-+", "+++", "---"]``.

    Yields:
        Parsed orientations.
    """
    for s in signatures:
        yield Orientation.parse(s)
