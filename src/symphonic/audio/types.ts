/**
 * Dual-Channel Consensus: Type Definitions
 *
 * Part of SCBE-AETHERMOORE v3.0.0
 * Patent: USPTO #63/961,403
 */

export interface AudioProfile {
  SR: number; // Sample rate (Hz)
  N: number; // Frame size (samples)
  binResolution: number; // Hz per bin
  f_min: number; // Minimum frequency (Hz)
  f_max: number; // Maximum frequency (Hz)
  k_min: number; // Minimum bin index
  k_max: number; // Maximum bin index
  b: number; // Challenge bits
  delta_k_min: number; // Minimum bin spacing
  gamma: number; // Mix gain
  betaFactor: number; // Threshold factor (0.3-0.6)
  E_min: number; // Minimum energy
  clipThreshold: number; // Clipping threshold
}

/**
 * Compute expected correlation for clean watermark
 */
export function expectedCorrelation(profile: AudioProfile): number {
  return profile.gamma * Math.sqrt(profile.b);
}

/**
 * Compute beta threshold from profile
 */
export function computeBeta(profile: AudioProfile): number {
  return profile.betaFactor * expectedCorrelation(profile);
}

export interface BinSelection {
  bins: number[]; // Selected bin indices
  phases: number[]; // Per-bin phases
}

export interface WatermarkResult {
  waveform: Float32Array; // Watermark signal
  bins: number[]; // Used bins
  phases: number[]; // Used phases
}

export interface VerificationResult {
  correlation: number; // Correlation score
  projections: number[]; // Per-bin projections
  energy: number; // Total watermark energy
  clipped: boolean; // Clipping detected
  passed: boolean; // Threshold check
}

export type DecisionOutcome = 'ALLOW' | 'QUARANTINE' | 'DENY';

/**
 * Predefined audio profiles for different use cases
 */
export const PROFILE_16K: AudioProfile = {
  SR: 16000,
  N: 4096,
  binResolution: 3.90625,
  f_min: 1200,
  f_max: 4200,
  k_min: 308,
  k_max: 1075,
  b: 32,
  delta_k_min: 10, // Reduced from 12 to accommodate harmonic collision checks
  gamma: 0.02,
  betaFactor: 0.4, // 40% of expected correlation
  E_min: 0.001,
  clipThreshold: 0.95,
};

export const PROFILE_44K: AudioProfile = {
  SR: 44100,
  N: 8192,
  binResolution: 5.383,
  f_min: 2000,
  f_max: 9000,
  k_min: 372,
  k_max: 1672,
  b: 48,
  delta_k_min: 11,
  gamma: 0.015,
  betaFactor: 0.35, // 35% of expected correlation
  E_min: 0.0008,
  clipThreshold: 0.95,
};

export const PROFILE_48K: AudioProfile = {
  SR: 48000,
  N: 8192,
  binResolution: 5.859,
  f_min: 2500,
  f_max: 12000,
  k_min: 427,
  k_max: 2048,
  b: 64,
  delta_k_min: 10,
  gamma: 0.01,
  betaFactor: 0.3, // 30% of expected correlation
  E_min: 0.0005,
  clipThreshold: 0.95,
};
