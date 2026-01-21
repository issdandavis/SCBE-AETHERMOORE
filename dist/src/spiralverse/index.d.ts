/**
 * Spiralverse Protocol - RWP v2.1 Multi-Signature Envelopes
 *
 * Provides multi-signature consensus (Roundtable) for AI governance.
 *
 * The Six Sacred Tongues:
 * - KO (Kor'aelin): Control & Orchestration
 * - AV (Avali): I/O & Messaging
 * - RU (Runethic): Policy & Constraints
 * - CA (Cassisivadan): Logic & Computation
 * - UM (Umbroth): Security & Privacy
 * - DR (Draumric): Types & Structures
 *
 * @module spiralverse
 */
/// <reference types="node" />
/// <reference types="node" />
/** Sacred Tongue identifier */
export type TongueID = 'ko' | 'av' | 'ru' | 'ca' | 'um' | 'dr';
/** Policy enforcement level */
export type PolicyLevel = 'standard' | 'strict' | 'critical';
/** Keyring containing keys for all tongues */
export type Keyring = {
    [K in TongueID]?: Buffer;
};
/** Signature map by tongue */
export type SignatureMap = {
    [K in TongueID]?: string;
};
/** RWP v2.1 Envelope structure */
export interface RWPEnvelope {
    ver: '2.1';
    primary_tongue: TongueID;
    aad: string;
    payload: string;
    sigs: SignatureMap;
    nonce: string;
    ts: number;
    kid?: string;
}
/** Verification result */
export interface VerifyResult {
    valid: boolean;
    validTongues: TongueID[];
    payload?: unknown;
    error?: string;
}
/** Options for signing */
export interface SignOptions {
    kid?: string;
    timestamp?: number;
    nonce?: Buffer;
}
/** Options for verification */
export interface VerifyOptions {
    policy?: PolicyLevel;
    maxAge?: number;
    maxFutureSkew?: number;
}
/**
 * Clear the nonce cache (for testing)
 */
export declare function clearNonceCache(): void;
/**
 * Sign a payload with multiple Sacred Tongues (Roundtable consensus)
 *
 * @param payload - The payload to sign
 * @param primaryTongue - The initiating tongue
 * @param aad - Additional authenticated data
 * @param keyring - Keys for signing
 * @param signingTongues - Which tongues should sign
 * @param options - Optional signing options
 * @returns The signed RWP envelope
 */
export declare function signRoundtable(payload: unknown, primaryTongue: TongueID, aad: string, keyring: Keyring, signingTongues: TongueID[], options?: SignOptions): RWPEnvelope;
/**
 * Verify an RWP envelope
 *
 * @param envelope - The envelope to verify
 * @param keyring - Keys for verification
 * @param options - Verification options
 * @returns Verification result
 */
export declare function verifyRoundtable(envelope: RWPEnvelope, keyring: Keyring, options?: VerifyOptions): VerifyResult;
/**
 * Check if a set of tongues satisfies a policy
 *
 * @param tongues - The tongues that have signed
 * @param policy - The policy level to check
 * @returns Whether the policy is satisfied
 */
export declare function checkPolicy(tongues: TongueID[], policy: PolicyLevel): boolean;
/**
 * Get the required tongues for a policy level
 *
 * @param policy - The policy level
 * @returns Array of required tongue IDs
 */
export declare function getRequiredTongues(policy: PolicyLevel): TongueID[];
/**
 * Suggest an appropriate policy level for an action
 *
 * @param action - The action being performed
 * @returns Suggested policy level
 */
export declare function suggestPolicy(action: string): PolicyLevel;
//# sourceMappingURL=index.d.ts.map