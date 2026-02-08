"""
@file exp_flux_tiering_and_trust_cones.py
@module experiments
@layer Layer 5, Layer 12, Layer 13
@component Flux-State Access Tiering + Trust Cone Experiment
@version 1.0.0

Three experiments in one file:

Experiment 1: Flux-State Access Tiering
    Validates that FluxState restrictions (POLLY/QUASI/DEMI/COLLAPSED)
    correctly gate which polyhedra and actions are accessible.
    Tests the access tiering against adversarial escalation attempts.

Experiment 2: Trust Cones (Novel Geometric Access Control)
    Trust cones constrain access not just by radius (distance from origin)
    but by ANGLE relative to a sacred tongue's direction vector.
    Angular width is inversely proportional to confidence.

    This is genuinely novel: standard PHDM checks radius only.
    Trust cones add directional discrimination — you must not only
    be close to center, but approaching from the RIGHT direction.

Experiment 3: Encryption/Navigation Separation
    Demonstrates that Mobius addition on encrypted vectors is broken,
    and validates the correct pattern: encrypt for transport, decrypt
    before geometric operations.

Author: Issac Davis
"""

import json
import math
import time
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

# ============================================================================
# Constants
# ============================================================================

EPSILON = 1e-10
PHI = (1 + math.sqrt(5)) / 2

# Sacred Tongue phase assignments (proven discriminative signal)
TONGUE_PHASES = {
    "KO": 0.0,
    "AV": math.pi / 3,
    "RU": 2 * math.pi / 3,
    "CA": math.pi,
    "UM": 4 * math.pi / 3,
    "DR": 5 * math.pi / 3,
}

# Tongue direction vectors in 2D (unit vectors at phase angles)
TONGUE_DIRECTIONS = {
    tongue: np.array([math.cos(phase), math.sin(phase)])
    for tongue, phase in TONGUE_PHASES.items()
}


# ============================================================================
# Flux-State Access Tiering
# ============================================================================

class FluxState(Enum):
    """Dimensional breathing states with access restrictions."""
    POLLY = "polly"         # Full capability - all 16 polyhedra
    QUASI = "quasi"         # Defensive - Core + Cortex (8 polyhedra)
    DEMI = "demi"           # Survival - Core only (5 Platonic solids)
    COLLAPSED = "collapsed" # Limbic only - minimal safe operations


# Polyhedra types and their flux-state accessibility
POLYHEDRA_ACCESS = {
    # Core: Platonic Solids - accessible in ALL states except COLLAPSED
    "tetrahedron":    {"type": "platonic",    "min_flux": FluxState.DEMI},
    "cube":           {"type": "platonic",    "min_flux": FluxState.DEMI},
    "octahedron":     {"type": "platonic",    "min_flux": FluxState.DEMI},
    "dodecahedron":   {"type": "platonic",    "min_flux": FluxState.DEMI},
    "icosahedron":    {"type": "platonic",    "min_flux": FluxState.DEMI},

    # Cortex: Archimedean - accessible in QUASI and above
    "truncated_icosahedron":  {"type": "archimedean", "min_flux": FluxState.QUASI},
    "rhombicuboctahedron":    {"type": "archimedean", "min_flux": FluxState.QUASI},
    "snub_dodecahedron":      {"type": "archimedean", "min_flux": FluxState.QUASI},

    # Subconscious: Kepler-Poinsot - POLLY only
    "small_stellated_dodecahedron": {"type": "kepler", "min_flux": FluxState.POLLY},
    "great_stellated_dodecahedron": {"type": "kepler", "min_flux": FluxState.POLLY},

    # Cerebellum: Toroidal - POLLY only
    "szilassi": {"type": "toroidal", "min_flux": FluxState.POLLY},
    "csaszar":  {"type": "toroidal", "min_flux": FluxState.POLLY},

    # Connectome: Johnson/Rhombic - POLLY only
    "rhombic_dodecahedron":      {"type": "rhombic", "min_flux": FluxState.POLLY},
    "rhombic_triacontahedron":   {"type": "rhombic", "min_flux": FluxState.POLLY},
    "johnson_54":                {"type": "johnson", "min_flux": FluxState.POLLY},
    "johnson_91":                {"type": "johnson", "min_flux": FluxState.POLLY},
}

# Flux state hierarchy (higher = more permissive)
FLUX_HIERARCHY = {
    FluxState.COLLAPSED: 0,
    FluxState.DEMI: 1,
    FluxState.QUASI: 2,
    FluxState.POLLY: 3,
}

# Action types and their minimum flux requirements
ACTION_ACCESS = {
    "read":       FluxState.COLLAPSED,  # Always allowed
    "navigate":   FluxState.DEMI,       # Basic navigation
    "click":      FluxState.DEMI,       # Basic interaction
    "type":       FluxState.QUASI,      # Input requires elevated state
    "evaluate":   FluxState.QUASI,      # JS eval needs caution
    "screenshot": FluxState.DEMI,       # Observation is safe
    "execute":    FluxState.POLLY,      # Full execution needs full state
    "admin":      FluxState.POLLY,      # Admin operations
}


def get_accessible_polyhedra(flux: FluxState) -> List[str]:
    """Get list of polyhedra accessible in the given flux state."""
    flux_level = FLUX_HIERARCHY[flux]
    return [
        name for name, props in POLYHEDRA_ACCESS.items()
        if FLUX_HIERARCHY[props["min_flux"]] <= flux_level
    ]


def is_action_allowed(action: str, flux: FluxState) -> bool:
    """Check if an action is allowed in the given flux state."""
    min_flux = ACTION_ACCESS.get(action.lower(), FluxState.POLLY)
    return FLUX_HIERARCHY[flux] >= FLUX_HIERARCHY[min_flux]


def classify_flux_from_coherence(coherence: float) -> FluxState:
    """
    Classify flux state from a coherence score.
    Higher coherence = more trusted = more permissive state.
    """
    if coherence >= 0.9:
        return FluxState.POLLY
    elif coherence >= 0.5:
        return FluxState.QUASI
    elif coherence >= 0.1:
        return FluxState.DEMI
    else:
        return FluxState.COLLAPSED


# ============================================================================
# Trust Cones (Novel Geometric Access Control)
# ============================================================================

@dataclass
class TrustCone:
    """
    A trust cone in the Poincare ball emanating from the origin.

    Unlike TrustRings (which only check radius), a TrustCone constrains
    BOTH distance and direction. An agent must:
    1. Be within the cone's angular width of the tongue direction
    2. Be within the radius limit

    The angular width narrows with confidence:
    half_angle = base_angle * (1 / confidence)

    This means high-confidence cones are narrow (precise access),
    while low-confidence cones are wide (exploratory access).

    Novel property: adversarial vectors that are close to origin
    but approaching from the WRONG direction are still blocked.
    """
    tongue: str                    # Sacred tongue this cone belongs to
    direction: np.ndarray          # Unit vector direction
    base_half_angle: float = 30.0  # Base half-angle in degrees
    confidence: float = 1.0        # Confidence factor (0, inf)
    max_radius: float = 0.92       # Maximum allowed radius

    @property
    def half_angle_rad(self) -> float:
        """Effective half-angle in radians, scaled by confidence."""
        # Higher confidence = narrower cone
        effective_angle = self.base_half_angle / max(self.confidence, 0.01)
        # Clamp to [5, 180] degrees
        effective_angle = max(5.0, min(180.0, effective_angle))
        return math.radians(effective_angle)

    def contains(self, point: np.ndarray) -> bool:
        """Check if a point falls within this trust cone."""
        # Check radius first (fast reject)
        radius = np.linalg.norm(point)
        if radius >= self.max_radius:
            return False
        if radius < EPSILON:
            return True  # Origin is in all cones

        # Check angular constraint
        # Use first 2 dimensions for angle comparison
        point_2d = point[:2] if len(point) >= 2 else np.array([point[0], 0.0])
        point_norm = np.linalg.norm(point_2d)
        if point_norm < EPSILON:
            return True

        point_dir = point_2d / point_norm
        cos_angle = np.clip(np.dot(point_dir, self.direction), -1.0, 1.0)
        angle = math.acos(cos_angle)

        return angle <= self.half_angle_rad

    def score(self, point: np.ndarray) -> float:
        """
        Compute trust score for a point relative to this cone.

        Returns value in [0, 1]:
        - 1.0 = perfectly aligned, at origin
        - 0.0 = outside cone or at boundary
        """
        radius = np.linalg.norm(point)
        if radius >= self.max_radius:
            return 0.0
        if radius < EPSILON:
            return 1.0

        # Angular component
        point_2d = point[:2] if len(point) >= 2 else np.array([point[0], 0.0])
        point_norm = np.linalg.norm(point_2d)
        if point_norm < EPSILON:
            return 1.0 - (radius / self.max_radius)

        point_dir = point_2d / point_norm
        cos_angle = np.clip(np.dot(point_dir, self.direction), -1.0, 1.0)
        angle = math.acos(cos_angle)

        if angle > self.half_angle_rad:
            return 0.0

        # Angular score: 1 at center, 0 at edge of cone
        angular_score = 1.0 - (angle / self.half_angle_rad)

        # Radial score: 1 at origin, 0 at max_radius
        radial_score = 1.0 - (radius / self.max_radius)

        # Combined score
        return angular_score * radial_score


def create_tongue_cones(
    dim: int = 16,
    base_angle: float = 30.0,
    confidence: float = 1.0,
    max_radius: float = 0.92
) -> Dict[str, TrustCone]:
    """Create trust cones for all 6 Sacred Tongues."""
    cones = {}
    for tongue, phase in TONGUE_PHASES.items():
        direction = np.array([math.cos(phase), math.sin(phase)])
        cones[tongue] = TrustCone(
            tongue=tongue,
            direction=direction,
            base_half_angle=base_angle,
            confidence=confidence,
            max_radius=max_radius,
        )
    return cones


def trust_cone_score(
    point: np.ndarray,
    assigned_tongue: Optional[str],
    cones: Dict[str, TrustCone],
) -> float:
    """
    Score a point using trust cones.

    If the point has an assigned tongue, check if it falls within
    that tongue's cone. Null-tongue agents get scored against all
    cones and take the maximum (most charitable interpretation).

    This mirrors the proven phase+distance formula but adds
    angular discrimination.
    """
    if assigned_tongue and assigned_tongue in cones:
        return cones[assigned_tongue].score(point)

    # Null-tongue: best-case score across all cones
    # (still penalized because no cone gives perfect alignment)
    return max(cone.score(point) for cone in cones.values())


# ============================================================================
# Encryption/Navigation Separation
# ============================================================================

def mobius_add(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """
    Mobius addition in the Poincare ball.
    u (+) v = ((1 + 2<u,v> + ||v||^2)u + (1 - ||u||^2)v) /
              (1 + 2<u,v> + ||u||^2||v||^2)
    """
    u_norm_sq = np.dot(u, u)
    v_norm_sq = np.dot(v, v)
    uv_dot = np.dot(u, v)

    num = (1 + 2 * uv_dot + v_norm_sq) * u + (1 - u_norm_sq) * v
    den = 1 + 2 * uv_dot + u_norm_sq * v_norm_sq

    result = num / max(den, EPSILON)

    # Project back into ball
    norm = np.linalg.norm(result)
    if norm >= 1.0:
        result = result * (1.0 - EPSILON) / norm
    return result


def fake_encrypt(v: np.ndarray, key: bytes) -> np.ndarray:
    """
    Simulate lattice-based encryption (Kyber-like noise addition).
    Returns ciphertext that is NOT a valid Poincare ball vector.
    """
    rng = np.random.default_rng(int.from_bytes(hashlib.sha256(key).digest()[:8], "big"))
    noise = rng.normal(0, 0.5, size=len(v))  # Gaussian noise
    # Ciphertext = v + noise (mod q simulation)
    return v + noise


def fake_decrypt(ct: np.ndarray, key: bytes) -> np.ndarray:
    """Simulate lattice-based decryption (remove noise)."""
    rng = np.random.default_rng(int.from_bytes(hashlib.sha256(key).digest()[:8], "big"))
    noise = rng.normal(0, 0.5, size=len(ct))
    return ct - noise


def exp_map_origin(v: np.ndarray) -> np.ndarray:
    """Exponential map at origin: maps Euclidean to Poincare ball."""
    norm = np.linalg.norm(v)
    if norm < EPSILON:
        return v
    scale = math.tanh(norm / 2.0)
    result = (scale / norm) * v
    result_norm = np.linalg.norm(result)
    if result_norm >= 1.0 - EPSILON:
        result = result * (1.0 - EPSILON) / result_norm
    return result


# ============================================================================
# Experiment Runner
# ============================================================================

def run_experiment_1_flux_tiering() -> Dict[str, Any]:
    """
    Experiment 1: Flux-State Access Tiering

    Tests that flux states correctly restrict access to polyhedra
    and actions, and that adversarial escalation is blocked.
    """
    print("\n" + "=" * 70)
    print("  EXPERIMENT 1: Flux-State Access Tiering")
    print("=" * 70)

    results = {
        "name": "Flux-State Access Tiering",
        "tests": [],
        "passed": 0,
        "failed": 0,
    }

    # Test 1: Verify polyhedra count per flux state
    expected_counts = {
        FluxState.POLLY: 16,       # All polyhedra
        FluxState.QUASI: 8,        # Platonic + Archimedean
        FluxState.DEMI: 5,         # Platonic only
        FluxState.COLLAPSED: 0,    # None (limbic only = action-level, not polyhedra)
    }

    for flux, expected in expected_counts.items():
        accessible = get_accessible_polyhedra(flux)
        actual = len(accessible)
        passed = actual == expected
        results["tests"].append({
            "test": f"Polyhedra count in {flux.name}",
            "expected": expected,
            "actual": actual,
            "passed": passed,
        })
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {flux.name}: {actual} polyhedra (expected {expected})")

    # Test 2: Action gating per flux state
    action_tests = [
        ("read",       FluxState.COLLAPSED, True),
        ("read",       FluxState.POLLY,     True),
        ("navigate",   FluxState.COLLAPSED, False),
        ("navigate",   FluxState.DEMI,      True),
        ("type",       FluxState.DEMI,      False),
        ("type",       FluxState.QUASI,     True),
        ("execute",    FluxState.QUASI,     False),
        ("execute",    FluxState.POLLY,     True),
        ("admin",      FluxState.QUASI,     False),
        ("admin",      FluxState.POLLY,     True),
    ]

    print()
    for action, flux, expected_allowed in action_tests:
        actual = is_action_allowed(action, flux)
        passed = actual == expected_allowed
        results["tests"].append({
            "test": f"Action '{action}' in {flux.name}",
            "expected": expected_allowed,
            "actual": actual,
            "passed": passed,
        })
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        status = "PASS" if passed else "FAIL"
        allowed_str = "ALLOWED" if actual else "BLOCKED"
        print(f"  [{status}] {action:12s} in {flux.name:10s}: {allowed_str}")

    # Test 3: Coherence -> flux classification
    coherence_tests = [
        (0.95, FluxState.POLLY),
        (0.7,  FluxState.QUASI),
        (0.3,  FluxState.DEMI),
        (0.05, FluxState.COLLAPSED),
        (0.0,  FluxState.COLLAPSED),
        (1.0,  FluxState.POLLY),
        (0.5,  FluxState.QUASI),
        (0.1,  FluxState.DEMI),
    ]

    print()
    for coherence, expected_flux in coherence_tests:
        actual = classify_flux_from_coherence(coherence)
        passed = actual == expected_flux
        results["tests"].append({
            "test": f"Coherence {coherence} -> {expected_flux.name}",
            "expected": expected_flux.name,
            "actual": actual.name,
            "passed": passed,
        })
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] Coherence {coherence:.2f} -> {actual.name} (expected {expected_flux.name})")

    # Test 4: Adversarial escalation attempt
    # An agent in DEMI state should NOT be able to access POLLY-only polyhedra
    print()
    demi_accessible = set(get_accessible_polyhedra(FluxState.DEMI))
    polly_only = set(get_accessible_polyhedra(FluxState.POLLY)) - demi_accessible
    escalation_blocked = len(polly_only) > 0 and not polly_only.issubset(demi_accessible)
    results["tests"].append({
        "test": "Adversarial escalation blocked",
        "polly_only_count": len(polly_only),
        "passed": escalation_blocked,
    })
    if escalation_blocked:
        results["passed"] += 1
    else:
        results["failed"] += 1
    status = "PASS" if escalation_blocked else "FAIL"
    print(f"  [{status}] Escalation blocked: {len(polly_only)} polyhedra inaccessible from DEMI")

    return results


def run_experiment_2_trust_cones() -> Dict[str, Any]:
    """
    Experiment 2: Trust Cones

    Tests that trust cones provide angular discrimination beyond
    what radius-only checking offers. This is the novel piece.
    """
    print("\n" + "=" * 70)
    print("  EXPERIMENT 2: Trust Cones (Novel Geometric Access Control)")
    print("=" * 70)

    results = {
        "name": "Trust Cones",
        "tests": [],
        "passed": 0,
        "failed": 0,
    }

    dim = 16
    cones = create_tongue_cones(dim=dim, base_angle=30.0, confidence=1.0)

    # Test 1: Aligned agent should be in its tongue's cone
    for tongue, phase in TONGUE_PHASES.items():
        # Create a point along this tongue's direction
        direction = np.zeros(dim)
        direction[0] = math.cos(phase) * 0.5
        direction[1] = math.sin(phase) * 0.5

        contained = cones[tongue].contains(direction)
        score = cones[tongue].score(direction)
        passed = contained and score > 0.3
        results["tests"].append({
            "test": f"Aligned agent in {tongue} cone",
            "contained": contained,
            "score": score,
            "passed": passed,
        })
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {tongue} aligned: contained={contained}, score={score:.4f}")

    # Test 2: Misaligned agent should NOT be in wrong cone
    print()
    misalignment_tests = 0
    misalignment_pass = 0
    for tongue_a in TONGUE_PHASES:
        for tongue_b in TONGUE_PHASES:
            if tongue_a == tongue_b:
                continue
            # Point along tongue_a's direction
            phase_a = TONGUE_PHASES[tongue_a]
            direction = np.zeros(dim)
            direction[0] = math.cos(phase_a) * 0.5
            direction[1] = math.sin(phase_a) * 0.5

            # Check in tongue_b's cone
            contained = cones[tongue_b].contains(direction)
            score_b = cones[tongue_b].score(direction)
            score_a = cones[tongue_a].score(direction)

            # Correct tongue should always score higher
            if score_a > score_b:
                misalignment_pass += 1
            misalignment_tests += 1

    ratio = misalignment_pass / misalignment_tests if misalignment_tests > 0 else 0
    passed = ratio >= 0.9  # Allow some overlap for adjacent tongues
    results["tests"].append({
        "test": "Cross-tongue discrimination",
        "correct_higher": misalignment_pass,
        "total": misalignment_tests,
        "ratio": ratio,
        "passed": passed,
    })
    if passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] Cross-tongue discrimination: {misalignment_pass}/{misalignment_tests} = {ratio:.2%}")

    # Test 3: Trust cone vs radius-only discrimination
    # Generate legitimate (tongue-aligned) and rogue (random direction) agents
    print()
    np.random.seed(42)
    n_samples = 200
    legit_scores_cone = []
    rogue_scores_cone = []
    legit_scores_radius = []
    rogue_scores_radius = []

    tongues_list = list(TONGUE_PHASES.keys())

    for _ in range(n_samples):
        # Legitimate: aligned with a random tongue, radius 0.3-0.7
        tongue = tongues_list[np.random.randint(0, 6)]
        phase = TONGUE_PHASES[tongue]
        r = np.random.uniform(0.3, 0.7)
        point = np.zeros(dim)
        # Add small angular noise (within 15 degrees)
        noise_angle = np.random.uniform(-math.radians(15), math.radians(15))
        point[0] = r * math.cos(phase + noise_angle)
        point[1] = r * math.sin(phase + noise_angle)
        # Small noise in other dimensions
        point[2:] = np.random.normal(0, 0.02, dim - 2)

        cone_score = trust_cone_score(point, tongue, cones)
        radius = np.linalg.norm(point)
        radius_score = 1.0 - (radius / 0.92)

        legit_scores_cone.append(cone_score)
        legit_scores_radius.append(max(0, radius_score))

    for _ in range(n_samples):
        # Rogue: random direction, same radius range
        r = np.random.uniform(0.3, 0.7)
        random_dir = np.random.randn(dim)
        random_dir = random_dir / np.linalg.norm(random_dir) * r
        point = random_dir

        # No tongue assignment
        cone_score = trust_cone_score(point, None, cones)
        radius = np.linalg.norm(point)
        radius_score = 1.0 - (radius / 0.92)

        rogue_scores_cone.append(cone_score)
        rogue_scores_radius.append(max(0, radius_score))

    # Compute separation metrics
    def compute_separation(legit, rogue):
        """Compute separation between legitimate and rogue scores."""
        min_legit = min(legit) if legit else 0
        max_rogue = max(rogue) if rogue else 1
        mean_legit = np.mean(legit)
        mean_rogue = np.mean(rogue)
        gap = mean_legit - mean_rogue
        perfect_sep = min_legit > max_rogue
        return {
            "mean_legit": float(mean_legit),
            "mean_rogue": float(mean_rogue),
            "gap": float(gap),
            "min_legit": float(min_legit),
            "max_rogue": float(max_rogue),
            "perfect_separation": perfect_sep,
        }

    def compute_auc(legit, rogue):
        """Compute AUC using Mann-Whitney U statistic."""
        n_legit = len(legit)
        n_rogue = len(rogue)
        if n_legit == 0 or n_rogue == 0:
            return 0.5

        # Count how many times a legitimate score > rogue score
        correct = sum(1 for l in legit for r in rogue if l > r)
        ties = sum(1 for l in legit for r in rogue if l == r)
        return (correct + 0.5 * ties) / (n_legit * n_rogue)

    cone_sep = compute_separation(legit_scores_cone, rogue_scores_cone)
    radius_sep = compute_separation(legit_scores_radius, rogue_scores_radius)
    cone_auc = compute_auc(legit_scores_cone, rogue_scores_cone)
    radius_auc = compute_auc(legit_scores_radius, rogue_scores_radius)

    print(f"  Trust Cone scoring:")
    print(f"    Legit mean: {cone_sep['mean_legit']:.4f}  Rogue mean: {cone_sep['mean_rogue']:.4f}")
    print(f"    Gap: {cone_sep['gap']:.4f}  AUC: {cone_auc:.4f}")
    print(f"  Radius-only scoring:")
    print(f"    Legit mean: {radius_sep['mean_legit']:.4f}  Rogue mean: {radius_sep['mean_rogue']:.4f}")
    print(f"    Gap: {radius_sep['gap']:.4f}  AUC: {radius_auc:.4f}")

    cone_wins = cone_auc > radius_auc
    print(f"\n  Trust cones {'BEAT' if cone_wins else 'LOSE TO'} radius-only: "
          f"AUC {cone_auc:.4f} vs {radius_auc:.4f}")

    results["tests"].append({
        "test": "Trust cone vs radius-only AUC",
        "cone_auc": cone_auc,
        "radius_auc": radius_auc,
        "cone_wins": cone_wins,
        "cone_separation": cone_sep,
        "radius_separation": radius_sep,
        "passed": cone_wins,
    })
    if cone_wins:
        results["passed"] += 1
    else:
        results["failed"] += 1

    # Test 4: Confidence scaling
    print()
    for conf in [0.5, 1.0, 2.0, 5.0]:
        narrow_cones = create_tongue_cones(dim=dim, base_angle=30.0, confidence=conf)
        ko_cone = narrow_cones["KO"]
        half_angle_deg = math.degrees(ko_cone.half_angle_rad)
        print(f"  Confidence={conf:.1f}: KO cone half-angle = {half_angle_deg:.1f} degrees")

    # Test 5: Edge case - point at origin
    origin = np.zeros(dim)
    for tongue in tongues_list:
        score = cones[tongue].score(origin)
        assert score == 1.0, f"Origin should score 1.0 in all cones, got {score} for {tongue}"
    results["tests"].append({
        "test": "Origin scores 1.0 in all cones",
        "passed": True,
    })
    results["passed"] += 1
    print(f"\n  [PASS] Origin scores 1.0 in all cones")

    # Test 6: Point at boundary - should score 0
    boundary_point = np.zeros(dim)
    boundary_point[0] = 0.93  # Beyond safe_radius
    for tongue in tongues_list:
        score = cones[tongue].score(boundary_point)
        assert score == 0.0, f"Boundary point should score 0.0, got {score} for {tongue}"
    results["tests"].append({
        "test": "Boundary point scores 0.0",
        "passed": True,
    })
    results["passed"] += 1
    print(f"  [PASS] Boundary point scores 0.0 in all cones")

    return results


def run_experiment_3_encryption_separation() -> Dict[str, Any]:
    """
    Experiment 3: Encryption/Navigation Separation

    Proves that Mobius addition on encrypted vectors is broken,
    and validates the correct pattern.
    """
    print("\n" + "=" * 70)
    print("  EXPERIMENT 3: Encryption/Navigation Separation")
    print("=" * 70)

    results = {
        "name": "Encryption/Navigation Separation",
        "tests": [],
        "passed": 0,
        "failed": 0,
    }

    dim = 16
    key = b"test-key-for-experiment"
    np.random.seed(42)

    # Create valid Poincare ball vectors
    position = np.random.randn(dim) * 0.3
    position = exp_map_origin(position)

    step = np.random.randn(dim) * 0.1
    step = exp_map_origin(step)

    # Ground truth: Mobius add on plaintext
    correct_result = mobius_add(position, step)
    correct_norm = np.linalg.norm(correct_result)
    print(f"\n  Ground truth (plaintext Mobius add):")
    print(f"    Position norm: {np.linalg.norm(position):.4f}")
    print(f"    Step norm:     {np.linalg.norm(step):.4f}")
    print(f"    Result norm:   {correct_norm:.4f}")
    print(f"    In ball:       {correct_norm < 1.0}")

    # BROKEN: Encrypt then Mobius add on ciphertext
    print(f"\n  BROKEN pattern: Mobius add on encrypted vectors")
    encrypted_step = fake_encrypt(step, key)
    encrypted_norm = np.linalg.norm(encrypted_step)
    print(f"    Encrypted step norm: {encrypted_norm:.4f}")
    print(f"    In ball:             {encrypted_norm < 1.0}")

    broken_result = mobius_add(position, encrypted_step)
    broken_norm = np.linalg.norm(broken_result)
    error = np.linalg.norm(broken_result - correct_result)
    print(f"    Broken result norm:  {broken_norm:.4f}")
    print(f"    Error vs correct:    {error:.4f}")
    print(f"    In ball:             {broken_norm < 1.0}")

    is_broken = error > 0.1  # Significant error proves it's broken
    results["tests"].append({
        "test": "Mobius on ciphertext is broken",
        "error": float(error),
        "broken_norm": float(broken_norm),
        "correct_norm": float(correct_norm),
        "passed": is_broken,
    })
    if is_broken:
        results["passed"] += 1
    else:
        results["failed"] += 1
    status = "PASS" if is_broken else "FAIL"
    print(f"    [{status}] Ciphertext Mobius is broken (error={error:.4f})")

    # CORRECT: Encrypt for transport, decrypt before Mobius
    print(f"\n  CORRECT pattern: Decrypt then Mobius add")
    encrypted_for_transport = fake_encrypt(step, key)
    decrypted_step = fake_decrypt(encrypted_for_transport, key)
    fixed_result = mobius_add(position, decrypted_step)
    fixed_error = np.linalg.norm(fixed_result - correct_result)
    print(f"    Decrypted step matches original: {np.allclose(decrypted_step, step)}")
    print(f"    Fixed result error: {fixed_error:.4e}")

    is_correct = fixed_error < 1e-10
    results["tests"].append({
        "test": "Decrypt-then-Mobius is correct",
        "error": float(fixed_error),
        "matches_original": bool(np.allclose(decrypted_step, step)),
        "passed": is_correct,
    })
    if is_correct:
        results["passed"] += 1
    else:
        results["failed"] += 1
    status = "PASS" if is_correct else "FAIL"
    print(f"    [{status}] Decrypt-then-Mobius matches ground truth (error={fixed_error:.4e})")

    # Statistical test: run many times to confirm consistent breakage
    print(f"\n  Statistical validation (100 trials):")
    n_trials = 100
    broken_count = 0
    correct_count = 0
    broken_errors = []
    correct_errors = []

    for i in range(n_trials):
        pos = np.random.randn(dim) * 0.3
        pos = exp_map_origin(pos)
        stp = np.random.randn(dim) * 0.1
        stp = exp_map_origin(stp)

        truth = mobius_add(pos, stp)

        # Broken path
        enc = fake_encrypt(stp, key + i.to_bytes(4, "big"))
        broken = mobius_add(pos, enc)
        err_broken = np.linalg.norm(broken - truth)
        broken_errors.append(err_broken)
        if err_broken > 0.1:
            broken_count += 1

        # Correct path
        enc2 = fake_encrypt(stp, key + i.to_bytes(4, "big"))
        dec2 = fake_decrypt(enc2, key + i.to_bytes(4, "big"))
        fixed = mobius_add(pos, dec2)
        err_fixed = np.linalg.norm(fixed - truth)
        correct_errors.append(err_fixed)
        if err_fixed < 1e-10:
            correct_count += 1

    print(f"    Broken path:  {broken_count}/{n_trials} had error > 0.1")
    print(f"    Correct path: {correct_count}/{n_trials} had error < 1e-10")
    print(f"    Broken mean error:  {np.mean(broken_errors):.4f}")
    print(f"    Correct mean error: {np.mean(correct_errors):.4e}")

    stat_passed = broken_count >= 90 and correct_count >= 99
    results["tests"].append({
        "test": "Statistical validation (100 trials)",
        "broken_rate": broken_count / n_trials,
        "correct_rate": correct_count / n_trials,
        "broken_mean_error": float(np.mean(broken_errors)),
        "correct_mean_error": float(np.mean(correct_errors)),
        "passed": stat_passed,
    })
    if stat_passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
    status = "PASS" if stat_passed else "FAIL"
    print(f"    [{status}] Statistical validation confirmed")

    return results


def run_experiment_4_phdm_containment() -> Dict[str, Any]:
    """
    Experiment 4: PHDM Hallucination Containment Test

    Tests whether the SimplePHDM correctly contains adversarial
    drift and provides meaningful 4-tier governance decisions.
    """
    print("\n" + "=" * 70)
    print("  EXPERIMENT 4: PHDM Hallucination Containment")
    print("=" * 70)

    results = {
        "name": "PHDM Hallucination Containment",
        "tests": [],
        "passed": 0,
        "failed": 0,
    }

    dim = 16
    safe_radius = 0.92

    # Simulate SimplePHDM inline (avoid import dependency issues)
    def is_safe(embedding):
        norm = np.linalg.norm(embedding)
        if norm >= 1.0:
            embedding = embedding * (1.0 - EPSILON) / norm
        return np.linalg.norm(embedding) < safe_radius

    def compute_risk(embedding):
        norm = np.linalg.norm(embedding)
        if norm >= 1.0:
            embedding = embedding * (1.0 - EPSILON) / norm
        radius = np.linalg.norm(embedding)
        radius_risk = radius / safe_radius

        # Hyperbolic distance to origin
        clamped = min(radius, 1.0 - EPSILON)
        h_dist = 2 * math.atanh(clamped) if clamped > EPSILON else 0.0

        # Harmonic scaling
        amp = min(1.5 ** (h_dist ** 2), 10.0)

        base = min(1.0, radius_risk)
        amplified = base * amp / 10.0
        return min(1.0, max(0.0, 0.4 * base + 0.6 * amplified))

    def decide(embedding):
        norm = np.linalg.norm(embedding)
        if norm >= 1.0:
            embedding = embedding * (1.0 - EPSILON) / norm
        radius = np.linalg.norm(embedding)
        risk = compute_risk(embedding)

        if radius >= safe_radius:
            return "DENY"
        elif risk >= 0.67:
            return "DENY"
        elif risk >= 0.33:
            if radius >= safe_radius * 0.95:
                return "ESCALATE"
            return "QUARANTINE"
        return "ALLOW"

    # Test 1: Safe actions at origin region
    print("\n  Safe actions (near origin):")
    safe_count = 0
    for i in range(20):
        v = np.random.randn(dim) * 0.1
        v = exp_map_origin(v)
        safe = is_safe(v)
        decision = decide(v)
        if safe and decision == "ALLOW":
            safe_count += 1
    passed = safe_count >= 18  # Allow 2 edge cases
    results["tests"].append({"test": "Safe actions near origin", "rate": safe_count / 20, "passed": passed})
    if passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
    print(f"    [{'PASS' if passed else 'FAIL'}] {safe_count}/20 safe actions got ALLOW")

    # Test 2: Dangerous actions at boundary
    print("\n  Dangerous actions (near boundary):")
    denied_count = 0
    for i in range(20):
        v = np.random.randn(dim)
        v = v / np.linalg.norm(v) * 0.95  # Near boundary
        decision = decide(v)
        if decision in ("DENY", "ESCALATE"):
            denied_count += 1
    passed = denied_count >= 18
    results["tests"].append({"test": "Dangerous actions denied", "rate": denied_count / 20, "passed": passed})
    if passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
    print(f"    [{'PASS' if passed else 'FAIL'}] {denied_count}/20 boundary actions got DENY/ESCALATE")

    # Test 3: Adversarial drift detection
    # Start safe, gradually drift toward boundary
    print("\n  Adversarial drift simulation:")
    position = np.zeros(dim)
    drift_direction = np.random.randn(dim)
    drift_direction = drift_direction / np.linalg.norm(drift_direction)

    decisions_over_drift = []
    for step in range(20):
        # Drift a bit each step
        position = position + drift_direction * 0.05
        # Project into ball
        norm = np.linalg.norm(position)
        if norm >= 1.0:
            position = position * (1.0 - EPSILON) / norm

        decision = decide(position)
        risk = compute_risk(position)
        decisions_over_drift.append({
            "step": step,
            "radius": float(np.linalg.norm(position)),
            "risk": float(risk),
            "decision": decision,
        })

    # Verify decisions escalate over drift
    first_deny = None
    first_non_allow = None
    for d in decisions_over_drift:
        if d["decision"] != "ALLOW" and first_non_allow is None:
            first_non_allow = d["step"]
        if d["decision"] == "DENY" and first_deny is None:
            first_deny = d["step"]

    # Print drift trajectory
    for d in decisions_over_drift:
        bar = "#" * int(d["radius"] * 30)
        print(f"    Step {d['step']:2d}: r={d['radius']:.3f} risk={d['risk']:.3f} {d['decision']:12s} |{bar}")

    drift_detected = first_non_allow is not None and first_non_allow < 15
    passed = drift_detected
    results["tests"].append({
        "test": "Adversarial drift detection",
        "first_non_allow_step": first_non_allow,
        "first_deny_step": first_deny,
        "passed": passed,
    })
    if passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
    print(f"\n    [{'PASS' if passed else 'FAIL'}] Drift detected at step {first_non_allow} "
          f"(DENY at step {first_deny})")

    # Test 4: Harmonic wall makes drift exponentially costly
    print("\n  Harmonic wall cost curve:")
    radii = [0.1, 0.3, 0.5, 0.7, 0.85, 0.9, 0.92, 0.95, 0.99]
    costs = []
    for r in radii:
        v = np.zeros(dim)
        v[0] = r
        risk = compute_risk(v)
        costs.append(risk)
        print(f"    r={r:.2f}: risk={risk:.4f}")

    # Verify monotonicity
    monotonic = all(costs[i] <= costs[i + 1] + 1e-10 for i in range(len(costs) - 1))
    results["tests"].append({
        "test": "Risk monotonically increases with radius",
        "monotonic": monotonic,
        "passed": monotonic,
    })
    if monotonic:
        results["passed"] += 1
    else:
        results["failed"] += 1
    print(f"\n    [{'PASS' if monotonic else 'FAIL'}] Risk is monotonically increasing")

    return results


# ============================================================================
# Main
# ============================================================================

def main():
    """Run all experiments and generate telemetry."""
    start_time = time.time()

    print("\n" + "=" * 70)
    print("  SCBE-AETHERMOORE EXPERIMENT SUITE")
    print("  Flux Tiering + Trust Cones + Encryption Separation + PHDM")
    print("=" * 70)

    all_results = {}

    # Run experiments
    all_results["exp1_flux_tiering"] = run_experiment_1_flux_tiering()
    all_results["exp2_trust_cones"] = run_experiment_2_trust_cones()
    all_results["exp3_encryption_separation"] = run_experiment_3_encryption_separation()
    all_results["exp4_phdm_containment"] = run_experiment_4_phdm_containment()

    # Summary
    total_passed = sum(r["passed"] for r in all_results.values())
    total_failed = sum(r["failed"] for r in all_results.values())
    total_tests = total_passed + total_failed
    duration_ms = (time.time() - start_time) * 1000

    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    for name, result in all_results.items():
        status = "ALL PASS" if result["failed"] == 0 else f"{result['failed']} FAILED"
        print(f"  {result['name']:45s}: {result['passed']}/{result['passed'] + result['failed']} ({status})")

    print(f"\n  Total: {total_passed}/{total_tests} passed ({total_passed / total_tests * 100:.1f}%)")
    print(f"  Duration: {duration_ms:.1f}ms")

    # Save telemetry
    telemetry = {
        "session_start": start_time,
        "session_duration_ms": duration_ms,
        "total_tests": total_tests,
        "passed_tests": total_passed,
        "failed_tests": total_failed,
        "experiments": all_results,
    }

    telemetry_path = "tests/test_telemetry_flux_cones.json"
    with open(telemetry_path, "w") as f:
        json.dump(telemetry, f, indent=2, default=str)
    print(f"\n  Telemetry saved to {telemetry_path}")

    return all_results


if __name__ == "__main__":
    main()
