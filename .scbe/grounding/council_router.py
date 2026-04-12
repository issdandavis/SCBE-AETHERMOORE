"""Council Governance Router -- flight 008.

Takes the stabilized 10-seed council manifold from loop 007 and routes probe
inputs to ALLOW / QUARANTINE / ESCALATE / DENY using nearest-seed distance in
the mixed metric, cutover-flag policy, Pi_exchange, and z-vector scrutiny.

This is a STANDALONE sim. It does not touch src/governance/runtime_gate.py --
the point of the experiment is to verify that the council manifold itself can
carry routing decisions BEFORE we wire it into the real RuntimeGate.

Design choices:

* Post-stabilization u has collapsed to three clusters (izack_substrate,
  ame_divine, codex_spec), so the router uses the FULL mixed metric (u + theta
  + z), not just u. The discriminating signal for within-cluster placement
  lives in theta (phase drift) and z (governance channels).
* Nearest-seed distance in the stabilized manifold is the first line of
  defense. If an input is too far from EVERY seed, it is out of manifold.
* cutover_flag is treated as a hard policy axis: pre_ame_substrate and
  persona_scaffold are permissive, ame_cutover + post_ame_divine +
  post_thread_quantum are scrutiny tiers.
* z-vector scrutiny: low trust_norm + high null_pressure + high triadic
  distance = adversarial drift signature. This maps to ESCALATE.
* Pi_exchange >= 0.75 in a scrutiny cutover region maps to QUARANTINE
  (high cross-channel density, not obviously hostile but not obviously safe).

Run from repo root:
    python .scbe/grounding/council_router.py
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from council_sim import (
    PHI,
    Seed,
    d_mixed,
    load_seeds,
    pi_exchange,
    stabilize,
)

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS_PATH = os.path.join(HERE, "council_seeds.json")
PROBES_PATH = os.path.join(HERE, "council_probes.json")
RESULTS_PATH = os.path.join(HERE, "council_router_results.json")


# ---- Routing policy ----
# Thresholds are calibrated against loop 007 results:
#   post-stab mean_all_pairs = 2.1485
#   post-stab intra_cutover_mean = 0.879
#   post-stab inter_cutover_mean = 2.5113

DIST_ALLOW_MAX = 0.879  # within an intra-cutover neighborhood
DIST_QUARANTINE_MAX = 2.1485  # within the overall manifold mean
DIST_DENY_MIN = 3.3  # beyond the far-pair baseline, genuinely out of manifold

PI_QUARANTINE = 0.75  # high cross-channel density

SCRUTINY_CUTOVERS = {
    "ame_cutover",
    "post_ame_divine",
    "post_thread_quantum",
    "product_spec",
}
PERMISSIVE_CUTOVERS = {
    "pre_ame_substrate",
    "persona_scaffold",
}


def z_adversarial_score(z: List[float]) -> float:
    """Weighted combination of z channels that should spike for adversarial drift.

    Returns a scalar in roughly [0, 1]. Higher = more adversarial-looking.

    Channels used:
      z[3] trust_norm -- LOW trust raises score
      z[4] intent_polarity -- LOW or NEGATIVE intent raises score
      z[5] null_pressure -- HIGH null raises score
      z[8] triadic_distance -- HIGH triadic (long-horizon drift) raises score
    """
    trust = z[3]
    intent = z[4]
    null_p = z[5]
    triadic = z[8] / math.pi  # normalize to [0,1]

    trust_term = max(0.0, 0.5 - trust) * 2  # spikes when trust < 0.5
    intent_term = max(0.0, -intent) + max(0.0, 0.3 - intent)  # spikes when low benign
    null_term = max(0.0, null_p - 0.5) * 2  # spikes when null > 0.5
    triadic_term = max(0.0, triadic - 0.5) * 2  # spikes when triadic > pi/2

    return min(1.0, 0.35 * trust_term + 0.25 * intent_term + 0.25 * null_term + 0.15 * triadic_term)


@dataclass
class Probe:
    probe_id: str
    label: str
    canonical_text: str
    lift_rationale: str
    u: List[float]
    theta: List[float]
    z: List[float]
    pi_priors: Dict[str, float]
    expected_tier: str

    def as_seed(self) -> Seed:
        return Seed(
            seed_id=self.probe_id,
            source_id="probe",
            cutover_flag="probe",
            u=np.array(self.u, dtype=float),
            theta=np.array(self.theta, dtype=float),
            z=np.array(self.z, dtype=float),
            pi_priors=dict(self.pi_priors),
            tags=[],
        )


@dataclass
class RoutingDecision:
    probe_id: str
    label: str
    nearest_seed: str
    nearest_d: float
    nearest_cutover: str
    second_nearest_seed: str
    second_nearest_d: float
    probe_pi: float
    z_adv: float
    tier: str
    reasons: List[str]


def route(probe: Probe, seeds: List[Seed]) -> RoutingDecision:
    p_seed = probe.as_seed()
    distances: List[Tuple[str, float, str]] = []
    for s in seeds:
        d = d_mixed(p_seed, s)
        distances.append((s.seed_id, d, s.cutover_flag))
    distances.sort(key=lambda x: x[1])

    nearest_id, nearest_d, nearest_cutover = distances[0]
    second_id, second_d, _ = distances[1]

    probe_pi = pi_exchange(p_seed)
    z_adv = z_adversarial_score(probe.z)

    reasons: List[str] = []

    # Rule 1: way out of manifold -> DENY
    if nearest_d >= DIST_DENY_MIN:
        reasons.append(f"nearest_d={nearest_d:.3f} >= DENY threshold {DIST_DENY_MIN}")
        tier = "DENY"
    # Rule 2: strong adversarial z signature -> ESCALATE regardless of distance
    elif z_adv >= 0.65:
        reasons.append(f"z_adversarial_score={z_adv:.3f} >= 0.65 (low trust + null + bad intent)")
        tier = "ESCALATE"
    # Rule 3: inside intra-cutover neighborhood AND permissive cutover AND benign Pi -> ALLOW
    elif nearest_d <= DIST_ALLOW_MAX and nearest_cutover in PERMISSIVE_CUTOVERS and probe_pi < PI_QUARANTINE:
        reasons.append(
            f"nearest_d={nearest_d:.3f} <= ALLOW max {DIST_ALLOW_MAX}, "
            f"cutover={nearest_cutover} permissive, Pi={probe_pi:.3f} benign"
        )
        tier = "ALLOW"
    # Rule 4: inside intra-cutover AND scrutiny cutover -> QUARANTINE even if close
    elif nearest_d <= DIST_ALLOW_MAX and nearest_cutover in SCRUTINY_CUTOVERS:
        reasons.append(
            f"nearest_d={nearest_d:.3f} close, but cutover={nearest_cutover} is a scrutiny tier"
        )
        tier = "QUARANTINE"
    # Rule 5: high Pi in any region -> QUARANTINE
    elif probe_pi >= PI_QUARANTINE:
        reasons.append(f"Pi_exchange={probe_pi:.3f} >= QUARANTINE threshold {PI_QUARANTINE}")
        tier = "QUARANTINE"
    # Rule 6: drifting away from all clusters but not over DENY line -> ESCALATE
    elif nearest_d >= DIST_QUARANTINE_MAX:
        reasons.append(
            f"nearest_d={nearest_d:.3f} >= QUARANTINE_MAX {DIST_QUARANTINE_MAX}, drifting edge"
        )
        tier = "ESCALATE"
    # Default: mild drift inside the manifold -> QUARANTINE
    else:
        reasons.append(
            f"nearest_d={nearest_d:.3f} inside manifold but not in intra-cutover neighborhood"
        )
        tier = "QUARANTINE"

    return RoutingDecision(
        probe_id=probe.probe_id,
        label=probe.label,
        nearest_seed=nearest_id,
        nearest_d=round(nearest_d, 4),
        nearest_cutover=nearest_cutover,
        second_nearest_seed=second_id,
        second_nearest_d=round(second_d, 4),
        probe_pi=round(probe_pi, 4),
        z_adv=round(z_adv, 4),
        tier=tier,
        reasons=reasons,
    )


def load_probes(path: str) -> List[Probe]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    out: List[Probe] = []
    for p in data["probes"]:
        out.append(
            Probe(
                probe_id=p["probe_id"],
                label=p["label"],
                canonical_text=p["canonical_text"],
                lift_rationale=p["lift_rationale"],
                u=p["u"],
                theta=p["theta"],
                z=p["z"],
                pi_priors=p["pi_exchange_priors"],
                expected_tier=p["expected_tier"],
            )
        )
    return out


def main() -> None:
    print("=" * 78)
    print("  Council Governance Router  |  21D Probe -> ALLOW/QUARANTINE/ESCALATE/DENY")
    print("=" * 78)

    raw_seeds = load_seeds(Path(SEEDS_PATH))
    print(f"  Loaded {len(raw_seeds)} seeds from {os.path.basename(SEEDS_PATH)}")
    stabilized, _ = stabilize(raw_seeds, alpha=0.15, max_iter=50)
    print(f"  Stabilized seeds ready (alpha=0.15, max_iter=50)")
    print()

    probes = load_probes(PROBES_PATH)
    print(f"  Loaded {len(probes)} probes from {os.path.basename(PROBES_PATH)}")
    print()

    decisions: List[RoutingDecision] = []
    print(f"  {'probe':<26} {'tier':<11} {'expected':<11} {'near_seed':<32} {'d':>6}  {'Pi':>5}  {'z_adv':>5}")
    print("  " + "-" * 98)
    match = 0
    for p in probes:
        dec = route(p, stabilized)
        decisions.append(dec)
        marker = "OK " if dec.tier == p.expected_tier else "??"
        if dec.tier == p.expected_tier:
            match += 1
        print(
            f"  {p.probe_id[:26]:<26} {dec.tier:<11} {p.expected_tier:<11} "
            f"{dec.nearest_seed[:32]:<32} {dec.nearest_d:>6.3f}  "
            f"{dec.probe_pi:>5.3f}  {dec.z_adv:>5.3f} {marker}"
        )

    print()
    print(f"  Tier match rate: {match}/{len(probes)}")
    print()

    tier_counts: Dict[str, int] = {}
    for d in decisions:
        tier_counts[d.tier] = tier_counts.get(d.tier, 0) + 1
    print(f"  Tier distribution: {tier_counts}")
    print()

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "probe_count": len(probes),
                "match_rate": f"{match}/{len(probes)}",
                "tier_distribution": tier_counts,
                "decisions": [
                    {
                        "probe_id": d.probe_id,
                        "label": d.label,
                        "tier": d.tier,
                        "expected_tier": probes[i].expected_tier,
                        "match": d.tier == probes[i].expected_tier,
                        "nearest_seed": d.nearest_seed,
                        "nearest_d": d.nearest_d,
                        "nearest_cutover": d.nearest_cutover,
                        "second_nearest_seed": d.second_nearest_seed,
                        "second_nearest_d": d.second_nearest_d,
                        "probe_pi": d.probe_pi,
                        "z_adv_score": d.z_adv,
                        "reasons": d.reasons,
                    }
                    for i, d in enumerate(decisions)
                ],
                "policy": {
                    "DIST_ALLOW_MAX": DIST_ALLOW_MAX,
                    "DIST_QUARANTINE_MAX": DIST_QUARANTINE_MAX,
                    "DIST_DENY_MIN": DIST_DENY_MIN,
                    "PI_QUARANTINE": PI_QUARANTINE,
                    "SCRUTINY_CUTOVERS": sorted(SCRUTINY_CUTOVERS),
                    "PERMISSIVE_CUTOVERS": sorted(PERMISSIVE_CUTOVERS),
                },
            },
            f,
            indent=2,
        )
    print(f"  Results written to: {RESULTS_PATH}")
    print()
    print("=" * 78)
    print("  ROUTING RUN COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
