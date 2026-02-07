/**
 * Dual-Channel Consensus Gate
 *
 * Combines cryptographic transcript verification with
 * challenge-bound acoustic watermark verification.
 *
 * Part of SCBE-AETHERMOORE v3.0.0
 * Patent: USPTO #63/961,403
 */
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
export declare class DualChannelGate {
    private profile;
    private K;
    private N_seen;
    private W;
    constructor(profile: AudioProfile, K: Buffer, W?: number);
    /**
     * Verify request with dual-channel consensus
     */
    verify(request: VerifyRequest): DecisionOutcome;
    /**
     * Generate challenge for client
     */
    generateChallenge(): Uint8Array;
    /**
     * Clear old nonces (TTL cleanup)
     */
    clearOldNonces(): void;
    /**
     * Get current nonce count
     */
    getNonceCount(): number;
}
//# sourceMappingURL=dual-channel-gate.d.ts.map