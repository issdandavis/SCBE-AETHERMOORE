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
/** Sacred Tongue harmonic frequencies: 440 * φ^k Hz */
declare const TONGUE_HARMONICS: number[];
/** Default shadow buffer capacity (steps) */
declare const DEFAULT_BUFFER_CAPACITY = 256;
/** Coefficient of variation threshold for "too clean" detection */
declare const SYNTHETIC_CV_THRESHOLD = 0.3;
/** Minimum fractal dimension for genuine signals */
declare const GENUINE_FRACTAL_MIN = 1.2;
/** A single captured drift vector between pipeline steps */
export interface DriftCapture {
    /** Step index */
    readonly step: number;
    /** Pipeline layer that produced this drift (1-14) */
    readonly layer: number;
    /** Per-dimension drift values: δ[i] = after[i] - before[i] */
    readonly drift: number[];
    /** L2 magnitude of the drift vector */
    readonly magnitude: number;
    /** Coefficient of variation (std/mean of |drift|) */
    readonly cv: number;
    /** Timestamp */
    readonly timestamp: number;
}
/** Shadow buffer configuration */
export interface ShadowBufferConfig {
    /** Maximum capacity (default: 256) */
    capacity?: number;
    /** Dimensions of the state vector (default: 21) */
    dimensions?: number;
}
/** Fractal dimension estimate */
export interface FractalEstimate {
    /** Estimated fractal dimension (D_f) */
    dimension: number;
    /** Number of scale levels used */
    scales: number;
    /** R² of the log-log fit */
    r2: number;
    /** Whether the estimate is reliable (enough data + good fit) */
    reliable: boolean;
}
/** 6D Harmonic Key derived from drift */
export interface HarmonicKey {
    /** Per-tongue harmonic values [KO, AV, RU, CA, UM, DR] */
    tongues: [number, number, number, number, number, number];
    /** Overall key strength (0 = synthetic, 1 = strongly genuine) */
    strength: number;
    /** Phase angles per tongue (radians) */
    phases: [number, number, number, number, number, number];
    /** Entropy of the drift distribution */
    entropy: number;
    /** Whether this key indicates genuine (non-synthetic) drift */
    genuine: boolean;
}
/** Authenticity assessment of a drift key */
export interface DriftAuthenticity {
    /** Authenticity score [0, 1] — 1 = definitely genuine */
    score: number;
    /** Whether drift is classified as genuine */
    genuine: boolean;
    /** Fractal dimension */
    fractalDimension: number;
    /** Average CV across captures */
    avgCV: number;
    /** Harmonic coherence (correlation with φ-ratio spacing) */
    harmonicCoherence: number;
    /** Flags */
    flags: string[];
}
/** Audio signal derived from drift for sonification */
export interface DriftSonification {
    /** Audio samples (time-domain signal) */
    signal: number[];
    /** Sample rate */
    sampleRate: number;
    /** Duration in seconds */
    duration: number;
    /** Dominant frequency (Hz) */
    dominantFrequency: number;
    /** Spectral centroid estimate */
    centroid: number;
    /** Whether the sound is "harmonious" (genuine) or "dissonant" (synthetic) */
    harmonious: boolean;
}
/** Tracker statistics */
export interface DriftTrackerStats {
    /** Total captures recorded */
    totalCaptures: number;
    /** Captures currently in buffer */
    bufferSize: number;
    /** Buffer capacity */
    bufferCapacity: number;
    /** Average drift magnitude */
    avgMagnitude: number;
    /** Maximum drift magnitude seen */
    maxMagnitude: number;
    /** Average CV */
    avgCV: number;
    /** Number of synthetic-looking captures (CV < threshold) */
    syntheticCount: number;
    /** Current fractal dimension estimate */
    fractalDimension: number;
    /** Current authenticity score */
    authenticityScore: number;
}
/**
 * Capture the drift between two state vectors.
 *
 * @param before - State vector before a pipeline step
 * @param after - State vector after a pipeline step
 * @param step - Step index
 * @param layer - Pipeline layer number (1-14)
 * @returns DriftCapture with magnitude and uniformity metrics
 */
export declare function captureStepDrift(before: number[], after: number[], step: number, layer?: number): DriftCapture;
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
export declare function estimateFractalDimension(captures: DriftCapture[]): FractalEstimate;
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
export declare function deriveHarmonicKey(captures: DriftCapture[]): HarmonicKey;
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
export declare function assessAuthenticity(captures: DriftCapture[]): DriftAuthenticity;
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
export declare function sonifyDrift(captures: DriftCapture[], sampleRate?: number, duration?: number): DriftSonification;
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
export declare class DriftTracker {
    private buffer;
    private capacity;
    private dimensions;
    private totalCaptures;
    private maxMagnitude;
    constructor(config?: ShadowBufferConfig);
    /**
     * Capture drift between pipeline step states.
     */
    capture(before: number[], after: number[], step: number, layer?: number): DriftCapture;
    /**
     * Get current buffer contents.
     */
    getBuffer(): DriftCapture[];
    /**
     * Get buffer size.
     */
    get size(): number;
    /**
     * Estimate fractal dimension of accumulated drift.
     */
    fractalDimension(): FractalEstimate;
    /**
     * Derive the 6D harmonic key from accumulated drift.
     */
    harmonicKey(): HarmonicKey;
    /**
     * Assess authenticity of accumulated drift.
     */
    assess(): DriftAuthenticity;
    /**
     * Sonify the drift for Layer 14 auditory monitoring.
     */
    sonify(sampleRate?: number, duration?: number): DriftSonification;
    /**
     * Get tracker statistics.
     */
    getStats(): DriftTrackerStats;
    /**
     * Clear the buffer.
     */
    reset(): void;
}
export { TONGUE_HARMONICS, DEFAULT_BUFFER_CAPACITY, SYNTHETIC_CV_THRESHOLD, GENUINE_FRACTAL_MIN, };
//# sourceMappingURL=driftTracker.d.ts.map