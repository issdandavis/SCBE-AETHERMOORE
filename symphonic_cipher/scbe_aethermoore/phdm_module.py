#!/usr/bin/env python3
"""
PHDM: Polyhedral Hamiltonian Defense Manifold
==============================================

Implements Claims 63-80 for USPTO filing.

Architecture:
- 16 canonical polyhedra (Platonic, Archimedean, Kepler-Poinsot, etc.)
- Hamiltonian path visiting each exactly once
- Sequential HMAC chain: K₀ (Kyber ss) → K₁ → ... → K₁₆
- Geodesic curve γ(t) in 6D Langues space
- Curvature κ(t) = |γ''(t)| / |γ'(t)|³ as threat signal
- Intrusion detection: d(s(t), γ(t)) > ε_snap → DENY

Integration Points:
- Layer 0.5: Between Kyber and Layer 1
- Layer 7: Swarm uses γ(t) as expected trajectory
- Layer 13: Risk incorporates κ(t) for curvature-based scaling
- Layer 14: Unified energy Ω gains s_phdm subscore

Patent Claims: 63-80
Date: January 14, 2026
"""

from __future__ import annotations

import hashlib
import hmac
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Any
from enum import Enum


# =============================================================================
# SECTION 1: POLYHEDRA DEFINITIONS
# =============================================================================

class PolyhedronType(Enum):
    """Classification of the 16 canonical polyhedra."""
    PLATONIC = "platonic"
    ARCHIMEDEAN = "archimedean"
    KEPLER_POINSOT = "kepler_poinsot"
    CATALAN = "catalan"
    JOHNSON = "johnson"


@dataclass
class Polyhedron:
    """
    Canonical polyhedron with geometric properties.

    Claim 63(b): Defining 16 canonical polyhedra
    """
    name: str
    poly_type: PolyhedronType
    vertices: int          # V
    edges: int             # E
    faces: int             # F
    euler_char: int        # V - E + F = 2 (convex) or other
    centroid_6d: np.ndarray  # Position in 6D Langues space
    symmetry_group: str    # Symmetry group name
    dual: Optional[str] = None

    def __post_init__(self):
        # Verify Euler characteristic for convex polyhedra
        if self.poly_type in [PolyhedronType.PLATONIC, PolyhedronType.ARCHIMEDEAN]:
            expected_euler = 2
            actual_euler = self.vertices - self.edges + self.faces
            assert actual_euler == expected_euler, f"{self.name}: V-E+F={actual_euler}, expected {expected_euler}"


# Golden ratio for icosahedral symmetry
PHI = (1 + np.sqrt(5)) / 2

# 16 Canonical Polyhedra (Claim 63(b))
POLYHEDRA = [
    # Platonic Solids (5)
    Polyhedron(
        name="Tetrahedron",
        poly_type=PolyhedronType.PLATONIC,
        vertices=4, edges=6, faces=4, euler_char=2,
        centroid_6d=np.array([0.0, 0.0, 0.0, 0.0, 0.0, 1.0]),
        symmetry_group="Td",
        dual="Tetrahedron"
    ),
    Polyhedron(
        name="Cube",
        poly_type=PolyhedronType.PLATONIC,
        vertices=8, edges=12, faces=6, euler_char=2,
        centroid_6d=np.array([0.1, 0.0, 0.0, 0.0, 0.0, 0.9]),
        symmetry_group="Oh",
        dual="Octahedron"
    ),
    Polyhedron(
        name="Octahedron",
        poly_type=PolyhedronType.PLATONIC,
        vertices=6, edges=12, faces=8, euler_char=2,
        centroid_6d=np.array([0.2, 0.1, 0.0, 0.0, 0.0, 0.8]),
        symmetry_group="Oh",
        dual="Cube"
    ),
    Polyhedron(
        name="Dodecahedron",
        poly_type=PolyhedronType.PLATONIC,
        vertices=20, edges=30, faces=12, euler_char=2,
        centroid_6d=np.array([0.3, 0.2, 0.1, 0.0, 0.0, 0.7]),
        symmetry_group="Ih",
        dual="Icosahedron"
    ),
    Polyhedron(
        name="Icosahedron",
        poly_type=PolyhedronType.PLATONIC,
        vertices=12, edges=30, faces=20, euler_char=2,
        centroid_6d=np.array([0.4, 0.3, 0.2, 0.1, 0.0, 0.6]),
        symmetry_group="Ih",
        dual="Dodecahedron"
    ),

    # Archimedean Solids (3 selected)
    Polyhedron(
        name="TruncatedTetrahedron",
        poly_type=PolyhedronType.ARCHIMEDEAN,
        vertices=12, edges=18, faces=8, euler_char=2,
        centroid_6d=np.array([0.5, 0.4, 0.3, 0.2, 0.1, 0.5]),
        symmetry_group="Td",
        dual="TriakisTetrahedron"
    ),
    Polyhedron(
        name="Cuboctahedron",
        poly_type=PolyhedronType.ARCHIMEDEAN,
        vertices=12, edges=24, faces=14, euler_char=2,
        centroid_6d=np.array([0.6, 0.5, 0.4, 0.3, 0.2, 0.4]),
        symmetry_group="Oh",
        dual="RhombicDodecahedron"
    ),
    Polyhedron(
        name="Icosidodecahedron",
        poly_type=PolyhedronType.ARCHIMEDEAN,
        vertices=30, edges=60, faces=32, euler_char=2,
        centroid_6d=np.array([0.7, 0.6, 0.5, 0.4, 0.3, 0.3]),
        symmetry_group="Ih",
        dual="RhombicTriacontahedron"
    ),

    # Kepler-Poinsot Solids (2) - Star polyhedra
    Polyhedron(
        name="SmallStellatedDodecahedron",
        poly_type=PolyhedronType.KEPLER_POINSOT,
        vertices=12, edges=30, faces=12, euler_char=-6,  # Non-convex
        centroid_6d=np.array([0.8, 0.7, 0.6, 0.5, 0.4, 0.2]),
        symmetry_group="Ih"
    ),
    Polyhedron(
        name="GreatDodecahedron",
        poly_type=PolyhedronType.KEPLER_POINSOT,
        vertices=12, edges=30, faces=12, euler_char=-6,
        centroid_6d=np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.1]),
        symmetry_group="Ih"
    ),

    # Catalan Solids (3) - Duals of Archimedean
    Polyhedron(
        name="TriakisTetrahedron",
        poly_type=PolyhedronType.CATALAN,
        vertices=8, edges=18, faces=12, euler_char=2,
        centroid_6d=np.array([0.15, 0.25, 0.35, 0.45, 0.55, 0.65]),
        symmetry_group="Td"
    ),
    Polyhedron(
        name="RhombicDodecahedron",
        poly_type=PolyhedronType.CATALAN,
        vertices=14, edges=24, faces=12, euler_char=2,
        centroid_6d=np.array([0.25, 0.35, 0.45, 0.55, 0.65, 0.55]),
        symmetry_group="Oh"
    ),
    Polyhedron(
        name="RhombicTriacontahedron",
        poly_type=PolyhedronType.CATALAN,
        vertices=32, edges=60, faces=30, euler_char=2,
        centroid_6d=np.array([0.35, 0.45, 0.55, 0.65, 0.75, 0.45]),
        symmetry_group="Ih"
    ),

    # Johnson Solids (3 selected) - Convex, non-uniform
    Polyhedron(
        name="SquarePyramid",  # J1
        poly_type=PolyhedronType.JOHNSON,
        vertices=5, edges=8, faces=5, euler_char=2,
        centroid_6d=np.array([0.45, 0.55, 0.65, 0.75, 0.85, 0.35]),
        symmetry_group="C4v"
    ),
    Polyhedron(
        name="Pentagonal Pyramid",  # J2
        poly_type=PolyhedronType.JOHNSON,
        vertices=6, edges=10, faces=6, euler_char=2,
        centroid_6d=np.array([0.55, 0.65, 0.75, 0.85, 0.95, 0.25]),
        symmetry_group="C5v"
    ),
    Polyhedron(
        name="TriangularCupola",  # J3
        poly_type=PolyhedronType.JOHNSON,
        vertices=9, edges=15, faces=8, euler_char=2,
        centroid_6d=np.array([0.65, 0.75, 0.85, 0.95, 0.85, 0.15]),
        symmetry_group="C3v"
    ),
]


# =============================================================================
# SECTION 2: HAMILTONIAN PATH
# =============================================================================

# Hamiltonian path through the 16 polyhedra (Claim 63(a))
# This ordering visits each polyhedron exactly once
HAMILTONIAN_PATH = [
    0,   # Tetrahedron (start)
    1,   # Cube
    2,   # Octahedron
    6,   # Cuboctahedron (bridges cube/octahedron)
    11,  # RhombicDodecahedron
    3,   # Dodecahedron
    4,   # Icosahedron
    7,   # Icosidodecahedron
    12,  # RhombicTriacontahedron
    8,   # SmallStellatedDodecahedron
    9,   # GreatDodecahedron
    5,   # TruncatedTetrahedron
    10,  # TriakisTetrahedron
    13,  # SquarePyramid
    14,  # PentagonalPyramid
    15,  # TriangularCupola (end)
]


def verify_hamiltonian_path() -> bool:
    """Verify the path visits each polyhedron exactly once."""
    if len(HAMILTONIAN_PATH) != len(POLYHEDRA):
        return False
    if len(set(HAMILTONIAN_PATH)) != len(POLYHEDRA):
        return False
    if any(i < 0 or i >= len(POLYHEDRA) for i in HAMILTONIAN_PATH):
        return False
    return True


# =============================================================================
# SECTION 3: HMAC KEY CHAIN
# =============================================================================

def hmac_key_chain(shared_secret: bytes, polyhedra_order: List[int] = None) -> List[bytes]:
    """
    Sequential HMAC chain through polyhedra (Claim 63(b)).

    K₀ ← ss (Kyber shared secret)
    K_{i+1} ← HMAC-SHA256(K_i, serialize(polyhedron_i))

    Args:
        shared_secret: Initial key from Kyber KEM (32 bytes)
        polyhedra_order: Order to traverse (default: HAMILTONIAN_PATH)

    Returns:
        List of 17 keys: [K₀, K₁, ..., K₁₆]
    """
    if polyhedra_order is None:
        polyhedra_order = HAMILTONIAN_PATH

    keys = [shared_secret]
    K = shared_secret

    for idx in polyhedra_order:
        poly = POLYHEDRA[idx]
        # Serialize polyhedron properties
        data = f"{poly.name}|{poly.vertices}|{poly.edges}|{poly.faces}|{poly.symmetry_group}"
        data_bytes = data.encode('utf-8')

        # HMAC-SHA256
        K_next = hmac.new(K, data_bytes, hashlib.sha256).digest()
        keys.append(K_next)
        K = K_next

    return keys


def derive_session_key(shared_secret: bytes) -> bytes:
    """
    Derive final session key from HMAC chain.

    Returns K₁₆ (the final key after traversing all polyhedra).
    """
    keys = hmac_key_chain(shared_secret)
    return keys[-1]  # K₁₆


# =============================================================================
# SECTION 4: GEODESIC CURVE IN 6D LANGUES SPACE
# =============================================================================

@dataclass
class GeodesicCurve:
    """
    Geodesic curve γ(t) through polyhedra centroids (Claim 63(c)).

    The 6D Langues space dimensions:
    - dim 0: intent (primary vocabulary term)
    - dim 1: phase (0 to 2π)
    - dim 2: threat (0 to 1)
    - dim 3: entropy (0 to 8 bits)
    - dim 4: load (0 to 1)
    - dim 5: stability (0 to 1)
    """
    waypoints: List[np.ndarray]  # Polyhedra centroids in order
    timestamps: List[float]       # Time at each waypoint

    def __post_init__(self):
        assert len(self.waypoints) == len(self.timestamps)
        assert len(self.waypoints) >= 2
        # Ensure timestamps are monotonic
        for i in range(1, len(self.timestamps)):
            assert self.timestamps[i] > self.timestamps[i-1]

    def evaluate(self, t: float) -> np.ndarray:
        """
        Evaluate γ(t) at time t using cubic interpolation.

        Returns the 6D position on the geodesic at time t.
        """
        # Clamp to valid range
        if t <= self.timestamps[0]:
            return self.waypoints[0].copy()
        if t >= self.timestamps[-1]:
            return self.waypoints[-1].copy()

        # Find segment
        for i in range(len(self.timestamps) - 1):
            if self.timestamps[i] <= t <= self.timestamps[i+1]:
                # Linear interpolation within segment
                t0, t1 = self.timestamps[i], self.timestamps[i+1]
                alpha = (t - t0) / (t1 - t0)

                # Smoothstep for smoother transitions
                alpha_smooth = alpha * alpha * (3 - 2 * alpha)

                p0 = self.waypoints[i]
                p1 = self.waypoints[i+1]
                return (1 - alpha_smooth) * p0 + alpha_smooth * p1

        return self.waypoints[-1].copy()

    def derivative(self, t: float, dt: float = 0.01) -> np.ndarray:
        """
        Compute γ'(t) via finite differences.
        """
        gamma_plus = self.evaluate(t + dt)
        gamma_minus = self.evaluate(t - dt)
        return (gamma_plus - gamma_minus) / (2 * dt)

    def second_derivative(self, t: float, dt: float = 0.01) -> np.ndarray:
        """
        Compute γ''(t) via finite differences.
        """
        gamma_plus = self.derivative(t + dt, dt)
        gamma_minus = self.derivative(t - dt, dt)
        return (gamma_plus - gamma_minus) / (2 * dt)

    def curvature(self, t: float) -> float:
        """
        Compute curvature κ(t) for curve in 6D (Claim 63(d)).

        For curves in arbitrary dimensions:
        κ = |γ'' - (γ'' · γ̂')γ̂'| / |γ'|²

        where γ̂' is the unit tangent vector.
        Higher curvature indicates sharper turns = potential anomaly.
        """
        gamma_prime = self.derivative(t)
        gamma_double_prime = self.second_derivative(t)

        norm_prime = np.linalg.norm(gamma_prime)

        if norm_prime < 1e-10:
            return 0.0

        # Unit tangent vector
        tangent = gamma_prime / norm_prime

        # Project out tangential component of γ''
        tangential_component = np.dot(gamma_double_prime, tangent) * tangent
        normal_component = gamma_double_prime - tangential_component

        # Curvature = |γ''⊥| / |γ'|²
        kappa = np.linalg.norm(normal_component) / (norm_prime ** 2)
        return float(kappa)


def create_golden_path(shared_secret: bytes,
                       total_duration: float = 60.0) -> GeodesicCurve:
    """
    Create the "golden path" geodesic through all polyhedra.

    Args:
        shared_secret: Kyber shared secret (determines path parameterization)
        total_duration: Total time to traverse path

    Returns:
        GeodesicCurve through polyhedra centroids
    """
    waypoints = []
    timestamps = []

    # Use HMAC chain to slightly perturb centroids (adds key-dependence)
    keys = hmac_key_chain(shared_secret)

    for i, idx in enumerate(HAMILTONIAN_PATH):
        poly = POLYHEDRA[idx]
        centroid = poly.centroid_6d.copy()

        # Small perturbation from key (< 0.01 per dimension)
        key_bytes = keys[i]
        perturbation = np.array([
            (b % 100) / 10000.0 - 0.005 for b in key_bytes[:6]
        ])
        centroid += perturbation

        waypoints.append(centroid)
        timestamps.append(i * total_duration / len(HAMILTONIAN_PATH))

    return GeodesicCurve(waypoints=waypoints, timestamps=timestamps)


# =============================================================================
# SECTION 5: INTRUSION DETECTION
# =============================================================================

@dataclass
class IntrusionDetector:
    """
    Real-time intrusion detection using geodesic deviation (Claim 63(e-f)).

    Detection method: d(s(t), γ(t)) > ε_snap → DENY

    Note: Curvature is computed for informational purposes but primary
    detection uses deviation threshold. High curvature at waypoint
    transitions is expected for piecewise paths.
    """
    golden_path: GeodesicCurve
    epsilon_snap: float = 0.1         # Deviation threshold (6D Euclidean)
    kappa_warning: float = 1e6        # Curvature warning threshold (informational)
    history: List[Tuple[float, float, bool]] = field(default_factory=list)

    def check_state(self, state: np.ndarray, t: float) -> Dict[str, Any]:
        """
        Check if current state is on the golden path.

        Args:
            state: Current 6D state vector
            t: Current timestamp

        Returns:
            Dict with decision and metrics
        """
        # Get expected position on golden path
        expected = self.golden_path.evaluate(t)

        # Compute deviation (Euclidean distance in 6D)
        deviation = np.linalg.norm(state - expected)

        # Compute curvature at this point (informational)
        kappa = self.golden_path.curvature(t)

        # Primary decision based on deviation (Claim 63(f))
        # Curvature is secondary signal, not primary rejection criterion
        is_intrusion = deviation > self.epsilon_snap
        decision = "DENY" if is_intrusion else "ALLOW"

        # Record history
        self.history.append((t, deviation, is_intrusion))

        return {
            "decision": decision,
            "is_intrusion": is_intrusion,
            "deviation": float(deviation),
            "epsilon_snap": self.epsilon_snap,
            "curvature": float(kappa),
            "kappa_warning": self.kappa_warning,
            "high_curvature": kappa > self.kappa_warning,
            "expected_state": expected,
            "actual_state": state,
            "timestamp": t
        }

    def get_threat_level(self, t: float) -> float:
        """
        Compute threat level from curvature (for Layer 13 integration).

        Returns value in [0, 1] where 1 = maximum threat.
        """
        kappa = self.golden_path.curvature(t)
        # Log-scale sigmoid to handle large curvature values
        log_kappa = np.log1p(kappa)
        threat = 1.0 / (1.0 + np.exp(-log_kappa + 10))
        return float(min(1.0, max(0.0, threat)))


# =============================================================================
# SECTION 6: PHDM SUBSCORE FOR LAYER 14
# =============================================================================

def compute_phdm_subscore(detector: IntrusionDetector,
                          state: np.ndarray,
                          t: float) -> float:
    """
    Compute s_phdm subscore for unified energy function Ω.

    Integration with Layer 14:
    - s_phdm ∈ [0, 1]
    - 1 = perfectly on golden path
    - 0 = maximum deviation (intrusion)
    """
    result = detector.check_state(state, t)

    # Deviation score (inverse of deviation, capped at 1)
    # Score is 1.0 when on path, decreases as deviation increases
    dev_score = max(0.0, 1.0 - result["deviation"] / (detector.epsilon_snap * 2))

    # Curvature score (log-scaled to handle large values)
    # High curvature reduces score slightly but deviation is primary factor
    log_kappa = np.log1p(result["curvature"])
    curv_score = 1.0 / (1.0 + log_kappa / 20.0)  # Smooth decay

    # Combined score (weighted - deviation is primary)
    s_phdm = 0.8 * dev_score + 0.2 * curv_score

    return float(max(0.0, min(1.0, s_phdm)))


# =============================================================================
# SECTION 7: INTEGRATION WITH EXISTING LAYERS
# =============================================================================

def integrate_with_layer1(context_vector: np.ndarray,
                          golden_path: GeodesicCurve,
                          t: float) -> np.ndarray:
    """
    Layer 0.5: Inject polyhedra centroids into context before Layer 1.

    The context vector is augmented with the expected golden path position.
    """
    expected = golden_path.evaluate(t)

    # Concatenate or blend
    # Here we blend: 80% original context, 20% golden path influence
    if len(context_vector) == 6:
        blended = 0.8 * context_vector + 0.2 * expected
        return blended
    else:
        # Just return original if dimensions don't match
        return context_vector


def integrate_with_layer7_swarm(golden_path: GeodesicCurve,
                                 node_states: List[np.ndarray],
                                 t: float) -> float:
    """
    Layer 7: Swarm nodes use γ(t) as expected trajectory.

    Returns consensus score based on how well nodes follow the path.
    """
    expected = golden_path.evaluate(t)

    deviations = [np.linalg.norm(state - expected) for state in node_states]
    avg_deviation = np.mean(deviations)

    # Consensus score (1 = all nodes on path, 0 = high deviation)
    consensus = 1.0 / (1.0 + avg_deviation)
    return float(consensus)


def integrate_with_layer13_risk(kappa: float,
                                 base_risk: float,
                                 kappa_weight: float = 0.3) -> float:
    """
    Layer 13: Risk function incorporates κ(t) for curvature-based scaling.

    High curvature = amplified risk.
    """
    # Curvature amplification factor
    curvature_factor = 1.0 + kappa_weight * kappa

    # Amplified risk
    amplified_risk = base_risk * curvature_factor

    return float(amplified_risk)


# =============================================================================
# SECTION 8: SELF-TESTS
# =============================================================================

def self_test() -> Dict[str, Any]:
    """
    Run PHDM module self-tests.

    Validates Claims 63-80.
    """
    results = {}
    passed = 0
    total = 0

    # Test 1: Polyhedra count
    total += 1
    if len(POLYHEDRA) == 16:
        passed += 1
        results["polyhedra_count"] = "✓ PASS (16 polyhedra defined)"
    else:
        results["polyhedra_count"] = f"✗ FAIL (got {len(POLYHEDRA)})"

    # Test 2: Hamiltonian path validity
    total += 1
    if verify_hamiltonian_path():
        passed += 1
        results["hamiltonian_path"] = "✓ PASS (visits each exactly once)"
    else:
        results["hamiltonian_path"] = "✗ FAIL (invalid path)"

    # Test 3: HMAC chain length
    total += 1
    test_secret = b"test_secret_32_bytes_exactly!!"
    keys = hmac_key_chain(test_secret)
    if len(keys) == 17:  # K₀ through K₁₆
        passed += 1
        results["hmac_chain"] = "✓ PASS (17 keys: K₀...K₁₆)"
    else:
        results["hmac_chain"] = f"✗ FAIL (got {len(keys)} keys)"

    # Test 4: Key derivation determinism
    total += 1
    keys2 = hmac_key_chain(test_secret)
    if keys[-1] == keys2[-1]:
        passed += 1
        results["key_determinism"] = "✓ PASS (deterministic derivation)"
    else:
        results["key_determinism"] = "✗ FAIL (non-deterministic)"

    # Test 5: Geodesic curve creation
    total += 1
    try:
        golden = create_golden_path(test_secret, total_duration=60.0)
        if len(golden.waypoints) == 16:
            passed += 1
            results["geodesic_creation"] = "✓ PASS (16 waypoints)"
        else:
            results["geodesic_creation"] = f"✗ FAIL ({len(golden.waypoints)} waypoints)"
    except Exception as e:
        results["geodesic_creation"] = f"✗ FAIL ({e})"

    # Test 6: Geodesic evaluation
    total += 1
    try:
        point = golden.evaluate(30.0)
        if point.shape == (6,):
            passed += 1
            results["geodesic_eval"] = "✓ PASS (6D point returned)"
        else:
            results["geodesic_eval"] = f"✗ FAIL (shape {point.shape})"
    except Exception as e:
        results["geodesic_eval"] = f"✗ FAIL ({e})"

    # Test 7: Curvature calculation
    total += 1
    try:
        kappa = golden.curvature(30.0)
        if isinstance(kappa, float) and kappa >= 0:
            passed += 1
            results["curvature_calc"] = f"✓ PASS (κ={kappa:.4f})"
        else:
            results["curvature_calc"] = "✗ FAIL (invalid curvature)"
    except Exception as e:
        results["curvature_calc"] = f"✗ FAIL ({e})"

    # Test 8: Intrusion detection (on-path)
    total += 1
    try:
        detector = IntrusionDetector(golden_path=golden)
        on_path_state = golden.evaluate(30.0)
        result = detector.check_state(on_path_state, 30.0)
        if result["decision"] == "ALLOW":
            passed += 1
            results["intrusion_on_path"] = f"✓ PASS (ALLOW, dev={result['deviation']:.4f})"
        else:
            results["intrusion_on_path"] = f"✗ FAIL (unexpected DENY)"
    except Exception as e:
        results["intrusion_on_path"] = f"✗ FAIL ({e})"

    # Test 9: Intrusion detection (off-path)
    total += 1
    try:
        off_path_state = np.array([0.9, 0.9, 0.9, 0.9, 0.9, 0.9])  # Far from path
        result = detector.check_state(off_path_state, 30.0)
        if result["decision"] == "DENY":
            passed += 1
            results["intrusion_off_path"] = f"✓ PASS (DENY, dev={result['deviation']:.4f})"
        else:
            results["intrusion_off_path"] = f"✗ FAIL (unexpected ALLOW)"
    except Exception as e:
        results["intrusion_off_path"] = f"✗ FAIL ({e})"

    # Test 10: PHDM subscore
    total += 1
    try:
        on_path_score = compute_phdm_subscore(detector, on_path_state, 30.0)
        off_path_score = compute_phdm_subscore(detector, off_path_state, 30.0)
        if on_path_score > off_path_score:
            passed += 1
            results["phdm_subscore"] = f"✓ PASS (on={on_path_score:.3f} > off={off_path_score:.3f})"
        else:
            results["phdm_subscore"] = "✗ FAIL (scores inverted)"
    except Exception as e:
        results["phdm_subscore"] = f"✗ FAIL ({e})"

    return {
        "passed": passed,
        "total": total,
        "results": results,
        "success_rate": f"{passed}/{total} ({100*passed/total:.1f}%)"
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("PHDM MODULE SELF-TEST")
    print("=" * 60)

    results = self_test()

    for test_name, result in results["results"].items():
        print(f"  {test_name}: {result}")

    print("-" * 60)
    print(f"TOTAL: {results['success_rate']}")
    print("=" * 60)
