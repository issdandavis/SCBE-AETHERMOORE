"""Planted-diamond stress test for mirror_beam vs Tang/radial beams.

Synthetic landscape: N candidates of which D are "diamonds" (high alignment
with the query, high sketch norm) and N-D are "stones" (random low-alignment
sketches with smaller norms). True score for ranking = (sketch . query)**2,
so the diamonds are the unambiguous top-D answers.

Run all baselines at the same budget B and measure two things:
- regret: best_found_score - true_top_score (smaller is better)
- diamond_recall: fraction of the D diamonds that landed in the budget-B
  selection (higher is better)

This is the contrast-rich landscape that the metamaterial pool does not
provide: most candidates are noise, a few are the answer. Hyperbolic
resonance should crush Tang here because the exponential distance scaling
amplifies the diamond-vs-stone separation, not just average it.
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

SCHEMA_VERSION = "scbe_mahss_planted_diamond_sim_v1"
DIM = 64


@dataclass(frozen=True)
class PlantedSpec:
    """Generator spec for a planted-diamond landscape."""

    n_candidates: int = 200
    n_diamonds: int = 5
    diamond_norm: float = 6.0
    stone_norm: float = 1.0
    diamond_alignment: float = 0.92
    stone_alignment_jitter: float = 0.20
    seed: int = 17
    n_high_norm_misaligned: int = 0
    n_low_norm_aligned: int = 0
    high_norm_misaligned_norm: float = 6.0
    low_norm_aligned_norm: float = 1.0


def build_landscape(spec: PlantedSpec) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return (query, sketches, true_scores, diamond_indices)."""

    rng = np.random.default_rng(spec.seed)
    query = rng.standard_normal(DIM)
    query /= np.linalg.norm(query)

    sketches = np.empty((spec.n_candidates, DIM), dtype=float)
    n_decoys = spec.n_high_norm_misaligned + spec.n_low_norm_aligned
    if spec.n_diamonds + n_decoys > spec.n_candidates:
        raise ValueError("diamonds + decoys exceed pool size")
    chosen = rng.choice(spec.n_candidates, size=spec.n_diamonds + n_decoys, replace=False)
    diamond_idxs = chosen[: spec.n_diamonds]
    high_norm_misaligned_idxs = chosen[spec.n_diamonds : spec.n_diamonds + spec.n_high_norm_misaligned]
    low_norm_aligned_idxs = chosen[spec.n_diamonds + spec.n_high_norm_misaligned :]
    diamond_set = set(int(i) for i in diamond_idxs)
    high_misalign_set = set(int(i) for i in high_norm_misaligned_idxs)
    low_align_set = set(int(i) for i in low_norm_aligned_idxs)

    for i in range(spec.n_candidates):
        if i in diamond_set:
            jitter = rng.standard_normal(DIM)
            jitter -= jitter.dot(query) * query
            jitter /= np.linalg.norm(jitter) + 1e-12
            direction = spec.diamond_alignment * query + math.sqrt(
                max(0.0, 1.0 - spec.diamond_alignment**2)
            ) * jitter
            sketches[i] = spec.diamond_norm * direction / (np.linalg.norm(direction) + 1e-12)
        elif i in high_misalign_set:
            v = rng.standard_normal(DIM)
            v_perp = v - v.dot(query) * query
            v_perp /= np.linalg.norm(v_perp) + 1e-12
            sketches[i] = spec.high_norm_misaligned_norm * v_perp
        elif i in low_align_set:
            jitter = rng.standard_normal(DIM)
            jitter -= jitter.dot(query) * query
            jitter /= np.linalg.norm(jitter) + 1e-12
            direction = spec.diamond_alignment * query + math.sqrt(
                max(0.0, 1.0 - spec.diamond_alignment**2)
            ) * jitter
            sketches[i] = spec.low_norm_aligned_norm * direction / (np.linalg.norm(direction) + 1e-12)
        else:
            v = rng.standard_normal(DIM)
            cos = abs(float(v.dot(query) / (np.linalg.norm(v) + 1e-12)))
            cos = min(cos, spec.stone_alignment_jitter)
            v_perp = v - v.dot(query) * query
            v_perp /= np.linalg.norm(v_perp) + 1e-12
            direction = cos * query + math.sqrt(1.0 - cos**2) * v_perp
            sketches[i] = spec.stone_norm * direction / (np.linalg.norm(direction) + 1e-12)

    true_scores = (sketches @ query) ** 2
    return query, sketches, true_scores, np.asarray(sorted(diamond_set), dtype=int)


def select_uniform(sketches: np.ndarray, *, budget: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.choice(sketches.shape[0], size=budget, replace=False)


def select_tang_beam(sketches: np.ndarray, *, budget: int, power: float = 2.0) -> np.ndarray:
    norms = np.linalg.norm(sketches, axis=1) ** power
    return np.argsort(norms)[::-1][:budget]


def select_mirror_beam(
    sketches: np.ndarray, query: np.ndarray, *, budget: int, curvature: float = 1.0
) -> np.ndarray:
    sqrt_c = math.sqrt(curvature)

    def _project(v: np.ndarray) -> np.ndarray:
        n = np.linalg.norm(v, axis=-1, keepdims=True)
        n_safe = np.maximum(n, 1e-12)
        scale = np.tanh(sqrt_c * n) / (sqrt_c * n_safe)
        return v * scale

    q_ball = _project(query)
    q_norm_sq = float(q_ball.dot(q_ball))
    s_ball = _project(sketches)
    s_norm_sq = np.sum(s_ball * s_ball, axis=1)
    diff = s_ball - q_ball
    diff_sq = np.sum(diff * diff, axis=1)
    denom = np.maximum(1e-12, (1.0 - s_norm_sq) * (1.0 - q_norm_sq))
    cosh_arg = np.maximum(1.0, 1.0 + 2.0 * diff_sq / denom)
    distances = np.arccosh(cosh_arg)
    return np.argsort(distances)[:budget]


def select_cosine_top_k(sketches: np.ndarray, query: np.ndarray, *, budget: int) -> np.ndarray:
    norms = np.linalg.norm(sketches, axis=1) + 1e-12
    cos = (sketches @ query) / norms
    return np.argsort(cos)[::-1][:budget]


def select_mirror_resonance(
    sketches: np.ndarray, query: np.ndarray, *, budget: int, alpha: float = 1.0
) -> np.ndarray:
    """Resonance-amplitude version of the laser/diamond intuition.

    A_i = exp(alpha * ||s_i|| * cos(s_i, q))

    High norm AND high alignment combine multiplicatively in the exponent,
    so true diamonds (both large) stand out exponentially over noise. This
    is the physics-correct reading of "the diamond reflects brightest" —
    the right answer's amplitude is exponentially larger than near-misses.
    """

    norms = np.linalg.norm(sketches, axis=1) + 1e-12
    cos = (sketches @ query) / norms
    log_amplitude = alpha * norms * cos
    return np.argsort(log_amplitude)[::-1][:budget]


def evaluate_selection(
    selection: np.ndarray, true_scores: np.ndarray, diamond_indices: np.ndarray
) -> dict[str, float]:
    diamond_set = set(int(i) for i in diamond_indices)
    selected = set(int(i) for i in selection)
    diamonds_caught = len(selected & diamond_set)
    best_in_selection = float(true_scores[selection].max()) if len(selection) else 0.0
    best_overall = float(true_scores.max())
    regret = best_overall - best_in_selection
    return {
        "best_in_selection": round(best_in_selection, 9),
        "best_overall": round(best_overall, 9),
        "regret": round(regret, 9),
        "diamond_recall": diamonds_caught / max(1, len(diamond_set)),
        "diamonds_caught": diamonds_caught,
        "selection_size": len(selected),
    }


def run_compare(spec: PlantedSpec, *, budget: int) -> dict[str, object]:
    query, sketches, true_scores, diamond_idxs = build_landscape(spec)
    runs: dict[str, np.ndarray] = {
        "uniform_sampled": select_uniform(sketches, budget=budget, seed=spec.seed),
        "tang_beam_2": select_tang_beam(sketches, budget=budget, power=2.0),
        "tang_beam_2_125": select_tang_beam(sketches, budget=budget, power=2.125),
        "cosine_top_k": select_cosine_top_k(sketches, query, budget=budget),
        "mirror_beam_c1": select_mirror_beam(sketches, query, budget=budget, curvature=1.0),
        "mirror_beam_c0_25": select_mirror_beam(sketches, query, budget=budget, curvature=0.25),
        "mirror_beam_c4": select_mirror_beam(sketches, query, budget=budget, curvature=4.0),
        "mirror_resonance_a1": select_mirror_resonance(sketches, query, budget=budget, alpha=1.0),
    }
    summary = {name: evaluate_selection(idxs, true_scores, diamond_idxs) for name, idxs in runs.items()}
    return {
        "schema_version": SCHEMA_VERSION,
        "spec": {
            "n_candidates": spec.n_candidates,
            "n_diamonds": spec.n_diamonds,
            "diamond_norm": spec.diamond_norm,
            "stone_norm": spec.stone_norm,
            "diamond_alignment": spec.diamond_alignment,
            "stone_alignment_jitter": spec.stone_alignment_jitter,
            "seed": spec.seed,
        },
        "budget": budget,
        "summary": summary,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-candidates", type=int, default=200)
    parser.add_argument("--n-diamonds", type=int, default=5)
    parser.add_argument("--diamond-norm", type=float, default=6.0)
    parser.add_argument("--stone-norm", type=float, default=1.0)
    parser.add_argument("--diamond-alignment", type=float, default=0.92)
    parser.add_argument("--stone-alignment-jitter", type=float, default=0.20)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--budget", type=int, default=10)
    parser.add_argument("--n-high-norm-misaligned", type=int, default=0)
    parser.add_argument("--n-low-norm-aligned", type=int, default=0)
    parser.add_argument("--high-norm-misaligned-norm", type=float, default=6.0)
    parser.add_argument("--low-norm-aligned-norm", type=float, default=1.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/mahss_planted_diamond/planted_diamond_sim_v1.json"),
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    spec = PlantedSpec(
        n_candidates=args.n_candidates,
        n_diamonds=args.n_diamonds,
        diamond_norm=args.diamond_norm,
        stone_norm=args.stone_norm,
        diamond_alignment=args.diamond_alignment,
        stone_alignment_jitter=args.stone_alignment_jitter,
        seed=args.seed,
        n_high_norm_misaligned=args.n_high_norm_misaligned,
        n_low_norm_aligned=args.n_low_norm_aligned,
        high_norm_misaligned_norm=args.high_norm_misaligned_norm,
        low_norm_aligned_norm=args.low_norm_aligned_norm,
    )
    report = run_compare(spec, budget=args.budget)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"wrote {args.output}")
        print(f"landscape: n={spec.n_candidates} diamonds={spec.n_diamonds} budget={args.budget}")
        for name, row in report["summary"].items():
            print(
                f"  {name}: regret={row['regret']:.6f} "
                f"diamond_recall={row['diamond_recall']:.2f} "
                f"({row['diamonds_caught']}/{spec.n_diamonds})"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
