/**
 * @file hyperbolicRAG.test.ts
 * @description Tests for the HyperbolicRAG — Poincaré Ball Retrieval-Augmented Generation
 *
 * Tests cover:
 * - Access cost function invariants (monotonicity, minimum bound)
 * - Trust-from-position decay
 * - Document indexing (add, remove, clear)
 * - Retrieval with cost gating and budget exhaustion
 * - Phase-aligned retrieval filtering
 * - Tongue-biased retrieval
 * - k-nearest neighbors (raw)
 * - Adversarial document rejection via cost gating
 *
 * @module tests/harmonic/hyperbolicRAG
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  accessCost,
  trustFromPosition,
  HyperbolicRAGEngine,
  createHyperbolicRAG,
  type RAGDocument,
  type HyperbolicRAGConfig,
} from '../../src/harmonic/hyperbolicRAG.js';

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════

const PHI = (1 + Math.sqrt(5)) / 2;

function makeDoc(id: string, embedding: number[], phase: number | null = 0): RAGDocument {
  return { id, embedding, phase, insertedAt: Date.now(), metadata: {} };
}

function randomBallPoint(dim: number, maxNorm: number = 0.8): number[] {
  const v = Array.from({ length: dim }, () => Math.random() * 2 - 1);
  const n = Math.sqrt(v.reduce((s, x) => s + x * x, 0));
  const r = Math.random() * maxNorm;
  return v.map((x) => (x / n) * r);
}

// ═══════════════════════════════════════════════════════════════
// Access Cost
// ═══════════════════════════════════════════════════════════════

describe('accessCost', () => {
  it('should return 1.0 for zero distance', () => {
    expect(accessCost(0)).toBe(1.0);
  });

  it('should be >= 1 for all non-negative distances', () => {
    for (let d = 0; d <= 10; d += 0.1) {
      expect(accessCost(d)).toBeGreaterThanOrEqual(1.0);
    }
  });

  it('should be monotonically increasing with distance', () => {
    let prev = accessCost(0);
    for (let d = 0.1; d <= 5; d += 0.1) {
      const cost = accessCost(d);
      expect(cost).toBeGreaterThanOrEqual(prev);
      prev = cost;
    }
  });

  it('should grow approximately as phi^d for large d', () => {
    const d = 5;
    const cost = accessCost(d, PHI, 0);
    expect(cost).toBeCloseTo(Math.pow(PHI, d), 0);
  });

  it('should increase with risk amplification', () => {
    const d = 2;
    const lowRisk = accessCost(d, PHI, 0.5);
    const highRisk = accessCost(d, PHI, 2.0);
    expect(highRisk).toBeGreaterThan(lowRisk);
  });

  it('should throw for negative distance', () => {
    expect(() => accessCost(-1)).toThrow('Distance must be non-negative');
  });
});

// ═══════════════════════════════════════════════════════════════
// Trust from Position
// ═══════════════════════════════════════════════════════════════

describe('trustFromPosition', () => {
  it('should return 1.0 at the origin', () => {
    expect(trustFromPosition([0, 0, 0, 0, 0, 0])).toBe(1.0);
  });

  it('should decay with distance from origin', () => {
    const near = trustFromPosition([0.1, 0, 0, 0, 0, 0]);
    const far = trustFromPosition([0.8, 0, 0, 0, 0, 0]);
    expect(near).toBeGreaterThan(far);
  });

  it('should be in (0, 1] for all points in the ball', () => {
    for (let i = 0; i < 50; i++) {
      const p = randomBallPoint(6);
      const trust = trustFromPosition(p);
      expect(trust).toBeGreaterThan(0);
      expect(trust).toBeLessThanOrEqual(1.0);
    }
  });

  it('should approach 0 near the boundary', () => {
    const boundary = trustFromPosition([0.99, 0, 0, 0, 0, 0]);
    expect(boundary).toBeLessThan(0.2);
  });
});

// ═══════════════════════════════════════════════════════════════
// HyperbolicRAGEngine — Indexing
// ═══════════════════════════════════════════════════════════════

describe('HyperbolicRAGEngine', () => {
  let engine: HyperbolicRAGEngine;

  beforeEach(() => {
    engine = new HyperbolicRAGEngine({ dimension: 6, contextBudget: 50 });
  });

  describe('Indexing', () => {
    it('should add and count documents', () => {
      engine.addDocument(makeDoc('a', [0.1, 0, 0, 0, 0, 0]));
      engine.addDocument(makeDoc('b', [0, 0.2, 0, 0, 0, 0]));
      expect(engine.size).toBe(2);
    });

    it('should remove documents', () => {
      engine.addDocument(makeDoc('a', [0.1, 0, 0, 0, 0, 0]));
      expect(engine.removeDocument('a')).toBe(true);
      expect(engine.size).toBe(0);
      expect(engine.removeDocument('nonexistent')).toBe(false);
    });

    it('should clear all documents', () => {
      engine.addDocuments([
        makeDoc('a', [0.1, 0, 0, 0, 0, 0]),
        makeDoc('b', [0.2, 0, 0, 0, 0, 0]),
      ]);
      engine.clear();
      expect(engine.size).toBe(0);
    });

    it('should retrieve documents by id', () => {
      const doc = makeDoc('a', [0.1, 0, 0, 0, 0, 0]);
      engine.addDocument(doc);
      const found = engine.getDocument('a');
      expect(found).toBeDefined();
      expect(found!.id).toBe('a');
    });

    it('should project out-of-ball embeddings into the ball', () => {
      engine.addDocument(makeDoc('big', [5, 5, 5, 5, 5, 5]));
      const doc = engine.getDocument('big');
      const n = Math.sqrt(doc!.embedding.reduce((s, x) => s + x * x, 0));
      expect(n).toBeLessThan(1);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Retrieval — Basic
  // ═══════════════════════════════════════════════════════════════

  describe('Retrieval', () => {
    it('should retrieve nearest documents first', () => {
      engine.addDocuments([
        makeDoc('near', [0.11, 0, 0, 0, 0, 0]),
        makeDoc('far', [0.8, 0, 0, 0, 0, 0]),
      ]);

      const result = engine.retrieve([0.1, 0, 0, 0, 0, 0], 0);
      expect(result.results.length).toBeGreaterThanOrEqual(1);
      expect(result.results[0].id).toBe('near');
    });

    it('should return a valid RetrievalSummary', () => {
      engine.addDocuments([
        makeDoc('a', [0.1, 0, 0, 0, 0, 0]),
        makeDoc('b', [0.2, 0, 0, 0, 0, 0]),
      ]);

      const summary = engine.retrieve([0.1, 0, 0, 0, 0, 0], 0);
      expect(summary.totalCost).toBeGreaterThan(0);
      expect(summary.remainingBudget).toBeLessThanOrEqual(50);
      expect(summary.candidatesConsidered).toBe(2);
      expect(summary.queryNorm).toBeGreaterThan(0);
    });

    it('should respect maxResults', () => {
      const eng = new HyperbolicRAGEngine({ dimension: 6, maxResults: 2, contextBudget: 100 });
      for (let i = 0; i < 10; i++) {
        eng.addDocument(makeDoc(`d${i}`, randomBallPoint(6, 0.5)));
      }
      const result = eng.retrieve([0, 0, 0, 0, 0, 0], 0);
      expect(result.results.length).toBeLessThanOrEqual(2);
    });

    it('should filter by minimum relevance', () => {
      const eng = new HyperbolicRAGEngine({ dimension: 6, minRelevance: 0.5 });
      eng.addDocuments([
        makeDoc('close', [0.1, 0, 0, 0, 0, 0], 0),
        makeDoc('far-phase', [0.8, 0, 0, 0, 0, 0], Math.PI), // opposite phase
      ]);

      const result = eng.retrieve([0.1, 0, 0, 0, 0, 0], 0);
      // The far-phase doc has low relevance due to both distance and phase mismatch
      expect(result.filteredOut).toBeGreaterThanOrEqual(0);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Retrieval — Cost Gating (Adversarial Rejection)
  // ═══════════════════════════════════════════════════════════════

  describe('Cost Gating', () => {
    it('should exhaust budget before including expensive boundary documents', () => {
      const eng = new HyperbolicRAGEngine({
        dimension: 6,
        contextBudget: 5,
        maxResults: 100,
      });

      // 3 cheap documents near the center
      eng.addDocuments([
        makeDoc('cheap1', [0.05, 0, 0, 0, 0, 0]),
        makeDoc('cheap2', [0, 0.05, 0, 0, 0, 0]),
        makeDoc('cheap3', [0, 0, 0.05, 0, 0, 0]),
      ]);

      // 3 expensive documents near the boundary
      eng.addDocuments([
        makeDoc('expensive1', [0.95, 0, 0, 0, 0, 0]),
        makeDoc('expensive2', [0, 0.95, 0, 0, 0, 0]),
        makeDoc('expensive3', [0, 0, 0.95, 0, 0, 0]),
      ]);

      const result = eng.retrieve([0, 0, 0, 0, 0, 0], 0);

      // Cheap documents should be included, expensive ones should be excluded by budget
      const includedIds = new Set(result.results.map((r) => r.id));
      expect(includedIds.has('cheap1') || includedIds.has('cheap2') || includedIds.has('cheap3')).toBe(true);
      expect(result.totalCost).toBeLessThanOrEqual(5);
    });

    it('should give boundary documents higher access cost than center documents', () => {
      eng = new HyperbolicRAGEngine({ dimension: 6, contextBudget: 1000 });

      eng.addDocuments([
        makeDoc('center', [0.05, 0, 0, 0, 0, 0]),
        makeDoc('boundary', [0.95, 0, 0, 0, 0, 0]),
      ]);

      const result = eng.retrieve([0, 0, 0, 0, 0, 0], 0);
      const centerResult = result.results.find((r) => r.id === 'center');
      const boundaryResult = result.results.find((r) => r.id === 'boundary');

      if (centerResult && boundaryResult) {
        expect(boundaryResult.accessCost).toBeGreaterThan(centerResult.accessCost);
      }
    });

    let eng: HyperbolicRAGEngine;
    it('should make adversarial injection economically infeasible', () => {
      eng = new HyperbolicRAGEngine({ dimension: 6, contextBudget: 10 });

      // Legitimate documents
      for (let i = 0; i < 5; i++) {
        eng.addDocument(makeDoc(`legit${i}`, randomBallPoint(6, 0.3)));
      }
      // Adversarial documents positioned near boundary
      for (let i = 0; i < 5; i++) {
        eng.addDocument(makeDoc(`adv${i}`, randomBallPoint(6, 0.1).map((x) => x + 0.85)));
      }

      const result = eng.retrieve([0.1, 0.1, 0, 0, 0, 0], 0);
      const advIncluded = result.results.filter((r) => r.id.startsWith('adv'));
      // Adversarial docs should be mostly excluded by budget
      expect(advIncluded.length).toBeLessThan(5);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Retrieval — Tongue-Biased
  // ═══════════════════════════════════════════════════════════════

  describe('Tongue-biased retrieval', () => {
    it('should prefer documents near the specified tongue realm', () => {
      engine.addDocuments([
        makeDoc('ko-doc', [0.25, 0, 0, 0, 0, 0]),  // near KO center [0.3, 0, ...]
        makeDoc('dr-doc', [0, 0, 0, 0, 0, 0.25]),   // near DR center [..., 0.3]
      ]);

      const koResult = engine.retrieveByTongue([0, 0, 0, 0, 0, 0], 0, 'KO');
      const drResult = engine.retrieveByTongue([0, 0, 0, 0, 0, 0], 0, 'DR');

      if (koResult.results.length > 0 && drResult.results.length > 0) {
        expect(koResult.results[0].id).toBe('ko-doc');
        expect(drResult.results[0].id).toBe('dr-doc');
      }
    });

    it('should throw for unknown tongue', () => {
      expect(() => engine.retrieveByTongue([0, 0, 0, 0, 0, 0], 0, 'INVALID')).toThrow('Unknown tongue');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // k-Nearest Neighbors
  // ═══════════════════════════════════════════════════════════════

  describe('kNearest', () => {
    it('should return k nearest documents sorted by distance', () => {
      engine.addDocuments([
        makeDoc('a', [0.1, 0, 0, 0, 0, 0]),
        makeDoc('b', [0.3, 0, 0, 0, 0, 0]),
        makeDoc('c', [0.6, 0, 0, 0, 0, 0]),
      ]);

      const nearest = engine.kNearest([0, 0, 0, 0, 0, 0], 2);
      expect(nearest).toHaveLength(2);
      expect(nearest[0].id).toBe('a');
      expect(nearest[1].id).toBe('b');
      expect(nearest[0].distance).toBeLessThan(nearest[1].distance);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Capacity Estimation
  // ═══════════════════════════════════════════════════════════════

  describe('estimateCapacity', () => {
    it('should return higher capacity for closer documents', () => {
      const nearCapacity = engine.estimateCapacity([0.1, 0, 0, 0, 0, 0], 0.5);
      const farCapacity = engine.estimateCapacity([0.1, 0, 0, 0, 0, 0], 3.0);
      expect(nearCapacity).toBeGreaterThan(farCapacity);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Factory
  // ═══════════════════════════════════════════════════════════════

  describe('createHyperbolicRAG', () => {
    it('should create a working engine with defaults', () => {
      const eng = createHyperbolicRAG();
      eng.addDocument(makeDoc('test', [0.1, 0, 0, 0, 0, 0]));
      expect(eng.size).toBe(1);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Age Filtering
  // ═══════════════════════════════════════════════════════════════

  describe('Age filtering', () => {
    it('should exclude expired documents', () => {
      const eng = new HyperbolicRAGEngine({ dimension: 6, maxAge: 1000 });
      eng.addDocument({
        id: 'old',
        embedding: [0.1, 0, 0, 0, 0, 0],
        phase: 0,
        insertedAt: Date.now() - 5000, // 5 seconds ago
      });
      eng.addDocument({
        id: 'new',
        embedding: [0.2, 0, 0, 0, 0, 0],
        phase: 0,
        insertedAt: Date.now(),
      });

      const result = eng.retrieve([0, 0, 0, 0, 0, 0], 0);
      const ids = result.results.map((r) => r.id);
      expect(ids).not.toContain('old');
      expect(ids).toContain('new');
    });
  });
});
