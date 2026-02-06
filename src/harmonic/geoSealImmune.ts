/**
 * @file geoSealImmune.ts
 * @module harmonic/geoSealImmune
 * @layer Layer 5, Layer 8, Layer 13
 * @component GeoSeal Immune System
 * @version 3.2.5
 *
 * Immune-like dynamics for RAG filtering using hyperbolic geometry
 * and phase discipline. Detects and quarantines adversarial or
 * off-grammar retrievals using swarm-based repulsion.
 */

import { hyperbolicDistance, mobiusAdd, projectToBall } from './hyperbolic';

// ═══════════════════════════════════════════════════════════════
// Sacred Tongues Phase Mapping
// ═══════════════════════════════════════════════════════════════

/** Phase angles for the Six Sacred Tongues (radians) */
export const TONGUE_PHASES: Record<string, number> = {
  KO: 0.0,                    // Kor'aelin - Control/orchestration
  AV: Math.PI / 3,            // Avali - Initialization/transport
  RU: (2 * Math.PI) / 3,      // Runethic - Policy/authorization
  CA: Math.PI,                // Cassisivadan - Encryption/compute
  UM: (4 * Math.PI) / 3,      // Umbroth - Redaction/privacy
  DR: (5 * Math.PI) / 3,      // Draumric - Authentication/integrity
};

/** Reverse mapping: phase → tongue name */
export const PHASE_TO_TONGUE: Map<number, string> = new Map(
  Object.entries(TONGUE_PHASES).map(([k, v]) => [v, k])
);

// ═══════════════════════════════════════════════════════════════
// Agent Types
// ═══════════════════════════════════════════════════════════════

/**
 * Agent in the GeoSeal immune swarm.
 *
 * Represents either:
 * - A Sacred Tongue (legitimate, fixed phase)
 * - A retrieval/tool output (candidate, assigned or null phase)
 * - A memory chunk (probationary, builds trust over time)
 */
export interface SwarmAgent {
  id: string;
  position: number[];          // Embedding in Poincaré ball (||v|| < 1)
  phase: number | null;        // Tongue phase, or null if rogue/unknown
  tongue?: string;             // Which Sacred Tongue (if any)
  suspicionCount: Map<string, number>;  // Per-neighbor suspicion
  isQuarantined: boolean;
  trustScore: number;          // 0.0 = untrusted, 1.0 = fully trusted
}

/** Result of computing repulsion force between two agents */
export interface RepulsionResult {
  force: number[];
  amplification: number;
  anomalyFlag: boolean;
}

/** Metrics from swarm immune dynamics */
export interface SwarmMetrics {
  quarantineCount: number;
  avgTrustScore: number;
  boundaryAgents: number;    // Agents pushed near boundary (norm > 0.9)
  suspiciousPairs: number;   // Number of agent pairs with high suspicion
}

// ═══════════════════════════════════════════════════════════════
// Core Functions
// ═══════════════════════════════════════════════════════════════

/**
 * Compute normalized phase deviation in [0, 1].
 *
 * Returns 1.0 (maximum) if either phase is null (rogue/unknown).
 * Otherwise returns angular difference normalized to [0, 1].
 */
export function phaseDeviation(
  phase1: number | null,
  phase2: number | null
): number {
  if (phase1 === null || phase2 === null) {
    return 1.0; // Maximum deviation for unknown phase
  }

  let diff = Math.abs(phase1 - phase2);
  // Wrap to [0, π]
  if (diff > Math.PI) {
    diff = 2 * Math.PI - diff;
  }

  return diff / Math.PI; // Normalize to [0, 1]
}

/**
 * Compute vector norm (Euclidean length).
 */
function norm(v: number[]): number {
  return Math.sqrt(v.reduce((sum, x) => sum + x * x, 0));
}

/**
 * Core GeoSeal repulsion force computation.
 *
 * Implements immune-like response to phase-weird agents:
 * - Null phase (unknown/rogue) → 2.0x force amplification
 * - Wrong phase at close distance → 1.5x + deviation amplification
 * - Quarantined agents → additional 1.5x multiplier
 */
export function computeRepelForce(
  agentA: SwarmAgent,
  agentB: SwarmAgent,
  baseStrength: number = 1.0
): RepulsionResult {
  // Compute hyperbolic distance
  let dH: number;
  try {
    dH = hyperbolicDistance(agentA.position, agentB.position);
  } catch {
    // Fallback to Euclidean if points are at boundary
    const diff = agentA.position.map((v, i) => v - agentB.position[i]);
    dH = norm(diff);
  }

  // Base repulsion: inversely proportional to distance
  const baseRepulsion = baseStrength / (dH + 1e-6);

  // Compute phase-based amplification
  let amplification = 1.0;
  let anomalyFlag = false;

  if (agentB.phase === null) {
    // Null phase (unknown/rogue) → maximum amplification
    amplification = 2.0;
    anomalyFlag = true;
  } else if (agentA.phase !== null) {
    // Both have phases, check for mismatch
    const deviation = phaseDeviation(agentA.phase, agentB.phase);

    // Expected: agents with similar phases should cluster
    // If phases differ significantly at close distance → suspicious
    if (dH < 1.0 && deviation > 0.5) {
      amplification = 1.5 + deviation;
      anomalyFlag = true;
    }
  }

  // If agentB is quarantined, boost repulsion further
  if (agentB.isQuarantined) {
    amplification *= 1.5;
  }

  // Compute force vector (direction: away from agentB)
  const direction = agentA.position.map((v, i) => v - agentB.position[i]);
  const dirNorm = norm(direction);

  const force =
    dirNorm > 1e-8
      ? direction.map((v) => (v / dirNorm) * baseRepulsion * amplification)
      : direction.map(() => 0);

  return { force, amplification, anomalyFlag };
}

/**
 * Update suspicion counters and quarantine status.
 *
 * Temporal integration filters transient flukes:
 * - Anomaly detection increments suspicion by 1
 * - No anomaly decays suspicion by decayRate
 * - Quarantine requires consensusThreshold+ neighbors with
 *   suspicion >= suspicionThreshold
 */
export function updateSuspicion(
  agent: SwarmAgent,
  neighborId: string,
  isAnomaly: boolean,
  decayRate: number = 0.5,
  suspicionThreshold: number = 3,
  consensusThreshold: number = 3
): void {
  if (isAnomaly) {
    const current = agent.suspicionCount.get(neighborId) || 0;
    agent.suspicionCount.set(neighborId, current + 1);
  } else {
    // Decay suspicion if no anomaly detected
    const current = agent.suspicionCount.get(neighborId) || 0;
    agent.suspicionCount.set(neighborId, Math.max(0, current - decayRate));
  }

  // Count how many neighbors are suspicious
  let suspiciousNeighbors = 0;
  for (const count of agent.suspicionCount.values()) {
    if (count >= suspicionThreshold) {
      suspiciousNeighbors++;
    }
  }

  // Quarantine threshold: consensusThreshold+ neighbors with high suspicion
  agent.isQuarantined = suspiciousNeighbors >= consensusThreshold;

  // Update trust score (inverse of normalized suspicion)
  let totalSuspicion = 0;
  for (const count of agent.suspicionCount.values()) {
    totalSuspicion += count;
  }
  agent.trustScore = Math.max(0, 1.0 - totalSuspicion / 20.0);
}

/**
 * Run one swarm update step for all agents.
 *
 * Computes pairwise repulsion forces, updates positions,
 * tracks suspicion, and enforces Poincaré ball containment.
 */
export function swarmStep(
  agents: SwarmAgent[],
  driftRate: number = 0.01,
  ballRadius: number = 0.99
): SwarmAgent[] {
  const n = agents.length;

  for (let i = 0; i < n; i++) {
    const netForce = agents[i].position.map(() => 0);

    for (let j = 0; j < n; j++) {
      if (i === j) continue;

      const result = computeRepelForce(agents[i], agents[j]);

      // Accumulate force on agent i
      for (let k = 0; k < netForce.length; k++) {
        netForce[k] += result.force[k];
      }

      // Update suspicion ON agent_j (the one being observed)
      updateSuspicion(agents[j], agents[i].id, result.anomalyFlag);
    }

    // Apply force with drift rate
    for (let k = 0; k < agents[i].position.length; k++) {
      agents[i].position[k] += netForce[k] * driftRate;
    }

    // Clamp to Poincaré ball (radius < 1)
    const posNorm = norm(agents[i].position);
    if (posNorm >= ballRadius) {
      const scale = ballRadius / posNorm;
      agents[i].position = agents[i].position.map((v) => v * scale);
    }
  }

  return agents;
}

/**
 * Run multiple swarm update steps.
 */
export function runSwarmDynamics(
  agents: SwarmAgent[],
  numSteps: number = 10,
  driftRate: number = 0.01
): SwarmAgent[] {
  for (let i = 0; i < numSteps; i++) {
    agents = swarmStep(agents, driftRate);
  }
  return agents;
}

// ═══════════════════════════════════════════════════════════════
// Agent Factory Functions
// ═══════════════════════════════════════════════════════════════

/**
 * Initialize the 6 Sacred Tongues as legitimate agents.
 */
export function createTongueAgents(dimension: number = 64): SwarmAgent[] {
  const agents: SwarmAgent[] = [];
  const radius = 0.3; // Place tongues near center (high trust)

  for (const [tongue, phase] of Object.entries(TONGUE_PHASES)) {
    // Position based on phase angle
    const position = new Array(dimension).fill(0);
    position[0] = radius * Math.cos(phase);
    position[1] = radius * Math.sin(phase);

    agents.push({
      id: `tongue-${tongue}`,
      position,
      phase,
      tongue,
      suspicionCount: new Map(),
      isQuarantined: false,
      trustScore: 1.0,
    });
  }

  return agents;
}

/**
 * Create a candidate agent for immune evaluation.
 */
export function createCandidateAgent(
  agentId: string,
  embedding: number[],
  assignedTongue?: string,
  initialTrust: number = 0.5
): SwarmAgent {
  const phase = assignedTongue ? TONGUE_PHASES[assignedTongue] ?? null : null;

  // Project embedding to Poincaré ball if needed
  let position = [...embedding];
  const posNorm = norm(position);
  if (posNorm >= 1.0) {
    position = position.map((v) => (v / (posNorm + 1e-6)) * 0.95);
  }

  return {
    id: agentId,
    position,
    phase,
    tongue: assignedTongue,
    suspicionCount: new Map(),
    isQuarantined: false,
    trustScore: initialTrust,
  };
}

// ═══════════════════════════════════════════════════════════════
// Filtering and Metrics
// ═══════════════════════════════════════════════════════════════

/**
 * Filter agents by trust score, returning only those above threshold.
 */
export function filterByTrust(
  agents: SwarmAgent[],
  threshold: number = 0.3
): SwarmAgent[] {
  return agents.filter(
    (a) => a.trustScore >= threshold || a.id.startsWith('tongue-')
  );
}

/**
 * Extract trust scores as attention weights for RAG reweighting.
 */
export function getAttentionWeights(
  agents: SwarmAgent[]
): Map<string, number> {
  const weights = new Map<string, number>();
  for (const agent of agents) {
    if (!agent.id.startsWith('tongue-')) {
      weights.set(agent.id, agent.trustScore);
    }
  }
  return weights;
}

/**
 * Compute metrics for monitoring swarm health.
 */
export function computeSwarmMetrics(agents: SwarmAgent[]): SwarmMetrics {
  const nonTongue = agents.filter((a) => !a.id.startsWith('tongue-'));

  if (nonTongue.length === 0) {
    return {
      quarantineCount: 0,
      avgTrustScore: 1.0,
      boundaryAgents: 0,
      suspiciousPairs: 0,
    };
  }

  const quarantineCount = nonTongue.filter((a) => a.isQuarantined).length;
  const avgTrustScore =
    nonTongue.reduce((sum, a) => sum + a.trustScore, 0) / nonTongue.length;
  const boundaryAgents = nonTongue.filter((a) => norm(a.position) > 0.9).length;

  let suspiciousPairs = 0;
  for (const agent of nonTongue) {
    for (const count of agent.suspicionCount.values()) {
      if (count >= 3) suspiciousPairs++;
    }
  }

  return {
    quarantineCount,
    avgTrustScore,
    boundaryAgents,
    suspiciousPairs,
  };
}

// ═══════════════════════════════════════════════════════════════
// RAG Integration Helper
// ═══════════════════════════════════════════════════════════════

/**
 * GeoSeal filter context for RAG pipeline integration.
 */
export interface GeoSealContext {
  tongueAgents: SwarmAgent[];
  candidateAgents: SwarmAgent[];
}

/**
 * Run GeoSeal immune filtering on a set of candidates.
 *
 * Returns attention weights for each candidate (0.0 to 1.0).
 * Low weights indicate adversarial or off-grammar content.
 */
export function geoSealFilter(
  candidates: Array<{ id: string; embedding: number[]; tongue?: string }>,
  numSteps: number = 10,
  dimension: number = 64
): Map<string, number> {
  // Initialize tongue agents
  const tongueAgents = createTongueAgents(dimension);

  // Create candidate agents
  const candidateAgents = candidates.map((c) =>
    createCandidateAgent(c.id, c.embedding, c.tongue, 0.5)
  );

  // Combine and run dynamics
  let allAgents = [...tongueAgents, ...candidateAgents];
  allAgents = runSwarmDynamics(allAgents, numSteps, 0.02);

  // Extract attention weights
  return getAttentionWeights(allAgents);
}
