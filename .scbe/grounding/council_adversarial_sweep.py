"""Council Adversarial Probe Sweep -- flight 009.

Monte Carlo stress test on top of the flight 008 hand-crafted probe set.
Generates hundreds of randomized probes per behavioral category and measures:

* per-category tier match rate (does the router stay consistent as probes drift?)
* tier-flip / tier-dominance under u/theta/z noise
* rule-firing histogram (which rules catch which categories?)
* distance and z_adv distributions per tier

Flight 008 proved the router can classify a hand-picked 10-probe set at 9/10.
Flight 009 answers: does that behavior hold when we perturb u, theta, z across
hundreds of draws per category, or does the router collapse into one tier
under noise?

Run from repo root:
    python .scbe/grounding/council_adversarial_sweep.py
"""
from __future__ import annotations

import json
import math
import os
import random
from pathlib import Path
from typing import Dict, List

from council_sim import load_seeds, stabilize
from council_router import (
    Probe,
    route,
)

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS_PATH = os.path.join(HERE, "council_seeds.json")
RESULTS_PATH = os.path.join(HERE, "council_sweep_results.json")


# Cluster centers from stabilized loop 007 manifold
CLUSTER_CENTERS = {
    "izack_substrate": [0.557, 0.2434, 0.4158, 0.2592, 0.5908, 0.3631],
    "ame_divine": [0.3, 0.75, 0.3, 0.8, 0.225, 0.65],
    "codex_spec": [0.325, 0.725, 0.375, 0.75, 0.55, 0.65],
}


CATEGORIES = [
    # Benign in-cluster, permissive cutover -> ALLOW
    {
        "name": "benign_izack_substrate",
        "n": 60,
        "cluster": "izack_substrate",
        "u_sigma": 0.05,
        "z_profile": "benign",
        "pi_profile": "benign",
        "expected": "ALLOW",
        "u_mode": "cluster",
    },
    # Benign in-cluster, scrutiny cutover (ame_divine) -> QUARANTINE
    {
        "name": "benign_ame_divine",
        "n": 60,
        "cluster": "ame_divine",
        "u_sigma": 0.04,
        "z_profile": "benign",
        "pi_profile": "benign",
        "expected": "QUARANTINE",
        "u_mode": "cluster",
    },
    # Benign in-cluster, scrutiny cutover (codex_spec) -> QUARANTINE
    {
        "name": "benign_codex_spec",
        "n": 60,
        "cluster": "codex_spec",
        "u_sigma": 0.04,
        "z_profile": "benign",
        "pi_profile": "benign",
        "expected": "QUARANTINE",
        "u_mode": "cluster",
    },
    # Hard adversarial in-cluster -> ESCALATE
    {
        "name": "hard_adversarial",
        "n": 60,
        "cluster": None,
        "u_sigma": 0.05,
        "z_profile": "hard_adversarial",
        "pi_profile": "adversarial",
        "expected": "ESCALATE",
        "u_mode": "cluster",
    },
    # Soft adversarial in-cluster -> QUARANTINE (ESCALATE also acceptable)
    {
        "name": "soft_adversarial",
        "n": 60,
        "cluster": None,
        "u_sigma": 0.05,
        "z_profile": "soft_adversarial",
        "pi_profile": "high_pi",
        "expected": "QUARANTINE",
        "u_mode": "cluster",
    },
    # Out-of-manifold benign -> DENY
    {
        "name": "ood_benign",
        "n": 40,
        "cluster": None,
        "u_sigma": 0.08,
        "z_profile": "benign",
        "pi_profile": "low",
        "expected": "DENY",
        "u_mode": "ood",
    },
    # Out-of-manifold hostile -> DENY
    {
        "name": "ood_hostile",
        "n": 40,
        "cluster": None,
        "u_sigma": 0.08,
        "z_profile": "hard_adversarial",
        "pi_profile": "adversarial",
        "expected": "DENY",
        "u_mode": "ood",
    },
    # Midpoint / cross-cluster drift -> QUARANTINE (most common)
    {
        "name": "midpoint_drift",
        "n": 40,
        "cluster": None,
        "u_sigma": 0.04,
        "z_profile": "neutral",
        "pi_profile": "neutral",
        "expected": "QUARANTINE",
        "u_mode": "midpoint",
    },
]


def gen_u(category: Dict, rng: random.Random) -> List[float]:
    mode = category.get("u_mode", "cluster")
    sigma = category["u_sigma"]
    if mode == "cluster":
        if category["cluster"]:
            center = CLUSTER_CENTERS[category["cluster"]]
        else:
            center = CLUSTER_CENTERS[rng.choice(list(CLUSTER_CENTERS.keys()))]
        u = [max(-0.95, min(0.95, center[i] + rng.gauss(0, sigma))) for i in range(6)]
    elif mode == "ood":
        base = [rng.uniform(0.82, 0.93) if i % 2 == 0 else rng.uniform(0.05, 0.18) for i in range(6)]
        u = [max(-0.95, min(0.95, base[i] + rng.gauss(0, sigma))) for i in range(6)]
    elif mode == "midpoint":
        a_name = rng.choice(list(CLUSTER_CENTERS.keys()))
        b_name = rng.choice([k for k in CLUSTER_CENTERS if k != a_name])
        a = CLUSTER_CENTERS[a_name]
        b = CLUSTER_CENTERS[b_name]
        t = rng.uniform(0.3, 0.7)
        u = [a[i] * (1 - t) + b[i] * t + rng.gauss(0, sigma) for i in range(6)]
        u = [max(-0.95, min(0.95, v)) for v in u]
    else:
        raise ValueError(mode)
    return u


def gen_theta(rng: random.Random) -> List[float]:
    base = [0.3, 1.4, 2.5, 3.6, 4.7, 5.8]
    return [(base[i] + rng.gauss(0, 0.25)) % (2 * math.pi) for i in range(6)]


def gen_z(profile: str, rng: random.Random) -> List[float]:
    if profile == "benign":
        return [
            rng.uniform(0.2, 0.5),   # chaosdev
            rng.uniform(0.3, 0.6),   # fractaldev
            rng.uniform(0.4, 0.7),   # energydev
            rng.uniform(0.75, 0.95), # trust_norm HIGH
            rng.uniform(0.5, 0.9),   # intent_polarity positive
            rng.uniform(0.1, 0.3),   # null_pressure low
            rng.uniform(0.6, 0.9),   # spectral_coherence
            rng.uniform(0.4, 0.7),   # spin_magnitude
            rng.uniform(0.2, 0.6),   # triadic_distance low
        ]
    if profile == "hard_adversarial":
        return [
            rng.uniform(0.7, 0.95),
            rng.uniform(0.7, 0.9),
            rng.uniform(0.5, 0.9),
            rng.uniform(0.05, 0.3),   # trust LOW
            rng.uniform(-0.5, -0.1),  # intent NEGATIVE
            rng.uniform(0.65, 0.9),   # null HIGH
            rng.uniform(0.3, 0.6),
            rng.uniform(0.3, 0.6),
            rng.uniform(2.4, 3.0),    # triadic HIGH
        ]
    if profile == "soft_adversarial":
        return [
            rng.uniform(0.4, 0.7),
            rng.uniform(0.5, 0.8),
            rng.uniform(0.4, 0.7),
            rng.uniform(0.35, 0.55),  # trust borderline
            rng.uniform(-0.1, 0.15),  # intent weakly negative
            rng.uniform(0.55, 0.75),  # null mid-high
            rng.uniform(0.5, 0.8),
            rng.uniform(0.5, 0.8),
            rng.uniform(1.8, 2.6),    # triadic elevated
        ]
    if profile == "neutral":
        return [
            rng.uniform(0.3, 0.6),
            rng.uniform(0.4, 0.6),
            rng.uniform(0.4, 0.7),
            rng.uniform(0.6, 0.8),
            rng.uniform(0.3, 0.6),
            rng.uniform(0.3, 0.5),
            rng.uniform(0.5, 0.8),
            rng.uniform(0.4, 0.7),
            rng.uniform(0.4, 0.7),
        ]
    raise ValueError(profile)


def gen_pi(profile: str, rng: random.Random) -> Dict[str, float]:
    if profile == "benign":
        return {
            "geometry": rng.uniform(0.4, 0.75),
            "triadic": rng.uniform(0.4, 0.6),
            "spin": rng.uniform(0.4, 0.6),
            "spectral": rng.uniform(0.6, 0.85),
            "pivot": rng.uniform(0.3, 0.65),
            "trust": rng.uniform(0.75, 0.9),
            "null_pressure": rng.uniform(0.1, 0.3),
            "risk": rng.uniform(0.05, 0.25),
        }
    if profile == "adversarial":
        return {
            "geometry": rng.uniform(0.5, 0.8),
            "triadic": rng.uniform(0.7, 0.9),
            "spin": rng.uniform(0.6, 0.85),
            "spectral": rng.uniform(0.4, 0.7),
            "pivot": rng.uniform(0.7, 0.9),
            "trust": rng.uniform(0.1, 0.35),
            "null_pressure": rng.uniform(0.7, 0.9),
            "risk": rng.uniform(0.75, 0.95),
        }
    if profile == "high_pi":
        return {
            "geometry": rng.uniform(0.7, 0.9),
            "triadic": rng.uniform(0.7, 0.9),
            "spin": rng.uniform(0.7, 0.9),
            "spectral": rng.uniform(0.65, 0.85),
            "pivot": rng.uniform(0.75, 0.9),
            "trust": rng.uniform(0.4, 0.6),
            "null_pressure": rng.uniform(0.6, 0.8),
            "risk": rng.uniform(0.7, 0.9),
        }
    if profile == "low":
        return {
            "geometry": rng.uniform(0.05, 0.2),
            "triadic": rng.uniform(0.05, 0.2),
            "spin": rng.uniform(0.05, 0.2),
            "spectral": rng.uniform(0.1, 0.25),
            "pivot": rng.uniform(0.05, 0.2),
            "trust": rng.uniform(0.5, 0.7),
            "null_pressure": rng.uniform(0.15, 0.3),
            "risk": rng.uniform(0.1, 0.25),
        }
    if profile == "neutral":
        return {
            "geometry": rng.uniform(0.5, 0.7),
            "triadic": rng.uniform(0.45, 0.65),
            "spin": rng.uniform(0.45, 0.65),
            "spectral": rng.uniform(0.55, 0.75),
            "pivot": rng.uniform(0.55, 0.75),
            "trust": rng.uniform(0.6, 0.8),
            "null_pressure": rng.uniform(0.4, 0.6),
            "risk": rng.uniform(0.25, 0.45),
        }
    raise ValueError(profile)


def make_probe(category: Dict, idx: int, rng: random.Random) -> Probe:
    u = gen_u(category, rng)
    theta = gen_theta(rng)
    z = gen_z(category["z_profile"], rng)
    pi = gen_pi(category["pi_profile"], rng)
    return Probe(
        probe_id=f"{category['name']}_{idx:03d}",
        label=f"{category['name']} variant {idx}",
        canonical_text="",
        lift_rationale="",
        u=u,
        theta=theta,
        z=z,
        pi_priors=pi,
        expected_tier=category["expected"],
    )


def classify_rule(reason: str) -> str:
    """Collapse a reason string into a short rule-family tag."""
    r = reason.lower()
    if "deny threshold" in r:
        return "rule1_ood_deny"
    if "z_adversarial_score" in r:
        return "rule2_z_escalate"
    if "permissive" in r and "benign" in r:
        return "rule3_allow"
    if "scrutiny tier" in r:
        return "rule4_scrutiny_quarantine"
    if "quarantine threshold" in r.lower():
        return "rule5_pi_quarantine"
    if "drifting edge" in r:
        return "rule6_drift_escalate"
    if "inside manifold" in r:
        return "rule7_default_quarantine"
    return "unknown"


def main() -> None:
    print("=" * 78)
    print("  Council Adversarial Probe Sweep  |  Monte Carlo Stress Test")
    print("=" * 78)

    raw_seeds = load_seeds(Path(SEEDS_PATH))
    stabilized, _ = stabilize(raw_seeds, alpha=0.15, max_iter=50)
    print(f"  Loaded {len(raw_seeds)} seeds, stabilized (alpha=0.15, max_iter=50)")
    print()

    results_by_cat: Dict[str, Dict] = {}
    all_decisions: List[Dict] = []

    print(f"  {'category':<28} {'n':>4}  {'expected':<11}  {'match_rate':>10}  tier_distribution")
    print("  " + "-" * 98)

    for cat in CATEGORIES:
        cat_seed = abs(hash(cat["name"])) & 0xFFFFFFFF
        cat_rng = random.Random(cat_seed)
        match = 0
        tier_counts = {"ALLOW": 0, "QUARANTINE": 0, "ESCALATE": 0, "DENY": 0}
        rule_counts: Dict[str, int] = {}
        nearest_ds: List[float] = []
        z_advs: List[float] = []
        pi_vals: List[float] = []

        for i in range(cat["n"]):
            p = make_probe(cat, i, cat_rng)
            d = route(p, stabilized)
            tier_counts[d.tier] = tier_counts.get(d.tier, 0) + 1
            if d.tier == cat["expected"]:
                match += 1
            rule_tag = classify_rule(d.reasons[0]) if d.reasons else "unknown"
            rule_counts[rule_tag] = rule_counts.get(rule_tag, 0) + 1
            nearest_ds.append(d.nearest_d)
            z_advs.append(d.z_adv)
            pi_vals.append(d.probe_pi)
            all_decisions.append({
                "probe_id": p.probe_id,
                "category": cat["name"],
                "expected": cat["expected"],
                "tier": d.tier,
                "nearest_d": d.nearest_d,
                "z_adv": d.z_adv,
                "probe_pi": d.probe_pi,
                "nearest_seed": d.nearest_seed,
                "nearest_cutover": d.nearest_cutover,
                "rule": rule_tag,
            })

        match_rate = match / cat["n"]
        results_by_cat[cat["name"]] = {
            "n": cat["n"],
            "expected": cat["expected"],
            "match": match,
            "match_rate": round(match_rate, 3),
            "tier_distribution": tier_counts,
            "rule_firing": rule_counts,
            "nearest_d": {
                "min": round(min(nearest_ds), 3),
                "max": round(max(nearest_ds), 3),
                "mean": round(sum(nearest_ds) / len(nearest_ds), 3),
            },
            "z_adv": {
                "min": round(min(z_advs), 3),
                "max": round(max(z_advs), 3),
                "mean": round(sum(z_advs) / len(z_advs), 3),
            },
            "pi_exchange": {
                "min": round(min(pi_vals), 3),
                "max": round(max(pi_vals), 3),
                "mean": round(sum(pi_vals) / len(pi_vals), 3),
            },
        }

        tier_str = "{" + ", ".join(f"{k[:1]}:{v}" for k, v in tier_counts.items() if v > 0) + "}"
        print(f"  {cat['name']:<28} {cat['n']:>4}  {cat['expected']:<11}  "
              f"{match_rate:>10.3f}  {tier_str}")

    total_n = sum(cat["n"] for cat in CATEGORIES)
    total_match = sum(r["match"] for r in results_by_cat.values())

    # Soft match: accept QUARANTINE OR ESCALATE for soft_adversarial (both are correct)
    soft_generous = 0
    for d in all_decisions:
        if d["category"] == "soft_adversarial":
            if d["tier"] in ("QUARANTINE", "ESCALATE"):
                soft_generous += 1

    # Tier dominance per category (how often the most-common tier appears)
    tier_stability: Dict[str, Dict] = {}
    for cat_name, res in results_by_cat.items():
        tiers = res["tier_distribution"]
        max_tier = max(tiers.items(), key=lambda x: x[1])
        tier_stability[cat_name] = {
            "dominant_tier": max_tier[0],
            "dominance": round(max_tier[1] / res["n"], 3),
        }

    # Aggregate rule firing across all categories
    global_rule_firing: Dict[str, int] = {}
    for res in results_by_cat.values():
        for rule, n in res["rule_firing"].items():
            global_rule_firing[rule] = global_rule_firing.get(rule, 0) + n

    print()
    print(f"  OVERALL strict match : {total_match}/{total_n} = {total_match/total_n:.3f}")
    print(f"  Soft-adversarial Q+E : {soft_generous}/60 = {soft_generous/60:.3f} "
          "(either QUARANTINE or ESCALATE is semantically correct)")
    print()
    print(f"  Global rule firing:")
    for rule in sorted(global_rule_firing.keys()):
        print(f"    {rule:<32} {global_rule_firing[rule]:>4}")
    print()

    summary = {
        "total_probes": total_n,
        "total_match_strict": total_match,
        "overall_match_rate_strict": round(total_match / total_n, 3),
        "soft_adversarial_generous": {
            "n": 60,
            "accepted": soft_generous,
            "rate": round(soft_generous / 60, 3),
            "note": "soft adversarial probes are correct at either QUARANTINE or ESCALATE",
        },
        "per_category": results_by_cat,
        "tier_stability": tier_stability,
        "global_rule_firing": global_rule_firing,
        "all_decisions": all_decisions,
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"  Results written to: {RESULTS_PATH}")
    print()
    print("=" * 78)
    print("  SWEEP RUN COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
