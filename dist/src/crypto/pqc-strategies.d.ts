/**
 * @file pqc-strategies.ts
 * @module crypto/pqc-strategies
 * @layer Layer 4, Layer 5, Layer 13
 * @component PQC Strategy Profiles + TriStitch + Geometric Key Binding
 * @version 1.0.0
 *
 * Three capabilities in one module:
 *
 * 1. **Strategy Profiles** — named algorithm combos (balanced-v1, paranoid-v1,
 *    iot-v1, conservative-v1) so governance can pick by risk level, not by
 *    algorithm name. Swappable in one place when NIST updates guidance.
 *
 * 2. **TriStitch Combiner** — run 3 KEMs from different PQC families and XOR
 *    all shared secrets. Attacker must break all three math problems at once.
 *    PQC + PQC + PQC, not just classical + PQC.
 *
 * 3. **Geometric Key Binding** — fuse the PQC shared secret with the 21D brain
 *    state via HKDF. The resulting session key is only valid when both crypto
 *    AND geometry agree. "Valid math but wrong intent" gets rejected.
 *
 * Usage:
 *   const strategy = getStrategy('balanced-v1');
 *   const session = await executeStrategy(strategy, brainState);
 *   // session.boundKey is HKDF(pqcSecret, SHA256(21D state))
 */
import { type QSKeyPair, type PQCFamily, type NISTLevel } from './quantum-safe.js';
/** A named PQC strategy profile */
export interface PQCStrategy {
    /** Strategy identifier (e.g., 'balanced-v1') */
    name: string;
    /** Human description */
    description: string;
    /** KEM algorithm(s) — single for standard, multiple for TriStitch */
    kemAlgorithms: string[];
    /** Signature algorithm */
    sigAlgorithm: string;
    /** Include classical ECDH XOR component */
    classicalHybrid: boolean;
    /** Minimum NIST security level */
    minNistLevel: NISTLevel;
    /** Recommended use case */
    useCase: string;
    /** PQC families involved (for audit logging) */
    families: PQCFamily[];
}
/** Built-in strategy catalog */
export declare const STRATEGY_CATALOG: Record<string, PQCStrategy>;
/** Get a strategy by name. Checks custom, then built-in catalog. */
export declare function getStrategy(name: string): PQCStrategy;
/** Register a custom strategy profile */
export declare function registerStrategy(strategy: PQCStrategy): void;
/** List all available strategy names */
export declare function listStrategyNames(): string[];
/** Clear custom strategies (for testing) */
export declare function clearCustomStrategies(): void;
/** Result of a TriStitch multi-KEM combination */
export interface TriStitchResult {
    /** Combined shared secret (XOR of all KEM secrets + optional classical) */
    combinedSecret: Uint8Array;
    /** Per-KEM results for audit trail */
    kemResults: Array<{
        algorithm: string;
        family: PQCFamily;
        ciphertext: Uint8Array;
        secretSize: number;
    }>;
    /** Number of independent PQC families stitched */
    familyCount: number;
    /** Whether classical component was included */
    classicalComponent: boolean;
}
/**
 * TriStitch: run multiple KEMs from different families and XOR-combine
 * all shared secrets. The combined secret is compromised only if ALL
 * constituent families are broken simultaneously.
 *
 * @param kemNames - Array of KEM algorithm names (1-4)
 * @param classicalHybrid - XOR in 32 random bytes (classical ECDH placeholder)
 * @returns Combined secret + per-KEM audit data
 */
export declare function triStitch(kemNames: string[], classicalHybrid?: boolean): Promise<{
    result: TriStitchResult;
    keyPairs: QSKeyPair[];
}>;
/**
 * Compute the geometric fingerprint of a 21D brain state.
 *
 * SHA-256 over the IEEE 754 double representation of all 21 components,
 * preserving full precision including decimal drift artifacts.
 *
 * @param state - 21D brain state vector
 * @returns 32-byte fingerprint
 */
export declare function geometricFingerprint(state: number[]): Uint8Array;
/** Geometric binding configuration */
export interface GeoBindConfig {
    /** Domain separation label (default: 'scbe:geo-bind:v1') */
    domain?: string;
    /** Include Poincaré norm in info string (default: true) */
    includeNorm?: boolean;
    /** Include phase index in info string (default: true) */
    includePhase?: boolean;
}
/** Result of geometric key binding */
export interface GeoBoundKey {
    /** The bound session key: HKDF(pqcSecret, geoFingerprint, domainInfo) */
    boundKey: Uint8Array;
    /** Geometric fingerprint used as salt */
    geoFingerprint: Uint8Array;
    /** SHA-256 hex of the bound key (for audit logs) */
    keyId: string;
    /** Poincaré norm of the 21D state at binding time */
    stateNorm: number;
}
/**
 * Bind a PQC shared secret to a 21D brain state.
 *
 * boundKey = HKDF-SHA256(
 *   ikm  = pqcSharedSecret,
 *   salt = SHA256(21D state as IEEE 754 doubles),
 *   info = "scbe:geo-bind:v1|norm=X.XXX|phase=N"
 * )
 *
 * The resulting session key is valid only when:
 * 1. The PQC crypto decrypts correctly, AND
 * 2. The geometric state matches what was bound at key creation.
 *
 * "Valid math but wrong intent" → wrong geometric fingerprint → wrong key.
 *
 * @param sharedSecret - PQC shared secret (32 bytes from KEM/TriStitch)
 * @param brainState - 21D state vector [SCBE(6) + nav(6) + cog(3) + sem(3) + swarm(3)]
 * @param config - Optional binding configuration
 * @returns Bound session key + metadata
 */
export declare function bindKeyToGeometry(sharedSecret: Uint8Array, brainState: number[], config?: GeoBindConfig): GeoBoundKey;
/**
 * Verify that a key binding matches an expected geometric state.
 *
 * Re-derives the bound key from the same inputs and compares.
 * Uses constant-time comparison to prevent timing attacks.
 *
 * @param boundKey - Previously derived bound key
 * @param sharedSecret - Original PQC shared secret
 * @param brainState - Current 21D state to verify against
 * @param config - Same config used during binding
 * @returns true if geometric state matches
 */
export declare function verifyGeometricBinding(boundKey: Uint8Array, sharedSecret: Uint8Array, brainState: number[], config?: GeoBindConfig): boolean;
/** Full result of executing a PQC strategy with geometric binding */
export interface StrategyExecutionResult {
    /** Strategy that was executed */
    strategyName: string;
    /** Geometrically-bound session key */
    boundKey: GeoBoundKey;
    /** TriStitch result (if multi-KEM) or single KEM result */
    triStitch: TriStitchResult;
    /** Signature key pair for signing governance decisions */
    sigKeyPair: QSKeyPair;
    /** Signature algorithm instance */
    sigAlgorithm: string;
    /** Families involved (for Layer 13 audit) */
    families: PQCFamily[];
    /** Timestamp of execution */
    timestamp: number;
}
/**
 * Execute a complete PQC strategy with geometric binding.
 *
 * This is the top-level API for governance:
 *   1. Resolve strategy → algorithm combos
 *   2. TriStitch KEMs → combined shared secret
 *   3. Bind to 21D geometric state → session key
 *   4. Generate signature key pair for decision signing
 *
 * @param strategyName - Strategy profile name (e.g., 'balanced-v1')
 * @param brainState - Current 21D brain state for geometric binding
 * @param geoConfig - Optional geometric binding config
 * @returns Complete execution result with bound key + signing capability
 */
export declare function executeStrategy(strategyName: string, brainState: number[], geoConfig?: GeoBindConfig): Promise<StrategyExecutionResult>;
/**
 * Sign a governance decision using a strategy execution result.
 *
 * @param message - The governance decision payload
 * @param execution - Result from executeStrategy()
 * @returns Signature bytes
 */
export declare function signWithStrategy(message: Uint8Array, execution: StrategyExecutionResult): Promise<Uint8Array>;
//# sourceMappingURL=pqc-strategies.d.ts.map