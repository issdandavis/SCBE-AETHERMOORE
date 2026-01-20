/**
 * Dual-Channel Consensus: Bin Selection
 * 
 * Deterministically selects frequency bins and phases from challenge
 * 
 * Part of SCBE-AETHERMOORE v3.0.0
 * Patent: USPTO #63/961,403
 */

import * as crypto from 'crypto';
import { BinSelection } from './types';

/**
 * Select bins and phases deterministically from challenge
 * 
 * @param seed - HMAC-derived seed from (K, τ, n, c)
 * @param b - Number of bits (bins to select)
 * @param k_min - Minimum bin index
 * @param k_max - Maximum bin index
 * @param delta_k_min - Minimum bin spacing
 * @returns Selected bins and phases
 */
export function selectBinsAndPhases(
  seed: Buffer,
  b: number,
  k_min: number,
  k_max: number,
  delta_k_min: number
): BinSelection {
  const bins: number[] = [];
  const phases: number[] = [];
  const used = new Set<number>();
  
  let attempts = 0;
  const maxAttempts = b * 100;
  
  while (bins.length < b && attempts < maxAttempts) {
    // Generate candidate bin
    const hash = crypto.createHash('sha256')
      .update(seed)
      .update(Buffer.from([attempts]))
      .digest();
    
    const candidate = k_min + (hash.readUInt32BE(0) % (k_max - k_min + 1));
    
    // Check spacing constraint
    let valid = true;
    for (const existing of bins) {
      if (Math.abs(candidate - existing) < delta_k_min) {
        valid = false;
        break;
      }
      
      // Avoid harmonic collisions (2x, 3x)
      if (Math.abs(candidate - 2 * existing) < delta_k_min ||
          Math.abs(candidate - 3 * existing) < delta_k_min) {
        valid = false;
        break;
      }
    }
    
    if (valid && !used.has(candidate)) {
      bins.push(candidate);
      used.add(candidate);
      
      // Derive phase from same seed
      const phaseHash = crypto.createHash('sha256')
        .update(seed)
        .update(Buffer.from('phase'))
        .update(Buffer.from([bins.length]))
        .digest();
      
      phases.push(2 * Math.PI * (phaseHash.readUInt32BE(0) / 0xFFFFFFFF));
    }
    
    attempts++;
  }
  
  if (bins.length < b) {
    throw new Error(`Could not select ${b} bins with spacing ${delta_k_min}`);
  }
  
  return { bins, phases };
}
