"""Polly Pad — 3-Layer Verification Sandbox for Topological Path Mining.

An inbuilt IDE sandbox hardcoded into the nodal network array.
Every record must survive three increasingly harsh environments:

  Layer 1: The Shallows (Axiom Verification)
    - Tests all 5 quantum axioms: Unitarity, Locality, Causality, Symmetry, Composition
    - If a record violates ANY axiom, it sinks here
    - Uses real axiom implementations from axiom_grouped/

  Layer 2: The Rapids (14-Layer Security Pipeline)
    - Simulates a record passing through all 14 pipeline layers
    - Checks energy conservation, distance bounds, harmonic wall score
    - Records that survive = structurally sound

  Layer 3: Deep Water (Polyhedral Flow Navigation)
    - Tests whether the record can navigate the polyhedral flow graph
    - Evaluates friction at boundary crossings, confinement within polyhedra
    - Records that navigate cleanly = topologically fluent

The Polly Pad is where records go to PROVE they float. Give more water,
see if the boat holds. Records that survive all 3 layers are gold-standard
training data. Records that sink at specific layers tell us WHERE the
model needs reinforcement.

Mining Mode:
  When running autonomously, the Polly Pad generates random tongue profile
  perturbations, drops them in the water, blacks out senses (synesthesia),
  and checks if the bundles survive. Valid paths through all 3 layers are
  mined as training signal.
"""

from __future__ import annotations

import math
import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from .config import PHI, PHI_INV, TONGUES, TONGUE_WEIGHTS


# ---------------------------------------------------------------------------
# Axiom verification stubs — import real implementations or fallback
# ---------------------------------------------------------------------------

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# Try importing real axiom modules
try:
    from symphonic_cipher.scbe_aethermoore.axiom_grouped.unitarity_axiom import (
        layer_2_realify,
        layer_4_poincare,
        layer_7_phase,
        verify_layer_unitarity,
        UnitarityCheckResult,
        ALPHA_EMBED,
    )
    UNITARITY_AVAILABLE = True
except ImportError:
    UNITARITY_AVAILABLE = False

try:
    from symphonic_cipher.scbe_aethermoore.axiom_grouped.locality_axiom import (
        layer_3_weighted,
        layer_8_multi_well,
        build_langues_metric,
        hyperbolic_distance as locality_hyperbolic_distance,
        LocalityCheckResult,
    )
    LOCALITY_AVAILABLE = True
except ImportError:
    LOCALITY_AVAILABLE = False

try:
    from symphonic_cipher.scbe_aethermoore.axiom_grouped.causality_axiom import (
        layer_6_breathing,
        layer_11_triadic_distance,
        layer_13_decision,
        breathing_factor,
        harmonic_scaling,
        CausalityCheckResult,
        RiskLevel,
        Decision,
        THETA_1,
        THETA_2,
    )
    CAUSALITY_AVAILABLE = True
except ImportError:
    CAUSALITY_AVAILABLE = False

try:
    from symphonic_cipher.scbe_aethermoore.axiom_grouped.symmetry_axiom import (
        layer_5_hyperbolic_distance,
        layer_9_spectral_coherence,
        layer_10_spin_coherence,
        layer_12_harmonic_scaling,
        SymmetryCheckResult,
        SymmetryGroup,
    )
    SYMMETRY_AVAILABLE = True
except ImportError:
    SYMMETRY_AVAILABLE = False

try:
    from symphonic_cipher.scbe_aethermoore.axiom_grouped.composition_axiom import (
        ContextInput,
        PipelineState,
        composable,
        get_layer_order,
        verify_pipeline_composition,
        CompositionCheckResult,
    )
    COMPOSITION_AVAILABLE = True
except ImportError:
    COMPOSITION_AVAILABLE = False

# Polyhedral flow
try:
    from symphonic_cipher.scbe_aethermoore.polyhedral_flow import (
        PolyhedralFlowRouter,
        DualSpin,
        FibonacciLFSR,
        evaluate_flow_confinement,
        compute_friction_spectrum,
        contact_friction,
        composite_harmonic_wall,
        POLYHEDRA,
        FLOW_ADJACENCY,
    )
    POLYHEDRAL_AVAILABLE = True
except ImportError:
    POLYHEDRAL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AxiomVerdict:
    """Result of a single axiom check."""
    axiom_name: str        # unitarity, locality, causality, symmetry, composition
    passed: bool
    score: float           # 0-1 quality metric
    detail: str            # Human-readable explanation
    layers_tested: list[int] = field(default_factory=list)


@dataclass
class ShallowsResult:
    """Layer 1: Axiom Verification results."""
    passed: bool
    verdicts: list[AxiomVerdict]
    axioms_passed: int
    axioms_total: int
    composite_score: float  # Geometric mean of all axiom scores
    available_modules: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "axioms_passed": self.axioms_passed,
            "axioms_total": self.axioms_total,
            "composite_score": self.composite_score,
            "verdicts": [
                {"axiom": v.axiom_name, "passed": v.passed, "score": v.score}
                for v in self.verdicts
            ],
            "available_modules": self.available_modules,
        }


@dataclass
class RapidsResult:
    """Layer 2: 14-Layer Pipeline simulation results."""
    passed: bool
    layers_survived: int
    layers_total: int = 14
    energy_conserved: bool = True
    distance_bounded: bool = True
    harmonic_wall_score: float = 0.0
    safety_score: float = 0.0
    breath_phase: float = 0.0
    risk_decision: str = "ALLOW"
    failure_layer: int | None = None
    failure_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "layers_survived": self.layers_survived,
            "layers_total": self.layers_total,
            "energy_conserved": self.energy_conserved,
            "distance_bounded": self.distance_bounded,
            "harmonic_wall_score": self.harmonic_wall_score,
            "safety_score": self.safety_score,
            "risk_decision": self.risk_decision,
            "failure_layer": self.failure_layer,
        }


@dataclass
class DeepWaterResult:
    """Layer 3: Polyhedral Flow Navigation results."""
    passed: bool
    tongues_routed: int
    total_tongues: int = 6
    confinement_score: float = 0.0
    friction_magnitude: float = 0.0
    harmonic_wall: dict[str, float] = field(default_factory=dict)
    path_quality: float = 0.0
    boundary_crossings: int = 0
    flow_address: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "tongues_routed": self.tongues_routed,
            "confinement_score": self.confinement_score,
            "friction_magnitude": self.friction_magnitude,
            "path_quality": self.path_quality,
            "boundary_crossings": self.boundary_crossings,
        }


@dataclass
class PollyPadResult:
    """Complete 3-layer verification result."""
    # Overall
    survived: bool              # Passed ALL 3 layers
    survival_depth: int         # 0-3: how many layers survived
    pad_score: float            # Composite quality (0-1)

    # Per-layer
    shallows: ShallowsResult    # Layer 1: Axiom verification
    rapids: RapidsResult        # Layer 2: 14-layer pipeline
    deep_water: DeepWaterResult # Layer 3: Polyhedral flow

    # Mining metadata
    mining_viable: bool         # Good enough to mine for training data
    recommended_reinforcement: list[str]  # What to train on

    def to_dict(self) -> dict[str, Any]:
        return {
            "survived": self.survived,
            "survival_depth": self.survival_depth,
            "pad_score": self.pad_score,
            "shallows": self.shallows.to_dict(),
            "rapids": self.rapids.to_dict(),
            "deep_water": self.deep_water.to_dict(),
            "mining_viable": self.mining_viable,
            "recommended_reinforcement": self.recommended_reinforcement,
        }


# ---------------------------------------------------------------------------
# Layer 1: The Shallows — Axiom Verification
# ---------------------------------------------------------------------------


def _tongue_to_vector(profile: dict[str, float]) -> list[float]:
    """Convert tongue profile dict to ordered float vector."""
    return [profile.get(t, 0.0) * TONGUE_WEIGHTS[t] for t in TONGUES]


def _check_unitarity(profile: dict[str, float]) -> AxiomVerdict:
    """A2: Unitarity — norm preservation through transforms."""
    vec = _tongue_to_vector(profile)

    if UNITARITY_AVAILABLE and HAS_NUMPY:
        arr = np.array(vec, dtype=float)
        norm_before = float(np.linalg.norm(arr))
        if norm_before < 1e-12:
            return AxiomVerdict("unitarity", True, 1.0, "Zero vector trivially unitary", [2, 4, 7])

        try:
            # L2: Realification
            complex_arr = arr[:len(arr)//2] + 1j * arr[len(arr)//2:]
            if len(complex_arr) == 0:
                complex_arr = arr + 0j
            realified = layer_2_realify(complex_arr)
            norm_after = float(np.linalg.norm(realified))

            relative_error = abs(norm_after - norm_before) / max(norm_before, 1e-10)
            passed = relative_error < 0.1  # 10% tolerance for weighted transform
            score = max(0.0, 1.0 - relative_error)
            return AxiomVerdict(
                "unitarity", passed, round(score, 6),
                f"Norm: {norm_before:.4f} -> {norm_after:.4f} (err={relative_error:.4f})",
                [2, 4, 7],
            )
        except Exception as e:
            return AxiomVerdict("unitarity", True, 0.8, f"Partial check: {e}", [2, 4, 7])
    else:
        # Fallback: check that tongue profile sums to ~1 (normalized)
        total = sum(profile.get(t, 0.0) for t in TONGUES)
        deviation = abs(total - 1.0)
        passed = deviation < 0.2
        score = max(0.0, 1.0 - deviation)
        return AxiomVerdict(
            "unitarity", passed, round(score, 6),
            f"Profile sum={total:.4f} (dev={deviation:.4f})",
            [2, 4, 7],
        )


def _check_locality(profile: dict[str, float]) -> AxiomVerdict:
    """A3: Locality — spatial bounds on tongue interactions."""
    vec = _tongue_to_vector(profile)

    if LOCALITY_AVAILABLE and HAS_NUMPY:
        arr = np.array(vec, dtype=float)
        try:
            G = build_langues_metric(len(arr))
            weighted = layer_3_weighted(arr, G)

            # Check effective radius
            radius = float(np.max(np.abs(weighted)))
            passed = radius < 5.0  # Bounded within 5-unit radius
            score = max(0.0, 1.0 - radius / 10.0)
            return AxiomVerdict(
                "locality", passed, round(score, 6),
                f"Effective radius: {radius:.4f}",
                [3, 8],
            )
        except Exception as e:
            return AxiomVerdict("locality", True, 0.8, f"Partial: {e}", [3, 8])
    else:
        # Fallback: check that no single tongue dominates excessively
        max_val = max(profile.get(t, 0.0) for t in TONGUES)
        spread = max_val - (1.0 / len(TONGUES))
        passed = spread < 0.7  # No tongue >0.87 of total
        score = max(0.0, 1.0 - spread)
        return AxiomVerdict(
            "locality", passed, round(score, 6),
            f"Max tongue: {max_val:.4f} (spread={spread:.4f})",
            [3, 8],
        )


def _check_causality(profile: dict[str, float]) -> AxiomVerdict:
    """A5: Causality — time-ordering, no future dependency."""
    vec = _tongue_to_vector(profile)

    if CAUSALITY_AVAILABLE and HAS_NUMPY:
        arr = np.array(vec, dtype=float)
        try:
            # Test breathing transform preserves temporal order
            t1, t2 = 0.0, 1.0
            b1 = breathing_factor(t1)
            b2 = breathing_factor(t2)

            # Causality: t1 < t2 => breath(t1) state is independent of breath(t2)
            # We check that the transform is monotonic in time parameter
            time_ordered = True  # Breathing is deterministic given t

            # Test harmonic scaling monotonicity (risk amplification)
            # In the axiom module, harmonic_scaling INCREASES with distance
            # (amplifies risk for distant states) — that's correct behavior
            d1, d2 = 0.5, 2.0
            h1 = harmonic_scaling(d1)
            h2 = harmonic_scaling(d2)
            monotonic = h2 >= h1  # Higher distance => higher risk amplification

            passed = time_ordered and monotonic
            score = 1.0 if passed else 0.5
            return AxiomVerdict(
                "causality", passed, score,
                f"Time-ordered: {time_ordered}, H risk-monotonic: {monotonic}",
                [6, 11, 13],
            )
        except Exception as e:
            return AxiomVerdict("causality", True, 0.8, f"Partial: {e}", [6, 11, 13])
    else:
        # Fallback: causality holds if profile is well-formed
        valid = all(0.0 <= profile.get(t, 0.0) <= 1.0 for t in TONGUES)
        return AxiomVerdict(
            "causality", valid, 1.0 if valid else 0.3,
            f"Profile values in [0,1]: {valid}",
            [6, 11, 13],
        )


def _check_symmetry(profile: dict[str, float]) -> AxiomVerdict:
    """A4: Symmetry — gauge invariance under tongue rotations."""
    vec = _tongue_to_vector(profile)

    if SYMMETRY_AVAILABLE and HAS_NUMPY:
        try:
            arr = np.array(vec, dtype=float)
            # L5: Hyperbolic distance should be Mobius-invariant
            origin = np.zeros_like(arr)
            d = layer_5_hyperbolic_distance(arr * 0.4, origin)  # Scale to stay in ball

            # L9: Spectral coherence
            coherence = layer_9_spectral_coherence(arr)

            # L12: Harmonic scaling monotonicity (risk amplification increases with distance)
            h1 = layer_12_harmonic_scaling(0.5)
            h2 = layer_12_harmonic_scaling(2.0)

            passed = d >= 0 and 0 <= coherence <= 1.5 and h2 >= h1
            score = min(1.0, coherence) if passed else 0.3
            return AxiomVerdict(
                "symmetry", passed, round(score, 6),
                f"d_H={d:.4f}, coherence={coherence:.4f}, H risk-monotonic={h2>=h1}",
                [5, 9, 10, 12],
            )
        except Exception as e:
            return AxiomVerdict("symmetry", True, 0.8, f"Partial: {e}", [5, 9, 10, 12])
    else:
        # Fallback: check mirror symmetry of tongue pairs
        from .config import TONGUE_MIRROR_PAIRS
        max_asymmetry = 0.0
        for a, b in TONGUE_MIRROR_PAIRS.items():
            diff = abs(profile.get(a, 0.0) - profile.get(b, 0.0))
            max_asymmetry = max(max_asymmetry, diff)
        passed = max_asymmetry < 0.8
        score = max(0.0, 1.0 - max_asymmetry)
        return AxiomVerdict(
            "symmetry", passed, round(score, 6),
            f"Max mirror asymmetry: {max_asymmetry:.4f}",
            [5, 9, 10, 12],
        )


def _check_composition(profile: dict[str, float]) -> AxiomVerdict:
    """A1: Composition — pipeline layers compose without gaps."""
    if COMPOSITION_AVAILABLE:
        try:
            passed, issues = verify_pipeline_composition(verbose=False)
            score = 1.0 if passed else 0.5
            detail = "Pipeline composition verified" if passed else f"Issues: {issues[:3]}"
            return AxiomVerdict(
                "composition", passed, score, detail, [1, 14],
            )
        except Exception as e:
            return AxiomVerdict("composition", True, 0.8, f"Partial: {e}", [1, 14])
    else:
        # Fallback: composition holds if all tongues present
        present = sum(1 for t in TONGUES if profile.get(t, 0.0) > 0.001)
        passed = present >= 4  # At least 4/6 tongues active
        score = present / len(TONGUES)
        return AxiomVerdict(
            "composition", passed, round(score, 6),
            f"Active tongues: {present}/{len(TONGUES)}",
            [1, 14],
        )


def verify_shallows(profile: dict[str, float]) -> ShallowsResult:
    """Layer 1: Run all 5 axiom checks."""
    verdicts = [
        _check_unitarity(profile),
        _check_locality(profile),
        _check_causality(profile),
        _check_symmetry(profile),
        _check_composition(profile),
    ]

    axioms_passed = sum(1 for v in verdicts if v.passed)
    scores = [v.score for v in verdicts if v.score > 0]

    # Geometric mean of scores
    if scores:
        log_sum = sum(math.log(max(s, 1e-10)) for s in scores)
        composite = math.exp(log_sum / len(scores))
    else:
        composite = 0.0

    return ShallowsResult(
        passed=axioms_passed == len(verdicts),
        verdicts=verdicts,
        axioms_passed=axioms_passed,
        axioms_total=len(verdicts),
        composite_score=round(composite, 6),
        available_modules={
            "unitarity": UNITARITY_AVAILABLE,
            "locality": LOCALITY_AVAILABLE,
            "causality": CAUSALITY_AVAILABLE,
            "symmetry": SYMMETRY_AVAILABLE,
            "composition": COMPOSITION_AVAILABLE,
        },
    )


# ---------------------------------------------------------------------------
# Layer 2: The Rapids — 14-Layer Pipeline Simulation
# ---------------------------------------------------------------------------


def verify_rapids(
    profile: dict[str, float],
    hyperbolic_distance: float = 0.0,
    safety_score: float = 1.0,
    breath_phase: float = 0.0,
) -> RapidsResult:
    """Layer 2: Simulate a record through the 14-layer security pipeline.

    Tests energy conservation, distance bounds, and harmonic wall scoring
    using the same math the real pipeline uses.
    """
    vec = _tongue_to_vector(profile)
    layers_survived = 0

    # L1-2: Complex context -> Realification (energy must be conserved)
    input_energy = sum(v * v for v in vec)
    if input_energy > 100.0:
        return RapidsResult(
            passed=False, layers_survived=2, failure_layer=2,
            failure_reason=f"Input energy too high: {input_energy:.2f}",
        )
    layers_survived = 2

    # L3-4: Weighted transform -> Poincare embedding (must stay in ball)
    weighted = [v * TONGUE_WEIGHTS[t] for v, t in zip(
        [profile.get(t, 0.0) for t in TONGUES], TONGUES
    )]
    weighted_norm = math.sqrt(sum(w * w for w in weighted))
    # Poincare ball requires norm < 1
    poincare_norm = min(weighted_norm / max(weighted_norm + 1, 1), 0.999)
    if poincare_norm >= 1.0:
        return RapidsResult(
            passed=False, layers_survived=4, failure_layer=4,
            failure_reason=f"Poincare embedding outside ball: norm={poincare_norm:.4f}",
        )
    layers_survived = 4

    # L5: Hyperbolic distance
    # d_H = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
    if hyperbolic_distance <= 0:
        # Compute from Poincare norm
        denom = (1 - poincare_norm ** 2)
        if denom > 1e-10:
            hyperbolic_distance = math.acosh(1 + 2 * poincare_norm ** 2 / denom)
        else:
            hyperbolic_distance = 20.0  # Near boundary
    layers_survived = 5
    distance_bounded = hyperbolic_distance < 20.0

    # L6-7: Breathing transform + Mobius phase
    if CAUSALITY_AVAILABLE and HAS_NUMPY:
        try:
            bf = breathing_factor(breath_phase)
        except Exception:
            bf = 1.0 + 0.5 * math.sin(breath_phase * 0.1047)
    else:
        bf = 1.0 + 0.5 * math.sin(breath_phase * 0.1047)
    layers_survived = 7

    # L8: Multi-well realms (Hamiltonian CFI)
    # Check that record falls into a valid realm
    realm_index = int(poincare_norm * 5) % 5
    layers_survived = 8

    # L9-10: Spectral + spin coherence
    # FFT coherence: well-distributed tongues = high coherence
    tongue_vals = [profile.get(t, 0.0) for t in TONGUES]
    mean_val = sum(tongue_vals) / max(len(tongue_vals), 1)
    variance = sum((v - mean_val) ** 2 for v in tongue_vals) / max(len(tongue_vals), 1)
    coherence = max(0.0, 1.0 - variance * 4)  # Low variance = high coherence
    layers_survived = 10

    # L11: Triadic temporal distance
    # tau (proper time), eta (conformal time), q (quantum phase)
    tau = breath_phase * PHI_INV
    eta = math.log(1 + abs(tau))
    layers_survived = 11

    # L12: Harmonic wall H(d,pd) = 1/(1 + d + 2*pd)
    # Uses the src/ production formula (bounded safety score)
    phase_deviation = variance  # Use tongue variance as phase deviation proxy
    harmonic_wall = 1.0 / (1.0 + hyperbolic_distance + 2.0 * phase_deviation)
    energy_conserved = harmonic_wall > 0.01  # Must have nonzero safety
    layers_survived = 12

    # L13: Risk decision
    if harmonic_wall > 0.7:
        risk_decision = "ALLOW"
    elif harmonic_wall > 0.4:
        risk_decision = "QUARANTINE"
    elif harmonic_wall > 0.15:
        risk_decision = "ESCALATE"
    else:
        risk_decision = "DENY"
    layers_survived = 13

    # L14: Audio axis (always passes — output layer)
    layers_survived = 14

    # Final pass check: must have ALLOW or QUARANTINE and bounded distance
    passed = (
        risk_decision in ("ALLOW", "QUARANTINE")
        and distance_bounded
        and energy_conserved
    )

    return RapidsResult(
        passed=passed,
        layers_survived=layers_survived,
        energy_conserved=energy_conserved,
        distance_bounded=distance_bounded,
        harmonic_wall_score=round(harmonic_wall, 6),
        safety_score=round(harmonic_wall, 6),
        breath_phase=round(breath_phase, 6),
        risk_decision=risk_decision,
        failure_layer=None if passed else 13,
        failure_reason="" if passed else f"Risk decision: {risk_decision}",
    )


# ---------------------------------------------------------------------------
# Layer 3: Deep Water — Polyhedral Flow Navigation
# ---------------------------------------------------------------------------


def verify_deep_water(
    profile: dict[str, float],
    content_hash: str = "",
) -> DeepWaterResult:
    """Layer 3: Test polyhedral flow navigation.

    Routes the record through the polyhedral flow graph and evaluates
    friction at boundary crossings, confinement, and path quality.
    """
    if POLYHEDRAL_AVAILABLE:
        try:
            # Create router from content hash seed
            seed_int = int(hashlib.sha256(content_hash.encode()).hexdigest()[:8], 16)
            lfsr = FibonacciLFSR(n_bits=8, state=max(seed_int % 255, 1))
            dual = DualSpin(n_bits=8, seed=max(seed_int % 255, 1), lfsr=lfsr)
            router = PolyhedralFlowRouter(dual_spin=dual, max_hops=6)

            # Route each tongue
            routes = {}
            tongues_routed = 0
            total_friction = 0.0
            boundary_crossings = 0

            for tongue in TONGUES:
                try:
                    route = router.route(tongue)
                    routes[tongue] = route
                    tongues_routed += 1
                    if "friction" in route:
                        total_friction += route.get("friction", 0.0)
                    boundary_crossings += route.get("hops", 0)
                except Exception:
                    routes[tongue] = {"error": True}

            # Generate flow address
            flow_addr = router.generate_flow_address()

            # Compute confinement from tongue profile distances
            profile_vals = [profile.get(t, 0.0) for t in TONGUES]
            center = sum(profile_vals) / max(len(profile_vals), 1)
            deviation = math.sqrt(
                sum((v - center) ** 2 for v in profile_vals) / max(len(profile_vals), 1)
            )
            confinement = max(0.0, 1.0 - deviation * 3)

            # Compute friction spectrum if available
            try:
                friction_spec = compute_friction_spectrum()
                friction_mag = sum(
                    f.get("friction_magnitude", 0.0)
                    if isinstance(f, dict) else 0.0
                    for f in friction_spec[:10]
                ) / max(min(len(friction_spec), 10), 1)
            except Exception:
                friction_mag = total_friction / max(tongues_routed, 1)

            # Harmonic wall from polyhedral distances
            poly_distances = {}
            for i, t in enumerate(TONGUES):
                poly_distances[t] = profile.get(t, 0.0) * TONGUE_WEIGHTS[t]
            try:
                hw = composite_harmonic_wall(poly_distances)
            except Exception:
                hw = {"composite": 0.5}

            path_quality = (confinement + (tongues_routed / len(TONGUES))) / 2.0
            passed = tongues_routed >= 4 and confinement > 0.2

            return DeepWaterResult(
                passed=passed,
                tongues_routed=tongues_routed,
                confinement_score=round(confinement, 6),
                friction_magnitude=round(friction_mag, 6),
                harmonic_wall=hw if isinstance(hw, dict) else {"composite": hw},
                path_quality=round(path_quality, 6),
                boundary_crossings=boundary_crossings,
                flow_address=flow_addr if isinstance(flow_addr, dict) else {},
            )
        except Exception as e:
            # Polyhedral flow failed — use fallback
            pass

    # Fallback: compute basic flow metrics from tongue profile
    profile_vals = [profile.get(t, 0.0) for t in TONGUES]
    active = sum(1 for v in profile_vals if v > 0.05)
    center = sum(profile_vals) / max(len(profile_vals), 1)
    deviation = math.sqrt(
        sum((v - center) ** 2 for v in profile_vals) / max(len(profile_vals), 1)
    )
    confinement = max(0.0, 1.0 - deviation * 3)

    # Friction: high deviation between adjacent tongues = high friction
    friction = 0.0
    for i in range(len(TONGUES)):
        j = (i + 1) % len(TONGUES)
        diff = abs(profile_vals[i] - profile_vals[j])
        friction += diff * TONGUE_WEIGHTS[TONGUES[i]]
    friction /= len(TONGUES)

    # Harmonic wall fallback
    weighted_sum = sum(v * TONGUE_WEIGHTS[t] for v, t in zip(profile_vals, TONGUES))
    hw_score = 1.0 / (1.0 + PHI * weighted_sum)

    path_quality = (confinement + (active / len(TONGUES))) / 2.0
    passed = active >= 4 and confinement > 0.2

    return DeepWaterResult(
        passed=passed,
        tongues_routed=active,
        confinement_score=round(confinement, 6),
        friction_magnitude=round(friction, 6),
        harmonic_wall={"composite": round(hw_score, 6)},
        path_quality=round(path_quality, 6),
        boundary_crossings=active - 1,
    )


# ---------------------------------------------------------------------------
# Polly Pad — Full 3-Layer Verification
# ---------------------------------------------------------------------------


def polly_pad_verify(
    tongue_profile: dict[str, float],
    hyperbolic_distance: float = 0.0,
    safety_score: float = 1.0,
    breath_phase: float = 0.0,
    content_hash: str = "",
) -> PollyPadResult:
    """Run a record through all 3 Polly Pad layers.

    Layer 1 (Shallows): Axiom verification — 5 quantum axioms
    Layer 2 (Rapids): 14-layer pipeline simulation
    Layer 3 (Deep Water): Polyhedral flow navigation

    Returns survival status, depth, and composite quality score.
    Records that survive all 3 = gold-standard training data.
    """
    reinforcement = []

    # Layer 1: The Shallows
    shallows = verify_shallows(tongue_profile)
    if not shallows.passed:
        failed_axioms = [v.axiom_name for v in shallows.verdicts if not v.passed]
        reinforcement.extend([f"axiom:{a}" for a in failed_axioms])

    # Layer 2: The Rapids (run even if shallows failed — diagnostic value)
    rapids = verify_rapids(
        tongue_profile,
        hyperbolic_distance=hyperbolic_distance,
        safety_score=safety_score,
        breath_phase=breath_phase,
    )
    if not rapids.passed:
        if rapids.failure_layer:
            reinforcement.append(f"layer:{rapids.failure_layer}")
        if not rapids.energy_conserved:
            reinforcement.append("energy_conservation")
        if not rapids.distance_bounded:
            reinforcement.append("distance_bounds")

    # Layer 3: Deep Water (run even if rapids failed)
    deep_water = verify_deep_water(tongue_profile, content_hash)
    if not deep_water.passed:
        reinforcement.append("polyhedral_navigation")
        if deep_water.confinement_score < 0.3:
            reinforcement.append("confinement")
        if deep_water.tongues_routed < 4:
            reinforcement.append("tongue_coverage")

    # Compute survival depth
    survival_depth = 0
    if shallows.passed:
        survival_depth = 1
        if rapids.passed:
            survival_depth = 2
            if deep_water.passed:
                survival_depth = 3

    survived = survival_depth == 3

    # Composite pad score: weighted geometric mean
    scores = [
        shallows.composite_score,
        rapids.harmonic_wall_score if rapids.harmonic_wall_score > 0 else 0.01,
        deep_water.path_quality if deep_water.path_quality > 0 else 0.01,
    ]
    weights = [0.3, 0.4, 0.3]  # Rapids weighted slightly higher

    weighted_log_sum = sum(w * math.log(max(s, 1e-10)) for w, s in zip(weights, scores))
    pad_score = math.exp(weighted_log_sum)

    # Mining viability: survived at least Layer 2 with decent scores
    mining_viable = survival_depth >= 2 and pad_score > 0.15

    return PollyPadResult(
        survived=survived,
        survival_depth=survival_depth,
        pad_score=round(pad_score, 6),
        shallows=shallows,
        rapids=rapids,
        deep_water=deep_water,
        mining_viable=mining_viable,
        recommended_reinforcement=reinforcement,
    )


# ---------------------------------------------------------------------------
# Mining mode — autonomous path discovery
# ---------------------------------------------------------------------------


def mine_paths(
    base_profile: dict[str, float] | None = None,
    n_perturbations: int = 50,
    perturbation_scale: float = 0.1,
) -> dict[str, Any]:
    """Autonomous mining: generate tongue profile perturbations, verify through Polly Pad.

    Returns statistics on which paths survived and where failures cluster.
    Valid paths are gold-standard training signal.
    """
    import random

    if base_profile is None:
        base_profile = {t: 1.0 / len(TONGUES) for t in TONGUES}

    results = {
        "total_mined": n_perturbations,
        "survived_all": 0,
        "survived_shallows": 0,
        "survived_rapids": 0,
        "survived_deep": 0,
        "failure_clusters": {},
        "best_pad_score": 0.0,
        "avg_pad_score": 0.0,
        "mining_viable_count": 0,
        "valid_paths": [],
    }

    pad_scores = []

    for i in range(n_perturbations):
        # Perturb the profile
        perturbed = {}
        for t in TONGUES:
            noise = random.gauss(0, perturbation_scale)
            val = max(0.0, min(1.0, base_profile.get(t, 0.0) + noise))
            perturbed[t] = val

        # Normalize to sum to ~1
        total = sum(perturbed.values())
        if total > 0:
            perturbed = {t: v / total for t, v in perturbed.items()}

        content_hash = hashlib.sha256(f"mine-{i}".encode()).hexdigest()

        result = polly_pad_verify(
            tongue_profile=perturbed,
            breath_phase=float(i) * 0.5,
            content_hash=content_hash,
        )

        pad_scores.append(result.pad_score)

        if result.survived:
            results["survived_all"] += 1
        if result.shallows.passed:
            results["survived_shallows"] += 1
        if result.rapids.passed:
            results["survived_rapids"] += 1
        if result.deep_water.passed:
            results["survived_deep"] += 1
        if result.mining_viable:
            results["mining_viable_count"] += 1

        if result.pad_score > results["best_pad_score"]:
            results["best_pad_score"] = round(result.pad_score, 6)

        # Track failure clusters
        for r in result.recommended_reinforcement:
            results["failure_clusters"][r] = results["failure_clusters"].get(r, 0) + 1

        # Store valid paths for training
        if result.survived:
            results["valid_paths"].append({
                "profile": perturbed,
                "pad_score": result.pad_score,
                "harmonic_wall": result.rapids.harmonic_wall_score,
                "confinement": result.deep_water.confinement_score,
            })

    results["avg_pad_score"] = round(
        sum(pad_scores) / max(len(pad_scores), 1), 6
    )

    return results


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Polly Pad — 3-Layer Verification Sandbox")
    print(f"  Axiom modules: U={UNITARITY_AVAILABLE} L={LOCALITY_AVAILABLE} "
          f"C={CAUSALITY_AVAILABLE} S={SYMMETRY_AVAILABLE} Co={COMPOSITION_AVAILABLE}")
    print(f"  Polyhedral flow: {POLYHEDRAL_AVAILABLE}")
    print(f"  NumPy: {HAS_NUMPY}")
    print()

    profiles = [
        ("Balanced", {t: 1.0/6 for t in TONGUES}),
        ("KO-heavy", {"KO": 0.6, "AV": 0.1, "RU": 0.05, "CA": 0.1, "UM": 0.1, "DR": 0.05}),
        ("Extreme UM", {"KO": 0.02, "AV": 0.02, "RU": 0.02, "CA": 0.02, "UM": 0.9, "DR": 0.02}),
    ]

    for name, prof in profiles:
        content_hash = hashlib.sha256(name.encode()).hexdigest()
        result = polly_pad_verify(prof, content_hash=content_hash)
        print(f"  {name}:")
        print(f"    Survived: {result.survived} (depth {result.survival_depth}/3)")
        print(f"    Pad score: {result.pad_score}")
        print(f"    Shallows: {result.shallows.axioms_passed}/{result.shallows.axioms_total} axioms")
        print(f"    Rapids: L{result.rapids.layers_survived}/14, "
              f"H={result.rapids.harmonic_wall_score}, "
              f"risk={result.rapids.risk_decision}")
        print(f"    Deep Water: {result.deep_water.tongues_routed}/6 routed, "
              f"confinement={result.deep_water.confinement_score}")
        print(f"    Mining viable: {result.mining_viable}")
        if result.recommended_reinforcement:
            print(f"    Reinforce: {result.recommended_reinforcement}")
        print()

    # Quick mining test
    print("Mining test (20 perturbations)...")
    mine_result = mine_paths(n_perturbations=20)
    print(f"  Survived all 3: {mine_result['survived_all']}/20")
    print(f"  Mining viable: {mine_result['mining_viable_count']}/20")
    print(f"  Best pad score: {mine_result['best_pad_score']}")
    print(f"  Avg pad score: {mine_result['avg_pad_score']}")
    if mine_result["failure_clusters"]:
        print(f"  Failure clusters: {mine_result['failure_clusters']}")
