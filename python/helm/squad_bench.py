"""squad_bench: an offline, deterministic benchmark of the squad's load-bearing claims at SCALE.

The squad arc (coding_squad + squad_puzzle) ships demos; this turns the central claim -- "differentiation is
load-bearing" -- into a measured NUMBER over a distribution, with every result execution-verified. Mirrors
python/helm/public_bench.py (a dataset -> run -> verify -> score -> render pipeline), but for the geometric
squad instead of MBPP code.

Two parts, both seeded (reproducible -- the whole point) and offline ($0; no Kaggle account / network):
  1. COVERAGE benchmark -- over N random connected regions, how much of each can a DIFFERENTIATED piece-squad
     reach vs a CLONE squad (one shape)? The coverage gate's metric, at scale. Headline = the differentiation
     LIFT (diff coverage - clone coverage). Every "fully covered" verdict is independently re-checked.
  2. ENERGY benchmark -- over M random CSP boards, the Landauer cost of the squad solve: what fraction are
     conflict-free (forward-only, 0 J) vs pay for CBJ re-decisions, and the average bits erased.

HONEST: this benchmarks the GEOMETRIC differentiation + coverage + energy machinery on a synthetic
distribution; it is NOT a code-generation capability benchmark (that is public_bench/MBPP). A real online
Kaggle submission would need an account + network, which this does not fake -- it is the offline fixture.
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from python.scbe.coding_board import Board, Operator, region_must_agree  # noqa: E402
from python.scbe.coding_squad import solve_energy, solve_with_squad  # noqa: E402
from python.scbe.squad_puzzle import (  # noqa: E402
    DOMINO,
    I_TROMINO,
    L_TROMINO,
    SQUARE,
    T_TETRO,
    Piece,
    coverable_cells,
    holes,
)

Cell = Tuple[int, int]

# the two "competitors": a DIFFERENTIATED piece-squad (varied shapes; no monomino, so coverage is non-trivial)
# vs a CLONE squad (just the 2x2 frame, repeated). Coverage uses only the shapes, so the multiplicity is moot.
DIFFERENTIATED: List[Piece] = [DOMINO, L_TROMINO, I_TROMINO, T_TETRO, SQUARE]
CLONE: List[Piece] = [SQUARE]


def random_region(rng: random.Random, size: int) -> frozenset:
    """A connected polyomino of `size` cells grown by a random walk from the origin -- a 'puzzle' to cover."""
    cells = {(0, 0)}
    frontier = [(0, 0)]
    while len(cells) < size and frontier:
        r, c = rng.choice(frontier)
        nbrs = [(r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)]
        rng.shuffle(nbrs)
        grew = False
        for nb in nbrs:
            if nb not in cells:
                cells.add(nb)
                frontier.append(nb)
                grew = True
                break
        if not grew:
            frontier.remove((r, c))
    return frozenset(cells)


def coverable_fraction(region: frozenset, pieces: Sequence[Piece]) -> float:
    return len(coverable_cells(region, pieces)) / len(region) if region else 1.0


@dataclass
class CoverageRow:
    size: int
    diff_fraction: float
    clone_fraction: float
    diff_full: bool  # differentiated leaves no holes
    clone_full: bool  # clone leaves no holes


def run_coverage(n: int, seed: int, min_size: int = 4, max_size: int = 14) -> Dict[str, Any]:
    rng = random.Random(seed)
    rows: List[CoverageRow] = []
    for _ in range(n):
        region = random_region(rng, rng.randint(min_size, max_size))
        df = coverable_fraction(region, DIFFERENTIATED)
        cf = coverable_fraction(region, CLONE)
        # VERIFY a "fully covered" verdict independently: holes()==() iff fraction==1.0
        d_full = holes(region, DIFFERENTIATED) == ()
        c_full = holes(region, CLONE) == ()
        assert d_full == (df == 1.0) and c_full == (cf == 1.0), "coverage/holes disagree -- verifier bug"
        rows.append(CoverageRow(len(region), df, cf, d_full, c_full))
    diff_avg = sum(r.diff_fraction for r in rows) / n
    clone_avg = sum(r.clone_fraction for r in rows) / n
    return {
        "tasks": n,
        "diff_coverage_avg": round(diff_avg, 4),
        "clone_coverage_avg": round(clone_avg, 4),
        "coverage_lift": round(diff_avg - clone_avg, 4),  # the headline: differentiation's measured gain
        "diff_fully_covered_rate": round(sum(r.diff_full for r in rows) / n, 4),
        "clone_fully_covered_rate": round(sum(r.clone_full for r in rows) / n, 4),
    }


def random_board(rng: random.Random, n_ops: int) -> Board:
    """A random region-agreement CSP: operators share a region and must agree; some are pre-fixed. A low
    fixed-rate keeps most boards solvable, so the energy of a SOLVED board stays bounded and meaningful (an
    unsolvable board backtracks to exhaustion -- a pathological tail we report separately, not in the mean)."""
    domain = ("A", "B", "C")
    ops: List[Operator] = []
    for i in range(n_ops):
        fixed = rng.choice(domain) if rng.random() < 0.15 else None
        ops.append(Operator("o%d" % i, domain, region="r", fixed=fixed))
    return Board(ops, [region_must_agree])


def _median(xs: List[int]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    mid = len(s) // 2
    return float(s[mid]) if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def run_energy(m: int, seed: int, min_ops: int = 2, max_ops: int = 6) -> Dict[str, Any]:
    rng = random.Random(seed + 1)
    solved_overwrites: List[int] = []  # re-decisions among SOLVED boards -- the meaningful "cost of a solve"
    conflict_free = 0  # of SOLVED boards, how many were forward-only (0 J)
    solved = 0
    for _ in range(m):
        board = random_board(rng, rng.randint(min_ops, max_ops))
        res = solve_with_squad(board)
        e = res.squad_energy
        # VERIFY the metering matches a fresh, independent solve_energy over the same jumps
        assert e == solve_energy(board, res.jumps), "energy metering is not reproducible"
        if res.solved:
            solved += 1
            solved_overwrites.append(e.overwrites)
            conflict_free += 1 if e.overwrites == 0 else 0
    return {
        "tasks": m,
        "solved_rate": round(solved / m, 4),
        "conflict_free_rate_of_solved": round(conflict_free / solved, 4) if solved else 0.0,
        "median_overwrites_solved": _median(solved_overwrites),  # robust to the unsolvable backtrack tail
        "max_overwrites_solved": max(solved_overwrites) if solved_overwrites else 0,
    }


def run_bench(n: int = 200, m: int = 200, seed: int = 7) -> Dict[str, Any]:
    return {
        "benchmark": "squad-offline",
        "seed": seed,
        "coverage": run_coverage(n, seed),
        "energy": run_energy(m, seed),
    }


def render(summary: Dict[str, Any]) -> str:
    c, e = summary["coverage"], summary["energy"]
    lines = [
        "SQUAD BENCHMARK (offline, deterministic; seed=%d) -- differentiation at scale" % summary["seed"],
        "",
        "  COVERAGE (%d random regions)  differentiated vs clone piece-squad" % c["tasks"],
        "    avg cell coverage   : differentiated %.1f%%   clone %.1f%%   LIFT +%.1f%%"
        % (100 * c["diff_coverage_avg"], 100 * c["clone_coverage_avg"], 100 * c["coverage_lift"]),
        "    fully-covered rate  : differentiated %.1f%%   clone %.1f%%"
        % (100 * c["diff_fully_covered_rate"], 100 * c["clone_fully_covered_rate"]),
        "",
        "  ENERGY (%d random CSP boards)  the Landauer cost of the squad solve" % e["tasks"],
        "    solved                  : %.1f%%" % (100 * e["solved_rate"]),
        "    of solved, conflict-free: %.1f%%   (forward-only solves erase nothing -> 0 J)"
        % (100 * e["conflict_free_rate_of_solved"]),
        "    of solved, CBJ re-decisions: median %.1f, max %d   (the cost lives in the erasures)"
        % (e["median_overwrites_solved"], e["max_overwrites_solved"]),
        "",
        "  => differentiation's coverage lift and the energy distribution, measured + verified, not asserted.",
        "  (offline synthetic distribution; NOT a code-gen benchmark, and not a real online Kaggle run.)",
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] = None) -> int:
    ap = argparse.ArgumentParser(prog="squad-bench", description="offline benchmark of the squad's claims")
    ap.add_argument("--n", type=int, default=200, help="coverage tasks")
    ap.add_argument("--m", type=int, default=200, help="energy tasks")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args(argv)
    print(render(run_bench(a.n, a.m, a.seed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
