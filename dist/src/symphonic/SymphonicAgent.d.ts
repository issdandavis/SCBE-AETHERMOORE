/**
 * SCBE Symphonic Cipher - Symphonic Agent
 *
 * The Symphonic Agent handles "Audio Synthesis Simulation" - the transformation
 * of transaction intents into spectral fingerprints through signal processing.
 *
 * Pipeline:
 * 1. Intent Modulation (Feistel permutation) - scrambles input into pseudo-random signal
 * 2. Signal Generation - converts bytes to normalized floating-point samples
 * 3. Spectral Analysis (FFT) - transforms to frequency domain
 * 4. Fingerprint Extraction - samples magnitude spectrum
 *
 * @module symphonic/SymphonicAgent
 */
import { Complex } from './Complex.js';
import { type FeistelConfig } from './Feistel.js';
/**
 * Synthesis result containing signal and spectral data
 */
export interface SynthesisResult {
    /** Modulated buffer (Feistel output) */
    modulatedData: Uint8Array;
    /** Time-domain signal (normalized -1 to 1) */
    signal: number[];
    /** Complex frequency spectrum */
    spectrum: Complex[];
    /** Magnitude fingerprint */
    fingerprint: number[];
    /** Spectral coherence score (0-1) */
    coherence: number;
    /** Dominant frequency bin */
    dominantFrequency: number;
}
/**
 * Agent configuration options
 */
export interface SymphonicAgentConfig {
    /** Feistel network configuration */
    feistel: Partial<FeistelConfig>;
    /** Fingerprint size (default 32) */
    fingerprintSize: number;
    /** High frequency threshold for coherence (default 0.5) */
    highFreqThreshold: number;
}
/**
 * Symphonic Agent - orchestrates intent-to-spectrum transformation
 */
export declare class SymphonicAgent {
    private readonly feistel;
    private readonly config;
    /**
     * Creates a new Symphonic Agent.
     *
     * @param config Agent configuration
     */
    constructor(config?: Partial<SymphonicAgentConfig>);
    /**
     * Synthesizes harmonics from an intent.
     *
     * 1. Modulates (Scrambles) the Intent using Feistel Cipher
     * 2. Converts the byte stream to normalized floating point signal
     * 3. Performs FFT to get the Harmonic Spectrum
     * 4. Extracts fingerprint and computes metrics
     *
     * @param intent The user's intent (e.g., "TRANSFER_500_AETHER")
     * @param secretKey The user's private key for modulation
     * @returns Complete synthesis result
     */
    synthesizeHarmonics(intent: string, secretKey: string): SynthesisResult;
    /**
     * Extracts a compact fingerprint from spectrum magnitudes.
     *
     * @param spectrum Complex frequency spectrum
     * @returns Magnitude fingerprint array
     */
    extractFingerprint(spectrum: Complex[]): number[];
    /**
     * Quantizes a fingerprint to bytes for encoding.
     *
     * @param fingerprint Floating-point fingerprint
     * @returns Quantized byte array
     */
    quantizeFingerprint(fingerprint: number[]): Uint8Array;
    /**
     * Computes spectral coherence (low HF = high coherence).
     *
     * @param spectrum Complex frequency spectrum
     * @returns Coherence score in [0, 1]
     */
    private computeCoherence;
    /**
     * Finds the dominant frequency bin.
     *
     * @param spectrum Complex frequency spectrum
     * @returns Index of dominant frequency
     */
    private findDominantFrequency;
    /**
     * Verifies that an intent produces the expected fingerprint.
     *
     * @param intent Original intent
     * @param secretKey Secret key
     * @param expectedFingerprint Expected fingerprint bytes
     * @param tolerance Comparison tolerance (default 5)
     * @returns True if fingerprints match within tolerance
     */
    verifyFingerprint(intent: string, secretKey: string, expectedFingerprint: Uint8Array, tolerance?: number): boolean;
    /**
     * Computes similarity between two fingerprints.
     *
     * @param fp1 First fingerprint
     * @param fp2 Second fingerprint
     * @returns Similarity score in [0, 1]
     */
    static fingerprintSimilarity(fp1: number[], fp2: number[]): number;
    /**
     * Analyzes spectral properties for debugging/visualization.
     *
     * @param spectrum Complex spectrum
     * @returns Analysis object with various metrics
     */
    static analyzeSpectrum(spectrum: Complex[]): {
        totalEnergy: number;
        meanMagnitude: number;
        peakMagnitude: number;
        peakFrequency: number;
        spectralCentroid: number;
        spectralSpread: number;
    };
}
/**
 * Creates a Symphonic Agent with default settings.
 */
export declare function createSymphonicAgent(config?: Partial<SymphonicAgentConfig>): SymphonicAgent;
//# sourceMappingURL=SymphonicAgent.d.ts.map