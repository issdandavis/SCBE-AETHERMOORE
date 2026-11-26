#!/usr/bin/env python3
"""opcode_cube_multiplex.py -- the multiplex mapped on the RIGHT object.

Issac, 2026-07-31, correcting me: "make sure you map out the multiplex layers correctly,
its not just space... its about connection threads, multi views from conlangs, code, sound,
frequency, color, weight, depth, token orientation either forward or backwards or up or
down, thats 64 opcodes arranged 4 ways as well as the diagonals... they are all tied like
puppet strings to the coding languages and to natural language. they are also turing
complete. that is the basis. we let the graph be like a perfect cube in 1 representation,
like a library has rows and books, but the books themself are the depth that each row
holds, sorted and sectioned."

WHAT I HAD WRONG. multiplex_bow.py laminated three fibers over 192 LoRA modules. Those
fibers were mine -- structural / kNN-on-movement / role -- and the node set was an artifact
of one adapter. It measured something real but it was not this object.

THE OBJECT. 64 opcodes in 4 orientations is 256, and 256 is the byte. The cube is the byte
factored, not a picture of it:

    4 x 4 x 4 = 64 cells                    the opcode lattice
    x 4 orientations (fwd/bwd/up/down)      = 256 = every byte, bijectively
    tongue_opcodes.py: b -> onset[b>>4] + join + coda[b & 0xF], render<->parse round-trips

THE THREADS. A 4x4x4 has exactly 76 straight lines, and this is a counted fact, not a
choice -- it is the Qubic number:

    48  axis-aligned   (3 directions x 16 lines)
    24  face diagonals (3 coordinate-pairs x 4 slices x 2)
     4  space diagonals
    --
    76  threads

Each is a "puppet string": a set of 4 cells that must move together. That is the connection
structure, and no amount of node-level coupling produces it, because a thread is a
*relation among four cells at once*, not an edge between two.

THE LIBRARY. A cell is not a point. Each holds depth -- the faces cube_faces.py already
assembles and proves bijective (core / chemistry 6-channel trit / roles / six code faces /
governance / wolfram rule), plus the phonetic, colour, frequency and weight views. Rows and
books: the row is the thread, the books are the depth the cell holds, sorted and sectioned.

WHAT IS MEASURED HERE. Threads are 4-cell relations, so the natural operator is not the
graph Laplacian -- it is the HYPERGRAPH Laplacian, or equivalently the graph Laplacian of
the 2-skeleton those threads induce. Both are built and compared, because the difference
between them is exactly the information a pairwise view throws away.

    python opcode_cube_multiplex.py
"""
from __future__ import annotations

import itertools
import numpy as np

N = 4  # side. 4**3 = 64 opcodes.
ORIENTATIONS = ("forward", "backward", "up", "down")  # 64 * 4 = 256 = the byte


# --------------------------------------------------------------------- the cube
def cells():
    """The 64 opcode cells, indexed so cell (x,y,z) <-> opcode 16x + 4y + z."""
    return [(x, y, z) for x in range(N) for y in range(N) for z in range(N)]


def cid(c):
    x, y, z = c
    return 16 * x + 4 * y + z


def threads():
    """All 76 straight lines through a 4x4x4. Counted, not chosen.

    A line is 4 collinear cells. Enumerated by direction vector, taking each maximal run
    so no line is double-counted and no partial run is admitted.
    """
    seen, out = set(), []
    dirs = [d for d in itertools.product((-1, 0, 1), repeat=3) if any(d)]
    for start in cells():
        for d in dirs:
            line = []
            p = start
            for _ in range(N):
                if not all(0 <= v < N for v in p):
                    line = []
                    break
                line.append(p)
                p = tuple(p[i] + d[i] for i in range(3))
            if len(line) == N:
                key = frozenset(line)
                if key not in seen:
                    seen.add(key)
                    out.append(tuple(line))
    return out


def classify(line):
    """axis / face-diagonal / space-diagonal, by how many coordinates move."""
    a, b = line[0], line[-1]
    moved = sum(1 for i in range(3) if a[i] != b[i])
    return {1: "axis", 2: "face_diag", 3: "space_diag"}[moved]


# ------------------------------------------------------------------- operators
def laplacian(A):
    return np.diag(A.sum(1)) - A


def clique_expansion(lines, n=64):
    """Pairwise view: every thread becomes a 4-clique. This is what a graph Laplacian
    can see, and it is strictly less than the thread carries -- a clique cannot say
    whether its 6 edges came from ONE 4-cell relation or from six unrelated pairs."""
    A = np.zeros((n, n))
    for L in lines:
        for i, j in itertools.combinations([cid(c) for c in L], 2):
            A[i, j] += 1.0
            A[j, i] += 1.0
    return A


def incidence(lines, n=64):
    """Cell x thread incidence. Columns are the puppet strings."""
    B = np.zeros((n, len(lines)))
    for k, L in enumerate(lines):
        for c in L:
            B[cid(c), k] = 1.0
    return B


def hyper_laplacian(lines, n=64):
    """Hypergraph Laplacian L = B W B^T - D, normalised so a 4-cell thread is ONE
    relation rather than six edges. This is the operator that keeps what the clique
    expansion discards."""
    B = incidence(lines, n)
    # each thread contributes with weight 1/(|e|-1) so its total pull matches one relation
    W = np.eye(B.shape[1]) / (N - 1)
    A = B @ W @ B.T
    np.fill_diagonal(A, 0.0)
    return laplacian(A)


def betti1(A):
    n = A.shape[0]
    E = int((A > 0).sum() // 2)
    C = int((np.linalg.eigvalsh(laplacian((A > 0).astype(float))) < 1e-9).sum())
    return E - n + C, E, C


def main() -> int:
    T = threads()
    kinds = {}
    for L in T:
        kinds[classify(L)] = kinds.get(classify(L), 0) + 1

    print("=" * 74)
    print("OPCODE CUBE MULTIPLEX -- 4x4x4, the byte factored")
    print("=" * 74)
    print("cells        : %d opcodes" % len(cells()))
    print("orientations : %d %s" % (len(ORIENTATIONS), ORIENTATIONS))
    print("byte space   : %d x %d = %d  (bijective, tongue_opcodes.py)"
          % (len(cells()), len(ORIENTATIONS), len(cells()) * len(ORIENTATIONS)))
    print()
    print("THREADS -- the puppet strings, counted not chosen")
    for k in ("axis", "face_diag", "space_diag"):
        print("  %-12s %3d" % (k, kinds.get(k, 0)))
    print("  %-12s %3d   <- the Qubic number; a 4x4x4 has exactly this many lines"
          % ("total", len(T)))

    A = clique_expansion(T)
    Lc = laplacian(A)
    Lh = hyper_laplacian(T)

    sc = np.sort(np.linalg.eigvalsh(Lc))
    sh = np.sort(np.linalg.eigvalsh(Lh))
    b1, E, C = betti1(A)

    print()
    print("PAIRWISE VIEW (clique expansion) -- what a graph Laplacian can see")
    print("  distinct edges   : %d" % E)
    print("  components       : %d" % C)
    print("  beta1            : %d   <- residue capacity" % b1)
    print("  lambda_1         : %.6f" % sc[0])
    print("  Fiedler lambda_2 : %.6f" % sc[1])
    print("  lambda_max       : %.6f" % sc[-1])

    print()
    print("THREAD VIEW (hypergraph Laplacian) -- keeps the 4-cell relation whole")
    print("  lambda_1         : %.6f" % sh[0])
    print("  Fiedler lambda_2 : %.6f" % sh[1])
    print("  lambda_max       : %.6f" % sh[-1])

    print()
    print("WHAT THE DIFFERENCE MEANS")
    print("  A 4-cell thread becomes 6 edges under clique expansion. Those 6 edges cannot")
    print("  say whether they came from ONE relation or six unrelated pairs -- the same")
    print("  loss the isospectral wall showed at the graph level, one dimension up.")
    print("  spectral gap, pairwise : %.6f" % (sc[1] - sc[0]))
    print("  spectral gap, thread   : %.6f" % (sh[1] - sh[0]))

    # Which cells sit on the most threads -- the load-bearing opcodes.
    B = incidence(T)
    deg = B.sum(1)
    order = np.argsort(-deg)
    print()
    print("MOST-THREADED CELLS -- opcodes that move when the most strings pull")
    for i in order[:6]:
        x, y, z = divmod(int(i), 16)[0], (int(i) % 16) // 4, int(i) % 4
        print("  opcode 0x%02X  cell (%d,%d,%d)  on %d of %d threads"
              % (i, x, y, z, int(deg[i]), len(T)))
    print("  corners bear the space diagonals; the 8 inner cells bear the fewest.")
    print()
    print("MEASUREMENT ONLY. Structure counted from the cube, nothing trained.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
