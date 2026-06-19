"""dna_parse: hex braided into a DNA duplex -- fork-parse (each side does half) + a complement
strand that self-checks (a mutated base is caught).

hex<->DNA is a bijection (1 digit = 2 bases); the reverse-complement is a full redundant copy;
the fork-parse splits at the midpoint and must equal the plain value; corruption breaks the duplex.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.dna_parse import (  # noqa: E402
    duplex,
    fork_parse,
    fork_tree,
    from_dna,
    parse_checked,
    replicate,
    reverse_complement,
    to_dna,
    verify_duplex,
)


def test_hex_dna_is_a_bijection():
    assert to_dna("0") == "AA" and to_dna("f") == "TT"
    for h in ["0", "a", "f", "00", "2a", "ff", "10", "deadbeef", "0123456789abcdef"]:
        assert from_dna(to_dna(h)) == h  # round-trips exactly
    for d in range(16):  # every single digit maps to exactly 2 bases and back
        h = "%x" % d
        assert len(to_dna(h)) == 2 and from_dna(to_dna(h)) == h


def test_reverse_complement_is_an_involution_and_full_copy():
    for h in ["2a", "ff", "deadbeef", "1234"]:
        s = to_dna(h)
        assert reverse_complement(reverse_complement(s)) == s  # involution
        assert len(reverse_complement(s)) == len(s)  # a full copy, not half


def test_fork_parse_each_side_half_equals_plain_value():
    # the replication-fork (divide-and-conquer) parse must equal int(h, 16)
    for h in ["0", "a", "f", "2a", "ff", "10", "100", "2a1f", "deadbeef", "0123456789abcdef"]:
        assert fork_parse(h) == int(h, 16)
    assert fork_parse("") == 0


def test_fork_tree_divides_into_independent_halves():
    t = fork_tree("2a1f")
    assert t["value"] == 0x2A1F
    # the two daughters are parsed independently and recombine to the parent
    assert t["left"]["value"] == 0x2A and t["right"]["value"] == 0x1F
    assert t["left"]["value"] * (16**2) + t["right"]["value"] == t["value"]


def test_parse_checked_agrees_and_matches_the_board_hex_cases():
    # the same cases the hex_to_int board task uses
    for h, want in [("0", 0), ("a", 10), ("f", 15), ("10", 16), ("2a", 42), ("ff", 255)]:
        value, ok = parse_checked(h)
        assert value == want and ok is True


def test_a_mutated_base_is_caught():
    s, partner = duplex("2a")
    assert verify_duplex((s, partner)) is True
    mutated = ("C" if s[0] != "C" else "A") + s[1:]  # flip the first base
    assert verify_duplex((mutated, partner)) is False  # complementarity broken -> detected


def test_cell_division_yields_identical_full_daughters():
    s = to_dna("deadbeef")
    a, b = replicate(s)
    assert a == b  # both daughters identical
    assert from_dna(a[0]) == "deadbeef" and fork_parse(from_dna(a[0])) == 0xDEADBEEF
