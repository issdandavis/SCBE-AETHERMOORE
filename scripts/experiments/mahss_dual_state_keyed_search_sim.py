"""Dual-state keyed search: multigrid vs mirror_resonance over A x B.

Two candidate spaces A and B share a coupling matrix M (the "key"). The
score of a pair (a, b) is

    amplitude(a, b) = exp(alpha * ||a|| * ||b|| * cos(M @ a, b))

This is a bilinear-form-weighted resonance: both side norms multiply, the
coupling rotates A's vector into B's frame, and the cosine measures
alignment after rotation. A diamond pair has both high norms AND a
post-rotation alignment match -- neither side alone reveals it. The matrix
M plays the role of a key in a Diffie-Hellman-style exchange: knowledge
of M is required to predict which (a, b) pair scores highest, and brute
force is O(N_A * N_B).

Compares four methods at the same effective budget:
  - brute_pair:          all N_A * N_B pairs (reference)
  - tang_cross:          top-K by ||a||^2, top-K by ||b||^2, K^2 pairs evaluated
  - multigrid_cross:     two-level on A then on B, fine pass on top-K-each
                         only -> O(K * N_B + K * K_B) evaluations
  - resonance_cross:     compute amplitude over the joint outer product in
                         one batched op, take top-K_pair pairs

Diamonds are planted as matched pairs (a_diamond_i, b_diamond_i) with
b_diamond_i pointing along M @ a_diamond_i. Decoys are planted as
high-norm-misaligned-after-rotation entries on either side.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA_VERSION = "scbe_mahss_dual_state_keyed_search_sim_v1"
DIM = 32


@dataclass(frozen=True)
class DualStateSpec:
    """Generator spec for a dual-state keyed-search landscape."""

    n_a: int = 80
    n_b: int = 80
    n_diamond_pairs: int = 4
    diamond_norm: float = 6.0
    stone_norm: float = 1.0
    decoy_norm: float = 6.0
    n_decoys_per_side: int = 12
    diamond_alignment: float = 0.92
    seed: int = 19


def _random_unit(rng: np.random.Generator, dim: int) -> np.ndarray:
    v = rng.standard_normal(dim)
    return v / (np.linalg.norm(v) + 1e-12)


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-12
    return matrix / norms


def build_landscape(spec: DualStateSpec) -> dict[str, object]:
    """Return query-free dual-state landscape with planted matched pairs."""

    rng = np.random.default_rng(spec.seed)
    # Coupling key M: a fixed orthogonal-ish rotation built from QR.
    raw = rng.standard_normal((DIM, DIM))
    q, _ = np.linalg.qr(raw)
    M = q

    A = np.empty((spec.n_a, DIM), dtype=float)
    B = np.empty((spec.n_b, DIM), dtype=float)

    diamond_a = rng.choice(spec.n_a, size=spec.n_diamond_pairs, replace=False)
    diamond_b = rng.choice(spec.n_b, size=spec.n_diamond_pairs, replace=False)
    decoy_a = rng.choice(
        list(set(range(spec.n_a)) - set(int(i) for i in diamond_a)),
        size=spec.n_decoys_per_side,
        replace=False,
    )
    decoy_b = rng.choice(
        list(set(range(spec.n_b)) - set(int(i) for i in diamond_b)),
        size=spec.n_decoys_per_side,
        replace=False,
    )

    diamond_a_set = set(int(i) for i in diamond_a)
    diamond_b_set = set(int(i) for i in diamond_b)
    decoy_a_set = set(int(i) for i in decoy_a)
    decoy_b_set = set(int(i) for i in decoy_b)

    diamond_directions = [_random_unit(rng, DIM) for _ in range(spec.n_diamond_pairs)]

    pair_index_a = {int(idx): k for k, idx in enumerate(diamond_a)}
    pair_index_b = {int(idx): k for k, idx in enumerate(diamond_b)}

    def _aligned_with(direction: np.ndarray, alignment: float) -> np.ndarray:
        perp = rng.standard_normal(DIM)
        perp -= perp.dot(direction) * direction
        perp /= np.linalg.norm(perp) + 1e-12
        return alignment * direction + math.sqrt(max(0.0, 1.0 - alignment**2)) * perp

    for i in range(spec.n_a):
        if i in diamond_a_set:
            k = pair_index_a[i]
            direction = _aligned_with(diamond_directions[k], spec.diamond_alignment)
            A[i] = spec.diamond_norm * direction / (np.linalg.norm(direction) + 1e-12)
        elif i in decoy_a_set:
            v = _random_unit(rng, DIM)
            v = v - sum(v.dot(d) * d for d in diamond_directions) / max(1, spec.n_diamond_pairs)
            v /= np.linalg.norm(v) + 1e-12
            A[i] = spec.decoy_norm * v
        else:
            A[i] = spec.stone_norm * _random_unit(rng, DIM)

    for j in range(spec.n_b):
        if j in diamond_b_set:
            k = pair_index_b[j]
            target = M @ diamond_directions[k]
            target /= np.linalg.norm(target) + 1e-12
            direction = _aligned_with(target, spec.diamond_alignment)
            B[j] = spec.diamond_norm * direction / (np.linalg.norm(direction) + 1e-12)
        elif j in decoy_b_set:
            v = _random_unit(rng, DIM)
            B[j] = spec.decoy_norm * v
        else:
            B[j] = spec.stone_norm * _random_unit(rng, DIM)

    pair_set = set()
    for k in range(spec.n_diamond_pairs):
        pair_set.add((int(diamond_a[k]), int(diamond_b[k])))

    return {
        "A": A,
        "B": B,
        "M": M,
        "diamond_pairs": pair_set,
        "diamond_a": np.asarray(sorted(diamond_a_set)),
        "diamond_b": np.asarray(sorted(diamond_b_set)),
    }


def amplitude_matrix(A: np.ndarray, B: np.ndarray, M: np.ndarray, *, alpha: float = 1.0) -> np.ndarray:
    """exp(alpha * ||a|| * ||b|| * cos(M@a, b)) for all pairs (i, j)."""

    a_norms = np.linalg.norm(A, axis=1)
    b_norms = np.linalg.norm(B, axis=1)
    rotated = A @ M.T
    rotated_norms = np.linalg.norm(rotated, axis=1, keepdims=True) + 1e-12
    rotated_unit = rotated / rotated_norms
    b_unit = _normalize_rows(B)
    cos = rotated_unit @ b_unit.T
    log_amp = alpha * np.outer(a_norms, b_norms) * cos
    return log_amp


def select_brute_pair(
    A: np.ndarray, B: np.ndarray, M: np.ndarray, *, budget_pairs: int, alpha: float = 1.0
) -> tuple[list[tuple[int, int]], int]:
    log_amp = amplitude_matrix(A, B, M, alpha=alpha)
    flat = np.argsort(log_amp.ravel())[::-1][:budget_pairs]
    pairs = [(int(idx // log_amp.shape[1]), int(idx % log_amp.shape[1])) for idx in flat]
    return pairs, A.shape[0] * B.shape[0]


def select_tang_cross(
    A: np.ndarray, B: np.ndarray, M: np.ndarray, *, k_per_side: int, budget_pairs: int, alpha: float = 1.0
) -> tuple[list[tuple[int, int]], int]:
    a_norms = np.linalg.norm(A, axis=1) ** 2
    b_norms = np.linalg.norm(B, axis=1) ** 2
    a_idx = np.argsort(a_norms)[::-1][:k_per_side]
    b_idx = np.argsort(b_norms)[::-1][:k_per_side]
    sub = amplitude_matrix(A[a_idx], B[b_idx], M, alpha=alpha)
    flat = np.argsort(sub.ravel())[::-1][:budget_pairs]
    pairs: list[tuple[int, int]] = []
    cols = sub.shape[1]
    for idx in flat:
        ai = int(a_idx[int(idx // cols)])
        bj = int(b_idx[int(idx % cols)])
        pairs.append((ai, bj))
    evaluations = k_per_side * k_per_side
    return pairs, evaluations


def select_resonance_cross(
    A: np.ndarray,
    B: np.ndarray,
    M: np.ndarray,
    *,
    budget_pairs: int,
    alpha: float = 1.0,
) -> tuple[list[tuple[int, int]], int]:
    log_amp = amplitude_matrix(A, B, M, alpha=alpha)
    flat = np.argsort(log_amp.ravel())[::-1][:budget_pairs]
    pairs = [(int(idx // log_amp.shape[1]), int(idx % log_amp.shape[1])) for idx in flat]
    # Resonance ranks the SAME log_amp matrix as brute force, but the
    # "evaluations" cost is one batched outer product, not N_A * N_B
    # individual scoring calls. Cost in matmul-flops: O((N_A + N_B) * d^2)
    # for the rotation + O(N_A * N_B) for the cosine matrix; we report
    # the cosine-matrix size as the evaluation count for direct comparison.
    evaluations = log_amp.size
    return pairs, evaluations


def select_resonance_cross_lowrank(
    A: np.ndarray,
    B: np.ndarray,
    M: np.ndarray,
    *,
    rank: int,
    budget_pairs: int,
    alpha: float = 1.0,
) -> tuple[list[tuple[int, int]], int]:
    """Rank-r SVD-truncated coupling, then resonance over the joint space.

    If the coupling matrix M has effective rank r << d, we can replace
    M with its rank-r SVD M_r = U_r diag(s_r) V_r^T. The amplitude matrix
    becomes a rank-r outer product structure that costs O((N_A + N_B) * d * r)
    instead of O((N_A + N_B) * d^2). This empirically tests the claim that
    "cryptographic strength of the coupling = search-method efficiency
    frontier": low-rank M (weak key) admits sub-quadratic in d, full-rank
    random M (strong key) does not.
    """

    if rank <= 0:
        raise ValueError("rank must be > 0")
    U, s, Vt = np.linalg.svd(M, full_matrices=False)
    rank_eff = min(rank, len(s))
    M_r = (U[:, :rank_eff] * s[:rank_eff]) @ Vt[:rank_eff, :]
    log_amp = amplitude_matrix(A, B, M_r, alpha=alpha)
    flat = np.argsort(log_amp.ravel())[::-1][:budget_pairs]
    pairs = [(int(idx // log_amp.shape[1]), int(idx % log_amp.shape[1])) for idx in flat]
    # Cost: O((N_A + N_B) * d * r) for the projection + O(N_A * N_B) for
    # the cosine matrix on the rank-r-rotated vectors. We report the cosine-
    # matrix size (the largest term) for direct comparison with full-rank.
    evaluations = log_amp.size
    return pairs, evaluations


def select_disagreement_probe_cross(
    A: np.ndarray,
    B: np.ndarray,
    M: np.ndarray,
    *,
    method_a_pairs: Sequence[tuple[int, int]],
    method_b_pairs: Sequence[tuple[int, int]],
    budget_pairs: int,
    alpha: float = 1.0,
) -> tuple[list[tuple[int, int]], int]:
    """Non-linear "negative-between-negatives" selector.

    Two source methods produce two pair sets P_a and P_b. Their null spaces
    in the BUDGET-RECOVERED region are the symmetric difference:

        D = P_a ⊕ P_b = (P_a \\ P_b) ∪ (P_b \\ P_a)

    These are pairs each method picked but the other did not -- the
    DISAGREEMENT region. The "negative between the negatives" is the
    geometric midpoint between a disagreeing pair from P_a and one from
    P_b in the joint sketch space, mapped back to candidate pairs that
    sit closest to that midpoint. Those midpoints are the pairs neither
    method nominated despite both half-nominating: pure non-linear probe
    candidates that neither single-method ranking surfaces.

    Concretely:
      1. For every (a_i, b_j) in P_a \\ P_b and every (a_k, b_l) in P_b \\ P_a,
         compute the midpoint sketch (a_i + a_k)/2 in A and (b_j + b_l)/2 in B.
      2. For each midpoint, find the candidate (a*, b*) closest to it (by
         Euclidean distance in the sketch space).
      3. Score those probe pairs with the actual amplitude function.
      4. Return the top-budget_pairs.
    """

    P_a = set(method_a_pairs)
    P_b = set(method_b_pairs)
    only_a = list(P_a - P_b)
    only_b = list(P_b - P_a)
    if not only_a or not only_b:
        return list(P_a | P_b)[:budget_pairs], 0

    probes: set[tuple[int, int]] = set()
    for ai, bj in only_a:
        for ak, bl in only_b:
            mid_a = 0.5 * (A[ai] + A[ak])
            mid_b = 0.5 * (B[bj] + B[bl])
            a_dists = np.linalg.norm(A - mid_a, axis=1)
            b_dists = np.linalg.norm(B - mid_b, axis=1)
            a_star = int(np.argmin(a_dists))
            b_star = int(np.argmin(b_dists))
            probes.add((a_star, b_star))

    union = list(P_a | P_b)
    candidates: list[tuple[int, int]] = list(probes | set(union))
    log_amp = amplitude_matrix(A, B, M, alpha=alpha)
    candidates.sort(key=lambda pair: float(log_amp[pair[0], pair[1]]), reverse=True)
    selected = candidates[:budget_pairs]
    evaluations = len(candidates)
    return selected, evaluations


def select_multigrid_cross(
    A: np.ndarray,
    B: np.ndarray,
    M: np.ndarray,
    *,
    coarse_per_side: int,
    fine_top_k: int,
    budget_pairs: int,
    alpha: float = 1.0,
) -> tuple[list[tuple[int, int]], int]:
    """Two-level multigrid on each side, then full pairwise on top-K of each.

    Coarse: sample coarse_per_side rows from each side uniformly and score
    against a single representative on the other side (the highest-norm
    representative -- a cheap proxy). Promote the top fine_top_k from each
    side. Fine: full amplitude over fine_top_k x fine_top_k subgrid.
    """

    a_norms = np.linalg.norm(A, axis=1)
    b_norms = np.linalg.norm(B, axis=1)
    rep_a = int(np.argmax(a_norms))
    rep_b = int(np.argmax(b_norms))

    coarse_a_idx = np.linspace(0, A.shape[0] - 1, coarse_per_side, dtype=int)
    coarse_b_idx = np.linspace(0, B.shape[0] - 1, coarse_per_side, dtype=int)

    A_coarse = A[coarse_a_idx]
    B_coarse = B[coarse_b_idx]
    coarse_amp_a = amplitude_matrix(A_coarse, B[rep_b : rep_b + 1], M, alpha=alpha).ravel()
    coarse_amp_b = amplitude_matrix(A[rep_a : rep_a + 1], B_coarse, M, alpha=alpha).ravel()

    top_a_local = np.argsort(coarse_amp_a)[::-1][:fine_top_k]
    top_b_local = np.argsort(coarse_amp_b)[::-1][:fine_top_k]
    top_a_global = coarse_a_idx[top_a_local]
    top_b_global = coarse_b_idx[top_b_local]

    fine_amp = amplitude_matrix(A[top_a_global], B[top_b_global], M, alpha=alpha)
    flat = np.argsort(fine_amp.ravel())[::-1][:budget_pairs]
    cols = fine_amp.shape[1]
    pairs: list[tuple[int, int]] = []
    for idx in flat:
        ai = int(top_a_global[int(idx // cols)])
        bj = int(top_b_global[int(idx % cols)])
        pairs.append((ai, bj))
    evaluations = (
        coarse_per_side  # coarse_amp_a vs rep_b
        + coarse_per_side  # coarse_amp_b vs rep_a
        + fine_top_k * fine_top_k
    )
    return pairs, evaluations


def evaluate_selection(
    pairs: list[tuple[int, int]],
    landscape: dict[str, object],
    log_amp_full: np.ndarray,
) -> dict[str, float]:
    diamond_pairs = landscape["diamond_pairs"]
    assert isinstance(diamond_pairs, set)
    selected_set = set(pairs)
    diamonds_caught = len(selected_set & diamond_pairs)
    if pairs:
        best_in_selection = float(max(log_amp_full[a, b] for a, b in pairs))
    else:
        best_in_selection = float(log_amp_full.min())
    best_overall = float(log_amp_full.max())
    return {
        "best_in_selection": round(best_in_selection, 6),
        "best_overall": round(best_overall, 6),
        "regret_log_amp": round(best_overall - best_in_selection, 6),
        "diamond_recall": diamonds_caught / max(1, len(diamond_pairs)),
        "diamonds_caught": diamonds_caught,
        "n_diamond_pairs": len(diamond_pairs),
        "selection_size": len(selected_set),
    }


def run_compare(spec: DualStateSpec, *, budget_pairs: int = 8, alpha: float = 1.0) -> dict[str, object]:
    landscape = build_landscape(spec)
    A = landscape["A"]
    B = landscape["B"]
    M = landscape["M"]
    assert isinstance(A, np.ndarray) and isinstance(B, np.ndarray) and isinstance(M, np.ndarray)
    log_amp_full = amplitude_matrix(A, B, M, alpha=alpha)

    runs: dict[str, tuple[list[tuple[int, int]], int]] = {
        "brute_pair": select_brute_pair(A, B, M, budget_pairs=budget_pairs, alpha=alpha),
        "tang_cross_k10": select_tang_cross(
            A, B, M, k_per_side=10, budget_pairs=budget_pairs, alpha=alpha
        ),
        "tang_cross_k20": select_tang_cross(
            A, B, M, k_per_side=20, budget_pairs=budget_pairs, alpha=alpha
        ),
        "resonance_cross_a1": select_resonance_cross(
            A, B, M, budget_pairs=budget_pairs, alpha=alpha
        ),
        "multigrid_cross_c20_k6": select_multigrid_cross(
            A, B, M, coarse_per_side=20, fine_top_k=6, budget_pairs=budget_pairs, alpha=alpha
        ),
        "multigrid_cross_c30_k10": select_multigrid_cross(
            A, B, M, coarse_per_side=30, fine_top_k=10, budget_pairs=budget_pairs, alpha=alpha
        ),
    }

    rank_sweep = [1, 2, 4, 8, 16, A.shape[1]]
    for rank in rank_sweep:
        if rank > A.shape[1]:
            continue
        runs[f"resonance_lowrank_r{rank}"] = select_resonance_cross_lowrank(
            A, B, M, rank=rank, budget_pairs=budget_pairs, alpha=alpha
        )

    # Disagreement probes: pair two methods that have COMPLEMENTARY partial
    # truth so their XOR midpoints actually land near diamonds. "Double
    # negative makes positive" works only when each negative carries partial
    # signal in different directions.
    multigrid_pairs = runs["multigrid_cross_c30_k10"][0]
    tang20_pairs = runs["tang_cross_k20"][0]
    lowrank4_pairs = runs["resonance_lowrank_r4"][0]
    lowrank8_pairs = runs["resonance_lowrank_r8"][0]

    runs["disagreement_tang_vs_multigrid"] = select_disagreement_probe_cross(
        A, B, M,
        method_a_pairs=tang20_pairs,
        method_b_pairs=multigrid_pairs,
        budget_pairs=budget_pairs,
        alpha=alpha,
    )
    runs["disagreement_lowrank_seam"] = select_disagreement_probe_cross(
        A, B, M,
        method_a_pairs=lowrank4_pairs,
        method_b_pairs=lowrank8_pairs,
        budget_pairs=budget_pairs,
        alpha=alpha,
    )

    summary: dict[str, dict[str, object]] = {}
    for name, (pairs, evaluations) in runs.items():
        row = evaluate_selection(pairs, landscape, log_amp_full)
        row["evaluations"] = int(evaluations)
        summary[name] = row

    return {
        "schema_version": SCHEMA_VERSION,
        "spec": {
            "n_a": spec.n_a,
            "n_b": spec.n_b,
            "n_diamond_pairs": spec.n_diamond_pairs,
            "diamond_norm": spec.diamond_norm,
            "stone_norm": spec.stone_norm,
            "decoy_norm": spec.decoy_norm,
            "n_decoys_per_side": spec.n_decoys_per_side,
            "diamond_alignment": spec.diamond_alignment,
            "seed": spec.seed,
        },
        "alpha": alpha,
        "budget_pairs": budget_pairs,
        "joint_pool_size": int(A.shape[0] * B.shape[0]),
        "summary": summary,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-a", type=int, default=80)
    parser.add_argument("--n-b", type=int, default=80)
    parser.add_argument("--n-diamond-pairs", type=int, default=4)
    parser.add_argument("--n-decoys-per-side", type=int, default=12)
    parser.add_argument("--diamond-norm", type=float, default=6.0)
    parser.add_argument("--stone-norm", type=float, default=1.0)
    parser.add_argument("--decoy-norm", type=float, default=6.0)
    parser.add_argument("--diamond-alignment", type=float, default=0.92)
    parser.add_argument("--budget-pairs", type=int, default=8)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=19)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/mahss_dual_state/dual_state_keyed_search_sim_v1.json"),
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    spec = DualStateSpec(
        n_a=args.n_a,
        n_b=args.n_b,
        n_diamond_pairs=args.n_diamond_pairs,
        diamond_norm=args.diamond_norm,
        stone_norm=args.stone_norm,
        decoy_norm=args.decoy_norm,
        n_decoys_per_side=args.n_decoys_per_side,
        diamond_alignment=args.diamond_alignment,
        seed=args.seed,
    )
    report = run_compare(spec, budget_pairs=args.budget_pairs, alpha=args.alpha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"wrote {args.output}")
        print(
            f"landscape: n_a={spec.n_a} n_b={spec.n_b} "
            f"diamond_pairs={spec.n_diamond_pairs} budget={args.budget_pairs} "
            f"joint_pool={report['joint_pool_size']}"
        )
        for name, row in report["summary"].items():
            print(
                f"  {name}: evals={row['evaluations']:>6} "
                f"recall={row['diamond_recall']:.2f} ({row['diamonds_caught']}/{spec.n_diamond_pairs}) "
                f"regret_log_amp={row['regret_log_amp']:.4f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
