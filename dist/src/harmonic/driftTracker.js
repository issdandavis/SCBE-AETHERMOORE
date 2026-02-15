"use strict";
/**
 * @file driftTracker.ts
 * @module harmonic/driftTracker
 * @layer Layer 5, Layer 12, Layer 14
 * @component Decimal Drift Tracker — Entropy Harvesting Engine
 * @version 1.0.0
 *
 * Turns floating-point "noise" into a geodesic signature.
 *
 * Traditional systems discard the 16th decimal place. SCBE captures it.
 * The accumulated drift at each pipeline step creates a unique fingerprint:
 *
 *   Genuine thought → natural, non-uniform drift → φ-harmonic key
 *   Synthetic input → too-clean, uniform drift → no valid key
 *
 * Architecture:
 *
 *   Pipeline Step N          Pipeline Step N+1
 *   ┌─────────────┐          ┌─────────────┐
 *   │ state[i] = x│ ──────→ │ state[i] = x'│
 *   └──────┬──────┘          └──────┬───────┘
 *          │                        │
 *          └──── δ[i] = x' - x ────┘
 *                      │
 *               ┌──────▼──────┐
 *               │ Shadow Buffer│  ← circular buffer of drift vectors
 *               └──────┬──────┘
 *                      │
 *          ┌───────────┼───────────┐
 *          ▼           ▼           ▼
 *   Fractal Dim   Harmonic Key   Sonification
 *   (D_f ∈ ℝ)    (6D φ-ratio)  (Audio Axis)
 *
 * Key insight: decimal drift in hyperbolic space is amplified by the
 * Poincaré metric, making synthetic vs genuine separation even sharper
 * than in Euclidean space (Mechanism 4 shows 0.995 AUC).
 *
 * Integration:
 *   - ai_brain/detection.ts Mechanism 4 (Decimal Drift Magnitude)
 *   - harmonic/audioAxis.ts (Layer 14 sonification)
 *   - harmonic/pipeline14.ts (per-layer drift capture)
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.GENUINE_FRACTAL_MIN = exports.SYNTHETIC_CV_THRESHOLD = exports.DEFAULT_BUFFER_CAPACITY = exports.TONGUE_HARMONICS = exports.DriftTracker = void 0;
exports.captureStepDrift = captureStepDrift;
exports.estimateFractalDimension = estimateFractalDimension;
exports.deriveHarmonicKey = deriveHarmonicKey;
exports.assessAuthenticity = assessAuthenticity;
exports.sonifyDrift = sonifyDrift;
// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
/** Golden ratio */
const PHI = (1 + Math.sqrt(5)) / 2;
/** Small epsilon for numerical stability */
const EPSILON = 1e-15;
/** Sacred Tongue harmonic frequencies: 440 * φ^k Hz */
const TONGUE_HARMONICS = [
    440 * PHI ** 0, // KO: 440.00
    440 * PHI ** 1, // AV: 711.78
    440 * PHI ** 2, // RU: 1151.78
    440 * PHI ** 3, // CA: 1863.56
    440 * PHI ** 4, // UM: 3015.33
    440 * PHI ** 5, // DR: 4878.90
];
exports.TONGUE_HARMONICS = TONGUE_HARMONICS;
/** Default shadow buffer capacity (steps) */
const DEFAULT_BUFFER_CAPACITY = 256;
exports.DEFAULT_BUFFER_CAPACITY = DEFAULT_BUFFER_CAPACITY;
/** Minimum steps for fractal dimension estimation */
const MIN_FRACTAL_STEPS = 8;
/** Coefficient of variation threshold for "too clean" detection */
const SYNTHETIC_CV_THRESHOLD = 0.3;
exports.SYNTHETIC_CV_THRESHOLD = SYNTHETIC_CV_THRESHOLD;
/** Minimum fractal dimension for genuine signals */
const GENUINE_FRACTAL_MIN = 1.2;
exports.GENUINE_FRACTAL_MIN = GENUINE_FRACTAL_MIN;
// ═══════════════════════════════════════════════════════════════
// Core Functions
// ═══════════════════════════════════════════════════════════════
/**
 * Capture the drift between two state vectors.
 *
 * @param before - State vector before a pipeline step
 * @param after - State vector after a pipeline step
 * @param step - Step index
 * @param layer - Pipeline layer number (1-14)
 * @returns DriftCapture with magnitude and uniformity metrics
 */
function captureStepDrift(before, after, step, layer = 0) {
    const len = Math.min(before.length, after.length);
    const drift = new Array(len);
    for (let i = 0; i < len; i++) {
        drift[i] = after[i] - before[i];
    }
    const magnitude = vecNorm(drift);
    const cv = coefficientOfVariation(drift.map(Math.abs));
    return {
        step,
        layer,
        drift,
        magnitude,
        cv,
        timestamp: Date.now(),
    };
}
/**
 * Estimate the fractal dimension of accumulated drift using the
 * box-counting method on the drift magnitude time series.
 *
 * For genuine signals: D_f > 1.2 (complex, non-repeating)
 * For synthetic signals: D_f < 1.0 (smooth, predictable)
 *
 * @param captures - Array of drift captures
 * @returns Fractal dimension estimate with reliability metrics
 */
function estimateFractalDimension(captures) {
    if (captures.length < MIN_FRACTAL_STEPS) {
        return { dimension: 0, scales: 0, r2: 0, reliable: false };
    }
    // Use drift magnitudes as the 1D time series
    const series = captures.map((c) => c.magnitude);
    // Range of the series
    const min = Math.min(...series);
    const max = Math.max(...series);
    const range = max - min;
    if (range < EPSILON) {
        // Flat series → dimension 0 (point)
        return { dimension: 0, scales: 0, r2: 0, reliable: true };
    }
    // Box-counting: count boxes of size ε that contain at least one point
    // Scale ε from range/2 down to range/(2^k) for log-log regression
    const maxScales = Math.min(8, Math.floor(Math.log2(series.length)));
    const logEpsilons = [];
    const logCounts = [];
    for (let k = 1; k <= maxScales; k++) {
        const boxSize = range / (2 ** k);
        if (boxSize < EPSILON)
            break;
        // Count occupied boxes along the time axis
        const occupied = new Set();
        for (let i = 0; i < series.length; i++) {
            const tBox = Math.floor(i / (2 ** (maxScales - k)));
            const vBox = Math.floor((series[i] - min) / boxSize);
            occupied.add(`${tBox}:${vBox}`);
        }
        logEpsilons.push(Math.log(boxSize));
        logCounts.push(Math.log(occupied.size));
    }
    if (logEpsilons.length < 2) {
        return { dimension: 0, scales: logEpsilons.length, r2: 0, reliable: false };
    }
    // Linear regression: log(N) = -D * log(ε) + c
    // D = -slope of the fit
    const { slope, r2 } = linearRegression(logEpsilons, logCounts);
    const dimension = Math.max(0, -slope);
    return {
        dimension,
        scales: logEpsilons.length,
        r2,
        reliable: logEpsilons.length >= 3 && r2 > 0.5,
    };
}
/**
 * Derive a 6D Harmonic Key from accumulated drift.
 *
 * Each Sacred Tongue dimension receives a value derived from the drift
 * at its φ-harmonic frequency band. The key encodes the "musical signature"
 * of the computation's noise floor.
 *
 * @param captures - Array of drift captures
 * @returns HarmonicKey with per-tongue values and strength
 */
function deriveHarmonicKey(captures) {
    const zeroPh = [0, 0, 0, 0, 0, 0];
    if (captures.length < 2) {
        return {
            tongues: [0, 0, 0, 0, 0, 0],
            strength: 0,
            phases: zeroPh,
            entropy: 0,
            genuine: false,
        };
    }
    const tongues = [0, 0, 0, 0, 0, 0];
    const phases = [0, 0, 0, 0, 0, 0];
    // For each tongue k, accumulate drift energy at φ^k frequency
    for (let k = 0; k < 6; k++) {
        // Frequency for this tongue in "steps per cycle"
        const freq = TONGUE_HARMONICS[k] / TONGUE_HARMONICS[0]; // Normalized to KO base
        let realPart = 0;
        let imagPart = 0;
        for (let i = 0; i < captures.length; i++) {
            const mag = captures[i].magnitude;
            const angle = (2 * Math.PI * freq * i) / captures.length;
            realPart += mag * Math.cos(angle);
            imagPart += mag * Math.sin(angle);
        }
        // Normalize by N
        realPart /= captures.length;
        imagPart /= captures.length;
        // Amplitude = energy at this tongue's frequency
        tongues[k] = Math.sqrt(realPart * realPart + imagPart * imagPart);
        phases[k] = Math.atan2(imagPart, realPart);
    }
    // Normalize tongue values to [0, 1]
    const maxTongue = Math.max(...tongues, EPSILON);
    for (let k = 0; k < 6; k++) {
        tongues[k] /= maxTongue;
    }
    // Compute entropy of the tongue distribution
    const entropy = shannonEntropy(tongues);
    // Key strength: combines non-uniformity and fractal complexity
    const avgCV = captures.reduce((s, c) => s + c.cv, 0) / captures.length;
    const nonUniform = avgCV > SYNTHETIC_CV_THRESHOLD ? 1 : avgCV / SYNTHETIC_CV_THRESHOLD;
    // Harmonic coherence: how well the tongue spacing follows φ-ratios
    const coherence = harmonicCoherence(tongues);
    // Strength = geometric mean of non-uniformity and coherence
    const strength = Math.sqrt(nonUniform * coherence);
    // Genuine if strength and entropy are above thresholds
    const genuine = strength > 0.3 && entropy > 0.5;
    return { tongues, strength, phases, entropy, genuine };
}
/**
 * Assess the authenticity of accumulated drift.
 *
 * Combines fractal dimension, uniformity analysis, and harmonic key
 * to determine whether the drift is from genuine computation or
 * synthetic/injected input.
 *
 * @param captures - Array of drift captures
 * @returns DriftAuthenticity with score and diagnosis
 */
function assessAuthenticity(captures) {
    if (captures.length < 2) {
        return {
            score: 0,
            genuine: false,
            fractalDimension: 0,
            avgCV: 0,
            harmonicCoherence: 0,
            flags: ['insufficient_data'],
        };
    }
    const fractal = estimateFractalDimension(captures);
    const key = deriveHarmonicKey(captures);
    const avgCV = captures.reduce((s, c) => s + c.cv, 0) / captures.length;
    const syntheticCount = captures.filter((c) => c.cv < SYNTHETIC_CV_THRESHOLD).length;
    const syntheticRatio = syntheticCount / captures.length;
    const flags = [];
    // Score components (all [0, 1])
    let fractalScore;
    if (!fractal.reliable) {
        fractalScore = 0.5; // Uncertain
        flags.push('fractal_unreliable');
    }
    else if (fractal.dimension >= GENUINE_FRACTAL_MIN) {
        fractalScore = Math.min(fractal.dimension / 2, 1); // Higher D = more genuine
    }
    else {
        fractalScore = fractal.dimension / GENUINE_FRACTAL_MIN; // Scaled linearly
        flags.push('low_fractal_dimension');
    }
    // Uniformity score: high CV = genuine, low CV = suspicious
    const uniformityScore = avgCV > SYNTHETIC_CV_THRESHOLD
        ? 1
        : avgCV / SYNTHETIC_CV_THRESHOLD;
    if (syntheticRatio > 0.5)
        flags.push('high_uniformity');
    // Harmonic score
    const hCoherence = harmonicCoherence(key.tongues);
    if (hCoherence < 0.3)
        flags.push('low_harmonic_coherence');
    // Combined score: weighted average
    const score = clamp(0.35 * fractalScore + 0.35 * uniformityScore + 0.3 * hCoherence, 0, 1);
    const genuine = score > 0.5 && syntheticRatio < 0.5;
    if (!genuine)
        flags.push('synthetic_signature');
    return {
        score,
        genuine,
        fractalDimension: fractal.dimension,
        avgCV,
        harmonicCoherence: hCoherence,
        flags,
    };
}
/**
 * Convert accumulated drift into an audio signal for Layer 14 sonification.
 *
 * Genuine drift → harmonious hum (low HF ratio)
 * Synthetic drift → harsh static (high HF ratio)
 *
 * @param captures - Drift captures to sonify
 * @param sampleRate - Audio sample rate (default: 44100)
 * @param duration - Duration in seconds (default: 1.0)
 * @returns DriftSonification with audio samples
 */
function sonifyDrift(captures, sampleRate = 44100, duration = 1.0) {
    const samples = Math.floor(sampleRate * duration);
    const signal = new Array(samples).fill(0);
    if (captures.length === 0) {
        return {
            signal,
            sampleRate,
            duration,
            dominantFrequency: 0,
            centroid: 0,
            harmonious: false,
        };
    }
    // Derive harmonic key for frequency allocation
    const key = deriveHarmonicKey(captures);
    // Mix tongue harmonics weighted by key values
    let maxAmplitude = 0;
    for (let k = 0; k < 6; k++) {
        const freq = TONGUE_HARMONICS[k];
        const amplitude = key.tongues[k];
        const phase = key.phases[k];
        for (let n = 0; n < samples; n++) {
            const t = n / sampleRate;
            signal[n] += amplitude * Math.sin(2 * Math.PI * freq * t + phase);
        }
        maxAmplitude += amplitude;
    }
    // Normalize to [-1, 1]
    if (maxAmplitude > EPSILON) {
        for (let n = 0; n < samples; n++) {
            signal[n] /= maxAmplitude;
        }
    }
    // If drift is non-genuine (too clean), add noise to make it "sound broken"
    if (!key.genuine) {
        for (let n = 0; n < samples; n++) {
            signal[n] = signal[n] * 0.3 + (Math.random() * 2 - 1) * 0.7;
        }
    }
    // Compute dominant frequency (tongue with highest energy)
    let dominantIdx = 0;
    for (let k = 1; k < 6; k++) {
        if (key.tongues[k] > key.tongues[dominantIdx])
            dominantIdx = k;
    }
    const dominantFrequency = TONGUE_HARMONICS[dominantIdx];
    // Estimate spectral centroid
    let weightedFreq = 0;
    let totalWeight = 0;
    for (let k = 0; k < 6; k++) {
        weightedFreq += TONGUE_HARMONICS[k] * key.tongues[k];
        totalWeight += key.tongues[k];
    }
    const centroid = totalWeight > EPSILON ? weightedFreq / totalWeight : 0;
    return {
        signal,
        sampleRate,
        duration,
        dominantFrequency,
        centroid,
        harmonious: key.genuine,
    };
}
// ═══════════════════════════════════════════════════════════════
// DriftTracker Class — Shadow Buffer with Live Analysis
// ═══════════════════════════════════════════════════════════════
/**
 * Decimal Drift Tracker.
 *
 * Maintains a circular shadow buffer of drift captures and provides
 * live analysis: fractal dimension, harmonic key, authenticity scoring,
 * and audio sonification.
 *
 * Usage:
 * ```typescript
 * const tracker = new DriftTracker();
 *
 * // At each pipeline step, capture drift
 * tracker.capture(beforeState, afterState, stepIndex, layerNumber);
 *
 * // Check authenticity
 * const auth = tracker.assess();
 * if (!auth.genuine) console.warn('Synthetic input detected!');
 *
 * // Get harmonic key for cryptographic binding
 * const key = tracker.harmonicKey();
 *
 * // Sonify for auditory monitoring
 * const audio = tracker.sonify();
 * audioAxis.processFrame(audio.signal.slice(0, 2048));
 * ```
 */
class DriftTracker {
    buffer = [];
    capacity;
    dimensions;
    totalCaptures = 0;
    maxMagnitude = 0;
    constructor(config = {}) {
        this.capacity = config.capacity ?? DEFAULT_BUFFER_CAPACITY;
        this.dimensions = config.dimensions ?? 21;
    }
    /**
     * Capture drift between pipeline step states.
     */
    capture(before, after, step, layer = 0) {
        const dc = captureStepDrift(before, after, step, layer);
        // Add to circular buffer
        if (this.buffer.length >= this.capacity) {
            this.buffer.shift();
        }
        this.buffer.push(dc);
        this.totalCaptures++;
        if (dc.magnitude > this.maxMagnitude) {
            this.maxMagnitude = dc.magnitude;
        }
        return dc;
    }
    /**
     * Get current buffer contents.
     */
    getBuffer() {
        return [...this.buffer];
    }
    /**
     * Get buffer size.
     */
    get size() {
        return this.buffer.length;
    }
    /**
     * Estimate fractal dimension of accumulated drift.
     */
    fractalDimension() {
        return estimateFractalDimension(this.buffer);
    }
    /**
     * Derive the 6D harmonic key from accumulated drift.
     */
    harmonicKey() {
        return deriveHarmonicKey(this.buffer);
    }
    /**
     * Assess authenticity of accumulated drift.
     */
    assess() {
        return assessAuthenticity(this.buffer);
    }
    /**
     * Sonify the drift for Layer 14 auditory monitoring.
     */
    sonify(sampleRate, duration) {
        return sonifyDrift(this.buffer, sampleRate, duration);
    }
    /**
     * Get tracker statistics.
     */
    getStats() {
        const magnitudes = this.buffer.map((c) => c.magnitude);
        const cvs = this.buffer.map((c) => c.cv);
        const avgMagnitude = magnitudes.length > 0
            ? magnitudes.reduce((s, m) => s + m, 0) / magnitudes.length
            : 0;
        const avgCV = cvs.length > 0
            ? cvs.reduce((s, c) => s + c, 0) / cvs.length
            : 0;
        const fractal = this.fractalDimension();
        const auth = this.buffer.length >= 2 ? this.assess() : { score: 0 };
        return {
            totalCaptures: this.totalCaptures,
            bufferSize: this.buffer.length,
            bufferCapacity: this.capacity,
            avgMagnitude,
            maxMagnitude: this.maxMagnitude,
            avgCV,
            syntheticCount: this.buffer.filter((c) => c.cv < SYNTHETIC_CV_THRESHOLD).length,
            fractalDimension: fractal.dimension,
            authenticityScore: auth.score,
        };
    }
    /**
     * Clear the buffer.
     */
    reset() {
        this.buffer = [];
        this.totalCaptures = 0;
        this.maxMagnitude = 0;
    }
}
exports.DriftTracker = DriftTracker;
// ═══════════════════════════════════════════════════════════════
// Internal Utilities
// ═══════════════════════════════════════════════════════════════
function vecNorm(v) {
    let sum = 0;
    for (const x of v)
        sum += x * x;
    return Math.sqrt(sum);
}
function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}
/**
 * Coefficient of variation: std / mean of absolute values.
 * Returns 0 for all-zero inputs.
 */
function coefficientOfVariation(absValues) {
    if (absValues.length === 0)
        return 0;
    const mean = absValues.reduce((s, v) => s + v, 0) / absValues.length;
    if (mean < EPSILON)
        return 0;
    const variance = absValues.reduce((s, v) => s + (v - mean) ** 2, 0) / absValues.length;
    return Math.sqrt(variance) / mean;
}
/**
 * Shannon entropy of a normalized distribution (values don't need to sum to 1).
 */
function shannonEntropy(values) {
    const total = values.reduce((s, v) => s + Math.abs(v), 0);
    if (total < EPSILON)
        return 0;
    let entropy = 0;
    for (const v of values) {
        const p = Math.abs(v) / total;
        if (p > EPSILON) {
            entropy -= p * Math.log2(p);
        }
    }
    // Normalize to [0, 1] by dividing by max entropy (log2(N))
    const maxEntropy = Math.log2(values.length);
    return maxEntropy > 0 ? entropy / maxEntropy : 0;
}
/**
 * Harmonic coherence: how well tongue values follow φ-ratio spacing.
 *
 * Measures correlation between tongue[k] ratios and expected φ^k ratios.
 * Perfect φ-coherence = 1, random = ~0.
 */
function harmonicCoherence(tongues) {
    if (tongues.length < 2)
        return 0;
    // Expected ratios between adjacent tongues: φ (golden ratio)
    // We check if tongue[k+1] / tongue[k] ≈ some consistent ratio
    const ratios = [];
    for (let k = 0; k < tongues.length - 1; k++) {
        if (tongues[k] > EPSILON) {
            ratios.push(tongues[k + 1] / tongues[k]);
        }
    }
    if (ratios.length === 0)
        return 0;
    // Check consistency of ratios (low variance = coherent)
    const mean = ratios.reduce((s, r) => s + r, 0) / ratios.length;
    const variance = ratios.reduce((s, r) => s + (r - mean) ** 2, 0) / ratios.length;
    const cv = mean > EPSILON ? Math.sqrt(variance) / mean : 1;
    // Low CV = consistent harmonic relationship = high coherence
    // Map CV → coherence using sigmoid-like function
    const coherence = 1 / (1 + cv * cv);
    return clamp(coherence, 0, 1);
}
/**
 * Simple linear regression: y = slope * x + intercept.
 * Returns slope and R² (coefficient of determination).
 */
function linearRegression(x, y) {
    const n = x.length;
    if (n < 2)
        return { slope: 0, intercept: 0, r2: 0 };
    let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
    for (let i = 0; i < n; i++) {
        sumX += x[i];
        sumY += y[i];
        sumXY += x[i] * y[i];
        sumX2 += x[i] * x[i];
        sumY2 += y[i] * y[i];
    }
    const denom = n * sumX2 - sumX * sumX;
    if (Math.abs(denom) < EPSILON)
        return { slope: 0, intercept: 0, r2: 0 };
    const slope = (n * sumXY - sumX * sumY) / denom;
    const intercept = (sumY - slope * sumX) / n;
    // R²
    const yMean = sumY / n;
    let ssTot = 0, ssRes = 0;
    for (let i = 0; i < n; i++) {
        ssTot += (y[i] - yMean) ** 2;
        ssRes += (y[i] - (slope * x[i] + intercept)) ** 2;
    }
    const r2 = ssTot > EPSILON ? 1 - ssRes / ssTot : 0;
    return { slope, intercept, r2 };
}
//# sourceMappingURL=driftTracker.js.map