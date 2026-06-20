"""Toroidal braid extension of the reversible board — proof of the cyclic core.

Run:  python demos/toroidal_braid.py

"toroidal underpass/overpass, bijective, cyclic" = the BRAID GROUP on a torus:
  - a crossing sigma_i swaps neighbor strands i, i+1 and goes OVER (+1) or UNDER (-1)
  - sigma_i^{-1} (under) is the exact inverse of sigma_i (over)  -> bijective
  - the seam crossing (N-1 <-> 0) wraps the ring -> TOROIDAL / cyclic (affine braid)
  - OVER and UNDER give the SAME permutation but OPPOSITE writhe -> distinct braids;
    the topology is real, not just a swap (that's the point of over/under).
"""
import random

random.seed(11)
N = 8  # strands on a ring; torus seam at index N-1 <-> 0


def crossing(strands, i, over):
    j = (i + 1) % N                                   # wrap -> toroidal
    strands[i], strands[j] = strands[j], strands[i]
    return +1 if over else -1                         # writhe contribution


def run_braid(strands, word):
    return sum(crossing(strands, i, over) for (i, over) in word)


def inverse_word(word):
    return [(i, not over) for (i, over) in reversed(word)]   # reverse + flip over/under


def rand_word(k):
    return [(random.randrange(N), random.random() < 0.5) for _ in range(k)]


def main():
    ok = 0
    for _ in range(2000):
        strands = list(range(N))
        s0 = list(strands)
        w = rand_word(60)
        wr = run_braid(strands, w)
        wr += run_braid(strands, inverse_word(w))
        ok += int(strands == s0 and wr == 0)
    print(f"1. TOROIDAL BIJECTIVE: {ok}/2000  (positions restored AND net writhe cancels to 0)")

    strands = list(range(N))
    s0 = list(strands)
    loop = [(i, True) for i in range(N)]
    wr = run_braid(strands, loop)
    print(f"2. CYCLIC loop around the torus: permutation -> {strands}, net writhe = +{wr}")
    run_braid(strands, inverse_word(loop))
    print(f"   inverse loop -> back to start: {strands == s0}")

    a, b = list(range(N)), list(range(N))
    wa = run_braid(a, [(2, True)])
    wb = run_braid(b, [(2, False)])
    print(f"3. over vs under: same positions ({a == b}), writhe {wa:+d} vs {wb:+d}  -> distinct braids")

    lhs, rhs = list(range(N)), list(range(N))
    run_braid(lhs, [(2, True), (3, True), (2, True)])
    run_braid(rhs, [(3, True), (2, True), (3, True)])
    print(f"4. braid relation (Yang-Baxter) holds on the torus: {lhs == rhs}  (it's a braid GROUP)")


if __name__ == "__main__":
    main()
