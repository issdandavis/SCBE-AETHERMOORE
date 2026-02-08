/**
 * @file bee-immune-tiers.ts
 * @module ai_brain/bee-immune-tiers
 * @layer Layer 12, Layer 13, Layer 14
 * @component Bee-Colony Tiered Immune System
 * @version 1.0.0
 * @since 2026-02-08
 *
 * Implements a bee-colony-inspired tiered immune system for AI agents.
 *
 * In a real bee colony, immunity operates across multiple tiers with
 * specialized castes:
 *
 *   Tier 1 (Propolis Barrier) - Passive mathematical boundaries
 *     Like the resinous coating bees build at the hive entrance.
 *     Enforces norm checks, dimension validation, and Poincare boundary.
 *
 *   Tier 2 (Hemocyte Response) - Individual agent immune tracking
 *     Like haemocytes in each bee's hemolymph.
 *     Wraps the existing ImmuneResponseSystem for per-agent suspicion.
 *
 *   Tier 3 (Social Grooming) - Neighbor-based anomaly detection
 *     Like nurse bees inspecting brood for disease.
 *     Agents inspect neighbors, perform "waggle dance" threat reporting.
 *
 *   Tier 4 (Colony Fever) - Global collective response
 *     Like the whole hive raising temperature to kill pathogens.
 *     Colony-wide alarm pheromone shifts ALL detection thresholds.
 *
 * Agent castes (bee-inspired roles):
 *   queen   - Central coordinator, sets global alarm pheromone level
 *   guard   - Entry-point validation, first line of defense
 *   nurse   - Monitors adjacent agents, performs hygienic behavior
 *   forager - Scouts external/new threats, brings intel back
 *   undertaker - Handles expelled/dead agents, cleanup duty
 *   worker  - Default caste, regular agent processing
 */

import { PHI, POINCARE_MAX_NORM, type RiskDecision } from './types.js';
import {
  ImmuneResponseSystem,
  type ImmuneState,
  type AgentImmuneStatus,
  type ImmuneConfig,
  type ImmuneEvent,
} from './immune-response.js';

// ═══════════════════════════════════════════════════════════════
// Agent Castes (Bee-Inspired Roles)
// ═══════════════════════════════════════════════════════════════

/**
 * Agent caste determines its role in the colony immune system.
 *
 * - queen: Central coordinator (one per hive). Sets alarm pheromone level.
 * - guard: Entry validation. Checks agents at the "hive entrance" (system boundary).
 * - nurse: Inspects adjacent agents for anomalies. Reports via waggle dance.
 * - forager: Scouts external environments. Brings back threat intelligence.
 * - undertaker: Removes expelled agents, cleans up resources.
 * - worker: Default role. Processes tasks normally.
 */
export type AgentCaste =
  | 'queen'
  | 'guard'
  | 'nurse'
  | 'forager'
  | 'undertaker'
  | 'worker';

/**
 * Caste capabilities and responsibilities
 */
export interface CasteProfile {
  /** Caste identifier */
  caste: AgentCaste;
  /** Trust multiplier (queen and guards get higher innate trust) */
  trustMultiplier: number;
  /** Inspection range (how many neighbors this caste can inspect) */
  inspectionRange: number;
  /** Whether this caste can trigger colony fever */
  canTriggerFever: boolean;
  /** Whether this caste can release agents from quarantine */
  canRelease: boolean;
  /** Whether this caste can expel agents */
  canExpel: boolean;
  /** Pheromone production rate (how loudly this caste signals threats) */
  pheromoneRate: number;
}

/**
 * Default caste profiles
 */
export const CASTE_PROFILES: Record<AgentCaste, CasteProfile> = {
  queen: {
    caste: 'queen',
    trustMultiplier: 1.5,
    inspectionRange: 0, // Queen doesn't inspect directly
    canTriggerFever: true,
    canRelease: true,
    canExpel: true,
    pheromoneRate: 2.0, // Strongest pheromone signal
  },
  guard: {
    caste: 'guard',
    trustMultiplier: 1.3,
    inspectionRange: 1, // Checks agents at boundary
    canTriggerFever: false,
    canRelease: false,
    canExpel: false,
    pheromoneRate: 1.5,
  },
  nurse: {
    caste: 'nurse',
    trustMultiplier: 1.2,
    inspectionRange: 3, // Wide inspection radius
    canTriggerFever: false,
    canRelease: true,
    canExpel: false,
    pheromoneRate: 1.0,
  },
  forager: {
    caste: 'forager',
    trustMultiplier: 1.0,
    inspectionRange: 2,
    canTriggerFever: false,
    canRelease: false,
    canExpel: false,
    pheromoneRate: 1.2, // Scouts bring back good intel
  },
  undertaker: {
    caste: 'undertaker',
    trustMultiplier: 1.1,
    inspectionRange: 1,
    canTriggerFever: false,
    canRelease: false,
    canExpel: true,
    pheromoneRate: 0.5,
  },
  worker: {
    caste: 'worker',
    trustMultiplier: 1.0,
    inspectionRange: 1,
    canTriggerFever: false,
    canRelease: false,
    canExpel: false,
    pheromoneRate: 0.3,
  },
};

// ═══════════════════════════════════════════════════════════════
// Waggle Dance (Threat Communication Protocol)
// ═══════════════════════════════════════════════════════════════

/**
 * A "waggle dance" encodes threat intelligence from one agent to the colony.
 *
 * In real bees, the waggle dance communicates direction, distance, and quality
 * of a food source. Here it communicates:
 * - Which dimensions the threat came from
 * - Threat magnitude
 * - Distance from the hive center (safe origin)
 */
export interface WaggleDance {
  /** Agent that performed the dance */
  dancerId: string;
  /** Caste of the dancer */
  dancerCaste: AgentCaste;
  /** Target agent being reported */
  targetId: string;
  /** Which dimensions showed anomaly (indices into 21D state) */
  anomalyDimensions: number[];
  /** Threat magnitude [0, 1] */
  magnitude: number;
  /** Distance from hive center (safe origin) */
  distanceFromCenter: number;
  /** Confidence of the report [0, 1] (weighted by caste) */
  confidence: number;
  /** Timestamp of dance */
  timestamp: number;
  /** Pheromone decay factor (how fast this info fades) */
  decayRate: number;
}

// ═══════════════════════════════════════════════════════════════
// Colony Pheromone System
// ═══════════════════════════════════════════════════════════════

/**
 * Colony pheromone state (global immune posture)
 *
 * The balance between alarm and calm pheromones determines the
 * colony's overall defensive posture.
 */
export interface ColonyPheromoneState {
  /** Alarm pheromone level [0, 1] — triggers heightened vigilance */
  alarm: number;
  /** Calm pheromone (queen mandibular) [0, 1] — stabilization signal */
  calm: number;
  /** Net immune posture [-1, 1] where -1=relaxed, +1=maximum alert */
  posture: number;
  /** Whether colony fever is active */
  feverActive: boolean;
  /** Colony fever temperature multiplier (1.0 = normal, up to 3.0 in fever) */
  feverMultiplier: number;
  /** Number of active waggle dances in the last window */
  activeDances: number;
}

// ═══════════════════════════════════════════════════════════════
// Tier Results
// ═══════════════════════════════════════════════════════════════

/**
 * Result from a single agent passing through all immune tiers
 */
export interface TieredImmuneResult {
  /** Agent identifier */
  agentId: string;
  /** Agent's assigned caste */
  caste: AgentCaste;

  /** Tier 1: Propolis barrier result */
  propolis: {
    passed: boolean;
    normCheck: boolean;
    dimensionCheck: boolean;
    boundaryDistance: number;
  };

  /** Tier 2: Hemocyte (individual immune) result */
  hemocyte: AgentImmuneStatus;

  /** Tier 3: Social grooming result */
  grooming: {
    inspectedBy: string[];
    waggleDances: number;
    neighborConsensus: boolean;
    groomingScore: number;
  };

  /** Tier 4: Colony fever modifier */
  colonyFever: {
    feverActive: boolean;
    thresholdShift: number;
    amplifiedSuspicion: number;
  };

  /** Final decision after all tiers */
  finalDecision: RiskDecision;
  /** Effective trust score after all tier modifications */
  effectiveTrust: number;
}

// ═══════════════════════════════════════════════════════════════
// Hive Immune Configuration
// ═══════════════════════════════════════════════════════════════

export interface HiveImmuneConfig {
  /** Tier 1: Maximum allowed norm for state vectors */
  maxNorm: number;
  /** Tier 1: Required dimensionality */
  requiredDimensions: number;
  /** Tier 1: Poincare boundary epsilon */
  boundaryEpsilon: number;

  /** Tier 3: Minimum dances needed to affect suspicion */
  minDancesForEffect: number;
  /** Tier 3: Dance decay half-life (in steps) */
  danceDecayHalfLife: number;
  /** Tier 3: Dance confidence weight */
  danceConfidenceWeight: number;

  /** Tier 4: Alarm level that triggers colony fever */
  feverThreshold: number;
  /** Tier 4: Maximum fever multiplier */
  maxFeverMultiplier: number;
  /** Tier 4: Alarm decay rate per step (natural calming) */
  alarmDecayRate: number;
  /** Tier 4: Calm pheromone base level from queen */
  queenCalmBase: number;

  /** How many recent dances to keep */
  danceHistorySize: number;
}

export const DEFAULT_HIVE_CONFIG: HiveImmuneConfig = {
  maxNorm: 10.0,
  requiredDimensions: 21,
  boundaryEpsilon: 1e-8,

  minDancesForEffect: 2,
  danceDecayHalfLife: 20,
  danceConfidenceWeight: 0.5,

  feverThreshold: 0.6,
  maxFeverMultiplier: 3.0,
  alarmDecayRate: 0.03,
  queenCalmBase: 0.4,

  danceHistorySize: 100,
};

// ═══════════════════════════════════════════════════════════════
// Hive Immune System (Tiered)
// ═══════════════════════════════════════════════════════════════

/**
 * Bee-Colony Tiered Immune System
 *
 * Orchestrates four tiers of immune defense, inspired by the layered
 * immunity of a honeybee colony:
 *
 *   Tier 1: Propolis Barrier (passive mathematical filtering)
 *   Tier 2: Hemocyte Response (per-agent suspicion tracking)
 *   Tier 3: Social Grooming (neighbor-based anomaly detection)
 *   Tier 4: Colony Fever (global threshold adjustment)
 *
 * Each agent is assigned a caste that determines its role and
 * capabilities within the colony.
 */
export class HiveImmuneSystem {
  private readonly config: HiveImmuneConfig;
  private readonly hemocytes: ImmuneResponseSystem;
  private readonly agentCastes: Map<string, AgentCaste> = new Map();
  private dances: WaggleDance[] = [];
  private pheromone: ColonyPheromoneState;
  private stepCounter: number = 0;

  constructor(
    config: Partial<HiveImmuneConfig> = {},
    immuneConfig: Partial<ImmuneConfig> = {}
  ) {
    this.config = { ...DEFAULT_HIVE_CONFIG, ...config };
    this.hemocytes = new ImmuneResponseSystem(immuneConfig);
    this.pheromone = {
      alarm: 0,
      calm: this.config.queenCalmBase,
      posture: -this.config.queenCalmBase,
      feverActive: false,
      feverMultiplier: 1.0,
      activeDances: 0,
    };
  }

  // ═══════════════════════════════════════════════════════════════
  // Caste Management
  // ═══════════════════════════════════════════════════════════════

  /** Assign a caste to an agent */
  assignCaste(agentId: string, caste: AgentCaste): void {
    this.agentCastes.set(agentId, caste);
  }

  /** Get an agent's caste (defaults to worker) */
  getCaste(agentId: string): AgentCaste {
    return this.agentCastes.get(agentId) ?? 'worker';
  }

  /** Get the caste profile for an agent */
  getCasteProfile(agentId: string): CasteProfile {
    return CASTE_PROFILES[this.getCaste(agentId)];
  }

  /** Get all agents of a specific caste */
  getAgentsByCaste(caste: AgentCaste): string[] {
    const result: string[] = [];
    for (const [id, c] of this.agentCastes) {
      if (c === caste) result.push(id);
    }
    return result;
  }

  // ═══════════════════════════════════════════════════════════════
  // Tier 1: Propolis Barrier (Passive Mathematical Filtering)
  // ═══════════════════════════════════════════════════════════════

  /**
   * Check if a state vector passes the propolis barrier.
   * This is the outermost defense — pure mathematical validation.
   *
   * @param state - The 21D state vector to validate
   * @returns Propolis check result
   */
  checkPropolis(state: number[]): TieredImmuneResult['propolis'] {
    // Dimension check
    const dimensionCheck = state.length >= this.config.requiredDimensions;

    // Norm check (L2 norm must be within bounds)
    let norm = 0;
    for (let i = 0; i < state.length; i++) {
      norm += state[i] * state[i];
    }
    norm = Math.sqrt(norm);
    const normCheck = norm <= this.config.maxNorm && isFinite(norm);

    // Boundary distance (how far from Poincare boundary)
    const boundaryDistance = Math.max(0, POINCARE_MAX_NORM - norm);

    return {
      passed: dimensionCheck && normCheck,
      normCheck,
      dimensionCheck,
      boundaryDistance,
    };
  }

  // ═══════════════════════════════════════════════════════════════
  // Tier 3: Social Grooming (Neighbor-Based Anomaly Detection)
  // ═══════════════════════════════════════════════════════════════

  /**
   * Perform a waggle dance to report a threat.
   *
   * Any agent can dance, but the confidence is weighted by caste:
   * - Queen: 2.0x confidence (strongest signal)
   * - Guard: 1.5x
   * - Nurse: 1.0x
   * - Forager: 1.2x (good intelligence)
   * - Worker: 0.3x (weakest signal)
   */
  performWaggleDance(
    dancerId: string,
    targetId: string,
    anomalyDimensions: number[],
    magnitude: number,
    distanceFromCenter: number
  ): WaggleDance {
    const caste = this.getCaste(dancerId);
    const profile = CASTE_PROFILES[caste];
    const confidence = Math.min(1, magnitude * profile.pheromoneRate);

    const dance: WaggleDance = {
      dancerId,
      dancerCaste: caste,
      targetId,
      anomalyDimensions,
      magnitude: Math.min(1, Math.max(0, magnitude)),
      distanceFromCenter,
      confidence,
      timestamp: this.stepCounter,
      decayRate: Math.LN2 / this.config.danceDecayHalfLife,
    };

    this.dances.push(dance);

    // Trim old dances
    if (this.dances.length > this.config.danceHistorySize) {
      this.dances = this.dances.slice(-this.config.danceHistorySize);
    }

    // Each dance contributes to alarm pheromone
    this.pheromone.alarm = Math.min(
      1,
      this.pheromone.alarm + confidence * 0.05
    );

    return dance;
  }

  /**
   * Get all active (non-decayed) dances targeting a specific agent.
   */
  getActiveDancesFor(targetId: string): WaggleDance[] {
    return this.dances.filter((d) => {
      const age = this.stepCounter - d.timestamp;
      const decayedConfidence = d.confidence * Math.exp(-d.decayRate * age);
      return d.targetId === targetId && decayedConfidence > 0.01;
    });
  }

  /**
   * Compute the social grooming score for an agent.
   * This aggregates all waggle dances targeting this agent,
   * weighted by confidence and decay.
   */
  computeGroomingScore(targetId: string): {
    inspectedBy: string[];
    waggleDances: number;
    neighborConsensus: boolean;
    groomingScore: number;
  } {
    const activeDances = this.getActiveDancesFor(targetId);
    const inspectedBy = [...new Set(activeDances.map((d) => d.dancerId))];

    let totalScore = 0;
    for (const dance of activeDances) {
      const age = this.stepCounter - dance.timestamp;
      const decayedConfidence = dance.confidence * Math.exp(-dance.decayRate * age);
      totalScore += decayedConfidence * this.config.danceConfidenceWeight;
    }

    const neighborConsensus = activeDances.length >= this.config.minDancesForEffect;

    return {
      inspectedBy,
      waggleDances: activeDances.length,
      neighborConsensus,
      groomingScore: Math.min(1, totalScore),
    };
  }

  // ═══════════════════════════════════════════════════════════════
  // Tier 4: Colony Fever (Global Collective Response)
  // ═══════════════════════════════════════════════════════════════

  /**
   * Update the colony pheromone state and check for fever.
   *
   * Colony fever activates when alarm pheromone exceeds the threshold.
   * During fever, ALL detection thresholds are amplified (like bees
   * collectively raising hive temperature to kill pathogens).
   */
  updateColonyState(): ColonyPheromoneState {
    this.stepCounter++;

    // Natural alarm decay
    this.pheromone.alarm = Math.max(
      0,
      this.pheromone.alarm - this.config.alarmDecayRate
    );

    // Queen calming pheromone
    const hasQueen = this.getAgentsByCaste('queen').length > 0;
    this.pheromone.calm = hasQueen
      ? this.config.queenCalmBase
      : this.config.queenCalmBase * 0.5; // Reduced calming without queen

    // Compute net posture
    this.pheromone.posture = this.pheromone.alarm - this.pheromone.calm;

    // Colony fever check
    const wasFeverActive = this.pheromone.feverActive;
    this.pheromone.feverActive = this.pheromone.alarm >= this.config.feverThreshold;

    if (this.pheromone.feverActive) {
      // Fever ramps up: multiplier = 1 + (maxMultiplier - 1) * (alarm / 1.0)
      const ramp = (this.pheromone.alarm - this.config.feverThreshold) /
        (1 - this.config.feverThreshold);
      this.pheromone.feverMultiplier = 1 + (this.config.maxFeverMultiplier - 1) *
        Math.min(1, Math.max(0, ramp));
    } else {
      // Cool down toward 1.0
      this.pheromone.feverMultiplier = Math.max(
        1.0,
        this.pheromone.feverMultiplier - 0.1
      );
    }

    // Count active dances
    this.pheromone.activeDances = this.dances.filter((d) => {
      const age = this.stepCounter - d.timestamp;
      return d.confidence * Math.exp(-d.decayRate * age) > 0.01;
    }).length;

    return { ...this.pheromone };
  }

  /**
   * Get the current colony pheromone state
   */
  getPheromoneState(): ColonyPheromoneState {
    return { ...this.pheromone };
  }

  // ═══════════════════════════════════════════════════════════════
  // Full Tiered Assessment
  // ═══════════════════════════════════════════════════════════════

  /**
   * Process an agent through all four immune tiers.
   *
   * @param agentId - Agent to assess
   * @param state21D - Agent's 21D state vector
   * @param combinedScore - Detection combined score [0, 1]
   * @param flagCount - Number of detection mechanisms that flagged
   * @returns Complete tiered immune result
   */
  assess(
    agentId: string,
    state21D: number[],
    combinedScore: number,
    flagCount: number
  ): TieredImmuneResult {
    const caste = this.getCaste(agentId);
    const profile = CASTE_PROFILES[caste];

    // ── Tier 1: Propolis Barrier ──
    const propolis = this.checkPropolis(state21D);

    // If propolis fails, immediately deny
    if (!propolis.passed) {
      return {
        agentId,
        caste,
        propolis,
        hemocyte: this.hemocytes.getAgentStatus(agentId) ?? createDefaultStatus(agentId),
        grooming: { inspectedBy: [], waggleDances: 0, neighborConsensus: false, groomingScore: 0 },
        colonyFever: {
          feverActive: this.pheromone.feverActive,
          thresholdShift: 0,
          amplifiedSuspicion: 0,
        },
        finalDecision: 'DENY',
        effectiveTrust: 0,
      };
    }

    // ── Tier 2: Hemocyte Response ──
    const assessment = {
      detections: [],
      combinedScore,
      decision: scoreToDecision(combinedScore),
      anyFlagged: flagCount > 0,
      flagCount,
      timestamp: Date.now(),
    };
    const hemocyte = this.hemocytes.processAssessment(agentId, assessment);

    // ── Tier 3: Social Grooming ──
    const grooming = this.computeGroomingScore(agentId);

    // Grooming consensus increases suspicion
    if (grooming.neighborConsensus && grooming.groomingScore > 0.1) {
      // Feed grooming results back into hemocyte system
      const groomAssessment = {
        detections: [],
        combinedScore: grooming.groomingScore,
        decision: scoreToDecision(grooming.groomingScore),
        anyFlagged: true,
        flagCount: grooming.waggleDances,
        timestamp: Date.now(),
      };
      // Grooming accusations from inspecting agents
      const accusers = new Set(grooming.inspectedBy);
      this.hemocytes.processAssessment(agentId, groomAssessment, accusers);
    }

    // ── Tier 4: Colony Fever ──
    const thresholdShift = this.pheromone.feverActive
      ? (this.pheromone.feverMultiplier - 1) * 0.1
      : 0;

    // Amplify suspicion during fever
    const amplifiedSuspicion = hemocyte.suspicion * this.pheromone.feverMultiplier;

    const colonyFever = {
      feverActive: this.pheromone.feverActive,
      thresholdShift,
      amplifiedSuspicion,
    };

    // ── Compute Final Decision ──
    // Start with hemocyte-based decision
    let decision = immuneStateToDecision(hemocyte.state);

    // Colony fever shifts thresholds (lower threshold = more sensitive)
    if (this.pheromone.feverActive) {
      if (amplifiedSuspicion >= 0.5 && decision === 'ALLOW') {
        decision = 'QUARANTINE';
      }
      if (amplifiedSuspicion >= 0.8) {
        decision = 'DENY';
      }
    }

    // Grooming consensus can escalate
    if (grooming.neighborConsensus && grooming.groomingScore > 0.5 && decision === 'ALLOW') {
      decision = 'QUARANTINE';
    }

    // Caste trust modifier
    const baseTrust = 1 - hemocyte.suspicion;
    const effectiveTrust = Math.max(
      0,
      Math.min(1, baseTrust * profile.trustMultiplier)
    );

    return {
      agentId,
      caste,
      propolis,
      hemocyte,
      grooming,
      colonyFever,
      finalDecision: decision,
      effectiveTrust,
    };
  }

  // ═══════════════════════════════════════════════════════════════
  // Colony Management
  // ═══════════════════════════════════════════════════════════════

  /** Get the underlying hemocyte system */
  getHemocytes(): ImmuneResponseSystem {
    return this.hemocytes;
  }

  /** Get all waggle dances */
  getDances(): ReadonlyArray<WaggleDance> {
    return this.dances;
  }

  /** Get colony statistics */
  getStats(): {
    totalAgents: number;
    casteCounts: Record<AgentCaste, number>;
    pheromone: ColonyPheromoneState;
    activeDances: number;
    hemocyteStats: ReturnType<ImmuneResponseSystem['getStats']>;
    step: number;
  } {
    const casteCounts: Record<AgentCaste, number> = {
      queen: 0, guard: 0, nurse: 0, forager: 0, undertaker: 0, worker: 0,
    };
    for (const caste of this.agentCastes.values()) {
      casteCounts[caste]++;
    }

    return {
      totalAgents: this.agentCastes.size,
      casteCounts,
      pheromone: { ...this.pheromone },
      activeDances: this.pheromone.activeDances,
      hemocyteStats: this.hemocytes.getStats(),
      step: this.stepCounter,
    };
  }

  /** Reset the entire hive immune state */
  reset(): void {
    this.agentCastes.clear();
    this.dances = [];
    this.stepCounter = 0;
    this.pheromone = {
      alarm: 0,
      calm: this.config.queenCalmBase,
      posture: -this.config.queenCalmBase,
      feverActive: false,
      feverMultiplier: 1.0,
      activeDances: 0,
    };
  }
}

// ═══════════════════════════════════════════════════════════════
// Helper Functions
// ═══════════════════════════════════════════════════════════════

function scoreToDecision(score: number): RiskDecision {
  if (score >= 0.9) return 'DENY';
  if (score >= 0.7) return 'ESCALATE';
  if (score >= 0.5) return 'QUARANTINE';
  return 'ALLOW';
}

function immuneStateToDecision(state: ImmuneState): RiskDecision {
  switch (state) {
    case 'expelled': return 'DENY';
    case 'quarantined': return 'QUARANTINE';
    case 'inflamed': return 'ESCALATE';
    case 'monitoring': return 'ALLOW';
    case 'healthy': return 'ALLOW';
  }
}

function createDefaultStatus(agentId: string): AgentImmuneStatus {
  return {
    agentId,
    suspicion: 0,
    flagCount: 0,
    state: 'healthy',
    repulsionForce: 0,
    accusers: new Set(),
    lastStateChange: Date.now(),
    quarantineCount: 0,
    suspicionHistory: [],
  };
}
