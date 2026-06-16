"""
Bijective DNA coding - build from the middle, verify both ways.
===============================================================

A cube program is a strand. Because every face decoding is BIJECTIVE, a build does
not have to start at the beginning: you can drop a replication fork at any MIDPOINT
and grow both directions at once, proof-reading each base as it is laid down - the
way DNA polymerase works outward from an origin of replication.

Two ideas, made testable:

  * MIDPOINT ASSEMBLY.  Split a program at index m. Grow a LEFTWARD strand
    (positions m-1, m-2, ... 0) and a RIGHTWARD strand (m, m+1, ... n-1) at the same
    time. At every step the partial assembly must stay an exact infix of the original
    (forward proof-read) and, joined, must reconstruct it exactly (backward proof).
    This holds from EVERY midpoint, so a build is seekable.

  * REVERSE-COMPLEMENT (antiparallel strand).  Each opcode has a base-pair partner
    under an involution C (add<->sub, mul<->div, sqrt<->pow, ...). The complement
    strand is read antiparallel: rc(P)[i] = C(P[n-1-i]). Because C is an involution,
    rc(rc(P)) == P - the double strand is self-verifying: read either way, the other
    strand is forced.

"Multi strings": the SAME object is carried by 18 language strands (every emitted
face embeds the opcodes as `(0xNN)` comments, so any face decodes back to P), plus
the antiparallel complement strand, plus a bijective splitmix64 seal strand. All must
agree. If any strand disagrees, the build is tampered.
"""

from __future__ import annotations

import re
from typing import Dict, List, Sequence, Tuple

from . import polyglot as P

try:  # bijective seal (proven invertible)
    from .elastic_bijective_hash import splitmix64, splitmix64_inverse

    _HAVE_SEAL = True
except Exception:  # pragma: no cover - optional
    _HAVE_SEAL = False

# --- base pairing: an involution over the v1 scalar core (11 pairs, 22 ops) -----
_PAIRS = [
    ("add", "sub"),
    ("mul", "div"),
    ("inc", "dec"),
    ("floor", "ceil"),
    ("lt", "gt"),
    ("lte", "gte"),
    ("eq", "neq"),
    ("min", "max"),
    ("neg", "abs"),
    ("sqrt", "pow"),
    ("round", "mod"),
]
COMPLEMENT: Dict[str, str] = {}
for _a, _b in _PAIRS:
    COMPLEMENT[_a] = _b
    COMPLEMENT[_b] = _a
assert set(COMPLEMENT) == P.SCALAR_OPS, "complement must cover the whole scalar core"
assert all(COMPLEMENT[COMPLEMENT[x]] == x for x in COMPLEMENT), "C must be an involution"

# the opcode tag every face embeds — ANCHORED to end of line (emit always appends it
# as the last thing on an op line), so an identifier like `f(0x05)` mid-line can't
# inject a phantom opcode.
_HEX = re.compile(r"\(0x([0-9a-fA-F]{2})\)\s*$", re.M)


def program(*op_names: str) -> List[int]:
    """A strand: opcode names -> opcode bytes (raises on any non-core op)."""
    return P.program_bytes(*op_names)


def names(prog: Sequence[int]) -> List[str]:
    return [P.BYTE_TO_NAME[b] for b in prog]


# --- many faces, one object: decode the strand back out of ANY language ---------
def decode_from_source(src: str) -> List[int]:
    """Recover the opcode strand from emitted source, via its end-of-line `(0xNN)`
    tags. Only the 22 defined CORE ops decode — anything else (a hand-forged tag for
    a non-core or out-of-table byte) is ignored, so the decode surface equals the emit
    image. This is the bijection that makes a language face a *decoder*, not just output."""
    out = []
    for h in _HEX.findall(src):
        b = int(h, 16)
        if P.BYTE_TO_NAME.get(b) in P.SCALAR_OPS:
            out.append(b)
    return out


def faces_agree(prog: Sequence[int]) -> Dict[str, bool]:
    """Emit P to every language face and decode each back; all must equal P."""
    want = list(prog)
    return {lang: decode_from_source(P.emit(prog, lang)) == want for lang in P.languages()}


# --- reverse-complement: the antiparallel strand --------------------------------
def complement(prog: Sequence[int]) -> List[int]:
    return [P.NAME_TO_BYTE[COMPLEMENT[P.BYTE_TO_NAME[b]]] for b in prog]


def reverse_complement(prog: Sequence[int]) -> List[int]:
    return list(reversed(complement(prog)))


def base_pairs_ok(prog: Sequence[int]) -> bool:
    """Antiparallel check: position i on the strand base-pairs with n-1-i on rc."""
    rc = reverse_complement(prog)
    n = len(prog)
    return all(
        rc[n - 1 - i] == P.NAME_TO_BYTE[COMPLEMENT[P.BYTE_TO_NAME[prog[i]]]] for i in range(n)
    ) and reverse_complement(rc) == list(prog)


# --- midpoint assembly: a replication fork that grows both ways ------------------
def midpoint_assemble(prog: Sequence[int], m: int) -> Tuple[List[int], List[int], List[int]]:
    """Drop a fork at m. Grow leftward and rightward, proof-reading each step against
    the original infix. Returns (left_strand_5to3, right_strand, reconstructed)."""
    n = len(prog)
    if not 0 <= m <= n:
        raise ValueError("midpoint out of range")
    left: List[int] = []  # grown leftward: positions m-1..0
    for i in range(m - 1, -1, -1):
        left.append(prog[i])
        # proof-read: the leftward strand so far must match the original run [i, m)
        if list(reversed(left)) != list(prog[i:m]):
            raise AssertionError("leftward strand diverged at %d" % i)
    right: List[int] = []  # grown rightward: positions m..n-1
    for j in range(m, n):
        right.append(prog[j])
        if right != list(prog[m : j + 1]):
            raise AssertionError("rightward strand diverged at %d" % j)
    reconstructed = list(reversed(left)) + right  # join the fork
    return list(reversed(left)), right, reconstructed


def seekable(prog: Sequence[int]) -> bool:
    """A build is seekable iff assembly from EVERY midpoint reconstructs it exactly."""
    return all(midpoint_assemble(prog, m)[2] == list(prog) for m in range(len(prog) + 1))


# --- bijective seal strand (splitmix64) -----------------------------------------
def seal(prog: Sequence[int]) -> List[int]:
    """Scramble each (position, opcode) through the invertible 64-bit permutation."""
    return [splitmix64((i << 8) | (b & 0xFF)) for i, b in enumerate(prog)]


def unseal(words: Sequence[int]) -> List[int]:
    return [splitmix64_inverse(w) & 0xFF for w in words]


# --- full battery ---------------------------------------------------------------
def verify(op_names: Sequence[str]) -> Dict[str, object]:
    """Run every strand check on one program. Every value must be truthy/consistent."""
    prog = program(*op_names)
    faces = faces_agree(prog)
    rc = reverse_complement(prog)
    report: Dict[str, object] = {
        "program": list(op_names),
        "length": len(prog),
        "faces_total": len(faces),
        "faces_agree": sum(faces.values()),
        "all_faces_agree": all(faces.values()),
        "midpoints_total": len(prog) + 1,
        "seekable": seekable(prog),
        "rc_involution": reverse_complement(rc) == prog,
        "base_pairs_ok": base_pairs_ok(prog),
        "rc_decodes": decode_from_source(P.emit(rc, "python")) == rc,
    }
    if _HAVE_SEAL:
        report["seal_roundtrip"] = unseal(seal(prog)) == prog
    report["all_ok"] = bool(
        report["all_faces_agree"]
        and report["seekable"]
        and report["rc_involution"]
        and report["base_pairs_ok"]
        and report["rc_decodes"]
        and report.get("seal_roundtrip", True)
    )
    return report


def _demo() -> None:
    ops = ["add", "sqrt", "mul", "inc", "div", "max", "sub", "floor"]
    prog = program(*ops)
    n = len(prog)
    print("Bijective DNA coding - build from the middle, verify both ways\n")
    print("  strand 5'->3' :", " ".join(names(prog)))
    print("  complement    :", " ".join(names(complement(prog))), " (base pairs)")
    print("  rev-complement:", " ".join(names(reverse_complement(prog))), " (antiparallel)\n")

    m = n // 2
    left, right, recon = midpoint_assemble(prog, m)
    print("  replication fork at midpoint m=%d:" % m)
    print("    <-- leftward  grows:", " ".join(names(left)))
    print("    --> rightward grows:", " ".join(names(right)))
    print("    joined == original :", recon == list(prog))
    print("    seekable from ALL %d midpoints:" % (n + 1), seekable(prog), "\n")

    faces = faces_agree(prog)
    print("  multi-strand consensus (18 language faces all decode to one object):")
    print("    %d/%d faces agree" % (sum(faces.values()), len(faces)))
    print("    rc(rc(P)) == P (double strand self-verifies):", reverse_complement(reverse_complement(prog)) == prog)
    print("    antiparallel base-pairing intact            :", base_pairs_ok(prog))
    if _HAVE_SEAL:
        print("    splitmix64 seal strand round-trips          :", unseal(seal(prog)) == prog)
    print("\n  ALL STRANDS AGREE:", verify(ops)["all_ok"])


if __name__ == "__main__":
    _demo()
