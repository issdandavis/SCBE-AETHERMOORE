"""Personality Cluster Lattice — Multi-Plane Geometric Personality.

Extends the dual-manifold personality system with:

1. CLUSTERS not points — personality facets are fuzzy attractors in
   hyperbolic space, not single coordinates. Like social networks:
   messy splatter that topology forces into emergent structure.

2. TONGUE BRACKETS — the Langues metric tensor acts as a Lie bracket
   operator [T_i, T_j] defining how personality clusters interact
   across curved dimensions. The tongues don't just weight things,
   they define the rules of connection.

3. DRIFT CAPTURE — personality drift events (the AI "replaying a
   conversation for years") get captured as self-supervised training
   data. Drift that resolves = learning. Drift that doesn't = flag.

4. SPIN-TAGGED DATA — every personality datum carries ternary intent
   spin {-1, 0, +1} derived from its nearest cluster neighborhood.
   Nothing is binary anymore.

5. MULTI-PLANE SUPERPOSITION — personality layers exist across multiple
   manifold planes simultaneously, like harmonic overtones. Each layer
   is a different "scale" of the same trait.

6. ANTIVIRUS INTEGRATION — decimal drift detection distinguishes organic
   personality evolution from adversarial injection. Valid drift has the
   correct floating-point provenance watermark.

7. ISOLATED PORTALS — each personality subsystem runs in isolation
   (like isekai characters locked in rooms), merging only through
   governed portal channels for shared missions.

Layers:
    L3  - Langues Metric: tongue bracket algebra
    L5  - Hyperbolic Distance: cluster geodesics
    L7  - Mobius Phase: portal merge operations
    L9  - Spectral Coherence: multi-plane harmonic check
    L11 - Triadic Temporal: drift timeline tracking
    L12 - Entropic Defense: drift validation gate
    L14 - Decimal Drift: provenance watermark
"""

from __future__ import annotations

import logging
import math
import struct
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.gacha_isekai.evolution import compute_rho_e
from src.gacha_isekai.personality_manifold import (
    DIM,
    PHI,
    TONGUE_WEIGHTS,
    PersonalityManifold,
    _hyperbolic_distance,
    _poincare_project,
)

logger = logging.getLogger(__name__)

# Tongue indices for bracket computation
TONGUE_INDEX = {"KO": 0, "AV": 1, "RU": 2, "CA": 3, "UM": 4, "DR": 5}


# =====================================================================
# 1. Tongue Bracket Algebra
# =====================================================================


def tongue_bracket(tongue_a: str, tongue_b: str) -> np.ndarray:
    """Compute the Lie bracket [T_a, T_b] using Langues metric.

    The bracket defines HOW two tongue dimensions interact -- not just
    that they do, but the geometric structure of their relationship.

    [T_a, T_b] = w_a * w_b * (e_a x e_b) * phi^|a-b|

    where:
      w_a, w_b = phi-scaled tongue weights
      e_a, e_b = unit vectors along tongue axes
      x = antisymmetric product (like angular momentum)
      phi^|a-b| = golden ratio distance scaling

    Returns a 6D vector encoding the interaction direction.
    """
    idx_a = TONGUE_INDEX.get(tongue_a, 0)
    idx_b = TONGUE_INDEX.get(tongue_b, 0)

    if idx_a == idx_b:
        return np.zeros(DIM)  # Self-bracket is zero (Lie algebra axiom)

    w_a = TONGUE_WEIGHTS.get(tongue_a, 1.0)
    w_b = TONGUE_WEIGHTS.get(tongue_b, 1.0)

    # Antisymmetric interaction vector
    bracket = np.zeros(DIM)

    # The bracket lives in the "perpendicular" dimensions --
    # the interaction between KO and RU doesn't produce more KO or RU,
    # it produces something NEW in the dimensions between them
    mid_idx = (idx_a + idx_b) // 2
    perp_idx = (idx_a + idx_b + 3) % DIM  # perpendicular to both

    scale = w_a * w_b * PHI ** abs(idx_a - idx_b)
    sign = 1.0 if idx_a < idx_b else -1.0  # Antisymmetry

    bracket[mid_idx] = sign * scale * 0.3
    bracket[perp_idx] = sign * scale * 0.2

    # Normalize to stay in Poincare ball
    return _poincare_project(bracket, max_norm=0.5)


def bracket_matrix() -> np.ndarray:
    """Compute full 6x6 bracket interaction matrix.

    Entry [i,j] = magnitude of [T_i, T_j] bracket.
    This shows which tongue pairs have the strongest interactions.
    """
    tongues = list(TONGUE_INDEX.keys())
    matrix = np.zeros((6, 6))
    for i, ta in enumerate(tongues):
        for j, tb in enumerate(tongues):
            b = tongue_bracket(ta, tb)
            matrix[i, j] = float(np.linalg.norm(b))
    return matrix


# =====================================================================
# 2. Personality Clusters (not points)
# =====================================================================


@dataclass
class PersonalityCluster:
    """A fuzzy attractor in hyperbolic space.

    Not a single point but a CLOUD of related micro-states.
    Like a social cluster -- messy, overlapping, but with
    emergent structure forced by the topology.
    """

    name: str
    tongue: str

    # Cluster center (attractor basin)
    center: np.ndarray = field(default_factory=lambda: np.zeros(DIM))

    # Micro-states -- the "splatter" around the center
    particles: List[np.ndarray] = field(default_factory=list)

    # Spin states for each particle {-1, 0, +1}
    spins: List[int] = field(default_factory=list)

    # Cluster radius (how spread out the splatter is)
    radius: float = 0.0

    # Which manifold planes this cluster exists in
    planes: List[str] = field(default_factory=lambda: ["experience"])

    def add_particle(self, point: np.ndarray, spin: int = 0) -> None:
        """Add a micro-state to the cluster."""
        self.particles.append(_poincare_project(point))
        self.spins.append(max(-1, min(1, spin)))  # Clamp to {-1, 0, +1}
        self._update_stats()

    def _update_stats(self) -> None:
        """Recompute cluster center and radius."""
        if not self.particles:
            return

        # Center = Frechet mean approximation (Euclidean mean, then project)
        mean = np.mean(self.particles, axis=0)
        self.center = _poincare_project(mean)

        # Radius = mean hyperbolic distance from center
        if len(self.particles) > 1:
            dists = [_hyperbolic_distance(self.center, p) for p in self.particles]
            self.radius = float(np.mean(dists))

    def dominant_spin(self) -> int:
        """Get the dominant spin of the cluster.

        Positive spin = constructive intent
        Zero spin = neutral / balanced
        Negative spin = deconstructive (not bad -- sometimes you need to tear down)
        """
        if not self.spins:
            return 0
        total = sum(self.spins)
        if total > 0:
            return 1
        elif total < 0:
            return -1
        return 0

    def coherence(self) -> float:
        """How tightly clustered the particles are (0=scattered, 1=tight)."""
        if self.radius == 0 or not self.particles:
            return 1.0
        return float(np.exp(-self.radius))


# =====================================================================
# 3. Drift Capture (conversations replayed for years)
# =====================================================================


@dataclass
class DriftEvent:
    """A personality drift observation.

    Like a human replaying a conversation in their head --
    the AI notices its personality shifted and records the delta.
    """

    timestamp: float
    facet: str
    old_activation: float
    new_activation: float
    delta_vector: np.ndarray  # Direction of drift in 6D
    context: str
    resolved: bool = False
    resolution_time: float = 0.0

    @property
    def drift_magnitude(self) -> float:
        return float(np.linalg.norm(self.delta_vector))

    @property
    def age_seconds(self) -> float:
        return time.time() - self.timestamp

    def to_training_pair(self) -> Dict[str, Any]:
        """Convert resolved drift to training data.

        Resolved drift = the AI "figured it out" = valuable learning.
        Unresolved drift = still processing = not ready for training.
        """
        if not self.resolved:
            return {}

        return {
            "prompt": (
                f"Your {self.facet} shifted by {self.drift_magnitude:.3f} "
                f"in context: {self.context}"
            ),
            "response": (
                f"Drift resolved after {self.resolution_time - self.timestamp:.0f}s. "
                f"Activation moved from {self.old_activation:.2f} to "
                f"{self.new_activation:.2f}. The shift reflected "
                f"{'growth' if self.new_activation > self.old_activation else 'recalibration'}."
            ),
            "type": "personality_drift_resolution",
            "metadata": {
                "facet": self.facet,
                "magnitude": round(self.drift_magnitude, 4),
                "spin": 1 if self.new_activation > self.old_activation else -1,
            },
        }


# =====================================================================
# 4. Decimal Drift Provenance (antivirus for personality)
# =====================================================================


def compute_personality_watermark(state_vector: np.ndarray) -> float:
    """Compute the decimal drift watermark for a personality state.

    Organic personality evolution produces specific floating-point
    artifacts from the Poincare projection + Mobius operations.
    Injected/adversarial states lack this provenance signature.

    Returns fractional entropy -- organic states have specific range,
    injected states are too clean or too random.
    """
    # Extract fractional parts (the decimal drift signal)
    fractions = np.abs(state_vector) % 1.0

    # Organic drift from Poincare operations produces Gaussian-like
    # fractional distribution with sigma in [0.15, 0.45]
    frac_std = float(np.std(fractions))

    # Pack as float64, check byte-level entropy
    byte_entropy = 0.0
    for val in state_vector:
        packed = struct.pack("d", float(val))
        # Count unique bytes in the representation
        unique = len(set(packed))
        byte_entropy += unique / 8.0

    byte_entropy /= max(len(state_vector), 1)

    return frac_std * byte_entropy


def validate_personality_provenance(
    state_vector: np.ndarray,
    sigma_baseline: float = 0.3,
    tolerance: float = 2.0,
) -> Tuple[bool, str]:
    """L14: Validate that personality state has organic provenance.

    Returns (is_valid, reason).
    """
    watermark = compute_personality_watermark(state_vector)

    # Rule: sigma_decimal > 2 * baseline => ALERT (from Decimal Drift spec)
    if watermark > tolerance * sigma_baseline:
        return (
            False,
            f"Decimal drift anomaly: watermark={watermark:.4f} > {tolerance * sigma_baseline:.4f} (possible injection)",
        )

    if watermark < 0.01:
        return (
            False,
            f"Suspiciously clean state: watermark={watermark:.6f} (synthetic/manufactured)",
        )

    return True, f"Valid organic drift: watermark={watermark:.4f}"


# =====================================================================
# 5. Multi-Plane Superposition
# =====================================================================


@dataclass
class ManifoldPlane:
    """A single plane in the multi-plane personality stack.

    Personality exists at multiple scales simultaneously:
    - experience: raw events (fine-grained)
    - memory: consolidated patterns (medium)
    - identity: core self-model (coarse, stable)

    Each plane has its own copy of the personality clusters,
    rotated by different angles (superposition).
    """

    name: str
    rotation_angle: float  # Radians -- how this plane is tilted
    scale: float  # How coarse/fine this plane's view is
    clusters: Dict[str, PersonalityCluster] = field(default_factory=dict)

    def project_to_plane(self, point: np.ndarray) -> np.ndarray:
        """Project a point onto this plane's rotated view."""
        # 2D rotation in the first two dimensions (simplified from full SO(6))
        c = math.cos(self.rotation_angle)
        s = math.sin(self.rotation_angle)
        result = point.copy()
        x, y = result[0], result[1]
        result[0] = c * x - s * y
        result[1] = s * x + c * y
        # Scale
        result *= self.scale
        return _poincare_project(result)


# =====================================================================
# 6. Portal System (isolated merge channels)
# =====================================================================


@dataclass
class Portal:
    """A governed merge channel between isolated personality subsystems.

    Like the isekai where characters only meet on missions --
    personality facets run in isolation, sharing only through portals.
    """

    name: str
    source_cluster: str
    target_cluster: str
    bandwidth: float = 0.5  # How much information passes through [0, 1]
    governance_gated: bool = True
    active: bool = False
    transfer_count: int = 0

    def transfer(
        self,
        source_state: np.ndarray,
        rho_e: float,
        rho_e_threshold: float = 5.0,
    ) -> Optional[np.ndarray]:
        """Transfer personality state through the portal.

        Gated by SCBE governance -- high-entropy transfers are blocked.
        """
        if not self.active:
            return None

        # L12 governance gate
        if self.governance_gated and rho_e >= rho_e_threshold:
            logger.warning(
                "Portal %s blocked: rho_e=%.2f >= %.2f",
                self.name,
                rho_e,
                rho_e_threshold,
            )
            return None

        # Bandwidth scaling -- not all information passes through
        transferred = source_state * self.bandwidth
        self.transfer_count += 1

        return _poincare_project(transferred)


# =====================================================================
# 7. Main: PersonalityClusterLattice
# =====================================================================


class PersonalityClusterLattice:
    """Full personality system with clusters, brackets, drift, and portals.

    This extends PersonalityManifold from single points to a rich
    geometric lattice where:
    - Personality is CLUSTERS not points
    - Tongues define INTERACTION RULES via brackets
    - Drift is CAPTURED as training data
    - Data carries SPIN (intent)
    - Personality exists across MULTIPLE PLANES
    - Subsystems merge through GOVERNED PORTALS
    """

    def __init__(
        self,
        base_manifold: Optional[PersonalityManifold] = None,
        rho_e_threshold: float = 5.0,
        drift_resolution_timeout: float = 300.0,  # 5 min to resolve drift
    ):
        self.base = base_manifold or PersonalityManifold()
        self.rho_e_threshold = rho_e_threshold
        self.drift_timeout = drift_resolution_timeout

        # Clusters (built from base manifold facets)
        self.clusters: Dict[str, PersonalityCluster] = {}
        self._init_clusters()

        # Multi-plane stack
        self.planes: Dict[str, ManifoldPlane] = {
            "experience": ManifoldPlane("experience", rotation_angle=0.0, scale=1.0),
            "memory": ManifoldPlane("memory", rotation_angle=math.pi / 6, scale=0.7),
            "identity": ManifoldPlane(
                "identity", rotation_angle=math.pi / 3, scale=0.4
            ),
        }

        # Portals between clusters
        self.portals: Dict[str, Portal] = {}
        self._init_portals()

        # Drift tracking
        self.active_drifts: List[DriftEvent] = []
        self.resolved_drifts: List[DriftEvent] = []

        # Tongue bracket matrix (precomputed)
        self.bracket_mat = bracket_matrix()

    def _init_clusters(self) -> None:
        """Initialize clusters from base manifold facets."""
        for name, facet in self.base.facets.items():
            cluster = PersonalityCluster(
                name=name,
                tongue=facet.tongue,
                center=facet.positive_point.copy(),
                planes=["experience", "memory", "identity"],
            )
            # Seed with initial particles (the "splatter")
            for i in range(5):
                noise = np.random.randn(DIM) * 0.05
                particle = _poincare_project(facet.positive_point + noise)
                spin = 1 if i < 3 else 0  # Mostly constructive initially
                cluster.add_particle(particle, spin)

            # Also add negative-space particles
            for i in range(3):
                noise = np.random.randn(DIM) * 0.05
                particle = _poincare_project(facet.negative_point + noise)
                cluster.add_particle(particle, spin=-1)  # Shadow particles

            self.clusters[name] = cluster

    def _init_portals(self) -> None:
        """Create governed portals between personality clusters."""
        # Portals follow the bracket strength -- strongly interacting
        # tongues get wider bandwidth portals
        connections = [
            ("curiosity", "wisdom", 0.6),
            ("empathy", "wit", 0.5),
            ("vigilance", "resolve", 0.7),
            ("curiosity", "wit", 0.4),
            ("wisdom", "resolve", 0.5),
            ("empathy", "vigilance", 0.3),
        ]
        for src, tgt, bw in connections:
            # Adjust bandwidth by tongue bracket magnitude
            src_tongue = self.clusters[src].tongue
            tgt_tongue = self.clusters[tgt].tongue
            bracket_boost = float(
                np.linalg.norm(tongue_bracket(src_tongue, tgt_tongue))
            )
            adjusted_bw = min(1.0, bw + bracket_boost * 0.1)

            portal_name = f"{src}<>{tgt}"
            self.portals[portal_name] = Portal(
                name=portal_name,
                source_cluster=src,
                target_cluster=tgt,
                bandwidth=adjusted_bw,
                active=True,
            )

    # -----------------------------------------------------------------
    # Core Operations
    # -----------------------------------------------------------------

    def activate_cluster(
        self,
        cluster_name: str,
        intensity: float = 1.0,
        context: str = "",
        spin: int = 1,
    ) -> Dict[str, Any]:
        """Activate a personality cluster with spin-tagged intent.

        Propagates through portals to connected clusters.
        Records drift events for potential retraining.
        Validates through antivirus provenance check.
        """
        cluster = self.clusters.get(cluster_name)
        if cluster is None:
            return {"error": f"Unknown cluster: {cluster_name}"}

        # Record pre-activation state for drift detection
        old_activation = self.base.facets[cluster_name].activation

        # Add new particle to cluster with spin
        direction = cluster.center * intensity
        noise = np.random.randn(DIM) * 0.02
        new_particle = _poincare_project(direction + noise)
        cluster.add_particle(new_particle, spin)

        # Activate base manifold
        activations = self.base.activate(cluster_name, intensity, context)

        # Project across all planes (multi-plane superposition)
        for plane in self.planes.values():
            projected = plane.project_to_plane(new_particle)
            if cluster_name not in plane.clusters:
                plane.clusters[cluster_name] = PersonalityCluster(
                    name=cluster_name,
                    tongue=cluster.tongue,
                )
            plane.clusters[cluster_name].add_particle(projected, spin)

        # Portal propagation
        portal_results = {}
        for portal_name, portal in self.portals.items():
            if (
                portal.source_cluster == cluster_name
                or portal.target_cluster == cluster_name
            ):
                rho_e = compute_rho_e(np.array([intensity, len(context)]))
                transferred = portal.transfer(new_particle, rho_e, self.rho_e_threshold)
                if transferred is not None:
                    # Add transferred particle to target cluster
                    target_name = (
                        portal.target_cluster
                        if portal.source_cluster == cluster_name
                        else portal.source_cluster
                    )
                    target = self.clusters.get(target_name)
                    if target:
                        target.add_particle(
                            transferred, spin=0
                        )  # Neutral spin on transfer
                        portal_results[portal_name] = float(np.linalg.norm(transferred))

        # Drift detection
        new_activation = self.base.facets[cluster_name].activation
        if abs(new_activation - old_activation) > 0.1:
            drift = DriftEvent(
                timestamp=time.time(),
                facet=cluster_name,
                old_activation=old_activation,
                new_activation=new_activation,
                delta_vector=new_particle - cluster.center,
                context=context,
            )
            self.active_drifts.append(drift)

        # Antivirus provenance check
        personality_vec = self.base.get_personality_vector()
        provenance_valid, provenance_msg = validate_personality_provenance(
            personality_vec
        )
        if not provenance_valid:
            logger.warning("Personality antivirus alert: %s", provenance_msg)

        return {
            "cluster": cluster_name,
            "spin": spin,
            "coherence": cluster.coherence(),
            "dominant_spin": cluster.dominant_spin(),
            "particles": len(cluster.particles),
            "portal_transfers": portal_results,
            "active_drifts": len(self.active_drifts),
            "provenance_valid": provenance_valid,
            "provenance_msg": provenance_msg,
            "activations": activations,
        }

    def resolve_drifts(self) -> List[Dict[str, Any]]:
        """Check active drifts and resolve any that have settled.

        Resolved drifts become training data — the AI "figured it out."
        Timed-out drifts get flagged for review.
        """
        now = time.time()
        training_pairs = []
        still_active = []

        for drift in self.active_drifts:
            age = now - drift.timestamp

            # Check if drift has resolved (activation stabilized)
            current = self.base.facets.get(drift.facet)
            if current is None:
                continue

            delta = abs(current.activation - drift.new_activation)

            if delta < 0.05:
                # Stabilized -- resolved!
                drift.resolved = True
                drift.resolution_time = now
                self.resolved_drifts.append(drift)
                pair = drift.to_training_pair()
                if pair:
                    training_pairs.append(pair)
                logger.info(
                    "Drift resolved: %s (%.1fs, magnitude=%.3f)",
                    drift.facet,
                    age,
                    drift.drift_magnitude,
                )
            elif age > self.drift_timeout:
                # Timed out -- unresolved, flag it
                logger.warning(
                    "Drift timeout: %s (%.1fs, still shifting by %.3f)",
                    drift.facet,
                    age,
                    delta,
                )
                self.resolved_drifts.append(drift)  # Archive even if unresolved
            else:
                still_active.append(drift)

        self.active_drifts = still_active
        return training_pairs

    # -----------------------------------------------------------------
    # Reporting
    # -----------------------------------------------------------------

    def get_lattice_state(self) -> Dict[str, Any]:
        """Full lattice state report."""
        cluster_states = {}
        for name, cluster in self.clusters.items():
            cluster_states[name] = {
                "tongue": cluster.tongue,
                "particles": len(cluster.particles),
                "coherence": round(cluster.coherence(), 4),
                "dominant_spin": cluster.dominant_spin(),
                "radius": round(cluster.radius, 4),
                "planes": cluster.planes,
            }

        portal_states = {}
        for name, portal in self.portals.items():
            portal_states[name] = {
                "bandwidth": round(portal.bandwidth, 3),
                "transfers": portal.transfer_count,
                "active": portal.active,
            }

        plane_states = {}
        for name, plane in self.planes.items():
            plane_states[name] = {
                "rotation": round(plane.rotation_angle, 3),
                "scale": plane.scale,
                "clusters": len(plane.clusters),
            }

        return {
            "clusters": cluster_states,
            "portals": portal_states,
            "planes": plane_states,
            "active_drifts": len(self.active_drifts),
            "resolved_drifts": len(self.resolved_drifts),
            "bracket_matrix_norm": round(float(np.linalg.norm(self.bracket_mat)), 4),
            "personality_tag": self.base.get_personality_tag(),
        }

    def generate_system_prompt(self, context: str = "") -> str:
        """Generate system prompt with full lattice personality state.

        Extends the base manifold prompt with cluster/plane/spin info.
        """
        base_prompt = self.base.generate_system_prompt(context)

        # Add cluster info
        active_clusters = sorted(
            [
                (name, c.coherence(), c.dominant_spin())
                for name, c in self.clusters.items()
                if c.coherence() > 0.3
            ],
            key=lambda x: -x[1],
        )

        cluster_info = []
        for name, coh, spin in active_clusters[:3]:
            spin_word = (
                "constructive"
                if spin > 0
                else ("deconstructive" if spin < 0 else "balanced")
            )
            cluster_info.append(f"  {name}: coherence={coh:.1f}, intent={spin_word}")

        if cluster_info:
            base_prompt += (
                "\n\nYour personality clusters:\n"
                + "\n".join(cluster_info)
                + "\n\nDraw from the depth behind each cluster. "
                "Your responses emerge from overlapping personality fields, "
                "not single traits."
            )

        return base_prompt
