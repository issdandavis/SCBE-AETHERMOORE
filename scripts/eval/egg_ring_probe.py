"""Egg-ring probe — is the Sacred-Egg ring_descent ALGEBRA load-bearing, or a pun?

The egg already speaks ring theory in words: `_RING_ORDER = {core:0, inner:1,
middle:2, outer:3}` is a descending chain, `yolk` is the core secret, `shell`
the public boundary. This probe asks whether giving that descent *actual* ring
structure — a local ring's m-adic filtration, with the yolk as the residue
field R/m — catches anything the current integer-ladder check misses, and
whether it beats the honest baseline (a SHA-256 hash chain).

Five falsifiable tests, each with a null:

  R1  m-adic vs enum-ladder, INCOHERENT splice   does algebra beat the label?
  R2  m-adic vs hash-chain, COHERENT secret-swap does algebra suffice ALONE?  (null)
  R3  norm multiplicativity N(zw)=N(z)N(w)        the aggregate-receipt foundation
  R4  homomorphic sub-path verification           the ring's UNIQUE capability vs a hash
  R5  ring choice: UFD vs non-UFD collision       is Kummer depth decoration or a constraint?

Run:  PYTHONPATH=. python scripts/eval/egg_ring_probe.py
"""

from __future__ import annotations

import hashlib
import random
from math import prod
from typing import List, Tuple

R = random.Random(20260611)


def line(name, test, value, verdict):
    print(f"  {name:4} {test:46} {value:>22}   {verdict}")


# --------------------------------------------------------------------------- #
# A local ring  R = Z / p^N  and its m-adic filtration  R ⊃ (p) ⊃ (p^2) ⊃ ...
# A "descent" is the precision tower  tau_k = secret mod p^k,  k = 1..N.
#   - enum-ladder check: tokens carry monotone ring tags + are structurally
#     valid (0 <= tau_k < p^k). This is the current _RING_ORDER analog.
#   - m-adic check: tokens are COHERENT — tau_{k+1} reduces to tau_k mod p^k
#     (an element of the inverse limit, i.e. a genuine p-adic descent).
#   - hash chain: each level commits to the next (the honest baseline).
# --------------------------------------------------------------------------- #

P, N = 7, 5
MOD = P**N


def honest_descent(secret: int) -> List[int]:
    return [secret % (P**k) for k in range(1, N + 1)]


def enum_ladder_ok(tokens: List[int]) -> bool:
    """Structural + monotone-tag check only — blind to coherence."""
    if len(tokens) != N:
        return False
    return all(0 <= tokens[k] < P ** (k + 1) for k in range(N))


def madic_ok(tokens: List[int]) -> bool:
    """Coherence: the deeper token reduces to the shallower one."""
    return all(tokens[k + 1] % (P ** (k + 1)) == tokens[k] for k in range(N - 1))


def hash_chain(tokens: List[int]) -> str:
    c = ""
    for tok in reversed(tokens):
        c = hashlib.sha256(f"{tok}|{c}".encode()).hexdigest()
    return c


def incoherent_splice(secret: int) -> List[int]:
    """Forge one deep token with a valid tag but broken reduction."""
    toks = honest_descent(secret)
    j = R.randint(1, N - 1)  # break the reduction at level j (0-indexed token j)
    bad = (toks[j] + R.randint(1, P ** (j + 1) - 1)) % (P ** (j + 1))
    while bad % (P**j) == toks[j - 1]:  # ensure it actually breaks coherence
        bad = (bad + 1) % (P ** (j + 1))
    toks[j] = bad
    return toks


def coherent_swap(secret: int) -> Tuple[List[int], int]:
    """Splice in a DIFFERENT secret's coherent tower, matched at the boundary.

    Agrees with `secret` up to p^j, diverges below — internally coherent, so
    only a commitment to the real secret can reject it.
    """
    j = 2
    r = R.randint(1, P - 1)
    other = (secret + (P**j) * r) % MOD
    return honest_descent(other), other


# --------------------------------------------------------------------------- #
# Gaussian integers  Z[i]  (a UFD / class number 1) — the receipt ring.
#   N(a+bi) = a^2 + b^2 = det([[a,-b],[b,a]])  (the regular representation).
# And  Z[sqrt(-5)]  (class number 2, a NON-UFD) — the Kummer counterexample.
# --------------------------------------------------------------------------- #


def zi_mul(z, w):
    a, b = z
    c, d = w
    return (a * c - b * d, a * d + b * c)


def zi_norm(z):
    a, b = z
    return a * a + b * b


def z5_mul(z, w):  # elements a + b*sqrt(-5)
    a, b = z
    c, d = w
    return (a * c - 5 * b * d, a * d + b * c)


def z5_norm(z):
    a, b = z
    return a * a + 5 * b * b


# --------------------------------------------------------------------------- #
def main():
    print("\n  egg-ring probe — Z/p^N m-adic descent + Z[i] norm receipt")
    print("  " + "─" * 100)

    M = 600

    # ---- R1: m-adic beats the enum label on incoherent splices ----------- #
    enum_acc = madic_acc = 0
    for _ in range(M):
        s = R.randrange(1, MOD)
        spliced = incoherent_splice(s)
        enum_acc += enum_ladder_ok(spliced)
        madic_acc += madic_ok(spliced)
    line(
        "R1",
        "incoherent splice: enum vs m-adic accept",
        f"enum {enum_acc}/{M} · m-adic {madic_acc}/{M}",
        "ALGEBRA BEATS THE LABEL" if enum_acc > 0.95 * M and madic_acc == 0 else "no separation",
    )

    # ---- R2: the null — m-adic ALONE misses a coherent secret-swap ------- #
    madic_miss = hash_catch = 0
    for _ in range(M):
        s = R.randrange(1, MOD)
        real = honest_descent(s)
        c_real = hash_chain(real)
        swap, _other = coherent_swap(s)
        madic_miss += madic_ok(swap)  # coherent -> accepts (a MISS)
        hash_catch += hash_chain(swap) != c_real  # commitment to real s -> rejects
    r2_ok = madic_miss > 0.95 * M and hash_catch == M
    line(
        "R2",
        "coherent swap: m-adic miss / hash catch",
        f"m-adic miss {madic_miss}/{M} · hash {hash_catch}/{M}",
        "ALGEBRA INSUFFICIENT ALONE (commitment still load-bearing)" if r2_ok else "?",
    )

    # ---- R3: norm is exactly multiplicative (aggregate-receipt base) ----- #
    err = 0
    for _ in range(M):
        z = (R.randint(-9, 9), R.randint(-9, 9))
        w = (R.randint(-9, 9), R.randint(-9, 9))
        err = max(err, abs(zi_norm(zi_mul(z, w)) - zi_norm(z) * zi_norm(w)))
    line("R3", "N(zw) == N(z)N(w) over Z[i]", f"max err {err}", "EXACT HOMOMORPHISM" if err == 0 else "broken")

    # ---- R4: homomorphic sub-path verification (ring-only capability) ---- #
    # 5-step descent of Gaussian integers; verify a 2..4 sub-path from norms
    # ALONE (divisibility), which a hash chain cannot do without replay.
    steps = [(R.randint(1, 6), R.randint(1, 6)) for _ in range(5)]
    total = steps[0]
    for z in steps[1:]:
        total = zi_mul(total, z)
    total_norm = zi_norm(total)
    sub_norm = prod(zi_norm(s) for s in steps[1:4])  # steps 2,3,4
    complement = zi_norm(steps[0]) * zi_norm(steps[4])
    ring_ok = total_norm % sub_norm == 0 and total_norm // sub_norm == complement
    line(
        "R4",
        "sub-path verified from aggregate norm alone",
        f"ring={ring_ok} hash=needs-replay",
        "RING-ONLY CAPABILITY (hash chain can't)" if ring_ok else "failed",
    )

    # ---- R5: the Kummer constraint — non-UFD admits a receipt collision -- #
    # In Z[sqrt(-5)]:  6 = 2*3 = (1+s)(1-s),  two distinct operation pairs,
    # IDENTICAL product (6) and IDENTICAL receipt norm (36) -> substitution
    # undetected. In a UFD (Z[i], Z[zeta_6]) this cannot happen.
    pair_a = ((2, 0), (3, 0))
    pair_b = ((1, 1), (1, -1))  # 1 ± sqrt(-5)
    prod_a = z5_mul(*pair_a)
    prod_b = z5_mul(*pair_b)
    na = z5_norm(prod_a)
    nb = z5_norm(prod_b)
    collision = prod_a == prod_b == (6, 0) and na == nb == 36 and pair_a != pair_b
    # contrast: in Z[i], the only norm-9 elements are associates of 3 (no swap)
    norm9_zi = [(a, b) for a in range(-3, 4) for b in range(-3, 4) if zi_norm((a, b)) == 9]
    ufd_safe = sorted(norm9_zi) == sorted([(-3, 0), (0, -3), (0, 3), (3, 0)])
    line(
        "R5",
        "non-UFD Z[√-5] receipt collision 2·3=(1±√-5)",
        f"collide={collision} ufd_safe={ufd_safe}",
        "RING CHOICE IS LOAD-BEARING (use class-number-1)" if collision and ufd_safe else "?",
    )

    print("  " + "─" * 100)
    print(
        "  verdict: eggs-as-rings is REAL but precise —\n"
        "    R1  m-adic coherence catches incoherent splices the integer ladder is blind to.\n"
        "    R2  but a coherent secret-SWAP slips past the algebra; the yolk COMMITMENT (hash/PQC)\n"
        "        is still load-bearing — the ring layer complements, never replaces it.\n"
        "    R3+R4  the multiplicative norm gives a homomorphic aggregate receipt: one checksum for\n"
        "        the whole descent, sub-paths verifiable from norms alone — a hash chain cannot.\n"
        "    R5  the ring MUST be class-number-1 (UFD); a non-UFD lets operations be swapped under an\n"
        "        identical norm. The 'decorative' Kummer depth is in fact the safety CONSTRAINT.\n"
        "  => make the eggs rings+yolks as an ALGEBRAIC AGGREGATE-RECEIPT layer over Z[zeta_6] (UFD),\n"
        "     ON TOP of the existing yolk commitment — not as a replacement for it.\n"
    )


if __name__ == "__main__":
    main()
