"""Lossless charge encoding for the 64-opcode ISA, and the x86-64 attachment.

`ca_opcode_table.py` gives each opcode a hand-assigned 6-trit vector. Those trits carry
real judgements -- `bitclear` has DR = -1 because it destroys information, which no index
can express -- so they stay exactly as they are. But as an IDENTITY they lose most of the
ISA. Measured over all 64 opcodes:

    CA  {1: 64}                CONSTANT, zero information
    KO/AV/RU/UM               binary only, never negative
    DR  {-1: 8, 0: 43, 1: 13} the ONLY tongue that is actually a trit

    -> 21 distinct codes for 64 opcodes, in 11 collision classes.

The largest class merges add, sub, mul, mod, abs, neg, inc, dec, bitset, min, max. Another
merges and, or, not, nand, nor, eq, neq, lt, lte, gt, gte. It collapses operations with
their own inverses -- inc/dec, and/nand, lt/gte -- which is precisely what a sign system
should separate best.

Nothing needs assigning to fix this. The opcode INDEX already is a six-position sign field
(0 -> -, 1 -> +), and `binary_index` is the first entry in `layers_per_opcode` in
loom/opcode_multilayer_map.json. The structure falls straight out of the numbering:

    realm = the TOP TWO SIGNS      number --   bits -+   judge +-   gather ++
    each realm spans C(4,k) = 1,4,6,4,1 ; the ISA spans C(6,k) = 1,6,15,20,15,6,1
    bits and judge are CHARGE-CONJUGATE (both prefixes net zero) -> identical shells
    nor(0x15) and within(0x2A) are the only size-2 rotation orbit: -+-+-+ / +-+-+-

Measured payoff on six real DLL .text sections (15 pairs, same opcodes, same lifted
instructions -- the only change is reading the index instead of the trit vector):

    mean pairwise separation   trit 0.2675   charge 0.9418   3.52x
    MIN  pairwise separation   trit 0.0793   charge 0.4655   5.87x

All fifteen pairs improved. The minimum is what matters: it is the closest pair the
encoding still has to tell apart. Under trits `_decimal` and `_elementtree` sit at 0.0793
-- an arbitrary-precision arithmetic library and an XML parser, effectively identical.

NEGABINARY is also provided and does a DIFFERENT job. Reading the index in base -2 gives
each opcode a unique signed integer in exactly [-42, +21] -- 64 values, a bijection -- with
the realms as four contiguous non-overlapping bands. Negative bases give integers unique
representations (no 0.999... ambiguity), so it is a good NAME and a good ORDER. It is a
worse DISCRIMINATOR (min/mean 0.086 vs charge's 0.494) because collapsing six dimensions to
one scalar loses the tightest pairs. Use charge for identity, negabinary for order.
"""

from __future__ import annotations

from typing import Iterable, Sequence

BITS = 6
N_OPCODES = 1 << BITS  # 64

# Top two signs select the realm. This is the ISA's own 0x00/0x10/0x20/0x30 blocking,
# read as signs rather than as a hex nibble.
REALM_NAMES = ("number", "bits", "judge", "gather")


def opcode_bits(op_id: int) -> tuple[int, ...]:
    """The six binary digits, most significant first."""
    if not 0 <= op_id < N_OPCODES:
        raise ValueError("op_id %r outside 0..%d" % (op_id, N_OPCODES - 1))
    return tuple((op_id >> (BITS - 1 - b)) & 1 for b in range(BITS))


def opcode_charge(op_id: int) -> tuple[int, ...]:
    """Lossless 6-sign charge: 0 -> -1, 1 -> +1. Distinct for all 64 opcodes."""
    return tuple(1 if b else -1 for b in opcode_bits(op_id))


def render_charge(op_id: int) -> str:
    """Charge as a sign string, e.g. 0x2A -> '+-+-+-'."""
    return "".join("+" if s > 0 else "-" for s in opcode_charge(op_id))


def opcode_number(op_id: int) -> int:
    """The COUNT: (#plus - #minus). Conserved under rotation of the charge -- this is the
    nucleus in charge_numerals' nucleus/shell model, and it is NOT unique per opcode."""
    return sum(opcode_charge(op_id))


def opcode_negabinary(op_id: int) -> int:
    """The index read in base -2. Bijective onto exactly [-42, +21].

    Even positions carry +1, +4, +16 (= +21); odd positions carry -2, -8, -32 (= -42),
    so six digits span 64 consecutive integers with no sign symbol anywhere.
    """
    return sum(b * ((-2) ** k) for k, b in enumerate(reversed(opcode_bits(op_id))))


def opcode_realm(op_id: int) -> str:
    """Realm from the top two signs -- not a lookup table, just the numbering."""
    return REALM_NAMES[op_id >> (BITS - 2)]


def charge_distance(a: Sequence[int], b: Sequence[int]) -> int:
    """L1 between two charge vectors. Always even, since every position differs by 0 or 2."""
    return sum(abs(x - y) for x, y in zip(a, b))


def signature(op_ids: Iterable[int]) -> list[float]:
    """Mean charge over a stream of opcodes -- the per-tongue signature of a program.

    Normalised by count so a 5 MB binary and a 72 KB one are comparable; raw sums scale
    with section size for reasons that have nothing to do with what the code does.
    """
    total = [0.0] * BITS
    n = 0
    for oid in op_ids:
        n += 1
        for k, s in enumerate(opcode_charge(oid)):
            total[k] += s
    return [v / n for v in total] if n else [0.0] * BITS


# --------------------------------------------------------------------------------------
# x86-64 attachment
# --------------------------------------------------------------------------------------
# Only genuine ALU work is mapped. mov/lea/push/pop/jmp/call/ret and the addressing-mode
# variants carry no ALU meaning -- they are data movement and control, and a 64-op
# arithmetic ISA has no honest slot for them. Forcing them in would inflate coverage and
# fill the signature with noise, so they are left unmapped and counted by the caller.
#
# Coverage on real binaries is therefore LOW (15-30%), and a large part of the denominator
# is not even instructions: `int3` padding between functions dominated the unmapped tally
# at 83,865 occurrences across four DLLs. Exclude padding before quoting any coverage
# figure.
X86_TO_ISA: dict[str, str] = {
    # arithmetic
    "add": "add",
    "adc": "add",
    "sub": "sub",
    "sbb": "sub",
    "imul": "mul",
    "mul": "mul",
    "idiv": "div",
    "div": "div",
    "inc": "inc",
    "dec": "dec",
    "neg": "neg",
    "cmp": "cmp",
    # logic and bit work
    "and": "and",
    "or": "or",
    "xor": "xor",
    "not": "not",
    "test": "and",
    "shl": "shl",
    "sal": "shl",
    "shr": "shr",
    "sar": "shr",
    "rol": "rotl",
    "ror": "rotr",
    "popcnt": "popcount",
    "lzcnt": "clz",
    "bsr": "clz",
    "tzcnt": "ctz",
    "bsf": "ctz",
    # scalar float
    "addsd": "add",
    "addss": "add",
    "subsd": "sub",
    "subss": "sub",
    "mulsd": "mul",
    "mulss": "mul",
    "divsd": "div",
    "divss": "div",
    "sqrtsd": "sqrt",
    "sqrtss": "sqrt",
    "minsd": "min",
    "minss": "min",
    "maxsd": "max",
    "maxss": "max",
    "roundsd": "round",
    "roundss": "round",
    "andpd": "and",
    "andps": "and",
    "orpd": "or",
    "xorpd": "xor",
    "xorps": "xor",
}

# ARM64, kept alongside because the point of an interlingua is that two machines land in
# the same place. Verified in test_opcode_charge.py: `shl shr xor and popcnt` (x86) and
# `lsl lsr eor and cnt` (ARM64) expressing the same bit-mixing kernel give an IDENTICAL
# charge signature, L1 = 0, while a different computation on the SAME machine separates.
#
# ARM64's popcount is `cnt`, NOT `clz`. An earlier version of this comment paired popcnt
# with clz and claimed L1 = 0 -- those are different operations, and they only matched
# because the trit table collides popcount/clz/ctz/sign into one code. Charge scores that
# pair 0.4 apart, which is how the overclaim was caught. Do not "restore" the old pairing.
ARM64_TO_ISA: dict[str, str] = {
    "add": "add",
    "adds": "add",
    "adc": "add",
    "sub": "sub",
    "subs": "sub",
    "mul": "mul",
    "madd": "mul",
    "sdiv": "div",
    "udiv": "div",
    "neg": "neg",
    "and": "and",
    "ands": "and",
    "orr": "or",
    "eor": "xor",
    "mvn": "not",
    "lsl": "shl",
    "lsr": "shr",
    "asr": "shr",
    "ror": "rotr",
    "cnt": "popcount",
    "clz": "clz",
    "cls": "clz",
    "cmp": "cmp",
    "ccmp": "cmp",
    "fadd": "add",
    "fsub": "sub",
    "fmul": "mul",
    "fdiv": "div",
    "fsqrt": "sqrt",
    "fmin": "min",
    "fmax": "max",
    "fabs": "abs",
    "fneg": "neg",
    "frinta": "round",
    "frintz": "floor",
}


def _name_to_id() -> dict[str, int]:
    """Mnemonic -> op_id, read from the shipped table so the two cannot drift apart."""
    from .ca_opcode_table import get_ca_opcode

    out: dict[str, int] = {}
    for oid in range(N_OPCODES):
        try:
            out[get_ca_opcode(oid).name] = oid
        except Exception:  # noqa: BLE001 - a gap in the table is not fatal here
            continue
    return out


def lift_mnemonics(mnemonics: Iterable[str], arch: str = "x86") -> tuple[list[int], list[str]]:
    """Map machine mnemonics to opcode ids. Returns (mapped_ids, unmapped_mnemonics).

    Unmapped instructions are RETURNED rather than dropped, so a caller can report real
    coverage instead of quietly presenting a filtered stream as complete.
    """
    table = ARM64_TO_ISA if arch in ("arm", "arm64", "aarch64") else X86_TO_ISA
    ids_by_name = _name_to_id()
    mapped: list[int] = []
    unmapped: list[str] = []
    for mn in mnemonics:
        op = table.get(mn)
        oid = ids_by_name.get(op) if op else None
        if oid is None:
            unmapped.append(mn)
        else:
            mapped.append(oid)
    return mapped, unmapped
