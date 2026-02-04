#!/usr/bin/env python3
"""
Layer 13 + Hive Memory Integration
===================================

Wires Hive Memory to Layer 13 for:
- Storing agent decision history
- Cross-session learning from past decisions
- Temporal pattern analysis for risk assessment

Integration Points:
- Every Layer 13 decision → stored in Hive Memory
- Historical decisions → inform future risk assessment
- CHARM priority → based on decision severity

Date: February 2026
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

# Layer 13 imports
from .layer_13 import (
    Decision,
    RiskComponents,
    CompositeRisk,
    DecisionResponse,
    HarmonicParams,
    TimeMultiplier,
    IntentMultiplier,
    execute_decision,
    compute_composite_risk,
)

# Hive Memory imports (use relative import with fallback)
try:
    from ...spiralverse.hive_memory import (
        MemoryBlock,
        MemoryTier,
        EvictionPriority,
        MemoryEvictionEngine,
        AgentSnapshot,
    )
    HIVE_AVAILABLE = True
except ImportError:
    # Hive Memory not available - create minimal stubs
    HIVE_AVAILABLE = False

    class MemoryBlock:
        """Stub for when Hive Memory is not available."""
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class MemoryTier(Enum):
        HOT = "hot"
        WARM = "warm"
        COLD = "cold"


# =============================================================================
# CONSTANTS
# =============================================================================

# CHARM priorities for different decision types
DECISION_CHARM = {
    Decision.ALLOW: 0.3,      # Normal operations, lower retention priority
    Decision.WARN: 0.5,       # Moderate priority
    Decision.REVIEW: 0.7,     # Higher priority - needs human attention
    Decision.DENY: 0.85,      # High priority - security event
    Decision.REJECT: 0.9,     # Very high priority
    Decision.SNAP: 0.95,      # Critical - noise injection event
}

# Tongue codes for decision types
DECISION_TONGUE = {
    Decision.ALLOW: "CA",     # Computation - normal flow
    Decision.WARN: "AV",      # I/O warning
    Decision.REVIEW: "KO",    # Control flow - human review
    Decision.DENY: "UM",      # Security - blocked
    Decision.REJECT: "UM",    # Security - rejected
    Decision.SNAP: "DR",      # Types - noise injection
}


# =============================================================================
# DECISION RECORD
# =============================================================================

@dataclass
class DecisionRecord:
    """
    Serializable record of a Layer 13 decision for Hive storage.
    """
    record_id: str
    timestamp: datetime
    agent_id: str
    session_id: str

    # Decision info
    decision: str  # Decision enum value as string
    action: str
    confidence: float

    # Risk components
    behavioral_risk: float
    d_star: float
    time_multi: float
    intent_multi: float
    risk_prime: float
    risk_normalized: float

    # Context
    context_hash: str  # Hash of input context for deduplication
    noise_injected: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DecisionRecord':
        """Reconstruct from dict."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

    def to_bytes(self) -> bytes:
        """Serialize to bytes for Hive storage."""
        return json.dumps(self.to_dict()).encode('utf-8')

    @classmethod
    def from_bytes(cls, data: bytes) -> 'DecisionRecord':
        """Deserialize from bytes."""
        return cls.from_dict(json.loads(data.decode('utf-8')))


# =============================================================================
# HIVE-INTEGRATED LAYER 13
# =============================================================================

class HiveIntegratedLayer13:
    """
    Layer 13 Risk Decision Engine with Hive Memory integration.

    Features:
    - Automatic storage of all decisions in Hive Memory
    - Historical decision lookup for pattern analysis
    - Cross-session learning from decision history
    - CHARM-based retention priority

    Usage:
        layer13 = HiveIntegratedLayer13(agent_id="agent-001")
        response = layer13.execute_with_history(components)
        history = layer13.get_decision_history(limit=100)
    """

    def __init__(
        self,
        agent_id: str,
        session_id: Optional[str] = None,
        harmonic_params: Optional[HarmonicParams] = None,
        theta_1: float = 0.5,
        theta_2: float = 2.0,
        max_history: int = 10000,
    ):
        """
        Initialize Hive-integrated Layer 13.

        Args:
            agent_id: Unique agent identifier
            session_id: Current session ID (auto-generated if None)
            harmonic_params: Parameters for H(d*) computation
            theta_1: ALLOW threshold
            theta_2: DENY threshold
            max_history: Maximum decisions to retain in hot memory
        """
        self.agent_id = agent_id
        self.session_id = session_id or self._generate_session_id()
        self.harmonic_params = harmonic_params
        self.theta_1 = theta_1
        self.theta_2 = theta_2
        self.max_history = max_history

        # In-memory decision history (hot tier)
        self._hot_memory: List[DecisionRecord] = []

        # Statistics
        self._decision_counts: Dict[str, int] = {d.value: 0 for d in Decision}
        self._total_decisions = 0

        # Eviction engine for memory management
        if HIVE_AVAILABLE:
            self._eviction_engine = MemoryEvictionEngine()
        else:
            self._eviction_engine = None

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        now = datetime.utcnow().isoformat()
        return hashlib.sha256(f"{self.agent_id}:{now}".encode()).hexdigest()[:16]

    def _generate_record_id(self, components: RiskComponents) -> str:
        """Generate unique record ID for a decision."""
        now = datetime.utcnow().isoformat()
        content = f"{self.agent_id}:{self.session_id}:{now}:{components.behavioral_risk}"
        return hashlib.sha256(content.encode()).hexdigest()[:24]

    def _compute_context_hash(self, components: RiskComponents) -> str:
        """Hash the input context for deduplication."""
        content = (
            f"{components.behavioral_risk}:"
            f"{components.d_star}:"
            f"{components.time_multi.value}:"
            f"{components.intent_multi.value}"
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def execute_with_history(
        self,
        components: RiskComponents,
        store_in_hive: bool = True,
    ) -> Tuple[DecisionResponse, DecisionRecord]:
        """
        Execute Layer 13 decision and store in Hive Memory.

        Args:
            components: Risk components for evaluation
            store_in_hive: Whether to store in Hive (default True)

        Returns:
            Tuple of (DecisionResponse, DecisionRecord)
        """
        # Execute Layer 13 decision
        response = execute_decision(
            components,
            self.harmonic_params,
            self.theta_1,
            self.theta_2,
        )

        # Create decision record
        record = DecisionRecord(
            record_id=self._generate_record_id(components),
            timestamp=datetime.utcnow(),
            agent_id=self.agent_id,
            session_id=self.session_id,
            decision=response.decision.value,
            action=response.action,
            confidence=response.risk.confidence,
            behavioral_risk=response.risk.behavioral_risk,
            d_star=components.d_star,
            time_multi=response.risk.time_multi,
            intent_multi=response.risk.intent_multi,
            risk_prime=response.risk.risk_prime,
            risk_normalized=response.risk.risk_normalized,
            context_hash=self._compute_context_hash(components),
            noise_injected=response.noise_injected,
        )

        # Store in hot memory
        if store_in_hive:
            self._store_decision(record, response.decision)

        # Update statistics
        self._decision_counts[response.decision.value] += 1
        self._total_decisions += 1

        return response, record

    def _store_decision(self, record: DecisionRecord, decision: Decision) -> None:
        """Store decision record in memory hierarchy."""
        # Add to hot memory
        self._hot_memory.append(record)

        # Evict if over capacity
        if len(self._hot_memory) > self.max_history:
            self._evict_old_decisions()

    def _evict_old_decisions(self) -> None:
        """Evict low-priority decisions from hot memory."""
        if not HIVE_AVAILABLE or not self._eviction_engine:
            # Simple eviction: remove oldest
            self._hot_memory = self._hot_memory[-self.max_history:]
            return

        # Convert records to MemoryBlocks for eviction engine
        blocks = []
        for record in self._hot_memory:
            charm = DECISION_CHARM.get(
                Decision(record.decision), 0.5
            )
            block = MemoryBlock(
                block_id=record.record_id,
                data=record.to_bytes(),
                timestamp=record.timestamp,
                tongue=DECISION_TONGUE.get(Decision(record.decision), "AET"),
                charm=charm,
                critical_event=(record.decision in ["DENY", "REJECT", "SNAP"]),
            )
            blocks.append(block)

        # Use eviction engine to rank
        target_count = int(self.max_history * 0.8)  # Keep 80%
        ranked = self._eviction_engine.rank_for_eviction(blocks)

        # Keep highest priority records
        keep_ids = {b.block_id for b, _ in ranked[-target_count:]}
        self._hot_memory = [r for r in self._hot_memory if r.record_id in keep_ids]

    def get_decision_history(
        self,
        limit: int = 100,
        decision_filter: Optional[List[Decision]] = None,
        since: Optional[datetime] = None,
    ) -> List[DecisionRecord]:
        """
        Retrieve decision history.

        Args:
            limit: Maximum records to return
            decision_filter: Filter by decision types
            since: Only return decisions after this time

        Returns:
            List of DecisionRecords (newest first)
        """
        results = self._hot_memory.copy()

        # Apply filters
        if decision_filter:
            filter_values = {d.value for d in decision_filter}
            results = [r for r in results if r.decision in filter_values]

        if since:
            results = [r for r in results if r.timestamp >= since]

        # Sort by timestamp (newest first) and limit
        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get decision statistics.

        Returns:
            Dict with counts, rates, and patterns
        """
        if self._total_decisions == 0:
            return {"total": 0, "rates": {}, "patterns": {}}

        rates = {
            k: v / self._total_decisions
            for k, v in self._decision_counts.items()
        }

        # Compute recent pattern (last 100 decisions)
        recent = self._hot_memory[-100:] if self._hot_memory else []
        recent_risks = [r.risk_prime for r in recent]

        return {
            "total": self._total_decisions,
            "counts": self._decision_counts.copy(),
            "rates": rates,
            "deny_rate": (
                self._decision_counts["DENY"] +
                self._decision_counts["REJECT"] +
                self._decision_counts["SNAP"]
            ) / self._total_decisions,
            "recent_risk_mean": sum(recent_risks) / len(recent_risks) if recent_risks else 0,
            "recent_risk_max": max(recent_risks) if recent_risks else 0,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
        }

    def get_similar_decisions(
        self,
        components: RiskComponents,
        limit: int = 5,
    ) -> List[Tuple[DecisionRecord, float]]:
        """
        Find similar historical decisions for learning.

        Args:
            components: Current risk components
            limit: Maximum similar records to return

        Returns:
            List of (DecisionRecord, similarity_score) tuples
        """
        if not self._hot_memory:
            return []

        # Compute similarity based on component distances
        def similarity(record: DecisionRecord) -> float:
            d_br = abs(record.behavioral_risk - components.behavioral_risk)
            d_ds = abs(record.d_star - components.d_star)
            d_tm = abs(record.time_multi - components.time_multi.value)
            d_im = abs(record.intent_multi - components.intent_multi.value)

            # Weighted distance (lower = more similar)
            distance = 0.4 * d_br + 0.3 * d_ds + 0.15 * d_tm + 0.15 * d_im
            return 1.0 / (1.0 + distance)  # Convert to similarity [0, 1]

        scored = [(r, similarity(r)) for r in self._hot_memory]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def predict_from_history(
        self,
        components: RiskComponents,
    ) -> Optional[Dict[str, Any]]:
        """
        Predict decision based on similar historical cases.

        This enables cross-session learning by using past decisions
        to inform current risk assessment.

        Args:
            components: Current risk components

        Returns:
            Prediction dict or None if insufficient history
        """
        similar = self.get_similar_decisions(components, limit=10)
        if len(similar) < 3:
            return None  # Insufficient data

        # Weight decisions by similarity
        decision_weights: Dict[str, float] = {}
        total_weight = 0

        for record, sim_score in similar:
            decision_weights[record.decision] = (
                decision_weights.get(record.decision, 0) + sim_score
            )
            total_weight += sim_score

        # Normalize
        if total_weight > 0:
            decision_weights = {
                k: v / total_weight for k, v in decision_weights.items()
            }

        # Predict most likely decision
        predicted = max(decision_weights.items(), key=lambda x: x[1])

        return {
            "predicted_decision": predicted[0],
            "confidence": predicted[1],
            "decision_distribution": decision_weights,
            "similar_cases": len(similar),
            "avg_similarity": sum(s for _, s in similar) / len(similar),
        }

    def to_memory_block(self) -> Optional[MemoryBlock]:
        """
        Export current state as a MemoryBlock for Hive cold storage.

        Returns:
            MemoryBlock with serialized state, or None if Hive unavailable
        """
        if not HIVE_AVAILABLE:
            return None

        state = {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "decision_counts": self._decision_counts,
            "total_decisions": self._total_decisions,
            "history": [r.to_dict() for r in self._hot_memory[-1000:]],
        }

        return MemoryBlock(
            block_id=f"layer13-{self.agent_id}-{self.session_id}",
            data=json.dumps(state).encode('utf-8'),
            timestamp=datetime.utcnow(),
            tongue="KO",  # Control flow
            charm=0.8,  # High retention priority
            critical_event=False,
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_layer13_with_hive(
    agent_id: str,
    **kwargs
) -> HiveIntegratedLayer13:
    """
    Factory function to create Hive-integrated Layer 13.

    Args:
        agent_id: Unique agent identifier
        **kwargs: Additional arguments for HiveIntegratedLayer13

    Returns:
        Configured HiveIntegratedLayer13 instance
    """
    return HiveIntegratedLayer13(agent_id=agent_id, **kwargs)


def batch_evaluate_with_history(
    layer13: HiveIntegratedLayer13,
    requests: List[RiskComponents],
) -> Dict[str, Any]:
    """
    Evaluate batch of requests with history storage.

    Args:
        layer13: HiveIntegratedLayer13 instance
        requests: List of RiskComponents to evaluate

    Returns:
        Batch results with statistics
    """
    results = []
    for components in requests:
        response, record = layer13.execute_with_history(components)
        results.append({
            "decision": response.decision.value,
            "risk_prime": response.risk.risk_prime,
            "action": response.action,
            "record_id": record.record_id,
        })

    return {
        "total": len(requests),
        "results": results,
        "statistics": layer13.get_statistics(),
    }
