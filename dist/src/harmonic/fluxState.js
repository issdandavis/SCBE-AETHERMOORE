"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.FluxStateGate = exports.FLUX_POLICIES = exports.NavigationOp = exports.FluxState = void 0;
exports.getValidTransitions = getValidTransitions;
exports.coherenceToFluxState = coherenceToFluxState;
const adaptiveNavigator_js_1 = require("./adaptiveNavigator.js");
// ═══════════════════════════════════════════════════════════════
// Flux State Enum
// ═══════════════════════════════════════════════════════════════
/** Flux states governing navigation access */
var FluxState;
(function (FluxState) {
    /** Full access — can navigate to any realm, perform any operation */
    FluxState["POLLY"] = "POLLY";
    /** Limited access — can observe all realms but navigate only to permitted set */
    FluxState["SUPERPOSITION"] = "SUPERPOSITION";
    /** Minimal access — can only navigate to the nearest/assigned realm */
    FluxState["COLLAPSED"] = "COLLAPSED";
    /** Bound access — position is entangled with a partner entity */
    FluxState["ENTANGLED"] = "ENTANGLED";
})(FluxState || (exports.FluxState = FluxState = {}));
/** Navigation operation types */
var NavigationOp;
(function (NavigationOp) {
    /** Navigate to any realm via Möbius addition */
    NavigationOp["FULL_NAVIGATE"] = "FULL_NAVIGATE";
    /** Navigate only to a specific subset of realms */
    NavigationOp["REALM_NAVIGATE"] = "REALM_NAVIGATE";
    /** Navigate only to the nearest realm (limbic restriction) */
    NavigationOp["LIMBIC_ONLY"] = "LIMBIC_ONLY";
    /** Observe position/distance but cannot move */
    NavigationOp["OBSERVE_ONLY"] = "OBSERVE_ONLY";
    /** Encrypt/decrypt vectors for transport */
    NavigationOp["ENCRYPT_TRANSPORT"] = "ENCRYPT_TRANSPORT";
    /** Read the current position */
    NavigationOp["READ_POSITION"] = "READ_POSITION";
})(NavigationOp || (exports.NavigationOp = NavigationOp = {}));
const ALL_REALMS = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
/** Default access policies per flux state */
exports.FLUX_POLICIES = {
    [FluxState.POLLY]: {
        allowedOps: [
            NavigationOp.FULL_NAVIGATE,
            NavigationOp.REALM_NAVIGATE,
            NavigationOp.LIMBIC_ONLY,
            NavigationOp.OBSERVE_ONLY,
            NavigationOp.ENCRYPT_TRANSPORT,
            NavigationOp.READ_POSITION,
        ],
        allowedRealms: null, // all realms
        maxStepNorm: null, // no limit
        canEncrypt: true,
        description: 'Full navigation access — all realms, all operations',
    },
    [FluxState.SUPERPOSITION]: {
        allowedOps: [
            NavigationOp.REALM_NAVIGATE,
            NavigationOp.OBSERVE_ONLY,
            NavigationOp.ENCRYPT_TRANSPORT,
            NavigationOp.READ_POSITION,
        ],
        allowedRealms: ['KO', 'AV', 'RU'], // Control, I/O, Policy only
        maxStepNorm: 0.3,
        canEncrypt: true,
        description: 'Limited navigation — KO/AV/RU realms only, bounded steps',
    },
    [FluxState.COLLAPSED]: {
        allowedOps: [NavigationOp.LIMBIC_ONLY, NavigationOp.OBSERVE_ONLY, NavigationOp.READ_POSITION],
        allowedRealms: null, // determined dynamically by nearest realm
        maxStepNorm: 0.1,
        canEncrypt: false,
        description: 'Limbic-only — can only navigate to nearest realm',
    },
    [FluxState.ENTANGLED]: {
        allowedOps: [
            NavigationOp.REALM_NAVIGATE,
            NavigationOp.OBSERVE_ONLY,
            NavigationOp.ENCRYPT_TRANSPORT,
            NavigationOp.READ_POSITION,
        ],
        allowedRealms: ['KO', 'RU', 'UM'], // Control, Policy, Security
        maxStepNorm: 0.2,
        canEncrypt: true,
        description: 'Entangled navigation — position bound to partner, restricted realms',
    },
};
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
class FluxStateGate {
    state;
    policy;
    partnerId;
    constructor(initialState = FluxState.POLLY, partnerId) {
        this.state = initialState;
        this.policy = exports.FLUX_POLICIES[initialState];
        this.partnerId = partnerId;
    }
    /** Get current flux state */
    getState() {
        return this.state;
    }
    /** Get current access policy */
    getPolicy() {
        return { ...this.policy };
    }
    /**
     * Transition to a new flux state.
     *
     * State transitions follow these rules:
     * - POLLY → any state (admin downgrade)
     * - SUPERPOSITION → COLLAPSED or ENTANGLED (decoherence)
     * - COLLAPSED → POLLY only (requires re-authentication)
     * - ENTANGLED → COLLAPSED or POLLY (disentanglement)
     */
    transition(newState) {
        const valid = VALID_TRANSITIONS[this.state];
        if (!valid.includes(newState)) {
            return {
                success: false,
                reason: `Cannot transition from ${this.state} to ${newState}`,
            };
        }
        this.state = newState;
        this.policy = exports.FLUX_POLICIES[newState];
        if (newState !== FluxState.ENTANGLED) {
            this.partnerId = undefined;
        }
        return { success: true };
    }
    /**
     * Check if a navigation operation to a target realm is allowed.
     *
     * @param targetRealm - Target Sacred Tongue realm
     * @param stepVector - The navigation step vector (to check magnitude)
     * @returns FluxGateResult with allowed/denied status
     */
    checkNavigation(targetRealm, stepVector) {
        // Check operation type
        const requiredOp = this.policy.allowedRealms === null
            ? NavigationOp.FULL_NAVIGATE
            : NavigationOp.REALM_NAVIGATE;
        if (!this.policy.allowedOps.includes(requiredOp) &&
            !this.policy.allowedOps.includes(NavigationOp.LIMBIC_ONLY)) {
            return {
                allowed: false,
                reason: `Operation ${requiredOp} not permitted in ${this.state} state`,
                policy: this.policy,
            };
        }
        // Check realm access (COLLAPSED uses dynamic nearest-realm check)
        if (this.state !== FluxState.COLLAPSED && this.policy.allowedRealms !== null) {
            if (!this.policy.allowedRealms.includes(targetRealm)) {
                return {
                    allowed: false,
                    reason: `Realm ${targetRealm} not accessible in ${this.state} state. Allowed: ${this.policy.allowedRealms.join(', ')}`,
                    policy: this.policy,
                };
            }
        }
        // Check step magnitude
        if (this.policy.maxStepNorm !== null) {
            const normSq = stepVector.reduce((sum, x) => sum + x * x, 0);
            if (normSq > this.policy.maxStepNorm * this.policy.maxStepNorm) {
                return {
                    allowed: false,
                    reason: `Step magnitude ‖v‖=${Math.sqrt(normSq).toFixed(4)} exceeds max ${this.policy.maxStepNorm} for ${this.state} state`,
                    policy: this.policy,
                };
            }
        }
        return { allowed: true, policy: this.policy };
    }
    /**
     * Check if encryption/decryption of vectors is allowed.
     */
    checkEncrypt() {
        if (!this.policy.canEncrypt) {
            return {
                allowed: false,
                reason: `Encryption not permitted in ${this.state} state`,
                policy: this.policy,
            };
        }
        return { allowed: true, policy: this.policy };
    }
    /**
     * For COLLAPSED state: determine the nearest realm to a given position
     * and only allow navigation toward it.
     *
     * @param currentPosition - Current position in 6D Poincaré ball
     * @param targetRealm - Intended target realm
     * @returns Whether targetRealm is the nearest realm
     */
    checkCollapsedRealm(currentPosition, targetRealm) {
        if (this.state !== FluxState.COLLAPSED) {
            return { allowed: true, policy: this.policy };
        }
        // Find nearest realm
        let minDist = Infinity;
        let nearestRealm = 'KO';
        for (const [realm, center] of Object.entries(adaptiveNavigator_js_1.REALM_CENTERS)) {
            const distSq = center.reduce((sum, c, i) => sum + (c - currentPosition[i]) ** 2, 0);
            if (distSq < minDist) {
                minDist = distSq;
                nearestRealm = realm;
            }
        }
        if (targetRealm !== nearestRealm) {
            return {
                allowed: false,
                reason: `COLLAPSED state: can only navigate to nearest realm ${nearestRealm}, not ${targetRealm}`,
                policy: this.policy,
            };
        }
        return { allowed: true, policy: this.policy };
    }
    /** Get the partner ID for ENTANGLED state */
    getPartnerId() {
        return this.partnerId;
    }
}
exports.FluxStateGate = FluxStateGate;
// ═══════════════════════════════════════════════════════════════
// State Transition Rules
// ═══════════════════════════════════════════════════════════════
/** Valid state transitions */
const VALID_TRANSITIONS = {
    [FluxState.POLLY]: [FluxState.SUPERPOSITION, FluxState.COLLAPSED, FluxState.ENTANGLED],
    [FluxState.SUPERPOSITION]: [FluxState.COLLAPSED, FluxState.ENTANGLED, FluxState.POLLY],
    [FluxState.COLLAPSED]: [FluxState.POLLY],
    [FluxState.ENTANGLED]: [FluxState.COLLAPSED, FluxState.POLLY],
};
/**
 * Get valid transitions from a given state.
 */
function getValidTransitions(state) {
    return [...VALID_TRANSITIONS[state]];
}
/**
 * Determine the appropriate flux state from a coherence score.
 *
 * @param coherence - Intent validation coherence [0, 1]
 * @returns Recommended flux state
 */
function coherenceToFluxState(coherence) {
    const c = Math.max(0, Math.min(1, coherence));
    if (c >= 0.8)
        return FluxState.POLLY;
    if (c >= 0.5)
        return FluxState.SUPERPOSITION;
    if (c >= 0.2)
        return FluxState.ENTANGLED;
    return FluxState.COLLAPSED;
}
//# sourceMappingURL=fluxState.js.map