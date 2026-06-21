"""squad_bench: an offline, deterministic benchmark of the squad's claims -- HONEST instruments only.

A prior version headlined a "+41.6% differentiation LIFT" from a coverage-UNION metric. A self-audit showed
that number is an artifact of pitting the differentiated set against the WORST-reaching single shape (the 2x2
SQUARE): coverage is a UNION over pieces, so any all-reaching piece saturates it -- a DOMINO clone gives a
0.0 lift. Coverage-union is the WRONG instrument for differentiation. This version reports only honest ones:

  1. REACH -- the single-shape reach deficit: a fact about ONE shape's footprint on connected regions, with
     the strawman exposed in-line (the 2x2 SQUARE leaves a gap; a DOMINO leaves none). This is NOT a
     differentiation result; it is one shape's reachability.
  2. TILING -- the RIGHT instrument: at MATCHED total area, can a CLONE piece-set tile what a DIFFERENTIATED
     set tiles? On a parity-obstructed (mutilated) region a domino-only roster CANNOT tile, while
     domino + 2 monominoes (same area, shape-diverse) CAN. Every tiling is re-verified. This is where
     shape-diversity is genuinely load-bearing (the same claim squad_puzzle's matched-area tests prove).
  3. ENERGY -- honest disclosure: with forward-checking, a SOLVED board of these CSP classes is forward-only
     BY CONSTRUCTION (0 J), a tautology not a measurement (verified across region_must_agree AND
     all_distinct_in_region). The dissipating cost appears only on UNSOLVABLE boards (the solver flailing);
     it is reported there, labeled as such.

Offline, seeded ($0; no Kaggle account/network). NOT a code-generation benchmark; NOT a real online Kaggle run.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from python.scbe.coding_board import Board, Operator, all_distinct_in_region  # noqa: E402
from python.scbe.coding_squad import solve_with_squad  # noqa: E402
from python.scbe.squad_puzzle import DOMINO, MONO, SQUARE, assemble, coverable_cells, rect  # noqa: E402

Cell = Any


def random_region(rng: random.Random, size: int) -> frozenset:
    """A connected polyomino of `size` cells grown by a random walk from the origin."""
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


def _coverable_fraction(region: frozenset, piece) -> float:
    return len(coverable_cells(region, [piece])) / len(region) if region else 1.0


def run_reach(n: int, seed: int, min_size: int = 4, max_size: int = 14) -> Dict[str, Any]:
    """How much of a connected region a SINGLE shape's footprint reaches. The 2x2 SQUARE starves on thin/
    branchy regions; a DOMINO reaches (almost) everything. The DOMINO==SQUARE gap is the strawman exposed:
    coverage-union does NOT measure differentiation -- one all-reaching shape saturates it."""
    rng = random.Random(seed)
    sq_total = 0.0
    dom_total = 0.0
    for _ in range(n):
        region = random_region(rng, rng.randint(min_size, max_size))
        sq_total += _coverable_fraction(region, SQUARE)
        dom_total += _coverable_fraction(region, DOMINO)
    return {
        "tasks": n,
        "square_reach_avg": round(sq_total / n, 4),  # the 2x2 frame starves on 1-wide seams
        "domino_reach_avg": round(dom_total / n, 4),  # a domino reaches nearly all cells
        "square_deficit": round(1.0 - sq_total / n, 4),  # a single-shape reachability fact (NOT differentiation)
        "domino_deficit": round(1.0 - dom_total / n, 4),  # ~0: the strawman -- union saturates with any reacher
    }


def _mutilated(h: int, w: int) -> frozenset:
    """An h x w rectangle minus two opposite (same-colour) corners -> even area, colour-parity imbalanced,
    so a domino-only roster cannot tile it (the mutilated-chessboard obstruction)."""
    return frozenset(c for c in rect(h, w) if c not in {(0, 0), (h - 1, w - 1)})


def run_tiling() -> Dict[str, Any]:
    """The RIGHT instrument for differentiation: at matched area, a CLONE (domino-only) set vs a DIFFERENTIATED
    (domino + 2 monomino) set on parity-obstructed regions. Small fixed sizes (proving the clone CANNOT tile is
    an exhaustive search, so this stays small). Every differentiated tiling is independently re-verified."""
    rows = []
    for h, w in [(2, 4), (4, 4)]:
        reg = _mutilated(h, w)
        a = len(reg)
        clone = assemble(reg, [DOMINO] * (a // 2))
        diff = assemble(reg, [DOMINO] * ((a - 2) // 2) + [MONO, MONO])
        rows.append(
            {
                "region": "%dx%d-mutilated" % (h, w),
                "area": a,
                "clone_domino_tiles": clone.solved,
                "diff_tiles": diff.solved,
                "diff_verified": diff.verify(reg) if diff.solved else False,
            }
        )
    return {
        "cases": rows,
        "clone_fails_all": all(not r["clone_domino_tiles"] for r in rows),
        "diff_tiles_all_verified": all(r["diff_tiles"] and r["diff_verified"] for r in rows),
    }


def _random_board(rng: random.Random, n_ops: int) -> Board:
    domain = tuple("XYZW"[: rng.randint(2, 4)])
    ops = [Operator("o%d" % i, domain, region="r") for i in range(n_ops)]
    return Board(ops, [all_distinct_in_region])


def run_energy(m: int, seed: int, min_ops: int = 3, max_ops: int = 6) -> Dict[str, Any]:
    """Honest disclosure, not a measurement. Forward-checking prunes each unassigned operator to values
    consistent with the assigned ones BEFORE any conflict, so a SOLVED board never backjumps -> 0 J is
    structural. Backjumps (and thus energy) occur ONLY on UNSOLVABLE boards. We report both, labeled."""
    rng = random.Random(seed + 1)
    solved = 0
    solved_with_energy = 0  # MUST stay 0 -- the tautology we are disclosing
    unsolved = 0
    unsolved_overwrites: List[int] = []
    for _ in range(m):
        board = _random_board(rng, rng.randint(min_ops, max_ops))
        res = solve_with_squad(board)
        e = res.squad_energy
        # genuine independent re-derivation of the bits from the jump list (not the same object)
        valid = [j for j in res.jumps if 0 <= j < len(board.operators)]
        assert e.overwrites == len(valid), "overwrites must equal the valid backjump count"
        if res.solved:
            solved += 1
            if e.overwrites > 0:
                solved_with_energy += 1
        else:
            unsolved += 1
            unsolved_overwrites.append(e.overwrites)
    avg_unsolved = sum(unsolved_overwrites) / unsolved if unsolved else 0.0
    return {
        "tasks": m,
        "solved_rate": round(solved / m, 4),
        "solved_with_nonzero_energy": solved_with_energy,  # 0 by construction (forward-checking) -> a tautology
        "energy_is_structural_not_measured": solved_with_energy == 0,
        "unsolved_avg_overwrites": round(avg_unsolved, 2),  # the only place energy appears: the solver flailing
    }


def run_bench(reach_n: int = 200, energy_m: int = 120, seed: int = 7) -> Dict[str, Any]:
    return {
        "benchmark": "squad-offline",
        "seed": seed,
        "reach": run_reach(reach_n, seed),
        "tiling": run_tiling(),
        "energy": run_energy(energy_m, seed),
    }


def render(summary: Dict[str, Any]) -> str:
    rc, ti, en = summary["reach"], summary["tiling"], summary["energy"]
    lines = [
        "SQUAD BENCHMARK (offline, deterministic; seed=%d) -- honest instruments only" % summary["seed"],
        "",
        "  REACH (%d random regions) -- a SINGLE shape's footprint, NOT differentiation" % rc["tasks"],
        "    2x2 SQUARE reaches %.1f%% of cells (deficit %.1f%% on thin/branchy regions)"
        % (100 * rc["square_reach_avg"], 100 * rc["square_deficit"]),
        "    DOMINO    reaches %.1f%% (deficit %.1f%%) -- the strawman: union saturates, so coverage != diversity"
        % (100 * rc["domino_reach_avg"], 100 * rc["domino_deficit"]),
        "",
        "  TILING (matched area) -- the RIGHT instrument: shape-diversity defeats a parity wall",
        "    clone (domino-only) tiles a mutilated region : %s   (every case)" % (not ti["clone_fails_all"]),
        "    diff (domino+2 monomino) tiles + re-verifies : %s   (every case)" % ti["diff_tiles_all_verified"],
        "",
        "  ENERGY (%d random CSP boards) -- DISCLOSURE, not a measurement" % en["tasks"],
        "    solved boards with nonzero energy : %d  (0 by construction: forward-checking -> solved is forward-only)"
        % en["solved_with_nonzero_energy"],
        "    energy appears only on UNSOLVABLE boards (avg %.2f backjumps -- the solver flailing)"
        % en["unsolved_avg_overwrites"],
        "",
        "  => coverage-union does NOT measure differentiation (domino strawman); exact TILING does. Energy among",
        "     solved boards is a forward-checking tautology, not an empirical Landauer distribution.",
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] = None) -> int:
    ap = argparse.ArgumentParser(prog="squad-bench", description="offline benchmark of the squad's claims")
    ap.add_argument("--n", type=int, default=200, help="reach tasks")
    ap.add_argument("--m", type=int, default=120, help="energy tasks")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args(argv)
    print(render(run_bench(a.n, a.m, a.seed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
