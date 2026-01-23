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

import { randomBytes } from 'crypto';
import {
  projectToBall,
  hyperbolicDistance,
  breathTransform,
  harmonicScale,
  LanguesMetric,
  type BreathConfig,
} from '../harmonic/index.js';

import {
  signRoundtable,
  verifyRoundtable,
  clearNonceCache,
  checkPolicy,
  getRequiredTongues,
  suggestPolicy,
  type Keyring,
  type RWPEnvelope,
  type TongueID,
  type PolicyLevel,
  type VerifyOptions,
} from '../spiralverse/index.js';

// ============================================================
// Types
// ============================================================

/** Arbitrary context for risk evaluation */
export interface Context {
  [key: string]: unknown;
}

/** Risk evaluation result */
export interface RiskResult {
  score: number;           // 0-1, higher = more risky
  distance: number;        // Hyperbolic distance from safe center
  scaledCost: number;      // Exponential cost to attack
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
  alpha?: number;           // Risk multiplier
}

// Re-export spiralverse types for convenience
export type { Keyring, RWPEnvelope, TongueID, PolicyLevel, VerifyOptions };

// ============================================================
// Configuration
// ============================================================

const DEFAULT_KEYRING: Keyring = {
  ko: randomBytes(32),
  av: randomBytes(32),
  ru: randomBytes(32),
  ca: randomBytes(32),
  um: randomBytes(32),
  dr: randomBytes(32),
};

const SAFE_CENTER = [0, 0, 0, 0, 0, 0];
const RISK_THRESHOLDS = {
  ALLOW: 0.3,
  REVIEW: 0.7,
};

const MAX_COMPLEXITY = 1e10; // Cap to prevent overflow

// ============================================================
// Agent - 6D Vector Navigation
// ============================================================

/**
 * An AI agent with a position in 6D space and trust tracking.
 *
 * Agents exist in a 6-dimensional space where:
 * - Close agents = simple security (they trust each other)
 * - Far agents = complex security (strangers need more checks)
 */
export class Agent {
  public readonly name: string;
  public readonly position: number[];
  public trustScore: number;
  public lastSeen: number;

  /**
   * Create a new agent in 6D space.
   * @param name - Agent identifier
   * @param position - 6D position vector
   * @param initialTrust - Starting trust score (0-1, default 1.0)
   */
  constructor(name: string, position: number[], initialTrust = 1.0) {
    if (!Array.isArray(position) || position.length !== 6) {
      throw new Error('Position must be a 6-element array');
    }
    if (!position.every(n => typeof n === 'number' && isFinite(n))) {
      throw new Error('Position elements must be finite numbers');
    }

    this.name = name;
    this.position = [...position];
    this.trustScore = Math.max(0, Math.min(1, initialTrust));
    this.lastSeen = Date.now();
  }

  /**
   * Calculate Euclidean distance to another agent.
   * Close agents = simple communication, far agents = complex security.
   */
  distanceTo(other: Agent): number {
    let sum = 0;
    for (let i = 0; i < 6; i++) {
      const diff = this.position[i] - other.position[i];
      sum += diff * diff;
    }
    return Math.sqrt(sum);
  }

  /**
   * Agent checks in - refreshes trust and timestamp.
   */
  checkIn(): void {
    this.lastSeen = Date.now();
    this.trustScore = Math.min(1.0, this.trustScore + 0.1);
  }

  /**
   * Apply trust decay based on time since last check-in.
   * @param decayRate - Rate of decay (default 0.01)
   * @returns Current trust score after decay
   */
  decayTrust(decayRate = 0.01): number {
    const elapsed = (Date.now() - this.lastSeen) / 1000; // seconds
    this.trustScore *= Math.exp(-decayRate * elapsed);
    return this.trustScore;
  }
}

// ============================================================
// SecurityGate - Adaptive Dwell Time
// ============================================================

/**
 * Security gate with adaptive dwell time based on risk.
 *
 * Like a nightclub bouncer that:
 * - Checks your ID (authentication)
 * - Looks at your reputation (trust score)
 * - Makes you wait longer if you're risky (adaptive dwell time)
 */
export class SecurityGate {
  private minWaitMs: number;
  private maxWaitMs: number;
  private alpha: number;

  constructor(config: SecurityGateConfig = {}) {
    this.minWaitMs = config.minWaitMs ?? 100;
    this.maxWaitMs = config.maxWaitMs ?? 5000;
    this.alpha = config.alpha ?? 1.5;
  }

  /**
   * Calculate risk score for an agent performing an action.
   * @returns Risk score (0 = safe, higher = riskier)
   */
  assessRisk(agent: Agent, action: string, context: Context): number {
    let risk = 0;

    // Low trust = high risk
    risk += (1.0 - agent.trustScore) * 2.0;

    // Dangerous actions = high risk
    const dangerousActions = ['delete', 'deploy', 'rotate_keys', 'grant_access'];
    if (dangerousActions.includes(action)) {
      risk += 3.0;
    }

    // External context = higher risk
    if (context.source === 'external') {
      risk += 1.5;
    }

    return risk;
  }

  /**
   * Perform security gate check with adaptive dwell time.
   *
   * Higher risk = longer wait time (slows attackers).
   * Returns allow/review/deny decision.
   */
  async check(agent: Agent, action: string, context: Context): Promise<GateResult> {
    const risk = this.assessRisk(agent, action, context);

    // Adaptive dwell time (higher risk = longer wait)
    const dwellMs = Math.min(this.maxWaitMs, this.minWaitMs * Math.pow(this.alpha, risk));

    // Wait (non-blocking)
    await new Promise(resolve => setTimeout(resolve, dwellMs));

    // Calculate composite score (0-1, higher = safer)
    const trustComponent = agent.trustScore * 0.4;
    const actionComponent = (dangerousActions.includes(action) ? 0.3 : 1.0) * 0.3;
    const contextComponent = (context.source === 'internal' ? 0.8 : 0.4) * 0.3;

    const score = trustComponent + actionComponent + contextComponent;

    if (score > 0.8) {
      return { status: 'allow', score, dwellMs };
    } else if (score > 0.5) {
      return { status: 'review', score, dwellMs, reason: 'Manual approval required' };
    } else {
      return { status: 'deny', score, dwellMs, reason: 'Security threshold not met' };
    }
  }
}

const dangerousActions = ['delete', 'deploy', 'rotate_keys', 'grant_access'];

// ============================================================
// Roundtable - Multi-Signature Consensus
// ============================================================

/**
 * Roundtable multi-signature consensus system.
 *
 * Different actions require different numbers of "departments" to agree:
 * - Low security: 1 signature (just control)
 * - Medium security: 2 signatures (control + policy)
 * - High security: 3 signatures (control + policy + security)
 * - Critical: 4+ signatures (all departments)
 */
export const Roundtable = {
  /** Tier definitions for multi-signature requirements */
  TIERS: {
    low: ['ko'] as TongueID[],
    medium: ['ko', 'ru'] as TongueID[],
    high: ['ko', 'ru', 'um'] as TongueID[],
    critical: ['ko', 'ru', 'um', 'dr'] as TongueID[],
  },

  /**
   * Get required tongues for an action.
   */
  requiredTongues(action: ActionType): TongueID[] {
    switch (action) {
      case 'read':
      case 'query':
        return this.TIERS.low;
      case 'write':
      case 'update':
        return this.TIERS.medium;
      case 'delete':
      case 'grant':
        return this.TIERS.high;
      case 'deploy':
      case 'rotate_keys':
      default:
        return this.TIERS.critical;
    }
  },

  /**
   * Check if we have all required signatures.
   */
  hasQuorum(signatures: TongueID[], required: TongueID[]): boolean {
    return required.every(t => signatures.includes(t));
  },

  /**
   * Get suggested policy level for an action (from spiralverse).
   */
  suggestPolicy,

  /**
   * Get required tongues for a policy level (from spiralverse).
   */
  getRequiredTongues,

  /**
   * Check if tongues satisfy a policy (from spiralverse).
   */
  checkPolicy,
};

// ============================================================
// Harmonic Complexity Pricing
// ============================================================

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
export function harmonicComplexity(depth: number, ratio = 1.5): number {
  const result = Math.pow(ratio, depth * depth);
  return Math.min(result, MAX_COMPLEXITY);
}

/**
 * Get pricing tier based on task complexity.
 */
export function getPricingTier(depth: number): PricingTier {
  const complexity = harmonicComplexity(depth);

  if (complexity < 2) {
    return { tier: 'FREE', complexity, description: 'Simple single-step tasks' };
  } else if (complexity < 10) {
    return { tier: 'STARTER', complexity, description: 'Basic workflows' };
  } else if (complexity < 100) {
    return { tier: 'PRO', complexity, description: 'Advanced multi-step' };
  } else {
    return { tier: 'ENTERPRISE', complexity, description: 'Complex orchestration' };
  }
}

// ============================================================
// Core API
// ============================================================

export class SCBE {
  private keyring: Keyring;
  private metric: LanguesMetric;

  constructor(keyring?: Keyring) {
    this.keyring = keyring || DEFAULT_KEYRING;
    this.metric = new LanguesMetric();
  }

  /**
   * Evaluate the risk of a context/action.
   * Returns a risk score and decision.
   */
  evaluateRisk(context: Context): RiskResult {
    // Convert context to 6D point
    const point = this.contextToPoint(context);

    // Project to Poincaré ball (ensures point is valid)
    const projected = projectToBall(point);

    // Compute hyperbolic distance from safe center
    const distance = hyperbolicDistance(projected, SAFE_CENTER);

    // Apply harmonic scaling (exponential cost)
    const d = Math.max(1, Math.ceil(distance));
    const scaledCost = harmonicScale(d, 1.5);

    // Normalize to 0-1 risk score
    const score = Math.min(1, distance / 5);

    // Make decision
    let decision: 'ALLOW' | 'REVIEW' | 'DENY';
    let reason: string;

    if (score < RISK_THRESHOLDS.ALLOW) {
      decision = 'ALLOW';
      reason = 'Context within safe zone';
    } else if (score < RISK_THRESHOLDS.REVIEW) {
      decision = 'REVIEW';
      reason = 'Context requires review - moderate deviation';
    } else {
      decision = 'DENY';
      reason = 'Context exceeds safe threshold - high risk';
    }

    return {
      score,
      distance,
      scaledCost,
      decision,
      reason,
    };
  }

  /**
   * Sign a payload using RWP multi-signature envelope.
   *
   * @param payload - Data to sign
   * @param tongues - Tongues to sign with (default: ['ko'])
   * @returns Signed envelope and tongues used
   */
  sign(payload: unknown, tongues: TongueID[] = ['ko']): SignResult {
    const envelope = signRoundtable(
      payload,
      tongues[0],
      'scbe-api',
      this.keyring,
      tongues
    );
    return { envelope, tongues };
  }

  /**
   * Verify an envelope signature.
   *
   * @param envelope - RWP envelope to verify
   * @param options - Verification options (policy, maxAge, etc.)
   * @returns Verification result with valid tongues and payload
   */
  verify(envelope: RWPEnvelope, options?: VerifyOptions): VerifyResult {
    clearNonceCache(); // Clear for fresh verification
    const result = verifyRoundtable(envelope, this.keyring, options);
    return {
      valid: result.valid,
      validTongues: result.validTongues,
      payload: result.payload,
      reason: result.error ?? (result.valid ? 'Signature valid - all tongues verified' : 'Signature invalid or tampered'),
    };
  }

  /**
   * Sign and verify with policy enforcement.
   *
   * Automatically determines required tongues based on action.
   *
   * @param payload - Data to sign
   * @param action - Action type (determines required tongues)
   * @returns Signed envelope
   */
  signForAction(payload: unknown, action: ActionType): SignResult {
    const tongues = Roundtable.requiredTongues(action);
    return this.sign(payload, tongues);
  }

  /**
   * Verify an envelope with policy enforcement.
   *
   * @param envelope - RWP envelope to verify
   * @param action - Expected action (determines required policy)
   * @returns Verification result
   */
  verifyForAction(envelope: RWPEnvelope, action: ActionType): VerifyResult {
    const policy = Roundtable.suggestPolicy(action);
    return this.verify(envelope, { policy });
  }

  /**
   * Apply breathing transform to a context point.
   * Used for dynamic security adaptation.
   */
  breathe(context: Context, intensity: number = 1.0): number[] {
    const point = this.contextToPoint(context);
    const projected = projectToBall(point);
    const config: BreathConfig = { amplitude: 0.1 * intensity, omega: 1.0 };
    return breathTransform(projected, Date.now() / 1000, config);
  }

  /**
   * Get the keyring (for advanced usage).
   */
  getKeyring(): Keyring {
    return this.keyring;
  }

  /**
   * Set a custom keyring.
   */
  setKeyring(keyring: Keyring): void {
    this.keyring = keyring;
  }

  // ============================================================
  // Private Methods
  // ============================================================

  private contextToPoint(context: Context): number[] {
    // Convert arbitrary context to 6D point using hash-based mapping
    const str = JSON.stringify(context);
    const hash = this.simpleHash(str);

    // Map hash to 6 dimensions, scaled to reasonable range
    const point: number[] = [];
    for (let i = 0; i < 6; i++) {
      // Extract 4 characters at a time, convert to number, scale to [-2, 2]
      const slice = hash.slice(i * 4, i * 4 + 4);
      const num = parseInt(slice, 16) / 65535; // 0 to 1
      point.push((num - 0.5) * 4); // -2 to 2
    }

    return point;
  }

  private simpleHash(str: string): string {
    // Simple hash for context-to-point mapping
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    // Pad to 24 hex chars (6 dimensions * 4 chars each)
    const hex = Math.abs(hash).toString(16).padStart(8, '0');
    return (hex + hex + hex).slice(0, 24);
  }
}

// ============================================================
// Singleton Export for Simple Usage
// ============================================================

/** Default SCBE instance for simple usage */
export const scbe = new SCBE();

/** Default security gate instance */
export const defaultGate = new SecurityGate();

// ============================================================
// Convenience Functions
// ============================================================

/**
 * Evaluate risk of a context using the default SCBE instance.
 */
export function evaluateRisk(context: Context): RiskResult {
  return scbe.evaluateRisk(context);
}

/**
 * Sign a payload using the default SCBE instance.
 */
export function sign(payload: unknown, tongues?: TongueID[]): SignResult {
  return scbe.sign(payload, tongues);
}

/**
 * Sign a payload for a specific action (determines required tongues).
 */
export function signForAction(payload: unknown, action: ActionType): SignResult {
  return scbe.signForAction(payload, action);
}

/**
 * Verify an envelope using the default SCBE instance.
 */
export function verify(envelope: RWPEnvelope, options?: VerifyOptions): VerifyResult {
  return scbe.verify(envelope, options);
}

/**
 * Verify an envelope for a specific action (enforces policy).
 */
export function verifyForAction(envelope: RWPEnvelope, action: ActionType): VerifyResult {
  return scbe.verifyForAction(envelope, action);
}

/**
 * Apply breathing transform to a context using the default SCBE instance.
 */
export function breathe(context: Context, intensity?: number): number[] {
  return scbe.breathe(context, intensity);
}

/**
 * Check if an agent can perform an action (using default gate).
 */
export async function checkAccess(
  agent: Agent,
  action: string,
  context: Context
): Promise<GateResult> {
  return defaultGate.check(agent, action, context);
}

/**
 * Get required tongues for an action.
 */
export function requiredTongues(action: ActionType): TongueID[] {
  return Roundtable.requiredTongues(action);
}
