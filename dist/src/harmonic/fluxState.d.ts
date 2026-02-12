/**
 * @file fluxState.ts
 * @module harmonic/fluxState
 * @layer Layer 13
 * @component Flux-State Access Tiering
 * @version 1.0.0
 * @since 2026-02-07
 *
 * Flux-State Access Tiering for Poincaré ball navigation.
 *
 * Each agent/entity exists in one of four flux states that determine
 * which navigation operations they can perform. This is analogous to
 * quantum state superposition — the entity's "observability" constrains
 * its degrees of freedom in the navigation manifold.
 *
 * Flux States:
 * - POLLY:         Full navigation (all realms, all operations)
 * - SUPERPOSITION: Limited navigation (read-only on restricted realms)
 * - COLLAPSED:     Limbic-only (can only navigate to nearest realm)
 * - ENTANGLED:     Shared navigation (position bound to partner)
 *
 * This provides the simplest, most useful access control layer for
 * the Spiralverse navigation system.
 */
/** Flux states governing navigation access */
export declare enum FluxState {
    /** Full access — can navigate to any realm, perform any operation */
    POLLY = "POLLY",
    /** Limited access — can observe all realms but navigate only to permitted set */
    SUPERPOSITION = "SUPERPOSITION",
    /** Minimal access — can only navigate to the nearest/assigned realm */
    COLLAPSED = "COLLAPSED",
    /** Bound access — position is entangled with a partner entity */
    ENTANGLED = "ENTANGLED"
}
/** Navigation operation types */
export declare enum NavigationOp {
    /** Navigate to any realm via Möbius addition */
    FULL_NAVIGATE = "FULL_NAVIGATE",
    /** Navigate only to a specific subset of realms */
    REALM_NAVIGATE = "REALM_NAVIGATE",
    /** Navigate only to the nearest realm (limbic restriction) */
    LIMBIC_ONLY = "LIMBIC_ONLY",
    /** Observe position/distance but cannot move */
    OBSERVE_ONLY = "OBSERVE_ONLY",
    /** Encrypt/decrypt vectors for transport */
    ENCRYPT_TRANSPORT = "ENCRYPT_TRANSPORT",
    /** Read the current position */
    READ_POSITION = "READ_POSITION"
}
/** Realm identifiers matching Sacred Tongues */
export type RealmID = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
/** Access policy for a given flux state */
export interface FluxAccessPolicy {
    /** Which navigation operations are allowed */
    allowedOps: NavigationOp[];
    /** Which realms can be navigated to (null = all) */
    allowedRealms: RealmID[] | null;
    /** Maximum Möbius step magnitude (‖step‖ upper bound, null = unlimited) */
    maxStepNorm: number | null;
    /** Whether encrypted transport is permitted */
    canEncrypt: boolean;
    /** Human-readable description */
    description: string;
}
/** Default access policies per flux state */
export declare const FLUX_POLICIES: Record<FluxState, FluxAccessPolicy>;
/** Result of a flux state access check */
export interface FluxGateResult {
    /** Whether the operation is permitted */
    allowed: boolean;
    /** Reason for denial (if denied) */
    reason?: string;
    /** The effective policy that was applied */
    policy: FluxAccessPolicy;
}
/**
 * FluxStateGate enforces access restrictions based on the entity's
 * current flux state.
 *
 * @example
 * ```typescript
 * const gate = new FluxStateGate(FluxState.SUPERPOSITION);
 *
 * // Check if navigation to UM realm is allowed
 * const check = gate.checkNavigation('UM', [0, 0, 0, 0, 0.2, 0]);
 * if (!check.allowed) {
 *   console.log('Denied:', check.reason);
 * }
 * ```
 */
export declare class FluxStateGate {
    private state;
    private policy;
    private partnerId?;
    constructor(initialState?: FluxState, partnerId?: string);
    /** Get current flux state */
    getState(): FluxState;
    /** Get current access policy */
    getPolicy(): FluxAccessPolicy;
    /**
     * Transition to a new flux state.
     *
     * State transitions follow these rules:
     * - POLLY → any state (admin downgrade)
     * - SUPERPOSITION → COLLAPSED or ENTANGLED (decoherence)
     * - COLLAPSED → POLLY only (requires re-authentication)
     * - ENTANGLED → COLLAPSED or POLLY (disentanglement)
     */
    transition(newState: FluxState): {
        success: boolean;
        reason?: string;
    };
    /**
     * Check if a navigation operation to a target realm is allowed.
     *
     * @param targetRealm - Target Sacred Tongue realm
     * @param stepVector - The navigation step vector (to check magnitude)
     * @returns FluxGateResult with allowed/denied status
     */
    checkNavigation(targetRealm: RealmID, stepVector: number[]): FluxGateResult;
    /**
     * Check if encryption/decryption of vectors is allowed.
     */
    checkEncrypt(): FluxGateResult;
    /**
     * For COLLAPSED state: determine the nearest realm to a given position
     * and only allow navigation toward it.
     *
     * @param currentPosition - Current position in 6D Poincaré ball
     * @param targetRealm - Intended target realm
     * @returns Whether targetRealm is the nearest realm
     */
    checkCollapsedRealm(currentPosition: number[], targetRealm: RealmID): FluxGateResult;
    /** Get the partner ID for ENTANGLED state */
    getPartnerId(): string | undefined;
}
/**
 * Get valid transitions from a given state.
 */
export declare function getValidTransitions(state: FluxState): FluxState[];
/**
 * Determine the appropriate flux state from a coherence score.
 *
 * @param coherence - Intent validation coherence [0, 1]
 * @returns Recommended flux state
 */
export declare function coherenceToFluxState(coherence: number): FluxState;
//# sourceMappingURL=fluxState.d.ts.map