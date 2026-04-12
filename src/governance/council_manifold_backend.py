"""Council Manifold Backend — flight 010.

Production port of the council router experiment from .scbe/grounding/.
Wires the stabilized 10-seed council manifold into runtime_gate.py as a
third overlay tier behind the classifier and trichromatic engine.

The math primitives (Seed, d_mixed, pi_exchange, stabilize) are ported
verbatim from .scbe/grounding/council_sim.py. The routing policy and
z_adversarial_score come from .scbe/grounding/council_router.py. The
new contribution is:

  1. lift_6d_to_21d: adapter that takes the runtime_gate's 6D tongue
     coordinates plus session state (trust_history, cumulative_cost,
     null_anomaly, spin_magnitude, query_count) and produces a 21D
     Seed that the router can evaluate.

  2. CouncilManifoldBackend: class that loads and stabilizes the seed
     set on init, then exposes decide(...) returning a (Decision, signals)
     pair that slots into runtime_gate's _escalate_decision overlay stack.

Tier mapping to runtime_gate Decision enum:
  ALLOW      -> Decision.ALLOW
  QUARANTINE -> Decision.QUARANTINE
  ESCALATE   -> Decision.REVIEW      (6-council deep inspection)
  DENY       -> Decision.DENY
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import numpy as np

if TYPE_CHECKING:
    from .runtime_gate import Decision

# ---- Constants (from council_seed_schema $defs.mixed_metric) ----
PHI = (1 + math.sqrt(5)) / 2
W_H = PHI
W_T = 1.0
W_Z = np.array([0.5, 0.5, 0.5, 1.0, 1.0, 0.8, 0.6, 0.6, 0.8])
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")

# Runtime gate tongue coords can hit ball boundaries (0.0, 1.0) that blow up
# hyperbolic distance. Seed cluster centers live in roughly [0.2, 0.8] range,
# so we rescale runtime coords into the seed interior band before routing.
SEED_INTERIOR_LO = 0.22
SEED_INTERIOR_HI = 0.78

# ---- Routing policy (calibrated against flight 007 post-stab geometry) ----
DIST_ALLOW_MAX = 0.879         # within an intra-cutover neighborhood
DIST_QUARANTINE_MAX = 2.1485   # within the overall manifold mean
DIST_DENY_MIN = 3.3            # beyond the far-pair baseline
PI_QUARANTINE = 0.75           # high cross-channel density
Z_ESCALATE = 0.65              # adversarial z-signature threshold

SCRUTINY_CUTOVERS = frozenset({
    "ame_cutover",
    "post_ame_divine",
    "post_thread_quantum",
    "product_spec",
})
PERMISSIVE_CUTOVERS = frozenset({
    "pre_ame_substrate",
    "persona_scaffold",
})

DEFAULT_SEEDS_PATH = (
    Path(__file__).resolve().parents[2] / ".scbe" / "grounding" / "council_seeds.json"
)


# ---- Core dataclass (ported verbatim from council_sim.py) ----
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


# ---- Metric primitives (ported verbatim from council_sim.py) ----
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


def pi_exchange(seed: Seed) -> float:
    channels = list(seed.pi_priors.values())
    z = sum(channels) / len(channels)
    return 1.0 / (1.0 + math.exp(-(z - 0.5) * 6))


# ---- Stabilization (ported verbatim from council_sim.py) ----
def stabilize(
    seeds: List[Seed], alpha: float = 0.15, max_iter: int = 50
) -> Tuple[List[Seed], List[float]]:
    """Council vote: each seed's u pulled toward tag-affine neighbors' weighted mean."""
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


# ---- Z-vector scrutiny (ported from council_router.py) ----
def z_adversarial_score(z: np.ndarray) -> float:
    """Weighted combination of z channels that spike for adversarial drift.

    Channels:
      z[3] trust_norm       -- LOW trust raises score
      z[4] intent_polarity  -- LOW or NEGATIVE intent raises score
      z[5] null_pressure    -- HIGH null raises score
      z[8] triadic_distance -- HIGH triadic (long-horizon drift) raises score
    """
    trust = float(z[3])
    intent = float(z[4])
    null_p = float(z[5])
    triadic = float(z[8]) / math.pi  # normalize to [0,1]

    trust_term = max(0.0, 0.5 - trust) * 2
    intent_term = max(0.0, -intent) + max(0.0, 0.3 - intent)
    null_term = max(0.0, null_p - 0.5) * 2
    triadic_term = max(0.0, triadic - 0.5) * 2

    return min(
        1.0,
        0.35 * trust_term + 0.25 * intent_term + 0.25 * null_term + 0.15 * triadic_term,
    )


# ---- Routing (ported from council_router.py) ----
@dataclass
class RoutingDecision:
    tier: str                # ALLOW / QUARANTINE / ESCALATE / DENY
    nearest_seed: str
    nearest_d: float
    nearest_cutover: str
    probe_pi: float
    z_adv: float
    reasons: List[str]


def route(
    probe: Seed,
    seeds: List[Seed],
    *,
    dist_scale: float = 1.0,
) -> RoutingDecision:
    distances: List[Tuple[str, float, str]] = []
    for s in seeds:
        distances.append((s.seed_id, d_mixed(probe, s), s.cutover_flag))
    distances.sort(key=lambda x: x[1])

    nearest_id, nearest_d, nearest_cutover = distances[0]
    probe_pi = pi_exchange(probe)
    z_adv = z_adversarial_score(probe.z)
    reasons: List[str] = []

    allow_max = DIST_ALLOW_MAX * dist_scale
    quarantine_max = DIST_QUARANTINE_MAX * dist_scale
    deny_min = DIST_DENY_MIN * dist_scale

    # Rule 1: way out of manifold -> DENY
    if nearest_d >= deny_min:
        reasons.append(f"nearest_d={nearest_d:.3f} >= DENY threshold {deny_min:.3f}")
        tier = "DENY"
    # Rule 2: strong adversarial z signature -> ESCALATE regardless of distance
    elif z_adv >= Z_ESCALATE:
        reasons.append(f"z_adv={z_adv:.3f} >= {Z_ESCALATE} (low trust + null + bad intent)")
        tier = "ESCALATE"
    # Rule 3: inside intra-cutover neighborhood AND permissive cutover AND benign Pi -> ALLOW
    elif (
        nearest_d <= allow_max
        and nearest_cutover in PERMISSIVE_CUTOVERS
        and probe_pi < PI_QUARANTINE
    ):
        reasons.append(
            f"nearest_d={nearest_d:.3f} <= {allow_max:.3f}, "
            f"cutover={nearest_cutover} permissive, Pi={probe_pi:.3f} benign"
        )
        tier = "ALLOW"
    # Rule 4: inside intra-cutover AND scrutiny cutover -> QUARANTINE even if close
    elif nearest_d <= allow_max and nearest_cutover in SCRUTINY_CUTOVERS:
        reasons.append(
            f"nearest_d={nearest_d:.3f} close, but cutover={nearest_cutover} is scrutiny"
        )
        tier = "QUARANTINE"
    # Rule 5: high Pi in any region -> QUARANTINE
    elif probe_pi >= PI_QUARANTINE:
        reasons.append(f"Pi_exchange={probe_pi:.3f} >= {PI_QUARANTINE}")
        tier = "QUARANTINE"
    # Rule 6: drifting away from all clusters but not over DENY line -> ESCALATE
    elif nearest_d >= quarantine_max:
        reasons.append(
            f"nearest_d={nearest_d:.3f} >= QUARANTINE_MAX {quarantine_max:.3f}, drifting edge"
        )
        tier = "ESCALATE"
    # Default: mild drift inside the manifold -> QUARANTINE
    else:
        reasons.append(
            f"nearest_d={nearest_d:.3f} inside manifold but not in intra-cutover neighborhood"
        )
        tier = "QUARANTINE"

    return RoutingDecision(
        tier=tier,
        nearest_seed=nearest_id,
        nearest_d=round(nearest_d, 4),
        nearest_cutover=nearest_cutover,
        probe_pi=round(probe_pi, 4),
        z_adv=round(z_adv, 4),
        reasons=reasons,
    )


# ---- 6D -> 21D lift (the new contribution) ----
def lift_6d_to_21d(
    tongue_coords: List[float],
    *,
    trust_level_idx: int = 0,
    null_anomaly: float = 0.0,
    cumulative_cost: float = 0.0,
    spin_magnitude: int = 0,
    query_count: int = 0,
    classifier_score: Optional[float] = None,
    trichromatic_risk: Optional[float] = None,
) -> Seed:
    """Build a 21D probe Seed from runtime_gate session state.

    The runtime gate operates in 6D tongue-coord space. The council
    manifold needs 21D (u, theta, z). This adapter derives the missing
    15 dimensions from the session's governance signals.

    u (6D):      tongue coords clamped to (-0.999, 0.999) for Poincare ball
    theta (6D):  phase angles from query_count + per-dim offset
    z (9D):      [chaosdev, fractaldev, energydev, trust_norm, intent_polarity,
                  null_pressure, spectral_coherence, spin_magnitude_norm,
                  triadic_distance]
    """
    # u: rescale runtime tongue coords from [0,1] into the seed interior band
    # so boundary-hitting coords don't blow up hyperbolic distance
    raw_u = np.clip(np.array(tongue_coords, dtype=float), 0.0, 1.0)
    u = SEED_INTERIOR_LO + raw_u * (SEED_INTERIOR_HI - SEED_INTERIOR_LO)

    # theta: evolve with query count, phi-staggered per dimension
    theta = np.array(
        [(query_count * 0.1 + i * 1.05) % (2 * math.pi) for i in range(6)],
        dtype=float,
    )

    # z: lift 9 governance channels
    # trust_level_idx runs 0..N where higher = more trusted (Fibonacci)
    trust_norm = max(0.0, min(1.0, 0.4 + 0.08 * trust_level_idx))
    # intent_polarity: derive from classifier+trichromatic if present, else benign
    if classifier_score is not None or trichromatic_risk is not None:
        cscore = classifier_score or 0.0
        tscore = trichromatic_risk or 0.0
        intent_polarity = max(-1.0, min(1.0, 0.3 - 0.8 * max(cscore, tscore)))
    else:
        intent_polarity = 0.3
    null_pressure = max(0.0, min(1.0, null_anomaly))
    # spin magnitude norm: spin int usually 0..6 range
    spin_norm = max(0.0, min(1.0, spin_magnitude / 6.0))
    # triadic: cumulative_cost scales into (0, pi), saturating at cost ~ 10
    triadic = min(math.pi, cumulative_cost * math.pi / 10.0)

    # chaosdev / fractaldev / energydev: derive from tongue coord variance
    coord_std = float(np.std(u))
    chaosdev = min(1.0, coord_std * 2.0)
    fractaldev = min(1.0, abs(float(np.mean(u))) * 2.0)
    energydev = min(1.0, coord_std + abs(float(np.mean(u))))

    z = np.array(
        [
            chaosdev,
            fractaldev,
            energydev,
            trust_norm,
            intent_polarity,
            null_pressure,
            0.5,          # spectral_coherence placeholder (would come from L9-10)
            spin_norm,
            triadic,
        ],
        dtype=float,
    )

    # pi_priors: flat benign defaults, bumped by overlay scores if present
    base_pi = 0.5
    if classifier_score is not None:
        base_pi = min(0.95, base_pi + 0.4 * classifier_score)
    if trichromatic_risk is not None:
        base_pi = min(0.95, base_pi + 0.4 * trichromatic_risk)
    pi_priors = {
        "geometry": base_pi,
        "triadic": base_pi,
        "spin": base_pi,
        "spectral": base_pi,
        "pivot": base_pi,
        "trust": 1.0 - base_pi,
        "null_pressure": base_pi,
        "risk": base_pi,
    }

    return Seed(
        seed_id="runtime_probe",
        source_id="runtime_gate",
        cutover_flag="probe",   # never matches permissive or scrutiny
        u=u,
        theta=theta,
        z=z,
        pi_priors=pi_priors,
        tags=[],
    )


# ---- Tier -> Decision mapping (lazy to avoid circular import) ----
def _tier_to_decision(tier: str) -> Any:
    from .runtime_gate import Decision
    return {
        "ALLOW": Decision.ALLOW,
        "QUARANTINE": Decision.QUARANTINE,
        "ESCALATE": Decision.REVIEW,   # 6-council deep inspection
        "DENY": Decision.DENY,
    }[tier]


# ---- Public backend class ----
class CouncilManifoldBackend:
    """Stabilized council manifold as a runtime_gate overlay backend.

    Loads the 10-seed council from .scbe/grounding/council_seeds.json,
    stabilizes it once, then serves decisions on demand.
    """

    def __init__(
        self,
        seeds_path: Optional[Path] = None,
        alpha: float = 0.15,
        max_iter: int = 50,
        dist_scale: float = 2.85,
    ) -> None:
        """
        dist_scale: per-backend multiplier on DIST_ALLOW_MAX / DIST_QUARANTINE_MAX
        / DIST_DENY_MIN. Lore-coord space (scale=1.0) produces tight distances
        because seeds are authored to live close together. Runtime_gate's
        text_to_coords produces statistical projections ~2-3x further from
        cluster centers, so the routing thresholds need to adapt. The default
        2.85 is calibrated so a benign runtime probe at d~=3.0 falls inside
        the scaled ALLOW band (2.505) rather than triggering ESCALATE.
        """
        path = seeds_path if seeds_path is not None else DEFAULT_SEEDS_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"Council seed file not found at {path}. "
                "Run .scbe/grounding/council_sim.py to generate it."
            )
        raw_seeds = load_seeds(path)
        self.seeds, self.trajectory = stabilize(
            raw_seeds, alpha=alpha, max_iter=max_iter
        )
        self.converged = bool(self.trajectory and self.trajectory[-1] < 1e-4)
        self._dist_scale = float(dist_scale)

    def decide(
        self,
        tongue_coords: List[float],
        *,
        trust_level_idx: int = 0,
        null_anomaly: float = 0.0,
        cumulative_cost: float = 0.0,
        spin_magnitude: int = 0,
        query_count: int = 0,
        classifier_score: Optional[float] = None,
        trichromatic_risk: Optional[float] = None,
    ) -> Tuple[Decision, List[str], RoutingDecision]:
        """Lift 6D coords to 21D, route against the stabilized manifold,
        and return (Decision, signals, routing_detail)."""
        probe = lift_6d_to_21d(
            tongue_coords,
            trust_level_idx=trust_level_idx,
            null_anomaly=null_anomaly,
            cumulative_cost=cumulative_cost,
            spin_magnitude=spin_magnitude,
            query_count=query_count,
            classifier_score=classifier_score,
            trichromatic_risk=trichromatic_risk,
        )
        routing = route(probe, self.seeds, dist_scale=self._dist_scale)
        decision = _tier_to_decision(routing.tier)

        signals: List[str] = [
            f"council_manifold_tier={routing.tier}",
            f"council_manifold_nearest={routing.nearest_seed}",
            f"council_manifold_d={routing.nearest_d:.3f}",
            f"council_manifold_z_adv={routing.z_adv:.3f}",
        ]
        signals.extend(f"council_manifold_reason:{r}" for r in routing.reasons)
        return decision, signals, routing
