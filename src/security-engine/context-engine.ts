/**
 * @file context-engine.ts
 * @module security-engine/context-engine
 * @layer L1-L14
 * @component Context-Coupled Security Engine
 *
 * The unified security gate that binds cryptography, behavior models,
 * routing, and trust to the same evolving simulation state.
 *
 * This is the core "machine science" engine: it doesn't simulate physics,
 * it uses physics-like invariants as coordination constants to shape how
 * tokens, agents, and policies interact in a shared hyperspace.
 *
 * Decision pipeline:
 *   1. Receive action request with 6D context
 *   2. Embed entity into hyperspace
 *   3. Evaluate all policy fields at that position
 *   4. Compute harmonic wall cost (exponential scaling)
 *   5. Check PQC envelope validity (context-locked crypto)
 *   6. Compute Omega decision score
 *   7. Return ALLOW / QUARANTINE / ESCALATE / DENY
 *
 * When an entity leaves the valid manifold:
 *   - Crypto becomes noise (wrong context → ciphertext dissolves)
 *   - Trust decays
 *   - Latency stretches (routing cost increases)
 *   - Agents refuse quorum
 *   - The digital twin predicts collapse and tightens controls
 */

import {
  type HyperspaceCoord,
  type HyperspacePoint,
  type EmbeddingInputs,
  HyperspaceManifold,
  distanceFromSafe,
} from './hyperspace.js';
import { type PolicyEvaluation, PolicyFieldEvaluator } from './policy-fields.js';
import { type MachineConstants, getGlobalRegistry, toQ16, fromQ16 } from './machine-constants.js';

// ═══════════════════════════════════════════════════════════════
// Decision Types
// ═══════════════════════════════════════════════════════════════

/** Security gate decision */
export enum SecurityDecision {
  ALLOW = 'ALLOW',
  QUARANTINE = 'QUARANTINE',
  ESCALATE = 'ESCALATE',
  DENY = 'DENY',
}

/** Full result of the security engine evaluation */
export interface SecurityEvaluation {
  /** The decision */
  readonly decision: SecurityDecision;
  /** Omega composite score [0, 1] */
  readonly omega: number;
  /** Hyperspace distance from safe origin */
  readonly hyperspaceDistance: number;
  /** Harmonic wall cost: R^(d^2 * x) */
  readonly harmonicWallCost: number;
  /** Intent persistence factor (x in H_eff) */
  readonly intentFactor: number;
  /** Policy field evaluation */
  readonly policyEvaluation: PolicyEvaluation;
  /** Hyperspace position */
  readonly hyperspacePoint: HyperspacePoint;
  /** PQC context validity */
  readonly pqcValid: boolean;
  /** Trust score */
  readonly trustScore: number;
  /** Routing cost multiplier (how much latency to add) */
  readonly routingCostMultiplier: number;
  /** Reason codes for the decision */
  readonly reasonCodes: string[];
  /** Timestamp of evaluation */
  readonly timestampUs: number;
}

/** Action request to the security engine */
export interface ActionRequest {
  /** Entity (agent/token) ID */
  entityId: string;
  /** Action being requested */
  action: string;
  /** Target object of the action */
  target: string;
  /** 6D context vector */
  context6D: [number, number, number, number, number, number];
  /** Current timestamp in microseconds */
  timestampUs: number;
  /** PQC envelope valid? */
  pqcValid: boolean;
  /** Spectral coherence score [0, 1] */
  spectralCoherence?: number;
  /** Triadic temporal stability [0, 1] */
  triadicStability?: number;
  /** System load [0, 1] */
  systemLoad?: number;
}

// ═══════════════════════════════════════════════════════════════
// Intent Tracking (simplified inline for the engine)
// ═══════════════════════════════════════════════════════════════

interface IntentState {
  accumulatedIntent: number;
  trustScore: number;
  lowTrustRounds: number;
  sampleCount: number;
  lastDistances: number[];
  exiled: boolean;
}

function createIntentState(): IntentState {
  return {
    accumulatedIntent: 0,
    trustScore: 1.0,
    lowTrustRounds: 0,
    sampleCount: 0,
    lastDistances: [],
    exiled: false,
  };
}

function updateIntentState(
  state: IntentState,
  distance: number,
  velocity: number,
  constants: MachineConstants
): IntentState {
  const next = { ...state };

  // Compute raw intent for this sample
  const velocityFactor = Math.max(0, velocity) * 2.0;
  const distanceFactor = distance * distance;
  const rawIntent = velocityFactor + distanceFactor;

  // Decay accumulated intent then add new
  next.accumulatedIntent = state.accumulatedIntent * constants.temporal.intentDecayRate + rawIntent;
  next.accumulatedIntent = Math.min(
    next.accumulatedIntent,
    constants.temporal.maxIntentAccumulation
  );

  // Track recent distances
  next.lastDistances = [...state.lastDistances.slice(-9), distance];
  next.sampleCount = state.sampleCount + 1;

  // Update trust
  if (next.lastDistances.length >= 3) {
    const avgDist = next.lastDistances.reduce((s, d) => s + d, 0) / next.lastDistances.length;
    let trustChange = -0.1 * avgDist - 0.05 * next.accumulatedIntent;
    if (next.accumulatedIntent < 0.5 && avgDist < 0.3) {
      trustChange += 0.02;
    }
    next.trustScore = Math.max(0, Math.min(1, state.trustScore + trustChange));
  }

  // Exile tracking
  if (next.trustScore < constants.trust.exileThreshold) {
    next.lowTrustRounds = state.lowTrustRounds + 1;
  } else {
    next.lowTrustRounds = 0;
  }
  next.exiled = next.lowTrustRounds >= constants.trust.exileRounds;

  return next;
}

function computeXFactor(state: IntentState): number {
  const baseX = 0.5 + state.accumulatedIntent * 0.25;
  const trustModifier = 1.0 + (1.0 - state.trustScore);
  return Math.min(3.0, baseX * trustModifier);
}

// ═══════════════════════════════════════════════════════════════
// Context-Coupled Security Engine
// ═══════════════════════════════════════════════════════════════

/**
 * The unified AI security engine.
 *
 * This engine ties all SCBE subsystems to a shared simulation state:
 *
 * - Entities are embedded in 9D hyperspace
 * - Policy fields shape which regions are "cheap" vs "expensive"
 * - The harmonic wall makes adversarial behavior exponentially costly
 * - PQC context-binding means wrong-context crypto dissolves to noise
 * - Trust, intent, and behavior all evolve on the same manifold
 * - The engine outputs decisions + routing cost multipliers
 *
 * Legitimate behavior → low-resistance geodesics
 * Adversarial behavior → high-entropy, high-latency regime
 */
export class ContextCoupledSecurityEngine {
  private _manifold: HyperspaceManifold;
  private _policyEvaluator: PolicyFieldEvaluator;
  private _intentStates: Map<string, IntentState> = new Map();
  private _evaluationCount: number = 0;

  constructor(manifold?: HyperspaceManifold, policyEvaluator?: PolicyFieldEvaluator) {
    this._manifold = manifold ?? new HyperspaceManifold();
    this._policyEvaluator = policyEvaluator ?? PolicyFieldEvaluator.createStandard();
  }

  /** Get the hyperspace manifold */
  get manifold(): HyperspaceManifold {
    return this._manifold;
  }

  /** Get the policy field evaluator */
  get policyEvaluator(): PolicyFieldEvaluator {
    return this._policyEvaluator;
  }

  /** Total evaluations performed */
  get evaluationCount(): number {
    return this._evaluationCount;
  }

  /**
   * Evaluate an action request through the full security pipeline.
   *
   * This is the main entry point — the "Grand Unified Gate."
   */
  evaluate(request: ActionRequest): SecurityEvaluation {
    const constants = getGlobalRegistry().active;
    this._evaluationCount++;

    // 1. Get or create intent state for this entity
    let intentState = this._intentStates.get(request.entityId);
    if (!intentState) {
      intentState = createIntentState();
    }

    // 2. Compute spectral entropy (inverse coherence)
    const spectralEntropy = 1.0 - (request.spectralCoherence ?? 1.0);

    // 3. Compute behavioral deviation from previous position
    const prevPoint = this._manifold.getPoint(request.entityId);
    let behaviorDeviation = 0;
    let velocity = 0;
    if (prevPoint) {
      const dt = (request.timestampUs - prevPoint.timestampUs) / 1_000_000;
      if (dt > 0) {
        // Distance moved per second
        velocity =
          distanceFromSafe(prevPoint.coords) - distanceFromSafe([0, 0, 0, 1, 0, 0, 0, 0, 0]);
        behaviorDeviation = Math.abs(velocity);
      }
    }

    // 4. Build embedding inputs
    const embeddingInputs: EmbeddingInputs = {
      context6D: request.context6D,
      timestampUs: request.timestampUs,
      accumulatedIntent: intentState.accumulatedIntent,
      trustScore: intentState.trustScore,
      riskScore: 0, // will be refined after policy eval
      spectralEntropy,
      policyPressure: 0, // will be set after policy eval
      systemLoad: request.systemLoad ?? 0,
      behaviorDeviation,
    };

    // 5. Embed entity into hyperspace
    const point = this._manifold.embed(request.entityId, embeddingInputs);

    // 6. Evaluate policy fields at this position
    const policyEval = this._policyEvaluator.evaluate(point.coords);

    // 7. Update intent state with current distance
    const hypDist = distanceFromSafe(point.coords);
    intentState = updateIntentState(intentState, hypDist, velocity, constants);
    this._intentStates.set(request.entityId, intentState);

    // 8. Compute harmonic wall with temporal intent
    const x = computeXFactor(intentState);
    const R = constants.harmonic.harmonicR;
    const harmonicWallCost = Math.pow(R, hypDist * hypDist * x);

    // 9. Compute Omega (composite decision score)
    const pqcFactor = request.pqcValid ? 1.0 : 0.0;
    const harmScore = 1.0 / (1.0 + Math.log(Math.max(1.0, harmonicWallCost)));
    const driftFactor =
      1.0 - intentState.accumulatedIntent / constants.temporal.maxIntentAccumulation;
    const triadicFactor = request.triadicStability ?? 1.0;
    const spectralFactor = request.spectralCoherence ?? 1.0;

    const omega = pqcFactor * harmScore * driftFactor * triadicFactor * spectralFactor;

    // 10. Compute routing cost multiplier
    // Legitimate: ~1.0x, Suspicious: 2-10x, Adversarial: 100x+
    const routingCostMultiplier = Math.max(
      1.0,
      harmonicWallCost * (1 + policyEval.totalPressure * 0.1)
    );

    // 11. Make decision
    const reasonCodes: string[] = [];
    let decision: SecurityDecision;

    if (intentState.exiled) {
      decision = SecurityDecision.DENY;
      reasonCodes.push('EXILE: trust exhausted after sustained adversarial behavior');
    } else if (!request.pqcValid) {
      decision = SecurityDecision.DENY;
      reasonCodes.push('PQC_INVALID: context-locked crypto failed verification');
    } else if (omega > constants.trust.allowThreshold) {
      decision = SecurityDecision.ALLOW;
    } else if (omega > constants.trust.quarantineThreshold) {
      if (policyEval.isDangerous) {
        decision = SecurityDecision.ESCALATE;
        reasonCodes.push(`POLICY_DANGER: dominant=${policyEval.dominantPolicy}`);
      } else {
        decision = SecurityDecision.QUARANTINE;
        reasonCodes.push('OMEGA_MID: within quarantine band');
      }
    } else {
      if (intentState.accumulatedIntent > constants.temporal.maxIntentAccumulation * 0.8) {
        decision = SecurityDecision.DENY;
        reasonCodes.push('INTENT_HIGH: accumulated intent near maximum');
      } else {
        decision = SecurityDecision.ESCALATE;
        reasonCodes.push('OMEGA_LOW: below quarantine threshold');
      }
    }

    // Add contextual reason codes
    if (hypDist > 1.0) {
      reasonCodes.push(`HYPER_DRIFT: distance=${hypDist.toFixed(3)}`);
    }
    if (policyEval.totalPressure > 3.0) {
      reasonCodes.push(`POLICY_PRESSURE: total=${policyEval.totalPressure.toFixed(3)}`);
    }
    if (intentState.trustScore < 0.5) {
      reasonCodes.push(`LOW_TRUST: score=${intentState.trustScore.toFixed(3)}`);
    }

    return {
      decision,
      omega,
      hyperspaceDistance: hypDist,
      harmonicWallCost,
      intentFactor: x,
      policyEvaluation: policyEval,
      hyperspacePoint: point,
      pqcValid: request.pqcValid,
      trustScore: intentState.trustScore,
      routingCostMultiplier,
      reasonCodes,
      timestampUs: request.timestampUs,
    };
  }

  /**
   * Batch-evaluate multiple action requests.
   * Returns evaluations in the same order as requests.
   */
  evaluateBatch(requests: ActionRequest[]): SecurityEvaluation[] {
    return requests.map((r) => this.evaluate(r));
  }

  /** Get intent state for an entity */
  getIntentState(entityId: string): IntentState | undefined {
    return this._intentStates.get(entityId);
  }

  /** Forcibly exile an entity (emergency governance action) */
  exile(entityId: string): void {
    const state = this._intentStates.get(entityId) ?? createIntentState();
    const constants = getGlobalRegistry().active;
    this._intentStates.set(entityId, {
      ...state,
      exiled: true,
      lowTrustRounds: constants.trust.exileRounds,
      trustScore: 0,
    });
  }

  /** Rehabilitate an exiled entity (governance override) */
  rehabilitate(entityId: string): void {
    const state = this._intentStates.get(entityId);
    if (state) {
      this._intentStates.set(entityId, {
        ...state,
        exiled: false,
        lowTrustRounds: 0,
        accumulatedIntent: 0, // reset intent to give a fresh start
        trustScore: 0.5, // start mid-range, must earn full trust back
        sampleCount: 0,
        lastDistances: [], // clear history so old distances don't drag trust down
      });
      // Clear manifold position so old adversarial coordinates don't create
      // a spurious velocity spike on the rehabilitated entity's next evaluation
      this._manifold.remove(entityId);
    }
  }

  /** Get summary statistics for all tracked entities */
  summary(): {
    totalEntities: number;
    clamped: number;
    unclamped: number;
    exiled: number;
    avgTrust: number;
    avgIntent: number;
  } {
    let exiled = 0;
    let totalTrust = 0;
    let totalIntent = 0;
    let count = 0;

    for (const state of this._intentStates.values()) {
      if (state.exiled) exiled++;
      totalTrust += state.trustScore;
      totalIntent += state.accumulatedIntent;
      count++;
    }

    return {
      totalEntities: this._manifold.size,
      clamped: this._manifold.getClamped().length,
      unclamped: this._manifold.getUnclamped().length,
      exiled,
      avgTrust: count > 0 ? totalTrust / count : 1.0,
      avgIntent: count > 0 ? totalIntent / count : 0,
    };
  }
}
