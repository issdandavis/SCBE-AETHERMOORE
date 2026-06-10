"""
Ternary Node Fusion — Multi-Agent Coordination in Ternary Space
================================================================

Fleet-level ternary fusion, coherence matrix, consensus protocol,
negative-base layer correction, and encoding bridges.

@module ternary_node_fusion
@layer Layer 9 (Spectral), Layer 12 (Entropy), Layer 13 (Governance)
@axiom A3: Causality (time-ordered fusion respects causal order)
@axiom A4: Symmetry (balanced ternary preserves gauge invariance)
@version 1.0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from .trinary import BalancedTernary, Trit
from .negabinary import NegaBinary
from .ternary_signed_architecture import (
    TritVector,
    SignedBinaryVector,
    SacredTongueTritBundle,
    AdversarialShadow,
    GovernanceDecision,
    sibling_coherence,
    negabase_alternating_sum,
    tri_fuse,
)

# ---------------------------------------------------------------------------
# Agent Trit State
# ---------------------------------------------------------------------------


@dataclass
class AgentTritState:
    """An agent's ternary output state for fleet-level fusion."""

    agent_id: str
    trit_output: TritVector
    tongue_bundle: Optional[SacredTongueTritBundle] = None
    polarity: Optional[SignedBinaryVector] = None
    confidence: float = 1.0
    timestamp: float = 0.0

    @property
    def is_adversarial(self) -> bool:
        if self.polarity is None:
            return False
        return self.polarity.polarity_score() < 0


# ---------------------------------------------------------------------------
# Coherence Matrix
# ---------------------------------------------------------------------------


@dataclass
class CoherenceMatrix:
    """Pairwise sibling coherence across all agent pairs."""

    agent_ids: List[str]
    matrix: List[List[float]]

    @property
    def size(self) -> int:
        return len(self.agent_ids)

    def mean_coherence(self) -> float:
        n = self.size
        if n < 2:
            return 1.0
        total = 0.0
        count = 0
        for i in range(n):
            for j in range(i + 1, n):
                total += self.matrix[i][j]
                count += 1
        return total / count if count > 0 else 0.0

    def min_coherence(self) -> float:
        n = self.size
        if n < 2:
            return 1.0
        worst = 1.0
        for i in range(n):
            for j in range(i + 1, n):
                worst = min(worst, self.matrix[i][j])
        return worst

    def max_opposition(self) -> Tuple[str, str, float]:
        n = self.size
        if n < 2:
            return ("", "", 0.0)
        worst_i, worst_j, worst_val = 0, 1, self.matrix[0][1]
        for i in range(n):
            for j in range(i + 1, n):
                if self.matrix[i][j] < worst_val:
                    worst_i, worst_j, worst_val = i, j, self.matrix[i][j]
        return (self.agent_ids[worst_i], self.agent_ids[worst_j], worst_val)

    def has_consensus(self, threshold: float = 0.5) -> bool:
        return self.min_coherence() >= threshold

    def faction_detection(self, threshold: float = 0.0) -> List[List[str]]:
        """Greedy clustering of mutually agreeing agents.

        Works on positional indices (not id lookups), so it is O(n^2)
        and robust to duplicate agent ids.
        """
        n = self.size
        assigned = [False] * n
        factions: List[List[str]] = []

        for i in range(n):
            if assigned[i]:
                continue
            member_indices = [i]
            assigned[i] = True
            for j in range(i + 1, n):
                if assigned[j]:
                    continue
                if all(self.matrix[m][j] >= threshold for m in member_indices):
                    member_indices.append(j)
                    assigned[j] = True
            factions.append([self.agent_ids[m] for m in member_indices])

        return factions


def compute_coherence_matrix(agents: Sequence[AgentTritState]) -> CoherenceMatrix:
    n = len(agents)
    ids = [a.agent_id for a in agents]
    matrix = [[0.0] * n for _ in range(n)]

    for i in range(n):
        matrix[i][i] = 1.0
        for j in range(i + 1, n):
            c = sibling_coherence(agents[i].trit_output, agents[j].trit_output)
            matrix[i][j] = c
            matrix[j][i] = c

    return CoherenceMatrix(agent_ids=ids, matrix=matrix)


# ---------------------------------------------------------------------------
# Ternary Consensus Protocol
# ---------------------------------------------------------------------------


@dataclass
class ConsensusResult:
    fused_vector: TritVector
    participating_agents: int
    mean_coherence: float
    consensus_strength: float
    contested_dimensions: List[int]
    decision: GovernanceDecision
    deferred_dimensions: List[int] = field(default_factory=list)


def ternary_consensus(
    agents: Sequence[AgentTritState],
    theta: float = 0.5,
    quorum: float = 0.0,
    coherence_matrix: Optional[CoherenceMatrix] = None,
) -> ConsensusResult:
    """Fleet-level ternary consensus across N agents.

    Args:
        agents: Agents contributing trit outputs.
        theta: Decision threshold for ``tri_fuse``.
        quorum: Minimum fraction of total confidence weight that must
            be non-abstaining (non-zero) on a dimension for it to reach
            a committed decision.  Dimensions below quorum are forced to
            0 (deferred / witness state) and recorded in
            ``deferred_dimensions``.  Defaults to 0.0 (no quorum gate).
        coherence_matrix: Optional precomputed matrix to avoid the
            O(n^2) recomputation when the caller already has one.
    """
    if not agents:
        raise ValueError("Need at least one agent for consensus")

    d = agents[0].trit_output.dim
    total_weight = sum(a.confidence for a in agents)

    if total_weight == 0:
        return ConsensusResult(
            fused_vector=TritVector.zeros(d),
            participating_agents=0,
            mean_coherence=0.0,
            consensus_strength=0.0,
            contested_dimensions=list(range(d)),
            decision=GovernanceDecision.QUARANTINE,
            deferred_dimensions=list(range(d)),
        )

    fused_values = []
    contested = []
    deferred = []
    non_zero_count = 0

    for k in range(d):
        r_k = sum(a.confidence * a.trit_output.values[k] for a in agents) / total_weight
        z_hat = tri_fuse(r_k, theta)

        # Quorum gate: a committed (non-zero) decision requires enough
        # non-abstaining weight on this dimension, else defer to witness.
        if z_hat != 0 and quorum > 0.0:
            participating = sum(a.confidence for a in agents if a.trit_output.values[k] != 0)
            if participating / total_weight < quorum:
                z_hat = 0
                deferred.append(k)

        fused_values.append(z_hat)
        if z_hat != 0:
            non_zero_count += 1
        pos_votes = sum(1 for a in agents if a.trit_output.values[k] == 1)
        neg_votes = sum(1 for a in agents if a.trit_output.values[k] == -1)
        if pos_votes > 0 and neg_votes > 0:
            contested.append(k)

    fused = TritVector(tuple(fused_values))
    consensus_strength = non_zero_count / d if d > 0 else 0.0

    if coherence_matrix is None and len(agents) >= 2:
        coherence_matrix = compute_coherence_matrix(agents)
    mean_coh = coherence_matrix.mean_coherence() if coherence_matrix else 1.0

    if d >= 6:
        bundle = SacredTongueTritBundle.from_trit_vector(TritVector(fused.values[:6]))
        decision = bundle.governance_decision()
    else:
        mean_val = sum(fused.values) / d if d > 0 else 0
        if mean_val > theta:
            decision = GovernanceDecision.ALLOW
        elif mean_val < -theta:
            decision = GovernanceDecision.DENY
        else:
            decision = GovernanceDecision.QUARANTINE

    return ConsensusResult(
        fused_vector=fused,
        participating_agents=len(agents),
        mean_coherence=mean_coh,
        consensus_strength=consensus_strength,
        contested_dimensions=contested,
        decision=decision,
        deferred_dimensions=deferred,
    )


# ---------------------------------------------------------------------------
# Negative-Base Layer Correction
# ---------------------------------------------------------------------------


@dataclass
class LayerCorrectionResult:
    raw_sum: float
    corrected_sum: float
    layer_contributions: List[float]
    dominant_polarity: str
    stability_index: float


def apply_layer_correction(
    layer_outputs: Sequence[float],
    layer_weights: Optional[Sequence[float]] = None,
) -> LayerCorrectionResult:
    """Negabase alternating correction across pipeline layers."""
    n = len(layer_outputs)
    if layer_weights is None:
        layer_weights = [1.0] * n

    raw_sum = sum(w * x for w, x in zip(layer_weights, layer_outputs))
    corrected_sum = negabase_alternating_sum(layer_outputs, layer_weights)

    contributions = []
    for d in range(n):
        sigma_d = (-1) ** d
        contributions.append(sigma_d * layer_weights[d] * layer_outputs[d])

    if abs(raw_sum) < 1e-10:
        stability = 1.0
    else:
        stability = 1.0 - abs(corrected_sum - raw_sum) / (abs(raw_sum) + abs(corrected_sum) + 1e-10)

    if corrected_sum > 0.1:
        polarity = "positive"
    elif corrected_sum < -0.1:
        polarity = "negative"
    else:
        polarity = "balanced"

    return LayerCorrectionResult(
        raw_sum=raw_sum,
        corrected_sum=corrected_sum,
        layer_contributions=contributions,
        dominant_polarity=polarity,
        stability_index=max(0.0, min(1.0, stability)),
    )


# ---------------------------------------------------------------------------
# Encoding bridges: TritVector <-> BalancedTernary <-> NegaBinary
# ---------------------------------------------------------------------------


def trit_vector_to_balanced_ternary(tv: TritVector) -> BalancedTernary:
    """Encode TritVector as a single BalancedTernary number (MSB-first)."""
    trits = [Trit(v) for v in tv.values]
    return BalancedTernary.from_trits(trits, msb_first=True)


def balanced_ternary_to_trit_vector(bt: BalancedTernary, width: int) -> TritVector:
    """Decode BalancedTernary to TritVector, padding to width."""
    msb_trits = list(bt.trits_msb)
    if len(msb_trits) < width:
        msb_trits = [Trit.ZERO] * (width - len(msb_trits)) + msb_trits
    elif len(msb_trits) > width:
        msb_trits = msb_trits[-width:]
    return TritVector(tuple(t.value for t in msb_trits))


def trit_vector_to_negabinary(tv: TritVector) -> NegaBinary:
    """Convert TritVector to NegaBinary via balanced ternary integer bridge."""
    bt = trit_vector_to_balanced_ternary(tv)
    return NegaBinary.from_int(bt.to_int())


def negabinary_to_trit_vector(nb: NegaBinary, width: int) -> TritVector:
    """Convert NegaBinary to TritVector via balanced ternary integer bridge."""
    bt = BalancedTernary.from_int(nb.to_int())
    return balanced_ternary_to_trit_vector(bt, width)


# ---------------------------------------------------------------------------
# Fleet Fusion Engine
# ---------------------------------------------------------------------------


@dataclass
class FleetFusionConfig:
    consensus_theta: float = 0.5
    consensus_quorum: float = 0.5
    shadow_lambda: float = 0.5
    shadow_contest_threshold: float = 0.3
    layer_correction_enabled: bool = True
    coherence_warning_threshold: float = 0.3
    faction_detection_threshold: float = 0.0


DEFAULT_FLEET_CONFIG = FleetFusionConfig()


@dataclass
class FleetFusionResult:
    consensus: ConsensusResult
    coherence_matrix: Optional[CoherenceMatrix]
    layer_correction: Optional[LayerCorrectionResult]
    factions: List[List[str]]
    adversarial_agents: List[str]
    shadow: AdversarialShadow
    final_decision: GovernanceDecision
    warnings: List[str]


class FleetTernaryFusion:
    """Fleet-level multi-agent ternary fusion engine.

    Pipeline:
      1. Pairwise coherence analysis
      2. Faction detection
      3. Adversarial shadow computation
      4. Weighted consensus fusion
      5. Negative-base layer correction
      6. Final governance decision
    """

    def __init__(self, config: Optional[FleetFusionConfig] = None) -> None:
        self.config = config or DEFAULT_FLEET_CONFIG

    def fuse(
        self,
        agents: Sequence[AgentTritState],
        layer_outputs: Optional[Sequence[float]] = None,
    ) -> FleetFusionResult:
        warnings: List[str] = []

        if not agents:
            raise ValueError("Need at least one agent for fleet fusion")

        coh_matrix = compute_coherence_matrix(agents) if len(agents) >= 2 else None

        factions: List[List[str]] = []
        if coh_matrix:
            factions = coh_matrix.faction_detection(self.config.faction_detection_threshold)
            if coh_matrix.mean_coherence() < self.config.coherence_warning_threshold:
                warnings.append(
                    f"Low fleet coherence: {coh_matrix.mean_coherence():.3f} "
                    f"< threshold {self.config.coherence_warning_threshold}"
                )

        adversarial = [a.agent_id for a in agents if a.is_adversarial]

        consensus = ternary_consensus(
            agents,
            theta=self.config.consensus_theta,
            quorum=self.config.consensus_quorum,
            coherence_matrix=coh_matrix,
        )

        aligned_scores = [a.confidence for a in agents if not a.is_adversarial]
        adversarial_scores = [a.confidence for a in agents if a.is_adversarial]
        shadow = AdversarialShadow(
            positive_score=sum(aligned_scores) if aligned_scores else 0.0,
            negative_score=sum(adversarial_scores) if adversarial_scores else 0.0,
            lambda_discount=self.config.shadow_lambda,
        )

        layer_corr = None
        if layer_outputs and self.config.layer_correction_enabled:
            layer_corr = apply_layer_correction(layer_outputs)
            if layer_corr.stability_index < 0.3:
                warnings.append(f"Layer correction unstable: stability={layer_corr.stability_index:.3f}")

        decision = consensus.decision

        if shadow.is_contested(self.config.shadow_contest_threshold):
            if decision == GovernanceDecision.ALLOW:
                decision = GovernanceDecision.QUARANTINE
                warnings.append("Shadow contest: ALLOW downgraded to QUARANTINE")
            elif decision == GovernanceDecision.QUARANTINE:
                decision = GovernanceDecision.ESCALATE
                warnings.append("Shadow contest: QUARANTINE escalated to ESCALATE")

        if consensus.contested_dimensions:
            warnings.append(f"Contested dimensions: {consensus.contested_dimensions}")

        return FleetFusionResult(
            consensus=consensus,
            coherence_matrix=coh_matrix,
            layer_correction=layer_corr,
            factions=factions,
            adversarial_agents=adversarial,
            shadow=shadow,
            final_decision=decision,
            warnings=warnings,
        )
