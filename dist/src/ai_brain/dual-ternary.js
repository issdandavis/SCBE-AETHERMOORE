"use strict";
/**
 * @file dual-ternary.ts
 * @module ai_brain/dual-ternary
 * @layer Layer 9, Layer 10, Layer 12, Layer 14
 * @component Dual Ternary Encoding with Full Negative State Flux
 * @version 1.0.0
 * @since 2026-02-08
 *
 * Implements dual ternary encoding with full negative state flux
 * for spectral governance and fractal-dimensional security.
 *
 * Standard binary: {0, 1} → amplitude only
 * Negative binary: {-1, 0, 1} → amplitude + phase
 * Dual ternary: {-1, 0, 1} × {-1, 0, 1} → 9 states
 *   with FULL negative state flux in BOTH dimensions
 *
 * Full State Space (3×3 = 9 states):
 *   (-1, -1)  (-1, 0)  (-1, 1)   ← negative coherence row
 *   ( 0, -1)  ( 0, 0)  ( 0, 1)   ← neutral row
 *   ( 1, -1)  ( 1, 0)  ( 1, 1)   ← positive coherence row
 *
 * Key properties:
 * - Constructive interference: (+1, +1) = energy +2
 * - Destructive interference: (+1, -1) = energy 0
 * - Negative resonance: (-1, -1) = energy +2 (both inverted)
 * - Ground state: (0, 0) = energy 0
 *
 * With recursive mirroring, the fractal dimension becomes non-integer:
 *   D ≈ log(9)/log(3) + fractal_component ≈ 2 + sign_entropy
 *
 * The Audio Axis (Layer 14) detects phase inversions as security anomalies.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.DualTernarySystem = exports.FULL_STATE_SPACE = exports.DEFAULT_DUAL_TERNARY_CONFIG = void 0;
exports.computeStateEnergy = computeStateEnergy;
exports.stateIndex = stateIndex;
exports.stateFromIndex = stateFromIndex;
exports.transition = transition;
exports.encodeToDualTernary = encodeToDualTernary;
exports.encodeSequence = encodeSequence;
exports.computeSpectrum = computeSpectrum;
exports.estimateFractalDimension = estimateFractalDimension;
const types_js_1 = require("./types.js");
exports.DEFAULT_DUAL_TERNARY_CONFIG = {
    minSequenceLength: 8,
    phaseAnomalyThreshold: 0.7,
    fractalDeviationThreshold: 0.5,
    mirrorDepth: 4,
    entropyNormalization: Math.log(3), // log₃ normalization
};
// ═══════════════════════════════════════════════════════════════
// Full 9-State Space
// ═══════════════════════════════════════════════════════════════
/**
 * All 9 states in the full dual ternary space.
 * Enumerated for complete coverage.
 */
exports.FULL_STATE_SPACE = [
    { primary: -1, mirror: -1 },
    { primary: -1, mirror: 0 },
    { primary: -1, mirror: 1 },
    { primary: 0, mirror: -1 },
    { primary: 0, mirror: 0 },
    { primary: 0, mirror: 1 },
    { primary: 1, mirror: -1 },
    { primary: 1, mirror: 0 },
    { primary: 1, mirror: 1 },
];
// ═══════════════════════════════════════════════════════════════
// State Energy & Phase Classification
// ═══════════════════════════════════════════════════════════════
/**
 * Compute the energy of a dual ternary state.
 *
 * E(p, m) = p² + m² + p × m
 *
 * Energy landscape:
 *   E(-1,-1) = 1 + 1 + 1 = 3  (negative coherence — both inverted)
 *   E(-1, 1) = 1 + 1 - 1 = 1  (destructive — phase opposition)
 *   E( 0, 0) = 0               (ground state)
 *   E( 1, 1) = 1 + 1 + 1 = 3  (constructive — positive coherence)
 *   E( 1,-1) = 1 + 1 - 1 = 1  (destructive — mirror opposition)
 */
function computeStateEnergy(state) {
    const { primary: p, mirror: m } = state;
    const primaryEnergy = p * p;
    const mirrorEnergy = m * m;
    const interaction = p * m;
    const energy = primaryEnergy + mirrorEnergy + interaction;
    let phase;
    if (p > 0 && m > 0) {
        phase = 'constructive';
    }
    else if (p < 0 && m < 0) {
        phase = 'negative_resonance';
    }
    else if ((p > 0 && m < 0) || (p < 0 && m > 0)) {
        phase = 'destructive';
    }
    else {
        phase = 'neutral';
    }
    return { energy, primaryEnergy, mirrorEnergy, interaction, phase };
}
/**
 * Get the state index (0-8) for a dual ternary state.
 * Maps (primary, mirror) to a unique index.
 */
function stateIndex(state) {
    return (state.primary + 1) * 3 + (state.mirror + 1);
}
/**
 * Reconstruct a dual ternary state from its index.
 */
function stateFromIndex(index) {
    const clamped = Math.max(0, Math.min(8, Math.floor(index)));
    const primary = (Math.floor(clamped / 3) - 1);
    const mirror = ((clamped % 3) - 1);
    return { primary, mirror };
}
// ═══════════════════════════════════════════════════════════════
// State Transitions
// ═══════════════════════════════════════════════════════════════
/**
 * Transition from one dual ternary state to another.
 * Both primary and mirror can independently change by {-1, 0, +1}.
 *
 * The clip function ensures we stay within {-1, 0, 1}.
 */
function transition(current, deltaP, deltaM) {
    return {
        primary: clip(current.primary + deltaP),
        mirror: clip(current.mirror + deltaM),
    };
}
/**
 * Clip a value to the ternary set {-1, 0, 1}.
 */
function clip(value) {
    if (value >= 1)
        return 1;
    if (value <= -1)
        return -1;
    return 0;
}
// ═══════════════════════════════════════════════════════════════
// Encoding: Continuous → Dual Ternary
// ═══════════════════════════════════════════════════════════════
/**
 * Encode a continuous value into a dual ternary state.
 *
 * The primary channel captures amplitude (sign and magnitude threshold).
 * The mirror channel captures phase (derivative or complementary signal).
 *
 * @param amplitude - Primary signal value (any real number)
 * @param phase - Phase/derivative signal (any real number)
 * @param threshold - Threshold for non-zero quantization (default: 0.33)
 */
function encodeToDualTernary(amplitude, phase, threshold = 0.33) {
    return {
        primary: quantize(amplitude, threshold),
        mirror: quantize(phase, threshold),
    };
}
/**
 * Quantize a continuous value to ternary.
 */
function quantize(value, threshold) {
    if (value > threshold)
        return 1;
    if (value < -threshold)
        return -1;
    return 0;
}
/**
 * Encode a sequence of 21D brain state values into dual ternary.
 *
 * Uses consecutive pairs (x[i], x[i+1]) as (amplitude, phase),
 * or (value, derivative) when derivatives are available.
 *
 * @param values - Array of continuous values
 * @param threshold - Quantization threshold
 * @returns Array of dual ternary states
 */
function encodeSequence(values, threshold = 0.33) {
    const states = [];
    for (let i = 0; i < values.length - 1; i += 2) {
        states.push(encodeToDualTernary(values[i], values[i + 1], threshold));
    }
    // Handle odd length
    if (values.length % 2 === 1) {
        states.push(encodeToDualTernary(values[values.length - 1], 0, threshold));
    }
    return states;
}
// ═══════════════════════════════════════════════════════════════
// Spectral Analysis of Dual Ternary Sequences
// ═══════════════════════════════════════════════════════════════
/**
 * Compute the spectral signature of a dual ternary sequence.
 *
 * Performs spectral decomposition on both the primary and mirror
 * channels independently, then computes cross-correlation.
 *
 * The 9-fold symmetry energy measures how evenly the states
 * are distributed across the 9-state space.
 *
 * Phase anomaly detection: Normal traffic produces balanced spectra.
 * Attack traffic shows sign bias (uniform signs → anomalous coherence).
 */
function computeSpectrum(sequence, config = exports.DEFAULT_DUAL_TERNARY_CONFIG) {
    if (sequence.length < config.minSequenceLength) {
        return {
            primaryMagnitudes: [],
            mirrorMagnitudes: [],
            crossCorrelation: [],
            ninefoldEnergy: 0,
            coherence: 0,
            phaseAnomaly: 0,
        };
    }
    // Pad to power of 2
    const n = nextPow2(sequence.length);
    const primarySignal = new Array(n).fill(0);
    const mirrorSignal = new Array(n).fill(0);
    for (let i = 0; i < sequence.length; i++) {
        primarySignal[i] = sequence[i].primary;
        mirrorSignal[i] = sequence[i].mirror;
    }
    // DFT of both channels
    const primaryDFT = simpleDFT(primarySignal);
    const mirrorDFT = simpleDFT(mirrorSignal);
    // Magnitudes
    const primaryMagnitudes = primaryDFT.map((c) => Math.sqrt(c.re * c.re + c.im * c.im));
    const mirrorMagnitudes = mirrorDFT.map((c) => Math.sqrt(c.re * c.re + c.im * c.im));
    // Cross-correlation: conj(P) × M
    const crossCorrelation = primaryDFT.map((p, i) => {
        const m = mirrorDFT[i];
        return p.re * m.re + p.im * m.im; // Real part of P* × M
    });
    // 9-fold symmetry energy
    const stateHistogram = new Array(9).fill(0);
    for (const s of sequence) {
        stateHistogram[stateIndex(s)]++;
    }
    const ideal = sequence.length / 9;
    let chiSquared = 0;
    for (const count of stateHistogram) {
        const diff = count - ideal;
        chiSquared += (diff * diff) / Math.max(ideal, types_js_1.BRAIN_EPSILON);
    }
    // Normalize: 0 = perfect distribution, 1 = maximally biased
    const ninefoldEnergy = 1 - 1 / (1 + chiSquared / sequence.length);
    // Spectral coherence: ratio of primary-mirror correlation to total energy
    const totalPrimaryEnergy = primaryMagnitudes.reduce((s, v) => s + v * v, 0);
    const totalMirrorEnergy = mirrorMagnitudes.reduce((s, v) => s + v * v, 0);
    const totalCross = crossCorrelation.reduce((s, v) => s + Math.abs(v), 0);
    const totalEnergy = totalPrimaryEnergy + totalMirrorEnergy;
    const coherence = totalEnergy > types_js_1.BRAIN_EPSILON
        ? totalCross / (totalEnergy + types_js_1.BRAIN_EPSILON)
        : 0;
    // Phase anomaly: detect sign bias
    // Normal: balanced positive/negative → low anomaly
    // Attack: biased signs → high anomaly
    const phaseAnomaly = computePhaseAnomaly(sequence);
    return {
        primaryMagnitudes,
        mirrorMagnitudes,
        crossCorrelation,
        ninefoldEnergy,
        coherence: Math.min(1, coherence),
        phaseAnomaly,
    };
}
/**
 * Detect phase anomalies from sign distribution bias.
 *
 * Normal traffic: balanced mix of all 9 states
 * Attack traffic: concentrated in certain states (e.g., all (+1,+1))
 *
 * Uses Shannon entropy of the state distribution, normalized
 * to [0, 1] where 0 = maximum entropy (uniform) and 1 = zero entropy.
 */
function computePhaseAnomaly(sequence) {
    if (sequence.length === 0)
        return 0;
    const histogram = new Array(9).fill(0);
    for (const s of sequence) {
        histogram[stateIndex(s)]++;
    }
    // Shannon entropy
    let entropy = 0;
    for (const count of histogram) {
        if (count > 0) {
            const p = count / sequence.length;
            entropy -= p * Math.log(p);
        }
    }
    // Maximum entropy for 9 states = log(9)
    const maxEntropy = Math.log(9);
    const normalizedEntropy = maxEntropy > 0 ? entropy / maxEntropy : 0;
    // Anomaly = 1 - normalized entropy (low entropy = high anomaly)
    return 1 - normalizedEntropy;
}
// ═══════════════════════════════════════════════════════════════
// Fractal Dimension Analysis
// ═══════════════════════════════════════════════════════════════
/**
 * Estimate the fractal dimension of a dual ternary state sequence.
 *
 * For standard dual ternary: D_base = log(9)/log(3) = 2
 * With recursive mirroring and sign entropy:
 *   D = D_base + fractal_component
 *
 * The fractal component emerges from:
 * - Sign flip self-similarity (recursive structure)
 * - Mirror symmetry breaking
 * - Phase interference patterns
 */
function estimateFractalDimension(sequence, config = exports.DEFAULT_DUAL_TERNARY_CONFIG) {
    const baseDimension = Math.log(9) / Math.log(3); // Always 2.0
    if (sequence.length < 4) {
        return {
            baseDimension,
            signEntropy: 0,
            hausdorffDimension: baseDimension,
            symmetryBreaking: 0,
            selfSimilarity: 0,
        };
    }
    // Sign entropy: how much information the signs carry
    const signEntropy = computeSignEntropy(sequence, config);
    // Symmetry breaking: measure how much primary ≠ mirror distribution
    const symmetryBreaking = computeSymmetryBreaking(sequence);
    // Self-similarity: compare statistical properties at different scales
    const selfSimilarity = computeSelfSimilarity(sequence, config);
    // Hausdorff dimension estimate
    // D = base + sign_entropy_contribution + interaction_term
    const interactionTerm = selfSimilarity * symmetryBreaking * Math.log(types_js_1.PHI) / Math.log(3);
    const hausdorffDimension = baseDimension + signEntropy + interactionTerm;
    return {
        baseDimension,
        signEntropy,
        hausdorffDimension,
        symmetryBreaking,
        selfSimilarity,
    };
}
/**
 * Compute sign entropy contribution to fractal dimension.
 *
 * Measures how much information is carried by the sign structure
 * (positive vs negative states). Higher sign entropy → higher
 * effective dimension.
 */
function computeSignEntropy(sequence, config) {
    // Count sign patterns: (signP, signM) where sign ∈ {-, 0, +}
    const signPatterns = new Array(9).fill(0);
    for (const s of sequence) {
        const signP = Math.sign(s.primary) + 1; // 0, 1, 2
        const signM = Math.sign(s.mirror) + 1;
        signPatterns[signP * 3 + signM]++;
    }
    let entropy = 0;
    for (const count of signPatterns) {
        if (count > 0) {
            const p = count / sequence.length;
            entropy -= p * Math.log(p);
        }
    }
    // Normalize by log(9) and scale by normalization factor
    return (entropy / (config.entropyNormalization * 2)) * 0.438; // log₃(φ) ≈ 0.438
}
/**
 * Compute mirror symmetry breaking.
 *
 * Measures how different the primary and mirror distributions are.
 * Perfect symmetry = 0, complete asymmetry = 1.
 */
function computeSymmetryBreaking(sequence) {
    const primaryHist = [0, 0, 0]; // {-1, 0, 1}
    const mirrorHist = [0, 0, 0];
    for (const s of sequence) {
        primaryHist[s.primary + 1]++;
        mirrorHist[s.mirror + 1]++;
    }
    // Jensen-Shannon divergence between primary and mirror distributions
    let divergence = 0;
    for (let i = 0; i < 3; i++) {
        const pP = primaryHist[i] / sequence.length;
        const pM = mirrorHist[i] / sequence.length;
        const mean = (pP + pM) / 2;
        if (pP > 0 && mean > 0) {
            divergence += 0.5 * pP * Math.log(pP / mean);
        }
        if (pM > 0 && mean > 0) {
            divergence += 0.5 * pM * Math.log(pM / mean);
        }
    }
    // Normalize to [0, 1] — max JSD for ternary is log(2)
    return Math.min(1, divergence / Math.log(2));
}
/**
 * Compute self-similarity across scales.
 *
 * Compares energy distribution at successive halvings of the sequence.
 * True fractal patterns maintain similar statistics at all scales.
 */
function computeSelfSimilarity(sequence, config) {
    const maxDepth = Math.min(config.mirrorDepth, Math.floor(Math.log2(sequence.length)));
    if (maxDepth < 2)
        return 0;
    const energyAtScale = [];
    for (let depth = 0; depth < maxDepth; depth++) {
        const step = 1 << depth; // 1, 2, 4, 8...
        let totalEnergy = 0;
        let count = 0;
        for (let i = 0; i < sequence.length; i += step) {
            const e = computeStateEnergy(sequence[i]);
            totalEnergy += e.energy;
            count++;
        }
        energyAtScale.push(count > 0 ? totalEnergy / count : 0);
    }
    // Correlation between consecutive scales
    let totalCorrelation = 0;
    let pairs = 0;
    for (let i = 0; i < energyAtScale.length - 1; i++) {
        const maxE = Math.max(energyAtScale[i], energyAtScale[i + 1]);
        if (maxE > types_js_1.BRAIN_EPSILON) {
            const minE = Math.min(energyAtScale[i], energyAtScale[i + 1]);
            totalCorrelation += minE / maxE;
            pairs++;
        }
    }
    return pairs > 0 ? totalCorrelation / pairs : 0;
}
// ═══════════════════════════════════════════════════════════════
// Dual Ternary Encoder/Analyzer System
// ═══════════════════════════════════════════════════════════════
/**
 * Dual Ternary Encoding System.
 *
 * Manages encoding of brain state vectors into dual ternary space,
 * spectral analysis of state sequences, and fractal dimension
 * monitoring for security anomaly detection.
 */
class DualTernarySystem {
    config;
    history = [];
    stepCounter = 0;
    constructor(config = {}) {
        this.config = { ...exports.DEFAULT_DUAL_TERNARY_CONFIG, ...config };
    }
    /**
     * Encode a 21D brain state into dual ternary representation.
     *
     * Pairs consecutive dimensions as (amplitude, phase):
     *   dims[0,1] → state[0], dims[2,3] → state[1], etc.
     *
     * This captures both the value and its contextual derivative
     * in each dual ternary symbol.
     */
    encode(state21D, threshold = 0.33) {
        this.stepCounter++;
        const encoded = encodeSequence(state21D, threshold);
        // Append to history
        this.history.push(...encoded);
        // Trim history to reasonable size
        if (this.history.length > 1024) {
            this.history = this.history.slice(-1024);
        }
        return encoded;
    }
    /**
     * Analyze the current state history for spectral anomalies.
     */
    analyzeSpectrum() {
        return computeSpectrum(this.history, this.config);
    }
    /**
     * Estimate the fractal dimension of the current history.
     */
    analyzeFractalDimension() {
        return estimateFractalDimension(this.history, this.config);
    }
    /**
     * Full security analysis: spectrum + fractal + threat assessment.
     *
     * @returns Combined analysis with anomaly flags
     */
    fullAnalysis() {
        const spectrum = this.analyzeSpectrum();
        const fractal = this.analyzeFractalDimension();
        const phaseAnomalyDetected = spectrum.phaseAnomaly >= this.config.phaseAnomalyThreshold;
        // Fractal anomaly: dimension deviates too far from expected
        const expectedDimension = 2.0; // log(9)/log(3)
        const fractalDeviation = Math.abs(fractal.hausdorffDimension - expectedDimension);
        const fractalAnomalyDetected = fractalDeviation > this.config.fractalDeviationThreshold;
        // Combined threat score
        const threatScore = Math.min(1, spectrum.phaseAnomaly * 0.4 +
            spectrum.ninefoldEnergy * 0.3 +
            (fractalDeviation / 2) * 0.3);
        return {
            spectrum,
            fractal,
            phaseAnomalyDetected,
            fractalAnomalyDetected,
            threatScore,
        };
    }
    /**
     * Convert dual ternary state to a signed tensor product representation.
     *
     * Returns a 3×3 matrix where entry (i,j) represents the
     * contribution of the (primary=i-1, mirror=j-1) state.
     */
    static toTensorProduct(state) {
        const tensor = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ];
        const pi = state.primary + 1; // 0, 1, 2
        const mi = state.mirror + 1;
        tensor[pi][mi] = 1;
        return tensor;
    }
    /**
     * Compute the signed tensor product sum over a sequence.
     * Shows the distribution across the 3×3 state space.
     */
    static tensorHistogram(sequence) {
        const tensor = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ];
        for (const s of sequence) {
            tensor[s.primary + 1][s.mirror + 1]++;
        }
        return tensor;
    }
    /** Get the history length */
    getHistoryLength() {
        return this.history.length;
    }
    /** Get the step counter */
    getStep() {
        return this.stepCounter;
    }
    /** Get the raw history */
    getHistory() {
        return this.history;
    }
    /** Reset all state */
    reset() {
        this.history = [];
        this.stepCounter = 0;
    }
}
exports.DualTernarySystem = DualTernarySystem;
/**
 * Simple DFT for small ternary sequences.
 * Uses direct O(N²) computation, suitable for the short
 * sequences typical in dual ternary analysis.
 */
function simpleDFT(signal) {
    const N = signal.length;
    const result = [];
    for (let k = 0; k < N; k++) {
        let re = 0;
        let im = 0;
        for (let n = 0; n < N; n++) {
            const angle = (-2 * Math.PI * k * n) / N;
            re += signal[n] * Math.cos(angle);
            im += signal[n] * Math.sin(angle);
        }
        result.push({ re, im });
    }
    return result;
}
/**
 * Next power of 2 >= n.
 */
function nextPow2(n) {
    let p = 1;
    while (p < n)
        p <<= 1;
    return p;
}
//# sourceMappingURL=dual-ternary.js.map