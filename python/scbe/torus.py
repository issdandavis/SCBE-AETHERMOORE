"""
Torus / hypercube embedding — the board wrapped into floating-point space.
==========================================================================

The discrete board (board.py) is a flat grid. Wrap its edges and it becomes a
TORUS: column 0xf sits next to column 0x0, row 0xf next to row 0x0. That wrap is
the "wormhole" — on the flat board the two edges look far apart; on the torus they
are neighbours, one short hop across the seam.

Make it continuous: each nibble n∈0..15 becomes an angle θ = 2π·n/16, embedded as
(cos θ, sin θ). One nibble → a circle; two → a 2-torus (a donut surface); k nibbles
→ a k-torus floating in ℝ^(2k). The space is now floating-point and PERIODIC, so the
geometric router's tangent-vector geodesics run on it the same way they run on the
Poincaré ball — just with wrap-around shortcuts.

And the discrete skeleton underneath is the HYPERCUBE graph Qₙ: opcodes are nodes,
an edge joins two that differ in one bit. Flipping a low bit is a small step;
flipping a high bit jumps you to "another plane" (another opcode band / cube face) —
the user's wormhole-to-a-new-node. It is one hop in the cube, a long jump on the
flat board. Three embeddings of one token now coexist:

    discrete board  → reversible ADDRESS      (board.py)
    Poincaré ball   → governance COST          (geometric_router.py)
    flat torus      → periodic LOCALITY        (here)
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

TWO_PI = 2.0 * math.pi
EDGE = 16
AXES = ("hi", "mid", "lo")  # the three nibble axes (the cube)


def _nibbles(b: int) -> dict:
    return {"hi": (b >> 4) & 0xF, "mid": (b >> 2) & 0xF, "lo": b & 0xF}


def angles(b: int, axes: Sequence[str] = AXES) -> Tuple[float, ...]:
    """opcode -> one angle per axis (the torus coordinates, in radians)."""
    nb = _nibbles(b)
    return tuple(TWO_PI * nb[a] / EDGE for a in axes)


def to_torus(b: int, axes: Sequence[str] = AXES) -> Tuple[float, ...]:
    """opcode -> a continuous point on the k-torus in ℝ^(2k) (floating point)."""
    pt: List[float] = []
    for th in angles(b, axes):
        pt += [math.cos(th), math.sin(th)]
    return tuple(pt)


def torus_distance(a: int, b: int, axes: Sequence[str] = AXES) -> float:
    """Wrap-around geodesic distance: per axis take the SHORTER way round the circle
    (that's the wormhole), then L2 across axes."""
    s = 0.0
    for x, y in zip(angles(a, axes), angles(b, axes)):
        d = abs(x - y) % TWO_PI
        d = min(d, TWO_PI - d)  # the seam: wrap is the short side
        s += d * d
    return math.sqrt(s)


def hamming(a: int, b: int) -> int:
    return bin((a ^ b) & 0x3F).count("1")  # within the 6-bit opcode space


def hypercube_neighbors(b: int, bits: int = 6) -> List[int]:
    """The Qₙ edges: every one-bit flip. Flipping bit≥4 is a jump to another band."""
    return [b ^ (1 << i) for i in range(bits)]


def is_wormhole(a: int, b: int) -> bool:
    """True when the torus (wrap) distance is strictly shorter than the flat board
    distance — i.e. these two reach each other across a seam, not the long way."""
    flat = math.hypot(*(abs(x - y) for x, y in zip(((a >> 4) & 0xF, a & 0xF), ((b >> 4) & 0xF, b & 0xF))))
    wrap = 0.0
    for x, y in (((a >> 4) & 0xF, (b >> 4) & 0xF), (a & 0xF, b & 0xF)):
        d = abs(x - y)
        wrap += min(d, EDGE - d) ** 2
    return math.sqrt(wrap) < flat - 1e-9


def _demo() -> None:
    print("Torus / hypercube embedding\n")
    a, b = 0x0F, 0x00  # col 15 vs col 0
    print("  flat board: 0x0f col=15, 0x00 col=0  -> 15 apart")
    print(
        "  on the torus they wrap:", "%.3f" % torus_distance(a, b, ("lo",)), "rad  (wormhole:", is_wormhole(a, b), ")"
    )
    print("\n  hypercube Q6 neighbours of add(0x00):", [("0x%02x" % n) for n in hypercube_neighbors(0x00)])
    print("  flipping the high band bit (0x00 -> 0x20) is 1 hop in the cube,")
    print("  but jumps from the arithmetic plane to the comparison plane.")


if __name__ == "__main__":
    _demo()
