/**
 * BFT Consensus Unit Tests
 *
 * Validates the corrected Byzantine Fault-Tolerant consensus:
 * - Formula: n >= 3f + 1 (not 2f + 1)
 * - Quorum: 2f + 1
 *
 * @layer Layer 10, Layer 13
 */

import { describe, expect, it } from 'vitest';

import { BFTConsensus, type ConsensusVote } from '../../src/ai_brain/index';

describe('BFTConsensus', () => {
  describe('Construction', () => {
    it('should require 3f+1 nodes for f faults', () => {
      const bft = new BFTConsensus(1);
      expect(bft.requiredNodes).toBe(4); // 3*1 + 1
      expect(bft.quorumSize).toBe(3); // 2*1 + 1
    });

    it('should scale for f=2', () => {
      const bft = new BFTConsensus(2);
      expect(bft.requiredNodes).toBe(7); // 3*2 + 1
      expect(bft.quorumSize).toBe(5); // 2*2 + 1
    });

    it('should handle f=0 (no faults)', () => {
      const bft = new BFTConsensus(0);
      expect(bft.requiredNodes).toBe(1);
      expect(bft.quorumSize).toBe(1);
    });
  });

  describe('Evaluation', () => {
    it('should approve with unanimous votes', () => {
      const bft = new BFTConsensus(1);
      const votes: ConsensusVote[] = ['approve', 'approve', 'approve', 'approve'];
      const result = bft.evaluate(votes);
      expect(result.outcome).toBe('approve');
      expect(result.reached).toBe(true);
    });

    it('should reject with majority reject', () => {
      const bft = new BFTConsensus(1);
      const votes: ConsensusVote[] = ['reject', 'reject', 'reject', 'approve'];
      const result = bft.evaluate(votes);
      expect(result.outcome).toBe('reject');
    });

    it('should handle abstentions', () => {
      const bft = new BFTConsensus(1);
      const votes: ConsensusVote[] = ['approve', 'approve', 'approve', 'abstain'];
      const result = bft.evaluate(votes);
      expect(result.outcome).toBe('approve');
    });

    it('should not reach quorum with too few votes', () => {
      const bft = new BFTConsensus(1);
      const votes: ConsensusVote[] = ['approve', 'approve']; // only 2, need 4
      const result = bft.evaluate(votes);
      expect(result.reached).toBe(false);
    });
  });

  describe('isSufficient', () => {
    it('should return true when node count meets requirement', () => {
      const bft = new BFTConsensus(1);
      expect(bft.isSufficient(4)).toBe(true);
      expect(bft.isSufficient(5)).toBe(true);
    });

    it('should return false when node count is too low', () => {
      const bft = new BFTConsensus(1);
      expect(bft.isSufficient(3)).toBe(false);
    });
  });

  describe('maxTolerableFaults', () => {
    it('should compute max faults from node count', () => {
      // n >= 3f+1 => f <= (n-1)/3
      expect(BFTConsensus.maxTolerableFaults(4)).toBe(1);
      expect(BFTConsensus.maxTolerableFaults(7)).toBe(2);
      expect(BFTConsensus.maxTolerableFaults(10)).toBe(3);
    });

    it('should return 0 for single node', () => {
      expect(BFTConsensus.maxTolerableFaults(1)).toBe(0);
    });
  });
});
