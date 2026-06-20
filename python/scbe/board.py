"""
Go-board embedding — the token grid as a board, opcodes as stones.
==================================================================

The byte space is a 16×16 grid: hi nibble = row, lo nibble = column. That grid is
literally the Sacred Tongue token table (16 prefixes × 16 suffixes). So a program's
opcodes are STONES placed on a Go-style board, numbered by move order.

Why it matters: this is a DISCRETE, fully reversible embedding — board point ⇄
opcode byte, no information lost. It's the flat counterpart to the hyperbolic
Poincaré embedding the router uses: the board is a reversible *address*, the ball is
a governance *cost*. Two embeddings of one token; the board closes the inverse gap
(position → token) that the continuous ball can't.

The v1 scalar core lives in bytes 0x00–0x3F, i.e. the top four rows — the four CA
opcode bands (arithmetic / logic / comparison / aggregation). A program is then a
game record on that strip; replaying a point just means the opcode recurs.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

EDGE = 16
BANDS = ("arithmetic", "logic", "comparison", "aggregation")  # rows 0..3 of the board

NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
MAJOR = (0, 2, 4, 5, 7, 9, 11, 12)  # major-scale semitones


def to_point(b: int) -> Tuple[int, int]:
    """opcode byte -> board point (row, col).  Bijective with from_point."""
    return (b >> 4) & 0xF, b & 0xF


def from_point(row: int, col: int) -> int:
    """board point -> opcode byte.  The inverse — this is what makes it reversible."""
    return ((row & 0xF) << 4) | (col & 0xF)


def mid_nibble(b: int) -> int:
    """The MID nibble — bits 2..5, straddling the hi/lo seam. For a Sacred Tongue
    token prefix'suffix it's exactly the 4 bits across the apostrophe (low 2 of the
    prefix + high 2 of the suffix), so it's a real third 'spot' / depth axis. hi+lo
    already recover the byte, so mid is a derived seam coordinate (a check digit)."""
    return (b >> 2) & 0xF


def to_cube(b: int) -> Tuple[int, int, int]:
    """A TRUE 3-axis split of the 6-bit opcode: (band, mid, col), each 0..3 — the
    64 opcodes tile a 4×4×4 cube (a Rubik's Revenge). Bijective via from_cube."""
    return (b >> 4) & 0x3, (b >> 2) & 0x3, b & 0x3


def from_cube(band: int, mid: int, col: int) -> int:
    return ((band & 0x3) << 4) | ((mid & 0x3) << 2) | (col & 0x3)


def rgb(b: int) -> Tuple[int, int, int]:
    """TRICHROMATIC: the cube's three axes (band, mid, col) -> one RGB colour, each
    2-bit axis spread across 0/85/170/255. Similar opcodes sit near each other in
    colour space, so a program reads as a colour gradient."""
    band, mid, col = to_cube(b)
    return band * 85, mid * 85, col * 85


def note_name(freq: float) -> str:
    """Frequency -> nearest equal-tempered note name (A4 = 440 Hz)."""
    if freq <= 0:
        return "-"
    midi = round(69 + 12 * math.log2(freq / 440.0))
    return NOTE_NAMES[midi % 12] + str(midi // 12 - 1)


def opcode_note(b: int, root_hz: float) -> Tuple[float, str]:
    """One opcode -> one pitch: a major-scale degree (from its low bits) above the
    tongue's root note. A program is then a melody in that tongue's key."""
    semis = MAJOR[b & 0x7]
    f = root_hz * (2.0 ** (semis / 12.0))
    return f, note_name(f)


def triad(b: int, root_hz: float) -> List[Tuple[float, str, str]]:
    """TRICHROMATIC NOTES: each opcode is a 3-note chord, one note per cube axis
    (band=R, mid=G, col=B), stacked over three octaves. Returns (freq, name, channel)."""
    out = []
    for axis, channel in zip(to_cube(b), ("R", "G", "B")):
        f = root_hz * (2.0 ** (MAJOR[axis] / 12.0)) * (2.0 ** (("RGB".index(channel))))
        out.append((f, note_name(f), channel))
    return out


def place(prog: Sequence[int]) -> List[Tuple[int, Tuple[int, int], int]]:
    """A program -> ordered stones: (move_number, point, byte)."""
    return [(i, to_point(b), b) for i, b in enumerate(prog, 1)]


def recover(stones: Sequence[Tuple[int, Tuple[int, int], int]]) -> List[int]:
    """Stones (in move order) -> program. Proves the board is a reversible embedding."""
    return [from_point(r, c) for _, (r, c), _ in stones]


def is_reversible(prog: Sequence[int]) -> bool:
    return recover(place(prog)) == list(prog)
