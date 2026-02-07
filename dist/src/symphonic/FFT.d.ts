/**
 * SCBE Symphonic Cipher - Fast Fourier Transform
 *
 * Iterative implementation of the Cooley-Tukey Radix-2 FFT algorithm.
 * Transforms time-domain signals to frequency-domain spectra in O(N log N).
 *
 * This implementation is optimized for V8 (Node.js) by avoiding deep recursion
 * and using iterative loops with bit-reversal permutation.
 *
 * @module symphonic/FFT
 */
import { Complex } from './Complex.js';
/**
 * FFT result containing both frequency spectrum and metadata
 */
export interface FFTResult {
    /** Complex frequency spectrum */
    spectrum: Complex[];
    /** Magnitude spectrum (|X[k]|) */
    magnitudes: number[];
    /** Power spectrum (|X[k]|²) */
    power: number[];
    /** Phase spectrum (arg(X[k])) */
    phases: number[];
    /** Number of samples */
    n: number;
    /** Frequency resolution (if sample rate provided) */
    frequencyResolution?: number;
}
/**
 * Fast Fourier Transform implementation
 */
export declare class FFT {
    /**
     * Performs the Forward FFT on a signal.
     *
     * @param input Array of Complex numbers representing the time-domain signal.
     * @returns Array of Complex numbers representing the frequency-domain spectrum.
     * @throws Error if input length is not a power of 2
     */
    static transform(input: Complex[]): Complex[];
    /**
     * Performs the Inverse FFT to recover time-domain signal.
     *
     * @param spectrum Complex frequency spectrum
     * @returns Time-domain signal
     */
    static inverse(spectrum: Complex[]): Complex[];
    /**
     * Performs FFT and returns detailed analysis results.
     *
     * @param signal Real-valued time-domain signal
     * @param sampleRate Optional sample rate for frequency resolution
     * @returns FFTResult with spectrum, magnitudes, power, and phases
     */
    static analyze(signal: number[], sampleRate?: number): FFTResult;
    /**
     * Computes the power spectral density.
     *
     * @param signal Real-valued signal
     * @returns Normalized power spectrum
     */
    static powerSpectralDensity(signal: number[]): number[];
    /**
     * Computes spectral coherence score (low HF ratio = high coherence).
     *
     * @param signal Time-domain signal
     * @param highFreqThreshold Fraction of spectrum considered "high frequency" (default 0.5)
     * @returns Coherence score in [0, 1]
     */
    static spectralCoherence(signal: number[], highFreqThreshold?: number): number;
    /**
     * Utility to pad a number array to the next power of 2 and convert to Complex.
     * Zero-padding interpolates the spectrum but does not add new information.
     *
     * @param data Real-valued input signal
     * @returns Complex signal padded to power of 2
     */
    static prepareSignal(data: number[]): Complex[];
    /**
     * Converts byte buffer to normalized signal [-1, 1].
     * Treats bytes as unsigned PCM samples.
     *
     * @param buffer Input byte buffer
     * @returns Normalized signal array
     */
    static bufferToSignal(buffer: Uint8Array): number[];
    /**
     * Extracts harmonic fingerprint from spectrum.
     * Samples magnitude spectrum at regular intervals.
     *
     * @param spectrum Complex frequency spectrum
     * @param fingerprintSize Number of samples to extract (default 32)
     * @returns Fingerprint as magnitude samples
     */
    static extractFingerprint(spectrum: Complex[], fingerprintSize?: number): number[];
    /**
     * Performs bit-reversal permutation for iterative FFT.
     * Reorders input so butterflies can be computed in-place.
     *
     * @param input Original array
     * @returns Bit-reversed copy
     */
    private static bitReversalPermutation;
    /**
     * Checks if a number is a power of 2.
     */
    static isPowerOf2(n: number): boolean;
    /**
     * Returns the next power of 2 >= n.
     */
    static nextPowerOf2(n: number): number;
}
//# sourceMappingURL=FFT.d.ts.map