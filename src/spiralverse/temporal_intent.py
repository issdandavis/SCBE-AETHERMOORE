"""
Temporal-Intent Harmonic Scaling - H_eff(d,R,x) Extended Harmonic Wall
======================================================================

Extends the Harmonic Scaling Law with temporal intent accumulation:

    H_eff(d, R, x) = R^(d^2 * x)

Where:
    d = distance from safe operation (Poincare ball, Layer 5)
    R = harmonic ratio (1.5 = perfect fifth)
    x = temporal intent factor derived from existing Layer 11 + CPSE channels

The 'x' factor is NOT a new concept - it aggregates existing metrics:

    x(t) = f(d_tri(t), chaosdev(t), fractaldev(t), energydev(t))

Where:
    d_tri(t)      = Triadic temporal distance (L11: immediate/medium/long-term)
    chaosdev(t)   = Lyapunov-based chaos deviation (CPSE z-vector)
    fractaldev(t) = Fractal dimension deviation
    energydev(t)  = Energy channel deviation

This makes security cost compound based on SUSTAINED adversarial behavior,
not just instantaneous distance. Brief deviations are forgiven; persistent
drift toward the boundary costs super-exponentially more over time.

Integration with existing layers:
    - L5:  Hyperbolic distance provides 'd'
    - L11: Triadic Temporal Distance provides d_tri(t)
    - L12: Harmonic Wall now uses H_eff(d,R,x) instead of H(d,R)
    - CPSE: Chaos/fractal/energy deviation channels provide z_t

From requirements.md AC-2.3.3:
    Omega = pqc_valid * harm_score * (1 - drift_norm/drift_max) * triadic_stable * spectral_score

The 'x' factor integrates drift_norm accumulation over time windows, keeping
everything axiom-safe with Layer 11 (Triadic Temporal) and CPSE z-vector tests.

"Security IS growth. Intent over time reveals truth."
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from collections import deque
import hashlib


# =============================================================================
# Constants
# =============================================================================

# Harmonic ratio (perfect fifth)
R_HARMONIC = 1.5

# Intent decay rate (how fast old intent fades)
INTENT_DECAY_RATE = 0.95  # per time window

# Time window for intent accumulation (seconds)
INTENT_WINDOW_SECONDS = 1.0

# Maximum intent accumulation before hard exile
MAX_INTENT_ACCUMULATION = 10.0

# Trust threshold for exile (from AC-2.3.2)
TRUST_EXILE_THRESHOLD = 0.3
TRUST_EXILE_ROUNDS = 10


# =============================================================================
# Intent State
# =============================================================================

class IntentState(Enum):
    """Classification of agent's temporal intent."""
    BENIGN = "benign"           # x < 0.5 - consistently safe
    NEUTRAL = "neutral"         # 0.5 <= x < 1.0 - normal operation
    DRIFTING = "drifting"       # 1.0 <= x < 2.0 - concerning pattern
    ADVERSARIAL = "adversarial" # x >= 2.0 - sustained adversarial behavior
    EXILED = "exiled"           # Null-space exile triggered


@dataclass
class IntentSample:
    """
    Single sample of distance/intent at a point in time.

    Integrates L5 (hyperbolic distance), L11 (triadic temporal), and CPSE z-vector.
    """
    timestamp: float
    distance: float        # d in Poincare ball (0 to ~1) from L5
    velocity: float        # rate of change of distance
    harmony: float         # CHARM value (-1 to 1)

    # CPSE z-vector deviation channels
    chaosdev: float = 0.0    # Lyapunov-based chaos deviation
    fractaldev: float = 0.0  # Fractal dimension deviation
    energydev: float = 0.0   # Energy channel deviation

    # Triadic temporal components (L11)
    d_tri_immediate: float = 0.0   # Immediate behavior
    d_tri_medium: float = 0.0      # Medium-term pattern
    d_tri_long: float = 0.0        # Long-term trajectory

    @property
    def d_tri(self) -> float:
        """Triadic temporal distance (L11) - geometric mean of time scales."""
        return (abs(self.d_tri_immediate) * abs(self.d_tri_medium) * abs(self.d_tri_long)) ** (1/3)

    @property
    def raw_intent(self) -> float:
        """
        Calculate raw intent from this sample using existing L11 + CPSE metrics.

        x(t) = f(d_tri(t), chaosdev(t), fractaldev(t), energydev(t))
        """
        # Velocity contribution (moving toward boundary is adversarial)
        velocity_factor = max(0, self.velocity) * 2.0

        # Distance contribution (further out = more suspicious)
        distance_factor = self.distance ** 2

        # Harmony dampening (high harmony reduces intent score)
        harmony_dampening = (1 - self.harmony) / 2  # 0 to 1

        # CPSE deviation channels contribution
        cpse_factor = (abs(self.chaosdev) + abs(self.fractaldev) + abs(self.energydev)) / 3

        # Triadic temporal contribution (L11)
        triadic_factor = self.d_tri

        base_intent = (velocity_factor + distance_factor) * (0.5 + harmony_dampening)

        # Amplify by CPSE deviations and triadic distance
        return base_intent * (1.0 + cpse_factor + triadic_factor)


@dataclass
class IntentHistory:
    """
    Tracks intent accumulation over time for a single agent.

    Uses sliding window to accumulate intent, with decay for old samples.
    """
    agent_id: str
    samples: deque = field(default_factory=lambda: deque(maxlen=1000))
    accumulated_intent: float = 0.0
    trust_score: float = 1.0
    low_trust_rounds: int = 0
    state: IntentState = IntentState.NEUTRAL
    last_update: float = field(default_factory=time.time)

    def add_sample(self, distance: float, velocity: float = 0.0, harmony: float = 0.0):
        """Add a new intent sample and update accumulation."""
        now = time.time()

        sample = IntentSample(
            timestamp=now,
            distance=distance,
            velocity=velocity,
            harmony=harmony
        )
        self.samples.append(sample)

        # Apply decay to accumulated intent
        time_delta = now - self.last_update
        decay_factor = INTENT_DECAY_RATE ** (time_delta / INTENT_WINDOW_SECONDS)
        self.accumulated_intent *= decay_factor

        # Add new intent
        self.accumulated_intent += sample.raw_intent

        # Cap at maximum
        self.accumulated_intent = min(self.accumulated_intent, MAX_INTENT_ACCUMULATION)

        # Update trust score
        self._update_trust()

        # Update state classification
        self._update_state()

        self.last_update = now

    def _update_trust(self):
        """Update trust score based on recent behavior."""
        if len(self.samples) < 5:
            return

        # Average recent distances
        recent = list(self.samples)[-10:]
        avg_distance = sum(s.distance for s in recent) / len(recent)

        # Trust decreases with distance and accumulated intent
        trust_change = -0.1 * avg_distance - 0.05 * self.accumulated_intent

        # Trust recovers slowly when behaving well
        if self.accumulated_intent < 0.5 and avg_distance < 0.3:
            trust_change += 0.02

        self.trust_score = max(0.0, min(1.0, self.trust_score + trust_change))

        # Track low trust rounds for exile
        if self.trust_score < TRUST_EXILE_THRESHOLD:
            self.low_trust_rounds += 1
        else:
            self.low_trust_rounds = 0

    def _update_state(self):
        """Classify intent state based on accumulation."""
        x = self.accumulated_intent

        # Check for exile condition (AC-2.3.2)
        if self.low_trust_rounds >= TRUST_EXILE_ROUNDS:
            self.state = IntentState.EXILED
        elif x < 0.5:
            self.state = IntentState.BENIGN
        elif x < 1.0:
            self.state = IntentState.NEUTRAL
        elif x < 2.0:
            self.state = IntentState.DRIFTING
        else:
            self.state = IntentState.ADVERSARIAL

    @property
    def x_factor(self) -> float:
        """
        Get the 'x' factor for H(d,R)^x formula.

        Returns a value typically between 0.5 and 3.0:
        - x < 1: Forgiving (brief deviation)
        - x = 1: Standard H(d,R)
        - x > 1: Compounding (sustained adversarial)
        """
        # Base x from accumulated intent
        base_x = 0.5 + self.accumulated_intent * 0.25

        # Modify by trust score (low trust amplifies x)
        trust_modifier = 1.0 + (1.0 - self.trust_score)

        return min(3.0, base_x * trust_modifier)


# =============================================================================
# Extended Harmonic Wall
# =============================================================================

def harmonic_wall_basic(d: float, R: float = R_HARMONIC) -> float:
    """
    Original Harmonic Wall: H(d, R) = R^(d²)
    """
    return R ** (d ** 2)


def harmonic_wall_temporal(d: float, x: float, R: float = R_HARMONIC) -> float:
    """
    Extended Harmonic Wall with temporal intent: H(d, R)^x = R^(d² · x)

    Args:
        d: Distance from safe operation (0 to ~1 in Poincaré ball)
        x: Intent persistence factor from IntentHistory.x_factor
        R: Harmonic ratio (default 1.5 = perfect fifth)

    Returns:
        Security cost multiplier (grows superexponentially with sustained drift)
    """
    return R ** (d ** 2 * x)


def compare_scaling(d: float, x: float) -> Dict[str, float]:
    """
    Compare basic vs temporal harmonic wall at given distance and intent.
    """
    basic = harmonic_wall_basic(d)
    temporal = harmonic_wall_temporal(d, x)

    return {
        "distance": d,
        "x_factor": x,
        "H_basic": basic,
        "H_temporal": temporal,
        "amplification": temporal / basic if basic > 0 else float('inf')
    }


# =============================================================================
# Security Gate Integration
# =============================================================================

@dataclass
class TemporalSecurityGate:
    """
    Security gate that uses H(d,R)^x for authorization decisions.

    Integrates with the Omega decision function (AC-2.3.3):
    Ω = pqc_valid × harm_score × (1 - drift_norm/drift_max) × triadic_stable × spectral_score

    The temporal intent scaling modifies harm_score via H(d,R)^x.
    """
    histories: Dict[str, IntentHistory] = field(default_factory=dict)

    # Decision thresholds from AC-2.3.4
    ALLOW_THRESHOLD = 0.85
    QUARANTINE_THRESHOLD = 0.40

    def get_or_create_history(self, agent_id: str) -> IntentHistory:
        """Get or create intent history for an agent."""
        if agent_id not in self.histories:
            self.histories[agent_id] = IntentHistory(agent_id=agent_id)
        return self.histories[agent_id]

    def record_observation(
        self,
        agent_id: str,
        distance: float,
        velocity: float = 0.0,
        harmony: float = 0.0
    ):
        """Record an observation for an agent."""
        history = self.get_or_create_history(agent_id)
        history.add_sample(distance, velocity, harmony)

    def compute_omega(
        self,
        agent_id: str,
        pqc_valid: bool = True,
        triadic_stable: float = 1.0,
        spectral_score: float = 1.0
    ) -> Tuple[float, str]:
        """
        Compute Omega decision score using temporal intent scaling.

        Ω = pqc_valid × harm_score × drift_factor × triadic_stable × spectral_score

        Where harm_score = 1 / H(d, R)^x (inverted so higher is better)
        And drift_factor = (1 - drift_norm/drift_max)

        Returns:
            (omega_score, decision) where decision is ALLOW/QUARANTINE/DENY/EXILE
        """
        history = self.get_or_create_history(agent_id)

        # Check for exile
        if history.state == IntentState.EXILED:
            return 0.0, "EXILE"

        # Get latest distance
        if history.samples:
            latest = history.samples[-1]
            d = latest.distance
        else:
            d = 0.0

        # Compute H(d,R)^x
        x = history.x_factor
        h_temporal = harmonic_wall_temporal(d, x)

        # Invert for harm_score (lower H = higher score = safer)
        # Use 1/(1 + log(H)) to keep in reasonable range
        harm_score = 1.0 / (1.0 + math.log(max(1.0, h_temporal)))

        # Drift factor from accumulated intent
        drift_factor = 1.0 - (history.accumulated_intent / MAX_INTENT_ACCUMULATION)

        # PQC factor
        pqc_factor = 1.0 if pqc_valid else 0.0

        # Compute Omega
        omega = pqc_factor * harm_score * drift_factor * triadic_stable * spectral_score

        # Decision
        if omega > self.ALLOW_THRESHOLD:
            decision = "ALLOW"
        elif omega > self.QUARANTINE_THRESHOLD:
            decision = "QUARANTINE"
        else:
            decision = "DENY"

        return omega, decision

    def get_status(self, agent_id: str) -> Dict:
        """Get full status for an agent."""
        history = self.get_or_create_history(agent_id)

        omega, decision = self.compute_omega(agent_id)

        return {
            "agent_id": agent_id,
            "state": history.state.value,
            "trust_score": history.trust_score,
            "accumulated_intent": history.accumulated_intent,
            "x_factor": history.x_factor,
            "low_trust_rounds": history.low_trust_rounds,
            "samples": len(history.samples),
            "omega": omega,
            "decision": decision
        }


# =============================================================================
# Demo
# =============================================================================

def demo():
    """Demonstrate temporal intent scaling."""
    print("=" * 70)
    print("  TEMPORAL INTENT SCALING - H(d,R)^x Extended Harmonic Wall")
    print("  'Security IS growth. Intent over time reveals truth.'")
    print("=" * 70)
    print()

    # Demo 1: Compare basic vs temporal at various distances and intents
    print("[SCALING] H(d,R) vs H(d,R)^x comparison:")
    print("-" * 60)
    print(f"  {'Distance':>8} {'x_factor':>8} {'H_basic':>12} {'H_temporal':>12} {'Amplify':>10}")
    print("-" * 60)

    test_cases = [
        (0.3, 0.5),   # Low distance, brief deviation (forgiving)
        (0.3, 1.0),   # Low distance, normal
        (0.3, 2.0),   # Low distance, sustained intent
        (0.6, 0.5),   # Medium distance, brief
        (0.6, 1.0),   # Medium distance, normal
        (0.6, 2.0),   # Medium distance, sustained
        (0.9, 0.5),   # High distance, brief
        (0.9, 1.0),   # High distance, normal
        (0.9, 2.0),   # High distance, sustained (catastrophic)
    ]

    for d, x in test_cases:
        result = compare_scaling(d, x)
        print(f"  {d:>8.2f} {x:>8.2f} {result['H_basic']:>12.2f} {result['H_temporal']:>12.2f} {result['amplification']:>10.2f}x")
    print()

    # Demo 2: Simulate agent behavior over time
    print("[SIMULATION] Agent behavior over time:")
    print("-" * 60)

    gate = TemporalSecurityGate()

    # Simulate benign agent
    print("  Benign Agent (stays near center):")
    for i in range(10):
        gate.record_observation("benign", distance=0.1 + 0.05 * (i % 3), harmony=0.8)
    status = gate.get_status("benign")
    print(f"    State: {status['state']}, x={status['x_factor']:.2f}, Omega={status['omega']:.3f} -> {status['decision']}")

    # Simulate drifting agent
    print("  Drifting Agent (gradually moves toward boundary):")
    for i in range(15):
        gate.record_observation("drifter", distance=0.2 + 0.04 * i, velocity=0.04, harmony=0.3)
    status = gate.get_status("drifter")
    print(f"    State: {status['state']}, x={status['x_factor']:.2f}, Omega={status['omega']:.3f} -> {status['decision']}")

    # Simulate adversarial agent
    print("  Adversarial Agent (sustained boundary approach):")
    for i in range(20):
        gate.record_observation("adversary", distance=0.7 + 0.01 * i, velocity=0.1, harmony=-0.5)
    status = gate.get_status("adversary")
    print(f"    State: {status['state']}, x={status['x_factor']:.2f}, Omega={status['omega']:.3f} -> {status['decision']}")

    # Simulate recovered agent (was drifting, came back)
    print("  Recovered Agent (drifted then returned):")
    for i in range(10):
        gate.record_observation("recovered", distance=0.5 + 0.03 * i, velocity=0.03, harmony=0.2)
    for i in range(15):
        gate.record_observation("recovered", distance=0.8 - 0.04 * i, velocity=-0.04, harmony=0.7)
    status = gate.get_status("recovered")
    print(f"    State: {status['state']}, x={status['x_factor']:.2f}, Omega={status['omega']:.3f} -> {status['decision']}")

    print()

    # Demo 3: Security amplification at boundary
    print("[BOUNDARY] Security amplification near Poincaré boundary:")
    print("-" * 60)
    print("  At d=0.95 (very close to boundary):")
    for x in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
        h = harmonic_wall_temporal(0.95, x)
        print(f"    x={x:.1f}: H(0.95, 1.5)^{x:.1f} = {h:,.0f}x security cost")
    print()

    print("=" * 70)
    print("  Summary:")
    print("    - Brief deviations (x<1): Forgiving, allows recovery")
    print("    - Normal operation (x=1): Standard H(d,R) scaling")
    print("    - Sustained drift (x>1): Compounding costs, triggers quarantine")
    print("    - Persistent adversarial (x>2): Near-infinite cost, exile imminent")
    print()
    print("  Formula: H(d, R)^x = R^(d² · x) where R=1.5")
    print("=" * 70)


if __name__ == "__main__":
    demo()
