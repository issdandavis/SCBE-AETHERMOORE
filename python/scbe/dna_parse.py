"""dna_parse: parse hex by REPLICATION FORK, with a complement strand that self-checks.

Sibling to bijective_dna.py (which does this for OPCODE strands); this does it for hex DATA, to
braid the hex_to_int board task into the DNA model. Two distinct mechanisms, both real, kept honest:

  * CELL DIVISION = each side does half.  A hex value is positional base-16. Split the string at a
    MIDPOINT and parse each half INDEPENDENTLY (a replication fork: left half and right half grow at
    once), then join: value = left * 16^len(right) + right. Recurse, and it's a divide-and-conquer
    parse whose two sides are independent work -- genuinely parallelizable, log-depth. This is the
    "each side does half the work" reading, and it's correct here (unlike for the complement strand).

  * COMPLEMENT STRAND = a redundant self-check.  Hex<->DNA is a clean bijection: a base is 2 bits, so
    one hex digit = exactly 2 bases (established DNA-data-storage coding). Watson-Crick pairing
    A<->T, C<->G is 2-bit complement, so the antiparallel partner is the reverse-complement -- a
    SECOND FULL copy of the value (not half). A duplex parses two independent ways that must agree, so
    a single mutated base is caught. That is verification baked into the representation.

HONEST: the power is the bijection + the fork + the complement check; "cell division"/"DNA" are the
names, not the magic. This is a Python REFERENCE (tested below); the cross-face loomfn board version
of the fork-parse is the next step.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

BASES = "ACGT"  # A=0 C=1 G=2 T=3 (2 bits each)
_B2I = {b: i for i, b in enumerate(BASES)}
_HEXCHARS = "0123456789abcdef"


# --- hex <-> DNA: a bijection (1 hex digit = 2 bases) ---------------------------
def to_dna(hexstr: str) -> str:
    out: List[str] = []
    for ch in hexstr.lower():
        d = int(ch, 16)
        out.append(BASES[(d >> 2) & 3])
        out.append(BASES[d & 3])
    return "".join(out)


def from_dna(strand: str) -> str:
    if len(strand) % 2 != 0:
        raise ValueError("strand length must be even (2 bases per hex digit)")
    out: List[str] = []
    for i in range(0, len(strand), 2):
        out.append(_HEXCHARS[(_B2I[strand[i]] << 2) | _B2I[strand[i + 1]]])
    return "".join(out)


def complement_base(b: str) -> str:
    return BASES[3 - _B2I[b]]  # A<->T, C<->G == 2-bit complement


def reverse_complement(strand: str) -> str:
    """The antiparallel partner strand (a full redundant copy)."""
    return "".join(complement_base(b) for b in reversed(strand))


def duplex(hexstr: str) -> Tuple[str, str]:
    """Braid a hex value into a double strand (template, antiparallel partner)."""
    s = to_dna(hexstr)
    return s, reverse_complement(s)


# --- the replication fork: each side does half ----------------------------------
def fork_parse(hexstr: str) -> int:
    """Parse hex by splitting at the midpoint and parsing each half independently, then joining.
    value = left * 16^len(right) + right. The two sides are independent work (parallelizable)."""
    if hexstr == "":
        return 0
    if len(hexstr) == 1:
        return int(hexstr, 16)  # a leaf: one digit (== 2 DNA bases)
    mid = len(hexstr) // 2
    left, right = hexstr[:mid], hexstr[mid:]
    return fork_parse(left) * (16 ** len(right)) + fork_parse(right)


def fork_tree(hexstr: str) -> Dict[str, Any]:
    """The replication-fork tree (to SEE the division): each node splits into two daughters."""
    if len(hexstr) <= 1:
        return {"seg": hexstr, "value": fork_parse(hexstr)}
    mid = len(hexstr) // 2
    return {
        "seg": hexstr,
        "value": fork_parse(hexstr),
        "left": fork_tree(hexstr[:mid]),
        "right": fork_tree(hexstr[mid:]),
    }


# --- parse with the complement self-check ---------------------------------------
def parse_checked(hexstr: str) -> Tuple[int, bool]:
    """Braid into a duplex, fork-parse the value, and confirm the two strands are truly
    complementary (a mutated base breaks this). ok=True means the duplex is self-consistent."""
    s, partner = duplex(hexstr)
    ok = reverse_complement(s) == partner and reverse_complement(partner) == s and from_dna(s) == hexstr.lower()
    return fork_parse(hexstr), ok


def verify_duplex(d: Tuple[str, str]) -> bool:
    """A received duplex is intact iff its strands reverse-complement each other (catches mutation)."""
    s, partner = d
    return reverse_complement(s) == partner and reverse_complement(partner) == s


def replicate(strand: str) -> Tuple[Tuple[str, str], Tuple[str, str]]:
    """Cell division: separate the strands; each one alone templates the FULL duplex back, so the
    two daughters are identical -- each carries the whole value."""
    partner = reverse_complement(strand)
    daughter_a = (strand, reverse_complement(strand))
    daughter_b = (reverse_complement(partner), partner)  # template the partner -> back to (strand, partner)
    return daughter_a, daughter_b


def _demo() -> None:
    h = "2a"
    s, partner = duplex(h)
    print("dna_parse: braid hex into a self-checking DNA duplex\n")
    print("  hex            :", h)
    print("  strand 5'->3'  :", s, " (1 hex digit = 2 bases)")
    print("  partner (rc)   :", partner, " (antiparallel, full redundant copy)")
    value, ok = parse_checked(h)
    print("  fork-parse     :", value, "  self-check ok:", ok)
    t = fork_tree("2a1f")
    print("\n  replication fork on '2a1f' (each side does half):")
    print("    '%s' = %d" % (t["seg"], t["value"]))
    print(
        "      <- '%s'=%d   -> '%s'=%d" % (t["left"]["seg"], t["left"]["value"], t["right"]["seg"], t["right"]["value"])
    )
    da, db = replicate(s)
    print("\n  cell division -> two identical daughters:", da == db, "(each carries the full value)")


if __name__ == "__main__":
    _demo()
