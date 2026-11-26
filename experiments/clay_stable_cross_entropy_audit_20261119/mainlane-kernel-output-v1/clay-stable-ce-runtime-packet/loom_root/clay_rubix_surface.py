#!/usr/bin/env python3
"""The token chart as a Rubik surface: 16x16 cells, 6 faces each, depth of relations.

    python clay_rubix_surface.py --demo
    python clay_rubix_surface.py --stochastic "some text" --samples 5
    python clay_rubix_surface.py --selftest

Issac (2026-07-27): "the tokenizer we made, the chart, is the OVERLAY. tag the
corners of each single slot like a dice and make 6 opcodes with a numerical
cross-representation to the opposite face ... the surface is the representation
of the things. then the depth of each individual cell is a factor of the
relations it has (color, code, word, sound, frequency, relationship to self and
others) ... moving the base to the depth and back to the base again."

THE STRUCTURE

  SURFACE   16 x 16 = 256 cells, addressed by the existing bijective barn
            alphabet (token_grid_buckets.ALPHA, glyph index == nibble).
            Cell (i,j) <-> a 2-glyph name. This part already existed.

  FACES     each cell carries 6 faces, numbered 1..6 like a die, so that
            OPPOSITE FACES SUM TO 7:  (1,6) (2,5) (3,4).
            face(f) and face(7-f) are duals -- the same slot, the opposite
            reading. The dual is an involution: apply it twice, you are home.

  DEPTH     a cell's depth is its relation vector: colour, code, word, sound,
            frequency, self-relation, cross-relations. Depth is DERIVED from
            the surface address plus the face, never stored separately, which
            is what makes base -> depth -> base exact rather than approximate.

WHY THIS IS ALSO THE STOCHASTIC TOKENIZER

Training on multiple segmentations of the same text improves robustness --
the model cannot lean on one encoding (arXiv:2604.16037). Six faces per cell
give exactly that for free: the same text encodes six ways, all valid, all
round-tripping to the same string.

That matters because Clay sits under the scale where models freely recover
character structure (arXiv:2406.11687, arXiv:2603.10771). Measured surfaces
(2026-07-29/30): Waterfall ≈ 59.5M trainable (the ~60M figure); ConnectX wave
base ≈ **17.2M** with LoRA rank-16 on top. The "hand structure the model cannot
recover" argument applies to **both**, and **more strongly** to the 17.2M
ConnectX surface than to Waterfall — do not let the 60M number travel alone
with this doc when discussing ConnectX.

Everything below round-trips. A representation that cannot return to base is
a lossy summary wearing a bijection's clothes.
"""

from __future__ import annotations

import argparse
import hashlib
import random
import sys
from dataclasses import dataclass
from typing import Dict, Iterator, List, Tuple

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ALPHA = "aeioubcdfghjklmn"          # barn glyphs: index == nibble, bijective
N = len(ALPHA)                      # 16
FACES = (1, 2, 3, 4, 5, 6)
RELATIONS = ("colour", "code", "word", "sound", "frequency", "self", "cross")


# ------------------------------------------------------------------ surface
def addr(i: int, j: int) -> str:
    return ALPHA[i] + ALPHA[j]


def cell(a: str) -> Tuple[int, int]:
    return ALPHA.index(a[0]), ALPHA.index(a[1])


def byte_to_addr(b: int) -> str:
    """A byte is exactly two nibbles, so a byte IS a cell address."""
    return addr(b >> 4, b & 0x0F)


def addr_to_byte(a: str) -> int:
    i, j = cell(a)
    return (i << 4) | j


# -------------------------------------------------------------------- faces
def dual(face: int) -> int:
    """Opposite face. On a die opposite faces sum to 7."""
    return 7 - face


@dataclass(frozen=True)
class Slot:
    """One cell seen through one face."""
    i: int
    j: int
    face: int

    @property
    def name(self) -> str:
        return f"{addr(self.i, self.j)}.{self.face}"

    @property
    def byte(self) -> int:
        return (self.i << 4) | self.j

    def opposite(self) -> "Slot":
        return Slot(self.i, self.j, dual(self.face))

    def depth(self) -> Dict[str, int]:
        """Relations, DERIVED from (address, face). Never stored.

        Derivation must be a pure function of the surface, or base -> depth ->
        base stops being exact and the whole structure degrades into a lookup
        table with extra steps.
        """
        b = self.byte
        f = self.face
        seed = hashlib.blake2s(bytes([b, f]), digest_size=8).digest()
        return {
            "colour": ((b * 6 + f * 41) % 360),          # hue on the wheel
            "code": (b ^ (f * 0x1F)) & 0xFF,
            "word": (b + f) % N,
            "sound": (self.i * 3 + self.j * 5 + f) % 12,  # 12 phonetic buckets
            "frequency": seed[0],
            "self": (self.i == self.j),
            "cross": seed[1] % N,
        }


def all_slots() -> Iterator[Slot]:
    for i in range(N):
        for j in range(N):
            for f in FACES:
                yield Slot(i, j, f)


# ---------------------------------------------------- base -> depth -> base
def to_depth(text: str, face_of: Dict[int, int] | None = None) -> List[Slot]:
    """Base (bytes) -> surface cells -> faces. The 'going down'."""
    out = []
    for k, b in enumerate(text.encode("utf-8")):
        f = (face_of or {}).get(k, 1)
        out.append(Slot(b >> 4, b & 0x0F, f))
    return out


def to_base(slots: List[Slot]) -> str:
    """Depth -> base. Face is carried, not consumed: any face returns home."""
    return bytes(s.byte for s in slots).decode("utf-8", errors="replace")


# ------------------------------------------------- stochastic tokenization
def stochastic_encode(text: str, rng: random.Random) -> List[Slot]:
    """One of 6^len valid encodings. All decode to the same string."""
    return [Slot(b >> 4, b & 0x0F, rng.choice(FACES)) for b in text.encode("utf-8")]


def stochastic_views(text: str, n: int, seed: int = 20260727) -> List[List[Slot]]:
    rng = random.Random(seed)
    return [stochastic_encode(text, rng) for _ in range(n)]


# ------------------------------------------------------------------ checks
def selftest() -> int:
    fails = 0

    # 1. surface bijection
    for b in range(256):
        if addr_to_byte(byte_to_addr(b)) != b:
            print(f"  FAIL byte round-trip at {b}"); fails += 1
    print(f"  surface bijection      256/256 bytes round-trip  {'OK' if not fails else 'FAIL'}")

    # 2. dual is an involution and opposite faces sum to 7
    bad = [f for f in FACES if dual(dual(f)) != f or f + dual(f) != 7]
    print(f"  dual involution        {len(FACES)-len(bad)}/{len(FACES)} faces, opposite sums to 7  "
          f"{'OK' if not bad else 'FAIL'}")
    fails += len(bad)

    # 3. depth is a PURE function of the surface -- same slot, same depth, always
    a, b = Slot(3, 7, 2).depth(), Slot(3, 7, 2).depth()
    print(f"  depth determinism      {'OK' if a == b else 'FAIL'}")
    fails += (a != b)

    # 4. opposite faces give DIFFERENT depth (the dual is a real distinction)
    same = sum(1 for s in all_slots() if s.depth() == s.opposite().depth())
    print(f"  dual separates depth   {1536-same}/1536 slots differ from their opposite  "
          f"{'OK' if same == 0 else 'FAIL'}")
    fails += (same != 0)

    # 5. base -> depth -> base is exact for EVERY face assignment
    txt = "the quick brown fox — ünïcödé 漢字 42"
    ok = all(to_base(v) == txt for v in stochastic_views(txt, 40))
    print(f"  base->depth->base      40/40 random face assignments return home  "
          f"{'OK' if ok else 'FAIL'}")
    fails += (not ok)

    # 6. the views are actually DIFFERENT (or it is not stochastic)
    views = stochastic_views(txt, 40)
    sigs = {tuple(s.face for s in v) for v in views}
    print(f"  views are distinct     {len(sigs)}/40 unique face-signatures  "
          f"{'OK' if len(sigs) > 30 else 'WEAK'}")

    # 7. slot count
    total = sum(1 for _ in all_slots())
    print(f"  slot count             {N}x{N}x{len(FACES)} = {total} slots")
    return 1 if fails else 0


def demo() -> None:
    print("=" * 70)
    print("RUBIX SURFACE   16x16 cells x 6 faces, depth derived from the surface")
    print("=" * 70)
    s = Slot(*cell("bd"), face=2)
    o = s.opposite()
    print(f"\n  slot {s.name}  (byte {s.byte:3d})     opposite {o.name}  (face {s.face}+{o.face}=7)")
    print(f"\n  {'relation':12} {'face '+str(s.face):>10} {'face '+str(o.face):>10}")
    ds, do = s.depth(), o.depth()
    for r in RELATIONS:
        print(f"  {r:12} {str(ds[r]):>10} {str(do[r]):>10}")
    print("\n  same cell, same address, opposite reading. Depth is DERIVED, so the")
    print("  surface remains the whole truth and nothing is stored twice.\n")

    txt = "clay"
    print(f"  stochastic tokenization of {txt!r} -- 6^{len(txt)} = {6**len(txt):,} valid encodings:")
    for v in stochastic_views(txt, 4):
        faces = "".join(str(s.face) for s in v)
        cells = " ".join(addr(s.i, s.j) for s in v)
        print(f"    faces {faces}   cells [{cells}]   -> {to_base(v)!r}")
    print("\n  every one decodes to the same string. That is the training signal:")
    print("  the model sees one text six ways and cannot lean on a single encoding.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--stochastic", type=str)
    ap.add_argument("--samples", type=int, default=5)
    a = ap.parse_args()
    if a.selftest:
        print("SELFTEST\n")
        return selftest()
    if a.stochastic:
        for v in stochastic_views(a.stochastic, a.samples):
            print("".join(str(s.face) for s in v), "->", repr(to_base(v)))
        return 0
    demo()
    return 0


if __name__ == "__main__":
    sys.exit(main())
