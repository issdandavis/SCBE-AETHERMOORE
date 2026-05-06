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
  - polyhedral_edge:     keyed sign-facet edge walk over rotated A and B
                         cells, then exact scoring of the frontier
  - phase_angle:         keyed angular phase matching over rotated A and B
                         using phi-spaced cyclic offsets
  - constructive_oscillation:
                         repeated phase/sign compatibility passes whose
                         constructive votes define the exact-scored frontier
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
PHI = (1.0 + math.sqrt(5.0)) / 2.0


def _platonic_solid(name: str) -> tuple[np.ndarray, list[tuple[int, int]]]:
    """Return (unit-sphere vertices, edges) for a named Platonic solid.

    Edges are the pairs of vertices at the minimum nonzero pairwise
    distance on the unit sphere. The polyhedron acts as a bounded-
    diameter compass over the joint A x B direction space; each edge
    walked between vertices counts as one "turning" in the search.

    Diameters (max graph-distance between any two vertices):
      tetrahedron  (4 v,  6 e)  diameter 1
      octahedron   (6 v, 12 e)  diameter 2
      cube         (8 v, 12 e)  diameter 3
      icosahedron (12 v, 30 e)  diameter 3
      dodecahedron(20 v, 30 e)  diameter 5
    """

    name = name.lower()
    if name == "tetrahedron":
        verts = np.array(
            [[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]],
            dtype=float,
        )
    elif name == "octahedron":
        verts = np.array(
            [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]],
            dtype=float,
        )
    elif name == "cube":
        verts = np.array(
            [
                [s1, s2, s3]
                for s1 in (-1.0, 1.0)
                for s2 in (-1.0, 1.0)
                for s3 in (-1.0, 1.0)
            ],
            dtype=float,
        )
    elif name == "icosahedron":
        rows: list[list[float]] = []
        for s1 in (-1.0, 1.0):
            for s2 in (-1.0, 1.0):
                rows.append([0.0, s1, s2 * PHI])
                rows.append([s1, s2 * PHI, 0.0])
                rows.append([s2 * PHI, 0.0, s1])
        verts = np.array(rows, dtype=float)
    elif name == "dodecahedron":
        rows = []
        for s1 in (-1.0, 1.0):
            for s2 in (-1.0, 1.0):
                for s3 in (-1.0, 1.0):
                    rows.append([s1, s2, s3])
        inv_phi = 1.0 / PHI
        for s1 in (-1.0, 1.0):
            for s2 in (-1.0, 1.0):
                rows.append([0.0, s1 * inv_phi, s2 * PHI])
                rows.append([s1 * inv_phi, s2 * PHI, 0.0])
                rows.append([s2 * PHI, 0.0, s1 * inv_phi])
        verts = np.array(rows, dtype=float)
    else:
        raise ValueError(f"unknown polyhedron: {name}")

    norms = np.linalg.norm(verts, axis=1, keepdims=True)
    verts = verts / (norms + 1e-12)

    n = verts.shape[0]
    dists = np.linalg.norm(verts[:, None, :] - verts[None, :, :], axis=2)
    iu = np.triu_indices(n, k=1)
    nonzero = dists[iu]
    if nonzero.size == 0:
        return verts, []
    min_d = float(nonzero.min())
    edges: list[tuple[int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            if abs(float(dists[i, j]) - min_d) < 1e-6:
                edges.append((i, j))
    return verts, edges


def _polyhedron_diameter(n_vertices: int, edges: list[tuple[int, int]]) -> int:
    """BFS-based graph diameter for a polyhedron's edge skeleton."""

    if n_vertices <= 1:
        return 0
    adj: list[list[int]] = [[] for _ in range(n_vertices)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    diameter = 0
    for start in range(n_vertices):
        dist = [-1] * n_vertices
        dist[start] = 0
        queue = [start]
        while queue:
            u = queue.pop(0)
            for nb in adj[u]:
                if dist[nb] == -1:
                    dist[nb] = dist[u] + 1
                    diameter = max(diameter, dist[nb])
                    queue.append(nb)
    return diameter


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
    key_mode: str = "random_orthogonal"


def _random_unit(rng: np.random.Generator, dim: int) -> np.ndarray:
    v = rng.standard_normal(dim)
    return v / (np.linalg.norm(v) + 1e-12)


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-12
    return matrix / norms


def _hadamard_matrix(order: int) -> np.ndarray:
    """Return normalized Sylvester-Hadamard matrix for power-of-two order."""

    if order <= 0 or order & (order - 1):
        raise ValueError("Hadamard key requires a positive power-of-two dimension")
    H = np.asarray([[1.0]])
    while H.shape[0] < order:
        H = np.block([[H, H], [H, -H]])
    return H / math.sqrt(float(order))


def _key_matrix(rng: np.random.Generator, mode: str) -> np.ndarray:
    """Build deterministic orthogonal coupling key for a landscape mode."""

    if mode == "random_orthogonal":
        raw = rng.standard_normal((DIM, DIM))
        q, _ = np.linalg.qr(raw)
        return q
    if mode == "identity":
        return np.eye(DIM, dtype=float)
    if mode == "signed_permutation":
        perm = rng.permutation(DIM)
        signs = rng.choice(np.asarray([-1.0, 1.0]), size=DIM)
        M = np.zeros((DIM, DIM), dtype=float)
        M[np.arange(DIM), perm] = signs
        return M
    if mode == "hadamard":
        signs = rng.choice(np.asarray([-1.0, 1.0]), size=DIM)
        return np.diag(signs) @ _hadamard_matrix(DIM)
    if mode == "block_rotation":
        M = np.eye(DIM, dtype=float)
        for start in range(0, DIM - 1, 2):
            theta = float(rng.uniform(0.1, math.pi - 0.1))
            c = math.cos(theta)
            s = math.sin(theta)
            M[start : start + 2, start : start + 2] = np.asarray([[c, -s], [s, c]])
        return M
    raise ValueError(
        "key_mode must be one of: random_orthogonal, identity, signed_permutation, hadamard, block_rotation"
    )


def build_landscape(spec: DualStateSpec) -> dict[str, object]:
    """Return query-free dual-state landscape with planted matched pairs."""

    rng = np.random.default_rng(spec.seed)
    M = _key_matrix(rng, spec.key_mode)

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


def _signatures(matrix: np.ndarray) -> np.ndarray:
    """Return binary facet signatures for a coordinate-hyperplane polytope."""

    return matrix >= 0.0


def _hamming(signature: np.ndarray, signatures: np.ndarray) -> np.ndarray:
    return np.count_nonzero(signatures != signature, axis=1)


def _phase_angles(matrix: np.ndarray) -> np.ndarray:
    """Return a stable cyclic phase angle for each row.

    The angle is computed from paired even/odd coordinates. It is a compact
    phase sketch, not a replacement for the final amplitude score.
    """

    even = matrix[:, 0::2].sum(axis=1)
    odd = matrix[:, 1::2].sum(axis=1)
    return np.mod(np.arctan2(odd, even), 2.0 * math.pi)


def _cyclic_angle_distance(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    delta = np.abs(a - b)
    return np.minimum(delta, 2.0 * math.pi - delta)


def select_phase_angle_cross(
    A: np.ndarray,
    B: np.ndarray,
    M: np.ndarray,
    *,
    seed_count: int,
    offsets: int,
    angle_width: int,
    budget_pairs: int,
    alpha: float = 1.0,
) -> tuple[list[tuple[int, int]], int, dict[str, object]]:
    """Select pairs by keyed angular phase alignment.

    Once ``M`` maps A into B's frame, sign-facet edges are not the only
    relation available. This selector sketches each row into a cyclic phase
    angle, then tests self-similar phi-spaced phase offsets. It scores only
    the resulting angular frontier with the true amplitude function.
    """

    if seed_count <= 0:
        raise ValueError("seed_count must be > 0")
    if offsets <= 0:
        raise ValueError("offsets must be > 0")
    if angle_width <= 0:
        raise ValueError("angle_width must be > 0")

    a_norms = np.linalg.norm(A, axis=1)
    b_norms = np.linalg.norm(B, axis=1)
    rotated = A @ M.T
    a_phase = _phase_angles(rotated)
    b_phase = _phase_angles(B)
    phase_offsets = np.mod(
        np.arange(offsets, dtype=float) * (2.0 * math.pi / (PHI**2)),
        2.0 * math.pi,
    )

    pairs: set[tuple[int, int]] = set()
    a_seeds = np.argsort(a_norms)[::-1][: min(seed_count, A.shape[0])]
    b_seeds = np.argsort(b_norms)[::-1][: min(seed_count, B.shape[0])]

    for ai in a_seeds:
        for offset in phase_offsets:
            target = np.mod(a_phase[int(ai)] + offset, 2.0 * math.pi)
            distances = _cyclic_angle_distance(target, b_phase)
            order = np.lexsort((-b_norms, distances))
            for bj in order[: min(angle_width, B.shape[0])]:
                pairs.add((int(ai), int(bj)))

    for bj in b_seeds:
        for offset in phase_offsets:
            target = np.mod(b_phase[int(bj)] - offset, 2.0 * math.pi)
            distances = _cyclic_angle_distance(target, a_phase)
            order = np.lexsort((-a_norms, distances))
            for ai in order[: min(angle_width, A.shape[0])]:
                pairs.add((int(ai), int(bj)))

    candidates = sorted(pairs)
    log_amp = amplitude_matrix(A, B, M, alpha=alpha)
    candidates.sort(key=lambda pair: float(log_amp[pair[0], pair[1]]), reverse=True)
    selected = candidates[:budget_pairs]
    meta = {
        "seed_count": int(seed_count),
        "offsets": int(offsets),
        "angle_width": int(angle_width),
        "phase_offsets": [round(float(v), 6) for v in phase_offsets],
        "frontier_size": int(len(candidates)),
    }
    return selected, len(candidates), meta


def select_constructive_oscillation_cross(
    A: np.ndarray,
    B: np.ndarray,
    M: np.ndarray,
    *,
    seed_count: int,
    oscillations: int,
    beam_width: int,
    budget_pairs: int,
    alpha: float = 1.0,
) -> tuple[list[tuple[int, int]], int, dict[str, object]]:
    """Run repeated phase/sign passes and keep constructive intersections.

    This treats search as a short oscillatory run through the mapped solution
    space. Each oscillation applies a phi-spaced phase shift, then combines
    cyclic phase closeness with sign-facet compatibility. Pairs that repeatedly
    line up across passes get votes; only the voted frontier is exact-scored.

    The vote is an inverse-Lyapunov derivative surrogate. Let mismatch energy
    be ``E = phase_distance/pi + hamming_distance/d`` and
    ``L = 1 / (eps + E)``. A pair receives constructive mass when the current
    oscillation improves L relative to the previous phase pass for that pair.
    """

    if seed_count <= 0:
        raise ValueError("seed_count must be > 0")
    if oscillations <= 0:
        raise ValueError("oscillations must be > 0")
    if beam_width <= 0:
        raise ValueError("beam_width must be > 0")

    a_norms = np.linalg.norm(A, axis=1)
    b_norms = np.linalg.norm(B, axis=1)
    rotated = A @ M.T
    rotated_unit = _normalize_rows(rotated)
    b_unit = _normalize_rows(B)
    a_phase = _phase_angles(rotated)
    b_phase = _phase_angles(B)
    a_signatures = _signatures(rotated_unit)
    b_signatures = _signatures(b_unit)
    phase_offsets = np.mod(
        np.arange(oscillations, dtype=float) * (2.0 * math.pi / (PHI**2)),
        2.0 * math.pi,
    )

    a_seeds = np.argsort(a_norms)[::-1][: min(seed_count, A.shape[0])]
    b_seeds = np.argsort(b_norms)[::-1][: min(seed_count, B.shape[0])]
    votes: dict[tuple[int, int], float] = {}
    previous_l: dict[tuple[int, int], float] = {}
    eps = 1e-6

    def _add_vote(pair: tuple[int, int], phase_distance: float, hamming_distance: float) -> None:
        energy = (float(phase_distance) / math.pi) + (float(hamming_distance) / max(1, A.shape[1]))
        inverse_l = 1.0 / (eps + energy)
        derivative = inverse_l - previous_l.get(pair, 0.0)
        previous_l[pair] = max(previous_l.get(pair, 0.0), inverse_l)
        votes[pair] = votes.get(pair, 0.0) + max(0.0, derivative)

    for ai in a_seeds:
        ai_int = int(ai)
        hamming = _hamming(a_signatures[ai_int], b_signatures)
        for offset in phase_offsets:
            target = np.mod(a_phase[ai_int] + offset, 2.0 * math.pi)
            phase_distances = _cyclic_angle_distance(target, b_phase)
            score = phase_distances + (hamming / max(1, A.shape[1]))
            order = np.lexsort((-b_norms, score))
            for bj in order[: min(beam_width, B.shape[0])]:
                bj_int = int(bj)
                _add_vote((ai_int, bj_int), float(phase_distances[bj_int]), float(hamming[bj_int]))

    for bj in b_seeds:
        bj_int = int(bj)
        hamming = _hamming(b_signatures[bj_int], a_signatures)
        for offset in phase_offsets:
            target = np.mod(b_phase[bj_int] - offset, 2.0 * math.pi)
            phase_distances = _cyclic_angle_distance(target, a_phase)
            score = phase_distances + (hamming / max(1, A.shape[1]))
            order = np.lexsort((-a_norms, score))
            for ai in order[: min(beam_width, A.shape[0])]:
                ai_int = int(ai)
                _add_vote((ai_int, bj_int), float(phase_distances[ai_int]), float(hamming[ai_int]))

    candidates = sorted(votes)
    log_amp = amplitude_matrix(A, B, M, alpha=alpha)
    candidates.sort(
        key=lambda pair: (float(log_amp[pair[0], pair[1]]), votes[pair]),
        reverse=True,
    )
    selected = candidates[:budget_pairs]
    meta = {
        "seed_count": int(seed_count),
        "oscillations": int(oscillations),
        "beam_width": int(beam_width),
        "phase_offsets": [round(float(v), 6) for v in phase_offsets],
        "frontier_size": int(len(candidates)),
        "max_vote": round(float(max(votes.values()) if votes else 0.0), 6),
        "score_model": "inverse_lyapunov_derivative",
    }
    return selected, len(candidates), meta


def select_polyhedral_edge_walk_cross(
    A: np.ndarray,
    B: np.ndarray,
    M: np.ndarray,
    *,
    seed_count: int,
    edge_width: int,
    budget_pairs: int,
    edge_metric: str = "hamming",
    alpha: float = 1.0,
) -> tuple[list[tuple[int, int]], int]:
    """Walk keyed polyhedral sign-facet edges before exact pair scoring.

    This is a direct selector, not a source-plus-probe reranker. It maps
    ``M @ a`` and ``b`` into the same sign-facet cell system, starts from
    high-energy seeds on each side, then scores pairs on low-Hamming-distance
    cells. It is intended to test whether keyed geometry can expose paired
    solutions without evaluating the full outer product.
    """

    if seed_count <= 0:
        raise ValueError("seed_count must be > 0")
    if edge_width <= 0:
        raise ValueError("edge_width must be > 0")
    if edge_metric not in {"hamming", "phase", "hybrid", "weighted_hybrid"}:
        raise ValueError("edge_metric must be hamming, phase, hybrid, or weighted_hybrid")

    a_norms = np.linalg.norm(A, axis=1)
    b_norms = np.linalg.norm(B, axis=1)
    rotated = A @ M.T
    rotated_unit = _normalize_rows(rotated)
    b_unit = _normalize_rows(B)
    a_signatures = _signatures(rotated_unit)
    b_signatures = _signatures(b_unit)
    a_phase = _phase_angles(rotated)
    b_phase = _phase_angles(B)

    def _metric_for_a(ai: int) -> np.ndarray:
        hamming = _hamming(a_signatures[ai], b_signatures).astype(float)
        phase = _cyclic_angle_distance(a_phase[ai], b_phase) / math.pi
        if edge_metric == "hamming":
            return hamming
        if edge_metric == "phase":
            return phase
        if edge_metric == "hybrid":
            return (hamming / max(1, A.shape[1])) + phase
        return (0.7 * hamming / max(1, A.shape[1])) + (0.3 * phase)

    def _metric_for_b(bj: int) -> np.ndarray:
        hamming = _hamming(b_signatures[bj], a_signatures).astype(float)
        phase = _cyclic_angle_distance(b_phase[bj], a_phase) / math.pi
        if edge_metric == "hamming":
            return hamming
        if edge_metric == "phase":
            return phase
        if edge_metric == "hybrid":
            return (hamming / max(1, A.shape[1])) + phase
        return (0.7 * hamming / max(1, A.shape[1])) + (0.3 * phase)

    a_seeds = np.argsort(a_norms)[::-1][: min(seed_count, A.shape[0])]
    b_seeds = np.argsort(b_norms)[::-1][: min(seed_count, B.shape[0])]
    pairs: set[tuple[int, int]] = set()

    for ai in a_seeds:
        distances = _metric_for_a(int(ai))
        order = np.lexsort((-b_norms, distances))
        for bj in order[: min(edge_width, B.shape[0])]:
            pairs.add((int(ai), int(bj)))

    for bj in b_seeds:
        distances = _metric_for_b(int(bj))
        order = np.lexsort((-a_norms, distances))
        for ai in order[: min(edge_width, A.shape[0])]:
            pairs.add((int(ai), int(bj)))

    candidates = sorted(pairs)
    log_amp = amplitude_matrix(A, B, M, alpha=alpha)
    candidates.sort(key=lambda pair: float(log_amp[pair[0], pair[1]]), reverse=True)
    selected = candidates[:budget_pairs]
    return selected, len(candidates)


def select_polyhedral_edge_gear_cross(
    A: np.ndarray,
    B: np.ndarray,
    M: np.ndarray,
    *,
    seed_count: int,
    fast_width: int,
    torque_width: int,
    shift_threshold: int,
    budget_pairs: int,
    fast_metric: str = "hamming",
    torque_metric: str = "hamming",
    alpha: float = 1.0,
) -> tuple[list[tuple[int, int]], int, dict[str, object]]:
    """Adaptive edge-walk gear shift.

    Small boards use a narrow frontier for speed. Once the board crosses a
    threshold, the selector shifts to a wider frontier ("more torque") to
    reduce negative ingestion space: the missed-good region caused by an
    overly tight local neighborhood.
    """

    if shift_threshold <= 0:
        raise ValueError("shift_threshold must be > 0")
    joint_pool_size = int(A.shape[0] * B.shape[0])
    gear = "fast" if joint_pool_size <= shift_threshold else "torque"
    edge_width = fast_width if gear == "fast" else torque_width
    edge_metric = fast_metric if gear == "fast" else torque_metric
    pairs, evaluations = select_polyhedral_edge_walk_cross(
        A,
        B,
        M,
        seed_count=seed_count,
        edge_width=edge_width,
        edge_metric=edge_metric,
        budget_pairs=budget_pairs,
        alpha=alpha,
    )
    meta = {
        "gear": gear,
        "seed_count": int(seed_count),
        "edge_width": int(edge_width),
        "edge_metric": edge_metric,
        "fast_width": int(fast_width),
        "torque_width": int(torque_width),
        "fast_metric": fast_metric,
        "torque_metric": torque_metric,
        "shift_threshold": int(shift_threshold),
        "joint_pool_size": joint_pool_size,
    }
    return pairs, evaluations, meta


def _tangent_basis_pair(direction: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Deterministic two-vector tangent basis orthogonal to ``direction``."""

    d = np.asarray(direction, dtype=float)
    d = d / (np.linalg.norm(d) + 1e-12)
    dim = d.shape[0]
    order = np.argsort(np.abs(d))
    e1 = np.zeros(dim, dtype=float)
    e1[int(order[0])] = 1.0
    u = e1 - float(e1 @ d) * d
    u = u / (np.linalg.norm(u) + 1e-12)
    e2 = np.zeros(dim, dtype=float)
    for idx in order[1:]:
        e2[:] = 0.0
        e2[int(idx)] = 1.0
        v = e2 - float(e2 @ d) * d - float(e2 @ u) * u
        if np.linalg.norm(v) > 1e-9:
            v = v / (np.linalg.norm(v) + 1e-12)
            return u, v
    return u, np.roll(u, 1)


def select_polyhedral_edge_tangent_rescue_cross(
    A: np.ndarray,
    B: np.ndarray,
    M: np.ndarray,
    *,
    seed_count: int,
    edge_width: int,
    tangent_planes: int,
    rescue_budget: int,
    budget_pairs: int,
    alpha: float = 1.0,
) -> tuple[list[tuple[int, int]], int, dict[str, object]]:
    """Run fast polyhedral edge walk plus tangent sidecar rescue probes.

    This is "tangential parallelism" as a cost-audited selector. The main
    path stays ``polyhedral_edge_k20_w4``. Sidecar workers then search rotated
    tangent slices around the current keyed directions and collapse only a
    bounded number of candidates back into real exact scoring.
    """

    if tangent_planes <= 0:
        raise ValueError("tangent_planes must be > 0")
    if rescue_budget < 0:
        raise ValueError("rescue_budget must be >= 0")

    main_pairs, main_evaluations = select_polyhedral_edge_walk_cross(
        A,
        B,
        M,
        seed_count=seed_count,
        edge_width=edge_width,
        budget_pairs=budget_pairs,
        alpha=alpha,
    )
    if rescue_budget == 0:
        return main_pairs, main_evaluations, {
            "main_method": f"polyhedral_edge_k{seed_count}_w{edge_width}",
            "tangent_planes": int(tangent_planes),
            "rescue_budget": 0,
            "main_evaluations": int(main_evaluations),
            "rescue_evaluations": 0,
            "cheap_probe_count": 0,
            "frontier_size": int(main_evaluations),
        }

    a_norms = np.linalg.norm(A, axis=1)
    b_norms = np.linalg.norm(B, axis=1)
    rotated = A @ M.T
    rotated_unit = _normalize_rows(rotated)
    b_unit = _normalize_rows(B)
    a_seeds = np.argsort(a_norms)[::-1][: min(seed_count, A.shape[0])]
    b_seeds = np.argsort(b_norms)[::-1][: min(seed_count, B.shape[0])]

    sidecar_scores: dict[tuple[int, int], float] = {}
    cheap_probe_count = 0
    per_plane_budget = max(1, math.ceil(rescue_budget / (2 * tangent_planes)))
    phase_step = 2.0 * math.pi / (PHI * PHI)
    main_set = set(main_pairs)

    def _record(pair: tuple[int, int], score: float) -> None:
        if pair in main_set:
            return
        sidecar_scores[pair] = max(sidecar_scores.get(pair, -float("inf")), float(score))

    for plane in range(tangent_planes):
        theta = float((plane * phase_step) % (2.0 * math.pi))

        a_candidates: list[tuple[float, tuple[int, int]]] = []
        for ai_raw in a_seeds:
            ai = int(ai_raw)
            target = rotated_unit[ai]
            u, v = _tangent_basis_pair(target)
            side = math.cos(theta) * u + math.sin(theta) * v
            forward = b_unit @ target
            lateral = np.abs(b_unit @ side)
            score = forward + 0.08 * lateral + 0.01 * (b_norms / (float(b_norms.max()) + 1e-12))
            cheap_probe_count += int(B.shape[0])
            top = np.argsort(score)[::-1][: min(per_plane_budget, B.shape[0])]
            for bj in top:
                a_candidates.append((float(score[int(bj)]), (ai, int(bj))))
        a_candidates.sort(key=lambda item: item[0], reverse=True)
        for score, pair in a_candidates[:per_plane_budget]:
            _record(pair, score)

        b_candidates: list[tuple[float, tuple[int, int]]] = []
        for bj_raw in b_seeds:
            bj = int(bj_raw)
            target = b_unit[bj]
            u, v = _tangent_basis_pair(target)
            side = math.cos(-theta) * u + math.sin(-theta) * v
            forward = rotated_unit @ target
            lateral = np.abs(rotated_unit @ side)
            score = forward + 0.08 * lateral + 0.01 * (a_norms / (float(a_norms.max()) + 1e-12))
            cheap_probe_count += int(A.shape[0])
            top = np.argsort(score)[::-1][: min(per_plane_budget, A.shape[0])]
            for ai in top:
                b_candidates.append((float(score[int(ai)]), (int(ai), bj)))
        b_candidates.sort(key=lambda item: item[0], reverse=True)
        for score, pair in b_candidates[:per_plane_budget]:
            _record(pair, score)

    rescue_pairs = [
        pair for pair, _ in sorted(sidecar_scores.items(), key=lambda item: item[1], reverse=True)[:rescue_budget]
    ]
    candidates = list(dict.fromkeys([*main_pairs, *rescue_pairs]))
    log_amp = amplitude_matrix(A, B, M, alpha=alpha)
    candidates.sort(key=lambda pair: float(log_amp[pair[0], pair[1]]), reverse=True)
    selected = candidates[:budget_pairs]
    rescue_evaluations = len([pair for pair in rescue_pairs if pair not in main_set])
    evaluations = int(main_evaluations + rescue_evaluations)
    meta = {
        "main_method": f"polyhedral_edge_k{seed_count}_w{edge_width}",
        "tangent_planes": int(tangent_planes),
        "rescue_budget": int(rescue_budget),
        "phase_step": round(float(phase_step), 6),
        "main_evaluations": int(main_evaluations),
        "rescue_evaluations": int(rescue_evaluations),
        "cheap_probe_count": int(cheap_probe_count),
        "frontier_size": int(len(candidates)),
    }
    return selected, evaluations, meta


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


def _score_pair(
    A: np.ndarray, B: np.ndarray, M: np.ndarray, ai: int, bj: int, alpha: float
) -> float:
    """Single-pair amplitude evaluation; cost-honest unit for polyhedral walk."""

    rotated = M @ A[ai]
    rn = float(np.linalg.norm(rotated)) + 1e-12
    bn = float(np.linalg.norm(B[bj])) + 1e-12
    cos_v = float(rotated @ B[bj]) / (rn * bn)
    return alpha * float(np.linalg.norm(A[ai])) * float(np.linalg.norm(B[bj])) * cos_v


def select_polyhedral_walk_cross(
    A: np.ndarray,
    B: np.ndarray,
    M: np.ndarray,
    *,
    polyhedron: str,
    budget_pairs: int,
    alpha: float = 1.0,
) -> tuple[list[tuple[int, int]], int, dict[str, object]]:
    """Polyhedral edge-walk: bounded-diameter compass over the joint A x B space.

    Each side of the joint space is projected into R^3 via the top-3 SVD
    components of the coupling matrix M. Every Platonic-solid vertex
    represents a 3D direction; a candidate pair (a, b) "lives" at the
    vertex whose direction best matches both lifts. We start at the
    highest-affinity vertex and walk edges greedily, evaluating the
    locally-best pair at each visited vertex. The polyhedron's diameter
    bounds worst-case turnings to reach any region.

    Returns (pairs, evaluations, walk_meta) where evaluations counts
    one amplitude scoring per visited vertex (one "turning"), and
    walk_meta carries the structural fingerprint of the walk:
      - polyhedron name, n_vertices, n_edges, diameter
      - turnings (number of edge-traversals consumed)
      - vertices_visited (path through the polyhedron in order)
    """

    vertices, edges = _platonic_solid(polyhedron)
    n_v = vertices.shape[0]
    diameter = _polyhedron_diameter(n_v, edges)

    adj: list[list[int]] = [[] for _ in range(n_v)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)

    # Lift both sides into R^3 via top-3 SVD components of M:
    #   amplitude(a, b) ~ ||a|| ||b|| cos(M a, b)
    # In rank-3 truncation, M ~ U3 S3 V3^T, so M a ~ U3 S3 V3^T a.
    # In the U3 basis: a_lift = S3 V3^T a, b_lift = U3^T b. A diamond
    # pair has both lifts pointing in the same R^3 direction.
    U, s, Vt = np.linalg.svd(M, full_matrices=False)
    k = min(3, len(s))
    a_lift = (A @ Vt[:k].T) * s[:k]  # n_a x 3
    b_lift = B @ U[:, :k]  # n_b x 3

    # Per-vertex affinity uses the un-normalized lift so magnitude
    # (norm in the rank-3 subspace) matters as much as direction. The
    # amplitude function is ||a|| * ||b|| * cos, and the polyhedral
    # compass is the rank-3 surrogate of that score; weighting by lift
    # norm makes high-norm diamonds dominate random vectors that happen
    # to land near a vertex by direction alone.
    a_align = a_lift @ vertices.T  # n_a x n_v
    b_align = b_lift @ vertices.T  # n_b x n_v
    best_a_at_vertex = np.argmax(a_align, axis=0)  # n_v
    best_b_at_vertex = np.argmax(b_align, axis=0)  # n_v
    vertex_score = a_align.max(axis=0) + b_align.max(axis=0)

    start = int(np.argmax(vertex_score))
    visited: list[int] = []
    visited_set: set[int] = set()
    frontier: list[int] = [start]

    while frontier and len(visited) < n_v:
        frontier.sort(key=lambda v: -float(vertex_score[v]))
        v = frontier.pop(0)
        if v in visited_set:
            continue
        visited.append(v)
        visited_set.add(v)
        for nb in adj[v]:
            if nb not in visited_set:
                frontier.append(nb)

    # One amplitude eval per unique pair we land on while walking (the
    # "turning" cost). Distinct vertices may collapse to the same pair
    # when projected -- we count each unique pair once.
    evaluations = 0
    seen: set[tuple[int, int]] = set()
    scored: list[tuple[float, tuple[int, int]]] = []
    for v in visited:
        ai = int(best_a_at_vertex[v])
        bj = int(best_b_at_vertex[v])
        pair = (ai, bj)
        if pair in seen:
            continue
        seen.add(pair)
        score = _score_pair(A, B, M, ai, bj, alpha)
        scored.append((score, pair))
        evaluations += 1

    scored.sort(key=lambda t: -t[0])
    pairs = [pair for _, pair in scored[:budget_pairs]]
    turnings = max(0, len(visited) - 1)
    walk_meta = {
        "polyhedron": polyhedron,
        "n_vertices": int(n_v),
        "n_edges": int(len(edges)),
        "diameter": int(diameter),
        "turnings": int(turnings),
        "vertices_visited": [int(v) for v in visited],
        "unique_pair_evaluations": int(evaluations),
    }
    return pairs, evaluations, walk_meta


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
        "polyhedral_edge_k20_w4": select_polyhedral_edge_walk_cross(
            A, B, M, seed_count=20, edge_width=4, budget_pairs=budget_pairs, alpha=alpha
        ),
        "polyhedral_edge_k30_w6": select_polyhedral_edge_walk_cross(
            A, B, M, seed_count=30, edge_width=6, budget_pairs=budget_pairs, alpha=alpha
        ),
        "polyhedral_edge_k20_w10": select_polyhedral_edge_walk_cross(
            A, B, M, seed_count=20, edge_width=10, budget_pairs=budget_pairs, alpha=alpha
        ),
        "polyhedral_edge_k20_w4_hybrid": select_polyhedral_edge_walk_cross(
            A, B, M, seed_count=20, edge_width=4, edge_metric="hybrid", budget_pairs=budget_pairs, alpha=alpha
        ),
        "polyhedral_edge_k20_w10_weighted": select_polyhedral_edge_walk_cross(
            A, B, M, seed_count=20, edge_width=10, edge_metric="weighted_hybrid", budget_pairs=budget_pairs, alpha=alpha
        ),
    }

    gear_meta: dict[str, dict[str, object]] = {}
    pairs, evaluations, meta = select_polyhedral_edge_gear_cross(
        A,
        B,
        M,
        seed_count=20,
        fast_width=4,
        torque_width=10,
        shift_threshold=80_000,
        torque_metric="hamming",
        budget_pairs=budget_pairs,
        alpha=alpha,
    )
    runs["polyhedral_edge_gear_k20_w4_w10"] = (pairs, evaluations)
    gear_meta["polyhedral_edge_gear_k20_w4_w10"] = meta
    pairs, evaluations, meta = select_polyhedral_edge_tangent_rescue_cross(
        A,
        B,
        M,
        seed_count=20,
        edge_width=4,
        tangent_planes=4,
        rescue_budget=40,
        budget_pairs=budget_pairs,
        alpha=alpha,
    )
    runs["polyhedral_edge_k20_w4_tangent_rescue_r4_b40"] = (pairs, evaluations)
    gear_meta["polyhedral_edge_k20_w4_tangent_rescue_r4_b40"] = meta

    phase_meta: dict[str, dict[str, object]] = {}
    pairs, evaluations, meta = select_phase_angle_cross(
        A,
        B,
        M,
        seed_count=20,
        offsets=7,
        angle_width=2,
        budget_pairs=budget_pairs,
        alpha=alpha,
    )
    runs["phase_angle_k20_o7"] = (pairs, evaluations)
    phase_meta["phase_angle_k20_o7"] = meta
    pairs, evaluations, meta = select_constructive_oscillation_cross(
        A,
        B,
        M,
        seed_count=8,
        oscillations=4,
        beam_width=3,
        budget_pairs=budget_pairs,
        alpha=alpha,
    )
    runs["constructive_oscillation_k8_o4_w3"] = (pairs, evaluations)
    phase_meta["constructive_oscillation_k8_o4_w3"] = meta

    rank_sweep = [1, 2, 4, 8, 16, A.shape[1]]
    for rank in rank_sweep:
        if rank > A.shape[1]:
            continue
        runs[f"resonance_lowrank_r{rank}"] = select_resonance_cross_lowrank(
            A, B, M, rank=rank, budget_pairs=budget_pairs, alpha=alpha
        )

    # Platonic-solid compass walks. Each solid is a different
    # bounded-diameter compass: tetrahedron is the cheapest 4-direction
    # probe; icosahedron gives 12 directions with diameter 3; dodecahedron
    # gives 20 directions with diameter 5. The joint A x B direction space
    # is projected to R^3 via the top-3 SVD components of M, so each vertex
    # represents a "turning" toward a principal joint direction.
    polyhedral_meta: dict[str, dict[str, object]] = {}
    for shape in ("tetrahedron", "octahedron", "cube", "icosahedron", "dodecahedron"):
        pairs, evaluations, meta = select_polyhedral_walk_cross(
            A, B, M, polyhedron=shape, budget_pairs=budget_pairs, alpha=alpha
        )
        method_name = f"polyhedral_walk_{shape}"
        runs[method_name] = (pairs, evaluations)
        polyhedral_meta[method_name] = meta

    # Full C(N, 2) disagreement-probe matrix: every pair of source methods.
    # The "double-negative-makes-positive" mechanism may fire for any
    # (method_a, method_b) combination where their null-space XOR encodes
    # complementary partial signal. Skip brute_pair (it has full recall
    # already, no disagreement to mine).
    disagreement_input_methods = sorted(name for name in runs if name != "brute_pair")
    probe_sources: dict[str, tuple[str, str]] = {}
    for i, name_a in enumerate(disagreement_input_methods):
        for name_b in disagreement_input_methods[i + 1 :]:
            probe_key = f"disagree__{name_a}__X__{name_b}"
            runs[probe_key] = select_disagreement_probe_cross(
                A, B, M,
                method_a_pairs=runs[name_a][0],
                method_b_pairs=runs[name_b][0],
                budget_pairs=budget_pairs,
                alpha=alpha,
            )
            probe_sources[probe_key] = (name_a, name_b)

    summary: dict[str, dict[str, object]] = {}
    for name, (pairs, evaluations) in runs.items():
        row = evaluate_selection(pairs, landscape, log_amp_full)
        source_names = probe_sources.get(name)
        if source_names is None:
            source_evaluations = 0
            probe_evaluations = 0
            total_evaluations = int(evaluations)
            source_methods: list[str] = []
            cost_accounting = "direct"
        else:
            source_evaluations = int(sum(runs[source_name][1] for source_name in source_names))
            probe_evaluations = int(evaluations)
            total_evaluations = source_evaluations + probe_evaluations
            source_methods = list(source_names)
            cost_accounting = "source_plus_probe"
        row["evaluations"] = int(evaluations)
        row["probe_evaluations"] = probe_evaluations
        row["source_evaluations"] = source_evaluations
        row["source_methods"] = source_methods
        row["total_evaluations"] = total_evaluations
        row["cost_accounting"] = cost_accounting
        if name in polyhedral_meta:
            row["polyhedral_walk"] = polyhedral_meta[name]
        if name in gear_meta:
            if name.startswith("polyhedral_edge_gear"):
                row["polyhedral_edge_gear"] = gear_meta[name]
            else:
                row["tangent_rescue"] = gear_meta[name]
        if name in phase_meta:
            if name.startswith("constructive_oscillation"):
                row["constructive_oscillation"] = phase_meta[name]
            else:
                row["phase_angle"] = phase_meta[name]
        summary[name] = row

    def _best_full_recall(names: Sequence[str]) -> dict[str, object] | None:
        candidates = [
            (name, summary[name])
            for name in names
            if float(summary[name]["diamond_recall"]) >= 1.0
        ]
        if not candidates:
            return None
        best_name, best_row = min(candidates, key=lambda item: int(item[1]["total_evaluations"]))
        return {
            "method": best_name,
            "total_evaluations": int(best_row["total_evaluations"]),
            "evaluations": int(best_row["evaluations"]),
            "diamond_recall": float(best_row["diamond_recall"]),
            "regret_log_amp": float(best_row["regret_log_amp"]),
        }

    direct_methods = [name for name in runs if name not in probe_sources and name != "brute_pair"]
    probe_methods = sorted(probe_sources)
    best_single = _best_full_recall(direct_methods)
    best_probe = _best_full_recall(probe_methods)
    probe_beats_single = (
        best_single is not None
        and best_probe is not None
        and int(best_probe["total_evaluations"]) < int(best_single["total_evaluations"])
    )
    probe_cost_audit = {
        "note": (
            "Disagreement rows are re-rankers. total_evaluations includes both source selectors "
            "and the probe rerank cost; evaluations alone is only the probe-local candidate count."
        ),
        "best_full_recall_single_method": best_single,
        "best_full_recall_probe_method": best_probe,
        "probe_beats_single_on_total_cost": probe_beats_single,
    }

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
            "key_mode": spec.key_mode,
        },
        "alpha": alpha,
        "budget_pairs": budget_pairs,
        "joint_pool_size": int(A.shape[0] * B.shape[0]),
        "probe_cost_audit": probe_cost_audit,
        "summary": summary,
    }


def run_seed_size_sweep(
    *,
    sizes: Sequence[int],
    seeds: Sequence[int],
    budget_pairs: int = 8,
    n_diamond_pairs: int = 4,
    n_decoys_per_side: int = 12,
    key_mode: str = "random_orthogonal",
    alpha: float = 1.0,
) -> dict[str, object]:
    """Run a lightweight robustness sweep over seeds and problem sizes.

    This intentionally avoids the full disagreement-probe matrix. It answers
    the Tier-1 stability question: whether the direct speedup survives across
    multiple landscapes and n values.
    """

    method_order = [
        "tang_cross_k20",
        "polyhedral_edge_k20_w4",
        "polyhedral_edge_k20_w10",
        "polyhedral_edge_k20_w10_weighted",
        "polyhedral_edge_gear_k20_w4_w10",
        "polyhedral_edge_k20_w4_tangent_rescue_r4_b40",
        "constructive_oscillation_k8_o4_w3",
    ]
    rows: list[dict[str, object]] = []

    for size in sizes:
        for seed in seeds:
            spec = DualStateSpec(
                n_a=int(size),
                n_b=int(size),
                n_diamond_pairs=n_diamond_pairs,
                n_decoys_per_side=n_decoys_per_side,
                seed=int(seed),
                key_mode=key_mode,
            )
            landscape = build_landscape(spec)
            A = landscape["A"]
            B = landscape["B"]
            M = landscape["M"]
            assert isinstance(A, np.ndarray) and isinstance(B, np.ndarray) and isinstance(M, np.ndarray)
            log_amp_full = amplitude_matrix(A, B, M, alpha=alpha)
            runs = {
                "tang_cross_k20": select_tang_cross(
                    A, B, M, k_per_side=20, budget_pairs=budget_pairs, alpha=alpha
                ),
                "polyhedral_edge_k20_w4": select_polyhedral_edge_walk_cross(
                    A, B, M, seed_count=20, edge_width=4, budget_pairs=budget_pairs, alpha=alpha
                ),
                "polyhedral_edge_k20_w10": select_polyhedral_edge_walk_cross(
                    A, B, M, seed_count=20, edge_width=10, budget_pairs=budget_pairs, alpha=alpha
                ),
                "polyhedral_edge_k20_w10_weighted": select_polyhedral_edge_walk_cross(
                    A,
                    B,
                    M,
                    seed_count=20,
                    edge_width=10,
                    edge_metric="weighted_hybrid",
                    budget_pairs=budget_pairs,
                    alpha=alpha,
                ),
                "polyhedral_edge_gear_k20_w4_w10": select_polyhedral_edge_gear_cross(
                    A,
                    B,
                    M,
                    seed_count=20,
                    fast_width=4,
                    torque_width=10,
                    shift_threshold=80_000,
                    torque_metric="hamming",
                    budget_pairs=budget_pairs,
                    alpha=alpha,
                )[:2],
                "polyhedral_edge_k20_w4_tangent_rescue_r4_b40": select_polyhedral_edge_tangent_rescue_cross(
                    A,
                    B,
                    M,
                    seed_count=20,
                    edge_width=4,
                    tangent_planes=4,
                    rescue_budget=40,
                    budget_pairs=budget_pairs,
                    alpha=alpha,
                )[:2],
                "constructive_oscillation_k8_o4_w3": select_constructive_oscillation_cross(
                    A,
                    B,
                    M,
                    seed_count=8,
                    oscillations=4,
                    beam_width=3,
                    budget_pairs=budget_pairs,
                    alpha=alpha,
                )[:2],
            }

            evaluated: dict[str, dict[str, object]] = {}
            for name, (pairs, evaluations) in runs.items():
                row = evaluate_selection(pairs, landscape, log_amp_full)
                row["evaluations"] = int(evaluations)
                row["total_evaluations"] = int(evaluations)
                evaluated[name] = row

            full_recall = [
                name
                for name in method_order
                if float(evaluated[name]["diamond_recall"]) >= 1.0
            ]
            best_full_recall = (
                min(full_recall, key=lambda name: int(evaluated[name]["total_evaluations"]))
                if full_recall
                else None
            )
            rows.append(
                {
                    "size": int(size),
                    "seed": int(seed),
                    "joint_pool_size": int(size) * int(size),
                    "best_full_recall_method": best_full_recall,
                    "methods": evaluated,
                }
            )

    aggregate: dict[str, dict[str, object]] = {}
    for method in method_order:
        method_rows = [row["methods"][method] for row in rows]  # type: ignore[index]
        full = [float(row["diamond_recall"]) >= 1.0 for row in method_rows]
        zero = [float(row["regret_log_amp"]) == 0.0 for row in method_rows]
        evals = [int(row["total_evaluations"]) for row in method_rows]
        aggregate[method] = {
            "runs": len(method_rows),
            "full_recall_runs": int(sum(full)),
            "full_recall_rate": round(float(sum(full) / max(1, len(full))), 6),
            "zero_regret_runs": int(sum(zero)),
            "zero_regret_rate": round(float(sum(zero) / max(1, len(zero))), 6),
            "median_evaluations": int(np.median(evals)) if evals else 0,
            "min_evaluations": int(min(evals)) if evals else 0,
            "max_evaluations": int(max(evals)) if evals else 0,
        }

    winner_counts: dict[str, int] = {method: 0 for method in method_order}
    winner_counts["none"] = 0
    for row in rows:
        winner = row["best_full_recall_method"]
        winner_counts[str(winner) if winner is not None else "none"] += 1

    tang_evals = [
        int(row["methods"]["tang_cross_k20"]["total_evaluations"])  # type: ignore[index]
        for row in rows
    ]
    poly_evals = [
        int(row["methods"]["polyhedral_edge_k20_w4"]["total_evaluations"])  # type: ignore[index]
        for row in rows
    ]
    poly_w10_evals = [
        int(row["methods"]["polyhedral_edge_k20_w10"]["total_evaluations"])  # type: ignore[index]
        for row in rows
    ]
    poly_weighted_evals = [
        int(row["methods"]["polyhedral_edge_k20_w10_weighted"]["total_evaluations"])  # type: ignore[index]
        for row in rows
    ]
    gear_evals = [
        int(row["methods"]["polyhedral_edge_gear_k20_w4_w10"]["total_evaluations"])  # type: ignore[index]
        for row in rows
    ]
    tangent_rescue_evals = [
        int(row["methods"]["polyhedral_edge_k20_w4_tangent_rescue_r4_b40"]["total_evaluations"])  # type: ignore[index]
        for row in rows
    ]
    osc_evals = [
        int(row["methods"]["constructive_oscillation_k8_o4_w3"]["total_evaluations"])  # type: ignore[index]
        for row in rows
    ]

    return {
        "schema_version": "scbe_mahss_dual_state_seed_size_sweep_v1",
        "sizes": [int(size) for size in sizes],
        "seeds": [int(seed) for seed in seeds],
        "key_mode": key_mode,
        "budget_pairs": int(budget_pairs),
        "n_diamond_pairs": int(n_diamond_pairs),
        "n_decoys_per_side": int(n_decoys_per_side),
        "methods": method_order,
        "aggregate": aggregate,
        "winner_counts": winner_counts,
        "speedup_vs_tang_median": {
            "polyhedral_edge_k20_w4": round(float(np.median(np.asarray(tang_evals) / np.asarray(poly_evals))), 6),
            "polyhedral_edge_k20_w10": round(float(np.median(np.asarray(tang_evals) / np.asarray(poly_w10_evals))), 6),
            "polyhedral_edge_k20_w10_weighted": round(float(np.median(np.asarray(tang_evals) / np.asarray(poly_weighted_evals))), 6),
            "polyhedral_edge_gear_k20_w4_w10": round(float(np.median(np.asarray(tang_evals) / np.asarray(gear_evals))), 6),
            "polyhedral_edge_k20_w4_tangent_rescue_r4_b40": round(float(np.median(np.asarray(tang_evals) / np.asarray(tangent_rescue_evals))), 6),
            "constructive_oscillation_k8_o4_w3": round(float(np.median(np.asarray(tang_evals) / np.asarray(osc_evals))), 6),
        },
        "rows": rows,
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
        "--key-mode",
        default="random_orthogonal",
        choices=["random_orthogonal", "identity", "signed_permutation", "hadamard", "block_rotation"],
        help="Orthogonal coupling key family used to plant and score paired states.",
    )
    parser.add_argument("--sweep", action="store_true", help="Run seed/size robustness sweep instead of one board.")
    parser.add_argument("--sweep-sizes", default="80", help="Comma-separated n values for n_a=n_b.")
    parser.add_argument("--sweep-seeds", type=int, default=10, help="Number of deterministic seeds, 0..N-1.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/mahss_dual_state/dual_state_keyed_search_sim_v1.json"),
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.sweep:
        sizes = [int(part.strip()) for part in str(args.sweep_sizes).split(",") if part.strip()]
        seeds = list(range(int(args.sweep_seeds)))
        report = run_seed_size_sweep(
            sizes=sizes,
            seeds=seeds,
            budget_pairs=args.budget_pairs,
            n_diamond_pairs=args.n_diamond_pairs,
            n_decoys_per_side=args.n_decoys_per_side,
            key_mode=args.key_mode,
            alpha=args.alpha,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(f"wrote {args.output}")
            print(
                f"sweep: sizes={report['sizes']} seeds={len(seeds)} "
                f"budget={args.budget_pairs}"
            )
            for name, row in report["aggregate"].items():
                print(
                    f"  {name}: full_recall={row['full_recall_runs']}/{row['runs']} "
                    f"zero_regret={row['zero_regret_runs']}/{row['runs']} "
                    f"median_evals={row['median_evaluations']}"
                )
            print(f"  winner_counts={report['winner_counts']}")
            print(f"  speedup_vs_tang_median={report['speedup_vs_tang_median']}")
        return 0

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
        key_mode=args.key_mode,
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
            total = int(row["total_evaluations"])
            total_suffix = "" if total == int(row["evaluations"]) else f" total={total:>6} "
            print(
                f"  {name}: evals={row['evaluations']:>6} "
                f"{total_suffix}"
                f"recall={row['diamond_recall']:.2f} ({row['diamonds_caught']}/{spec.n_diamond_pairs}) "
                f"regret_log_amp={row['regret_log_amp']:.4f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
