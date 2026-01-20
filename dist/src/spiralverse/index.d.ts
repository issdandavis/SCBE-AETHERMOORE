/**
 * Spiralverse - RWP v2.1 Multi-Signature Envelopes
 * =================================================
 *
 * Real World Protocol for secure AI-to-AI communication using
 * domain-separated authentication via Sacred Tongues.
 *
 * @module spiralverse
 * @version 2.1.0
 * @since 2026-01-18
 *
 * @example
 * ```typescript
 * import { signRoundtable, verifyRoundtable } from '@scbe/aethermoore/spiralverse';
 *
 * // Create keyring
 * const keyring = {
 *   ko: Buffer.from('...'),  // Kor'aelin (Control)
 *   av: Buffer.from('...'),  // Avali (I/O)
 *   ru: Buffer.from('...'),  // Runethic (Policy)
 *   ca: Buffer.from('...'),  // Cassisivadan (Compute)
 *   um: Buffer.from('...'),  // Umbroth (Security)
 *   dr: Buffer.from('...'),  // Draumric (Structure)
 * };
 *
 * // Sign envelope
 * const envelope = signRoundtable(
 *   { action: 'deploy', target: 'production' },
 *   'ko',                    // Primary tongue
 *   'agent-123',             // AAD
 *   keyring,
 *   ['ko', 'ru', 'um']       // Sign with Control, Policy, Security
 * );
 *
 * // Verify envelope
 * const result = verifyRoundtable(envelope, keyring, {
 *   policy: 'critical',      // Requires RU + UM + DR
 * });
 *
 * if (result.valid) {
 *   console.log('Valid tongues:', result.validTongues);
 *   console.log('Payload:', result.payload);
 * }
 * ```
 */
export { clearNonceCache, destroyNonceCache, getNonceCacheSize, signRoundtable, verifyRoundtable, } from './rwp';
export { POLICY_MATRIX, checkPolicy, enforcePolicy, getPolicyDescription, getRequiredTongues, suggestPolicy, } from './policy';
export type { EnvelopeOptions, Keyring, NonceCacheEntry, PolicyLevel, PolicyMatrix, RWP2MultiEnvelope, TongueID, TongueSpec, VerificationOptions, VerificationResult, } from './types';
export { PolicyError, RWPError, ReplayError, SignatureError } from './types';
//# sourceMappingURL=index.d.ts.map