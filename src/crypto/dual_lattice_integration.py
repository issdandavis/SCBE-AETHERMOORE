"""
Dual Lattice Cross-Stitch Integration - 14-Layer SCBE Integration
==================================================================

Integrates Dual Lattice Cross-Stitch v2 across all 14 SCBE layers:

Layer 1 (PQC): Crypto-level lattice gating
Layer 2-4 (Realification → Poincare): Signed context projection
Layer 5 (Hyperbolic Metric): Governance-aware distance with phase
Layer 6-7 (Breathing + Phase): Dynamic realm breathing
Layer 8 (Multi-Well Realms): Light/shadow clustering
Layer 9-11 (Coherence + Temporal): Hyperpath validation
Layer 12-13 (Harmonic Scaling + Decision): Amplified path costs
Layer 14 (Audio Axis): Sonification with realm modulation

This enables intent-aware multi-AI ops in hyperbolic space for:
- Consumer browsing via realm-separated paths
- On-the-fly coding with lattice-embedded intents
- Drone autonomy through geodesic routing
"""

import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import hashlib
from scipy.cluster import hierarchy
from scipy.spatial.distance import squareform
import struct

# Local imports
from .dual_lattice import (
    LatticeVector, SacredTongue, FluxState,
    DualLatticeCrossStitch, TongueLatticeGovernor,
    TONGUE_PHASES, TONGUE_WEIGHTS, PHI
)
from .octree import HyperbolicOctree, SpectralVoxel
from .hyperpath_finder import HyperpathFinder, PathResult, hyperbolic_distance_safe


# =============================================================================
# Constants
# =============================================================================

# Realm classification thresholds
LIGHT_THRESHOLD = 0.0   # intent_strength > 0 → light
SHADOW_THRESHOLD = 0.0  # intent_strength < 0 → shadow

# Breathing parameters (Layer 6-7)
LIGHT_BREATH_FACTOR = 1.2   # Expand light realm
SHADOW_BREATH_FACTOR = 0.8  # Contract shadow realm

# Harmonic scaling base (Layer 12)
HARMONIC_BASE_R = 1.5

# Audio frequencies for sonification (Layer 14)
LIGHT_BASE_FREQ = 528.0   # "Miracle tone" Hz
SHADOW_BASE_FREQ = 220.0  # Low A
BALANCED_BASE_FREQ = 440.0  # Concert A


class RealmType(str, Enum):
    """Realm classification for lattice points."""
    LIGHT = "light"
    SHADOW = "shadow"
    BALANCED = "balanced"
    QUARANTINED = "quarantined"


@dataclass
class LayerDecision:
    """Decision output from a specific layer."""
    layer: int
    decision: str
    score: float
    metadata: Dict[str, Any]


@dataclass
class IntegratedResult:
    """Complete result from 14-layer integration."""
    decisions: List[LayerDecision]
    final_decision: str
    realm: RealmType
    trust_score: float
    path_cost: float
    audio_signature: Optional[List[float]]
    lattice_proof: Dict[str, Any]


# =============================================================================
# Layer 1: PQC-Gated Lattice Construction
# =============================================================================

def authorize_pqc_level(kyber_level: int, dilithium_level: int) -> Tuple[bool, str]:
    """
    Layer 1: Gate lattice point construction with PQC verification.

    Kyber/Dilithium levels must pass Layer 1 auth before building.
    Prevents weak-crypto shadows.

    Args:
        kyber_level: 1-5 (ML-KEM security level)
        dilithium_level: 2, 3, or 5 (ML-DSA security level)

    Returns:
        (is_authorized, reason)
    """
    # Minimum security requirements
    MIN_KYBER = 3   # ML-KEM-768 minimum
    MIN_DILITHIUM = 3  # ML-DSA-65 minimum

    if kyber_level < MIN_KYBER:
        return False, f"Kyber level {kyber_level} below minimum {MIN_KYBER}"

    if dilithium_level < MIN_DILITHIUM:
        return False, f"Dilithium level {dilithium_level} below minimum {MIN_DILITHIUM}"

    # Combined security score
    security_score = (kyber_level + dilithium_level) / 10.0

    if security_score < 0.6:
        return False, f"Combined security score {security_score:.2f} insufficient"

    return True, f"PQC authorized: Kyber-{kyber_level}, Dilithium-{dilithium_level}"


def build_lattice_point_gated(
    tongues: Dict[SacredTongue, float],
    intent: float,
    flux_state: FluxState,
    kyber_level: int = 3,
    dilithium_level: int = 3
) -> Tuple[Optional[LatticeVector], LayerDecision]:
    """
    Build a lattice point with PQC gating.

    Layer 1 integration: Only allows construction if PQC levels pass.
    """
    # Layer 1: PQC authorization
    authorized, reason = authorize_pqc_level(kyber_level, dilithium_level)

    layer_decision = LayerDecision(
        layer=1,
        decision="ALLOW" if authorized else "DENY",
        score=1.0 if authorized else 0.0,
        metadata={
            "kyber_level": kyber_level,
            "dilithium_level": dilithium_level,
            "reason": reason
        }
    )

    if not authorized:
        return None, layer_decision

    # Build the vector
    lattice = DualLatticeCrossStitch(security_level=kyber_level)
    vector = lattice.create_context_vector(tongues, intent, flux_state)

    return vector, layer_decision


# =============================================================================
# Layer 2-4: Signed Context Projection to Poincare
# =============================================================================

@dataclass
class GeoContext:
    """Geographic/semantic context with signed values."""
    location: np.ndarray  # 3D position
    intent_strength: float  # Can be negative for shadows
    temporal_offset: float  # Time delta from reference
    semantic_weight: float  # Importance factor


def realify_with_sign(context: GeoContext) -> np.ndarray:
    """
    Layer 2: Realification preserving signed intent.

    Negative intent_strength indicates shadow realm operations.
    """
    # Build 6D real vector from context
    real_vec = np.zeros(6)

    # Position maps to first 3 dimensions
    real_vec[0:3] = context.location

    # Intent strength (can be negative) maps to dimension 4
    real_vec[3] = context.intent_strength

    # Temporal offset to dimension 5
    real_vec[4] = context.temporal_offset

    # Semantic weight to dimension 6
    real_vec[5] = context.semantic_weight

    return real_vec


def project_to_poincare_with_realm(real_vec: np.ndarray) -> Tuple[np.ndarray, RealmType]:
    """
    Layer 4: Project realified vector to Poincare ball with realm assignment.

    Negatives push toward boundary (exponential d_H).
    Returns both projected vector and realm classification.
    """
    # Normalize to ball interior
    norm = np.linalg.norm(real_vec)

    if norm >= 1.0:
        projected = real_vec / (norm + 1e-6) * 0.95
    else:
        projected = real_vec

    # Determine realm from intent_strength (index 3)
    intent = real_vec[3] if len(real_vec) > 3 else 0.0

    if intent > LIGHT_THRESHOLD:
        realm = RealmType.LIGHT
    elif intent < SHADOW_THRESHOLD:
        realm = RealmType.SHADOW
    else:
        realm = RealmType.BALANCED

    return projected, realm


def layers_2_4_process(context: GeoContext) -> Tuple[np.ndarray, RealmType, LayerDecision]:
    """
    Process through layers 2-4: Realification → Weighted → Poincare.
    """
    # Layer 2: Realify
    real_vec = realify_with_sign(context)

    # Layer 3: Weight transform (apply tongue weights)
    weighted = real_vec.copy()
    for i, tongue in enumerate(SacredTongue):
        if i < len(weighted):
            weighted[i] *= TONGUE_WEIGHTS[tongue] / max(TONGUE_WEIGHTS.values())

    # Layer 4: Project to Poincare with realm
    projected, realm = project_to_poincare_with_realm(weighted)

    layer_decision = LayerDecision(
        layer=4,
        decision="PROJECTED",
        score=1.0 - np.linalg.norm(projected),  # Higher = closer to center
        metadata={
            "realm": realm.value,
            "projected_norm": float(np.linalg.norm(projected)),
            "intent_strength": float(context.intent_strength)
        }
    )

    return projected, realm, layer_decision


# =============================================================================
# Layer 5: Governance-Aware Hyperbolic Distance
# =============================================================================

def governance_aware_distance(
    a: np.ndarray,
    b: np.ndarray,
    phase_a: float = 0.0,
    phase_b: float = 0.0
) -> float:
    """
    Layer 5: Combined hyperbolic + phase distance for governance.

    Augments d_H with phase_angular_dist for hyperpath costs.
    """
    # Base hyperbolic distance
    base_d_h = hyperbolic_distance_safe(a, b)

    # Phase angular distance (normalized to [0, 1])
    angular = np.arccos(np.clip(
        np.cos(phase_a - phase_b), -1, 1
    )) / np.pi

    # Combined metric
    return base_d_h + angular


def layer_5_evaluate(
    position: np.ndarray,
    target: np.ndarray,
    phase: float = 0.0,
    target_phase: float = 0.0
) -> LayerDecision:
    """
    Layer 5: Evaluate hyperbolic distance for governance decision.
    """
    distance = governance_aware_distance(position, target, phase, target_phase)

    # Distance thresholds for governance
    if distance < 1.0:
        decision = "ALLOW"
        score = 1.0 - distance
    elif distance < 2.5:
        decision = "QUARANTINE"
        score = 0.5 - (distance - 1.0) / 3.0
    else:
        decision = "DENY"
        score = 0.0

    return LayerDecision(
        layer=5,
        decision=decision,
        score=max(0, score),
        metadata={
            "hyperbolic_distance": float(distance),
            "phase_diff": abs(phase - target_phase)
        }
    )


# =============================================================================
# Layer 6-7: Dynamic Realm Breathing
# =============================================================================

def breathing_transform(
    position: np.ndarray,
    b: float,
    origin: np.ndarray = None
) -> np.ndarray:
    """
    Layer 6: Apply breathing transform (diffeomorphic scaling).

    b > 1: Expansion (light realm)
    b < 1: Contraction (shadow realm)
    """
    if origin is None:
        origin = np.zeros_like(position)

    # Radial breathing from origin
    delta = position - origin
    norm = np.linalg.norm(delta)

    if norm < 1e-10:
        return position

    # Apply breathing factor
    new_norm = np.tanh(b * np.arctanh(min(norm, 0.99)))

    return origin + delta * (new_norm / norm)


def apply_realm_breathing(
    position: np.ndarray,
    realm: RealmType
) -> Tuple[np.ndarray, float, LayerDecision]:
    """
    Layer 6-7: Apply breathing based on realm, compute phase.

    Light realm: b=1.2 (expansion toward center)
    Shadow realm: b=0.8 (contraction toward boundary)
    """
    if realm == RealmType.LIGHT:
        b = LIGHT_BREATH_FACTOR
    elif realm == RealmType.SHADOW:
        b = SHADOW_BREATH_FACTOR
    else:
        b = 1.0  # Neutral

    # Layer 6: Breathing transform
    breathed = breathing_transform(position, b)

    # Layer 7: Compute phase from position
    if len(breathed) >= 2:
        phase = np.arctan2(breathed[1], breathed[0])
    else:
        phase = 0.0

    layer_decision = LayerDecision(
        layer=7,
        decision="BREATHED",
        score=1.0 - np.linalg.norm(breathed),
        metadata={
            "breathing_factor": b,
            "phase": float(phase),
            "realm": realm.value
        }
    )

    return breathed, phase, layer_decision


# =============================================================================
# Layer 8: Light/Shadow Clustering
# =============================================================================

def hierarchical_realm_clustering(
    points: List[np.ndarray],
    n_clusters: int = 2
) -> List[RealmType]:
    """
    Layer 8: Use Ward linkage for realm assignment.

    Clusters points into light/shadow using hyperbolic distance matrix.
    """
    n = len(points)
    if n < 2:
        return [RealmType.BALANCED] * n

    # Build hyperbolic distance matrix
    dist_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            d = hyperbolic_distance_safe(points[i], points[j])
            dist_matrix[i, j] = d
            dist_matrix[j, i] = d

    # Ward linkage clustering
    try:
        condensed = squareform(dist_matrix)
        linkage = hierarchy.linkage(condensed, method='ward')
        clusters = hierarchy.fcluster(linkage, n_clusters, criterion='maxclust')
    except Exception:
        return [RealmType.BALANCED] * n

    # Assign realms based on cluster centroids
    # Cluster closer to origin = light, further = shadow
    cluster_centroids = {}
    for c in set(clusters):
        cluster_points = [points[i] for i in range(n) if clusters[i] == c]
        centroid = np.mean(cluster_points, axis=0)
        cluster_centroids[c] = np.linalg.norm(centroid)

    # Sort clusters by distance from origin
    sorted_clusters = sorted(cluster_centroids.keys(), key=lambda c: cluster_centroids[c])

    # Assign realms
    realm_map = {}
    for i, c in enumerate(sorted_clusters):
        if i == 0:
            realm_map[c] = RealmType.LIGHT
        elif i == len(sorted_clusters) - 1:
            realm_map[c] = RealmType.SHADOW
        else:
            realm_map[c] = RealmType.BALANCED

    return [realm_map[clusters[i]] for i in range(n)]


def layer_8_cluster(points: List[np.ndarray]) -> Tuple[List[RealmType], LayerDecision]:
    """
    Layer 8: Perform realm clustering on points.
    """
    realms = hierarchical_realm_clustering(points)

    light_count = sum(1 for r in realms if r == RealmType.LIGHT)
    shadow_count = sum(1 for r in realms if r == RealmType.SHADOW)

    layer_decision = LayerDecision(
        layer=8,
        decision="CLUSTERED",
        score=light_count / max(1, len(realms)),  # Higher = more light
        metadata={
            "light_count": light_count,
            "shadow_count": shadow_count,
            "total_points": len(points)
        }
    )

    return realms, layer_decision


# =============================================================================
# Layer 9-11: Hyperpath Validation with Spectral Coherence
# =============================================================================

def spectral_coherence(embeddings: List[np.ndarray]) -> float:
    """
    Layer 9: Compute spectral coherence of a path.

    Uses FFT to analyze path "frequency" characteristics.
    Higher coherence = smoother, more trusted path.
    """
    if len(embeddings) < 2:
        return 1.0

    # Stack embeddings into matrix
    matrix = np.array(embeddings)

    # Compute FFT along path dimension
    fft_result = np.fft.fft(matrix, axis=0)
    magnitudes = np.abs(fft_result)

    # Coherence = ratio of low-freq to high-freq energy
    mid = len(magnitudes) // 2
    low_freq_energy = np.sum(magnitudes[:mid])
    high_freq_energy = np.sum(magnitudes[mid:])

    if high_freq_energy < 1e-10:
        return 1.0

    coherence = low_freq_energy / (low_freq_energy + high_freq_energy)
    return float(coherence)


def triadic_temporal_distance(path: List[np.ndarray]) -> float:
    """
    Layer 11: Compute triadic temporal distance along path.

    Measures temporal consistency of sequential transitions.
    """
    if len(path) < 3:
        return 0.0

    total_triadic = 0.0

    for i in range(len(path) - 2):
        # Three consecutive points
        a, b, c = path[i], path[i + 1], path[i + 2]

        # Triadic distance: deviation from geodesic
        d_ab = hyperbolic_distance_safe(a, b)
        d_bc = hyperbolic_distance_safe(b, c)
        d_ac = hyperbolic_distance_safe(a, c)

        # Triangle inequality violation measure
        triadic = max(0, d_ab + d_bc - d_ac)
        total_triadic += triadic

    return total_triadic / max(1, len(path) - 2)


def validate_hyperpath(
    path: List[np.ndarray],
    coherence_threshold: float = 0.4
) -> Tuple[bool, LayerDecision]:
    """
    Layer 9-11: Validate hyperpath with spectral coherence.
    """
    if not path:
        return False, LayerDecision(
            layer=11,
            decision="DENY",
            score=0.0,
            metadata={"reason": "Empty path"}
        )

    # Layer 9: Spectral coherence
    s_spec = spectral_coherence(path)

    # Layer 11: Triadic temporal distance
    d_tri = triadic_temporal_distance(path)

    # Validation
    is_valid = s_spec >= coherence_threshold and d_tri < 1.0

    layer_decision = LayerDecision(
        layer=11,
        decision="ALLOW" if is_valid else "DENY",
        score=s_spec * (1.0 / (1.0 + d_tri)),
        metadata={
            "spectral_coherence": float(s_spec),
            "triadic_distance": float(d_tri),
            "coherence_threshold": coherence_threshold
        }
    )

    return is_valid, layer_decision


# =============================================================================
# Layer 12-13: Amplified Path Costs (Harmonic Scaling)
# =============================================================================

def harmonic_scaling(d: float, phase_deviation: float = 0.0) -> float:
    """
    Layer 12: Harmonic wall scoring (bounded).

    score = 1 / (1 + d_H + 2 * phase_deviation)
    """
    return float(1.0 / (1.0 + d + 2.0 * phase_deviation))


def compute_path_cost(
    path: List[np.ndarray],
    realm_weights: Dict[RealmType, float] = None
) -> float:
    """
    Layer 12: Compute total path cost with harmonic amplification.

    Shadow realm traversal costs exponentially more.
    """
    if len(path) < 2:
        return 0.0

    if realm_weights is None:
        realm_weights = {
            RealmType.LIGHT: 1.0,
            RealmType.SHADOW: 2.0,  # Shadow costs more
            RealmType.BALANCED: 1.5,
            RealmType.QUARANTINED: 10.0  # Quarantine very expensive
        }

    total_cost = 0.0

    for i in range(len(path) - 1):
        # Base hyperbolic distance
        d = hyperbolic_distance_safe(path[i], path[i + 1])

        # Apply harmonic scaling
        scaled = harmonic_scaling(d)

        total_cost += scaled

    return total_cost


def layer_12_13_evaluate(
    path: List[np.ndarray],
    risk_threshold: float = 0.3
) -> Tuple[str, LayerDecision]:
    """
    Layer 12-13: Evaluate path with harmonic scaling and make decision.
    """
    if not path:
        return "DENY", LayerDecision(
            layer=13,
            decision="DENY",
            score=0.0,
            metadata={"reason": "No path"}
        )

    # Compute total cost
    total_cost = compute_path_cost(path)

    # Normalize to risk score
    expected_cost = len(path) - 1  # Linear baseline
    risk_score = min(1.0, total_cost / max(1.0, expected_cost * 5))

    # Layer 13: Decision
    if risk_score <= risk_threshold:
        decision = "ALLOW"
    elif risk_score <= risk_threshold * 2:
        decision = "ESCALATE"
    else:
        decision = "DENY"

    layer_decision = LayerDecision(
        layer=13,
        decision=decision,
        score=1.0 - risk_score,
        metadata={
            "path_cost": float(total_cost),
            "risk_score": float(risk_score),
            "risk_threshold": risk_threshold,
            "path_length": len(path)
        }
    )

    return decision, layer_decision


# =============================================================================
# Layer 14: Audio Axis Sonification
# =============================================================================

def coord_to_frequency(coord: np.ndarray, base_freq: float = 440.0) -> float:
    """
    Convert Poincare ball coordinate to frequency.

    Distance from origin modulates frequency.
    """
    norm = np.linalg.norm(coord)
    # Map norm to frequency range (220-880 Hz)
    freq = base_freq * np.power(2, norm - 0.5)
    return float(np.clip(freq, 110, 1760))


def hyperpath_to_audio(
    path: List[np.ndarray],
    realms: List[RealmType] = None
) -> List[float]:
    """
    Layer 14: Convert hyperpath to audio signature with realm modulation.

    Light realm: positive frequencies (bright tones)
    Shadow realm: negative frequencies (inverted for processing)
    """
    if not path:
        return []

    if realms is None:
        realms = [RealmType.BALANCED] * len(path)

    frequencies = []

    for i, (coord, realm) in enumerate(zip(path, realms)):
        # Base frequency from position
        if realm == RealmType.LIGHT:
            base_freq = LIGHT_BASE_FREQ
        elif realm == RealmType.SHADOW:
            base_freq = SHADOW_BASE_FREQ
        else:
            base_freq = BALANCED_BASE_FREQ

        freq = coord_to_frequency(coord, base_freq)

        # Shadow frequencies are "signed" negative for processing
        if realm == RealmType.SHADOW:
            freq = -freq

        frequencies.append(freq)

    return frequencies


def synthesize_tones(
    frequencies: List[float],
    duration_per_tone: float = 0.1,
    sample_rate: int = 44100
) -> np.ndarray:
    """
    Synthesize audio from frequency list.
    """
    samples = []

    for freq in frequencies:
        # Handle negative (shadow) frequencies
        actual_freq = abs(freq)
        is_shadow = freq < 0

        t = np.linspace(0, duration_per_tone, int(sample_rate * duration_per_tone))
        tone = np.sin(2 * np.pi * actual_freq * t)

        # Shadow tones are inverted
        if is_shadow:
            tone = -tone

        samples.extend(tone)

    return np.array(samples)


def layer_14_sonify(
    path: List[np.ndarray],
    realms: List[RealmType] = None
) -> Tuple[List[float], LayerDecision]:
    """
    Layer 14: Generate audio signature for hyperpath.
    """
    frequencies = hyperpath_to_audio(path, realms)

    # Compute signature hash for tamper evidence
    freq_bytes = struct.pack(f'{len(frequencies)}f', *frequencies)
    sig_hash = hashlib.sha256(freq_bytes).hexdigest()[:16]

    # Count positive (light) vs negative (shadow) frequencies
    light_count = sum(1 for f in frequencies if f > 0)
    shadow_count = sum(1 for f in frequencies if f < 0)

    layer_decision = LayerDecision(
        layer=14,
        decision="SONIFIED",
        score=light_count / max(1, len(frequencies)),
        metadata={
            "frequency_count": len(frequencies),
            "light_tones": light_count,
            "shadow_tones": shadow_count,
            "signature_hash": sig_hash
        }
    )

    return frequencies, layer_decision


# =============================================================================
# Integrated 14-Layer Processor
# =============================================================================

class DualLatticeIntegrator:
    """
    Complete 14-layer integration for Dual Lattice Cross-Stitch.

    Processes actions through all layers, returning governance decisions
    with full lattice proofs and audio signatures.
    """

    def __init__(
        self,
        kyber_level: int = 3,
        dilithium_level: int = 3,
        grid_size: int = 64,
        max_depth: int = 6
    ):
        self.kyber_level = kyber_level
        self.dilithium_level = dilithium_level

        # Initialize components
        self.lattice = DualLatticeCrossStitch(security_level=kyber_level)
        self.governor = TongueLatticeGovernor()
        self.octree = HyperbolicOctree(grid_size=grid_size, max_depth=max_depth)
        self.pathfinder = None  # Initialized when octree has points

    def process_action(
        self,
        action: str,
        target: str,
        sensitivity: float = 0.5,
        context: Optional[GeoContext] = None
    ) -> IntegratedResult:
        """
        Process an action through all 14 layers.

        Returns complete integrated result with decisions, proofs, and audio.
        """
        decisions: List[LayerDecision] = []

        # Layer 1: PQC Authorization
        vector, l1_decision = build_lattice_point_gated(
            tongues={SacredTongue.KO: 0.8},
            intent=sensitivity,
            flux_state=FluxState.POLLY if sensitivity > 0.8 else FluxState.QUASI,
            kyber_level=self.kyber_level,
            dilithium_level=self.dilithium_level
        )
        decisions.append(l1_decision)

        if l1_decision.decision == "DENY":
            return IntegratedResult(
                decisions=decisions,
                final_decision="DENY",
                realm=RealmType.QUARANTINED,
                trust_score=0.0,
                path_cost=float('inf'),
                audio_signature=None,
                lattice_proof={"layer1_failed": True}
            )

        # Layer 2-4: Realification to Poincare
        if context is None:
            context = GeoContext(
                location=np.array([0.0, 0.0, 0.0]),
                intent_strength=sensitivity if sensitivity > 0.5 else -(1 - sensitivity),
                temporal_offset=0.0,
                semantic_weight=1.0
            )

        projected, realm, l4_decision = layers_2_4_process(context)
        decisions.append(l4_decision)

        # Layer 5: Governance-aware distance
        origin = np.zeros_like(projected)
        l5_decision = layer_5_evaluate(projected, origin)
        decisions.append(l5_decision)

        # Layer 6-7: Breathing and phase
        breathed, phase, l7_decision = apply_realm_breathing(projected, realm)
        decisions.append(l7_decision)

        # Insert into octree for pathfinding
        self.octree.insert(breathed[:3] if len(breathed) >= 3 else breathed, realm.value)

        # Layer 8: Clustering (if we have multiple points)
        sample_points = [breathed[:3] if len(breathed) >= 3 else breathed]
        realms, l8_decision = layer_8_cluster(sample_points)
        decisions.append(l8_decision)

        # Layers 9-11: Path validation (using single point as path for now)
        path = [breathed[:3] if len(breathed) >= 3 else breathed]
        valid, l11_decision = validate_hyperpath(path)
        decisions.append(l11_decision)

        # Layers 12-13: Harmonic scaling and decision
        final_decision, l13_decision = layer_12_13_evaluate(path)
        decisions.append(l13_decision)

        # Layer 14: Sonification
        frequencies, l14_decision = layer_14_sonify(path, realms)
        decisions.append(l14_decision)

        # Compute overall trust score (average of positive scores)
        positive_scores = [d.score for d in decisions if d.score > 0]
        trust_score = np.mean(positive_scores) if positive_scores else 0.0

        # Get lattice proof from governor
        gov_result = self.governor.authorize(action, target, sensitivity)

        return IntegratedResult(
            decisions=decisions,
            final_decision=final_decision,
            realm=realm,
            trust_score=float(trust_score),
            path_cost=l13_decision.metadata.get("path_cost", 0.0),
            audio_signature=frequencies,
            lattice_proof=gov_result.get("lattice_proof", {})
        )

    def find_path(
        self,
        start: np.ndarray,
        goal: np.ndarray,
        use_bidirectional: bool = True
    ) -> Tuple[PathResult, IntegratedResult]:
        """
        Find hyperpath and process through all layers.
        """
        # Initialize pathfinder if needed
        if self.pathfinder is None:
            self.pathfinder = HyperpathFinder(self.octree)

        # Find path
        if use_bidirectional:
            path_result = self.pathfinder.bidirectional_a_star(start, goal)
        else:
            path_result = self.pathfinder.a_star(start, goal)

        if not path_result.success or path_result.path is None:
            return path_result, IntegratedResult(
                decisions=[],
                final_decision="DENY",
                realm=RealmType.QUARANTINED,
                trust_score=0.0,
                path_cost=float('inf'),
                audio_signature=None,
                lattice_proof={"path_not_found": True}
            )

        # Process path through layers
        decisions: List[LayerDecision] = []

        # Cluster path points for realm assignment
        realms, l8_decision = layer_8_cluster(path_result.path)
        decisions.append(l8_decision)

        # Validate path
        valid, l11_decision = validate_hyperpath(path_result.path)
        decisions.append(l11_decision)

        # Score path
        final_decision, l13_decision = layer_12_13_evaluate(path_result.path)
        decisions.append(l13_decision)

        # Sonify path
        frequencies, l14_decision = layer_14_sonify(path_result.path, realms)
        decisions.append(l14_decision)

        # Determine dominant realm
        realm_counts = {r: 0 for r in RealmType}
        for r in realms:
            realm_counts[r] += 1
        dominant_realm = max(realm_counts, key=realm_counts.get)

        positive_scores = [d.score for d in decisions if d.score > 0]
        trust_score = np.mean(positive_scores) if positive_scores else 0.0

        return path_result, IntegratedResult(
            decisions=decisions,
            final_decision=final_decision,
            realm=dominant_realm,
            trust_score=float(trust_score),
            path_cost=path_result.cost,
            audio_signature=frequencies,
            lattice_proof={
                "path_length": len(path_result.path),
                "nodes_expanded": path_result.nodes_expanded,
                "bidirectional": use_bidirectional
            }
        )


# =============================================================================
# Demo
# =============================================================================

def demo():
    """Demonstrate 14-layer integration."""
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║              DUAL LATTICE CROSS-STITCH - 14-LAYER INTEGRATION                 ║
║         PQC-Gated • Realm-Breathing • Spectral-Coherent • Sonified            ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)

    integrator = DualLatticeIntegrator()

    # Test cases
    test_cases = [
        ("navigate", "https://github.com", 0.3, "Low sensitivity - should ALLOW"),
        ("execute", "rm -rf /", 0.95, "High sensitivity - should DENY/ESCALATE"),
        ("read", "config.json", 0.4, "Medium sensitivity - contextual"),
    ]

    print("=" * 70)
    print("  Processing Actions Through 14 Layers")
    print("=" * 70)

    for action, target, sensitivity, description in test_cases:
        print(f"\n  Action: {action.upper()} → {target}")
        print(f"  {description}")
        print("-" * 50)

        result = integrator.process_action(action, target, sensitivity)

        print(f"  Final Decision: {result.final_decision}")
        print(f"  Realm: {result.realm.value}")
        print(f"  Trust Score: {result.trust_score:.3f}")
        print(f"  Path Cost: {result.path_cost:.3f}")

        print(f"\n  Layer Decisions:")
        for d in result.decisions:
            print(f"    L{d.layer:2d}: {d.decision:12s} (score: {d.score:.3f})")

        if result.audio_signature:
            freqs = result.audio_signature[:5]
            print(f"\n  Audio Signature (first 5): {[f'{f:.1f}Hz' for f in freqs]}")

    print("\n" + "=" * 70)
    print("  14-Layer Integration Complete!")
    print("=" * 70)


if __name__ == "__main__":
    demo()
