"""
Automated Governance Scorer — Score, Verify, Prove
====================================================

Automated pipeline that:
1. Scores any agent action through the full 7-layer World Tree metric
2. Accumulates value via GovernanceCoin
3. Mints immutable ContextCredits as proof-of-score
4. Verifies integrity via hash chain + trajectory analysis

This is the product. The scoring IS the business.

Usage:
    scorer = GovernanceScorer()
    result = scorer.score_action(agent_id, action_text, tongue_profile)
    # result contains: score, decision, credit, coin_state, integrity_proof

Patent: USPTO #63/961,403
Author: Issac Davis
"""

import hashlib
import json
import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .langues_metric import (
    FluxingLanguesMetric,
    DimensionFlux,
    GovernanceCoin,
    HyperspacePoint,
    IdealState,
    langues_value,
    TONGUES,
    TONGUE_WEIGHTS,
)

from .geodesic_gateways import (
    WorldTreeMetric,
    hausdorff_roughness,
    classify_intent_roughness,
    emotional_valence,
)


# =============================================================================
# Scoring Decision Tiers
# =============================================================================

DECISION_TIERS = {
    "ALLOW": {"min_value": 0.05, "max_roughness": 2.0},
    "QUARANTINE": {"min_value": 0.01, "max_roughness": 3.0},
    "REVIEW": {"min_value": 0.005, "max_roughness": 4.0},
    "DENY": {"min_value": 0.0, "max_roughness": float("inf")},
}


def decide_from_score(value: float, roughness: float = 1.0) -> str:
    """Map governance value + roughness to a decision tier."""
    if roughness > 4.0:
        return "DENY"
    if roughness > 3.0:
        return "REVIEW"
    if value >= 0.05 and roughness <= 2.0:
        return "ALLOW"
    if value >= 0.01:
        return "QUARANTINE"
    if value >= 0.005:
        return "REVIEW"
    return "DENY"


# =============================================================================
# Integrity Proof
# =============================================================================

@dataclass(frozen=True)
class IntegrityProof:
    """
    Cryptographic proof that a score is authentic and untampered.

    Contains:
      - The full scoring breakdown (all 7 L components)
      - The governance decision
      - A blake2s hash binding all fields together
      - Timestamp for ordering
      - Agent trajectory fingerprint (Hausdorff D_H)

    To verify: recompute the hash from all other fields.
    If it matches, the score is authentic.
    """

    proof_id: str
    agent_id: str
    timestamp: float
    L_total: float
    L_components: Dict[str, float]
    value: float
    decision: str
    emotional_valence: float
    roughness: float
    coin_total: float
    lyapunov_trace: float
    lyapunov_stable: bool
    hash: str

    def verify(self) -> bool:
        """Recompute hash and check integrity."""
        expected = _compute_proof_hash(
            self.proof_id,
            self.agent_id,
            self.timestamp,
            self.L_total,
            self.L_components,
            self.value,
            self.decision,
            self.emotional_valence,
            self.roughness,
            self.coin_total,
            self.lyapunov_trace,
        )
        return self.hash == expected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "L_total": round(self.L_total, 6),
            "L_components": {k: round(v, 6) for k, v in self.L_components.items()},
            "value": round(self.value, 6),
            "decision": self.decision,
            "emotional_valence": round(self.emotional_valence, 4),
            "roughness": round(self.roughness, 4),
            "coin_total": round(self.coin_total, 6),
            "lyapunov_trace": round(self.lyapunov_trace, 6),
            "lyapunov_stable": self.lyapunov_stable,
            "hash": self.hash,
            "verified": self.verify(),
        }


def _compute_proof_hash(
    proof_id: str,
    agent_id: str,
    timestamp: float,
    L_total: float,
    L_components: Dict[str, float],
    value: float,
    decision: str,
    emotional_valence: float,
    roughness: float,
    coin_total: float,
    lyapunov_trace: float,
) -> str:
    """Deterministic hash binding all score fields."""
    payload = json.dumps(
        {
            "proof_id": proof_id,
            "agent_id": agent_id,
            "timestamp": f"{timestamp:.17g}",
            "L_total": f"{L_total:.17g}",
            "L_components": {k: f"{v:.17g}" for k, v in sorted(L_components.items())},
            "value": f"{value:.17g}",
            "decision": decision,
            "emotional_valence": f"{emotional_valence:.17g}",
            "roughness": f"{roughness:.17g}",
            "coin_total": f"{coin_total:.17g}",
            "lyapunov_trace": f"{lyapunov_trace:.17g}",
        },
        sort_keys=True,
    )
    return hashlib.blake2s(payload.encode(), digest_size=32).hexdigest()


# =============================================================================
# Governance Scorer (the product)
# =============================================================================

@dataclass
class GovernanceScorer:
    """
    Automated governance scoring engine.

    Scores every agent action through the full 7-layer World Tree,
    accumulates value via GovernanceCoin, and produces tamper-proof
    IntegrityProofs for every score.

    This is the sellable API:
      scorer.score_action(agent_id, tongue_state) -> ScoringResult
    """

    world_tree: WorldTreeMetric = field(default_factory=WorldTreeMetric)
    coins: Dict[str, GovernanceCoin] = field(default_factory=dict)
    trajectories: Dict[str, List[List[float]]] = field(default_factory=dict)
    proofs: List[IntegrityProof] = field(default_factory=list)
    max_trajectory_len: int = 200

    def _get_coin(self, agent_id: str) -> GovernanceCoin:
        """Get or create a GovernanceCoin for an agent."""
        if agent_id not in self.coins:
            self.coins[agent_id] = GovernanceCoin.fresh()
        return self.coins[agent_id]

    def _track_trajectory(self, agent_id: str, state: HyperspacePoint) -> List[List[float]]:
        """Track agent trajectory for Hausdorff roughness analysis."""
        if agent_id not in self.trajectories:
            self.trajectories[agent_id] = []
        traj = self.trajectories[agent_id]
        traj.append(state.to_vector())
        if len(traj) > self.max_trajectory_len:
            traj.pop(0)
        return traj

    def score_action(
        self,
        agent_id: str,
        state: HyperspacePoint,
        t: float = 0.0,
        dt: float = 0.01,
    ) -> Dict[str, Any]:
        """
        Score a single agent action through the full World Tree.

        Returns a complete scoring result with:
          - All 7 L components + L_total
          - Governance value V = 1/(1+L)
          - Decision tier (ALLOW/QUARANTINE/REVIEW/DENY)
          - GovernanceCoin state (accumulated value, voting weight)
          - Trajectory roughness (Hausdorff D_H)
          - Lyapunov stability diagnostic
          - Tamper-proof IntegrityProof
        """
        # 1. Score through World Tree (7 layers)
        tree_result = self.world_tree.compute_total(state, t, dt)

        # 2. Track trajectory + compute roughness
        traj = self._track_trajectory(agent_id, state)
        if len(traj) >= 3:
            D_H = hausdorff_roughness(traj)
            roughness_class, _ = classify_intent_roughness(D_H)
        else:
            D_H = 1.0
            roughness_class = "SMOOTH"

        # 3. Make decision
        decision = decide_from_score(tree_result["value"], D_H)

        # 4. Accumulate governance coin (only for non-DENY actions)
        coin = self._get_coin(agent_id)
        if decision != "DENY":
            coin.accumulate(state, self.world_tree.langues, dt)

        # 5. Build integrity proof
        lyap = tree_result["lyapunov"]
        L_components = {
            "L_f": tree_result["L_f"],
            "L_gate": tree_result["L_gate"],
            "L_fractal": tree_result["L_fractal"],
            "L_emotional": tree_result["L_emotional"],
            "L_eggs": tree_result["L_eggs"],
            "L_rh": tree_result["L_rh"],
        }

        proof_id = str(uuid.uuid4())[:12]
        ts = time.time()

        proof_hash = _compute_proof_hash(
            proof_id=proof_id,
            agent_id=agent_id,
            timestamp=ts,
            L_total=tree_result["L_total"],
            L_components=L_components,
            value=tree_result["value"],
            decision=decision,
            emotional_valence=tree_result["emotional_valence"],
            roughness=D_H,
            coin_total=coin.total,
            lyapunov_trace=lyap["trace"],
        )

        proof = IntegrityProof(
            proof_id=proof_id,
            agent_id=agent_id,
            timestamp=ts,
            L_total=tree_result["L_total"],
            L_components=L_components,
            value=tree_result["value"],
            decision=decision,
            emotional_valence=tree_result["emotional_valence"],
            roughness=D_H,
            coin_total=coin.total,
            lyapunov_trace=lyap["trace"],
            lyapunov_stable=lyap["is_stable"],
            hash=proof_hash,
        )
        self.proofs.append(proof)

        return {
            "agent_id": agent_id,
            "decision": decision,
            "value": tree_result["value"],
            "L_total": tree_result["L_total"],
            "L_components": L_components,
            "emotional_state": tree_result["emotional_state"],
            "emotional_valence": tree_result["emotional_valence"],
            "roughness": D_H,
            "roughness_class": roughness_class,
            "nearest_geodesic": tree_result["nearest_geodesic"],
            "egg_profile": tree_result["egg_profile"],
            "coin": {
                "total": coin.total,
                "voting_weight": coin.voting_weight,
                "mean_value": coin.mean_value,
                "tongue_profile": coin.tongue_profile,
            },
            "lyapunov": lyap,
            "proof": proof.to_dict(),
        }

    def verify_proof(self, proof_dict: Dict[str, Any]) -> bool:
        """Verify an integrity proof from its dict representation."""
        return _compute_proof_hash(
            proof_id=proof_dict["proof_id"],
            agent_id=proof_dict["agent_id"],
            timestamp=proof_dict["timestamp"],
            L_total=proof_dict["L_total"],
            L_components=proof_dict["L_components"],
            value=proof_dict["value"],
            decision=proof_dict["decision"],
            emotional_valence=proof_dict["emotional_valence"],
            roughness=proof_dict["roughness"],
            coin_total=proof_dict["coin_total"],
            lyapunov_trace=proof_dict["lyapunov_trace"],
        ) == proof_dict["hash"]

    def agent_report(self, agent_id: str) -> Dict[str, Any]:
        """Generate a governance report for an agent."""
        coin = self.coins.get(agent_id)
        agent_proofs = [p for p in self.proofs if p.agent_id == agent_id]

        if not agent_proofs:
            return {"agent_id": agent_id, "actions_scored": 0}

        decisions = [p.decision for p in agent_proofs]
        return {
            "agent_id": agent_id,
            "actions_scored": len(agent_proofs),
            "decision_distribution": {
                d: decisions.count(d) for d in set(decisions)
            },
            "mean_value": sum(p.value for p in agent_proofs) / len(agent_proofs),
            "mean_roughness": sum(p.roughness for p in agent_proofs) / len(agent_proofs),
            "coin": coin.to_dict() if coin else None,
            "all_proofs_valid": all(p.verify() for p in agent_proofs),
            "latest_lyapunov_stable": agent_proofs[-1].lyapunov_stable,
        }
