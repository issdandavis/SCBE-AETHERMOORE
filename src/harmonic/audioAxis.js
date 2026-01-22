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
/** Small epsilon for numerical stability */
const EPSILON = 1e-10;
/**
 * Simple DFT implementation (for environments without Web Audio API)
 * Returns magnitude spectrum (power)
 */
function computeDFT(signal) {
  const N = signal.length;
  const spectrum = new Array(Math.floor(N / 2) + 1);
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
  sampleRate;
  fftSize;
  hfCutoff;
  riskWeight;
  prevSpectrum = null;
  constructor(config = {}) {
    this.sampleRate = config.sampleRate ?? 44100;
    this.fftSize = config.fftSize ?? 2048;
    this.hfCutoff = config.hfCutoff ?? 0.5;
    this.riskWeight = config.riskWeight ?? 0.1;
  }
  /**
   * Compute frame energy
   * Ea = log(ε + Σₙ a[n]²)
   */
  computeEnergy(signal) {
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
  computeCentroid(spectrum) {
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
  computeFlux(spectrum, prevSpectrum) {
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
  computeHFRatio(spectrum) {
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
  processFrame(signal) {
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
  integrateRisk(baseRisk, features) {
    return baseRisk + this.riskWeight * (1 - features.stability);
  }
  /**
   * Reset processor state
   */
  reset() {
    this.prevSpectrum = null;
  }
  /**
   * Get configuration
   */
  getConfig() {
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
export function generateTestSignal(frequency, duration, sampleRate = 44100) {
  const samples = Math.floor(duration * sampleRate);
  const signal = new Array(samples);
  for (let n = 0; n < samples; n++) {
    signal[n] = Math.sin((2 * Math.PI * frequency * n) / sampleRate);
  }
  return signal;
}
/**
 * Generate white noise
 */
export function generateNoise(samples) {
  const signal = new Array(samples);
  for (let n = 0; n < samples; n++) {
    signal[n] = Math.random() * 2 - 1;
  }
  return signal;
}
//# sourceMappingURL=audioAxis.js.map
