/**
 * @file bft-consensus.ts
 * @module ai_brain/bft-consensus
 * @layer Layer 10, Layer 13
 * @component Byzantine Fault-Tolerant Consensus
 * @version 1.1.0
 * @since 2026-02-07
 *
 * Corrected BFT consensus implementation for swarm governance.
 *
 * Key Fix: Uses the correct formula n >= 3f + 1 (not 2f + 1).
 * For f = 1 fault: need n >= 4 nodes, quorum = 2f + 1 = 3.
 *
 * This is majority voting with Byzantine fault tolerance guarantees,
 * NOT full PBFT (reframed per security review).
 */

/**
 * BFT consensus vote
 */
export type ConsensusVote = 'approve' | 'reject' | 'abstain';

/**
 * Consensus result
 */
export interface ConsensusResult {
  /** Whether consensus was reached */
  reached: boolean;
  /** The consensus outcome (if reached) */
  outcome?: ConsensusVote;
  /** Total participating nodes */
  totalNodes: number;
  /** Maximum tolerated faults */
  maxFaults: number;
  /** Required minimum nodes (3f + 1) */
  requiredNodes: number;
  /** Required quorum size (2f + 1) */
  quorumSize: number;
  /** Actual vote counts */
  voteCounts: Record<ConsensusVote, number>;
  /** Whether the configuration is valid (enough nodes) */
  validConfiguration: boolean;
}

/**
 * Byzantine Fault-Tolerant Consensus Engine
 *
 * Implements majority voting with Byzantine fault tolerance.
 * Corrected formula: requires n >= 3f + 1 total nodes to tolerate f faults.
 *
 * For f = 1: n >= 4 nodes, quorum = 3
 * For f = 2: n >= 7 nodes, quorum = 5
 * For f = 3: n >= 10 nodes, quorum = 7
 *
 * Note: This provides BFT guarantees for simple majority decisions.
 * It is NOT full PBFT (Practical Byzantine Fault Tolerance), which
 * requires additional message rounds and leader election. The distinction
 * matters for security claims.
 */
export class BFTConsensus {
  /** Maximum faults to tolerate */
  readonly maxFaults: number;
  /** Minimum total nodes required: 3f + 1 */
  readonly requiredNodes: number;
  /** Quorum size: 2f + 1 */
  readonly quorumSize: number;

  /**
   * @param maxFaults - Maximum Byzantine faults to tolerate (default: 1)
   */
  constructor(maxFaults: number = 1) {
    if (maxFaults < 0 || !Number.isInteger(maxFaults)) {
      throw new RangeError('maxFaults must be a non-negative integer');
    }
    this.maxFaults = maxFaults;
    this.requiredNodes = 3 * maxFaults + 1;
    this.quorumSize = 2 * maxFaults + 1;
  }

  /**
   * Run consensus on a set of votes.
   *
   * @param votes - Array of votes from participating nodes
   * @returns Consensus result
   */
  evaluate(votes: ConsensusVote[]): ConsensusResult {
    const totalNodes = votes.length;
    const validConfiguration = totalNodes >= this.requiredNodes;

    // Count votes
    const voteCounts: Record<ConsensusVote, number> = {
      approve: 0,
      reject: 0,
      abstain: 0,
    };

    for (const vote of votes) {
      voteCounts[vote]++;
    }

    // If not enough nodes, consensus cannot be reached
    if (!validConfiguration) {
      return {
        reached: false,
        totalNodes,
        maxFaults: this.maxFaults,
        requiredNodes: this.requiredNodes,
        quorumSize: this.quorumSize,
        voteCounts,
        validConfiguration,
      };
    }

    // Check if any non-abstain vote meets quorum
    let reached = false;
    let outcome: ConsensusVote | undefined;

    if (voteCounts.approve >= this.quorumSize) {
      reached = true;
      outcome = 'approve';
    } else if (voteCounts.reject >= this.quorumSize) {
      reached = true;
      outcome = 'reject';
    }

    return {
      reached,
      outcome,
      totalNodes,
      maxFaults: this.maxFaults,
      requiredNodes: this.requiredNodes,
      quorumSize: this.quorumSize,
      voteCounts,
      validConfiguration,
    };
  }

  /**
   * Check if a given number of nodes is sufficient for this BFT level.
   */
  isSufficient(nodeCount: number): boolean {
    return nodeCount >= this.requiredNodes;
  }

  /**
   * Compute the maximum faults tolerable for a given node count.
   * f_max = floor((n - 1) / 3)
   */
  static maxTolerableFaults(nodeCount: number): number {
    return Math.floor((nodeCount - 1) / 3);
  }
}
