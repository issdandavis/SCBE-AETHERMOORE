/**
 * @file triDirectionalPlanner.unit.test.ts
 * @tier L2-unit
 * @axiom 3 (Causality), 4 (Symmetry)
 * @category unit
 *
 * Unit tests for tri-directional Hamiltonian path planner.
 */

import { describe, it, expect } from 'vitest';
import {
  CoreFunctionGraph,
  planTrace,
  planTriDirectional,
  STANDARD_CHECKPOINTS,
  DIRECTION_WEIGHTS,
  type TraceOutput,
  type TriDirectionalResult,
} from '../../src/harmonic/triDirectionalPlanner.js';
import type { Vector6D } from '../../src/harmonic/constants.js';

// ═══════════════════════════════════════════════════════════════
// CoreFunctionGraph Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: CoreFunctionGraph', () => {
  it('should initialize with standard checkpoints', () => {
    const graph = new CoreFunctionGraph();
    const ids = graph.getIds();
    expect(ids.length).toBe(STANDARD_CHECKPOINTS.length);
  });

  it('should have the correct required checkpoints', () => {
    const graph = new CoreFunctionGraph();
    const required = graph.getRequired();
    // INTENT, POLICY, MEMORY_FETCH, PLAN, COST_WALL, EXECUTE are required
    expect(required.length).toBe(6);
    expect(required).not.toContain(5); // QUORUM is optional
  });

  it('should build default edges as a chain', () => {
    const graph = new CoreFunctionGraph();
    graph.buildDefaultEdges();
    // 0 → 1 should be an edge
    expect(graph.successors(0)).toContain(1);
    // Last checkpoint should have no successors
    expect(graph.successors(6)).toHaveLength(0);
  });

  it('should allow skipping non-required checkpoints', () => {
    const graph = new CoreFunctionGraph();
    graph.buildDefaultEdges();
    // Checkpoint 5 (QUORUM) is non-required, so 4 → 6 skip edge should exist
    expect(graph.successors(4)).toContain(6);
  });

  it('should support custom checkpoints', () => {
    const custom = [
      { id: 0, name: 'A', required: true },
      { id: 1, name: 'B', required: false },
      { id: 2, name: 'C', required: true },
    ];
    const graph = new CoreFunctionGraph(custom);
    expect(graph.getIds()).toHaveLength(3);
    expect(graph.getRequired()).toEqual([0, 2]);
  });
});

// ═══════════════════════════════════════════════════════════════
// Single Trace Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: planTrace', () => {
  function makeGraph(): CoreFunctionGraph {
    const g = new CoreFunctionGraph();
    g.buildDefaultEdges();
    return g;
  }

  it('should produce a VALID trace for safe state + low d*', () => {
    const graph = makeGraph();
    const state: Vector6D = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1];
    const trace = planTrace(graph, 'STRUCTURE', state, 0.1);
    expect(trace.result).toBe('VALID');
    expect(trace.direction).toBe('STRUCTURE');
    expect(trace.path.length).toBeGreaterThan(0);
    expect(trace.missedRequired).toHaveLength(0);
    expect(trace.coherence).toBeGreaterThan(0);
  });

  it('should produce different costs for different directions', () => {
    const graph = makeGraph();
    const state: Vector6D = [0.3, 0.1, 0.5, 0.2, 0.4, 0.1];
    const t1 = planTrace(graph, 'STRUCTURE', state, 0.1);
    const t2 = planTrace(graph, 'CONFLICT', state, 0.1);
    const t3 = planTrace(graph, 'TIME', state, 0.1);
    // Costs may differ because weights differ
    expect(t1.cost).not.toBe(t2.cost);
    // All should have same path since graph is linear
    expect(t1.path).toEqual(t2.path);
  });

  it('should block trace when cost exceeds max', () => {
    const graph = makeGraph();
    const state: Vector6D = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1];
    // Very low max cost
    const trace = planTrace(graph, 'STRUCTURE', state, 10.0, {
      weights: DIRECTION_WEIGHTS.STRUCTURE,
      phaseOffsets: [0, 0, 0, 0, 0, 0],
      maxCost: 0.0001, // Impossibly low
      minCoherence: 0.5,
    });
    expect(trace.result).toBe('BLOCKED');
    expect(trace.missedRequired.length).toBeGreaterThan(0);
  });

  it('should track visited required checkpoints', () => {
    const graph = makeGraph();
    const state: Vector6D = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1];
    const trace = planTrace(graph, 'STRUCTURE', state, 0.1);
    if (trace.result === 'VALID') {
      // Should have visited all required checkpoints
      expect(trace.visitedRequired.length).toBe(graph.getRequired().length);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Tri-Directional Planning Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: planTriDirectional', () => {
  function makeGraph(): CoreFunctionGraph {
    const g = new CoreFunctionGraph();
    g.buildDefaultEdges();
    return g;
  }

  it('should return ALLOW when all 3 traces are VALID', () => {
    const graph = makeGraph();
    const state: Vector6D = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1];
    const result = planTriDirectional(graph, state, 0.1);
    expect(result.validCount).toBe(3);
    expect(result.decision).toBe('ALLOW');
    expect(result.traces).toHaveLength(3);
  });

  it('should include all three directions', () => {
    const graph = makeGraph();
    const state: Vector6D = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1];
    const result = planTriDirectional(graph, state, 0.1);
    const dirs = result.traces.map((t) => t.direction);
    expect(dirs).toContain('STRUCTURE');
    expect(dirs).toContain('CONFLICT');
    expect(dirs).toContain('TIME');
  });

  it('should compute a positive triadic distance', () => {
    const graph = makeGraph();
    const state: Vector6D = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1];
    const result = planTriDirectional(graph, state, 0.1);
    expect(result.triadicDistance).toBeGreaterThan(0);
  });

  it('should compute agreement in [0, 1]', () => {
    const graph = makeGraph();
    const state: Vector6D = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1];
    const result = planTriDirectional(graph, state, 0.1);
    expect(result.agreement).toBeGreaterThanOrEqual(0);
    expect(result.agreement).toBeLessThanOrEqual(1);
  });

  it('should return DENY when no traces are valid', () => {
    const graph = makeGraph();
    const state: Vector6D = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1];
    // Override all configs with impossible constraints
    const impossibleConfig = {
      weights: [1, 1, 1, 1, 1, 1] as Vector6D,
      phaseOffsets: [0, 0, 0, 0, 0, 0] as Vector6D,
      maxCost: 0.00001,
      minCoherence: 0.99,
    };
    const result = planTriDirectional(graph, state, 100, {
      STRUCTURE: impossibleConfig,
      CONFLICT: impossibleConfig,
      TIME: impossibleConfig,
    });
    expect(result.decision).toBe('DENY');
  });
});

// ═══════════════════════════════════════════════════════════════
// Direction Weights Validation
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: Direction Weights', () => {
  it('should have 6 components each', () => {
    for (const dir of ['STRUCTURE', 'CONFLICT', 'TIME'] as const) {
      expect(DIRECTION_WEIGHTS[dir]).toHaveLength(6);
    }
  });

  it('should sum to approximately 1.0 per direction', () => {
    for (const dir of ['STRUCTURE', 'CONFLICT', 'TIME'] as const) {
      const sum = DIRECTION_WEIGHTS[dir].reduce((a, b) => a + b, 0);
      expect(sum).toBeCloseTo(1.0, 5);
    }
  });

  it('STRUCTURE should be KO+CA dominant', () => {
    const w = DIRECTION_WEIGHTS.STRUCTURE;
    expect(w[0] + w[3]).toBeGreaterThan(0.7); // KO + CA
  });

  it('CONFLICT should be RU dominant', () => {
    const w = DIRECTION_WEIGHTS.CONFLICT;
    expect(w[2]).toBeGreaterThan(0.5); // RU
  });

  it('TIME should be AV+DR+UM dominant', () => {
    const w = DIRECTION_WEIGHTS.TIME;
    expect(w[1] + w[4] + w[5]).toBeGreaterThan(0.7); // AV + UM + DR
  });
});
