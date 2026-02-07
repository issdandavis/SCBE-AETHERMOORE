/**
 * Spiralverse Protocol SDK - TypeScript Implementation
 *
 * Implements RWP v2.1 with Roundtable multi-signature governance,
 * Six Sacred Tongues domain separation, and 6D vector navigation.
 *
 * @version 2.1.0
 * @author Issac Davis
 * @license MIT
 */
/** Six Sacred Tongues as protocol domains */
export declare enum SacredTongue {
    KO = "KO",// Kor'aelin: Control & Intent
    AV = "AV",// Avali: I/O & Messaging
    RU = "RU",// Runethic: Policy & Constraints
    CA = "CA",// Cassisivadan: Logic & Computation
    UM = "UM",// Umbroth: Security & Secrets
    DR = "DR"
}
/** Message envelope with hybrid spelltext + payload structure */
export interface SpiralverseEnvelope {
    spelltext: string;
    payload: string;
    signatures: SignatureSet;
    ts: string;
    nonce: string;
}
/** Signature set for Roundtable governance */
export interface SignatureSet {
    [key: string]: string;
}
/** Action payload (before Base64URL encoding) */
export interface ActionPayload {
    action: string;
    params: Record<string, any>;
    metadata?: Record<string, any>;
}
/** 6D Position vector */
export interface Position6D {
    axiom: number;
    flow: number;
    glyph: number;
    oracle: number;
    charm: number;
    ledger: number;
}
export declare class SpiralverseProtocol {
    private secrets;
    constructor(secrets: Record<SacredTongue, string>);
    /**
     * Create signed envelope with specified tongues
     * @param origin Primary tongue initiating the action
     * @param requiredTongues Additional tongues for Roundtable governance
     * @param action Action payload
     */
    createEnvelope(origin: SacredTongue, requiredTongues: SacredTongue[], action: ActionPayload): SpiralverseEnvelope;
    /**
     * Verify envelope signatures against required tongues
     * @param envelope Message to verify
     * @param requiredTongues Tongues that must have signed
     */
    verifyEnvelope(envelope: SpiralverseEnvelope, requiredTongues: SacredTongue[]): boolean;
    /**
     * Decode payload from envelope
     */
    decodePayload(envelope: SpiralverseEnvelope): ActionPayload;
    private canonicalString;
    private sign;
}
export declare enum SecurityTier {
    TIER1_LOW = 1,// Single tongue (KO)
    TIER2_MEDIUM = 2,// Dual tongues (KO + RU)
    TIER3_HIGH = 3,// Triple tongues (KO + RU + UM)
    TIER4_CRITICAL = 4
}
/**
 * Get required tongues for a given security tier
 */
export declare function getRequiredTongues(tier: SecurityTier): SacredTongue[];
/**
 * Classify action by security tier
 */
export declare function classifyAction(action: string): SecurityTier;
//# sourceMappingURL=spiralverse-sdk.d.ts.map