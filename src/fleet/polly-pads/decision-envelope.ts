/**
 * @file decision-envelope.ts
 * @module fleet/polly-pads/decision-envelope
 * @layer Layer 12, Layer 13
 * @component Decision Envelope — Pre-Authorized Autonomy Boundaries
 * @version 3.2.4
 *
 * Extends the Polly Pad `canPromoteToSafe()` mechanism with Decision Envelopes:
 * pre-authorized autonomy boundaries signed by ground control for missions
 * where human-in-the-loop has 4-24 minute communication latency (Mars, deep space).
 *
 * Ground control signs an envelope defining what actions are AUTO_ALLOW,
 * which require QUARANTINE (BFT quorum), and which are DENY.
 * The SCBE pipeline (L12 harmonic wall + L13 decision gate) still runs as
 * a belt-and-suspenders check even for AUTO_ALLOW actions.
 *
 * Emergency override keys allow DENY-boundary actions to execute when
 * comms are unavailable and crew safety is at stake.
 *
 * Envelope lifecycle:
 *   1. Ground control creates + signs envelope for a mission phase
 *   2. Envelope uplinked during comms window
 *   3. EnvelopeManager loads envelope, validates signature + time window
 *   4. Actions evaluated against envelope rules + SCBE pipeline
 *   5. Expired/missing envelopes queue actions for next comms window
 */

import { createHash } from 'crypto';
import {
  scbeDecide,
  harmonicCost,
  type SCBEThresholds,
  DEFAULT_THRESHOLDS,
} from '../../harmonic/voxelRecord.js';
import type { UnitState } from '../polly-pad-runtime.js';
import type { Decision } from '../../harmonic/scbe_voxel_types.js';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/** Envelope boundary types — what an action is classified as within the envelope */
export type EnvelopeBoundary = 'AUTO_ALLOW' | 'QUARANTINE' | 'DENY';

/**
 * Mission phase for phase-based envelope selection.
 *
 * Covers the full lifecycle of a Mars/deep-space mission from launch
 * through surface operations and return.
 */
export type MissionPhase =
  | 'LAUNCH'
  | 'TRANSIT'
  | 'ORBIT_INSERT'
  | 'DESCENT'
  | 'LANDING'
  | 'SURFACE_OPS'
  | 'EMERGENCY_OPS'
  | 'RETURN_PREP'
  | 'ASCENT'
  | 'TRANSIT_HOME'
  | 'REENTRY';

/** Communication state between unit and ground control */
export type CommsState = 'LIVE' | 'DELAYED' | 'BLACKOUT';

/**
 * Action category for envelope matching.
 *
 * Each action executed by an autonomous unit is categorized by domain
 * and risk level so envelope rules can match against it.
 */
export interface ActionCategory {
  /** Unique action identifier */
  id: string;
  /** Domain of the action (e.g., 'navigation', 'sampling', 'habitat', 'power') */
  domain: string;
  /** Risk classification of this action */
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
}

/**
 * A single envelope rule mapping action patterns to boundary types.
 *
 * Rules are matched in order; first match wins. The pattern field uses
 * glob-like syntax: `*` matches any segment, `**` matches any depth.
 * Example patterns: `navigation.*`, `sampling.drill.*`, `power.shutdown`.
 */
export interface EnvelopeRule {
  /** Action pattern (glob-like matching on `domain.riskLevel` or `domain.*`) */
  pattern: string;
  /** What boundary this action falls under */
  boundary: EnvelopeBoundary;
  /** Optional: max executions within this envelope's validity window */
  maxExecutions?: number;
  /** Optional: resource floor (don't allow if resource below this) */
  resourceFloor?: { resource: string; minimum: number };
}

/**
 * The Decision Envelope — signed by ground control.
 *
 * A time-bounded, phase-scoped authorization document that pre-approves
 * categories of actions for autonomous execution. Signed with ML-DSA-65
 * in production (sha256 placeholder in dev).
 */
export interface DecisionEnvelope {
  /** Unique envelope ID */
  id: string;
  /** Mission phase this envelope applies to */
  missionPhase: MissionPhase;
  /** Human-readable label (e.g., "surface_ops_sol_47") */
  label: string;
  /** Valid time window start (epoch ms) */
  validFrom: number;
  /** Valid time window end (epoch ms) */
  validUntil: number;
  /** Rules defining what actions are allowed, quarantined, or denied */
  rules: EnvelopeRule[];
  /** SCBE thresholds override for this phase */
  thresholds: SCBEThresholds;
  /** Ground control signature (ML-DSA-65 in production, sha256 placeholder) */
  signature: string;
  /** Counter-signature (mission commander) */
  counterSignature?: string;
  /** Emergency override key hash (for DENY override in emergencies) */
  emergencyKeyHash?: string;
  /** Epoch when this was signed */
  signedAt: number;
  /** Who signed it (ground controller ID) */
  signedBy: string;
}

/**
 * Result of envelope evaluation for a given action.
 *
 * Combines the envelope boundary, the SCBE decision, and comms state
 * into a final actionable decision.
 */
export interface EnvelopeDecision {
  /** The boundary decision from the envelope rule */
  boundary: EnvelopeBoundary;
  /** The SCBE decision (may differ from boundary) */
  scbeDecision: Decision;
  /** Combined final decision */
  finalDecision: 'EXECUTE' | 'QUORUM_REQUIRED' | 'DENIED' | 'QUEUED';
  /** Reason for the decision */
  reason: string;
  /** Rule that matched (if any) */
  matchedRule?: EnvelopeRule;
  /** Whether this was envelope-approved or required live human */
  autonomousApproval: boolean;
}

// ═══════════════════════════════════════════════════════════════
// Glob-like Pattern Matching
// ═══════════════════════════════════════════════════════════════

/**
 * Match an action's identity string against a glob-like pattern.
 *
 * Supported wildcards:
 * - `*`  matches exactly one segment (between dots)
 * - `**` matches zero or more segments
 *
 * The action identity is constructed as `domain.riskLevel`.
 *
 * @param identity - The action identity string (e.g., "navigation.low")
 * @param pattern  - The glob pattern (e.g., "navigation.*", "**.critical")
 * @returns true if the pattern matches
 */
function globMatch(identity: string, pattern: string): boolean {
  const identityParts = identity.split('.');
  const patternParts = pattern.split('.');

  let ip = 0;
  let pp = 0;

  while (ip < identityParts.length && pp < patternParts.length) {
    const pat = patternParts[pp];

    if (pat === '**') {
      // ** matches zero or more segments
      // If ** is the last pattern part, it matches everything remaining
      if (pp === patternParts.length - 1) return true;

      // Try matching ** against 0..N identity segments
      for (let skip = 0; skip <= identityParts.length - ip; skip++) {
        const remainingIdentity = identityParts.slice(ip + skip).join('.');
        const remainingPattern = patternParts.slice(pp + 1).join('.');
        if (globMatch(remainingIdentity, remainingPattern)) return true;
      }
      return false;
    }

    if (pat === '*') {
      // * matches exactly one segment
      ip++;
      pp++;
      continue;
    }

    // Literal match
    if (pat !== identityParts[ip]) return false;
    ip++;
    pp++;
  }

  // Handle trailing ** in pattern
  while (pp < patternParts.length && patternParts[pp] === '**') pp++;

  return ip === identityParts.length && pp === patternParts.length;
}

// ═══════════════════════════════════════════════════════════════
// Signature Helpers
// ═══════════════════════════════════════════════════════════════

/**
 * Compute the canonical digest of an envelope's content fields.
 *
 * Used for both signing and verification. Excludes the signature and
 * counterSignature fields from the digest input.
 *
 * @param envelope - The envelope to digest
 * @returns hex-encoded sha256 digest
 */
function envelopeDigest(envelope: DecisionEnvelope): string {
  const canonical = JSON.stringify({
    id: envelope.id,
    missionPhase: envelope.missionPhase,
    label: envelope.label,
    validFrom: envelope.validFrom,
    validUntil: envelope.validUntil,
    rules: envelope.rules,
    thresholds: envelope.thresholds,
    signedAt: envelope.signedAt,
    signedBy: envelope.signedBy,
  });
  return createHash('sha256').update(canonical, 'utf-8').digest('hex');
}

/**
 * Compute sha256 signature placeholder for an envelope.
 *
 * In production, this would use ML-DSA-65 (NIST FIPS 204) with the
 * ground controller's private key. This placeholder uses HMAC-SHA256
 * with the signer ID as the key material.
 *
 * @param envelope - The envelope to sign (without signature field)
 * @param signerKey - Key material for signing (signer ID in dev mode)
 * @returns hex-encoded sha256 signature placeholder
 */
function computeSignature(envelope: DecisionEnvelope, signerKey: string): string {
  const digest = envelopeDigest(envelope);
  return createHash('sha256')
    .update(`${signerKey}:${digest}`, 'utf-8')
    .digest('hex');
}

// ═══════════════════════════════════════════════════════════════
// Core Functions
// ═══════════════════════════════════════════════════════════════

/**
 * Validate an envelope's signature and time window.
 *
 * Checks:
 * 1. Envelope has a non-empty signature
 * 2. Signature matches the canonical envelope digest
 * 3. Current time falls within [validFrom, validUntil]
 * 4. validUntil > validFrom (sane time window)
 *
 * @param envelope - The envelope to validate
 * @param now - Current epoch ms (defaults to Date.now())
 * @returns Validation result with reason on failure
 */
export function validateEnvelope(
  envelope: DecisionEnvelope,
  now?: number
): { valid: boolean; reason?: string } {
  const currentTime = now ?? Date.now();

  // Check signature presence
  if (!envelope.signature || envelope.signature.length === 0) {
    return { valid: false, reason: 'Missing envelope signature' };
  }

  // Verify signature against digest
  const expectedSig = computeSignature(envelope, envelope.signedBy);
  if (envelope.signature !== expectedSig) {
    return { valid: false, reason: 'Invalid envelope signature' };
  }

  // Check time window sanity
  if (envelope.validUntil <= envelope.validFrom) {
    return { valid: false, reason: 'Invalid time window: validUntil must be after validFrom' };
  }

  // Check if envelope has started
  if (currentTime < envelope.validFrom) {
    return { valid: false, reason: 'Envelope not yet valid (before validFrom)' };
  }

  // Check if envelope has expired
  if (currentTime > envelope.validUntil) {
    return { valid: false, reason: 'Envelope expired (past validUntil)' };
  }

  return { valid: true };
}

/**
 * Match an action against envelope rules.
 *
 * The action identity is constructed as `domain.riskLevel` and matched
 * against each rule's pattern in order. First match wins.
 *
 * @param action - The action category to match
 * @param rules - The envelope rules to match against
 * @returns The first matching rule, or null if no rule matches
 */
export function matchAction(action: ActionCategory, rules: EnvelopeRule[]): EnvelopeRule | null {
  const identity = `${action.domain}.${action.riskLevel}`;

  for (const rule of rules) {
    if (globMatch(identity, rule.pattern)) {
      return rule;
    }
  }

  return null;
}

/**
 * Envelope-aware promotion check -- replaces canPromoteToSafe() for space missions.
 *
 * Decision logic:
 * 1. Check envelope validity (time window, signature)
 * 2. Match action against envelope rules
 * 3. If AUTO_ALLOW: check SCBE decision still passes (belt + suspenders)
 *    - If SCBE says ALLOW: finalDecision = EXECUTE (autonomous)
 *    - If SCBE says QUARANTINE: finalDecision = QUORUM_REQUIRED (override envelope)
 *    - If SCBE says DENY: finalDecision = DENIED (SCBE always wins)
 * 4. If QUARANTINE: require BFT quorum (4/6) from squad
 *    - If quorum met and SCBE != DENY: finalDecision = EXECUTE
 *    - Otherwise: QUORUM_REQUIRED or DENIED
 * 5. If DENY: reject unless emergency key is provided and validated
 * 6. If no envelope or expired: queue for next comms window
 *
 * @param action - The action to evaluate
 * @param envelope - The active decision envelope (or null if none)
 * @param state - The unit's current governance state
 * @param commsState - Current communication state
 * @param quorumVotes - Number of BFT quorum votes (if available)
 * @param emergencyKey - Emergency override key (if provided)
 * @returns The combined envelope decision
 */
export function envelopeDecide(
  action: ActionCategory,
  envelope: DecisionEnvelope | null,
  state: UnitState,
  commsState: CommsState,
  quorumVotes?: number,
  emergencyKey?: string
): EnvelopeDecision {
  // ── No envelope: queue for comms window ──────────────────────
  if (!envelope) {
    const scbeResult = scbeDecide(state.dStar, state.coherence, state.hEff, DEFAULT_THRESHOLDS);
    return {
      boundary: 'DENY',
      scbeDecision: scbeResult,
      finalDecision: 'QUEUED',
      reason: 'No active envelope; action queued for next comms window',
      autonomousApproval: false,
    };
  }

  // ── Validate envelope ────────────────────────────────────────
  const validation = validateEnvelope(envelope);
  if (!validation.valid) {
    const scbeResult = scbeDecide(
      state.dStar,
      state.coherence,
      state.hEff,
      envelope.thresholds,
    );
    return {
      boundary: 'DENY',
      scbeDecision: scbeResult,
      finalDecision: 'QUEUED',
      reason: `Envelope invalid: ${validation.reason}; action queued for next comms window`,
      autonomousApproval: false,
    };
  }

  // ── Run SCBE pipeline (always — belt + suspenders) ───────────
  const scbeResult = scbeDecide(
    state.dStar,
    state.coherence,
    state.hEff,
    envelope.thresholds,
  );

  // ── Match action against envelope rules ──────────────────────
  const matchedRule = matchAction(action, envelope.rules);

  if (!matchedRule) {
    // No rule matches — action not covered by this envelope
    return {
      boundary: 'DENY',
      scbeDecision: scbeResult,
      finalDecision: commsState === 'BLACKOUT' ? 'QUEUED' : 'QUEUED',
      reason: 'Action not covered by any envelope rule; queued for ground control review',
      autonomousApproval: false,
    };
  }

  const boundary = matchedRule.boundary;

  // ── AUTO_ALLOW: envelope says ok, but SCBE must also agree ───
  if (boundary === 'AUTO_ALLOW') {
    if (scbeResult === 'ALLOW') {
      return {
        boundary,
        scbeDecision: scbeResult,
        finalDecision: 'EXECUTE',
        reason: 'Envelope AUTO_ALLOW confirmed by SCBE ALLOW',
        matchedRule,
        autonomousApproval: true,
      };
    }

    if (scbeResult === 'QUARANTINE') {
      return {
        boundary,
        scbeDecision: scbeResult,
        finalDecision: 'QUORUM_REQUIRED',
        reason: 'Envelope AUTO_ALLOW overridden by SCBE QUARANTINE; BFT quorum required',
        matchedRule,
        autonomousApproval: false,
      };
    }

    // SCBE says DENY — SCBE always wins, even over envelope
    return {
      boundary,
      scbeDecision: scbeResult,
      finalDecision: 'DENIED',
      reason: 'Envelope AUTO_ALLOW overridden by SCBE DENY; action denied',
      matchedRule,
      autonomousApproval: false,
    };
  }

  // ── QUARANTINE: require BFT quorum (4/6) ─────────────────────
  if (boundary === 'QUARANTINE') {
    // SCBE DENY always wins
    if (scbeResult === 'DENY') {
      return {
        boundary,
        scbeDecision: scbeResult,
        finalDecision: 'DENIED',
        reason: 'Envelope QUARANTINE + SCBE DENY; action denied',
        matchedRule,
        autonomousApproval: false,
      };
    }

    // Require BFT quorum of 4/6
    if (quorumVotes !== undefined && quorumVotes >= 4) {
      return {
        boundary,
        scbeDecision: scbeResult,
        finalDecision: 'EXECUTE',
        reason: `Envelope QUARANTINE resolved by BFT quorum (${quorumVotes}/6)`,
        matchedRule,
        autonomousApproval: false,
      };
    }

    return {
      boundary,
      scbeDecision: scbeResult,
      finalDecision: 'QUORUM_REQUIRED',
      reason: `Envelope QUARANTINE; BFT quorum required (have ${quorumVotes ?? 0}/4 needed)`,
      matchedRule,
      autonomousApproval: false,
    };
  }

  // ── DENY: reject unless emergency key is provided ────────────
  if (boundary === 'DENY') {
    // Check emergency override
    if (emergencyKey && envelope.emergencyKeyHash) {
      if (validateEmergencyKey(emergencyKey, envelope)) {
        // Emergency override — but still respect SCBE DENY
        if (scbeResult === 'DENY') {
          return {
            boundary,
            scbeDecision: scbeResult,
            finalDecision: 'DENIED',
            reason: 'Emergency key accepted but SCBE DENY cannot be overridden',
            matchedRule,
            autonomousApproval: false,
          };
        }

        return {
          boundary,
          scbeDecision: scbeResult,
          finalDecision: 'EXECUTE',
          reason: 'Envelope DENY overridden by valid emergency key',
          matchedRule,
          autonomousApproval: false,
        };
      }
    }

    return {
      boundary,
      scbeDecision: scbeResult,
      finalDecision: 'DENIED',
      reason: 'Envelope DENY; action denied',
      matchedRule,
      autonomousApproval: false,
    };
  }

  // Unreachable — all boundary types handled above
  return {
    boundary: 'DENY',
    scbeDecision: scbeResult,
    finalDecision: 'DENIED',
    reason: 'Unknown boundary type; action denied',
    autonomousApproval: false,
  };
}

/**
 * Create a signed envelope (ground control side).
 *
 * Generates a unique envelope ID, computes the valid time window from
 * the current time + validHours, and signs the envelope with a sha256
 * placeholder signature. In production, this would use ML-DSA-65.
 *
 * @param params - Envelope creation parameters
 * @returns A fully signed DecisionEnvelope
 */
export function createEnvelope(params: {
  missionPhase: MissionPhase;
  label: string;
  validHours: number;
  rules: EnvelopeRule[];
  thresholds?: SCBEThresholds;
  signedBy: string;
  emergencyKey?: string;
}): DecisionEnvelope {
  const now = Date.now();
  const validFrom = now;
  const validUntil = now + params.validHours * 60 * 60 * 1000;

  // Generate deterministic envelope ID from content
  const idSeed = `${params.label}:${params.missionPhase}:${now}:${params.signedBy}`;
  const id = createHash('sha256').update(idSeed, 'utf-8').digest('hex').slice(0, 32);

  // Compute emergency key hash if provided
  let emergencyKeyHash: string | undefined;
  if (params.emergencyKey) {
    emergencyKeyHash = createHash('sha256')
      .update(params.emergencyKey, 'utf-8')
      .digest('hex');
  }

  // Build the envelope without signature first
  const envelope: DecisionEnvelope = {
    id,
    missionPhase: params.missionPhase,
    label: params.label,
    validFrom,
    validUntil,
    rules: params.rules,
    thresholds: params.thresholds ?? { ...DEFAULT_THRESHOLDS },
    signature: '', // placeholder — will be computed below
    emergencyKeyHash,
    signedAt: now,
    signedBy: params.signedBy,
  };

  // Sign the envelope
  envelope.signature = computeSignature(envelope, params.signedBy);

  return envelope;
}

/**
 * Check if an emergency key matches the envelope's emergency hash.
 *
 * Emergency keys are a last-resort mechanism for crew safety when
 * comms are unavailable. The key is sha256-hashed and compared against
 * the envelope's pre-stored hash.
 *
 * @param key - The emergency key to validate
 * @param envelope - The envelope containing the expected hash
 * @returns true if the key hash matches
 */
export function validateEmergencyKey(key: string, envelope: DecisionEnvelope): boolean {
  if (!envelope.emergencyKeyHash) return false;
  const keyHash = createHash('sha256').update(key, 'utf-8').digest('hex');
  return keyHash === envelope.emergencyKeyHash;
}

// ═══════════════════════════════════════════════════════════════
// EnvelopeManager Class
// ═══════════════════════════════════════════════════════════════

/**
 * Manages active decision envelopes for a unit/squad.
 *
 * Responsibilities:
 * - Stores current and queued envelopes
 * - Handles phase transitions (auto-activates queued envelopes)
 * - Tracks execution counts per rule pattern
 * - Queues actions for comms window when no valid envelope exists
 * - Enforces maxExecutions limits on envelope rules
 *
 * Usage:
 * ```ts
 * const manager = new EnvelopeManager('DELAYED');
 * manager.loadEnvelope(envelopeFromGroundControl);
 * const decision = manager.evaluate(action, unitState);
 * if (decision.finalDecision === 'EXECUTE') { ... }
 * ```
 */
export class EnvelopeManager {
  /** Currently active envelope (if valid) */
  private activeEnvelope: DecisionEnvelope | null = null;
  /** Envelopes queued for future activation */
  private queuedEnvelopes: DecisionEnvelope[] = [];
  /** Execution count per rule pattern within the active envelope */
  private executionCounts: Map<string, number> = new Map();
  /** Actions queued for next comms window (when no valid envelope) */
  private actionQueue: Array<{ action: ActionCategory; queuedAt: number }> = [];
  /** Current communication state */
  private commsState: CommsState;

  /**
   * Create an EnvelopeManager.
   *
   * @param initialCommsState - Initial comms state (defaults to 'DELAYED')
   */
  constructor(initialCommsState?: CommsState) {
    this.commsState = initialCommsState ?? 'DELAYED';
  }

  /**
   * Load a new envelope (e.g., received from ground control).
   *
   * If the envelope's mission phase matches the currently active envelope's
   * phase, it replaces the active envelope (newer envelope wins).
   * Otherwise, it is queued for future phase transitions.
   *
   * Loading a new active envelope resets execution counts.
   *
   * @param envelope - The envelope to load
   */
  loadEnvelope(envelope: DecisionEnvelope): void {
    const validation = validateEnvelope(envelope);

    if (!validation.valid) {
      // Still queue it — it might become valid later (e.g., future validFrom)
      this.queuedEnvelopes.push(envelope);
      return;
    }

    if (!this.activeEnvelope) {
      // No active envelope — activate this one
      this.activeEnvelope = envelope;
      this.executionCounts.clear();
      return;
    }

    if (envelope.missionPhase === this.activeEnvelope.missionPhase) {
      // Same phase — replace with newer envelope
      if (envelope.signedAt >= this.activeEnvelope.signedAt) {
        this.activeEnvelope = envelope;
        this.executionCounts.clear();
      } else {
        // Older envelope for same phase — queue it
        this.queuedEnvelopes.push(envelope);
      }
      return;
    }

    // Different phase — queue for future transition
    this.queuedEnvelopes.push(envelope);
  }

  /**
   * Get the currently active envelope.
   *
   * @returns The active envelope, or null if none is active
   */
  getActiveEnvelope(): DecisionEnvelope | null {
    return this.activeEnvelope;
  }

  /**
   * Check and execute an action through the envelope.
   *
   * This is the primary evaluation entry point. It:
   * 1. Checks if the active envelope is still valid (auto-expires)
   * 2. Checks maxExecutions limits
   * 3. Delegates to envelopeDecide() for the core decision
   * 4. Increments execution counts on EXECUTE
   * 5. Queues actions when no valid envelope exists
   *
   * @param action - The action to evaluate
   * @param state - The unit's current governance state
   * @param quorumVotes - Number of BFT quorum votes (if available)
   * @param emergencyKey - Emergency override key (if provided)
   * @returns The combined envelope decision
   */
  evaluate(
    action: ActionCategory,
    state: UnitState,
    quorumVotes?: number,
    emergencyKey?: string
  ): EnvelopeDecision {
    // Auto-expire active envelope if past validUntil
    if (this.activeEnvelope) {
      const validation = validateEnvelope(this.activeEnvelope);
      if (!validation.valid) {
        // Try to activate a queued envelope for the same phase
        this.tryActivateQueued(this.activeEnvelope.missionPhase);
      }
    }

    // Check maxExecutions limit before deciding
    if (this.activeEnvelope) {
      const matchedRule = matchAction(action, this.activeEnvelope.rules);
      if (matchedRule && matchedRule.maxExecutions !== undefined) {
        const currentCount = this.executionCounts.get(matchedRule.pattern) ?? 0;
        if (currentCount >= matchedRule.maxExecutions) {
          const scbeResult = scbeDecide(
            state.dStar,
            state.coherence,
            state.hEff,
            this.activeEnvelope.thresholds,
          );
          return {
            boundary: matchedRule.boundary,
            scbeDecision: scbeResult,
            finalDecision: 'DENIED',
            reason: `Max executions reached for rule "${matchedRule.pattern}" (${currentCount}/${matchedRule.maxExecutions})`,
            matchedRule,
            autonomousApproval: false,
          };
        }
      }
    }

    // Delegate to core decision logic
    const decision = envelopeDecide(
      action,
      this.activeEnvelope,
      state,
      this.commsState,
      quorumVotes,
      emergencyKey,
    );

    // Track execution count on EXECUTE
    if (decision.finalDecision === 'EXECUTE' && decision.matchedRule) {
      const pattern = decision.matchedRule.pattern;
      const current = this.executionCounts.get(pattern) ?? 0;
      this.executionCounts.set(pattern, current + 1);
    }

    // Queue actions that couldn't be decided
    if (decision.finalDecision === 'QUEUED') {
      this.actionQueue.push({ action, queuedAt: Date.now() });
    }

    return decision;
  }

  /**
   * Update the communication state.
   *
   * @param state - New comms state
   */
  setCommsState(state: CommsState): void {
    this.commsState = state;
  }

  /**
   * Get the current communication state.
   *
   * @returns Current CommsState
   */
  getCommsState(): CommsState {
    return this.commsState;
  }

  /**
   * Get queued actions (for syncing during comms window).
   *
   * Returns a copy of the queue without draining it. Use drainQueue()
   * to consume and clear the queue after successful comms sync.
   *
   * @returns Array of queued actions with timestamps
   */
  getActionQueue(): Array<{ action: ActionCategory; queuedAt: number }> {
    return [...this.actionQueue];
  }

  /**
   * Drain action queue (after comms sync).
   *
   * Returns all queued actions and clears the queue. Call this after
   * successfully syncing with ground control during a comms window.
   *
   * @returns Array of queued actions that were drained
   */
  drainQueue(): Array<{ action: ActionCategory; queuedAt: number }> {
    const drained = [...this.actionQueue];
    this.actionQueue = [];
    return drained;
  }

  /**
   * Handle phase transition.
   *
   * Attempts to activate a queued envelope matching the new phase.
   * If no matching envelope is found, the active envelope is cleared
   * and actions will be queued until a new envelope arrives.
   *
   * @param newPhase - The mission phase to transition to
   */
  transitionPhase(newPhase: MissionPhase): void {
    // Clear current active envelope
    this.activeEnvelope = null;
    this.executionCounts.clear();

    // Try to activate a queued envelope for the new phase
    this.tryActivateQueued(newPhase);
  }

  /**
   * Get execution stats for the current envelope's rules.
   *
   * Returns a map of rule pattern to { used, max } counts.
   * Useful for telemetry and ground control status reports.
   *
   * @returns Map of pattern to execution stats
   */
  getExecutionStats(): Map<string, { used: number; max: number | undefined }> {
    const stats = new Map<string, { used: number; max: number | undefined }>();

    if (!this.activeEnvelope) return stats;

    for (const rule of this.activeEnvelope.rules) {
      stats.set(rule.pattern, {
        used: this.executionCounts.get(rule.pattern) ?? 0,
        max: rule.maxExecutions,
      });
    }

    return stats;
  }

  /**
   * Try to activate a queued envelope matching the given phase.
   *
   * Searches the queue for valid envelopes matching the target phase
   * and activates the most recently signed one.
   *
   * @param phase - The mission phase to find an envelope for
   */
  private tryActivateQueued(phase: MissionPhase): void {
    // Find all valid envelopes for this phase in the queue
    const candidates: DecisionEnvelope[] = [];
    const remainingQueue: DecisionEnvelope[] = [];

    for (const env of this.queuedEnvelopes) {
      if (env.missionPhase === phase) {
        const validation = validateEnvelope(env);
        if (validation.valid) {
          candidates.push(env);
        } else {
          remainingQueue.push(env);
        }
      } else {
        remainingQueue.push(env);
      }
    }

    this.queuedEnvelopes = remainingQueue;

    if (candidates.length === 0) {
      this.activeEnvelope = null;
      return;
    }

    // Activate the most recently signed candidate
    candidates.sort((a, b) => b.signedAt - a.signedAt);
    this.activeEnvelope = candidates[0];
    this.executionCounts.clear();

    // Re-queue the rest
    for (let i = 1; i < candidates.length; i++) {
      this.queuedEnvelopes.push(candidates[i]);
    }
  }
}
