/**
 * @file sacredEggsGenesis.ts
 * @module harmonic/sacredEggsGenesis
 * @layer Layer 12, Layer 13
 * @component Sacred Eggs Genesis Gate — Agent-Only Scope (v1)
 * @version 1.0.0
 * @since 2026-02-11
 *
 * Deterministic genesis gate for agent spawning.
 * Scope A (v1): Sacred Eggs ONLY spawn agents — the narrowest, hardest target.
 *
 * The genesis gate is a 5-predicate conjunction with fail-to-noise semantics:
 *   GENESIS(E, s) ⟺ P_tongue ∧ P_geo ∧ P_path ∧ P_quorum ∧ (W ≥ T_genesis)
 *
 * Where W = Σ φ^(k_i) · w_i is the golden-ratio-weighted hatch weight,
 * T_genesis = φ³ ≈ 4.236 is the genesis threshold, and the geometric
 * boundary condition requires d* < d_max (GeoSeal).
 *
 * Output on success: GenesisCertificate containing:
 *   - Agent ID (cryptographic random UUID)
 *   - Realm binding (ring level + tongue domain)
 *   - Creation record (epoch, predicates passed, hatch weight)
 *   - Genesis seal (SHA-256 hash of all fields)
 *
 * Output on failure: Constant-length random noise (fail-to-noise).
 *
 * Key Theorems:
 *   T1: Fail-to-noise — |output_fail| ≡ |output_pass|, both random to observer
 *   T2: Monotone path — ring descent prevents lateral privilege escalation
 *   T3: φ-weighted threshold — T_genesis = φ³ requires ≥3 strong predicates
 *   T4: GeoSeal — d* < d_max bounds agent spawn to trusted region
 */
import { type Tongue, type RingLevel, type SacredEgg, type VerifierState, type Approval } from './sacredEggs.js';
/** Genesis threshold T_genesis = φ³ ≈ 4.236 */
export declare const GENESIS_THRESHOLD: number;
/** Default GeoSeal maximum distance */
export declare const DEFAULT_GEOSEAL_MAX_DISTANCE = 2;
/**
 * Genesis configuration for agent spawning.
 */
export interface GenesisConfig {
    /** Genesis threshold T_genesis (default: φ³ ≈ 4.236) */
    genesisThreshold: number;
    /** GeoSeal maximum Poincaré distance (default: 2.0) */
    geoSealMaxDistance: number;
    /** Triadic quorum mode: 2-of-3 or 3-of-3 (default: '2of3') */
    quorumMode: '2of3' | '3of3';
    /** Predicate importance ranks [tongue, geo, path, quorum, crypto] */
    predicateRanks: [number, number, number, number, number];
}
/**
 * Default genesis configuration.
 */
export declare const DEFAULT_GENESIS_CONFIG: GenesisConfig;
/**
 * Genesis certificate — proof that an agent was legitimately spawned.
 */
export interface GenesisCertificate {
    /** Agent identifier (UUID v4) */
    agentId: string;
    /** Epoch at which the agent was spawned */
    epoch: number;
    /** Tongue domain the agent belongs to */
    tongueDomain: Tongue;
    /** Ring level at spawn (trust radius) */
    ringLevel: RingLevel;
    /** Hatch weight W achieved */
    hatchWeight: number;
    /** Which predicates passed [tongue, geo, path, quorum, crypto] */
    predicatesPassed: [boolean, boolean, boolean, boolean, boolean];
    /** Genesis seal (hex-encoded SHA-256 of certificate fields) */
    genesisSeal: string;
}
/**
 * Genesis result — either a certificate or noise.
 */
export type GenesisResult = {
    spawned: true;
    certificate: GenesisCertificate;
    serialized: Uint8Array;
} | {
    spawned: false;
    output: Uint8Array;
};
/**
 * Genesis evaluation report (for diagnostics, not exposed on failure).
 */
export interface GenesisEvaluation {
    /** Per-predicate pass/fail */
    predicateResults: [boolean, boolean, boolean, boolean, boolean];
    /** Hatch weight W */
    hatchWeight: number;
    /** Whether W ≥ T_genesis */
    meetsThreshold: boolean;
    /** GeoSeal distance d* */
    geoSealDistance: number;
    /** Whether d* < d_max */
    geoSealPassed: boolean;
    /** Overall genesis decision */
    genesisGranted: boolean;
}
/**
 * Compute golden-ratio hatch weight W = Σ φ^(k_i) · w_i.
 *
 * Each predicate i has an importance rank k_i and a pass score w_i (0 or 1).
 * The φ-weighting ensures high-rank predicates contribute exponentially more.
 *
 * @param passed - Boolean array of predicate pass results
 * @param ranks - Importance rank for each predicate (lower = more important)
 */
export declare function computeHatchWeight(passed: boolean[], ranks?: number[]): number;
/**
 * Compute Poincaré distance from position to origin (GeoSeal distance).
 *
 * d* = 2 · arctanh(‖u‖) for a point u in the Poincaré ball.
 * For positions already in the ball (‖u‖ < 1), this gives the
 * hyperbolic distance from center.
 */
export declare function geoSealDistance(position: number[]): number;
/**
 * Evaluate the genesis gate predicates.
 *
 * Evaluates all 5 predicates and computes the hatch weight.
 * This is the diagnostic function — it does NOT produce certificates.
 *
 * @param egg - Sacred Egg policy container
 * @param state - Current verifier state
 * @param config - Genesis configuration
 * @param verifyApproval - Approval verification callback
 */
export declare function evaluateGenesis(egg: SacredEgg, state: VerifierState, config?: Partial<GenesisConfig>, verifyApproval?: (approval: Approval, eggId: string) => boolean): GenesisEvaluation;
/**
 * GENESIS: Attempt to spawn an agent via Sacred Egg genesis gate.
 *
 * This is the primary entry point for agent creation in v1.
 * The gate evaluates all predicates, computes the φ-weighted hatch weight,
 * checks GeoSeal boundary, and either produces a GenesisCertificate
 * or returns indistinguishable random noise (fail-to-noise).
 *
 * Constant-time: Both success and failure paths produce output
 * of identical length, making the two cases indistinguishable
 * to a timing side-channel observer.
 *
 * @param egg - Sacred Egg policy container
 * @param state - Current verifier state
 * @param config - Genesis configuration
 * @param verifyApproval - Approval verification callback
 * @returns GenesisResult — spawned certificate or noise
 */
export declare function genesis(egg: SacredEgg, state: VerifierState, config?: Partial<GenesisConfig>, verifyApproval?: (approval: Approval, eggId: string) => boolean): GenesisResult;
/**
 * Verify a genesis certificate's seal integrity.
 *
 * Recomputes the seal from the certificate fields and compares.
 */
export declare function verifyCertificateSeal(cert: GenesisCertificate): boolean;
//# sourceMappingURL=sacredEggsGenesis.d.ts.map