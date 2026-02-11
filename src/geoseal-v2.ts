/**
 * @file geoseal-v2.ts
 * @module geoseal-v2
 * @layer Layer 9, Layer 12, Layer 13
 * @version 2.0.0
 *
 * GeoSeal v2: Mixed-Curvature Geometric Access Control Kernel
 *
 * Extends GeoSeal v1 with a product manifold H^a x S^b x R^c where:
 * - Hyperbolic (H^a): hierarchy, trust zones, boundary quarantine
 * - Spherical  (S^b): tongue phase discipline, cyclic role coherence
 * - Gaussian   (R^c): retrieval uncertainty, memory write gating
 *
 * Each agent carries three coordinate families:
 *   u ∈ B^n   (Poincaré ball position)     — hierarchy / containment
 *   p ∈ S^1   (phase as [cos θ, sin θ])    — tongue discipline
 *   (μ, σ²)   (diagonal Gaussian)          — retrieval confidence
 *
 * Scoring fuses three independent geometry scores:
 *   trust = w_H · s_H + w_S · s_S + w_G · s_G
 *
 * where:
 *   s_H = 1 / (1 + d_H)               — hyperbolic proximity
 *   s_S = 1 - phaseDeviation           — phase consistency
 *   s_G = 1 / (1 + trace(Σ))          — uncertainty (low = trustworthy)
 *
 * Quarantine triggers when fused trust drops below threshold OR when
 * spatial consensus (3+ neighbors) flags the agent.
 */

import {
  hyperbolicDistance,
  phaseDeviation,
  clampToBall,
} from './harmonic/hyperbolic.js';
import {
  TONGUE_PHASES,
  SUSPICION_DECAY,
  SUSPICION_THRESHOLD,
  QUARANTINE_CONSENSUS,
  TRUST_DENOMINATOR,
} from './geoseal.js';

// Re-export v1 constants for convenience
export { TONGUE_PHASES, SUSPICION_THRESHOLD, QUARANTINE_CONSENSUS };

// ═══════════════════════════════════════════════════════════════
// Fusion weights (tunable hyperparameters)
// ═══════════════════════════════════════════════════════════════

export interface FusionWeights {
  /** Weight for hyperbolic proximity score */
  wH: number;
  /** Weight for spherical phase consistency score */
  wS: number;
  /** Weight for Gaussian certainty score */
  wG: number;
}

export const DEFAULT_FUSION_WEIGHTS: FusionWeights = {
  wH: 0.4,
  wS: 0.35,
  wG: 0.25,
};

/** Quarantine threshold for fused trust score */
export const QUARANTINE_TRUST_THRESHOLD = 0.3;

/** Memory write threshold (only chunks above this get promoted) */
export const MEMORY_WRITE_THRESHOLD = 0.7;

// ═══════════════════════════════════════════════════════════════
// Mixed-geometry Agent (v2)
// ═══════════════════════════════════════════════════════════════

export interface MixedAgent {
  id: string;

  // --- Hyperbolic component (H^a) ---
  /** Embedding position in Poincaré ball */
  position: number[];

  // --- Spherical component (S^1) ---
  /** Tongue phase angle (null if unknown/rogue) */
  phase: number | null;
  /** Phase as [cos θ, sin θ] for computation (auto-derived) */
  phaseVec: [number, number];

  // --- Gaussian component ---
  /** Uncertainty variance (diagonal; scalar per dimension) */
  sigma: number;

  // --- Metadata ---
  tongue?: string;
  suspicion_count: Map<string, number>;
  is_quarantined: boolean;
  trust_score: number;

  // --- v2 scoring breakdown ---
  score_hyperbolic: number;
  score_phase: number;
  score_certainty: number;
}

/**
 * Create a v2 mixed-geometry agent.
 *
 * @param id - Agent identifier
 * @param position - Poincaré ball embedding
 * @param phase - Tongue phase (null = rogue)
 * @param sigma - Uncertainty variance (0 = perfectly certain)
 * @param tongue - Optional tongue code
 * @param trust - Initial trust score
 */
export function createMixedAgent(
  id: string,
  position: number[],
  phase: number | null,
  sigma: number = 0.0,
  tongue?: string,
  trust: number = 0.5
): MixedAgent {
  return {
    id,
    position: [...position],
    phase,
    phaseVec: phase !== null ? [Math.cos(phase), Math.sin(phase)] : [0, 0],
    sigma,
    tongue,
    suspicion_count: new Map(),
    is_quarantined: false,
    trust_score: trust,
    score_hyperbolic: 0,
    score_phase: 0,
    score_certainty: 0,
  };
}

// ═══════════════════════════════════════════════════════════════
// Individual geometry scores
// ═══════════════════════════════════════════════════════════════

/**
 * Hyperbolic proximity score: s_H = 1 / (1 + d_H)
 * High when agents are close in the Poincaré ball.
 */
export function scoreHyperbolic(a: MixedAgent, b: MixedAgent): number {
  const dH = hyperbolicDistance(a.position, b.position);
  return 1.0 / (1.0 + dH);
}

/**
 * Spherical phase consistency score: s_S = 1 - phaseDeviation
 * High when agents share the same tongue phase.
 */
export function scorePhase(a: MixedAgent, b: MixedAgent): number {
  return 1.0 - phaseDeviation(a.phase, b.phase);
}

/**
 * Gaussian certainty score: s_G = 1 / (1 + σ²)
 * High when the agent has low uncertainty.
 * Scored for agent b (the candidate being evaluated).
 */
export function scoreCertainty(b: MixedAgent): number {
  return 1.0 / (1.0 + b.sigma);
}

// ═══════════════════════════════════════════════════════════════
// Product manifold fusion
// ═══════════════════════════════════════════════════════════════

export interface FusedScore {
  /** Combined trust score in [0, 1] */
  trust: number;
  /** Individual geometry scores */
  sH: number;
  sS: number;
  sG: number;
  /** Anomaly flag (any geometry triggered) */
  anomaly: boolean;
  /** Recommended action */
  action: 'ALLOW' | 'QUARANTINE' | 'DENY';
}

/**
 * Fuse three geometry scores into a single trust value.
 *
 * trust = w_H * s_H + w_S * s_S + w_G * s_G
 *
 * Actions:
 * - ALLOW:      trust >= MEMORY_WRITE_THRESHOLD
 * - QUARANTINE: QUARANTINE_TRUST_THRESHOLD <= trust < MEMORY_WRITE_THRESHOLD
 * - DENY:       trust < QUARANTINE_TRUST_THRESHOLD
 *
 * @param anchor - Reference agent (e.g., tongue agent)
 * @param candidate - Agent being evaluated
 * @param weights - Fusion weights (default: 0.4/0.35/0.25)
 */
export function fuseScores(
  anchor: MixedAgent,
  candidate: MixedAgent,
  weights: FusionWeights = DEFAULT_FUSION_WEIGHTS
): FusedScore {
  const sH = scoreHyperbolic(anchor, candidate);
  const sS = scorePhase(anchor, candidate);
  const sG = scoreCertainty(candidate);

  const trust = weights.wH * sH + weights.wS * sS + weights.wG * sG;

  // Anomaly: low phase consistency or high uncertainty
  const anomaly = sS < 0.5 || sG < 0.5;

  let action: 'ALLOW' | 'QUARANTINE' | 'DENY';
  if (trust >= MEMORY_WRITE_THRESHOLD) {
    action = 'ALLOW';
  } else if (trust >= QUARANTINE_TRUST_THRESHOLD) {
    action = 'QUARANTINE';
  } else {
    action = 'DENY';
  }

  return { trust, sH, sS, sG, anomaly, action };
}

// ═══════════════════════════════════════════════════════════════
// v2 Suspicion (same algorithm as v1, applied to MixedAgent)
// ═══════════════════════════════════════════════════════════════

export function updateSuspicionV2(
  agent: MixedAgent,
  neighbor_id: string,
  is_anomaly: boolean
): void {
  if (is_anomaly) {
    const current = agent.suspicion_count.get(neighbor_id) || 0;
    agent.suspicion_count.set(neighbor_id, current + 1);
  } else {
    const current = agent.suspicion_count.get(neighbor_id) || 0;
    agent.suspicion_count.set(neighbor_id, Math.max(0, current - SUSPICION_DECAY));
  }

  let suspicious_neighbors = 0;
  for (const count of agent.suspicion_count.values()) {
    if (count >= SUSPICION_THRESHOLD) suspicious_neighbors++;
  }
  agent.is_quarantined = suspicious_neighbors >= QUARANTINE_CONSENSUS;

  let total_suspicion = 0;
  for (const count of agent.suspicion_count.values()) {
    total_suspicion += count;
  }
  agent.trust_score = Math.max(0, 1.0 - total_suspicion / TRUST_DENOMINATOR);
}

// ═══════════════════════════════════════════════════════════════
// v2 Repulsion (enhanced with uncertainty amplification)
// ═══════════════════════════════════════════════════════════════

export interface RepulsionResultV2 {
  force: number[];
  amplification: number;
  anomaly_flag: boolean;
  fused: FusedScore;
}

/**
 * v2 repulsion force: includes uncertainty in amplification.
 *
 * Amplification rules (additive):
 * - v1 phase rules still apply (null=2.0x, mismatch=1.5x+dev, quarantine=1.5x)
 * - High uncertainty (σ > 0.5) adds +0.5x amplification
 * - Fused anomaly adds +0.25x
 */
export function computeRepelForceV2(
  agent_a: MixedAgent,
  agent_b: MixedAgent,
  anchor: MixedAgent | null = null,
  base_strength: number = 1.0,
  weights: FusionWeights = DEFAULT_FUSION_WEIGHTS
): RepulsionResultV2 {
  const d_H = hyperbolicDistance(agent_a.position, agent_b.position);
  const base_repulsion = base_strength / (d_H + 1e-6);

  // v1 phase-based amplification
  let amplification = 1.0;
  let anomaly_flag = false;

  if (agent_b.phase === null) {
    amplification = 2.0;
    anomaly_flag = true;
  } else if (agent_a.phase !== null) {
    const deviation = phaseDeviation(agent_a.phase, agent_b.phase);
    if (d_H < 1.0 && deviation > 0.5) {
      amplification = 1.5 + deviation;
      anomaly_flag = true;
    }
  }

  if (agent_b.is_quarantined) {
    amplification *= 1.5;
  }

  // v2: uncertainty amplification
  if (agent_b.sigma > 0.5) {
    amplification += 0.5;
    anomaly_flag = true;
  }

  // v2: fused score (use anchor if provided, else agent_a)
  // Only apply fused anomaly amplification when the source has a valid phase;
  // a null-phase source would always produce sS=0, falsely flagging legit targets.
  const ref = anchor || agent_a;
  const fused = fuseScores(ref, agent_b, weights);

  if (fused.anomaly && ref.phase !== null) {
    amplification += 0.25;
    anomaly_flag = true;
  }

  // Force vector
  const dim = agent_a.position.length;
  const force = new Array<number>(dim);
  for (let i = 0; i < dim; i++) {
    const direction = agent_a.position[i] - agent_b.position[i];
    force[i] = direction * base_repulsion * amplification;
  }

  // Store score breakdown on the candidate
  agent_b.score_hyperbolic = fused.sH;
  agent_b.score_phase = fused.sS;
  agent_b.score_certainty = fused.sG;

  return { force, amplification, anomaly_flag, fused };
}

// ═══════════════════════════════════════════════════════════════
// v2 Swarm dynamics
// ═══════════════════════════════════════════════════════════════

/**
 * Run one v2 swarm update step.
 *
 * Same structure as v1 but uses mixed-geometry repulsion and
 * optionally applies uncertainty decay (σ decreases when an agent
 * consistently matches its neighbors, increases under anomaly).
 */
export function swarmStepV2(
  agents: MixedAgent[],
  drift_rate: number = 0.01,
  sigma_decay: number = 0.01,
  weights: FusionWeights = DEFAULT_FUSION_WEIGHTS
): MixedAgent[] {
  const n = agents.length;
  const dim = agents[0]?.position.length ?? 0;

  for (let i = 0; i < n; i++) {
    const net_force = new Array<number>(dim).fill(0);

    for (let j = 0; j < n; j++) {
      if (i === j) continue;

      const result = computeRepelForceV2(agents[i], agents[j], null, 1.0, weights);

      for (let k = 0; k < dim; k++) {
        net_force[k] += result.force[k];
      }

      // Update suspicion on the TARGET (j) from the SOURCE (i)
      updateSuspicionV2(agents[j], agents[i].id, result.anomaly_flag);
    }

    // Apply force with drift
    for (let k = 0; k < dim; k++) {
      agents[i].position[k] += net_force[k] * drift_rate;
    }
    agents[i].position = clampToBall(agents[i].position, 0.99);

    // v2: uncertainty evolution
    // Sigma is driven by how much others flag THIS agent (suspicion_count),
    // not by how many anomalies it detects on others.
    let total_incoming_suspicion = 0;
    for (const count of agents[i].suspicion_count.values()) {
      total_incoming_suspicion += count;
    }
    if (total_incoming_suspicion > 3) {
      // Others are flagging this agent: uncertainty grows
      agents[i].sigma = Math.min(10.0, agents[i].sigma + sigma_decay * 2);
    } else {
      // Not being flagged: uncertainty decays
      agents[i].sigma = Math.max(0, agents[i].sigma - sigma_decay);
    }
  }

  return agents;
}

/**
 * Run multiple v2 swarm steps.
 */
export function runSwarmV2(
  agents: MixedAgent[],
  num_steps: number = 10,
  drift_rate: number = 0.01,
  sigma_decay: number = 0.01,
  weights: FusionWeights = DEFAULT_FUSION_WEIGHTS
): MixedAgent[] {
  for (let step = 0; step < num_steps; step++) {
    swarmStepV2(agents, drift_rate, sigma_decay, weights);
  }
  return agents;
}

// ═══════════════════════════════════════════════════════════════
// v2 Batch scoring (for RAG result reranking)
// ═══════════════════════════════════════════════════════════════

export interface ScoredCandidate {
  id: string;
  trust: number;
  action: 'ALLOW' | 'QUARANTINE' | 'DENY';
  sH: number;
  sS: number;
  sG: number;
  is_quarantined: boolean;
  sigma: number;
}

/**
 * Score all candidates against a set of tongue anchors.
 *
 * For each candidate, computes the best fused score across all anchors
 * (i.e., the tongue that trusts this candidate the most).
 *
 * @param anchors - Tongue agents (trusted references)
 * @param candidates - Retrieval/memory agents to score
 * @param weights - Fusion weights
 * @returns Scored candidates sorted by trust (descending)
 */
export function scoreAllCandidates(
  anchors: MixedAgent[],
  candidates: MixedAgent[],
  weights: FusionWeights = DEFAULT_FUSION_WEIGHTS
): ScoredCandidate[] {
  const results: ScoredCandidate[] = [];

  for (const candidate of candidates) {
    // Best score across all anchors
    let bestFused: FusedScore | null = null;

    for (const anchor of anchors) {
      const fused = fuseScores(anchor, candidate, weights);
      if (!bestFused || fused.trust > bestFused.trust) {
        bestFused = fused;
      }
    }

    if (bestFused) {
      results.push({
        id: candidate.id,
        trust: bestFused.trust,
        action: bestFused.action,
        sH: bestFused.sH,
        sS: bestFused.sS,
        sG: bestFused.sG,
        is_quarantined: candidate.is_quarantined,
        sigma: candidate.sigma,
      });
    }
  }

  // Sort by trust descending
  results.sort((a, b) => b.trust - a.trust);
  return results;
}
