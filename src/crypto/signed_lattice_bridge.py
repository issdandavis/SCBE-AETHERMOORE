"""
Signed Lattice Bridge - Connecting Symphonic Cipher + GeoSeal + Dual Lattice
============================================================================

This module bridges three systems that move past binary:

1. Symphonic Cipher: Negative token IDs -> sub-440Hz frequencies (shadow)
2. GeoSeal: Negative context components + hyperbolic negative curvature
3. Dual Lattice: 10D Kyber/Dilithium structure with Sacred Tongues

Key Insight: "Moving Past Binary"
---------------------------------
Instead of binary {0,1} decisions, we use:
- Continuous values in [0,1] (flux states)
- Signed values in [-1,1] or (-inf, +inf) (polarity)
- Quaternary classifications (Demi, Quasi, Polly, Collapsed)
- Hyperbolic geometry where distance to boundary -> infinity

The integration flow:
  Symphonic (signed freq) -> GeoSeal (hyperbolic) -> Dual Lattice (governance)
"""

import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

# Import the three systems
from .symphonic_cipher import (
    SymphonicToken, TonguePolarity, SACRED_TONGUE_VOCAB,
    token_to_frequency, analyze_polarity_balance,
    generate_symphonic_sequence, BASE_FREQ
)
from .geo_seal import (
    ContextVector, SecurityPosture,
    hyperbolic_distance, trust_from_position,
    harmonic_wall_cost, compute_triangle_deficit
)
from .dual_lattice import (
    SacredTongue, FluxState, LatticeVector,
    DualLatticeCrossStitch, TongueLatticeGovernor,
    TONGUE_PHASES, TONGUE_WEIGHTS, PHI
)


@dataclass
class SignedGovernanceResult:
    """Result of governance through the signed lattice bridge."""
    decision: str                    # ALLOW/QUARANTINE/ESCALATE/DENY
    trust_score: float              # [0, 1]
    polarity: str                   # light/shadow/balanced
    hyperbolic_distance: float      # Distance in Poincare ball
    harmonic_cost: float            # Exponential cost from harmonic wall
    frequency_signature: float      # Dominant frequency (+ or - from 440)
    tongues_active: List[str]       # Active Sacred Tongues
    lattice_proof: Dict[str, Any]   # Cryptographic proof from dual lattice


class SignedLatticeBridge:
    """
    Bridge connecting signed/continuous systems with dual lattice governance.

    This enables:
    1. Shadow vocabulary (negative IDs) to affect governance decisions
    2. Hyperbolic position to modulate trust scores
    3. Continuous flux states instead of binary on/off
    4. Polarity-aware cross-stitch patterns
    """

    def __init__(self):
        self.dual_lattice = DualLatticeCrossStitch()
        self.lattice_governor = TongueLatticeGovernor()

    def symphonic_to_context(
        self,
        tokens: List[str]
    ) -> Tuple[ContextVector, Dict[str, Any]]:
        """
        Convert symphonic tokens to a context vector.

        Maps token polarities to context dimensions:
        - Light tokens contribute positive values
        - Shadow tokens contribute negative values
        - Balance affects the security posture
        """
        analysis = analyze_polarity_balance(tokens)

        # Build context vector from token analysis
        # Dimension mapping:
        # [0]: Polarity sum (can be negative)
        # [1]: Balance ratio [-1, 1]
        # [2]: Light momentum
        # [3]: Shadow momentum (negative)
        # [4]: Security level (from balance)
        # [5]: Trust baseline
        # [6]: Temporal (normalized)
        # [7]: Intent (from dominant polarity)
        # [8]: Phase (from average frequency offset)

        now = datetime.now(timezone.utc)
        day_fraction = (now.hour * 3600 + now.minute * 60 + now.second) / 86400

        # Compute average frequency offset from 440 Hz
        freq_offsets = []
        for token in tokens:
            try:
                freq = token_to_frequency(token)
                freq_offsets.append(freq - BASE_FREQ)
            except ValueError:
                pass

        avg_freq_offset = np.mean(freq_offsets) if freq_offsets else 0

        components = [
            analysis["polarity_sum"],           # Can be negative
            analysis["balance_ratio"],          # [-1, 1]
            analysis["light_count"],            # Positive momentum
            -analysis["shadow_count"],          # Negative momentum
            analysis["balance_ratio"] * 5,      # Security level (scaled)
            0.5 + analysis["balance_ratio"] * 0.3,  # Trust baseline
            day_fraction,                       # Temporal
            1.0 if analysis["dominant_polarity"] == "light" else
            -1.0 if analysis["dominant_polarity"] == "shadow" else 0.0,  # Intent
            avg_freq_offset / 30.0,             # Phase (scaled by FREQ_STEP)
        ]

        return ContextVector(components), analysis

    def context_to_lattice(
        self,
        context: ContextVector,
        security_posture: SecurityPosture = SecurityPosture.QUASI
    ) -> LatticeVector:
        """
        Project context vector into 10D dual lattice space.

        Handles negative values through sigmoid mapping while
        preserving polarity information in the phase dimension.
        """
        # Get 10D mapping from context
        raw_10d = context.to_lattice_10d()

        # Determine flux state from security posture
        flux_map = {
            SecurityPosture.POLLY: 0.95,
            SecurityPosture.QUASI: 0.7,
            SecurityPosture.DEMI: 0.3,
            SecurityPosture.COLLAPSED: 0.05,
        }
        flux = flux_map.get(security_posture, 0.5)

        # Compute phase from signed components (preserve polarity info)
        # Only use first 6 components for tongue phase calculation
        phase_weights = np.array([
            TONGUE_PHASES.get(SacredTongue.KO, 0) / 360,
            TONGUE_PHASES.get(SacredTongue.AV, 60) / 360,
            TONGUE_PHASES.get(SacredTongue.RU, 120) / 360,
            TONGUE_PHASES.get(SacredTongue.CA, 180) / 360,
            TONGUE_PHASES.get(SacredTongue.UM, 240) / 360,
            TONGUE_PHASES.get(SacredTongue.DR, 300) / 360,
        ])
        n_tongue = min(6, len(context.components))
        signed_phase = np.sum(context.components[:n_tongue] * phase_weights[:n_tongue]) * 60

        # Normalize phase to [0, 360)
        phase = signed_phase % 360

        return LatticeVector(
            tongues=raw_10d[:6],
            time=raw_10d[6] if len(raw_10d) > 6 else 0.5,
            intent=raw_10d[7] if len(raw_10d) > 7 else 0.5,
            phase=phase,
            flux=flux
        )

    def compute_hyperbolic_trust(
        self,
        context: ContextVector,
        reference: ContextVector = None
    ) -> Tuple[float, float]:
        """
        Compute trust score using hyperbolic geometry.

        Returns:
            (trust_score, hyperbolic_distance)

        Trust is highest at the origin (safe center) and decays
        hyperbolically toward the boundary (adversarial edge).
        """
        # Project context to Poincare ball
        point = context.to_poincare()

        if reference is not None:
            ref_point = reference.to_poincare()
        else:
            ref_point = np.zeros_like(point)

        # Truncate to same dimension
        min_dim = min(len(point), len(ref_point))
        point = point[:min_dim]
        ref_point = ref_point[:min_dim]

        # Compute hyperbolic distance
        try:
            h_dist = hyperbolic_distance(point, ref_point)
        except ValueError:
            # Points outside ball - maximum distance
            h_dist = 10.0

        # Trust from position (decays with distance)
        trust = trust_from_position(point)

        return trust, h_dist

    def govern_with_polarity(
        self,
        tokens: List[str],
        action: str,
        target: str,
        sensitivity: float = 0.5
    ) -> SignedGovernanceResult:
        """
        Full governance pipeline with signed/continuous values.

        Flow:
        1. Symphonic tokens -> Context vector (with negative values)
        2. Context -> Hyperbolic trust score
        3. Context -> 10D Lattice vector
        4. Lattice -> Dual lattice governance decision
        5. Apply harmonic wall cost modulation
        """
        # Step 1: Convert tokens to context
        context, polarity_analysis = self.symphonic_to_context(tokens)

        # Step 2: Compute hyperbolic trust
        hyper_trust, h_dist = self.compute_hyperbolic_trust(context)

        # Step 3: Determine security posture from polarity
        polarity = polarity_analysis["dominant_polarity"]
        if polarity == "shadow":
            posture = SecurityPosture.DEMI  # More restrictive
        elif polarity == "balanced":
            posture = SecurityPosture.QUASI
        else:
            posture = SecurityPosture.POLLY

        # Step 4: Convert to lattice and govern
        lattice_vec = self.context_to_lattice(context, posture)

        # Adjust sensitivity based on polarity
        # Shadow-dominant = higher sensitivity (more scrutiny)
        polarity_adjustment = -polarity_analysis["balance_ratio"] * 0.2
        adjusted_sensitivity = min(1.0, max(0.0, sensitivity + polarity_adjustment))

        # Run through lattice governor
        lattice_result = self.lattice_governor.authorize(
            action, target, adjusted_sensitivity
        )

        # Step 5: Apply harmonic wall modulation
        harmonic_cost = harmonic_wall_cost(h_dist)

        # Modulate trust score by harmonic cost
        # Higher cost = lower effective trust
        effective_trust = lattice_result["trust_score"] / (1 + np.log1p(harmonic_cost - 1))

        # Final decision based on effective trust and thresholds
        thresholds = lattice_result.get("thresholds", {
            "allow": 0.7, "quarantine": 0.5, "escalate": 0.3
        })

        if effective_trust > thresholds.get("allow", 0.7):
            decision = "ALLOW"
        elif effective_trust > thresholds.get("quarantine", 0.5):
            decision = "QUARANTINE"
        elif effective_trust > thresholds.get("escalate", 0.3):
            decision = "ESCALATE"
        else:
            decision = "DENY"

        # Shadow tokens always escalate or deny
        if polarity == "shadow" and decision == "ALLOW":
            decision = "QUARANTINE"

        # Compute frequency signature
        freq_sig = polarity_analysis["polarity_sum"] * 30  # Sum of offsets from 440

        return SignedGovernanceResult(
            decision=decision,
            trust_score=float(effective_trust),
            polarity=polarity,
            hyperbolic_distance=float(h_dist),
            harmonic_cost=float(harmonic_cost),
            frequency_signature=float(freq_sig),
            tongues_active=lattice_result.get("tongues_active", []),
            lattice_proof=lattice_result.get("lattice_proof", {})
        )


# =============================================================================
# Demo
# =============================================================================

def demo():
    """Demonstrate the signed lattice bridge."""
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║              SIGNED LATTICE BRIDGE - Moving Past Binary                       ║
║         Symphonic Cipher + GeoSeal + Dual Lattice Integration                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)

    bridge = SignedLatticeBridge()

    # Test cases with different polarity mixes
    test_cases = [
        # Light-dominant sequence
        (["light", "fire", "truth", "wisdom"], "navigate", "https://github.com", 0.3),
        # Shadow-dominant sequence
        (["shadow", "void", "abyss", "phantom"], "execute", "rm -rf /", 0.8),
        # Balanced sequence
        (["light", "shadow", "balance", "truth", "void"], "click", "button.submit", 0.5),
        # Mixed with neutrals
        (["center", "light", "echo", "harmony", "mist"], "type", "input#search", 0.4),
    ]

    for tokens, action, target, sensitivity in test_cases:
        print(f"\n{'='*70}")
        print(f"  Tokens: {tokens}")
        print(f"  Action: {action} -> {target[:30]}")
        print(f"  Base Sensitivity: {sensitivity}")

        result = bridge.govern_with_polarity(tokens, action, target, sensitivity)

        print(f"\n  Polarity Analysis:")
        print(f"    Dominant: {result.polarity.upper()}")
        print(f"    Frequency Signature: {result.frequency_signature:+.1f} Hz from 440")

        print(f"\n  Hyperbolic Geometry:")
        print(f"    Distance: {result.hyperbolic_distance:.3f}")
        print(f"    Harmonic Cost: {result.harmonic_cost:.3f}")

        print(f"\n  Lattice Governance:")
        print(f"    Trust Score: {result.trust_score:.3f}")
        print(f"    Active Tongues: {', '.join(result.tongues_active)}")
        print(f"    DECISION: {result.decision}")

    print(f"\n{'='*70}")
    print("  Key Insights - Moving Past Binary:")
    print("  - Negative token IDs create shadow frequencies below 440 Hz")
    print("  - Context vectors support negative components (-inf to +inf)")
    print("  - Hyperbolic distance uses negative curvature (angle sum < 180)")
    print("  - Flux states provide quaternary (not binary) classification")
    print("  - Trust is continuous [0,1], not boolean on/off")


if __name__ == "__main__":
    demo()
