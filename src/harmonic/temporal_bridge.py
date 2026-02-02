"""
Temporal Pipeline Bridge

Bridges the stateless 14-layer pipeline with stateful temporal intent tracking.
This module wires temporal_intent_scaling.py into the pipeline execution flow.

Usage:
    from harmonic.temporal_bridge import TemporalPipelineBridge

    # Create bridge for an agent
    bridge = TemporalPipelineBridge(agent_id="agent-123")

    # Use with pipeline processing
    d_star = 0.7  # Distance from Layer 8
    H_eff, x = bridge.process_layer12(d_star)
    assessment = bridge.process_layer13(d_star)

    # Check agent reputation over time
    reputation = bridge.get_reputation()

@module harmonic/temporal_bridge
@layer Layer 11, Layer 12, Layer 13
@version 1.0.0
@since 2026-02-02
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import time
import math

from .temporal_intent_scaling import (
    TemporalIntentState,
    DeviationChannels,
    TriadicTemporalState,
    TrajectoryCoherence,
    TemporalRiskAssessment,
    DriftMonitor,
    compute_temporal_intent_factor,
    update_temporal_state,
    harmonic_scale_basic,
    harmonic_scale_effective,
    harmonic_scale_with_state,
    assess_risk_temporal,
    PERFECT_FIFTH,
    PHI,
)


# ============================================================================
# Agent History Tracking
# ============================================================================

@dataclass
class AgentDecisionRecord:
    """Record of a single risk decision for an agent."""
    timestamp: float
    d_star: float
    H_basic: float
    H_effective: float
    x_factor: float
    decision: str
    reasoning: str
    deviation_channels: Optional[DeviationChannels] = None


@dataclass
class AgentProfile:
    """Profile tracking an agent's behavior over time."""
    agent_id: str
    created_at: float = field(default_factory=time.time)
    decisions: List[AgentDecisionRecord] = field(default_factory=list)
    total_requests: int = 0
    allow_count: int = 0
    quarantine_count: int = 0
    escalate_count: int = 0
    deny_count: int = 0
    reputation_score: float = 0.5  # Neutral starting reputation

    def update_reputation(self) -> float:
        """Update reputation based on decision history."""
        if not self.decisions:
            return 0.5

        # Exponential weighting: recent decisions matter more
        weights = []
        scores = []
        decay = 0.9

        for i, record in enumerate(reversed(self.decisions[-50:])):  # Last 50
            weight = decay ** i
            weights.append(weight)

            # Score mapping
            if record.decision == "ALLOW":
                score = 1.0
            elif record.decision == "QUARANTINE":
                score = 0.6
            elif record.decision == "ESCALATE":
                score = 0.3
            else:  # DENY
                score = 0.0

            scores.append(score)

        total_weight = sum(weights)
        if total_weight > 0:
            self.reputation_score = sum(s * w for s, w in zip(scores, weights)) / total_weight

        return self.reputation_score


# ============================================================================
# Temporal Pipeline Bridge
# ============================================================================

class TemporalPipelineBridge:
    """
    Bridges the stateless 14-layer pipeline with stateful temporal tracking.

    This class maintains temporal intent state per agent, enabling:
    - Forgiveness for brief behavioral spikes (x < 1)
    - Compounding penalties for sustained adversarial behavior (x > 1)
    - Cross-session memory via decision history
    - Reputation-based threshold adjustment

    Integration Points:
    - Layer 11 (Triadic Temporal): Provides d_tri calculation with decay
    - Layer 12 (Harmonic Scaling): Enhanced H_eff(d, R, x) = R^(d²) · x
    - Layer 13 (Risk Decision): Four-tier decision with temporal context

    Thread Safety:
        Not thread-safe. Use one bridge per agent per thread, or add locking.
    """

    def __init__(
        self,
        agent_id: str,
        R: float = PERFECT_FIFTH,
        allow_threshold: float = 0.3,
        quarantine_threshold: float = 0.5,
        escalate_threshold: float = 0.7,
    ):
        """
        Initialize bridge for an agent.

        Args:
            agent_id: Unique identifier for the agent
            R: Harmonic base (default 1.5 "Perfect Fifth")
            allow_threshold: H_eff normalized threshold for ALLOW
            quarantine_threshold: H_eff normalized threshold for QUARANTINE
            escalate_threshold: H_eff normalized threshold for ESCALATE
        """
        self.agent_id = agent_id
        self.R = R
        self.allow_threshold = allow_threshold
        self.quarantine_threshold = quarantine_threshold
        self.escalate_threshold = escalate_threshold

        # Temporal state
        self.state = TemporalIntentState()
        self.drift_monitor = DriftMonitor()

        # Agent profile
        self.profile = AgentProfile(agent_id=agent_id)

        # Timestamps
        self.created_at = time.time()
        self.last_update = self.created_at

    def update_state(
        self,
        d_star: float,
        deviation_channels: Optional[DeviationChannels] = None,
        is_adversarial: bool = False,
    ) -> float:
        """
        Update temporal state with new observation.

        Args:
            d_star: Deviation distance from Layer 8 multi-well
            deviation_channels: Optional CPSE z-vector channels
            is_adversarial: Hint if this is adversarial (increases update weight)

        Returns:
            Updated temporal intent factor x
        """
        # Apply amplification for adversarial hints
        effective_d = d_star * (1.5 if is_adversarial else 1.0)

        # Update triadic distances
        x = update_temporal_state(
            self.state,
            effective_d,
            deviation_channels,
            decay_rate=0.85 if is_adversarial else 0.9,
        )

        # Track trajectory coherence
        self._update_trajectory(d_star)

        self.last_update = time.time()
        return x

    def _update_trajectory(self, d_star: float) -> None:
        """Update trajectory coherence metrics."""
        history = self.state.history

        if len(history) < 2:
            return

        # Check for direction reversal
        if len(history) >= 3:
            prev_delta = history[-2] - history[-3] if len(history) >= 3 else 0
            curr_delta = history[-1] - history[-2]
            if prev_delta * curr_delta < 0:  # Sign change
                self.state.trajectory.reversal_count += 1

        # Update drift rate (moving average of absolute changes)
        if len(history) >= 2:
            drift = abs(history[-1] - history[-2])
            alpha = 0.2
            self.state.trajectory.drift_rate = (
                alpha * drift + (1 - alpha) * self.state.trajectory.drift_rate
            )

        # Update coherence based on variance
        if len(history) >= 5:
            recent = history[-5:]
            variance = sum((x - sum(recent)/len(recent))**2 for x in recent) / len(recent)
            # High variance = low coherence
            self.state.trajectory.coherence = 1.0 / (1.0 + variance)

        # Stability score combines coherence and low reversal count
        reversal_penalty = 1.0 / (1.0 + 0.1 * self.state.trajectory.reversal_count)
        self.state.trajectory.stability_score = (
            self.state.trajectory.coherence * reversal_penalty
        )

    def process_layer12(
        self,
        d_star: float,
        R: Optional[float] = None,
    ) -> Tuple[float, float]:
        """
        Enhanced Layer 12 with temporal intent modulation.

        Computes H_eff(d, R, x) = R^(d²) · x

        Args:
            d_star: Deviation distance (usually from Layer 8)
            R: Optional override for harmonic base

        Returns:
            Tuple of (H_effective, temporal_factor_x)
        """
        R = R or self.R
        x = compute_temporal_intent_factor(self.state)

        # Apply drift correction
        H_basic = harmonic_scale_basic(d_star, R)
        H_basic = self.drift_monitor.check_and_correct("H_basic", H_basic)

        H_eff = H_basic * x
        H_eff = self.drift_monitor.check_and_correct("H_eff", H_eff)

        return H_eff, x

    def process_layer13(
        self,
        d_star: float,
        R: Optional[float] = None,
    ) -> TemporalRiskAssessment:
        """
        Enhanced Layer 13 with temporal state and reputation adjustment.

        Args:
            d_star: Deviation distance
            R: Optional override for harmonic base

        Returns:
            TemporalRiskAssessment with decision and explanation
        """
        R = R or self.R

        # Get reputation-adjusted thresholds
        reputation = self.profile.reputation_score
        # Good reputation (high score) → more lenient thresholds
        # Bad reputation (low score) → stricter thresholds
        threshold_adjustment = 0.1 * (reputation - 0.5)  # [-0.05, +0.05]

        adjusted_allow = self.allow_threshold + threshold_adjustment
        adjusted_quarantine = self.quarantine_threshold + threshold_adjustment
        adjusted_escalate = self.escalate_threshold + threshold_adjustment

        # Assess risk with adjusted thresholds
        assessment = assess_risk_temporal(
            d_star,
            self.state,
            R,
            allow_threshold=adjusted_allow,
            quarantine_threshold=adjusted_quarantine,
            escalate_threshold=adjusted_escalate,
        )

        # Record decision
        record = AgentDecisionRecord(
            timestamp=time.time(),
            d_star=d_star,
            H_basic=assessment.H_basic,
            H_effective=assessment.H_effective,
            x_factor=assessment.x_factor,
            decision=assessment.risk_level,
            reasoning=assessment.reasoning,
            deviation_channels=self.state.deviations,
        )
        self.profile.decisions.append(record)
        self.profile.total_requests += 1

        # Update counters
        if assessment.risk_level == "ALLOW":
            self.profile.allow_count += 1
        elif assessment.risk_level == "QUARANTINE":
            self.profile.quarantine_count += 1
        elif assessment.risk_level == "ESCALATE":
            self.profile.escalate_count += 1
        else:  # DENY
            self.profile.deny_count += 1

        # Update reputation
        self.profile.update_reputation()

        return assessment

    def get_reputation(self) -> float:
        """Get current agent reputation score [0, 1]."""
        return self.profile.reputation_score

    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current temporal state."""
        x = compute_temporal_intent_factor(self.state)
        drift = self.drift_monitor.get_drift_report()

        return {
            "agent_id": self.agent_id,
            "temporal_factor_x": x,
            "triadic": {
                "d_immediate": self.state.triadic.d_immediate,
                "d_medium": self.state.triadic.d_medium,
                "d_longterm": self.state.triadic.d_longterm,
                "d_tri": self.state.triadic.d_tri(),
            },
            "deviations": {
                "chaosdev": self.state.deviations.chaosdev,
                "fractaldev": self.state.deviations.fractaldev,
                "energydev": self.state.deviations.energydev,
                "composite": self.state.deviations.composite(),
            },
            "trajectory": {
                "coherence": self.state.trajectory.coherence,
                "drift_rate": self.state.trajectory.drift_rate,
                "reversal_count": self.state.trajectory.reversal_count,
                "stability_score": self.state.trajectory.stability_score,
            },
            "reputation": self.profile.reputation_score,
            "total_requests": self.profile.total_requests,
            "decision_counts": {
                "allow": self.profile.allow_count,
                "quarantine": self.profile.quarantine_count,
                "escalate": self.profile.escalate_count,
                "deny": self.profile.deny_count,
            },
            "drift_status": drift,
        }

    def reset(self) -> None:
        """Reset temporal state (but preserve profile history)."""
        self.state = TemporalIntentState()
        self.drift_monitor = DriftMonitor()
        self.last_update = time.time()


# ============================================================================
# Bridge Registry
# ============================================================================

_bridge_registry: Dict[str, TemporalPipelineBridge] = {}


def get_bridge(agent_id: str, **kwargs) -> TemporalPipelineBridge:
    """
    Get or create a temporal bridge for an agent.

    Args:
        agent_id: Unique agent identifier
        **kwargs: Arguments for TemporalPipelineBridge constructor

    Returns:
        TemporalPipelineBridge for the agent
    """
    if agent_id not in _bridge_registry:
        _bridge_registry[agent_id] = TemporalPipelineBridge(agent_id, **kwargs)
    return _bridge_registry[agent_id]


def clear_bridges() -> None:
    """Clear all bridges from registry."""
    global _bridge_registry
    _bridge_registry = {}


def list_agents() -> List[str]:
    """List all agents with active bridges."""
    return list(_bridge_registry.keys())


def get_all_summaries() -> Dict[str, Dict[str, Any]]:
    """Get state summaries for all agents."""
    return {
        agent_id: bridge.get_state_summary()
        for agent_id, bridge in _bridge_registry.items()
    }


# ============================================================================
# Pipeline Integration Helper
# ============================================================================

def process_with_temporal(
    pipeline_result: Dict[str, Any],
    agent_id: str,
    deviation_channels: Optional[DeviationChannels] = None,
) -> Dict[str, Any]:
    """
    Enhance pipeline result with temporal intent processing.

    This is a convenience function that takes a standard pipeline result
    and augments it with temporal-aware Layer 12/13 processing.

    Args:
        pipeline_result: Result from FourteenLayerPipeline.process()
        agent_id: Agent identifier
        deviation_channels: Optional CPSE channels

    Returns:
        Enhanced result with temporal fields added
    """
    bridge = get_bridge(agent_id)

    # Extract d_star from pipeline (Layer 8 output)
    d_star = pipeline_result.get("d_star", pipeline_result.get("layer_8_distance", 0.5))

    # Update temporal state
    bridge.update_state(d_star, deviation_channels)

    # Get enhanced Layer 12/13
    H_eff, x = bridge.process_layer12(d_star)
    assessment = bridge.process_layer13(d_star)

    # Augment result
    enhanced = dict(pipeline_result)
    enhanced["temporal"] = {
        "H_effective": H_eff,
        "x_factor": x,
        "assessment": {
            "risk_level": assessment.risk_level,
            "reasoning": assessment.reasoning,
            "forgiveness_applied": assessment.forgiveness_applied,
            "compounding_applied": assessment.compounding_applied,
        },
        "reputation": bridge.get_reputation(),
    }

    return enhanced


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Main class
    "TemporalPipelineBridge",
    # Data classes
    "AgentDecisionRecord",
    "AgentProfile",
    # Registry functions
    "get_bridge",
    "clear_bridges",
    "list_agents",
    "get_all_summaries",
    # Helper
    "process_with_temporal",
]
