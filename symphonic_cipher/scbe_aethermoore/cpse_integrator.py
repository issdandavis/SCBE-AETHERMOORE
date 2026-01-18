"""
CPSE → SCBE Math-Safe Integrator

Fixes the boundedness violations in the original integration:
    A) d* was unbounded → now clamped to d_max
    B) τ was outside [0,1] → now properly bounded
    C) S_spec could go negative → now clamped
    D) spin risk could exceed 1 → now clamped

CPSE Axioms (C1-C3):
    C1 (Bounded CPSE deviations): Each CPSE output is mapped by a
        monotone bounded function into [0,1]:
        delay_dev, cost_dev, spin_dev, sol_dev, flux_dev ∈ [0,1]

    C2 (Monotone coupling): CPSE can only move SCBE features in the
        "worse" direction (decreasing coherences/trust, increasing
        effective distance), via monotone maps.

    C3 (Range preservation): After coupling, all SCBE features remain
        in their required domains:
        τ, S_spec, S_audio, C_spin ∈ [0,1] and d*_eff ∈ [0, d_max]

With C1-C3, the existing E.2 and E.3 proofs survive unchanged.
"""

import math
from dataclasses import dataclass
from typing import Dict


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp x to [lo, hi]."""
    return lo if x < lo else hi if x > hi else x


@dataclass
class CPSEDeviations:
    """Bounded CPSE deviation values, all in [0,1] per Axiom C1."""
    delay_dev: float   # Latency deviation
    cost_dev: float    # Harmonic cost deviation
    spin_dev: float    # Spin mismatch deviation
    sol_dev: float     # Soliton decay deviation
    flux_dev: float    # Flux interference deviation


@dataclass
class SCBEEffectiveState:
    """SCBE state after CPSE coupling, all in valid domains per Axiom C3."""
    tau_eff: float      # Trust in [0,1]
    d_star_eff: float   # Realm distance in [0, d_max]
    C_spin_eff: float   # Spin coherence in [0,1]
    S_spec_eff: float   # Spectral stability in [0,1]
    S_audio_eff: float  # Audio stability in [0,1]


@dataclass
class RiskOutput:
    """Complete risk calculation output."""
    deviations: CPSEDeviations
    state: SCBEEffectiveState
    risk_base: float      # Base risk in [0,1]
    H: float              # Harmonic scaling H(d*,R) = R^(d*²)
    risk_prime: float     # Amplified risk = risk_base × H
    log10_risk: float     # log₁₀(Risk') for display


class CPSESCBEIntegrator:
    """
    CPSE → SCBE Coupling Layer (math-safe).

    Preserves all SCBE theorems by:
    - Mapping CPSE outputs to bounded deviations in [0,1] (Axiom C1)
    - Only degrading SCBE features, never improving (Axiom C2)
    - Clamping all outputs to valid domains (Axiom C3)

    The "vertical wall" effect of H(d,R) = R^(d²) is preserved,
    but d* is bounded by d_max to prevent overflow.
    """

    def __init__(
        self,
        R: float = 1.618,       # Golden ratio (base for harmonic scaling)
        d_max: float = 12.0,    # Maximum realm distance (preserves E.3)
        # SCBE baseline features (in their theorem domains)
        tau_baseline: float = 1.0,
        d_star_baseline: float = 0.5,
        C_spin_baseline: float = 0.9,
        S_spec_baseline: float = 0.9,
        S_audio_baseline: float = 0.9,
    ):
        self.R = max(R, 1.0 + 1e-9)  # Ensure R > 1
        self.d_max = d_max

        # SCBE baseline state (clean, no threat)
        self.tau_0 = clip(tau_baseline)
        self.d_star_0 = clip(d_star_baseline, 0.0, d_max)
        self.C_spin_0 = clip(C_spin_baseline)
        self.S_spec_0 = clip(S_spec_baseline)
        self.S_audio_0 = clip(S_audio_baseline)

        # Risk weights (must sum to 1)
        self.w_d = 0.3    # d_tri weight
        self.w_c = 0.2    # coherence weight
        self.w_s = 0.2    # spectral weight
        self.w_t = 0.2    # trust weight
        self.w_a = 0.1    # audio weight

        # Coupling constants (policy knobs / Choice Script Θ)
        self.kappa_delay = 0.6    # Delay → τ degradation
        self.kappa_cost = 1.0     # Cost → d* inflation
        self.kappa_spin = 0.8     # Spin mismatch → C_spin degradation
        self.kappa_sol = 0.6      # Soliton decay → C_spin degradation
        self.kappa_flux = 0.6     # Flux → S_spec degradation

        # CPSE deviation scaling parameters
        self.delay_scale = 0.25   # seconds (tanh saturation point)
        self.cost_0 = 1000.0      # baseline cost for log scaling
        self.cost_scale = 2.0     # tanh scaling for cost_dev
        self.flux_scale = 0.25    # variance (tanh saturation point)

    # =========================================================================
    # CPSE DEVIATION MAPPINGS (Axiom C1: bounded, monotone)
    # =========================================================================

    def compute_delay_dev(self, delay_s: float) -> float:
        """
        Map latency delay to bounded deviation.

        delay_dev := tanh(delay / s_d) ∈ [0,1)

        High delay → deviation approaches 1
        """
        return math.tanh(delay_s / max(self.delay_scale, 1e-12))

    def compute_cost_dev(self, cost: float) -> float:
        """
        Map harmonic cost to bounded deviation.

        cost_dev := tanh(log₂(1 + cost/cost₀) / s_c) ∈ [0,1)

        High cost → deviation approaches 1
        """
        x = math.log2(1.0 + cost / max(self.cost_0, 1e-12))
        return math.tanh(x / max(self.cost_scale, 1e-12))

    def compute_spin_dev(self, spin_angle_deg: float) -> float:
        """
        Map spin mismatch angle to bounded deviation.

        spin_dev := sin²(Δψ/2) ∈ [0,1]

        Δψ=0° → 0 (aligned), Δψ=180° → 1 (anti-aligned)
        """
        rad = math.radians(spin_angle_deg)
        return math.sin(rad / 2.0) ** 2

    def compute_sol_dev(self, soliton_gain: float) -> float:
        """
        Map soliton gain to bounded deviation.

        sol_dev := max(0, 1 - gain) ∈ [0,1]

        gain=1 → 0 (stable), gain=0 → 1 (decayed)
        """
        return clip(1.0 - soliton_gain, 0.0, 1.0)

    def compute_flux_dev(self, flux_var: float) -> float:
        """
        Map flux variance to bounded deviation.

        flux_dev := tanh(Var(flux) / s_f) ∈ [0,1)

        High variance → deviation approaches 1
        """
        return math.tanh(flux_var / max(self.flux_scale, 1e-12))

    # =========================================================================
    # HARMONIC SCALING (preserved from original proofs)
    # =========================================================================

    def H(self, d_star: float) -> float:
        """
        Harmonic scaling H(d*, R) = R^(d*²)

        Uses exp form for numerical stability:
            H = exp(d² × ln(R))

        Theorem 12.1: ∂H/∂d = 2d·ln(R)·R^(d²) > 0 for d > 0, R > 1
        """
        d = min(d_star, self.d_max)  # Clamp to prevent overflow
        return math.exp((d * d) * math.log(self.R))

    # =========================================================================
    # MAIN INTEGRATION (Axioms C2-C3: monotone coupling, range preservation)
    # =========================================================================

    def integrate(
        self,
        delay: float,
        cost: float,
        soliton_gain: float,
        spin_angle_deg: float,
        flux_var: float,
        d_tri_normalized: float = 0.0,  # Triadic distance in [0,1]
    ) -> RiskOutput:
        """
        Integrate CPSE outputs into SCBE risk calculation.

        All inputs are raw CPSE values. All outputs satisfy Axioms C1-C3.

        Args:
            delay: Latency delay in seconds
            cost: Harmonic cost (security level penalty)
            soliton_gain: Soliton amplitude gain [0,1]
            spin_angle_deg: Spin mismatch angle in degrees
            flux_var: Flux variance
            d_tri_normalized: Normalized triadic distance [0,1]

        Returns:
            RiskOutput with all bounded values and amplified risk
        """
        # Step 1: Compute bounded CPSE deviations (Axiom C1)
        devs = CPSEDeviations(
            delay_dev=self.compute_delay_dev(delay),
            cost_dev=self.compute_cost_dev(cost),
            spin_dev=self.compute_spin_dev(spin_angle_deg),
            sol_dev=self.compute_sol_dev(soliton_gain),
            flux_dev=self.compute_flux_dev(flux_var),
        )

        # Step 2: Apply monotone coupling to SCBE features (Axiom C2)
        # Only DEGRADE features (decrease coherences, increase distance)

        # τ_eff = clip(τ₀ - κ_delay × delay_dev)
        tau_eff = clip(self.tau_0 - self.kappa_delay * devs.delay_dev)

        # S_spec_eff = clip(S_spec₀ - κ_flux × flux_dev)
        S_spec_eff = clip(self.S_spec_0 - self.kappa_flux * devs.flux_dev)

        # C_spin_eff = clip(C_spin₀ - κ_spin × spin_dev - κ_sol × sol_dev)
        C_spin_eff = clip(
            self.C_spin_0
            - self.kappa_spin * devs.spin_dev
            - self.kappa_sol * devs.sol_dev
        )

        # d*_eff = min(d_max, d*₀ × (1 + κ_cost × cost_dev))
        d_star_eff = min(
            self.d_max,
            self.d_star_0 * (1.0 + self.kappa_cost * devs.cost_dev)
        )

        # S_audio unchanged (no CPSE coupling yet)
        S_audio_eff = self.S_audio_0

        # Step 3: Build effective state (Axiom C3: all in valid domains)
        state = SCBEEffectiveState(
            tau_eff=tau_eff,
            d_star_eff=d_star_eff,
            C_spin_eff=C_spin_eff,
            S_spec_eff=S_spec_eff,
            S_audio_eff=S_audio_eff,
        )

        # Step 4: Compute base risk (bounded in [0,1])
        d_tri = clip(d_tri_normalized)
        risk_base = (
            self.w_d * d_tri +
            self.w_c * (1.0 - state.C_spin_eff) +
            self.w_s * (1.0 - state.S_spec_eff) +
            self.w_t * (1.0 - state.tau_eff) +
            self.w_a * (1.0 - state.S_audio_eff)
        )

        # Step 5: Amplify risk via harmonic scaling
        H_value = self.H(state.d_star_eff)
        risk_prime = risk_base * H_value

        return RiskOutput(
            deviations=devs,
            state=state,
            risk_base=risk_base,
            H=H_value,
            risk_prime=risk_prime,
            log10_risk=math.log10(max(risk_prime, 1e-300)),
        )


# =============================================================================
# VERIFICATION
# =============================================================================

def verify_axioms(integrator: CPSESCBEIntegrator, n_tests: int = 100) -> Dict[str, bool]:
    """
    Verify C1-C3 axioms hold under random inputs.

    C1: All deviations in [0,1]
    C2: SCBE features only degrade (monotone in CPSE outputs)
    C3: All SCBE features in valid domains
    """
    import random

    results = {"C1_bounded": True, "C2_monotone": True, "C3_range": True}

    for _ in range(n_tests):
        # Random CPSE inputs (including extreme values)
        delay = random.uniform(0, 10)
        cost = random.uniform(0, 100000)
        gain = random.uniform(-1, 2)
        spin = random.uniform(0, 360)
        flux = random.uniform(0, 10)

        out = integrator.integrate(delay, cost, gain, spin, flux)

        # C1: All deviations in [0,1]
        devs = out.deviations
        if not (0 <= devs.delay_dev <= 1):
            results["C1_bounded"] = False
        if not (0 <= devs.cost_dev <= 1):
            results["C1_bounded"] = False
        if not (0 <= devs.spin_dev <= 1):
            results["C1_bounded"] = False
        if not (0 <= devs.sol_dev <= 1):
            results["C1_bounded"] = False
        if not (0 <= devs.flux_dev <= 1):
            results["C1_bounded"] = False

        # C3: All SCBE features in valid domains
        state = out.state
        if not (0 <= state.tau_eff <= 1):
            results["C3_range"] = False
        if not (0 <= state.d_star_eff <= integrator.d_max):
            results["C3_range"] = False
        if not (0 <= state.C_spin_eff <= 1):
            results["C3_range"] = False
        if not (0 <= state.S_spec_eff <= 1):
            results["C3_range"] = False
        if not (0 <= state.S_audio_eff <= 1):
            results["C3_range"] = False

        # C2: Check monotonicity (larger inputs → worse outputs)
        # This requires comparing two runs, so we do it separately

    # C2 monotonicity test
    base_out = integrator.integrate(0.1, 100, 0.9, 10, 0.05)
    worse_out = integrator.integrate(1.0, 10000, 0.5, 90, 0.5)

    # τ should decrease (or stay same)
    if worse_out.state.tau_eff > base_out.state.tau_eff + 1e-9:
        results["C2_monotone"] = False

    # C_spin should decrease (or stay same)
    if worse_out.state.C_spin_eff > base_out.state.C_spin_eff + 1e-9:
        results["C2_monotone"] = False

    # S_spec should decrease (or stay same)
    if worse_out.state.S_spec_eff > base_out.state.S_spec_eff + 1e-9:
        results["C2_monotone"] = False

    # d_star should increase (or stay same)
    if worse_out.state.d_star_eff < base_out.state.d_star_eff - 1e-9:
        results["C2_monotone"] = False

    return results


# =============================================================================
# DEMO
# =============================================================================

def demo():
    """Demonstrate the math-safe integrator."""
    print("=" * 70)
    print("CPSE → SCBE MATH-SAFE INTEGRATOR")
    print("=" * 70)
    print()

    # Create integrator with golden ratio base
    integrator = CPSESCBEIntegrator(
        R=1.618,
        d_max=12.0,
        tau_baseline=1.0,
        d_star_baseline=0.5,
        C_spin_baseline=0.9,
        S_spec_baseline=0.9,
    )

    print("AXIOM VERIFICATION")
    print("-" * 70)
    axioms = verify_axioms(integrator)
    for axiom, passed in axioms.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {axiom}: {status}")
    print()

    print("SCENARIO: High-threat attack")
    print("-" * 70)
    print("CPSE Inputs:")
    print("  delay = 0.35s (latency spike)")
    print("  cost = 2500 (high security level)")
    print("  soliton_gain = 0.82 (slight decay)")
    print("  spin_angle = 45° (context mismatch)")
    print("  flux_var = 0.18 (network jitter)")
    print()

    out = integrator.integrate(
        delay=0.35,
        cost=2500,
        soliton_gain=0.82,
        spin_angle_deg=45,
        flux_var=0.18,
        d_tri_normalized=0.3,
    )

    print("CPSE Deviations (all in [0,1] per C1):")
    print(f"  delay_dev = {out.deviations.delay_dev:.4f}")
    print(f"  cost_dev  = {out.deviations.cost_dev:.4f}")
    print(f"  spin_dev  = {out.deviations.spin_dev:.4f}")
    print(f"  sol_dev   = {out.deviations.sol_dev:.4f}")
    print(f"  flux_dev  = {out.deviations.flux_dev:.4f}")
    print()

    print("SCBE Effective State (all in valid domains per C3):")
    print(f"  τ_eff      = {out.state.tau_eff:.4f} ∈ [0,1]")
    print(f"  d*_eff     = {out.state.d_star_eff:.4f} ∈ [0,{integrator.d_max}]")
    print(f"  C_spin_eff = {out.state.C_spin_eff:.4f} ∈ [0,1]")
    print(f"  S_spec_eff = {out.state.S_spec_eff:.4f} ∈ [0,1]")
    print()

    print("RISK CALCULATION:")
    print(f"  risk_base = {out.risk_base:.4f} ∈ [0,1]")
    print(f"  H(d*,R)   = {out.H:.2e}")
    print(f"  Risk'     = {out.risk_prime:.2e}")
    print(f"  log₁₀(Risk') = {out.log10_risk:.2f}")
    print()

    # Compare clean vs attack
    print("COMPARISON: Clean vs Attack")
    print("-" * 70)
    clean = integrator.integrate(0.01, 10, 0.99, 1, 0.01, 0.1)
    print(f"Clean scenario:  Risk' = {clean.risk_prime:.2e} (log₁₀ = {clean.log10_risk:.2f})")
    print(f"Attack scenario: Risk' = {out.risk_prime:.2e} (log₁₀ = {out.log10_risk:.2f})")
    print(f"Amplification:   {out.risk_prime / max(clean.risk_prime, 1e-300):.1f}x")
    print()

    print("=" * 70)
    all_pass = all(axioms.values())
    print(f"STATUS: {'ALL AXIOMS VERIFIED ✓' if all_pass else 'AXIOM VIOLATION ✗'}")
    print("=" * 70)

    return all_pass


if __name__ == "__main__":
    demo()
