/**
 * Byzantine Fault Detection & Rogue Agent Handling
 * =================================================
 *
 * Implements Byzantine fault tolerance for swarm coordination.
 *
 * Theorem: Need 3f + 1 agents to tolerate f Byzantine faults
 * - 6 agents → tolerate 1 Byzantine fault (f=1, 3×1+1=4)
 * - 9 agents → tolerate 2 Byzantine faults (f=2, 3×2+1=7)
 *
 * Detection Methods:
 * - Position consistency checking
 * - Phase-null intruder detection
 * - Replay attack detection
 * - Sybil attack prevention (PoW)
 *
 * @module fleet/byzantine
 * @version 1.0.0
 * @since 2026-01-29
 */

import { createHmac, randomBytes } from 'crypto';
import { Position3D, euclideanDistance, hyperbolicDistance } from './formations';
import { TongueID } from '../spiralverse/types';

/**
 * Agent report from a peer
 */
export interface PeerReport {
  /** Reporter agent ID */
  reporterId: string;
  /** Subject agent ID */
  subjectId: string;
  /** Reported position */
  position: Position3D;
  /** Reported phase */
  phase: number;
  /** Report timestamp */
  timestamp: number;
  /** Signature for authenticity */
  signature?: string;
}

/**
 * Byzantine detection result
 */
export interface ByzantineDetectionResult {
  /** Detected Byzantine agents */
  byzantineAgents: string[];
  /** Confidence scores (0-1) */
  confidences: Map<string, number>;
  /** Detection reasons */
  reasons: Map<string, string[]>;
  /** Timestamp of detection */
  timestamp: number;
}

/**
 * Rogue agent types
 */
export type RogueType =
  | 'phase_null'
  | 'position_inconsistent'
  | 'replay_attack'
  | 'sybil'
  | 'coherence_drop'
  | 'boundary_violation';

/**
 * Rogue agent detection result
 */
export interface RogueDetectionResult {
  agentId: string;
  type: RogueType;
  severity: 'low' | 'medium' | 'high' | 'critical';
  details: string;
  detectedAt: number;
  /** Recommended action */
  action: 'monitor' | 'quarantine' | 'expel';
}

/**
 * Quarantine state
 */
export interface QuarantineState {
  agentId: string;
  reason: RogueType;
  quarantinedAt: number;
  /** Position pushed to boundary */
  boundaryPosition: Position3D;
  /** Release conditions */
  releaseConditions: string[];
  /** Whether agent can be released */
  canRelease: boolean;
}

/**
 * PoW challenge for Sybil prevention
 */
export interface PoWChallenge {
  publicKey: string;
  nonce: string;
  difficulty: number;
  createdAt: number;
  expiresAt: number;
}

/**
 * Byzantine detection thresholds
 */
export interface ByzantineThresholds {
  /** Position variance threshold */
  positionVariance: number;
  /** Phase deviation threshold (radians) */
  phaseDeviation: number;
  /** Coherence drop threshold */
  coherenceDropThreshold: number;
  /** Boundary distance threshold */
  boundaryThreshold: number;
  /** Minimum reports needed for detection */
  minReports: number;
}

/**
 * Default thresholds
 */
export const DEFAULT_THRESHOLDS: ByzantineThresholds = {
  positionVariance: 0.1,
  phaseDeviation: Math.PI / 4, // 45°
  coherenceDropThreshold: 0.65,
  boundaryThreshold: 0.87,
  minReports: 3,
};

/**
 * Byzantine Fault Detector
 *
 * Detects Byzantine (malicious/faulty) agents in the swarm.
 */
export class ByzantineDetector {
  private thresholds: ByzantineThresholds;
  private reports: Map<string, PeerReport[]> = new Map(); // subjectId -> reports
  private nonceCache: Set<string> = new Set();
  private nonceTimes: Map<string, number> = new Map();
  private quarantined: Map<string, QuarantineState> = new Map();

  constructor(thresholds: ByzantineThresholds = DEFAULT_THRESHOLDS) {
    this.thresholds = thresholds;
  }

  /**
   * Submit a peer report
   *
   * Each agent reports what it observes about other agents.
   */
  public submitReport(report: PeerReport): void {
    const existing = this.reports.get(report.subjectId) || [];
    existing.push(report);
    this.reports.set(report.subjectId, existing);

    // Cleanup old reports (> 5 minutes)
    this.cleanupOldReports(report.subjectId);
  }

  /**
   * Detect Byzantine agents based on collected reports
   *
   * An agent is Byzantine if different peers report inconsistent states.
   */
  public detectByzantine(): ByzantineDetectionResult {
    const byzantineAgents: string[] = [];
    const confidences = new Map<string, number>();
    const reasons = new Map<string, string[]>();

    const reportEntries = Array.from(this.reports.entries());
    for (const [subjectId, reports] of reportEntries) {
      if (reports.length < this.thresholds.minReports) {
        continue; // Not enough reports
      }

      const agentReasons: string[] = [];
      let byzantineScore = 0;

      // Check position consistency
      const positionVariance = this.calculatePositionVariance(reports);
      if (positionVariance > this.thresholds.positionVariance) {
        byzantineScore += 0.4;
        agentReasons.push(
          `Position variance ${positionVariance.toFixed(3)} > threshold ${this.thresholds.positionVariance}`
        );
      }

      // Check phase consistency
      const phaseDeviation = this.calculatePhaseDeviation(reports);
      if (phaseDeviation > this.thresholds.phaseDeviation) {
        byzantineScore += 0.3;
        agentReasons.push(
          `Phase deviation ${phaseDeviation.toFixed(3)} rad > threshold ${this.thresholds.phaseDeviation.toFixed(3)}`
        );
      }

      // Check for null phases
      const hasNullPhase = reports.some(
        (r) => r.phase === null || r.phase === undefined || isNaN(r.phase)
      );
      if (hasNullPhase) {
        byzantineScore += 0.5;
        agentReasons.push('Phase-null intruder detected');
      }

      // Check boundary violations
      const hasBoundaryViolation = reports.some((r) => {
        const radius = Math.sqrt(
          r.position[0] ** 2 + r.position[1] ** 2 + r.position[2] ** 2
        );
        return radius > this.thresholds.boundaryThreshold;
      });
      if (hasBoundaryViolation) {
        byzantineScore += 0.2;
        agentReasons.push('Boundary violation detected');
      }

      // If score exceeds threshold, mark as Byzantine
      if (byzantineScore >= 0.5) {
        byzantineAgents.push(subjectId);
        confidences.set(subjectId, Math.min(1, byzantineScore));
        reasons.set(subjectId, agentReasons);
      }
    }

    return {
      byzantineAgents,
      confidences,
      reasons,
      timestamp: Date.now(),
    };
  }

  /**
   * Detect specific rogue agent conditions
   */
  public detectRogue(
    agentId: string,
    position: Position3D,
    phase: number | null | undefined,
    coherenceScore: number
  ): RogueDetectionResult | null {
    // 1. Phase-null intruder
    if (phase === null || phase === undefined || isNaN(phase)) {
      return {
        agentId,
        type: 'phase_null',
        severity: 'critical',
        details: 'Agent has null/invalid phase - possible intruder',
        detectedAt: Date.now(),
        action: 'quarantine',
      };
    }

    // 2. Phase out of bounds
    if (phase < 0 || phase >= 2 * Math.PI) {
      return {
        agentId,
        type: 'phase_null',
        severity: 'high',
        details: `Phase ${phase} out of valid range [0, 2π)`,
        detectedAt: Date.now(),
        action: 'quarantine',
      };
    }

    // 3. Boundary violation
    const radius = Math.sqrt(position[0] ** 2 + position[1] ** 2 + position[2] ** 2);
    if (radius > this.thresholds.boundaryThreshold) {
      return {
        agentId,
        type: 'boundary_violation',
        severity: 'high',
        details: `Position radius ${radius.toFixed(3)} exceeds boundary ${this.thresholds.boundaryThreshold}`,
        detectedAt: Date.now(),
        action: 'quarantine',
      };
    }

    // 4. Coherence drop
    if (coherenceScore < this.thresholds.coherenceDropThreshold) {
      return {
        agentId,
        type: 'coherence_drop',
        severity: 'medium',
        details: `Coherence ${coherenceScore.toFixed(3)} below threshold ${this.thresholds.coherenceDropThreshold}`,
        detectedAt: Date.now(),
        action: 'monitor',
      };
    }

    return null;
  }

  /**
   * Check for replay attack
   *
   * Validates that nonce hasn't been used before and timestamp is fresh.
   */
  public checkReplayAttack(
    nonce: string,
    timestamp: number,
    replayWindowMs: number = 60000
  ): { isReplay: boolean; reason?: string } {
    // Check timestamp freshness
    const age = Date.now() - timestamp;
    if (age > replayWindowMs) {
      return { isReplay: true, reason: 'Envelope expired (timestamp too old)' };
    }

    if (age < -5000) {
      // Allow 5s future skew
      return { isReplay: true, reason: 'Envelope from future (clock skew)' };
    }

    // Check nonce uniqueness
    if (this.nonceCache.has(nonce)) {
      return { isReplay: true, reason: 'Duplicate nonce (replay detected)' };
    }

    // Add to cache
    this.nonceCache.add(nonce);
    this.nonceTimes.set(nonce, Date.now());

    // Cleanup old nonces
    this.cleanupNonces(replayWindowMs);

    return { isReplay: false };
  }

  /**
   * Generate PoW challenge for Sybil prevention
   */
  public generatePoWChallenge(publicKey: string, difficulty: number = 5): PoWChallenge {
    return {
      publicKey,
      nonce: randomBytes(16).toString('hex'),
      difficulty,
      createdAt: Date.now(),
      expiresAt: Date.now() + 300000, // 5 minutes
    };
  }

  /**
   * Verify PoW solution
   *
   * Challenge: Find nonce such that SHA256(publicKey + challengeNonce + solutionNonce)
   * has `difficulty` leading zeros.
   */
  public verifyPoW(
    challenge: PoWChallenge,
    solutionNonce: string
  ): { valid: boolean; reason?: string } {
    // Check expiry
    if (Date.now() > challenge.expiresAt) {
      return { valid: false, reason: 'Challenge expired' };
    }

    // Compute hash
    const input = challenge.publicKey + challenge.nonce + solutionNonce;
    const hash = createHmac('sha256', 'scbe-pow').update(input).digest('hex');

    // Check leading zeros
    const leadingZeros = this.countLeadingZeros(hash);
    if (leadingZeros < challenge.difficulty) {
      return {
        valid: false,
        reason: `Insufficient PoW: got ${leadingZeros} zeros, need ${challenge.difficulty}`,
      };
    }

    return { valid: true };
  }

  /**
   * Quarantine an agent
   *
   * Pushes agent to boundary position and restricts actions.
   */
  public quarantine(agentId: string, reason: RogueType): QuarantineState {
    // Push to boundary (r = 0.95)
    const angle = Math.random() * 2 * Math.PI;
    const boundaryPosition: Position3D = [
      0.95 * Math.cos(angle),
      0.95 * Math.sin(angle),
      0.0,
    ];

    const state: QuarantineState = {
      agentId,
      reason,
      quarantinedAt: Date.now(),
      boundaryPosition,
      releaseConditions: this.getReleaseConditions(reason),
      canRelease: false,
    };

    this.quarantined.set(agentId, state);
    return state;
  }

  /**
   * Check if agent is quarantined
   */
  public isQuarantined(agentId: string): boolean {
    return this.quarantined.has(agentId);
  }

  /**
   * Get quarantine state
   */
  public getQuarantineState(agentId: string): QuarantineState | undefined {
    return this.quarantined.get(agentId);
  }

  /**
   * Release agent from quarantine
   */
  public release(agentId: string): boolean {
    const state = this.quarantined.get(agentId);
    if (!state || !state.canRelease) {
      return false;
    }
    this.quarantined.delete(agentId);
    return true;
  }

  /**
   * Mark quarantine as releasable (after conditions met)
   */
  public markReleasable(agentId: string): void {
    const state = this.quarantined.get(agentId);
    if (state) {
      state.canRelease = true;
    }
  }

  /**
   * Get all quarantined agents
   */
  public getQuarantinedAgents(): QuarantineState[] {
    return Array.from(this.quarantined.values());
  }

  // Private helpers

  private calculatePositionVariance(reports: PeerReport[]): number {
    if (reports.length < 2) return 0;

    // Calculate mean position
    const mean: Position3D = [0, 0, 0];
    for (const r of reports) {
      mean[0] += r.position[0];
      mean[1] += r.position[1];
      mean[2] += r.position[2];
    }
    mean[0] /= reports.length;
    mean[1] /= reports.length;
    mean[2] /= reports.length;

    // Calculate variance
    let variance = 0;
    for (const r of reports) {
      const dx = r.position[0] - mean[0];
      const dy = r.position[1] - mean[1];
      const dz = r.position[2] - mean[2];
      variance += dx * dx + dy * dy + dz * dz;
    }
    variance /= reports.length;

    return variance;
  }

  private calculatePhaseDeviation(reports: PeerReport[]): number {
    if (reports.length < 2) return 0;

    const phases = reports.map((r) => r.phase).filter((p) => p !== null && !isNaN(p));
    if (phases.length < 2) return Math.PI; // Max deviation if invalid phases

    // Use circular mean for phase
    let sinSum = 0;
    let cosSum = 0;
    for (const phase of phases) {
      sinSum += Math.sin(phase);
      cosSum += Math.cos(phase);
    }
    const meanPhase = Math.atan2(sinSum / phases.length, cosSum / phases.length);

    // Calculate mean absolute deviation
    let deviation = 0;
    for (const phase of phases) {
      let diff = Math.abs(phase - meanPhase);
      if (diff > Math.PI) diff = 2 * Math.PI - diff; // Wrap around
      deviation += diff;
    }

    return deviation / phases.length;
  }

  private countLeadingZeros(hex: string): number {
    let count = 0;
    for (const char of hex) {
      if (char === '0') {
        count += 4;
      } else {
        const nibble = parseInt(char, 16);
        if (nibble < 2) count += 3;
        else if (nibble < 4) count += 2;
        else if (nibble < 8) count += 1;
        break;
      }
    }
    return count;
  }

  private getReleaseConditions(reason: RogueType): string[] {
    switch (reason) {
      case 'phase_null':
        return ['Valid phase must be set', 'Pass 3 consecutive coherence checks'];
      case 'position_inconsistent':
        return ['Position must be consistent for 5 minutes', 'Coherence > 0.8'];
      case 'replay_attack':
        return ['New valid nonce required', 'Admin review required'];
      case 'sybil':
        return ['Pass PoW challenge', 'Admin verification'];
      case 'coherence_drop':
        return ['Coherence must exceed 0.7 for 10 minutes'];
      case 'boundary_violation':
        return ['Position must be within r < 0.8'];
      default:
        return ['Admin review required'];
    }
  }

  private cleanupOldReports(subjectId: string): void {
    const reports = this.reports.get(subjectId);
    if (!reports) return;

    const cutoff = Date.now() - 300000; // 5 minutes
    const filtered = reports.filter((r) => r.timestamp > cutoff);
    this.reports.set(subjectId, filtered);
  }

  private cleanupNonces(maxAgeMs: number): void {
    const cutoff = Date.now() - maxAgeMs;
    const toDelete: string[] = [];

    this.nonceTimes.forEach((time, nonce) => {
      if (time < cutoff) {
        toDelete.push(nonce);
      }
    });

    for (const nonce of toDelete) {
      this.nonceCache.delete(nonce);
      this.nonceTimes.delete(nonce);
    }
  }
}

/**
 * Calculate maximum Byzantine faults tolerable
 *
 * Formula: f = floor((n - 1) / 3)
 */
export function maxByzantineFaults(agentCount: number): number {
  return Math.floor((agentCount - 1) / 3);
}

/**
 * Calculate minimum agents needed to tolerate f faults
 *
 * Formula: n = 3f + 1
 */
export function minAgentsForFaultTolerance(faults: number): number {
  return 3 * faults + 1;
}

/**
 * Check if swarm has Byzantine fault tolerance
 */
export function hasByzantineTolerance(agentCount: number, requiredFaults: number): boolean {
  return agentCount >= minAgentsForFaultTolerance(requiredFaults);
}

/**
 * Global Byzantine detector instance
 */
let globalByzantineDetector: ByzantineDetector | null = null;

/**
 * Get global Byzantine detector
 */
export function getByzantineDetector(): ByzantineDetector {
  if (!globalByzantineDetector) {
    globalByzantineDetector = new ByzantineDetector();
  }
  return globalByzantineDetector;
}
