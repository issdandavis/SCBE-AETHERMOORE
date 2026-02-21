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
/** Ternary value: {-1, 0, 1} */
export type TernaryValue = -1 | 0 | 1;
/**
 * A single dual ternary state.
 * Both primary and mirror can independently be {-1, 0, 1}.
 */
export interface DualTernaryState {
    /** Primary ternary value (amplitude channel) */
    readonly primary: TernaryValue;
    /** Mirror ternary value (phase channel) */
    readonly mirror: TernaryValue;
}
/**
 * Energy properties of a dual ternary state.
 */
export interface StateEnergy {
    /** Total energy: primary² + mirror² + interaction */
    energy: number;
    /** Primary contribution: primary² */
    primaryEnergy: number;
    /** Mirror contribution: mirror² */
    mirrorEnergy: number;
    /** Cross-term interaction: primary × mirror */
    interaction: number;
    /** Phase classification */
    phase: 'constructive' | 'destructive' | 'neutral' | 'negative_resonance';
}
/**
 * Spectral signature of a dual ternary sequence.
 */
export interface DualTernarySpectrum {
    /** Primary channel FFT magnitudes */
    primaryMagnitudes: number[];
    /** Mirror channel FFT magnitudes */
    mirrorMagnitudes: number[];
    /** Cross-correlation spectrum */
    crossCorrelation: number[];
    /** 9-fold symmetry energy */
    ninefoldEnergy: number;
    /** Spectral coherence [0, 1] */
    coherence: number;
    /** Phase anomaly score [0, 1] — high = sign bias detected */
    phaseAnomaly: number;
}
/**
 * Fractal dimension estimate for dual ternary state sequences.
 */
export interface FractalDimensionResult {
    /** Base dimension (always 2 for dual ternary) */
    baseDimension: number;
    /** Sign entropy contribution to fractal dimension */
    signEntropy: number;
    /** Estimated Hausdorff dimension */
    hausdorffDimension: number;
    /** Mirror symmetry breaking indicator */
    symmetryBreaking: number;
    /** Self-similarity score [0, 1] */
    selfSimilarity: number;
}
/**
 * Dual Ternary configuration
 */
export interface DualTernaryConfig {
    /** Minimum sequence length for spectral analysis */
    minSequenceLength: number;
    /** Phase anomaly threshold for security alert */
    phaseAnomalyThreshold: number;
    /** Fractal dimension deviation threshold */
    fractalDeviationThreshold: number;
    /** Recursive mirroring depth for fractal computation */
    mirrorDepth: number;
    /** Sign entropy normalization factor */
    entropyNormalization: number;
}
export declare const DEFAULT_DUAL_TERNARY_CONFIG: DualTernaryConfig;
/**
 * All 9 states in the full dual ternary space.
 * Enumerated for complete coverage.
 */
export declare const FULL_STATE_SPACE: ReadonlyArray<DualTernaryState>;
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
export declare function computeStateEnergy(state: DualTernaryState): StateEnergy;
/**
 * Get the state index (0-8) for a dual ternary state.
 * Maps (primary, mirror) to a unique index.
 */
export declare function stateIndex(state: DualTernaryState): number;
/**
 * Reconstruct a dual ternary state from its index.
 */
export declare function stateFromIndex(index: number): DualTernaryState;
/**
 * Transition from one dual ternary state to another.
 * Both primary and mirror can independently change by {-1, 0, +1}.
 *
 * The clip function ensures we stay within {-1, 0, 1}.
 */
export declare function transition(current: DualTernaryState, deltaP: number, deltaM: number): DualTernaryState;
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
export declare function encodeToDualTernary(amplitude: number, phase: number, threshold?: number): DualTernaryState;
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
export declare function encodeSequence(values: number[], threshold?: number): DualTernaryState[];
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
export declare function computeSpectrum(sequence: DualTernaryState[], config?: DualTernaryConfig): DualTernarySpectrum;
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
export declare function estimateFractalDimension(sequence: DualTernaryState[], config?: DualTernaryConfig): FractalDimensionResult;
/**
 * Dual Ternary Encoding System.
 *
 * Manages encoding of brain state vectors into dual ternary space,
 * spectral analysis of state sequences, and fractal dimension
 * monitoring for security anomaly detection.
 */
export declare class DualTernarySystem {
    private readonly config;
    private history;
    private stepCounter;
    constructor(config?: Partial<DualTernaryConfig>);
    /**
     * Encode a 21D brain state into dual ternary representation.
     *
     * Pairs consecutive dimensions as (amplitude, phase):
     *   dims[0,1] → state[0], dims[2,3] → state[1], etc.
     *
     * This captures both the value and its contextual derivative
     * in each dual ternary symbol.
     */
    encode(state21D: number[], threshold?: number): DualTernaryState[];
    /**
     * Analyze the current state history for spectral anomalies.
     */
    analyzeSpectrum(): DualTernarySpectrum;
    /**
     * Estimate the fractal dimension of the current history.
     */
    analyzeFractalDimension(): FractalDimensionResult;
    /**
     * Full security analysis: spectrum + fractal + threat assessment.
     *
     * @returns Combined analysis with anomaly flags
     */
    fullAnalysis(): {
        spectrum: DualTernarySpectrum;
        fractal: FractalDimensionResult;
        phaseAnomalyDetected: boolean;
        fractalAnomalyDetected: boolean;
        threatScore: number;
    };
    /**
     * Convert dual ternary state to a signed tensor product representation.
     *
     * Returns a 3×3 matrix where entry (i,j) represents the
     * contribution of the (primary=i-1, mirror=j-1) state.
     */
    static toTensorProduct(state: DualTernaryState): number[][];
    /**
     * Compute the signed tensor product sum over a sequence.
     * Shows the distribution across the 3×3 state space.
     */
    static tensorHistogram(sequence: DualTernaryState[]): number[][];
    /** Get the history length */
    getHistoryLength(): number;
    /** Get the step counter */
    getStep(): number;
    /** Get the raw history */
    getHistory(): ReadonlyArray<DualTernaryState>;
    /** Reset all state */
    reset(): void;
}
//# sourceMappingURL=dual-ternary.d.ts.map