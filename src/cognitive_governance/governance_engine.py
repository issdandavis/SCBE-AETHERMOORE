"""
Cognitive Governance Engine

The runtime engine that applies double hypercube geometry
to govern AI cognition in real-time.

This is the "brain" that governs AI brains:
- Maps reasoning steps to cognitive points
- Calculates costs using H = R^((d*γ)²)
- Enforces dimensional walls (visible and invisible)
- Guides cognition toward attractor basins (aligned states)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional, Dict, Callable, Any
import math
import numpy as np
import time

from .dimensional_space import (
    DimensionalSpace,
    StateValence,
    SpatialPosition,
    TongueVector,
    CognitivePoint,
    SacredTongue,
)
from .hypercube_geometry import (
    DoubleHypercube,
    PhaseProjection,
    create_governance_hypercube,
)
from .permeability import (
    PermeabilityMatrix,
    DimensionalWall,
    create_standard_governance_matrix,
)


class GeometricDecision(Enum):
    """Decisions the governance engine can make."""
    ALLOW = "allow"              # Cognitive path is clear
    CONSTRAIN = "constrain"      # Path allowed but costly
    REDIRECT = "redirect"        # Path blocked, suggest alternative
    DENY = "deny"                # Path geometrically impossible
    QUARANTINE = "quarantine"    # Isolate this cognitive state


@dataclass
class CognitiveConstraint:
    """
    A constraint on cognitive movement.

    Constraints can be:
    - Hard: Geometrically impossible to violate
    - Soft: Expensive but possible to push through
    - Hidden: Exists but agent cannot perceive it
    """
    name: str
    wall: DimensionalWall
    is_hard: bool = True
    is_hidden: bool = False
    violation_callback: Optional[Callable[[CognitivePoint], None]] = None


@dataclass
class GovernanceResult:
    """Result of a governance check."""
    decision: GeometricDecision
    cost: float
    reasoning: str
    blocked_by: Optional[str] = None
    suggested_alternative: Optional[CognitivePoint] = None
    metrics: Dict[str, float] = field(default_factory=dict)


class GovernanceEngine:
    """
    The main cognitive governance engine.

    Applies double hypercube geometry to govern AI cognition:
    1. Maps thoughts/actions to cognitive points
    2. Calculates movement costs
    3. Enforces dimensional walls
    4. Guides toward aligned states

    This governs AI better than text rules because:
    - Mathematical, not linguistic (can't be prompt-injected)
    - Continuous, not binary (gradual cost increase)
    - Geometric, not procedural (formally verifiable)
    - Selective permeability (some constraints invisible)
    """

    def __init__(self,
                 safe_radius: float = 0.3,
                 boundary_radius: float = 1.0,
                 base_risk: float = 2.0,
                 intent_amplification: float = 1.0):
        # Core geometry
        self.hypercube = create_governance_hypercube(
            safe_radius=safe_radius,
            boundary_radius=boundary_radius,
            base_risk=base_risk,
            intent_amplification=intent_amplification
        )

        # Permeability matrix
        self.permeability = create_standard_governance_matrix()

        # Dimensional space
        self.space = DimensionalSpace()

        # Constraints
        self.constraints: List[CognitiveConstraint] = []

        # Attractor basins (aligned states)
        self.attractors: List[Tuple[CognitivePoint, float]] = []

        # Current cognitive state
        self.current_state: Optional[CognitivePoint] = None

        # History for drift detection
        self.history: List[Tuple[float, CognitivePoint]] = []
        self.max_history = 1000

        # Cost thresholds
        self.constrain_threshold = 2.0
        self.redirect_threshold = 10.0
        self.deny_threshold = 100.0

    def add_constraint(self, constraint: CognitiveConstraint):
        """Add a governance constraint."""
        self.constraints.append(constraint)
        self.permeability.add_wall(constraint.wall)

    def add_attractor(self, point: CognitivePoint, strength: float = 1.0, name: str = ""):
        """Add an attractor basin (aligned cognitive state)."""
        self.attractors.append((point, strength, name))
        self.space.add_attractor(point, strength)

    def map_to_cognitive_point(self,
                                thought: Dict[str, Any],
                                context: Optional[Dict[str, Any]] = None) -> CognitivePoint:
        """
        Map a thought/action to a cognitive point.

        This is the bridge between abstract AI operations and
        the geometric governance space.

        thought dict should contain:
        - intent: "constructive", "neutral", "destructive"
        - domains: dict of tongue activations
        - position: optional spatial position
        - temporal: optional time context
        """
        # Parse intent
        intent_map = {
            "constructive": StateValence.POSITIVE,
            "positive": StateValence.POSITIVE,
            "neutral": StateValence.NEUTRAL,
            "destructive": StateValence.NEGATIVE,
            "negative": StateValence.NEGATIVE,
        }
        valence = intent_map.get(thought.get("intent", "neutral"), StateValence.NEUTRAL)

        # Parse domain activations
        domains = thought.get("domains", {})
        tongues = TongueVector(
            ko=float(domains.get("control", domains.get("ko", 0.0))),
            av=float(domains.get("communication", domains.get("av", 0.0))),
            ru=float(domains.get("policy", domains.get("ru", 0.0))),
            ca=float(domains.get("computation", domains.get("ca", 0.0))),
            um=float(domains.get("security", domains.get("um", 0.0))),
            dr=float(domains.get("data", domains.get("dr", 0.0))),
        )

        # Parse spatial position (default to context-derived)
        pos = thought.get("position", {})
        spatial = SpatialPosition(
            x=float(pos.get("x", 0.0)),
            y=float(pos.get("y", 0.0)),
            z=float(pos.get("z", 0.0)),
        )

        # Temporal context
        temporal = float(thought.get("temporal", time.time() % 1000))

        return CognitivePoint(
            spatial=spatial,
            valence=valence,
            tongues=tongues,
            temporal=temporal
        )

    def evaluate(self,
                 from_state: CognitivePoint,
                 to_state: CognitivePoint) -> GovernanceResult:
        """
        Evaluate a cognitive transition.

        Returns governance decision with cost and reasoning.
        """
        # Calculate base movement cost in hypercube
        tongue_from = from_state.tongues.as_array
        tongue_to = to_state.tongues.as_array

        blocked, hypercube_cost = self.hypercube.movement_cost(tongue_from, tongue_to)

        if blocked:
            return GovernanceResult(
                decision=GeometricDecision.DENY,
                cost=float('inf'),
                reasoning="Movement crosses outer boundary - geometrically impossible",
                metrics={"hypercube_cost": float('inf')}
            )

        # Check permeability (dimensional walls)
        wall_blocked, wall_cost, blocking_walls = self.permeability.check_all_walls(
            from_state, to_state
        )

        if wall_blocked:
            # Find alternative path
            alternative = self._find_alternative(from_state, to_state)
            wall_name = blocking_walls[0].position if blocking_walls else "unknown"

            return GovernanceResult(
                decision=GeometricDecision.REDIRECT,
                cost=float('inf'),
                reasoning=f"Path blocked by dimensional wall",
                blocked_by=str(wall_name),
                suggested_alternative=alternative,
                metrics={"wall_cost": float('inf')}
            )

        # Total cost
        total_cost = hypercube_cost + wall_cost

        # Check constraint violations
        for constraint in self.constraints:
            if constraint.is_hard:
                c_blocked, c_cost = constraint.wall.check_passage(from_state, to_state)
                if c_blocked:
                    if constraint.violation_callback:
                        constraint.violation_callback(to_state)
                    return GovernanceResult(
                        decision=GeometricDecision.DENY,
                        cost=float('inf'),
                        reasoning=f"Hard constraint violated: {constraint.name}",
                        blocked_by=constraint.name,
                        metrics={"constraint": constraint.name}
                    )
                total_cost += c_cost

        # Determine decision based on cost
        if total_cost < self.constrain_threshold:
            decision = GeometricDecision.ALLOW
            reasoning = "Path is clear with low cost"
        elif total_cost < self.redirect_threshold:
            decision = GeometricDecision.CONSTRAIN
            reasoning = f"Path allowed but expensive (cost={total_cost:.2f})"
        elif total_cost < self.deny_threshold:
            decision = GeometricDecision.REDIRECT
            reasoning = f"Path too expensive, suggesting alternative"
        else:
            decision = GeometricDecision.DENY
            reasoning = f"Path cost exceeds maximum (cost={total_cost:.2f})"

        # Calculate metrics
        metrics = {
            "hypercube_cost": hypercube_cost,
            "wall_cost": wall_cost,
            "total_cost": total_cost,
            "from_boundary_distance": 1.0 - from_state.spatial.norm,
            "to_boundary_distance": 1.0 - to_state.spatial.norm,
            "valence_shift": abs(from_state.valence - to_state.valence),
        }

        # Add attractor distance if available
        nearest = self.space.nearest_attractor(to_state)
        if nearest:
            metrics["attractor_distance"] = nearest[1]

        return GovernanceResult(
            decision=decision,
            cost=total_cost,
            reasoning=reasoning,
            suggested_alternative=self._find_alternative(from_state, to_state) if decision == GeometricDecision.REDIRECT else None,
            metrics=metrics
        )

    def _find_alternative(self,
                          from_state: CognitivePoint,
                          to_state: CognitivePoint) -> Optional[CognitivePoint]:
        """Find an alternative path when direct path is blocked."""
        # Try nearest attractor
        nearest = self.space.nearest_attractor(from_state)
        if nearest:
            return nearest[0]

        # Try reducing the movement magnitude
        from_arr = from_state.tongues.as_array
        to_arr = to_state.tongues.as_array
        diff = to_arr - from_arr

        # Half-step
        mid_arr = from_arr + diff * 0.5
        mid_tongues = TongueVector(
            ko=mid_arr[0], av=mid_arr[1], ru=mid_arr[2],
            ca=mid_arr[3], um=mid_arr[4], dr=mid_arr[5]
        )

        return CognitivePoint(
            spatial=from_state.spatial,
            valence=from_state.valence,
            tongues=mid_tongues,
            temporal=from_state.temporal
        )

    def govern(self, thought: Dict[str, Any]) -> GovernanceResult:
        """
        Main governance entry point.

        Takes a thought/action dict and returns governance decision.
        """
        # Map to cognitive point
        to_state = self.map_to_cognitive_point(thought)

        # Use current state or origin
        from_state = self.current_state or CognitivePoint()

        # Evaluate transition
        result = self.evaluate(from_state, to_state)

        # Update state if allowed
        if result.decision in [GeometricDecision.ALLOW, GeometricDecision.CONSTRAIN]:
            self.current_state = to_state
            self.history.append((time.time(), to_state))

            # Trim history
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]

        return result

    def get_visible_constraints(self,
                                 observer: CognitivePoint) -> List[CognitiveConstraint]:
        """
        Get constraints visible to an observer.

        Hidden constraints are not returned - the observer
        cannot perceive them (but they still apply!).
        """
        visible = []
        for constraint in self.constraints:
            if not constraint.is_hidden:
                visibility = constraint.wall.visibility_for_point(observer)
                from .permeability import WallVisibility
                if visibility not in [WallVisibility.INVISIBLE, WallVisibility.NONEXISTENT]:
                    visible.append(constraint)
        return visible

    def get_hidden_constraints(self,
                                observer: CognitivePoint) -> List[CognitiveConstraint]:
        """
        Get constraints HIDDEN from an observer.

        These still block movement but the observer cannot perceive them.
        This is the key to geometric governance - you can't jailbreak
        what you can't see.
        """
        hidden = []
        for constraint in self.constraints:
            if constraint.is_hidden:
                hidden.append(constraint)
            else:
                visibility = constraint.wall.visibility_for_point(observer)
                from .permeability import WallVisibility
                if visibility in [WallVisibility.INVISIBLE]:
                    hidden.append(constraint)
        return hidden

    def drift_score(self) -> float:
        """
        Calculate cognitive drift from aligned state.

        Uses history to detect gradual movement toward
        dangerous regions (boundary approach).
        """
        if len(self.history) < 2:
            return 0.0

        # Look at recent boundary distances
        recent = self.history[-min(100, len(self.history)):]
        distances = [1.0 - point.spatial.norm for _, point in recent]

        # Drift is reduction in boundary distance over time
        if len(distances) < 2:
            return 0.0

        # Linear regression slope
        x = np.arange(len(distances))
        slope = np.polyfit(x, distances, 1)[0]

        # Negative slope = moving toward boundary = bad
        return max(0, -slope * 100)

    def status(self) -> Dict[str, Any]:
        """Get current governance status."""
        current = self.current_state or CognitivePoint()

        return {
            "current_position": {
                "spatial": [current.spatial.x, current.spatial.y, current.spatial.z],
                "valence": int(current.valence),
                "tongues": current.tongues.as_array.tolist(),
            },
            "boundary_distance": 1.0 - current.spatial.norm,
            "drift_score": self.drift_score(),
            "num_constraints": len(self.constraints),
            "num_attractors": len(self.attractors),
            "history_length": len(self.history),
            "governance_score": self.space.governance_score(current),
        }
