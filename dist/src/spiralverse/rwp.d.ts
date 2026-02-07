/**
 * RWP v2.1 Multi-Signature Envelopes
 * ===================================
 *
 * Real World Protocol for secure AI-to-AI communication using
 * domain-separated HMAC-SHA256 signatures via Sacred Tongues.
 *
 * @module spiralverse/rwp
 * @version 2.1.0
 * @since 2026-01-18
 */
import { EnvelopeOptions, Keyring, RWP2MultiEnvelope, TongueID, VerificationOptions, VerificationResult } from './types';
/**
 * Create RWP v2.1 multi-signature envelope
 *
 * @param payload - Payload object (must be JSON-serializable)
 * @param primaryTongue - Primary tongue indicating intent domain
 * @param aad - Additional authenticated data (metadata)
 * @param keyring - HMAC keys for each tongue
 * @param signingTongues - List of tongues to sign with
 * @param options - Optional envelope options
 * @returns Signed envelope
 *
 * @example
 * ```typescript
 * const keyring = {
 *   ko: Buffer.from('...'),
 *   av: Buffer.from('...'),
 *   ru: Buffer.from('...'),
 * };
 *
 * const envelope = signRoundtable(
 *   { action: 'deploy', target: 'production' },
 *   'ko',
 *   'agent-123',
 *   keyring,
 *   ['ko', 'ru', 'um']  // Sign with Control, Policy, Security
 * );
 * ```
 */
export declare function signRoundtable<T = any>(payload: T, primaryTongue: TongueID, aad: string, keyring: Keyring, signingTongues: TongueID[], options?: EnvelopeOptions): RWP2MultiEnvelope<T>;
/**
 * Verify RWP v2.1 multi-signature envelope
 *
 * @param env - Envelope to verify
 * @param keyring - HMAC keys for each tongue
 * @param options - Verification options
 * @returns Verification result with valid tongues and decoded payload
 *
 * @example
 * ```typescript
 * const result = verifyRoundtable(envelope, keyring, {
 *   replayWindowMs: 300000,  // 5 minutes
 *   policy: 'critical',      // Requires RU + UM + DR
 * });
 *
 * if (result.valid) {
 *   console.log('Valid tongues:', result.validTongues);
 *   console.log('Payload:', result.payload);
 * } else {
 *   console.error('Verification failed:', result.error);
 * }
 * ```
 */
export declare function verifyRoundtable(env: RWP2MultiEnvelope, keyring: Keyring, options?: VerificationOptions): VerificationResult;
/**
 * Clear nonce cache (for testing)
 */
export declare function clearNonceCache(): void;
/**
 * Get nonce cache size (for monitoring)
 */
export declare function getNonceCacheSize(): number;
/**
 * Destroy nonce cache (cleanup)
 */
export declare function destroyNonceCache(): void;
//# sourceMappingURL=rwp.d.ts.map