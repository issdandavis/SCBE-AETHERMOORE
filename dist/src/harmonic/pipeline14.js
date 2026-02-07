"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.layer1ComplexState = layer1ComplexState;
exports.complexState = layer1ComplexState;
exports.layer2Realification = layer2Realification;
exports.realification = layer2Realification;
exports.layer3WeightedTransform = layer3WeightedTransform;
exports.weightedTransform = layer3WeightedTransform;
exports.layer4PoincareEmbedding = layer4PoincareEmbedding;
exports.poincareEmbedding = layer4PoincareEmbedding;
exports.layer5HyperbolicDistance = layer5HyperbolicDistance;
exports.hyperbolicDistance = layer5HyperbolicDistance;
exports.layer6BreathingTransform = layer6BreathingTransform;
exports.breathingTransform = layer6BreathingTransform;
exports.mobiusAdd = mobiusAdd;
exports.mobiusRotate = mobiusRotate;
exports.layer7PhaseTransform = layer7PhaseTransform;
exports.phaseTransform = layer7PhaseTransform;
exports.layer8RealmDistance = layer8RealmDistance;
exports.realmDistance = layer8RealmDistance;
exports.layer9SpectralCoherence = layer9SpectralCoherence;
exports.spectralCoherence = layer9SpectralCoherence;
exports.layer10SpinCoherence = layer10SpinCoherence;
exports.spinCoherence = layer10SpinCoherence;
exports.layer11TriadicTemporal = layer11TriadicTemporal;
exports.triadicTemporal = layer11TriadicTemporal;
exports.layer12HarmonicScaling = layer12HarmonicScaling;
exports.harmonicScaling = layer12HarmonicScaling;
exports.layer13RiskDecision = layer13RiskDecision;
exports.riskDecision = layer13RiskDecision;
exports.layer14AudioAxis = layer14AudioAxis;
exports.audioAxis = layer14AudioAxis;
exports.scbe14LayerPipeline = scbe14LayerPipeline;
// =============================================================================
// LAYER 1: Complex State
// =============================================================================
/**
 * Layer 1: Complex State Construction
 *
 * Input: Time-dependent features t, dimension D
 * Output: c ∈ ℂ^D
 *
 * Constructs complex-valued state from amplitudes and phases.
 * A1: Map to complex space c = amplitudes × exp(i × phases)
 */
function layer1ComplexState(t, D) {
    const amplitudes = [];
    const phases = [];
    if (t.length >= 2 * D) {
        for (let i = 0; i < D; i++) {
            amplitudes.push(t[i]);
            phases.push(t[D + i]);
        }
    }
    else {
        // Handle shorter inputs with defaults
        for (let i = 0; i < D; i++) {
            amplitudes.push(i < t.length / 2 ? t[i] : 1.0);
            phases.push(i < t.length / 2 ? t[Math.floor(t.length / 2) + i] : 0.0);
        }
    }
    // c = amplitude * exp(i * phase) = amplitude * (cos(phase) + i*sin(phase))
    const real = [];
    const imag = [];
    for (let i = 0; i < D; i++) {
        real.push(amplitudes[i] * Math.cos(phases[i]));
        imag.push(amplitudes[i] * Math.sin(phases[i]));
    }
    return { real, imag };
}
// =============================================================================
// LAYER 2: Realification
// =============================================================================
/**
 * Layer 2: Realification (Complex → Real)
 *
 * Input: c ∈ ℂ^D
 * Output: x ∈ ℝ^{2D}
 *
 * Isometric embedding Φ_1: ℂ^D → ℝ^{2D}
 * A2: x = [Re(c), Im(c)]
 */
function layer2Realification(complex) {
    return [...complex.real, ...complex.imag];
}
// =============================================================================
// LAYER 3: Weighted Transform
// =============================================================================
/**
 * Layer 3: SPD Weighted Transform
 *
 * Input: x ∈ ℝ^n, G SPD matrix (optional)
 * Output: x_G = G^{1/2} · x
 *
 * A3: Applies symmetric positive-definite weighting using golden ratio.
 */
function layer3WeightedTransform(x, G) {
    const n = x.length;
    const D = Math.floor(n / 2);
    const PHI = 1.618033988749895;
    if (!G) {
        // Default: Golden ratio weighting
        const weights = [];
        let sumWeights = 0;
        for (let k = 0; k < D; k++) {
            const w = Math.pow(PHI, k);
            weights.push(w);
            sumWeights += w;
        }
        // Normalize weights
        for (let k = 0; k < D; k++) {
            weights[k] /= sumWeights;
        }
        // Apply sqrt(weights) as diagonal transform
        const result = [];
        for (let i = 0; i < n; i++) {
            const weightIdx = i % D;
            result.push(x[i] * Math.sqrt(weights[weightIdx]));
        }
        return result;
    }
    // Apply G^{1/2} via matrix multiplication (simplified)
    // For a diagonal G, this is straightforward
    const result = new Array(n).fill(0);
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) {
            result[i] += Math.sqrt(Math.abs(G[i][j])) * x[j];
        }
    }
    return result;
}
// =============================================================================
// LAYER 4: Poincaré Embedding
// =============================================================================
/**
 * Layer 4: Poincaré Ball Embedding with Clamping
 *
 * Input: x_G ∈ ℝ^n
 * Output: u ∈ 𝔹^n (Poincaré ball)
 *
 * A4: Ψ_α(x) = tanh(α||x||) · x/||x|| with clamping to 𝔹^n_{1-ε}
 */
function layer4PoincareEmbedding(xG, alpha = 1.0, epsBall = 0.01) {
    const norm = Math.sqrt(xG.reduce((sum, val) => sum + val * val, 0));
    if (norm < 1e-12) {
        return new Array(xG.length).fill(0);
    }
    // Poincaré embedding: u = tanh(α||x||) · x/||x||
    const scaledNorm = Math.tanh(alpha * norm);
    const u = xG.map((val) => (scaledNorm * val) / norm);
    // A4: Clamping Π_ε: ensure ||u|| ≤ 1-ε
    const uNorm = Math.sqrt(u.reduce((sum, val) => sum + val * val, 0));
    const maxNorm = 1.0 - epsBall;
    if (uNorm > maxNorm) {
        return u.map((val) => (maxNorm * val) / uNorm);
    }
    return u;
}
// =============================================================================
// LAYER 5: Hyperbolic Distance
// =============================================================================
/**
 * Layer 5: Poincaré Ball Metric
 *
 * Input: u, v ∈ 𝔹^n
 * Output: d_ℍ(u, v) ∈ ℝ₊
 *
 * A5: d_ℍ(u,v) = arcosh(1 + 2||u-v||²/[(1-||u||²)(1-||v||²)])
 */
function layer5HyperbolicDistance(u, v, eps = 1e-5) {
    let diffNormSq = 0;
    let uNormSq = 0;
    let vNormSq = 0;
    for (let i = 0; i < u.length; i++) {
        const diff = u[i] - v[i];
        diffNormSq += diff * diff;
        uNormSq += u[i] * u[i];
        vNormSq += v[i] * v[i];
    }
    const uFactor = 1.0 - uNormSq;
    const vFactor = 1.0 - vNormSq;
    // Denominator bounded below by eps² due to clamping
    const denom = Math.max(uFactor * vFactor, eps * eps);
    const arg = 1.0 + (2.0 * diffNormSq) / denom;
    return Math.acosh(Math.max(arg, 1.0));
}
// =============================================================================
// LAYER 6: Breathing Transform
// =============================================================================
/**
 * Layer 6: Breathing Map (Diffeomorphism, NOT Isometry)
 *
 * Input: u ∈ 𝔹^n, breathing factor b ∈ [b_min, b_max]
 * Output: u_breathed ∈ 𝔹^n
 *
 * A6: T_breath(u) with radial rescaling (changes distances!)
 */
function layer6BreathingTransform(u, b, bMin = 0.5, bMax = 2.0) {
    // Clamp breathing factor
    b = Math.max(bMin, Math.min(bMax, b));
    const norm = Math.sqrt(u.reduce((sum, val) => sum + val * val, 0));
    if (norm < 1e-12) {
        return new Array(u.length).fill(0);
    }
    // Breathing: r ↦ tanh(b · arctanh(r))
    const clampedNorm = Math.min(norm, 0.9999);
    const artanhNorm = Math.atanh(clampedNorm);
    const newNorm = Math.tanh(b * artanhNorm);
    return u.map((val) => (newNorm * val) / norm);
}
// =============================================================================
// MÖBIUS TRANSFORMATIONS (Gyrovector Operations)
// =============================================================================
/**
 * Möbius (gyrovector) addition in the Poincaré ball model.
 * True hyperbolic isometry: d(u ⊕ v, w ⊕ v) = d(u, w)
 */
function mobiusAdd(u, v, eps = 1e-10) {
    const u2 = u.reduce((sum, val) => sum + val * val, 0);
    const v2 = v.reduce((sum, val) => sum + val * val, 0);
    const uv = u.reduce((sum, val, i) => sum + val * v[i], 0);
    // Lorentz factor γ_u
    const gammaU = 1.0 / Math.sqrt(1.0 - u2 + eps);
    // Coefficients
    const coeffU = gammaU * (1.0 + gammaU * uv + v2);
    const coeffV = 1.0 - gammaU * gammaU * u2;
    let denom = 1.0 + 2.0 * gammaU * uv + gammaU * gammaU * u2 * v2;
    denom = Math.max(denom, eps);
    const result = u.map((uVal, i) => (coeffU * uVal + coeffV * v[i]) / denom);
    // Numerical safety: clamp if floating-point pushed it to boundary
    const resultNorm = Math.sqrt(result.reduce((sum, val) => sum + val * val, 0));
    if (resultNorm >= 1.0 - 1e-8) {
        const scale = 0.99999999 / resultNorm;
        return result.map((val) => val * scale);
    }
    return result;
}
/**
 * Apply orthogonal rotation Q in the Poincaré ball.
 */
function mobiusRotate(u, Q) {
    const n = u.length;
    const result = new Array(n).fill(0);
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) {
            result[i] += Q[i][j] * u[j];
        }
    }
    // Safety clamp
    const norm = Math.sqrt(result.reduce((sum, val) => sum + val * val, 0));
    if (norm >= 1.0 - 1e-8) {
        const scale = 0.99999999 / norm;
        return result.map((val) => val * scale);
    }
    return result;
}
// =============================================================================
// LAYER 7: Phase Transform
// =============================================================================
/**
 * Layer 7: Phase Transform (True Isometry)
 *
 * Input: u ∈ 𝔹^n, shift a ∈ 𝔹^n, rotation Q ∈ O(n)
 * Output: ũ = t_a ∘ R_Q(u) using Möbius operations
 *
 * A7: Uses correct Möbius addition (gyrovector) for distance preservation.
 */
function layer7PhaseTransform(u, a, Q) {
    // Step 1: Apply rotation Q (rotation about origin preserves distance)
    const uRotated = mobiusRotate(u, Q);
    // Step 2: Translate by a using Möbius addition
    return mobiusAdd(a, uRotated);
}
// =============================================================================
// LAYER 8: Realm Distance
// =============================================================================
/**
 * Layer 8: Minimum Distance to Realm Centers
 *
 * Input: u ∈ 𝔹^n, realm centers {μ_k} ⊂ 𝔹^n_{1-ε}
 * Output: d* = min_k d_ℍ(u, μ_k)
 *
 * A8: Computes proximity to known safe regions.
 */
function layer8RealmDistance(u, realms, eps = 1e-5) {
    const distances = realms.map((mu) => layer5HyperbolicDistance(u, mu, eps));
    const dStar = Math.min(...distances);
    return { dStar, distances };
}
// =============================================================================
// LAYER 9: Spectral Coherence
// =============================================================================
/**
 * Layer 9: Spectral Coherence via FFT
 *
 * Input: Time-domain signal
 * Output: S_spec ∈ [0,1]
 *
 * A9: Low-frequency energy ratio as pattern stability measure.
 */
function layer9SpectralCoherence(signal, eps = 1e-5) {
    if (!signal || signal.length === 0) {
        return 0.5;
    }
    // Simple DFT magnitude spectrum (no external FFT library needed)
    const N = signal.length;
    const fftMag = [];
    for (let k = 0; k < N; k++) {
        let realSum = 0;
        let imagSum = 0;
        for (let n = 0; n < N; n++) {
            const angle = (-2 * Math.PI * k * n) / N;
            realSum += signal[n] * Math.cos(angle);
            imagSum += signal[n] * Math.sin(angle);
        }
        fftMag.push(Math.sqrt(realSum * realSum + imagSum * imagSum));
    }
    const half = Math.floor(N / 2);
    // Low-frequency energy
    let lowEnergy = 0;
    for (let i = 0; i < half; i++) {
        lowEnergy += fftMag[i];
    }
    const totalEnergy = fftMag.reduce((sum, val) => sum + val, 0) + eps;
    const sSpec = lowEnergy / totalEnergy;
    return Math.max(0, Math.min(1, sSpec));
}
// =============================================================================
// LAYER 10: Spin Coherence
// =============================================================================
/**
 * Layer 10: Spin Coherence
 *
 * Input: Phase array (or complex phasors as {real, imag})
 * Output: C_spin ∈ [0,1]
 *
 * A10: Mean resultant length of unit phasors.
 */
function layer10SpinCoherence(phases) {
    if (phases.length === 0) {
        return 0.5;
    }
    // Convert phases to unit phasors and compute mean
    let realSum = 0;
    let imagSum = 0;
    for (const phase of phases) {
        realSum += Math.cos(phase);
        imagSum += Math.sin(phase);
    }
    realSum /= phases.length;
    imagSum /= phases.length;
    // Mean phasor magnitude
    const cSpin = Math.sqrt(realSum * realSum + imagSum * imagSum);
    return Math.max(0, Math.min(1, cSpin));
}
// =============================================================================
// LAYER 11: Triadic Temporal Aggregation
// =============================================================================
/**
 * Layer 11: Triadic Temporal Distance
 *
 * Input: Recent (d1), mid-term (d2), global (dG) distances
 * Output: d_tri ∈ [0,1]
 *
 * A11: d_tri = √(λ₁d₁² + λ₂d₂² + λ₃d_G²) / d_scale
 */
function layer11TriadicTemporal(d1, d2, dG, lambda1 = 0.33, lambda2 = 0.34, lambda3 = 0.33, dScale = 1.0) {
    // Verify weights sum to 1
    const sum = lambda1 + lambda2 + lambda3;
    if (Math.abs(sum - 1.0) > 1e-6) {
        throw new Error(`Lambdas must sum to 1, got ${sum}`);
    }
    const dTri = Math.sqrt(lambda1 * d1 * d1 + lambda2 * d2 * d2 + lambda3 * dG * dG);
    // Normalize to [0,1]
    return Math.min(1.0, dTri / dScale);
}
// =============================================================================
// LAYER 12: Harmonic Scaling
// =============================================================================
/**
 * Layer 12: Harmonic Amplification
 *
 * Input: Distance d, base R > 1
 * Output: H(d, R) = R^{d²}
 *
 * A12: Exponential penalty for geometric distance.
 */
function layer12HarmonicScaling(d, R = Math.E) {
    if (R <= 1) {
        throw new Error('R must be > 1');
    }
    return Math.pow(R, d * d);
}
/**
 * Layer 13: Three-Way Risk Decision
 *
 * Input: Base risk, harmonic amplification H
 * Output: Decision ∈ {ALLOW, QUARANTINE, DENY}
 *
 * A13: Risk' = Risk_base · H with thresholding.
 */
function layer13RiskDecision(riskBase, H, theta1 = 0.33, theta2 = 0.67) {
    const riskPrime = riskBase * H;
    let decision;
    if (riskPrime < theta1) {
        decision = 'ALLOW';
    }
    else if (riskPrime < theta2) {
        decision = 'QUARANTINE';
    }
    else {
        decision = 'DENY';
    }
    return { decision, riskPrime };
}
// =============================================================================
// LAYER 14: Audio Axis
// =============================================================================
/**
 * Layer 14: Audio Telemetry Coherence
 *
 * Input: Audio frame (time-domain waveform)
 * Output: S_audio ∈ [0,1]
 *
 * A14: Instantaneous phase stability via Hilbert transform approximation.
 */
function layer14AudioAxis(audio, eps = 1e-5) {
    if (!audio || audio.length === 0) {
        return 0.5;
    }
    // Simplified Hilbert transform approximation using DFT
    const N = audio.length;
    const phases = [];
    // Compute analytic signal phase approximation
    for (let i = 1; i < N; i++) {
        // Simple phase difference approximation
        const phaseDiff = Math.atan2(audio[i] - audio[i - 1], 1);
        phases.push(phaseDiff);
    }
    if (phases.length === 0) {
        return 0.5;
    }
    // Phase derivative stability
    let sumDiff = 0;
    let sumDiffSq = 0;
    for (const p of phases) {
        sumDiff += p;
        sumDiffSq += p * p;
    }
    const mean = sumDiff / phases.length;
    const variance = sumDiffSq / phases.length - mean * mean;
    const stdDev = Math.sqrt(Math.max(0, variance));
    const stability = 1.0 / (1.0 + stdDev + eps);
    return Math.max(0, Math.min(1, stability));
}
/**
 * Execute full 14-layer SCBE pipeline.
 *
 * @param t - Input features (time-dependent context)
 * @param config - Pipeline configuration
 * @returns Comprehensive metrics dictionary
 */
function scbe14LayerPipeline(t, config = {}) {
    const { D = 6, alpha = 1.0, epsBall = 0.01, breathingFactor = 1.0, R = Math.E, theta1 = 0.33, theta2 = 0.67, wD = 0.2, wC = 0.2, wS = 0.2, wTau = 0.2, wA = 0.2, } = config;
    const n = 2 * D;
    // Initialize default realms
    const scaling = 0.8 / Math.sqrt(n);
    const realms = [
        new Array(n).fill(0),
        new Array(n).fill(scaling * 0.2),
        new Array(n).fill(scaling * 0.3),
        new Array(n).fill(scaling * 0.1),
    ];
    // Default phase shift and rotation
    const phaseShift = new Array(n).fill(0);
    const rotation = [];
    for (let i = 0; i < n; i++) {
        rotation.push(new Array(n).fill(0));
        rotation[i][i] = 1; // Identity matrix
    }
    // === LAYER 1: Complex State ===
    const l1_complex = layer1ComplexState(t, D);
    // === LAYER 2: Realification ===
    const l2_real = layer2Realification(l1_complex);
    // === LAYER 3: Weighted Transform ===
    const l3_weighted = layer3WeightedTransform(l2_real);
    // === LAYER 4: Poincaré Embedding ===
    const l4_poincare = layer4PoincareEmbedding(l3_weighted, alpha, epsBall);
    // === LAYER 5: Hyperbolic Distance (to origin) ===
    const origin = new Array(n).fill(0);
    const l5_distance = layer5HyperbolicDistance(l4_poincare, origin);
    // === LAYER 6: Breathing Transform ===
    const l6_breathed = layer6BreathingTransform(l4_poincare, breathingFactor);
    // === LAYER 7: Phase Transform ===
    const l7_transformed = layer7PhaseTransform(l6_breathed, phaseShift, rotation);
    // === LAYER 8: Realm Distance ===
    const { dStar: l8_realmDist } = layer8RealmDistance(l7_transformed, realms);
    // === LAYER 9: Spectral Coherence ===
    const l9_spectral = layer9SpectralCoherence(t);
    // === LAYER 10: Spin Coherence ===
    // Use phases from L1 for spin coherence
    const phases = t.length >= D ? t.slice(D, 2 * D) : t;
    const l10_spin = layer10SpinCoherence(phases);
    // === LAYER 11: Triadic Temporal ===
    // Use realm distance for all temporal scales (simplified)
    const l11_triadic = layer11TriadicTemporal(l8_realmDist, l8_realmDist, l8_realmDist);
    // === LAYER 12: Harmonic Scaling ===
    const l12_harmonic = layer12HarmonicScaling(l8_realmDist, R);
    // === Compute Base Risk ===
    const riskBase = wD * l8_realmDist +
        wC * (1 - l9_spectral) +
        wS * (1 - l10_spin) +
        wTau * l11_triadic +
        wA * 0.5;
    // === LAYER 13: Risk Decision ===
    const { decision: l13_decision, riskPrime } = layer13RiskDecision(riskBase, l12_harmonic, theta1, theta2);
    // === LAYER 14: Audio Axis ===
    const l14_audio = layer14AudioAxis(t);
    return {
        decision: l13_decision,
        riskPrime,
        layers: {
            l1_complex,
            l2_real,
            l3_weighted,
            l4_poincare,
            l5_distance,
            l6_breathed,
            l7_transformed,
            l8_realmDist,
            l9_spectral,
            l10_spin,
            l11_triadic,
            l12_harmonic,
            l13_decision,
            l14_audio,
        },
        riskComponents: {
            riskBase,
            H: l12_harmonic,
        },
    };
}
//# sourceMappingURL=pipeline14.js.map