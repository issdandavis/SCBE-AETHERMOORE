"""dna_parse: a bijective hex<->base-4 codec, plus two honest demos.

DEMOTED 2026-06-18 after a self-audit (the metaphor was carrying weight the math won't bear).
Reducing each borrowed word to its one line of math:

  * KEEP -- the bijection.  "hex<->DNA" reduces to: a base is 2 bits, so one hex digit = exactly 2
    base-4 symbols over {A,C,G,T} (established DNA-data-storage coding). `to_dna`/`from_dna`
    round-trip exactly. This is the only load-bearing claim and it stands.

  * DEMO ONLY -- the "replication fork".  `fork_parse` reduces to: value = left*16^len(right) + right.
    But 16^k is a power of two, so the multiply is a shift and the add never carries -- on a
    power-of-2 base this is just CONCATENATING the nibbles, which Horner's O(n) loop already does.
    The recursion buys NOTHING on hex. Divide-and-conquer base conversion only earns its keep on
    NON-power-of-2 bases (base 10) with fast bignum multiply -- and even there, CPython's int() is
    already subquadratic, so the technique only matters in a target without optimized bignum. Kept
    as an illustration, not an algorithm.

  * DEMO ONLY -- the "complement self-check".  The reverse-complement (Watson-Crick A<->T C<->G =
    2-bit complement) is a 2x redundant copy that only DETECTS a single flipped base. As an integrity
    code it is strictly dominated: a 1-bit parity detects any single flip at ~1/n the cost; a CRC
    detects far more; Reed-Solomon corrects. Its only non-dominated role would be a second
    INDEPENDENT decode path -- but this stores a byte-for-byte copy, not independent logic, and the
    py/js/rust cross-face check already gives three independent paths. So: not a verification
    primitive. Use a CRC. Kept as a bijection demo.
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


# --- midpoint split (DEMO: on a power-of-2 base this is just nibble concatenation) ----------------
def fork_parse(hexstr: str) -> int:
    """Parse hex by splitting at the midpoint and joining: value = left*16^len(right) + right.
    NOTE: 16^k is a power of two, so this reduces to concatenating nibbles -- the same thing Horner's
    O(n) loop does. The recursion is illustrative, not faster. Divide-and-conquer only helps on
    non-power-of-2 bases with fast bignum multiply (and even then, CPython's int() is already
    subquadratic). Kept as a demo; `int(hexstr, 16)` is the right tool."""
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


# --- complement check (DEMO: a 2x redundant copy, detection-only, dominated by a CRC) ------------
def parse_checked(hexstr: str) -> Tuple[int, bool]:
    """Parse, and confirm the two strands reverse-complement each other. ok=True == self-consistent.
    NOTE: this is a 2x redundant copy that only DETECTS one flipped base -- a CRC does that better
    for a fraction of the cost. Not a verification primitive; kept as a bijection demo."""
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
