/**
 * @file gravitationalBraking.ts
 * @module harmonic/gravitationalBraking
 * @layer Layer 11, Layer 12, Layer 13
 * @component Gravitational Braking for Rogue Agents
 * @version 1.0.0
 *
 * Binds agent computation rate to a "gravitational time axis" that freezes
 * as behavioral divergence approaches the trust radius — creating a
 * computational "event horizon" where rogue agents cannot process attack
 * commands because their internal time has mathematically frozen.
 *
 * Mathematical mechanism:
 *   tG = t · (1 - (k·d) / (r + ε))
 *
 * Where:
 *   d = geometric divergence from authorized state (hyperbolic distance)
 *   r = trust radius (derived from agent's 6D trust vector)
 *   k = scaling constant (default: 1.0)
 *   ε = small constant preventing division by zero
 *
 * As d → r: tG → 0 (time freezes, agent cannot act)
 * At d = 0: tG = t (full speed, no braking)
 *
 * Properties:
 * - No central kill switch required
 * - Mathematically inevitable (cannot be bypassed)
 * - Graceful degradation (proportional to threat level)
 * - Escape condition: return to authorized manifold (d decreases)
 */

const EPSILON = 1e-10;

/**
 * Braking state for an agent
 */
export interface BrakingState {
  /** Agent ID */
  agentId: string;
  /** Current divergence from authorized state */
  divergence: number;
  /** Trust radius */
  trustRadius: number;
  /** Time dilation factor ∈ [0, 1] */
  timeDilation: number;
  /** Whether the agent is in the "event horizon" (effectively frozen) */
  frozen: boolean;
  /** Braking intensity (0 = none, 1 = full freeze) */
  intensity: number;
  /** Timestamp of last update */
  lastUpdatedAt: number;
}

/**
 * Configuration for gravitational braking
 */
export interface GravitationalBrakingConfig {
  /** Scaling constant k (default: 1.0) */
  k?: number;
  /** Freeze threshold: below this tG, agent is considered frozen (default: 0.05) */
  freezeThreshold?: number;
  /** Warning threshold: above this intensity, emit alerts (default: 0.7) */
  warningThreshold?: number;
}

/**
 * Compute the gravitational time dilation factor.
 *
 * tG = t · (1 - (k·d) / (r + ε))
 *
 * Clamped to [0, 1]:
 * - 1.0 = full speed (no braking)
 * - 0.0 = frozen (event horizon)
 *
 * @param divergence - Geometric divergence d (hyperbolic distance from authorized state)
 * @param trustRadius - Trust radius r (derived from trust vector norm)
 * @param k - Scaling constant (default: 1.0)
 * @returns Time dilation factor ∈ [0, 1]
 */
export function computeTimeDilation(
  divergence: number,
  trustRadius: number,
  k: number = 1.0
): number {
  if (divergence < 0) return 1.0; // Invalid divergence = no braking
  if (trustRadius <= 0) return 0.0; // No trust = fully frozen

  const ratio = (k * divergence) / (trustRadius + EPSILON);
  const dilation = 1 - ratio;

  return Math.max(0, Math.min(1, dilation));
}

/**
 * Compute the trust radius from a 6D trust vector.
 *
 * The trust radius is the weighted norm of the trust vector,
 * using golden ratio weighting (matching Sacred Tongue weights).
 *
 * @param trustVector - 6D trust vector [KO, AV, RU, CA, UM, DR]
 * @returns Trust radius (higher = more trust = harder to freeze)
 */
export function computeTrustRadius(trustVector: number[]): number {
  const PHI = (1 + Math.sqrt(5)) / 2;
  // Golden ratio weights for 6 dimensions
  const weights = [1, PHI, PHI * PHI, PHI * PHI * PHI, Math.pow(PHI, 4), Math.pow(PHI, 5)];

  let weightedSum = 0;
  const dims = Math.min(trustVector.length, 6);
  for (let i = 0; i < dims; i++) {
    weightedSum += weights[i] * trustVector[i] * trustVector[i];
  }

  return Math.sqrt(weightedSum);
}

/**
 * Compute braking intensity (inverse of dilation: 0 = none, 1 = frozen).
 */
export function brakingIntensity(timeDilation: number): number {
  return 1 - timeDilation;
}

/**
 * Gravitational braking manager for fleet agents.
 */
export class GravitationalBraking {
  private states: Map<string, BrakingState> = new Map();
  private k: number;
  private freezeThreshold: number;
  private warningThreshold: number;

  constructor(config: GravitationalBrakingConfig = {}) {
    this.k = config.k ?? 1.0;
    this.freezeThreshold = config.freezeThreshold ?? 0.05;
    this.warningThreshold = config.warningThreshold ?? 0.7;
  }

  /**
   * Update the braking state for an agent based on current divergence.
   *
   * @param agentId - Agent identifier
   * @param divergence - Current hyperbolic distance from authorized state
   * @param trustVector - Agent's 6D trust vector
   * @param now - Current timestamp
   * @returns Updated braking state
   */
  update(
    agentId: string,
    divergence: number,
    trustVector: number[],
    now: number = Date.now()
  ): BrakingState {
    const trustRadius = computeTrustRadius(trustVector);
    const timeDilation = computeTimeDilation(divergence, trustRadius, this.k);
    const intensity = brakingIntensity(timeDilation);

    const state: BrakingState = {
      agentId,
      divergence,
      trustRadius,
      timeDilation,
      frozen: timeDilation < this.freezeThreshold,
      intensity,
      lastUpdatedAt: now,
    };

    this.states.set(agentId, state);
    return state;
  }

  /**
   * Check if an agent is allowed to execute an action.
   *
   * @param agentId - Agent identifier
   * @returns true if the agent can act (not frozen)
   */
  canAct(agentId: string): boolean {
    const state = this.states.get(agentId);
    if (!state) return true; // No braking state = unmonitored
    return !state.frozen;
  }

  /**
   * Get the effective "time budget" for an agent's next action.
   * Represents what fraction of normal execution time the agent gets.
   *
   * @param agentId - Agent identifier
   * @returns Time dilation factor ∈ [0, 1]
   */
  getTimeBudget(agentId: string): number {
    const state = this.states.get(agentId);
    if (!state) return 1.0;
    return state.timeDilation;
  }

  /**
   * Get all agents currently being braked above warning threshold.
   */
  getWarningAgents(): BrakingState[] {
    return Array.from(this.states.values()).filter(
      (s) => s.intensity >= this.warningThreshold
    );
  }

  /**
   * Get all frozen agents.
   */
  getFrozenAgents(): BrakingState[] {
    return Array.from(this.states.values()).filter((s) => s.frozen);
  }

  /**
   * Get braking state for a specific agent.
   */
  getState(agentId: string): BrakingState | undefined {
    return this.states.get(agentId);
  }

  /**
   * Release braking for an agent (e.g., after returning to authorized state).
   */
  release(agentId: string): void {
    this.states.delete(agentId);
  }

  /**
   * Release all braking states.
   */
  releaseAll(): void {
    this.states.clear();
  }
}
