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
// L6 Breathing + Phase-Lock Dynamics (optional)
// ═══════════════════════════════════════════════════════════════

/**
 * Optional runtime dynamics context.
 * If omitted, FluxStateGate behaves exactly as before (static policy).
 */
export interface FluxDynamicsContext {
  /** Wall clock time in seconds (or monotonic seconds). */
  tSec?: number;
  /** Breathing parameters for L6-like policy modulation. */
  breathing?: BreathingParams;
  /** Phase-lock context for ENTANGLED (swarm synchronization). */
  phase?: PhaseLockContext;
}

/** Breathing parameters (b(t) clamped to remain > 0). */
export interface BreathingParams {
  /** Angular frequency (rad/s). Default: 2π/60 (one minute cycle). */
  omega?: number;
  /** Amplitude A in b(t)=1 + A·sin(ωt). Recommended 0 ≤ A < 1. */
  amplitude?: number;
  /** Clamp lower bound for b(t). Default: 0.25 */
  min?: number;
  /** Clamp upper bound for b(t). Default: 2.5 */
  max?: number;
}

/** Phase-lock context for ENTANGLED (Kuramoto-lite). */
export interface PhaseLockContext {
  /** Self phase angle in radians. */
  selfTheta: number;
  /** Partner phase angle in radians. */
  partnerTheta: number;
  /** Score threshold [0,1] required to treat pair as "locked". Default: 0.8 */
  lockThreshold?: number;
  /** If true, an "unlocked" ENTANGLED pair becomes observe-only. Default: true. */
  unlockDisablesNavigation?: boolean;
}

function clamp(x: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, x));
}

/**
 * L6-style breathing factor: b(t) = 1 + A·sin(ωt), clamped to (min,max).
 * Not an isometry unless b(t)=1; this is a smooth ball-preserving diffeomorphism.
 */
export function breathingFactor(tSec: number, params: BreathingParams = {}): number {
  const omega = params.omega ?? (2 * Math.PI) / 60;
  const amplitude = params.amplitude ?? 0.25;
  const lo = params.min ?? 0.25;
  const hi = params.max ?? 2.5;
  const b = 1 + amplitude * Math.sin(omega * tSec);
  return clamp(b, lo, hi);
}

/**
 * Convert a static maxStepNorm into an effective bound under breathing.
 * b(t) > 1 ("expansion") tightens steps; b(t) < 1 ("contraction") relaxes steps.
 */
export function breathingAdjustedMaxStepNorm(
  baseMaxStepNorm: number | null,
  tSec: number,
  params?: BreathingParams
): number | null {
  if (baseMaxStepNorm === null) return null;
  const b = breathingFactor(tSec, params);
  return baseMaxStepNorm / b;
}

/** Circular distance on S^1 in [0, π]. */
export function circularDistanceRad(a: number, b: number): number {
  const twoPi = 2 * Math.PI;
  let d = (a - b) % twoPi;
  if (d < -Math.PI) d += twoPi;
  if (d > Math.PI) d -= twoPi;
  return Math.abs(d);
}

/**
 * Phase-lock score in [0,1]. 1 = identical phase, 0 = opposite phase.
 */
export function phaseLockScore(selfTheta: number, partnerTheta: number): number {
  return 1 - circularDistanceRad(selfTheta, partnerTheta) / Math.PI;
}

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
   * Derive an effective policy from the static policy using optional dynamics context.
   *
   * Enables:
   * - L6-like "breathing" modulation of maxStepNorm (time-dependent tightening/relaxing)
   * - Phase-locking checks for ENTANGLED (navigation disabled unless sufficiently locked)
   *
   * Determinism: given the same ctx inputs, the result is replayable/non-random.
   */
  private deriveEffectivePolicy(ctx?: FluxDynamicsContext): FluxAccessPolicy {
    const effective: FluxAccessPolicy = {
      ...this.policy,
      allowedOps: [...this.policy.allowedOps],
      allowedRealms: this.policy.allowedRealms === null ? null : [...this.policy.allowedRealms],
    };

    // L6: breathing-adjust step limits
    if (ctx?.tSec !== undefined) {
      effective.maxStepNorm = breathingAdjustedMaxStepNorm(
        effective.maxStepNorm,
        ctx.tSec,
        ctx.breathing
      );
    }

    // Phase-locking: ENTANGLED requires lock to allow navigation
    if (this.state === FluxState.ENTANGLED && ctx?.phase) {
      const score = phaseLockScore(ctx.phase.selfTheta, ctx.phase.partnerTheta);
      const threshold = ctx.phase.lockThreshold ?? 0.8;
      const disable = ctx.phase.unlockDisablesNavigation ?? true;

      if (disable && score < threshold) {
        // Remove movement ops; keep read/observe/encrypt
        effective.allowedOps = effective.allowedOps.filter(
          (op) =>
            op !== NavigationOp.FULL_NAVIGATE &&
            op !== NavigationOp.REALM_NAVIGATE &&
            op !== NavigationOp.LIMBIC_ONLY
        );

        // Defense-in-depth: tighten step norm when unlocked
        if (effective.maxStepNorm !== null) {
          const t = clamp((threshold - score) / Math.max(1e-9, threshold), 0, 1);
          effective.maxStepNorm = effective.maxStepNorm * (1 - 0.5 * t);
        }
      }
    }

    return effective;
  }

  /**
   * Check if a navigation operation to a target realm is allowed.
   *
   * @param targetRealm - Target Sacred Tongue realm
   * @param stepVector - The navigation step vector (to check magnitude)
   * @param ctx - Optional dynamics context for L6 breathing + phase-lock
   * @returns FluxGateResult with allowed/denied status
   */
  checkNavigation(targetRealm: RealmID, stepVector: number[], ctx?: FluxDynamicsContext): FluxGateResult {
    const policy = this.deriveEffectivePolicy(ctx);

    // Check operation type
    const requiredOp = policy.allowedRealms === null
      ? NavigationOp.FULL_NAVIGATE
      : NavigationOp.REALM_NAVIGATE;

    if (!policy.allowedOps.includes(requiredOp) &&
        !policy.allowedOps.includes(NavigationOp.LIMBIC_ONLY)) {
      return {
        allowed: false,
        reason: `Operation ${requiredOp} not permitted in ${this.state} state`,
        policy,
      };
    }

    // Check realm access (COLLAPSED uses dynamic nearest-realm check)
    if (this.state !== FluxState.COLLAPSED && policy.allowedRealms !== null) {
      if (!policy.allowedRealms.includes(targetRealm)) {
        return {
          allowed: false,
          reason: `Realm ${targetRealm} not accessible in ${this.state} state. Allowed: ${policy.allowedRealms.join(', ')}`,
          policy,
        };
      }
    }

    // Check step magnitude
    if (policy.maxStepNorm !== null) {
      const normSq = stepVector.reduce((sum, x) => sum + x * x, 0);
      if (normSq > policy.maxStepNorm * policy.maxStepNorm) {
        return {
          allowed: false,
          reason: `Step magnitude ‖v‖=${Math.sqrt(normSq).toFixed(4)} exceeds max ${policy.maxStepNorm} for ${this.state} state`,
          policy,
        };
      }
    }

    return { allowed: true, policy };
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
