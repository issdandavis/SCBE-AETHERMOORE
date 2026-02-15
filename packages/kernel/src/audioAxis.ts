/**
 * @file audioAxis.ts
 * @module harmonic/audioAxis
 * @layer Layer 14
 * @component Audio Telemetry Engine
 * @version 3.0.0
 * @since 2026-01-20
 *
 * SCBE Audio Axis - FFT-based telemetry without altering the invariant metric.
 *
 * Layer 14: f_audio(t) = [E_a, C_a, F_a, r_HF,a]
 *
 * Features:
 * - E_a = log(ε + Σₙ a[n]²) — Frame energy
 * - C_a = (Σₖ fₖ·Pₐ[k]) / (Σₖ Pₐ[k]) — Spectral centroid
 * - F_a = Σₖ (√Pₐ[k] - √Pₐ_prev[k])² — Spectral flux
 * - r_HF,a = Σₖ∈Khigh Pₐ[k] / Σₖ Pₐ[k] — High-frequency ratio
 * - S_audio = 1 - r_HF,a — Audio stability score ∈ [0,1]
 */

/** Small epsilon for numerical stability */
const EPSILON = 1e-10;

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
 * Simple DFT implementation (for environments without Web Audio API)
 * Returns magnitude spectrum (power)
 */
function computeDFT(signal: number[]): number[] {
  const N = signal.length;
  const spectrum: number[] = new Array(Math.floor(N / 2) + 1);

  for (let k = 0; k < spectrum.length; k++) {
    let re = 0,
      im = 0;
    for (let n = 0; n < N; n++) {
      const angle = (2 * Math.PI * k * n) / N;
      re += signal[n] * Math.cos(angle);
      im -= signal[n] * Math.sin(angle);
    }
    // Power spectrum: |X[k]|²
    spectrum[k] = (re * re + im * im) / N;
  }

  return spectrum;
}

/**
 * Audio Axis Processor - Layer 14 telemetry
 */
export class AudioAxisProcessor {
  private sampleRate: number;
  private fftSize: number;
  private hfCutoff: number;
  private riskWeight: number;
  private prevSpectrum: number[] | null = null;

  constructor(config: AudioAxisConfig = {}) {
    this.sampleRate = config.sampleRate ?? 44100;
    this.fftSize = config.fftSize ?? 2048;
    this.hfCutoff = config.hfCutoff ?? 0.5;
    this.riskWeight = config.riskWeight ?? 0.1;
  }

  /**
   * Compute frame energy
   * Ea = log(ε + Σₙ a[n]²)
   */
  private computeEnergy(signal: number[]): number {
    let sum = 0;
    for (const s of signal) {
      sum += s * s;
    }
    return Math.log(EPSILON + sum);
  }

  /**
   * Compute spectral centroid
   * Ca = (Σₖ fₖ·Pₐ[k]) / (Σₖ Pₐ[k])
   */
  private computeCentroid(spectrum: number[]): number {
    let weightedSum = 0;
    let totalPower = 0;
    const binWidth = this.sampleRate / this.fftSize;

    for (let k = 0; k < spectrum.length; k++) {
      const freq = k * binWidth;
      weightedSum += freq * spectrum[k];
      totalPower += spectrum[k];
    }

    return weightedSum / (totalPower + EPSILON);
  }

  /**
   * Compute spectral flux
   * Fa = Σₖ (√Pₐ[k] - √Pₐ_prev[k])²
   */
  private computeFlux(spectrum: number[], prevSpectrum: number[] | null): number {
    if (!prevSpectrum) return 0;

    let flux = 0;
    const len = Math.min(spectrum.length, prevSpectrum.length);

    for (let k = 0; k < len; k++) {
      const diff = Math.sqrt(spectrum[k]) - Math.sqrt(prevSpectrum[k]);
      flux += diff * diff;
    }

    // Normalize by number of bins
    return flux / len;
  }

  /**
   * Compute high-frequency ratio
   * rHF,a = Σₖ∈Khigh Pₐ[k] / Σₖ Pₐ[k]
   */
  private computeHFRatio(spectrum: number[]): number {
    const cutoffBin = Math.floor(spectrum.length * this.hfCutoff);
    let hfPower = 0;
    let totalPower = 0;

    for (let k = 0; k < spectrum.length; k++) {
      totalPower += spectrum[k];
      if (k >= cutoffBin) {
        hfPower += spectrum[k];
      }
    }

    return hfPower / (totalPower + EPSILON);
  }

  /**
   * Process an audio frame and extract features
   *
   * @param signal - Audio samples (time domain)
   * @returns Audio features
   */
  processFrame(signal: number[]): AudioFeatures {
    // Compute spectrum via DFT
    const spectrum = computeDFT(signal);

    // Extract features
    const energy = this.computeEnergy(signal);
    const centroid = this.computeCentroid(spectrum);
    const flux = this.computeFlux(spectrum, this.prevSpectrum);
    const hfRatio = this.computeHFRatio(spectrum);
    const stability = 1 - hfRatio;

    // Store for next frame
    this.prevSpectrum = spectrum;

    return { energy, centroid, flux, hfRatio, stability };
  }

  /**
   * Integrate audio risk into base risk
   * Risk' = Risk_base + wa·(1 - Saudio)
   *
   * @param baseRisk - Base risk value
   * @param features - Audio features
   * @returns Adjusted risk
   */
  integrateRisk(baseRisk: number, features: AudioFeatures): number {
    return baseRisk + this.riskWeight * (1 - features.stability);
  }

  /**
   * Reset processor state
   */
  reset(): void {
    this.prevSpectrum = null;
  }

  /**
   * Get configuration
   */
  getConfig(): AudioAxisConfig {
    return {
      sampleRate: this.sampleRate,
      fftSize: this.fftSize,
      hfCutoff: this.hfCutoff,
      riskWeight: this.riskWeight,
    };
  }
}

/**
 * Generate a test signal (sine wave)
 */
export function generateTestSignal(
  frequency: number,
  duration: number,
  sampleRate: number = 44100
): number[] {
  const samples = Math.floor(duration * sampleRate);
  const signal: number[] = new Array(samples);

  for (let n = 0; n < samples; n++) {
    signal[n] = Math.sin((2 * Math.PI * frequency * n) / sampleRate);
  }

  return signal;
}

/**
 * Generate white noise
 */
export function generateNoise(samples: number): number[] {
  const signal: number[] = new Array(samples);
  for (let n = 0; n < samples; n++) {
    signal[n] = Math.random() * 2 - 1;
  }
  return signal;
}
