/**
 * SCBE 14-Layer Pipeline - Complete TypeScript Implementation
 * ============================================================
 *
 * Direct mapping to mathematical specifications from proof document.
 * Each function matches the LaTeX specification exactly.
 *
 * Reference: scbe_proofs_complete.tex, scbe_14layer_reference.py
 *
 * @module harmonic/pipeline14
 * @version 3.0.0
 * @since 2026-01-20
 */
/**
 * Layer 1: Complex State Construction
 *
 * Input: Time-dependent features t, dimension D
 * Output: c ∈ ℂ^D
 *
 * Constructs complex-valued state from amplitudes and phases.
 * A1: Map to complex space c = amplitudes × exp(i × phases)
 */
export declare function layer1ComplexState(t: number[], D: number): {
    real: number[];
    imag: number[];
};
/**
 * Layer 2: Realification (Complex → Real)
 *
 * Input: c ∈ ℂ^D
 * Output: x ∈ ℝ^{2D}
 *
 * Isometric embedding Φ_1: ℂ^D → ℝ^{2D}
 * A2: x = [Re(c), Im(c)]
 */
export declare function layer2Realification(complex: {
    real: number[];
    imag: number[];
}): number[];
/**
 * Layer 3: SPD Weighted Transform
 *
 * Input: x ∈ ℝ^n, G SPD matrix (optional)
 * Output: x_G = G^{1/2} · x
 *
 * A3: Applies symmetric positive-definite weighting using golden ratio.
 */
export declare function layer3WeightedTransform(x: number[], G?: number[][]): number[];
/**
 * Layer 4: Poincaré Ball Embedding with Clamping
 *
 * Input: x_G ∈ ℝ^n
 * Output: u ∈ 𝔹^n (Poincaré ball)
 *
 * A4: Ψ_α(x) = tanh(α||x||) · x/||x|| with clamping to 𝔹^n_{1-ε}
 */
export declare function layer4PoincareEmbedding(xG: number[], alpha?: number, epsBall?: number): number[];
/**
 * Layer 5: Poincaré Ball Metric
 *
 * Input: u, v ∈ 𝔹^n
 * Output: d_ℍ(u, v) ∈ ℝ₊
 *
 * A5: d_ℍ(u,v) = arcosh(1 + 2||u-v||²/[(1-||u||²)(1-||v||²)])
 */
export declare function layer5HyperbolicDistance(u: number[], v: number[], eps?: number): number;
/**
 * Layer 6: Breathing Map (Diffeomorphism, NOT Isometry)
 *
 * Input: u ∈ 𝔹^n, breathing factor b ∈ [b_min, b_max]
 * Output: u_breathed ∈ 𝔹^n
 *
 * A6: T_breath(u) with radial rescaling (changes distances!)
 */
export declare function layer6BreathingTransform(u: number[], b: number, bMin?: number, bMax?: number): number[];
/**
 * Möbius (gyrovector) addition in the Poincaré ball model.
 * True hyperbolic isometry: d(u ⊕ v, w ⊕ v) = d(u, w)
 */
export declare function mobiusAdd(u: number[], v: number[], eps?: number): number[];
/**
 * Apply orthogonal rotation Q in the Poincaré ball.
 */
export declare function mobiusRotate(u: number[], Q: number[][]): number[];
/**
 * Layer 7: Phase Transform (True Isometry)
 *
 * Input: u ∈ 𝔹^n, shift a ∈ 𝔹^n, rotation Q ∈ O(n)
 * Output: ũ = t_a ∘ R_Q(u) using Möbius operations
 *
 * A7: Uses correct Möbius addition (gyrovector) for distance preservation.
 */
export declare function layer7PhaseTransform(u: number[], a: number[], Q: number[][]): number[];
/**
 * Layer 8: Minimum Distance to Realm Centers
 *
 * Input: u ∈ 𝔹^n, realm centers {μ_k} ⊂ 𝔹^n_{1-ε}
 * Output: d* = min_k d_ℍ(u, μ_k)
 *
 * A8: Computes proximity to known safe regions.
 */
export declare function layer8RealmDistance(u: number[], realms: number[][], eps?: number): {
    dStar: number;
    distances: number[];
};
/**
 * Layer 9: Spectral Coherence via FFT
 *
 * Input: Time-domain signal
 * Output: S_spec ∈ [0,1]
 *
 * A9: Low-frequency energy ratio as pattern stability measure.
 */
export declare function layer9SpectralCoherence(signal: number[] | null, eps?: number): number;
/**
 * Layer 10: Spin Coherence
 *
 * Input: Phase array (or complex phasors as {real, imag})
 * Output: C_spin ∈ [0,1]
 *
 * A10: Mean resultant length of unit phasors.
 */
export declare function layer10SpinCoherence(phases: number[]): number;
/**
 * Layer 11: Triadic Temporal Distance
 *
 * Input: Recent (d1), mid-term (d2), global (dG) distances
 * Output: d_tri ∈ [0,1]
 *
 * A11: d_tri = √(λ₁d₁² + λ₂d₂² + λ₃d_G²) / d_scale
 */
export declare function layer11TriadicTemporal(d1: number, d2: number, dG: number, lambda1?: number, lambda2?: number, lambda3?: number, dScale?: number): number;
/**
 * Layer 12: Harmonic Amplification
 *
 * Input: Distance d, base R > 1
 * Output: H(d, R) = R^{d²}
 *
 * A12: Exponential penalty for geometric distance.
 */
export declare function layer12HarmonicScaling(d: number, R?: number): number;
export type Decision = 'ALLOW' | 'QUARANTINE' | 'DENY';
/**
 * Layer 13: Three-Way Risk Decision
 *
 * Input: Base risk, harmonic amplification H
 * Output: Decision ∈ {ALLOW, QUARANTINE, DENY}
 *
 * A13: Risk' = Risk_base · H with thresholding.
 */
export declare function layer13RiskDecision(riskBase: number, H: number, theta1?: number, theta2?: number): {
    decision: Decision;
    riskPrime: number;
};
/**
 * Layer 14: Audio Telemetry Coherence
 *
 * Input: Audio frame (time-domain waveform)
 * Output: S_audio ∈ [0,1]
 *
 * A14: Instantaneous phase stability via Hilbert transform approximation.
 */
export declare function layer14AudioAxis(audio: number[] | null, eps?: number): number;
export interface Pipeline14Config {
    D?: number;
    alpha?: number;
    epsBall?: number;
    breathingFactor?: number;
    R?: number;
    theta1?: number;
    theta2?: number;
    wD?: number;
    wC?: number;
    wS?: number;
    wTau?: number;
    wA?: number;
}
export interface Pipeline14Result {
    decision: Decision;
    riskPrime: number;
    layers: {
        l1_complex: {
            real: number[];
            imag: number[];
        };
        l2_real: number[];
        l3_weighted: number[];
        l4_poincare: number[];
        l5_distance: number;
        l6_breathed: number[];
        l7_transformed: number[];
        l8_realmDist: number;
        l9_spectral: number;
        l10_spin: number;
        l11_triadic: number;
        l12_harmonic: number;
        l13_decision: Decision;
        l14_audio: number;
    };
    riskComponents: {
        riskBase: number;
        H: number;
    };
}
/**
 * Execute full 14-layer SCBE pipeline.
 *
 * @param t - Input features (time-dependent context)
 * @param config - Pipeline configuration
 * @returns Comprehensive metrics dictionary
 */
export declare function scbe14LayerPipeline(t: number[], config?: Pipeline14Config): Pipeline14Result;
export { layer1ComplexState as complexState, layer2Realification as realification, layer3WeightedTransform as weightedTransform, layer4PoincareEmbedding as poincareEmbedding, layer5HyperbolicDistance as hyperbolicDistance, layer6BreathingTransform as breathingTransform, layer7PhaseTransform as phaseTransform, layer8RealmDistance as realmDistance, layer9SpectralCoherence as spectralCoherence, layer10SpinCoherence as spinCoherence, layer11TriadicTemporal as triadicTemporal, layer12HarmonicScaling as harmonicScaling, layer13RiskDecision as riskDecision, layer14AudioAxis as audioAxis, };
//# sourceMappingURL=pipeline14.d.ts.map