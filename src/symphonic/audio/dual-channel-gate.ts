/**
 * Dual-Channel Consensus Gate
 * 
 * Combines cryptographic transcript verification with
 * challenge-bound acoustic watermark verification.
 * 
 * Part of SCBE-AETHERMOORE v3.0.0
 * Patent: USPTO #63/961,403
 */

import * as crypto from 'crypto';
import { selectBinsAndPhases } from './bin-selector';
import { verifyWatermark } from './matched-filter';
import { AudioProfile, DecisionOutcome } from './types';

export interface VerifyRequest {
  AAD: Buffer;
  payload: Buffer;
  timestamp: number;
  nonce: string;
  tag: Buffer;
  audio: Float32Array;
  challenge: Uint8Array;
}

/**
 * Dual-Channel Consensus Gate
 * 
 * Combines cryptographic transcript verification with
 * challenge-bound acoustic watermark verification.
 */
export class DualChannelGate {
  private profile: AudioProfile;
  private K: Buffer; // Master key
  private N_seen: Set<string>; // Nonce set
  private W: number; // Time window (seconds)
  
  constructor(profile: AudioProfile, K: Buffer, W: number = 60) {
    this.profile = profile;
    this.K = K;
    this.N_seen = new Set();
    this.W = W;
  }
  
  /**
   * Verify request with dual-channel consensus
   */
  verify(request: VerifyRequest): DecisionOutcome {
    const { AAD, payload, timestamp, nonce, tag, audio, challenge } = request;
    
    // --- Crypto Channel ---
    const C = Buffer.concat([
      Buffer.from('scbe.v1'),
      AAD,
      Buffer.from(timestamp.toString()),
      Buffer.from(nonce),
      payload
    ]);
    
    const expectedTag = crypto.createHmac('sha256', this.K).update(C).digest();
    const V_mac = crypto.timingSafeEqual(tag, expectedTag);
    
    const tau_recv = Date.now() / 1000;
    const V_time = Math.abs(tau_recv - timestamp) <= this.W;
    
    const V_nonce = !this.N_seen.has(nonce);
    
    const S_crypto = V_mac && V_time && V_nonce;
    
    if (!S_crypto) {
      return 'DENY';
    }
    
    // --- Audio Channel ---
    // Derive bins/phases from challenge
    const seed = crypto.createHmac('sha256', this.K)
      .update(Buffer.from('bins'))
      .update(Buffer.from(timestamp.toString()))
      .update(Buffer.from(nonce))
      .update(Buffer.from(challenge))
      .digest();
    
    const { bins, phases } = selectBinsAndPhases(
      seed,
      this.profile.b,
      this.profile.k_min,
      this.profile.k_max,
      this.profile.delta_k_min
    );
    
    // Verify watermark
    const result = verifyWatermark(audio, challenge, bins, phases, this.profile);
    
    const S_audio = result.passed;
    
    // Update nonce set (prevent replay)
    this.N_seen.add(nonce);
    
    // Decision logic
    if (S_audio) {
      return 'ALLOW';
    } else {
      return 'QUARANTINE';
    }
  }
  
  /**
   * Generate challenge for client
   */
  generateChallenge(): Uint8Array {
    const challenge = new Uint8Array(this.profile.b);
    crypto.randomFillSync(challenge);
    // Convert to 0/1
    for (let i = 0; i < challenge.length; i++) {
      challenge[i] = challenge[i] % 2;
    }
    return challenge;
  }
  
  /**
   * Clear old nonces (TTL cleanup)
   */
  clearOldNonces(): void {
    // In production, implement TTL-based cleanup
    // For now, simple clear
    this.N_seen.clear();
  }
  
  /**
   * Get current nonce count
   */
  getNonceCount(): number {
    return this.N_seen.size;
  }
}
