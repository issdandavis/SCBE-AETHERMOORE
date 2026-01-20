/**
 * SCBE Layer 9: Spectral Coherence Module
 *
 * Implements spectral coherence metrics based on Parseval's theorem.
 * S_spec = E_low / (E_low + E_high + epsilon)
 *
 * Key Properties:
 * - Energy partition is invariant (Parseval's theorem)
 * - Phase invariant (depends only on |X[k]|^2)
 * - Bounded to [0, 1]
 */
/**
 * Complex number representation for FFT
 */
export interface Complex {
    re: number;
    im: number;
}
/**
 * Spectral analysis result
 */
export interface SpectralAnalysis {
    /** Low-frequency energy (below cutoff) */
    E_low: number;
    /** High-frequency energy (at or above cutoff) */
    E_high: number;
    /** Total energy */
    E_total: number;
    /** Spectral coherence value [0, 1] */
    S_spec: number;
    /** Power spectrum array */
    powerSpectrum: number[];
    /** Frequency bins in Hz */
    frequencies: number[];
}
/**
 * STFT frame analysis result
 */
export interface STFTFrame {
    /** Time position in seconds */
    time: number;
    /** Spectral coherence for this frame */
    S_audio: number;
    /** High-frequency ratio */
    r_HF: number;
}
/**
 * Compute the Discrete Fourier Transform of a real signal
 * Uses Cooley-Tukey FFT algorithm for efficiency
 */
export declare function fft(signal: number[]): Complex[];
/**
 * Compute magnitude squared of complex number
 */
export declare function magnitudeSquared(c: Complex): number;
/**
 * Compute frequency bins for FFT result
 */
export declare function fftFrequencies(N: number, sampleRate: number): number[];
/**
 * Compute spectral coherence for a signal
 *
 * S_spec = E_low / (E_low + E_high + epsilon)
 *
 * @param signal - Input signal array
 * @param sampleRate - Sample rate in Hz
 * @param cutoffFreq - Cutoff frequency in Hz
 * @param epsilon - Small constant to prevent division by zero
 * @returns SpectralAnalysis result
 */
export declare function computeSpectralCoherence(signal: number[], sampleRate: number, cutoffFreq: number, epsilon?: number): SpectralAnalysis;
/**
 * Verify Parseval's theorem: time-domain energy equals frequency-domain energy
 *
 * Sum|x[n]|^2 = (1/N) Sum|X[k]|^2
 *
 * @param signal - Input signal
 * @param X - FFT of signal
 * @returns Object with energies and relative error
 */
export declare function verifyParseval(signal: number[], X: Complex[]): {
    timeEnergy: number;
    freqEnergy: number;
    relativeError: number;
};
/**
 * Generate a test signal: sum of sinusoids
 *
 * @param sampleRate - Sample rate in Hz
 * @param duration - Duration in seconds
 * @param components - Array of {freq, amplitude} for each sinusoid
 * @returns Signal array
 */
export declare function generateTestSignal(sampleRate: number, duration: number, components: Array<{
    freq: number;
    amplitude: number;
    phase?: number;
}>): number[];
/**
 * Simple Short-Time Fourier Transform
 *
 * @param signal - Input signal
 * @param sampleRate - Sample rate in Hz
 * @param windowSize - Window size in samples
 * @param hopSize - Hop size in samples
 * @param cutoffFreq - Cutoff frequency for S_audio calculation
 * @returns Array of STFT frame results
 */
export declare function stft(signal: number[], sampleRate: number, windowSize: number, hopSize: number, cutoffFreq: number): STFTFrame[];
/**
 * Generate a linear chirp signal (frequency increases linearly over time)
 *
 * @param sampleRate - Sample rate in Hz
 * @param duration - Duration in seconds
 * @param startFreq - Starting frequency in Hz
 * @param endFreq - Ending frequency in Hz
 * @returns Chirp signal array
 */
export declare function generateChirp(sampleRate: number, duration: number, startFreq: number, endFreq: number): number[];
/**
 * Layer 9 Spectral Coherence bounds check
 *
 * Verifies that S_spec is always in [0, 1]
 */
export declare function verifySpectralCoherenceBounds(S_spec: number): boolean;
/**
 * Check phase invariance: S_spec should not depend on signal phase
 *
 * @param sampleRate - Sample rate
 * @param duration - Duration
 * @param components - Signal components
 * @param cutoffFreq - Cutoff frequency
 * @param tolerance - Maximum allowed difference
 * @returns Whether phase invariance holds
 */
export declare function checkPhaseInvariance(sampleRate: number, duration: number, components: Array<{
    freq: number;
    amplitude: number;
}>, cutoffFreq: number, tolerance?: number): {
    invariant: boolean;
    maxDifference: number;
};
//# sourceMappingURL=index.d.ts.map