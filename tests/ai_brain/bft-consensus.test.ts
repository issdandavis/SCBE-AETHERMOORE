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
  // ═══════════════════════════════════════════════════════════════
  // Construction & Formula Validation
  // ═══════════════════════════════════════════════════════════════

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

    it('should scale for f=3', () => {
      const bft = new BFTConsensus(3);
      expect(bft.requiredNodes).toBe(10); // 3*3 + 1
      expect(bft.quorumSize).toBe(7); // 2*3 + 1
    });

    it('should scale for large f', () => {
      const bft = new BFTConsensus(10);
      expect(bft.requiredNodes).toBe(31); // 3*10 + 1
      expect(bft.quorumSize).toBe(21); // 2*10 + 1
    });

    it('should reject negative faults', () => {
      expect(() => new BFTConsensus(-1)).toThrow(RangeError);
    });

    it('should reject non-integer faults', () => {
      expect(() => new BFTConsensus(1.5)).toThrow(RangeError);
    });

    it('should use 3f+1 not 2f+1 (corrected formula)', () => {
      // This is the critical correctness test:
      // The old incorrect formula was n >= 2f + 1
      // The correct BFT formula is n >= 3f + 1
      const bft = new BFTConsensus(1);
      expect(bft.requiredNodes).toBe(4); // 3f+1, not 2f+1=3
      expect(bft.requiredNodes).not.toBe(3); // Would be wrong formula
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Evaluation
  // ═══════════════════════════════════════════════════════════════

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

    it('should not reach consensus with split votes below quorum', () => {
      const bft = new BFTConsensus(1);
      // 2 approve, 2 reject — neither reaches quorum of 3
      const votes: ConsensusVote[] = ['approve', 'approve', 'reject', 'reject'];
      const result = bft.evaluate(votes);
      expect(result.reached).toBe(false);
    });

    it('should reach consensus with exactly quorum votes', () => {
      const bft = new BFTConsensus(1);
      // Quorum = 3 approves, 1 reject
      const votes: ConsensusVote[] = ['approve', 'approve', 'approve', 'reject'];
      const result = bft.evaluate(votes);
      expect(result.reached).toBe(true);
      expect(result.outcome).toBe('approve');
    });

    it('should include vote counts', () => {
      const bft = new BFTConsensus(1);
      const votes: ConsensusVote[] = ['approve', 'reject', 'approve', 'abstain'];
      const result = bft.evaluate(votes);
      expect(result.voteCounts.approve).toBe(2);
      expect(result.voteCounts.reject).toBe(1);
      expect(result.voteCounts.abstain).toBe(1);
    });

    it('should report total nodes', () => {
      const bft = new BFTConsensus(1);
      const result = bft.evaluate(['approve', 'approve', 'approve', 'approve']);
      expect(result.totalNodes).toBe(4);
    });

    it('should report valid configuration', () => {
      const bft = new BFTConsensus(1);
      const valid = bft.evaluate(['approve', 'approve', 'approve', 'approve']);
      expect(valid.validConfiguration).toBe(true);
      const invalid = bft.evaluate(['approve', 'approve']);
      expect(invalid.validConfiguration).toBe(false);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Byzantine Scenarios
  // ═══════════════════════════════════════════════════════════════

  describe('Byzantine fault scenarios', () => {
    it('tolerates 1 Byzantine fault with 4 nodes', () => {
      const bft = new BFTConsensus(1);
      // 3 honest approve, 1 Byzantine rejects
      const votes: ConsensusVote[] = ['approve', 'approve', 'approve', 'reject'];
      const result = bft.evaluate(votes);
      expect(result.reached).toBe(true);
      expect(result.outcome).toBe('approve');
    });

    it('tolerates 2 Byzantine faults with 7 nodes', () => {
      const bft = new BFTConsensus(2);
      // 5 honest approve, 2 Byzantine reject
      const votes: ConsensusVote[] = [
        'approve', 'approve', 'approve', 'approve', 'approve',
        'reject', 'reject',
      ];
      const result = bft.evaluate(votes);
      expect(result.reached).toBe(true);
      expect(result.outcome).toBe('approve');
    });

    it('fails when Byzantine nodes = f+1 (exceeds tolerance)', () => {
      const bft = new BFTConsensus(1);
      // 2 honest approve, 2 Byzantine reject — split, no quorum
      const votes: ConsensusVote[] = ['approve', 'approve', 'reject', 'reject'];
      const result = bft.evaluate(votes);
      expect(result.reached).toBe(false);
    });

    it('all abstaining prevents consensus', () => {
      const bft = new BFTConsensus(1);
      const votes: ConsensusVote[] = ['abstain', 'abstain', 'abstain', 'abstain'];
      const result = bft.evaluate(votes);
      expect(result.reached).toBe(false);
    });

    it('all rejecting reaches reject consensus', () => {
      const bft = new BFTConsensus(1);
      const votes: ConsensusVote[] = ['reject', 'reject', 'reject', 'reject'];
      const result = bft.evaluate(votes);
      expect(result.reached).toBe(true);
      expect(result.outcome).toBe('reject');
    });

    it('empty vote array does not reach consensus', () => {
      const bft = new BFTConsensus(1);
      const result = bft.evaluate([]);
      expect(result.reached).toBe(false);
      expect(result.validConfiguration).toBe(false);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // isSufficient
  // ═══════════════════════════════════════════════════════════════

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

    it('exact boundary: 3f+1 is sufficient, 3f is not', () => {
      const bft = new BFTConsensus(2);
      expect(bft.isSufficient(7)).toBe(true);  // 3*2+1 = 7
      expect(bft.isSufficient(6)).toBe(false); // 3*2 = 6
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // maxTolerableFaults
  // ═══════════════════════════════════════════════════════════════

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

    it('should floor for non-exact multiples', () => {
      // 5 nodes: (5-1)/3 = 1.33 → floor = 1
      expect(BFTConsensus.maxTolerableFaults(5)).toBe(1);
      // 6 nodes: (6-1)/3 = 1.67 → floor = 1
      expect(BFTConsensus.maxTolerableFaults(6)).toBe(1);
      // 8 nodes: (8-1)/3 = 2.33 → floor = 2
      expect(BFTConsensus.maxTolerableFaults(8)).toBe(2);
    });

    it('round-trip: construct with f, verify sufficient', () => {
      for (let f = 0; f <= 5; f++) {
        const bft = new BFTConsensus(f);
        const maxF = BFTConsensus.maxTolerableFaults(bft.requiredNodes);
        expect(maxF).toBeGreaterThanOrEqual(f);
      }
    });
  });
});
