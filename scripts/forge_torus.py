#!/usr/bin/env python3
"""Aether Forge on the torus -- the map IS the program, as a path on a real surface.

3Blue1Brown's topology move: map your objects onto a surface and the structure
becomes visible (pairs of loop-points -> a Mobius strip). SCBE already ships that
surface -- python/scbe/torus.py folds a byte onto a k-torus with wrap-around (the
same edge-identification as a Mobius strip / "wormhole").

This lifts a Forge build onto it:
  - each BUILDING (move) -> a point on the 3-torus (its angles).
  - each ROAD (consecutive moves) -> a distance on the surface; some are WORMHOLES
    (far in raw value, adjacent on the torus -- the fold making structure obvious).
  - the DEED (the lossless prime signature) -> its bytes traced as a path: the
    program's TOPOLOGICAL ADDRESS. Reversible all the way back to the moves.

    python scripts/forge_torus.py            # lift a sample build onto the torus
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import _MOVE_ID, prime_signature  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from python.scbe.torus import angles, is_wormhole, torus_distance  # noqa: E402


def _byte(move: str) -> int:
    """A move -> a byte that uses both nibbles, so it spreads around the torus."""
    mid = _MOVE_ID.get(move, 0)
    return ((mid << 4) | mid) & 0xFF


def _deg(rads):
    return tuple(round(math.degrees(r) % 360, 1) for r in rads)


def lift(moves: list[str]):
    print(f"\n  build: {' -> '.join(moves)}")
    print("\n  BUILDINGS as points on the 3-torus (angles in degrees, hi/mid/lo):")
    bytes_ = []
    for m in moves:
        b = _byte(m)
        bytes_.append(b)
        print(f"    {m:<10} byte 0x{b:02x}  ->  {_deg(angles(b))}")

    print("\n  ROADS (distance on the surface; a WORMHOLE = the fold making them adjacent):")
    for a, b, ma, mb in zip(bytes_, bytes_[1:], moves, moves[1:]):
        d = torus_distance(a, b)
        worm = " <- WORMHOLE (far in value, close on the torus)" if is_wormhole(a, b) else ""
        print(f"    {ma} -> {mb}:  {d:.3f}{worm}")

    sig = prime_signature(moves)
    addr = [angles(byte)[0] for byte in sig.to_bytes((sig.bit_length() + 7) // 8, "big")]
    print(f"\n  the program's TOPOLOGICAL ADDRESS = its deed ({sig}) traced on the torus:")
    print("    first axis of each deed-byte (deg): "
          + " ".join(f"{round(math.degrees(a) % 360):>3}" for a in addr[:16]))
    print("\n  the map IS the program: a path on a real surface; the deed is its address;")
    print("  and it's reversible -- the deed factors back to the exact moves. Topology, made literal.\n")


def main():
    moves = sys.argv[1:] or ["add", "due", "agenda", "find"]
    lift([m for m in moves if m in _MOVE_ID])


if __name__ == "__main__":
    main()
