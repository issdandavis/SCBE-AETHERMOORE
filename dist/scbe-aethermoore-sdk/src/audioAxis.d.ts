/**
 * SCBE Audio Axis - Layer 14
 *
 * FFT-based telemetry without altering the invariant metric.
 * faudio(t) = [Ea, Ca, Fa, rHF,a]
 *
 * - Ea = log(ε + Σₙ a[n]²) — Frame energy
 * - Ca = (Σₖ fₖ·Pₐ[k]) / (Σₖ Pₐ[k]) — Spectral centroid
 * - Fa = Σₖ (√Pₐ[k] - √Pₐ_prev[k])² — Spectral flux
 * - rHF,a = Σₖ∈Khigh Pₐ[k] / Σₖ Pₐ[k] — High-frequency ratio
 * - Saudio = 1 - rHF,a — Audio stability score
 */
/**
 * Audio features extracted from a frame
 */
export interface AudioFeatures {
    /** Frame energy: Ea = log(ε + Σₙ a[n]²) */
    energy: number;
    /** Spectral centroid: Ca = (Σₖ fₖ·Pₐ[k]) / (Σₖ Pₐ[k]) */
    centroid: number;
    /** Spectral flux: Fa = Σₖ (√Pₐ[k] - √Pₐ_prev[k])² */
    flux: number;
    /** High-frequency ratio: rHF,a = Σₖ∈Khigh Pₐ[k] / Σₖ Pₐ[k] */
    hfRatio: number;
    /** Audio stability score: Saudio = 1 - rHF,a */
    stability: number;
}
/**
 * Audio Axis Processor configuration
 */
export interface AudioAxisConfig {
    /** Sample rate in Hz (default: 44100) */
    sampleRate?: number;
    /** FFT size (default: 2048) */
    fftSize?: number;
    /** High frequency cutoff ratio (default: 0.5 = half Nyquist) */
    hfCutoff?: number;
    /** Risk weight for audio channel (default: 0.1) */
    riskWeight?: number;
}
/**
 * Audio Axis Processor - Layer 14 telemetry
 */
export declare class AudioAxisProcessor {
    private sampleRate;
    private fftSize;
    private hfCutoff;
    private riskWeight;
    private prevSpectrum;
    constructor(config?: AudioAxisConfig);
    /**
     * Compute frame energy
     * Ea = log(ε + Σₙ a[n]²)
     */
    private computeEnergy;
    /**
     * Compute spectral centroid
     * Ca = (Σₖ fₖ·Pₐ[k]) / (Σₖ Pₐ[k])
     */
    private computeCentroid;
    /**
     * Compute spectral flux
     * Fa = Σₖ (√Pₐ[k] - √Pₐ_prev[k])²
     */
    private computeFlux;
    /**
     * Compute high-frequency ratio
     * rHF,a = Σₖ∈Khigh Pₐ[k] / Σₖ Pₐ[k]
     */
    private computeHFRatio;
    /**
     * Process an audio frame and extract features
     *
     * @param signal - Audio samples (time domain)
     * @returns Audio features
     */
    processFrame(signal: number[]): AudioFeatures;
    /**
     * Integrate audio risk into base risk
     * Risk' = Risk_base + wa·(1 - Saudio)
     *
     * @param baseRisk - Base risk value
     * @param features - Audio features
     * @returns Adjusted risk
     */
    integrateRisk(baseRisk: number, features: AudioFeatures): number;
    /**
     * Reset processor state
     */
    reset(): void;
    /**
     * Get configuration
     */
    getConfig(): AudioAxisConfig;
}
/**
 * Generate a test signal (sine wave)
 */
export declare function generateTestSignal(frequency: number, duration: number, sampleRate?: number): number[];
/**
 * Generate white noise
 */
export declare function generateNoise(samples: number): number[];
//# sourceMappingURL=audioAxis.d.ts.map