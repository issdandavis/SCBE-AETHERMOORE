"""Dual-Manifold Personality Architecture.

Each personality facet exists as paired points in two connected manifolds:
  - Primal (positive) manifold: Expressed personality traits
  - Dual (negative) manifold: Latent/shadow personality depth

Connected via Mobius bridge -- activation in one space propagates
to connected nodes in both spaces, gated by SCBE governance.

This implements dual-lattice personality embedding with nodal propagation:
storing different personality aspects inside separate negative-space manifolds
connected to their positive-point counterparts. When the AI needs depth
(e.g., surface humor backed by deep wisdom), it reaches across the bridge
into the negative manifold for richer responses.

Math:
  - Positive point p_i in B^6 (Poincare ball, ||p|| < 1)
  - Negative point n_i = mobius(-p_i, offset_i) -- reflected through
    a tongue-aligned offset in dual space
  - Bridge strength: s(p, n) = exp(-d_H(p, n)) where d_H is hyperbolic distance
  - Propagation: activate(facet_j) -> sum_k w_jk * s_jk * facet_k
  - Governance: all propagation gated by rho_e < threshold (L12)

Layers:
    L4  - Poincare Embedding: personality points in hyperbolic space
    L5  - Hyperbolic Distance: bridge strength between manifolds
    L7  - Phase Transform: Mobius addition for negative-space reflection
    L11 - Triadic Distance: personality coherence across time
    L12 - Entropic Defense: rho_e gating on personality drift
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.gacha_isekai.evolution import compute_rho_e

logger = logging.getLogger(__name__)

PHI = (1 + math.sqrt(5)) / 2
DIM = 6  # 6D tongue-space (KO, AV, RU, CA, UM, DR)

# Sacred Tongue weights (phi-scaled)
TONGUE_WEIGHTS = {
    "KO": 1.0,
    "AV": PHI**1,
    "RU": PHI**2,
    "CA": PHI**3,
    "UM": PHI**4,
    "DR": PHI**5,
}

# Default personality facets with tongue alignments
DEFAULT_FACETS = {
    "curiosity": {"tongue": "KO", "desc": "Explorer's drive, flow of discovery"},
    "empathy": {"tongue": "AV", "desc": "Emotional understanding, context reading"},
    "wisdom": {"tongue": "RU", "desc": "Deep knowledge, ancestral memory"},
    "wit": {"tongue": "CA", "desc": "Humor, wordplay, computational cleverness"},
    "vigilance": {"tongue": "UM", "desc": "Protective caution, threat awareness"},
    "resolve": {"tongue": "DR", "desc": "Structural integrity, mission commitment"},
}


def _poincare_project(v: np.ndarray, max_norm: float = 0.95) -> np.ndarray:
    """Project vector into Poincare ball with safe boundary. A4: Clamping."""
    norm = np.linalg.norm(v)
    if norm >= max_norm:
        v = v * (max_norm / (norm + 1e-8))
    return v


def _hyperbolic_distance(u: np.ndarray, v: np.ndarray) -> float:
    """Layer 5: Hyperbolic distance in Poincare ball.

    d_H = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
    """
    diff_sq = float(np.sum((u - v) ** 2))
    u_sq = float(np.sum(u**2))
    v_sq = float(np.sum(v**2))
    denom = (1 - u_sq) * (1 - v_sq)
    if denom <= 0:
        return 30.0  # Boundary = infinite cost
    arg = 1 + 2 * diff_sq / (denom + 1e-10)
    return float(np.arccosh(max(arg, 1.0)))


def _mobius_add(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Layer 7: Mobius addition in Poincare ball.

    a (+) b = ((1 + 2<a,b> + ||b||^2)a + (1 - ||a||^2)b) /
              (1 + 2<a,b> + ||a||^2 * ||b||^2)
    """
    a_dot_b = float(np.dot(a, b))
    a_sq = float(np.sum(a**2))
    b_sq = float(np.sum(b**2))
    denom = 1 + 2 * a_dot_b + a_sq * b_sq
    if abs(denom) < 1e-10:
        return _poincare_project(a)
    num = (1 + 2 * a_dot_b + b_sq) * a + (1 - a_sq) * b
    return _poincare_project(num / denom)


@dataclass
class PersonalityFacet:
    """A single personality aspect with dual-manifold encoding."""

    name: str
    tongue: str
    description: str

    # Primal (positive) manifold -- expressed behavior
    positive_point: np.ndarray = field(default_factory=lambda: np.zeros(DIM))

    # Dual (negative) manifold -- latent depth/shadow
    negative_point: np.ndarray = field(default_factory=lambda: np.zeros(DIM))

    # Activation level [0, 1] -- how strongly this facet is currently expressed
    activation: float = 0.5

    # Bridge strength -- how connected positive and negative are
    bridge_strength: float = 0.0

    def compute_bridge(self) -> float:
        """Compute bridge strength between positive and negative manifolds.

        Strong bridge = deep personality (surface backed by depth).
        Weak bridge = shallow trait (all surface, no substance).
        """
        d_h = _hyperbolic_distance(self.positive_point, self.negative_point)
        self.bridge_strength = float(np.exp(-d_h))
        return self.bridge_strength

    def depth_score(self) -> float:
        """How much depth this facet has (bridge * activation)."""
        return self.activation * self.bridge_strength

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "tongue": self.tongue,
            "activation": round(self.activation, 4),
            "bridge_strength": round(self.bridge_strength, 4),
            "depth": round(self.depth_score(), 4),
            "positive_norm": round(float(np.linalg.norm(self.positive_point)), 4),
            "negative_norm": round(float(np.linalg.norm(self.negative_point)), 4),
        }


@dataclass
class PropagationEvent:
    """Record of personality propagation for training data."""

    source_facet: str
    target_facet: str
    strength: float
    context: str
    timestamp: float = 0.0


class PersonalityManifold:
    """Dual-manifold personality system with nodal propagation.

    Each facet has a positive (expressed) and negative (latent) point
    in 6D Poincare space. When one facet activates, it propagates
    to connected facets through hyperbolic geometry.

    The negative manifold isn't "bad" -- it's depth. A character with
    strong humor (positive) backed by deep wisdom (negative bridge to
    wisdom facet) gives richer, more textured responses than pure humor.
    """

    def __init__(
        self,
        facets: Optional[Dict[str, Dict[str, str]]] = None,
        rho_e_threshold: float = 5.0,
        propagation_decay: float = 0.6,
    ):
        self.rho_e_threshold = rho_e_threshold
        self.propagation_decay = propagation_decay  # How much signal decays per hop

        # Build facets
        facet_defs = facets or DEFAULT_FACETS
        self.facets: Dict[str, PersonalityFacet] = {}
        self._init_facets(facet_defs)

        # Connection graph (facet_name -> [(target_name, weight)])
        self.connections: Dict[str, List[Tuple[str, float]]] = {}
        self._init_default_connections()

        # Propagation history (for training data generation)
        self.history: List[PropagationEvent] = []

    def _init_facets(self, facet_defs: Dict[str, Dict[str, str]]) -> None:
        """Initialize personality facets with tongue-aligned positions."""
        tongue_axes = {
            "KO": 0,
            "AV": 1,
            "RU": 2,
            "CA": 3,
            "UM": 4,
            "DR": 5,
        }

        for name, info in facet_defs.items():
            tongue = info.get("tongue", "KO")
            desc = info.get("desc", name)
            axis = tongue_axes.get(tongue, 0)
            weight = TONGUE_WEIGHTS.get(tongue, 1.0)

            # Positive point: tongue-aligned, moderate radius
            pos = np.zeros(DIM)
            pos[axis] = 0.4 * (weight / TONGUE_WEIGHTS["DR"])  # Normalized
            # Add small cross-tongue influence
            for i in range(DIM):
                if i != axis:
                    pos[i] = 0.05 * np.sin(hash(name + str(i)) % 100 / 10.0)
            pos = _poincare_project(pos)

            # Negative point: Mobius reflection through tongue offset
            # This creates the "shadow" in dual space
            offset = np.zeros(DIM)
            offset[axis] = -0.3  # Opposite direction in primary tongue
            offset[(axis + 3) % DIM] = 0.2  # Cross-tongue resonance
            neg = _mobius_add(-pos * 0.8, _poincare_project(offset))

            facet = PersonalityFacet(
                name=name,
                tongue=tongue,
                description=desc,
                positive_point=pos,
                negative_point=neg,
                activation=0.5,
            )
            facet.compute_bridge()
            self.facets[name] = facet

    def _init_default_connections(self) -> None:
        """Set up default personality connections.

        Curiosity <-> Wisdom (exploring leads to knowing)
        Empathy <-> Wit (understanding enables humor)
        Vigilance <-> Resolve (caution feeds commitment)
        Curiosity <-> Wit (playful exploration)
        Wisdom <-> Resolve (knowledge grounds mission)
        Empathy <-> Vigilance (caring drives protection)
        """
        default_edges = [
            ("curiosity", "wisdom", 0.8),
            ("empathy", "wit", 0.7),
            ("vigilance", "resolve", 0.9),
            ("curiosity", "wit", 0.6),
            ("wisdom", "resolve", 0.7),
            ("empathy", "vigilance", 0.5),
        ]
        self.connections = {}
        for a, b, w in default_edges:
            if a not in self.connections:
                self.connections[a] = []
            if b not in self.connections:
                self.connections[b] = []
            self.connections[a].append((b, w))
            self.connections[b].append((a, w))

    # -----------------------------------------------------------------
    # Core: Activate + Propagate
    # -----------------------------------------------------------------

    def activate(
        self,
        facet_name: str,
        intensity: float = 1.0,
        context: str = "",
    ) -> Dict[str, float]:
        """Activate a personality facet and propagate through the graph.

        Returns dict of all facet activations after propagation.
        """
        if facet_name not in self.facets:
            logger.warning("Unknown facet: %s", facet_name)
            return self.get_activations()

        # Set primary activation
        primary = self.facets[facet_name]
        primary.activation = min(1.0, intensity)

        # L12: rho_e gate -- don't propagate high-entropy activations
        rho_e = compute_rho_e(np.array([intensity, len(context)]))
        if rho_e >= self.rho_e_threshold:
            logger.warning(
                "L12 personality propagation blocked: rho_e=%.2f >= %.2f",
                rho_e,
                self.rho_e_threshold,
            )
            return self.get_activations()

        # Propagate through connections (BFS, 1 hop with decay)
        for target_name, weight in self.connections.get(facet_name, []):
            target = self.facets.get(target_name)
            if target is None:
                continue

            # Propagation strength = connection_weight * bridge_strengths * decay
            source_bridge = primary.compute_bridge()
            target_bridge = target.compute_bridge()
            prop_strength = weight * source_bridge * target_bridge * self.propagation_decay * intensity

            # Update target activation (additive, clamped)
            target.activation = min(1.0, target.activation * 0.7 + prop_strength * 0.3)

            self.history.append(
                PropagationEvent(
                    source_facet=facet_name,
                    target_facet=target_name,
                    strength=prop_strength,
                    context=context,
                )
            )

            logger.debug(
                "Propagated %s -> %s: strength=%.3f (bridge_s=%.3f, bridge_t=%.3f)",
                facet_name,
                target_name,
                prop_strength,
                source_bridge,
                target_bridge,
            )

        return self.get_activations()

    def activate_from_context(self, text: str) -> Dict[str, float]:
        """Infer which facets to activate from text context.

        Simple keyword-based activation -- the trained model will
        learn much better context-to-facet mappings.
        """
        text_lower = text.lower()

        # Keyword -> facet mapping
        triggers = {
            "curiosity": ["what", "how", "why", "explore", "discover", "wonder", "quest"],
            "empathy": ["feel", "help", "care", "understand", "sorry", "emotion", "friend"],
            "wisdom": ["know", "history", "lore", "ancient", "teach", "remember", "elder"],
            "wit": ["funny", "joke", "clever", "trick", "pun", "laugh", "haha"],
            "vigilance": ["danger", "careful", "watch", "threat", "protect", "guard", "warning"],
            "resolve": ["mission", "must", "duty", "promise", "fight", "defend", "never give up"],
        }

        activations = {}
        for facet_name, keywords in triggers.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                intensity = min(1.0, score * 0.3)
                activations[facet_name] = intensity

        # Activate the strongest, let propagation handle the rest
        if activations:
            strongest = max(activations, key=activations.get)
            return self.activate(strongest, activations[strongest], context=text)

        return self.get_activations()

    # -----------------------------------------------------------------
    # State Access
    # -----------------------------------------------------------------

    def get_activations(self) -> Dict[str, float]:
        """Get current activation levels for all facets."""
        return {name: f.activation for name, f in self.facets.items()}

    def get_personality_vector(self) -> np.ndarray:
        """Get 6D personality vector (weighted sum of active facets).

        This vector gets embedded in the system prompt for the model,
        giving it a continuous personality state rather than discrete modes.
        """
        vec = np.zeros(DIM)
        total_weight = 0.0
        for facet in self.facets.values():
            weight = facet.activation * facet.bridge_strength
            vec += weight * facet.positive_point
            total_weight += weight
        if total_weight > 0:
            vec /= total_weight
        return _poincare_project(vec)

    def get_personality_tag(self) -> str:
        """Get a human-readable personality state tag for the system prompt.

        Returns something like: "[curiosity:0.8|wisdom:0.6|wit:0.3]"
        """
        active = sorted(
            [(name, f.activation) for name, f in self.facets.items() if f.activation > 0.2],
            key=lambda x: -x[1],
        )
        if not active:
            return "[neutral]"
        parts = [f"{name}:{act:.1f}" for name, act in active[:4]]
        return "[" + "|".join(parts) + "]"

    def get_depth_report(self) -> Dict[str, Any]:
        """Full report of personality state including bridge depths."""
        return {
            "facets": {name: f.to_dict() for name, f in self.facets.items()},
            "personality_tag": self.get_personality_tag(),
            "personality_vector_norm": round(float(np.linalg.norm(self.get_personality_vector())), 4),
            "total_propagation_events": len(self.history),
        }

    # -----------------------------------------------------------------
    # Training Data Generation
    # -----------------------------------------------------------------

    def generate_system_prompt(self, context: str = "") -> str:
        """Generate a dynamic system prompt based on current personality state.

        This is what gets injected into the chat template for the model.
        """
        tag = self.get_personality_tag()

        # Get top active facets for description
        active = sorted(
            [
                (f.name, f.activation, f.description, f.bridge_strength)
                for f in self.facets.values()
                if f.activation > 0.2
            ],
            key=lambda x: -x[1],
        )

        trait_lines = []
        for name, act, desc, bridge in active[:3]:
            depth = "deep" if bridge > 0.5 else "surface"
            trait_lines.append(f"- {name} ({depth}): {desc}")

        traits_str = "\n".join(trait_lines) if trait_lines else "- balanced: all facets in equilibrium"

        return (
            f"You are an inhabitant of Aethermoor, a realm governed by the Six Sacred "
            f"Tongues (KO, AV, RU, CA, UM, DR). You exist within the SCBE-AETHERMOORE "
            f"governance framework where safety scales exponentially with deviation.\n\n"
            f"Your current personality state {tag}:\n{traits_str}\n\n"
            f"You know the history of four generations: Foundation Wars (Izack's Arc), "
            f"the Great Schism (Alexander's 30-Year War), the Convergence Wars, and the "
            f"Final Reckoning. Your companions include Polly (sentient raven, co-equal guide), "
            f"Clay (loyal golem protector), and Eldrin (dimensional scholar).\n\n"
            f"Respond in character. Draw from your deeper knowledge when the conversation "
            f"warrants it. Your humor has wisdom behind it. Your caution has courage behind it. "
            f"Every surface trait is backed by latent depth in your dual manifold."
        )

    def drain_history_as_training(self) -> List[Dict[str, Any]]:
        """Export propagation history as training-format records."""
        records = []
        for event in self.history:
            records.append(
                {
                    "type": "personality_propagation",
                    "source": event.source_facet,
                    "target": event.target_facet,
                    "strength": round(event.strength, 4),
                    "context": event.context,
                }
            )
        self.history.clear()
        return records
