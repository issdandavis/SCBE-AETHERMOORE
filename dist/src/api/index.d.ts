/**
 * SCBE-AETHERMOORE API
 *
 * Complete TypeScript API for the Spiralverse Protocol, exposing:
 * - Risk evaluation with hyperbolic geometry
 * - RWP v2.1 multi-signature envelopes
 * - Agent management with 6D positioning and trust
 * - SecurityGate with adaptive dwell time
 * - Roundtable consensus (multi-signature requirements)
 * - Harmonic complexity pricing
 *
 * Usage:
 *   import { SCBE, Agent, SecurityGate, Roundtable } from './api';
 *
 *   // Create agents in 6D space
 *   const alice = new Agent('Alice', [1, 2, 3, 0.5, 1.5, 2.5]);
 *
 *   // Evaluate risk
 *   const risk = scbe.evaluateRisk({ action: 'transfer', amount: 10000 });
 *
 *   // Security gate check with adaptive dwell time
 *   const gate = new SecurityGate();
 *   const result = await gate.check(alice, 'delete', { source: 'external' });
 *
 *   // Sign with Roundtable consensus
 *   const tongues = Roundtable.requiredTongues('deploy');
 *   const envelope = scbe.sign(payload, tongues);
 *
 * @module api
 */
import { checkPolicy, getRequiredTongues, suggestPolicy, type Keyring, type RWPEnvelope, type TongueID, type PolicyLevel, type VerifyOptions } from '../spiralverse/index.js';
/** Arbitrary context for risk evaluation */
export interface Context {
    [key: string]: unknown;
}
/** Risk evaluation result */
export interface RiskResult {
    score: number;
    distance: number;
    scaledCost: number;
    decision: 'ALLOW' | 'REVIEW' | 'DENY';
    reason: string;
}
/** Signing result with envelope and tongues used */
export interface SignResult {
    envelope: RWPEnvelope;
    tongues: TongueID[];
}
/** Verification result */
export interface VerifyResult {
    valid: boolean;
    validTongues?: TongueID[];
    payload?: unknown;
    reason?: string;
}
/** Security gate check result */
export interface GateResult {
    status: 'allow' | 'review' | 'deny';
    score: number;
    dwellMs: number;
    reason?: string;
}
/** Harmonic complexity pricing tier */
export interface PricingTier {
    tier: 'FREE' | 'STARTER' | 'PRO' | 'ENTERPRISE';
    complexity: number;
    description: string;
}
/** Action types for Roundtable consensus */
export type ActionType = 'read' | 'query' | 'write' | 'update' | 'delete' | 'grant' | 'deploy' | 'rotate_keys';
/** Security gate configuration */
export interface SecurityGateConfig {
    minWaitMs?: number;
    maxWaitMs?: number;
    alpha?: number;
}
export type { Keyring, RWPEnvelope, TongueID, PolicyLevel, VerifyOptions };
/**
 * An AI agent with a position in 6D space and trust tracking.
 *
 * Agents exist in a 6-dimensional space where:
 * - Close agents = simple security (they trust each other)
 * - Far agents = complex security (strangers need more checks)
 */
export declare class Agent {
    readonly name: string;
    readonly position: number[];
    trustScore: number;
    lastSeen: number;
    /**
     * Create a new agent in 6D space.
     * @param name - Agent identifier
     * @param position - 6D position vector
     * @param initialTrust - Starting trust score (0-1, default 1.0)
     */
    constructor(name: string, position: number[], initialTrust?: number);
    /**
     * Calculate Euclidean distance to another agent.
     * Close agents = simple communication, far agents = complex security.
     */
    distanceTo(other: Agent): number;
    /**
     * Agent checks in - refreshes trust and timestamp.
     */
    checkIn(): void;
    /**
     * Apply trust decay based on time since last check-in.
     * @param decayRate - Rate of decay (default 0.01)
     * @returns Current trust score after decay
     */
    decayTrust(decayRate?: number): number;
}
/**
 * Security gate with adaptive dwell time based on risk.
 *
 * Like a nightclub bouncer that:
 * - Checks your ID (authentication)
 * - Looks at your reputation (trust score)
 * - Makes you wait longer if you're risky (adaptive dwell time)
 */
export declare class SecurityGate {
    private minWaitMs;
    private maxWaitMs;
    private alpha;
    constructor(config?: SecurityGateConfig);
    /**
     * Calculate risk score for an agent performing an action.
     * @returns Risk score (0 = safe, higher = riskier)
     */
    assessRisk(agent: Agent, action: string, context: Context): number;
    /**
     * Perform security gate check with adaptive dwell time.
     *
     * Higher risk = longer wait time (slows attackers).
     * Returns allow/review/deny decision.
     */
    check(agent: Agent, action: string, context: Context): Promise<GateResult>;
}
/**
 * Roundtable multi-signature consensus system.
 *
 * Different actions require different numbers of "departments" to agree:
 * - Low security: 1 signature (just control)
 * - Medium security: 2 signatures (control + policy)
 * - High security: 3 signatures (control + policy + security)
 * - Critical: 4+ signatures (all departments)
 */
export declare const Roundtable: {
    /** Tier definitions for multi-signature requirements */
    TIERS: {
        low: TongueID[];
        medium: TongueID[];
        high: TongueID[];
        critical: TongueID[];
    };
    /**
     * Get required tongues for an action.
     */
    requiredTongues(action: ActionType): TongueID[];
    /**
     * Check if we have all required signatures.
     */
    hasQuorum(signatures: TongueID[], required: TongueID[]): boolean;
    /**
     * Get suggested policy level for an action (from spiralverse).
     */
    suggestPolicy: typeof suggestPolicy;
    /**
     * Get required tongues for a policy level (from spiralverse).
     */
    getRequiredTongues: typeof getRequiredTongues;
    /**
     * Check if tongues satisfy a policy (from spiralverse).
     */
    checkPolicy: typeof checkPolicy;
};
/**
 * Calculate harmonic complexity for a task depth.
 *
 * Uses the "perfect fifth" ratio (1.5) from music theory:
 * - depth=1: H = 1.5^1 = 1.5 (simple, like a single note)
 * - depth=2: H = 1.5^4 = 5.06 (medium, like a chord)
 * - depth=3: H = 1.5^9 = 38.4 (complex, like a symphony)
 *
 * @param depth - Task nesting depth (1-based)
 * @param ratio - Harmonic ratio (default 1.5 = perfect fifth)
 */
export declare function harmonicComplexity(depth: number, ratio?: number): number;
/**
 * Get pricing tier based on task complexity.
 */
export declare function getPricingTier(depth: number): PricingTier;
export declare class SCBE {
    private keyring;
    private metric;
    constructor(keyring?: Keyring);
    /**
     * Evaluate the risk of a context/action.
     * Returns a risk score and decision.
     */
    evaluateRisk(context: Context): RiskResult;
    /**
     * Sign a payload using RWP multi-signature envelope.
     *
     * @param payload - Data to sign
     * @param tongues - Tongues to sign with (default: ['ko'])
     * @returns Signed envelope and tongues used
     */
    sign(payload: unknown, tongues?: TongueID[]): SignResult;
    /**
     * Verify an envelope signature.
     *
     * @param envelope - RWP envelope to verify
     * @param options - Verification options (policy, maxAge, etc.)
     * @returns Verification result with valid tongues and payload
     */
    verify(envelope: RWPEnvelope, options?: VerifyOptions): VerifyResult;
    /**
     * Sign and verify with policy enforcement.
     *
     * Automatically determines required tongues based on action.
     *
     * @param payload - Data to sign
     * @param action - Action type (determines required tongues)
     * @returns Signed envelope
     */
    signForAction(payload: unknown, action: ActionType): SignResult;
    /**
     * Verify an envelope with policy enforcement.
     *
     * @param envelope - RWP envelope to verify
     * @param action - Expected action (determines required policy)
     * @returns Verification result
     */
    verifyForAction(envelope: RWPEnvelope, action: ActionType): VerifyResult;
    /**
     * Apply breathing transform to a context point.
     * Used for dynamic security adaptation.
     */
    breathe(context: Context, intensity?: number): number[];
    /**
     * Get the keyring (for advanced usage).
     */
    getKeyring(): Keyring;
    /**
     * Set a custom keyring.
     */
    setKeyring(keyring: Keyring): void;
    private contextToPoint;
    private simpleHash;
}
/** Default SCBE instance for simple usage */
export declare const scbe: SCBE;
/** Default security gate instance */
export declare const defaultGate: SecurityGate;
/**
 * Evaluate risk of a context using the default SCBE instance.
 */
export declare function evaluateRisk(context: Context): RiskResult;
/**
 * Sign a payload using the default SCBE instance.
 */
export declare function sign(payload: unknown, tongues?: TongueID[]): SignResult;
/**
 * Sign a payload for a specific action (determines required tongues).
 */
export declare function signForAction(payload: unknown, action: ActionType): SignResult;
/**
 * Verify an envelope using the default SCBE instance.
 */
export declare function verify(envelope: RWPEnvelope, options?: VerifyOptions): VerifyResult;
/**
 * Verify an envelope for a specific action (enforces policy).
 */
export declare function verifyForAction(envelope: RWPEnvelope, action: ActionType): VerifyResult;
/**
 * Apply breathing transform to a context using the default SCBE instance.
 */
export declare function breathe(context: Context, intensity?: number): number[];
/**
 * Check if an agent can perform an action (using default gate).
 */
export declare function checkAccess(agent: Agent, action: string, context: Context): Promise<GateResult>;
/**
 * Get required tongues for an action.
 */
export declare function requiredTongues(action: ActionType): TongueID[];
//# sourceMappingURL=index.d.ts.map