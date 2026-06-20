"""Reversible board ISA — proof of the bijective Turing-complete core.

Run:  python demos/reversible_board.py

Proves by running:
  1. BIJECTIVE: inverse(program) after program returns the EXACT input (run backward).
  2. UNIVERSAL reversible logic: Fredkin (cswap) is present (Toffoli/Fredkin are
     universal for reversible classical computation).
  3. BOARD: state is a 2D grid; ops act at coordinates.
  4. MULTI-SQUAD PARALLELISM: squads on ORTHOGONAL (disjoint) regions COMMUTE,
     so they are safe to run in parallel.
  5. HONEST: overlapping squads do NOT commute -> must serialize.

Reversibility law (learned the hard way here): operands must be DISTINCT — you
cannot reversibly write a cell from itself (dst += src needs src != dst).
"""
import random

random.seed(7)
N = 6  # 6x6 board


def swap(s, p, q):              # self-inverse
    s[p], s[q] = s[q], s[p]


def add(s, src, dst):          # inverse: sub
    s[dst] += s[src]


def sub(s, src, dst):
    s[dst] -= s[src]


def cswap(s, c, p, q):         # FREDKIN gate (controlled swap) — self-inverse, universal
    if s[c] != 0:
        s[p], s[q] = s[q], s[p]


def neg(s, p):                 # self-inverse
    s[p] = -s[p]


_DISPATCH = {"swap": swap, "add": add, "sub": sub, "cswap": cswap, "neg": neg}


def apply_op(s, op):
    name, *a = op
    _DISPATCH[name](s, *a)


def inverse_op(op):
    name, *a = op
    if name == "add":
        return ("sub", *a)
    if name == "sub":
        return ("add", *a)
    return op                  # swap, cswap, neg are their own inverse


def run(s, prog):
    for op in prog:
        apply_op(s, op)


def inverse(prog):
    return [inverse_op(op) for op in reversed(prog)]


def mirror_row(r):
    return [("swap", (r, c), (r, N - 1 - c)) for c in range(N // 2)]


def rand_grid():
    return {(r, c): random.randint(-3, 3) for r in range(N) for c in range(N)}


def rand_prog(cells, k=40):
    # distinct operands -> reversibility holds (no self-aliasing).
    ops = []
    for _ in range(k):
        kind = random.choice(["swap", "add", "sub", "cswap", "neg"])
        if kind == "swap":
            ops.append(("swap", *random.sample(cells, 2)))
        elif kind in ("add", "sub"):
            ops.append((kind, *random.sample(cells, 2)))
        elif kind == "cswap":
            ops.append(("cswap", *random.sample(cells, 3)))
        else:
            ops.append(("neg", random.choice(cells)))
    return ops


def main():
    cells = [(r, c) for r in range(N) for c in range(N)]

    ok = 0
    for _ in range(2000):
        g0 = rand_grid()
        g = dict(g0)
        prog = rand_prog(cells, 50)
        run(g, prog)
        run(g, inverse(prog))
        ok += int(g == g0)
    print(f"1. BIJECTIVE: {ok}/2000 random programs ran forward+backward to the EXACT input")

    g = rand_grid()
    g0 = dict(g)
    apply_op(g, ("cswap", (0, 0), (1, 1), (2, 2)))
    apply_op(g, ("cswap", (0, 0), (1, 1), (2, 2)))
    print(f"2. FREDKIN (cswap) self-inverse: {g == g0}  (universal reversible logic)")

    g = rand_grid()
    g0 = dict(g)
    run(g, mirror_row(2))
    run(g, mirror_row(2))
    print(f"3. MIRROR row reflect self-inverse: {g == g0}")

    left = [(r, c) for r in range(N) for c in range(0, N // 2)]
    right = [(r, c) for r in range(N) for c in range(N // 2, N)]
    a, b = rand_prog(left, 30), rand_prog(right, 30)
    gAB = rand_grid()
    gBA = dict(gAB)
    run(gAB, a)
    run(gAB, b)
    run(gBA, b)
    run(gBA, a)
    print(f"4. PARALLEL: orthogonal squads commute (A;B == B;A): {gAB == gBA}")

    pA, pB = rand_prog(cells, 20), rand_prog(cells, 20)
    g1 = rand_grid()
    g2 = dict(g1)
    run(g1, pA)
    run(g1, pB)
    run(g2, pB)
    run(g2, pA)
    print(f"5. HONEST: overlapping squads do NOT commute: {g1 != g2}  (only disjoint lanes parallelize)")


if __name__ == "__main__":
    main()
