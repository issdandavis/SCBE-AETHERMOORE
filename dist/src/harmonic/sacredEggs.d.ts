/**
 * @file sacredEggs.ts
 * @module harmonic/sacredEggs
 * @layer Layer 12, Layer 13
 * @component Sacred Eggs - Cryptographic Deferred Authorization
 * @version 3.2.5
 *
 * Sacred Eggs: Ciphertext containers that decrypt IFF a conjunction of predicates holds.
 *
 * PATENTABLE KERNEL:
 * Stateful secret release conditioned on a conjunction of:
 *   - domain membership (tongue)
 *   - geometric state
 *   - monotone path history
 *   - quorum
 *   - cryptographic validity
 * where failure collapses to a uniform response (fail-to-noise).
 *
 * This is NOT RBAC/ABAC. This is cryptographic deferred authorization.
 */
/** Sacred Tongue identifiers */
export type Tongue = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
/** All tongues */
export declare const ALL_TONGUES: Tongue[];
/** Trust ring levels (0 = core/most trusted, 4 = edge/least trusted) */
export type RingLevel = 0 | 1 | 2 | 3 | 4;
/** Ring boundaries (radii in Poincaré ball) */
export declare const RING_BOUNDARIES: number[];
/** Default tongue weights */
export declare const DEFAULT_TONGUE_WEIGHTS: Record<Tongue, number>;
/**
 * Policy specification for a Sacred Egg
 */
export interface EggPolicy {
    /** Primary tongue required */
    primaryTongue: Tongue;
    /** Additional tongues for multi-tongue mode (optional) */
    requiredTongues?: Tongue[];
    /** Tongue weights for weighted multi-tongue mode */
    tongueWeights?: Record<Tongue, number>;
    /** Minimum weight sum for multi-tongue mode */
    minWeightSum?: number;
    /** Maximum allowed ring level (0 = core only, 4 = any) */
    maxRing: RingLevel;
    /** Allowed policy cells (discrete state vectors) */
    allowedCells?: number[][];
    /** Required quorum count */
    quorumRequired: number;
    /** Maximum geometric distance to attractors */
    maxGeoDistance?: number;
    /** Attractor points in Poincaré ball */
    attractors?: number[][];
}
/**
 * Sacred Egg: Ciphertext container with policy-gated decryption
 *
 * E := (hdr, C, tag, policy)
 */
export interface SacredEgg {
    /** Header (public metadata) */
    header: {
        /** Egg identifier */
        id: string;
        /** Creation epoch */
        epoch: number;
        /** Policy hash (for verification without revealing policy) */
        policyHash: string;
    };
    /** Ciphertext (encrypted payload) */
    ciphertext: Uint8Array;
    /** Authentication tag */
    tag: Uint8Array;
    /** Policy specification */
    policy: EggPolicy;
    /** Domain separation tag (for key derivation) */
    dst: Uint8Array;
}
/**
 * Verifier state: The observed context at hatch time
 */
export interface VerifierState {
    /** Observed tongue of the request */
    observedTongue: Tongue;
    /** Valid tongues (those that passed MAC/signature verification) */
    validTongues: Set<Tongue>;
    /** Current position in Poincaré ball */
    position: number[];
    /** Current discrete policy cell */
    policyCell: number[];
    /** Ring history (sequence of ring levels, oldest first) */
    ringHistory: RingLevel[];
    /** Approvals presented */
    approvals: Approval[];
    /** Shared secret from PQ KEM */
    sharedSecret: Uint8Array;
}
/**
 * Approval (for quorum predicate)
 */
export interface Approval {
    /** Approver identifier */
    approverId: string;
    /** Signature over egg ID + epoch */
    signature: Uint8Array;
    /** Timestamp */
    timestamp: number;
}
/**
 * Hatch result
 */
export type HatchResult = {
    success: true;
    plaintext: Uint8Array;
} | {
    success: false;
    output: Uint8Array;
};
/**
 * P_tongue: Tongue/domain predicate
 *
 * Solitary mode: τ = τ₀
 * Weighted multi-tongue: Σ w(t) ≥ W_min for t ∈ T_valid
 */
export declare function predicateTongue(egg: SacredEgg, state: VerifierState): boolean;
/**
 * Get ring level from radius in Poincaré ball
 */
export declare function getRingLevel(radius: number): RingLevel;
/**
 * P_geo: Geometric predicate (ring + cell)
 *
 * Checks:
 *   1. ring(u) ≤ ring_max
 *   2. cell ∈ V_allowed (if specified)
 *   3. d*(u) ≤ ε_geo (distance to nearest attractor, if specified)
 */
export declare function predicateGeo(egg: SacredEgg, state: VerifierState): boolean;
/**
 * P_path: Path predicate (monotone ring descent)
 *
 * Checks: ring(u₀) > ring(u₁) > ... > ring(u_K) AND ring(u_K) ≤ r_core
 *
 * This is a STATE EVOLUTION CONSTRAINT - one of the key claim elements.
 */
export declare function predicatePath(egg: SacredEgg, state: VerifierState): boolean;
/**
 * P_quorum: Quorum predicate
 *
 * Checks: |A| ≥ q AND all approvals verify
 */
export declare function predicateQuorum(egg: SacredEgg, state: VerifierState, verifyApproval: (approval: Approval, eggId: string) => boolean): boolean;
/**
 * Derive key from shared secret and domain separation tag
 *
 * K := HKDF(ss, DST, ℓ)
 * DST := Enc(τ₀) || Enc(ring) || Enc(cell) || Enc(pathDigest) || Enc(epoch)
 */
export declare function deriveKey(sharedSecret: Uint8Array, egg: SacredEgg, state: VerifierState): Promise<Uint8Array>;
/**
 * P_crypto: Cryptographic predicate (AEAD decryption)
 *
 * Returns plaintext if successful, null if failed
 */
export declare function predicateCrypto(egg: SacredEgg, state: VerifierState): Promise<Uint8Array | null>;
/**
 * HATCH: Open a Sacred Egg
 *
 * HATCH(E, s) ⟺ P_tongue ∧ P_geo ∧ P_path ∧ P_quorum ∧ P_crypto
 *
 * Decision rule:
 *   Open(E, s) = { M, if HATCH = true
 *                { ⊥, if HATCH = false  (fail-to-noise)
 *
 * @param egg - Sacred Egg to open
 * @param state - Verifier's observed state
 * @param verifyApproval - Function to verify approvals
 * @returns HatchResult with plaintext on success, noise on failure
 */
export declare function hatch(egg: SacredEgg, state: VerifierState, verifyApproval?: (approval: Approval, eggId: string) => boolean): Promise<HatchResult>;
/**
 * Create a Sacred Egg (encrypt plaintext with policy)
 */
export declare function createEgg(plaintext: Uint8Array, policy: EggPolicy, sharedSecret: Uint8Array, expectedState: VerifierState): Promise<SacredEgg>;
//# sourceMappingURL=sacredEggs.d.ts.map