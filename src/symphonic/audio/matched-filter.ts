/**
 * Dual-Channel Consensus: Matched Filter Verification
 * 
 * Computes matched-filter projections and correlation scores
 * 
 * Part of SCBE-AETHERMOORE v3.0.0
 * Patent: USPTO #63/961,403
 */

import { AudioProfile, VerificationResult, computeBeta } from './types';

/**
 * Compute matched-filter projections
 * 
 * Formula: p_j = (2/N) · Σ y[n] · sin(2π k_j · n/N + φ_j)
 * 
 * @param audio - Received audio samples
 * @param bins - Expected bin indices
 * @param phases - Expected phases
 * @param N - Frame size (samples)
 * @returns Per-bin projections
 */
export function computeProjections(
  audio: Float32Array,
  bins: number[],
  phases: number[],
  N: number
): number[] {
  const projections: number[] = [];
  
  for (let j = 0; j < bins.length; j++) {
    const k_j = bins[j];
    const phi_j = phases[j];
    
    // p_j = (2/N) · Σ y[n] · sin(2π k_j · n/N + φ_j)
    let p_j = 0;
    for (let n = 0; n < N; n++) {
      p_j += audio[n] * Math.sin(2 * Math.PI * k_j * n / N + phi_j);
    }
    p_j *= (2 / N);
    
    projections.push(p_j);
  }
  
  return projections;
}

/**
 * Verify challenge-bound watermark
 * 
 * @param audio - Received audio samples
 * @param challenge - Expected challenge bitstring
 * @param bins - Expected bin indices
 * @param phases - Expected phases
 * @param profile - Audio profile with thresholds
 * @returns Verification result
 */
export function verifyWatermark(
  audio: Float32Array,
  challenge: Uint8Array,
  bins: number[],
  phases: number[],
  profile: AudioProfile
): VerificationResult {
  const N = profile.N;
  const beta = computeBeta(profile);  // Compute beta from profile
  const E_min = profile.E_min;
  const clipThreshold = profile.clipThreshold;
  
  // Enforce exact N samples
  if (audio.length !== N) {
    throw new Error(`Audio must be exactly ${N} samples, got ${audio.length}`);
  }
  
  // Compute projections
  const projections = computeProjections(audio, bins, phases, N);
  
  // Compute correlation
  let correlation = 0;
  for (let j = 0; j < bins.length; j++) {
    const c_j = challenge[j]; // 0 or 1
    const sign = c_j === 0 ? 1 : -1;
    correlation += sign * projections[j];
  }
  
  // Compute total watermark energy
  const energy = projections.reduce((sum, p) => sum + p * p, 0);
  
  // Check for clipping
  const maxAmplitude = Math.max(...Array.from(audio).map(Math.abs));
  const clipped = maxAmplitude >= clipThreshold;
  
  // Decision
  const passed = correlation >= beta && energy >= E_min && !clipped;
  
  return {
    correlation,
    projections,
    energy,
    clipped,
    passed
  };
}
