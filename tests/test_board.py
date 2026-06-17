"""Go-board / cube embedding — reversible address, mid-nibble axis, notes, trichromatic."""

import random

from python.scbe import board as B
from python.scbe import polyglot as P


def test_point_is_bijective_over_all_bytes():
    for b in range(256):
        r, c = B.to_point(b)
        assert B.from_point(r, c) == b  # hi/lo nibbles fully recover the byte


def test_cube_4x4x4_is_bijective_over_64_opcodes():
    seen = set()
    for b in range(64):
        band, mid, col = B.to_cube(b)
        assert 0 <= band < 4 and 0 <= mid < 4 and 0 <= col < 4
        assert B.from_cube(band, mid, col) == b
        seen.add((band, mid, col))
    assert len(seen) == 64  # tiles the whole 4x4x4 cube


def test_mid_nibble_is_the_seam_bits_2_to_5():
    for b in range(256):
        assert B.mid_nibble(b) == (b >> 2) & 0xF


def test_place_recover_round_trips():
    rng = random.Random(5)
    ops = sorted(P.SCALAR_OPS)
    for seed in range(20):
        prog = P.program_bytes(*[rng.choice(ops) for _ in range(rng.randint(0, 12))])
        assert B.recover(B.place(prog)) == prog
        assert B.is_reversible(prog)


def test_trichromatic_rgb_in_range_and_varies():
    colors = {B.rgb(b) for b in range(64)}
    for r, g, bl in colors:
        assert 0 <= r <= 255 and 0 <= g <= 255 and 0 <= bl <= 255
    assert len(colors) == 64  # every opcode a distinct colour


def test_notes_rooted_at_a4():
    assert B.note_name(440.0) == "A4"
    assert B.note_name(660.0) in ("E5",)  # ~659.25 Hz -> E5 (CA tongue)
    f, name = B.opcode_note(0x00, 440.0)  # add -> root degree -> A4
    assert name == "A4" and abs(f - 440.0) < 1e-6


def test_triad_is_three_notes_one_per_axis():
    tri = B.triad(0x2A, 440.0)
    assert [ch for _, _, ch in tri] == ["R", "G", "B"]
    assert all(isinstance(nm, str) for _, nm, _ in tri)
