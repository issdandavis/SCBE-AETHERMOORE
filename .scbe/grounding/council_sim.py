"""Council Stabilization Sim.

Takes the 10-seed council at .scbe/grounding/council_seeds.json and asks:
does the mixed metric d_M = sqrt(w_h*d_hyp^2 + w_t*d_torus^2 + d_z^2) actually
cluster narratively-affine lore fragments together across 4 canon sources
(Everweave 7, Claude SFT, Grok export, Avalon Codex)?

Three experiments in one run:
  (1) Pairwise distance matrix report  — expected-close vs expected-far pairs,
      plus intra/inter source and intra/inter cutover means.
  (2) Pi_exchange per seed                — centered sigmoid over the 8 priors.
  (3) Tag-affinity contraction step       — each seed's u pulled toward the
      weighted mean of seeds that share narrative tags. Checks whether the
      already-placed seeds are self-consistent: if yes, drift decays fast and
      cluster structure is preserved; if no, post-stab distances diverge.

Run from repo root:
    python .scbe/grounding/council_sim.py
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# ---- Constants (from council_seed_schema $defs.mixed_metric) ----
PHI = (1 + math.sqrt(5)) / 2
W_H = PHI
W_T = 1.0
W_Z = np.array([0.5, 0.5, 0.5, 1.0, 1.0, 0.8, 0.6, 0.6, 0.8])
TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]


@dataclass
class Seed:
    seed_id: str
    source_id: str
    cutover_flag: str
    u: np.ndarray
    theta: np.ndarray
    z: np.ndarray
    pi_priors: Dict[str, float]
    tags: List[str]


def load_seeds(path: Path) -> List[Seed]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return [
        Seed(
            seed_id=r["seed_id"],
            source_id=r["source_id"],
            cutover_flag=r["cutover_flag"],
            u=np.array(r["u"], dtype=float),
            theta=np.array(r["theta"], dtype=float),
            z=np.array(r["z"], dtype=float),
            pi_priors=r["pi_exchange_priors"],
            tags=r["narrative_tags"],
        )
        for r in data["seeds"]
    ]


# ---- Metric primitives ----
def d_poincare_1d(a: float, b: float) -> float:
    num = 2 * (a - b) ** 2
    den = (1 - a ** 2) * (1 - b ** 2)
    if den <= 0:
        return float("inf")
    arg = max(1.0, 1 + num / den)
    return math.acosh(arg)


def d_hyp(u_a: np.ndarray, u_b: np.ndarray) -> float:
    return math.sqrt(sum(d_poincare_1d(a, b) ** 2 for a, b in zip(u_a, u_b)))


def d_torus(theta_a: np.ndarray, theta_b: np.ndarray) -> float:
    two_pi = 2 * math.pi
    diff = np.abs(theta_a - theta_b) % two_pi
    diff = np.minimum(diff, two_pi - diff)
    return float(np.sqrt(np.sum(diff ** 2)))


def d_z(z_a: np.ndarray, z_b: np.ndarray) -> float:
    return float(np.sqrt(np.sum(W_Z * (z_a - z_b) ** 2)))


def d_mixed(a: Seed, b: Seed) -> float:
    return math.sqrt(
        W_H * d_hyp(a.u, b.u) ** 2
        + W_T * d_torus(a.theta, b.theta) ** 2
        + d_z(a.z, b.z) ** 2
    )


def pairwise(seeds: List[Seed]) -> np.ndarray:
    n = len(seeds)
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            D[i, j] = D[j, i] = d_mixed(seeds[i], seeds[j])
    return D


def pi_exchange(seed: Seed) -> float:
    channels = list(seed.pi_priors.values())
    z = sum(channels) / len(channels)
    return 1.0 / (1.0 + math.exp(-(z - 0.5) * 6))


# ---- Reporting ----
def report(seeds: List[Seed], D: np.ndarray, label: str) -> Dict:
    n = len(seeds)
    by_id = {s.seed_id: i for i, s in enumerate(seeds)}

    expected_close = [
        ("e7_shipwreck_awakening", "grok_izack_dimensional_odyssey"),
        ("e7_shipwreck_awakening", "claude_sft_cave_contract"),
        ("codex_third_thread", "codex_47_realities"),
        ("claude_sft_cave_contract", "claude_sft_world_tree_planting"),
        ("e7_crystal_garden_ame", "e7_chronological_nexus_staff"),
    ]
    expected_far = [
        ("e7_shipwreck_awakening", "codex_47_realities"),
        ("claude_sft_zara_timeless_bubble", "e7_chronological_nexus_staff"),
        ("e7_crystal_garden_ame", "grok_izack_dimensional_odyssey"),
        ("e7_forest_toward_smoke", "codex_third_thread"),
    ]

    out: Dict = {
        "label": label,
        "frobenius": round(float(np.sqrt(np.sum(D ** 2))), 4),
        "mean_all": round(float(np.sum(D) / (n * (n - 1))), 4),
        "max_d": round(float(np.max(D)), 4),
        "min_d_nonzero": round(float(np.min(D[D > 0])), 4) if np.any(D > 0) else 0.0,
    }

    out["expected_close"] = [
        {"pair": f"{a} <-> {b}", "d": round(float(D[by_id[a], by_id[b]]), 4)}
        for a, b in expected_close
        if a in by_id and b in by_id
    ]
    out["expected_far"] = [
        {"pair": f"{a} <-> {b}", "d": round(float(D[by_id[a], by_id[b]]), 4)}
        for a, b in expected_far
        if a in by_id and b in by_id
    ]

    intra_src, inter_src = [], []
    intra_cut, inter_cut = [], []
    for i in range(n):
        for j in range(i + 1, n):
            (intra_src if seeds[i].source_id == seeds[j].source_id else inter_src).append(D[i, j])
            (intra_cut if seeds[i].cutover_flag == seeds[j].cutover_flag else inter_cut).append(D[i, j])

    out["mean_intra_source"] = round(float(np.mean(intra_src)) if intra_src else 0.0, 4)
    out["mean_inter_source"] = round(float(np.mean(inter_src)) if inter_src else 0.0, 4)
    out["mean_intra_cutover"] = round(float(np.mean(intra_cut)) if intra_cut else 0.0, 4)
    out["mean_inter_cutover"] = round(float(np.mean(inter_cut)) if inter_cut else 0.0, 4)

    return out


# ---- Stabilization ----
def stabilize(
    seeds: List[Seed], alpha: float = 0.15, max_iter: int = 20
) -> Tuple[List[Seed], List[float]]:
    """Council vote: each seed's u pulled toward tag-affine neighbors' weighted mean.

    Weight of neighbor j on seed i = |tags_i ∩ tags_j|. Seeds with no shared
    tags do not contribute. u is clamped back into (-0.999, 0.999).
    """
    current = [
        Seed(
            seed_id=s.seed_id,
            source_id=s.source_id,
            cutover_flag=s.cutover_flag,
            u=s.u.copy(),
            theta=s.theta.copy(),
            z=s.z.copy(),
            pi_priors=dict(s.pi_priors),
            tags=list(s.tags),
        )
        for s in seeds
    ]
    trajectory: List[float] = []
    for _ in range(max_iter):
        drift = 0.0
        next_us: List[np.ndarray] = []
        for i, s in enumerate(current):
            total_w = 0.0
            centroid = np.zeros(6)
            for j, other in enumerate(current):
                if i == j:
                    continue
                shared = len(set(s.tags) & set(other.tags))
                if shared > 0:
                    centroid += shared * other.u
                    total_w += shared
            if total_w == 0.0:
                next_us.append(s.u.copy())
                continue
            centroid /= total_w
            new_u = (1 - alpha) * s.u + alpha * centroid
            new_u = np.clip(new_u, -0.999, 0.999)
            drift += float(np.linalg.norm(new_u - s.u))
            next_us.append(new_u)
        for i, new_u in enumerate(next_us):
            current[i].u = new_u
        trajectory.append(drift)
        if drift < 1e-5:
            break
    return current, trajectory


# ---- Main ----
def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    seeds_path = repo_root / ".scbe" / "grounding" / "council_seeds.json"
    out_path = repo_root / ".scbe" / "grounding" / "council_sim_results.json"

    print("=" * 76)
    print("  Council Stabilization Sim  —  21D Multi-Source Lore Manifold")
    print("=" * 76)

    seeds = load_seeds(seeds_path)
    print(f"  Loaded {len(seeds)} seeds from {seeds_path.name}\n")
    print(f"  {'seed_id':<42} {'source':<15} {'cutover':<22} dom")
    print(f"  {'-' * 42} {'-' * 15} {'-' * 22} ---")
    for s in seeds:
        dom = TONGUES[int(np.argmax(s.u))]
        print(f"  {s.seed_id:<42} {s.source_id:<15} {s.cutover_flag:<22} {dom}")
    print()

    D0 = pairwise(seeds)
    pre = report(seeds, D0, "pre")

    print("  --- Pre-Stabilization ---")
    print(f"  Frobenius:           {pre['frobenius']}")
    print(f"  Mean (all pairs):    {pre['mean_all']}")
    print(f"  Min / Max:           {pre['min_d_nonzero']} / {pre['max_d']}")
    print(f"  Intra-source mean:   {pre['mean_intra_source']}")
    print(f"  Inter-source mean:   {pre['mean_inter_source']}")
    print(f"  Intra-cutover mean:  {pre['mean_intra_cutover']}")
    print(f"  Inter-cutover mean:  {pre['mean_inter_cutover']}")
    print(f"  Expected CLOSE pairs (should be below mean={pre['mean_all']}):")
    for row in pre["expected_close"]:
        flag = "OK" if row["d"] < pre["mean_all"] else "??"
        print(f"    [{flag}] {row['pair']:<88} d={row['d']}")
    print(f"  Expected FAR pairs (should be above mean={pre['mean_all']}):")
    for row in pre["expected_far"]:
        flag = "OK" if row["d"] > pre["mean_all"] else "??"
        print(f"    [{flag}] {row['pair']:<88} d={row['d']}")
    print()

    print("  --- Pi_exchange per seed (centered sigmoid over 8 priors) ---")
    pi_vals: List[Dict] = []
    for s in seeds:
        pi = pi_exchange(s)
        pi_vals.append({"seed_id": s.seed_id, "pi": round(pi, 4)})
        bar = "#" * int(pi * 40)
        print(f"  {s.seed_id:<42}  Pi={pi:.4f}  {bar}")
    print()

    print("  --- Running council stabilization (alpha=0.15, max_iter=50) ---")
    stabilized, trajectory = stabilize(seeds, alpha=0.15, max_iter=50)
    print(f"  Iterations:      {len(trajectory)}")
    print(f"  First 5 drifts:  {[round(d, 5) for d in trajectory[:5]]}")
    print(f"  Last 5 drifts:   {[round(d, 5) for d in trajectory[-5:]]}")
    print(f"  Final drift:     {round(trajectory[-1], 6)}")
    print()

    D1 = pairwise(stabilized)
    post = report(stabilized, D1, "post")

    print("  --- Post-Stabilization ---")
    print(f"  Frobenius:           {post['frobenius']}  (delta {post['frobenius'] - pre['frobenius']:+.4f})")
    print(f"  Mean (all pairs):    {post['mean_all']}  (delta {post['mean_all'] - pre['mean_all']:+.4f})")
    print(f"  Intra-source mean:   {post['mean_intra_source']}  (delta {post['mean_intra_source'] - pre['mean_intra_source']:+.4f})")
    print(f"  Inter-source mean:   {post['mean_inter_source']}  (delta {post['mean_inter_source'] - pre['mean_inter_source']:+.4f})")
    print(f"  Intra-cutover mean:  {post['mean_intra_cutover']}  (delta {post['mean_intra_cutover'] - pre['mean_intra_cutover']:+.4f})")
    print(f"  Inter-cutover mean:  {post['mean_inter_cutover']}  (delta {post['mean_inter_cutover'] - pre['mean_inter_cutover']:+.4f})")
    print(f"  Expected CLOSE pairs after stabilization:")
    for row in post["expected_close"]:
        flag = "OK" if row["d"] < post["mean_all"] else "??"
        print(f"    [{flag}] {row['pair']:<88} d={row['d']}")
    print(f"  Expected FAR pairs after stabilization:")
    for row in post["expected_far"]:
        flag = "OK" if row["d"] > post["mean_all"] else "??"
        print(f"    [{flag}] {row['pair']:<88} d={row['d']}")
    print()

    # Summarize verdict
    close_hit_pre = sum(1 for r in pre["expected_close"] if r["d"] < pre["mean_all"])
    close_total = len(pre["expected_close"])
    far_hit_pre = sum(1 for r in pre["expected_far"] if r["d"] > pre["mean_all"])
    far_total = len(pre["expected_far"])
    close_hit_post = sum(1 for r in post["expected_close"] if r["d"] < post["mean_all"])
    far_hit_post = sum(1 for r in post["expected_far"] if r["d"] > post["mean_all"])

    cutover_separates_pre = pre["mean_inter_cutover"] > pre["mean_intra_cutover"]
    cutover_separates_post = post["mean_inter_cutover"] > post["mean_intra_cutover"]

    print("  --- Verdict ---")
    print(f"  Expected CLOSE recall:   pre {close_hit_pre}/{close_total}  post {close_hit_post}/{close_total}")
    print(f"  Expected FAR recall:     pre {far_hit_pre}/{far_total}  post {far_hit_post}/{far_total}")
    print(f"  Cutover-flag separation: pre {'yes' if cutover_separates_pre else 'no'}  post {'yes' if cutover_separates_post else 'no'}")
    print(f"  Contraction converged:   {'yes' if trajectory[-1] < 1e-4 else 'still drifting'}")
    print()

    results = {
        "seeds_loaded": len(seeds),
        "iterations": len(trajectory),
        "drift_trajectory": [round(d, 6) for d in trajectory],
        "pre": pre,
        "post": post,
        "pi_exchange_per_seed": pi_vals,
        "stabilized_u": [
            {"seed_id": s.seed_id, "u": [round(float(x), 4) for x in s.u.tolist()]}
            for s in stabilized
        ],
        "verdict": {
            "close_recall_pre": f"{close_hit_pre}/{close_total}",
            "close_recall_post": f"{close_hit_post}/{close_total}",
            "far_recall_pre": f"{far_hit_pre}/{far_total}",
            "far_recall_post": f"{far_hit_post}/{far_total}",
            "cutover_separation_pre": cutover_separates_pre,
            "cutover_separation_post": cutover_separates_post,
            "converged": bool(trajectory[-1] < 1e-4),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"  Results written to: {out_path}")
    print()
    print("=" * 76)
    print("  COUNCIL SIM COMPLETE")
    print("=" * 76)


if __name__ == "__main__":
    main()
