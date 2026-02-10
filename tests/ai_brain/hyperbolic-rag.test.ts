/**
 * @file hyperbolic-rag.test.ts
 * @module tests/ai_brain/hyperbolic-rag
 * @layer Layer 5, Layer 12
 *
 * Tests for HyperbolicRAG: k-NN retrieval in the Poincare ball with d* cost gating.
 */

import { describe, it, expect } from 'vitest';
import {
  HyperbolicRAG,
  DEFAULT_RAG_CONFIG,
  type RAGCandidate,
  type RAGResult,
  type HyperbolicRAGConfig,
} from '../../src/ai_brain/hyperbolic-rag.js';
import { TONGUE_PHASES } from '../../src/geoseal.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

function makeCandidate(
  id: string,
  embedding: number[],
  tongue?: string,
  metadata?: Record<string, unknown>
): RAGCandidate {
  return { id, embedding, tongue, metadata };
}

function nearQuery(): number[] {
  return [0.1, 0.1, 0.1, 0.1];
}

function farQuery(): number[] {
  return [10.0, 10.0, 10.0, 10.0];
}

// ═══════════════════════════════════════════════════════════════
// Construction
// ═══════════════════════════════════════════════════════════════

describe('HyperbolicRAG', () => {
  describe('construction', () => {
    it('should use default config', () => {
      const rag = new HyperbolicRAG();
      const config = rag.getConfig();
      expect(config.maxK).toBe(20);
      expect(config.costThreshold).toBe(1.5);
      expect(config.minPhaseAlignment).toBe(0.0);
      expect(config.phaseWeight).toBe(2.0);
    });

    it('should accept partial config', () => {
      const rag = new HyperbolicRAG({ maxK: 5, costThreshold: 2.0 });
      const config = rag.getConfig();
      expect(config.maxK).toBe(5);
      expect(config.costThreshold).toBe(2.0);
      expect(config.phaseWeight).toBe(2.0); // default preserved
    });

    it('should support config update', () => {
      const rag = new HyperbolicRAG();
      rag.updateConfig({ costThreshold: 3.0 });
      expect(rag.getConfig().costThreshold).toBe(3.0);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Basic retrieval
  // ═══════════════════════════════════════════════════════════════

  describe('basic retrieval', () => {
    it('should return empty for no candidates', () => {
      const rag = new HyperbolicRAG();
      const results = rag.retrieve([0.1, 0.2], []);
      expect(results).toEqual([]);
    });

    it('should return nearby candidates sorted by distance', () => {
      const rag = new HyperbolicRAG({ costThreshold: 10.0 });
      const query = [0.1, 0.1, 0.1, 0.1];
      const candidates = [
        makeCandidate('far', [5.0, 5.0, 5.0, 5.0]),
        makeCandidate('near', [0.15, 0.12, 0.11, 0.09]),
        makeCandidate('mid', [1.0, 1.0, 1.0, 1.0]),
      ];

      const results = rag.retrieve(query, candidates);
      expect(results.length).toBeGreaterThan(0);
      // Should be sorted by distance ascending
      for (let i = 1; i < results.length; i++) {
        expect(results[i].distance).toBeGreaterThanOrEqual(results[i - 1].distance);
      }
    });

    it('should respect maxK limit', () => {
      const rag = new HyperbolicRAG({ maxK: 2, costThreshold: 100.0 });
      const query = [0.1, 0.1];
      const candidates = [
        makeCandidate('a', [0.1, 0.2]),
        makeCandidate('b', [0.2, 0.1]),
        makeCandidate('c', [0.3, 0.1]),
        makeCandidate('d', [0.4, 0.1]),
      ];

      const results = rag.retrieve(query, candidates);
      expect(results.length).toBeLessThanOrEqual(2);
    });

    it('should include metadata in results', () => {
      const rag = new HyperbolicRAG({ costThreshold: 100.0 });
      const query = [0.1, 0.1];
      const candidates = [
        makeCandidate('a', [0.12, 0.11], undefined, { source: 'doc1' }),
      ];

      const results = rag.retrieve(query, candidates);
      expect(results.length).toBe(1);
      expect(results[0].metadata).toEqual({ source: 'doc1' });
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // d* cost gating (Layer 12 wall)
  // ═══════════════════════════════════════════════════════════════

  describe('d* cost gating', () => {
    it('should gate candidates above cost threshold', () => {
      const rag = new HyperbolicRAG({ costThreshold: 0.5 });
      const query = [0.1, 0.1];
      // One near, one very far (will be projected to ball boundary)
      const candidates = [
        makeCandidate('near', [0.12, 0.11]),
        makeCandidate('far', [100.0, 100.0]),
      ];

      const results = rag.retrieve(query, candidates);
      // Far candidate should be gated
      const farResult = results.find((r) => r.id === 'far');
      expect(farResult).toBeUndefined(); // gated out of retrieve()
    });

    it('should show gated candidates in retrieveAll', () => {
      const rag = new HyperbolicRAG({ costThreshold: 0.5 });
      const query = [0.1, 0.1];
      const candidates = [
        makeCandidate('near', [0.12, 0.11]),
        makeCandidate('far', [100.0, 100.0]),
      ];

      const all = rag.retrieveAll(query, candidates);
      expect(all.length).toBe(2);
      const gated = all.filter((r) => r.gated);
      expect(gated.length).toBeGreaterThanOrEqual(1);
    });

    it('should set trust_score to 0 for gated candidates', () => {
      const rag = new HyperbolicRAG({ costThreshold: 0.5 });
      const query = [0.1, 0.1];
      const candidates = [makeCandidate('far', [100.0, 100.0])];

      const all = rag.retrieveAll(query, candidates);
      expect(all[0].gated).toBe(true);
      expect(all[0].trust_score).toBe(0);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Phase alignment (tongue discipline)
  // ═══════════════════════════════════════════════════════════════

  describe('phase alignment', () => {
    it('should give high phase_score for same tongue', () => {
      const rag = new HyperbolicRAG({ costThreshold: 100.0 });
      const query = [0.1, 0.1];
      const candidates = [makeCandidate('same', [0.12, 0.11], 'KO')];

      const results = rag.retrieve(query, candidates, 'KO');
      expect(results[0].phase_score).toBe(1.0);
    });

    it('should give low phase_score for opposite tongue', () => {
      const rag = new HyperbolicRAG({ costThreshold: 100.0 });
      const query = [0.1, 0.1];
      const candidates = [makeCandidate('opp', [0.12, 0.11], 'CA')]; // CA = pi

      const results = rag.retrieve(query, candidates, 'KO'); // KO = 0
      expect(results[0].phase_score).toBeLessThan(0.5);
    });

    it('should give phase_score 0 for null tongue candidate', () => {
      const rag = new HyperbolicRAG({ costThreshold: 100.0 });
      const query = [0.1, 0.1];
      const candidates = [makeCandidate('none', [0.12, 0.11])]; // no tongue

      const results = rag.retrieve(query, candidates, 'KO');
      expect(results[0].phase_score).toBe(0.0);
    });

    it('should gate by minPhaseAlignment', () => {
      const rag = new HyperbolicRAG({ costThreshold: 100.0, minPhaseAlignment: 0.9 });
      const query = [0.1, 0.1];
      const candidates = [
        makeCandidate('same', [0.12, 0.11], 'KO'),
        makeCandidate('diff', [0.12, 0.11], 'CA'),
      ];

      const results = rag.retrieve(query, candidates, 'KO');
      // Only KO should pass the 0.9 phase threshold
      expect(results.length).toBe(1);
      expect(results[0].id).toBe('same');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Trust scoring
  // ═══════════════════════════════════════════════════════════════

  describe('trust scoring', () => {
    it('should produce positive trust for ungated candidates', () => {
      const rag = new HyperbolicRAG({ costThreshold: 100.0 });
      const query = [0.1, 0.1];
      const candidates = [makeCandidate('a', [0.12, 0.11], 'KO')];

      const results = rag.retrieve(query, candidates, 'KO');
      expect(results[0].trust_score).toBeGreaterThan(0);
    });

    it('should give higher trust to closer candidates', () => {
      const rag = new HyperbolicRAG({ costThreshold: 100.0 });
      const query = [0.1, 0.1];
      const candidates = [
        makeCandidate('near', [0.12, 0.11], 'KO'),
        makeCandidate('far', [2.0, 2.0], 'KO'),
      ];

      const results = rag.retrieve(query, candidates, 'KO');
      const nearResult = results.find((r) => r.id === 'near')!;
      const farResult = results.find((r) => r.id === 'far')!;
      expect(nearResult.trust_score).toBeGreaterThan(farResult.trust_score);
    });

    it('should penalize trust for phase mismatch', () => {
      const rag = new HyperbolicRAG({ costThreshold: 100.0 });
      const query = [0.1, 0.1];
      // Same position, different tongues
      const candidates = [
        makeCandidate('same_tongue', [0.12, 0.11], 'KO'),
        makeCandidate('diff_tongue', [0.12, 0.11], 'CA'),
      ];

      const results = rag.retrieve(query, candidates, 'KO');
      const same = results.find((r) => r.id === 'same_tongue')!;
      const diff = results.find((r) => r.id === 'diff_tongue')!;
      expect(same.trust_score).toBeGreaterThan(diff.trust_score);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // retrieveAll diagnostics
  // ═══════════════════════════════════════════════════════════════

  describe('retrieveAll', () => {
    it('should include all candidates regardless of gating', () => {
      const rag = new HyperbolicRAG({ costThreshold: 0.5, minPhaseAlignment: 0.9 });
      const query = [0.1, 0.1];
      const candidates = [
        makeCandidate('near_ko', [0.12, 0.11], 'KO'),
        makeCandidate('near_ca', [0.12, 0.11], 'CA'),
        makeCandidate('far', [100.0, 100.0], 'KO'),
      ];

      const all = rag.retrieveAll(query, candidates, 'KO');
      expect(all.length).toBe(3);
    });

    it('should sort all results by distance', () => {
      const rag = new HyperbolicRAG();
      const query = [0.1, 0.1];
      const candidates = [
        makeCandidate('a', [5.0, 5.0]),
        makeCandidate('b', [0.15, 0.12]),
        makeCandidate('c', [1.0, 1.0]),
      ];

      const all = rag.retrieveAll(query, candidates);
      for (let i = 1; i < all.length; i++) {
        expect(all[i].distance).toBeGreaterThanOrEqual(all[i - 1].distance);
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // All Sacred Tongues
  // ═══════════════════════════════════════════════════════════════

  describe('Sacred Tongues coverage', () => {
    it('should handle all 6 tongues', () => {
      const tongues = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
      const rag = new HyperbolicRAG({ costThreshold: 100.0 });
      const query = [0.1, 0.1];

      for (const tongue of tongues) {
        const candidates = [makeCandidate(`c_${tongue}`, [0.12, 0.11], tongue)];
        const results = rag.retrieve(query, candidates, tongue);
        expect(results.length).toBe(1);
        expect(results[0].phase_score).toBe(1.0);
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Edge cases
  // ═══════════════════════════════════════════════════════════════

  describe('edge cases', () => {
    it('should handle zero query', () => {
      const rag = new HyperbolicRAG({ costThreshold: 100.0 });
      const results = rag.retrieve([0, 0], [makeCandidate('a', [0.1, 0.1])]);
      expect(results.length).toBe(1);
    });

    it('should handle single-dimension', () => {
      const rag = new HyperbolicRAG({ costThreshold: 100.0 });
      const results = rag.retrieve([0.1], [makeCandidate('a', [0.2])]);
      expect(results.length).toBe(1);
    });

    it('should handle high-dimensional embeddings', () => {
      const rag = new HyperbolicRAG({ costThreshold: 100.0 });
      const dim = 64;
      const query = new Array(dim).fill(0.01);
      const candidates = [makeCandidate('a', new Array(dim).fill(0.02))];
      const results = rag.retrieve(query, candidates);
      expect(results.length).toBe(1);
    });

    it('should handle no tongue on query', () => {
      const rag = new HyperbolicRAG({ costThreshold: 100.0 });
      const query = [0.1, 0.1];
      const candidates = [makeCandidate('a', [0.12, 0.11], 'KO')];

      // No queryTongue -> phaseDeviation(null, phase) = 1.0 -> phase_score = 0
      const results = rag.retrieve(query, candidates);
      expect(results[0].phase_score).toBe(0.0);
    });
  });
});
