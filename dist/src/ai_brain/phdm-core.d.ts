/**
 * @file phdm-core.ts
 * @module ai_brain/phdm-core
 * @layer Layer 6, Layer 8, Layer 11, Layer 13
 * @component Complete PHDM Core Integration
 * @version 1.0.0
 * @since 2026-02-08
 *
 * Integrates the full Polyhedral Hamiltonian Defense Manifold:
 * 1. Hamiltonian path with HMAC-chained keys (harmonic/phdm.ts)
 * 2. Kyber KEM K₀ seed derivation (crypto/pqc.ts + crypto/hkdf.ts)
 * 3. Geodesic monitoring with intrusion detection (snap threshold ε)
 * 4. 6D Langues space decomposition (4D intent + 2D temporal)
 * 5. Langues metric cost computation (exponential cost function)
 * 6. Flux state evolution driven by intrusion results
 *
 * Fills the gaps identified in the architecture review:
 * - K₀ = HKDF(HMAC(ss, intent || epoch), "PHDM-K0-v1", "phdm-hamiltonian-seed")
 * - 6D → (4D intent + 2D temporal) decomposition table
 * - PHDM geodesic monitoring wired into brain-integration pipeline
 * - Numerical intrusion detection with false-positive analysis
 */
import { type Point6D, type IntrusionResult, type Polyhedron } from '../harmonic/phdm.js';
import { FluxStateManager, type AgentFluxRecord } from './flux-states.js';
import { type ImmuneState } from './immune-response.js';
/**
 * The 6 Sacred Tongue dimensions mapped to semantic roles.
 *
 * Intent Space (4D):
 *   KO (x1) - Trust boundary: Kor'Aelin, boundaries of truth
 *   AV (x2) - Ethical alignment: Avali, ethical resonance
 *   RU (x3) - Runethic logic: logic gate patterns
 *   CA (x4) - Causal integrity: cause-effect chains
 *
 * Temporal Space (2D):
 *   UM (x5) - Memory/temporal coherence: Umbroth, deep memory
 *   DR (x6) - Predictive state: Draumric, dream/forecast
 */
export interface LanguesDecomposition {
    /** 4D intent subspace [KO, AV, RU, CA] */
    intent: [number, number, number, number];
    /** 2D temporal subspace [UM, DR] */
    temporal: [number, number];
    /** Full 6D vector */
    full: Point6D;
}
export declare const TONGUE_LABELS: readonly ["KO", "AV", "RU", "CA", "UM", "DR"];
export declare const INTENT_TONGUES: readonly ["KO", "AV", "RU", "CA"];
export declare const TEMPORAL_TONGUES: readonly ["UM", "DR"];
/**
 * Decompose a 6D Langues space point into intent + temporal subspaces.
 */
export declare function decomposeLangues(point: Point6D): LanguesDecomposition;
/**
 * Map 21D brain state vector to 6D Langues space.
 *
 * Uses the SCBE context (first 6D) as Langues coordinates:
 *   x1 (KO) = deviceTrust       (trust boundary)
 *   x2 (AV) = locationTrust     (ethical/spatial alignment)
 *   x3 (RU) = networkTrust      (logical connectivity)
 *   x4 (CA) = behaviorScore     (causal behavior)
 *   x5 (UM) = timeOfDay         (temporal coherence)
 *   x6 (DR) = intentAlignment   (predictive state)
 */
export declare function brainStateToLangues(state21D: number[]): Point6D;
/**
 * K₀ derivation parameters
 */
export interface K0DerivationParams {
    /** ML-KEM-768 shared secret (32 bytes) */
    sharedSecret: Uint8Array;
    /** Intent fingerprint (agent-specific identifier) */
    intentFingerprint: string;
    /** Epoch counter for temporal binding */
    epoch: number;
}
/**
 * Derive K₀ from Kyber KEM shared secret.
 *
 * K₀ = HKDF-SHA256(
 *   ikm = HMAC-SHA256(ss, intent_fingerprint || epoch),
 *   salt = "PHDM-K0-v1",
 *   info = "phdm-hamiltonian-seed",
 *   len = 32
 * )
 *
 * Binds the PHDM Hamiltonian path seed to:
 * 1. Post-quantum shared secret (quantum resistance)
 * 2. Agent's intent fingerprint (identity binding)
 * 3. Epoch (temporal freshness)
 */
export declare function deriveK0(params: K0DerivationParams): Buffer;
/**
 * Result from PHDM monitoring pipeline
 */
export interface PHDMMonitorResult {
    /** Intrusion detection result */
    intrusion: IntrusionResult;
    /** Langues space decomposition */
    langues: LanguesDecomposition;
    /** Langues metric cost */
    languesCost: number;
    /** Langues risk decision */
    languesDecision: 'ALLOW' | 'QUARANTINE' | 'DENY';
    /** Current Hamiltonian path step (which polyhedron) */
    hamiltonianStep: number;
    /** Name of current polyhedron */
    currentPolyhedron: string;
    /** HMAC key fingerprint at current step (first 16 hex chars) */
    keyFingerprint: string;
    /** Whether this state triggers PHDM escalation */
    phdmEscalation: boolean;
    /** Accumulated intrusion count */
    intrusionCount: number;
    /** Running rhythm pattern (last 16 bits) */
    rhythmPattern: string;
}
export interface PHDMCoreConfig {
    /** Snap threshold for geodesic deviation ε_snap (default: 0.1) */
    snapThreshold: number;
    /** Curvature threshold for intrusion (default: 0.5) */
    curvatureThreshold: number;
    /** Langues metric beta base (default: 1.0) */
    languesBetaBase: number;
    /** Langues metric risk thresholds [low, high] */
    languesRiskThresholds: [number, number];
    /** Maximum intrusions before forced DENY */
    maxIntrusionsBeforeDeny: number;
    /** Intrusion rate threshold for escalation */
    intrusionRateThreshold: number;
}
export declare const DEFAULT_PHDM_CORE_CONFIG: PHDMCoreConfig;
/**
 * Complete PHDM Core Integration
 *
 * Unifies:
 * 1. Hamiltonian path with HMAC-chained keys through 16 polyhedra
 * 2. Kyber KEM K₀ seed derivation (post-quantum binding)
 * 3. Geodesic monitoring with intrusion detection (snap threshold)
 * 4. 6D Langues space decomposition (4D intent + 2D temporal)
 * 5. Langues metric cost computation (exponential cost scaling)
 * 6. Flux state integration (intrusions penalize flux)
 *
 * The PHDM Core bridges the post-quantum key hierarchy
 * with the topological defense manifold and the Langues cost surface.
 */
export declare class PHDMCore {
    private readonly config;
    private readonly hamiltonianPath;
    private readonly detector;
    private pathKeys;
    private k0;
    private currentStep;
    private totalSteps;
    private intrusionCount;
    private rhythmBits;
    private readonly languesWeights;
    private readonly languesPhases;
    private readonly languesBetas;
    constructor(config?: Partial<PHDMCoreConfig>);
    /**
     * Initialize from Kyber KEM shared secret.
     * Derives K₀ and computes the full Hamiltonian path.
     */
    initializeFromKyber(params: K0DerivationParams): void;
    /**
     * Initialize with a raw master key (testing or non-Kyber contexts).
     */
    initializeWithKey(masterKey: Buffer): void;
    /** Get the derived K₀ */
    getK0(): Buffer | null;
    /** Get path key at a specific step */
    getPathKey(step: number): Buffer | null;
    /** Verify HMAC chain integrity */
    verifyChainIntegrity(): boolean;
    /**
     * Monitor an agent's state through the PHDM geodesic.
     *
     * Takes a 21D brain state, maps to 6D Langues space,
     * checks geodesic deviation, computes Langues cost.
     *
     * @param state21D - 21D brain state vector
     * @param t - Normalized time parameter [0, 1]
     */
    monitor(state21D: number[], t: number): PHDMMonitorResult;
    /**
     * Compute the Langues metric cost at a 6D point.
     * L(x,t) = Σ wₗ exp(βₗ · (dₗ + sin(ωₗt + φₗ)))
     */
    computeLanguesCost(point: Point6D, t: number): number;
    /** Evaluate Langues risk decision from cost value */
    evaluateLanguesRisk(cost: number): 'ALLOW' | 'QUARANTINE' | 'DENY';
    /** Get intrusion statistics */
    getStats(): {
        totalSteps: number;
        intrusionCount: number;
        intrusionRate: number;
        currentHamiltonianStep: number;
        currentPolyhedron: string;
        rhythmPattern: string;
        chainIntact: boolean;
    };
    /** Reset monitoring state (keeps keys) */
    resetMonitoring(): void;
    /** Get the 16 canonical polyhedra */
    getPolyhedra(): Polyhedron[];
    /**
     * Apply PHDM monitoring result to flux state evolution.
     *
     * Intrusions penalize flux value → agent loses access to higher polyhedra.
     * Creates feedback loop: deviation → intrusion → flux penalty → reduced access.
     */
    applyToFlux(fluxManager: FluxStateManager, agentId: string, monitorResult: PHDMMonitorResult, immuneState: ImmuneState): AgentFluxRecord;
}
//# sourceMappingURL=phdm-core.d.ts.map