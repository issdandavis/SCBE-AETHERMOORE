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

import { REALM_CENTERS } from './adaptiveNavigator.js';

// ═══════════════════════════════════════════════════════════════
// Flux State Enum
// ═══════════════════════════════════════════════════════════════

/** Flux states governing navigation access */
export enum FluxState {
  /** Full access — can navigate to any realm, perform any operation */
  POLLY = 'POLLY',
  /** Limited access — can observe all realms but navigate only to permitted set */
  SUPERPOSITION = 'SUPERPOSITION',
  /** Minimal access — can only navigate to the nearest/assigned realm */
  COLLAPSED = 'COLLAPSED',
  /** Bound access — position is entangled with a partner entity */
  ENTANGLED = 'ENTANGLED',
}

/** Navigation operation types */
export enum NavigationOp {
  /** Navigate to any realm via Möbius addition */
  FULL_NAVIGATE = 'FULL_NAVIGATE',
  /** Navigate only to a specific subset of realms */
  REALM_NAVIGATE = 'REALM_NAVIGATE',
  /** Navigate only to the nearest realm (limbic restriction) */
  LIMBIC_ONLY = 'LIMBIC_ONLY',
  /** Observe position/distance but cannot move */
  OBSERVE_ONLY = 'OBSERVE_ONLY',
  /** Encrypt/decrypt vectors for transport */
  ENCRYPT_TRANSPORT = 'ENCRYPT_TRANSPORT',
  /** Read the current position */
  READ_POSITION = 'READ_POSITION',
}

// ═══════════════════════════════════════════════════════════════
// Access Policy
// ═══════════════════════════════════════════════════════════════

/** Realm identifiers matching Sacred Tongues */
export type RealmID = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

const ALL_REALMS: RealmID[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];

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
export const FLUX_POLICIES: Record<FluxState, FluxAccessPolicy> = {
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

// ═══════════════════════════════════════════════════════════════
// Flux State Gate
// ═══════════════════════════════════════════════════════════════

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
export class FluxStateGate {
  private state: FluxState;
  private policy: FluxAccessPolicy;
  private partnerId?: string;

  constructor(initialState: FluxState = FluxState.POLLY, partnerId?: string) {
    this.state = initialState;
    this.policy = FLUX_POLICIES[initialState];
    this.partnerId = partnerId;
  }

  /** Get current flux state */
  getState(): FluxState {
    return this.state;
  }

  /** Get current access policy */
  getPolicy(): FluxAccessPolicy {
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
  transition(newState: FluxState): { success: boolean; reason?: string } {
    const valid = VALID_TRANSITIONS[this.state];
    if (!valid.includes(newState)) {
      return {
        success: false,
        reason: `Cannot transition from ${this.state} to ${newState}`,
      };
    }

    this.state = newState;
    this.policy = FLUX_POLICIES[newState];

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
  checkNavigation(targetRealm: RealmID, stepVector: number[]): FluxGateResult {
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
  checkEncrypt(): FluxGateResult {
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
  checkCollapsedRealm(currentPosition: number[], targetRealm: RealmID): FluxGateResult {
    if (this.state !== FluxState.COLLAPSED) {
      return { allowed: true, policy: this.policy };
    }

    // Find nearest realm
    let minDist = Infinity;
    let nearestRealm: RealmID = 'KO';

    for (const [realm, center] of Object.entries(REALM_CENTERS)) {
      const distSq = center.reduce(
        (sum: number, c: number, i: number) => sum + (c - currentPosition[i]) ** 2,
        0
      );
      if (distSq < minDist) {
        minDist = distSq;
        nearestRealm = realm as RealmID;
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
  getPartnerId(): string | undefined {
    return this.partnerId;
  }
}

// ═══════════════════════════════════════════════════════════════
// State Transition Rules
// ═══════════════════════════════════════════════════════════════

/** Valid state transitions */
const VALID_TRANSITIONS: Record<FluxState, FluxState[]> = {
  [FluxState.POLLY]: [FluxState.SUPERPOSITION, FluxState.COLLAPSED, FluxState.ENTANGLED],
  [FluxState.SUPERPOSITION]: [FluxState.COLLAPSED, FluxState.ENTANGLED, FluxState.POLLY],
  [FluxState.COLLAPSED]: [FluxState.POLLY],
  [FluxState.ENTANGLED]: [FluxState.COLLAPSED, FluxState.POLLY],
};

/**
 * Get valid transitions from a given state.
 */
export function getValidTransitions(state: FluxState): FluxState[] {
  return [...VALID_TRANSITIONS[state]];
}

/**
 * Determine the appropriate flux state from a coherence score.
 *
 * @param coherence - Intent validation coherence [0, 1]
 * @returns Recommended flux state
 */
export function coherenceToFluxState(coherence: number): FluxState {
  const c = Math.max(0, Math.min(1, coherence));
  if (c >= 0.8) return FluxState.POLLY;
  if (c >= 0.5) return FluxState.SUPERPOSITION;
  if (c >= 0.2) return FluxState.ENTANGLED;
  return FluxState.COLLAPSED;
}
