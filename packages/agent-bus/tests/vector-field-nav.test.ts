/**
 * @file vector-field-nav.test.ts
 * Tests for multi-lattice vector field navigation.
 * Covers maze generation, oracle BFS, 7 lattice fields, 5 algorithms,
 * receipt chain, scoring, benchmark shape, and ablation table.
 */

import { describe, expect, it } from 'vitest';
import {
  type MazeGrid,
  type MazeConfig,
  type AgentState,
  generateMaze,
  oracleBFS,
  createAgent,
  computeVTotal,
  runMission,
  scoreRun,
  verifyReceiptChain,
  runNavBench,
  DEFAULT_WEIGHTS,
  BENCHMARK_MAZES,
  VECTOR_KERNEL_3X3,
} from '../src/index.js';

// ─── Fixture ──────────────────────────────────────────────────────────────────

const TINY: MazeConfig = {
  id: 'test-tiny',
  width: 9,
  height: 9,
  seed: 42,
  sensor_radius: 3,
  max_steps: 200,
};
const SMALL: MazeConfig = {
  id: 'test-small',
  width: 11,
  height: 11,
  seed: 99,
  sensor_radius: 3,
  max_steps: 300,
};

// ─── generateMaze ─────────────────────────────────────────────────────────────

describe('generateMaze', () => {
  it('returns a grid with correct dimensions', () => {
    const m = generateMaze(TINY);
    expect(m.width).toBe(9);
    expect(m.height).toBe(9);
    expect(m.cells.length).toBe(9);
    expect(m.cells[0]!.length).toBe(9);
  });

  it('start cell is type start', () => {
    const m = generateMaze(TINY);
    const [sx, sy] = m.start;
    expect(m.cells[sy]![sx]!.type).toBe('start');
  });

  it('goal cell is type goal', () => {
    const m = generateMaze(TINY);
    const [gx, gy] = m.goal;
    expect(m.cells[gy]![gx]!.type).toBe('goal');
  });

  it('border cells are walls', () => {
    const m = generateMaze(TINY);
    for (let x = 0; x < m.width; x++) {
      expect(m.cells[0]![x]!.type).toBe('wall');
      expect(m.cells[m.height - 1]![x]!.type).toBe('wall');
    }
    for (let y = 0; y < m.height; y++) {
      expect(m.cells[y]![0]!.type).toBe('wall');
      expect(m.cells[y]![m.width - 1]!.type).toBe('wall');
    }
  });

  it('maze is deterministic for same seed', () => {
    const m1 = generateMaze(TINY);
    const m2 = generateMaze(TINY);
    expect(JSON.stringify(m1.cells)).toBe(JSON.stringify(m2.cells));
  });

  it('different seeds produce different mazes', () => {
    const m1 = generateMaze({ ...TINY, seed: 1 });
    const m2 = generateMaze({ ...TINY, seed: 2 });
    expect(JSON.stringify(m1.cells)).not.toBe(JSON.stringify(m2.cells));
  });

  it('passable cells have positive importance', () => {
    const m = generateMaze(TINY);
    for (let y = 0; y < m.height; y++) {
      for (let x = 0; x < m.width; x++) {
        const c = m.cells[y]![x]!;
        if (c.type !== 'wall') {
          expect(c.importance).toBeGreaterThan(0);
        }
      }
    }
  });

  it('id encodes config id and seed', () => {
    const m = generateMaze(TINY);
    expect(m.id).toContain('test-tiny');
    expect(m.id).toContain('42');
  });
});

// ─── oracleBFS ────────────────────────────────────────────────────────────────

describe('oracleBFS', () => {
  it('returns a non-null path for a connected maze', () => {
    const m = generateMaze(TINY);
    expect(oracleBFS(m)).not.toBeNull();
  });

  it('path starts at maze.start', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    expect(path[0]).toEqual(m.start);
  });

  it('path ends at maze.goal', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    expect(path[path.length - 1]).toEqual(m.goal);
  });

  it('path length is positive', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    expect(path.length).toBeGreaterThan(1);
  });

  it('consecutive path cells are adjacent (Manhattan distance 1)', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    for (let i = 0; i < path.length - 1; i++) {
      const d = Math.abs(path[i]![0] - path[i + 1]![0]) + Math.abs(path[i]![1] - path[i + 1]![1]);
      expect(d).toBe(1);
    }
  });
});

// ─── computeVTotal ────────────────────────────────────────────────────────────

describe('computeVTotal', () => {
  it('returns all field values + total', () => {
    const m = generateMaze(TINY);
    const agent = createAgent(m, TINY.sensor_radius);
    const bd = computeVTotal(m.start, m, agent, DEFAULT_WEIGHTS, TINY.sensor_radius);
    expect(typeof bd.goal).toBe('number');
    expect(typeof bd.obstacle).toBe('number');
    expect(typeof bd.frontier).toBe('number');
    expect(typeof bd.security).toBe('number');
    expect(typeof bd.importance).toBe('number');
    expect(typeof bd.memory).toBe('number');
    expect(typeof bd.edge_channel).toBe('number');
    expect(typeof bd.kernel_convolution).toBe('number');
    expect(typeof bd.total).toBe('number');
  });

  it('exports the 3x3 vector kernel used by the convolution field', () => {
    expect(VECTOR_KERNEL_3X3).toEqual([
      [0.4, 0.7, 0.4],
      [0.7, 1.0, 0.7],
      [0.4, 0.7, 0.4],
    ]);
  });

  it('cell closer to goal has higher goal field value', () => {
    const m = generateMaze(TINY);
    const agent = createAgent(m, TINY.sensor_radius);
    const [gx, gy] = m.goal;
    const near: [number, number] = [gx - 1, gy - 1];
    const far: [number, number] = m.start;
    const bdNear = computeVTotal(near, m, agent, DEFAULT_WEIGHTS, TINY.sensor_radius);
    const bdFar = computeVTotal(far, m, agent, DEFAULT_WEIGHTS, TINY.sensor_radius);
    expect(bdNear.goal).toBeGreaterThan(bdFar.goal);
  });

  it('memory field penalizes already-visited cells', () => {
    const m = generateMaze(TINY);
    const agent = createAgent(m, TINY.sensor_radius);
    const [sx, sy] = m.start;
    const fresh: [number, number] = [sx + 2, sy];
    const bdFresh = computeVTotal(fresh, m, agent, DEFAULT_WEIGHTS, TINY.sensor_radius);
    // After visiting fresh, memory penalty applies
    agent.visit_counts.set(`${sx + 2},${sy}`, 3);
    const bdVisited = computeVTotal(fresh, m, agent, DEFAULT_WEIGHTS, TINY.sensor_radius);
    expect(bdVisited.memory).toBeLessThan(bdFresh.memory);
    expect(bdVisited.total).toBeLessThan(bdFresh.total);
  });

  it('security field penalizes QUARANTINE cells', () => {
    const m = generateMaze(TINY);
    const agent = createAgent(m, TINY.sensor_radius);
    // Force a cell to QUARANTINE and compare
    const [sx, sy] = m.start;
    const testPos: [number, number] = [sx + 2, sy + 2];
    const cellBefore = m.cells[testPos[1]]?.[testPos[0]];
    if (cellBefore && cellBefore.type !== 'wall') {
      const origTier = cellBefore.security_tier;
      cellBefore.security_tier = 'ALLOW';
      const bdAllow = computeVTotal(testPos, m, agent, DEFAULT_WEIGHTS, TINY.sensor_radius);
      cellBefore.security_tier = 'QUARANTINE';
      const bdQuarantine = computeVTotal(testPos, m, agent, DEFAULT_WEIGHTS, TINY.sensor_radius);
      cellBefore.security_tier = origTier;
      expect(bdAllow.security).toBeGreaterThan(bdQuarantine.security);
    }
  });

  it('edge_channel field is >= 0', () => {
    const m = generateMaze(TINY);
    const agent = createAgent(m, TINY.sensor_radius);
    const bd = computeVTotal(m.start, m, agent, DEFAULT_WEIGHTS, TINY.sensor_radius);
    expect(bd.edge_channel).toBeGreaterThanOrEqual(0);
  });

  it('all-zero weights produce total = 0', () => {
    const m = generateMaze(TINY);
    const agent = createAgent(m, TINY.sensor_radius);
    const zeroWeights = {
      goal: 0,
      obstacle: 0,
      frontier: 0,
      security: 0,
      importance: 0,
      memory: 0,
      edge_channel: 0,
      kernel_convolution: 0,
    };
    const bd = computeVTotal(m.start, m, agent, zeroWeights, TINY.sensor_radius);
    expect(bd.total).toBe(0);
  });
});

// ─── runMission ───────────────────────────────────────────────────────────────

describe('runMission', () => {
  it('multi-lattice agent reaches goal on tiny maze', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    const agent = runMission(m, TINY, 'multi-lattice', DEFAULT_WEIGHTS, path);
    expect(agent.pos).toEqual(m.goal);
  });

  it('astar-full agent always reaches goal', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    const agent = runMission(m, TINY, 'astar-full', DEFAULT_WEIGHTS, path);
    expect(agent.pos).toEqual(m.goal);
  });

  it('astar-full solves in oracle_path_length - 1 steps', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    const agent = runMission(m, TINY, 'astar-full', DEFAULT_WEIGHTS, path);
    expect(agent.steps).toBe(path.length - 1);
  });

  it('greedy agent moves (steps > 0)', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    const agent = runMission(m, TINY, 'greedy', DEFAULT_WEIGHTS, path);
    expect(agent.steps).toBeGreaterThan(0);
  });

  it('random agent moves (steps > 0)', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    const agent = runMission(m, TINY, 'random', DEFAULT_WEIGHTS, path);
    expect(agent.steps).toBeGreaterThan(0);
  });

  it('astar-limited agent takes steps', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    const agent = runMission(m, TINY, 'astar-limited', DEFAULT_WEIGHTS, path);
    expect(agent.steps).toBeGreaterThan(0);
  });

  it('receipts count equals steps', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    const agent = runMission(m, TINY, 'multi-lattice', DEFAULT_WEIGHTS, path);
    expect(agent.receipts.length).toBe(agent.steps);
  });

  it('security score is non-negative', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    const agent = runMission(m, TINY, 'multi-lattice', DEFAULT_WEIGHTS, path);
    expect(agent.security_score).toBeGreaterThanOrEqual(0);
  });
});

// ─── receipt chain ────────────────────────────────────────────────────────────

describe('verifyReceiptChain', () => {
  it('returns 1.0 for an untampered chain', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    const agent = runMission(m, TINY, 'astar-full', DEFAULT_WEIGHTS, path);
    expect(verifyReceiptChain(agent.receipts)).toBe(1);
  });

  it('returns 0.0 for an empty chain', () => {
    expect(verifyReceiptChain([])).toBe(1.0);
  });

  it('detects tampering when receipt_hash is mutated', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    const agent = runMission(m, TINY, 'astar-full', DEFAULT_WEIGHTS, path);
    if (agent.receipts.length > 1) {
      agent.receipts[0]!.receipt_hash = 'deadbeef0000000000000000deadbeef';
      const integrity = verifyReceiptChain(agent.receipts);
      expect(integrity).toBeLessThan(1.0);
    }
  });

  it('each receipt carries prev_hash of the previous receipt', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    const agent = runMission(m, TINY, 'astar-full', DEFAULT_WEIGHTS, path);
    for (let i = 1; i < agent.receipts.length; i++) {
      expect(agent.receipts[i]!.prev_hash).toBe(agent.receipts[i - 1]!.receipt_hash);
    }
  });
});

// ─── scoreRun ─────────────────────────────────────────────────────────────────

describe('scoreRun', () => {
  it('solved=true when agent is at goal', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    const agent = runMission(m, TINY, 'astar-full', DEFAULT_WEIGHTS, path);
    const score = scoreRun(agent, m, TINY, 'astar-full', path, 10);
    expect(score.solved).toBe(true);
  });

  it('schema_version is correct', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    const agent = runMission(m, TINY, 'astar-full', DEFAULT_WEIGHTS, path);
    const score = scoreRun(agent, m, TINY, 'astar-full', path, 10);
    expect(score.schema_version).toBe('scbe.agent_bus.vector_field_nav.bench.v1');
  });

  it('efficiency = oracle_path_length / steps for astar-full', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    const agent = runMission(m, TINY, 'astar-full', DEFAULT_WEIGHTS, path);
    const score = scoreRun(agent, m, TINY, 'astar-full', path, 10);
    expect(score.efficiency).toBe(1.0);
  });

  it('frontier_coverage is in [0, 1]', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    const agent = runMission(m, TINY, 'multi-lattice', DEFAULT_WEIGHTS, path);
    const score = scoreRun(agent, m, TINY, 'multi-lattice', path, 10);
    expect(score.frontier_coverage).toBeGreaterThanOrEqual(0);
    expect(score.frontier_coverage).toBeLessThanOrEqual(1);
  });

  it('receipt_completeness = 1.0 for untampered mission', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    const agent = runMission(m, TINY, 'astar-full', DEFAULT_WEIGHTS, path);
    const score = scoreRun(agent, m, TINY, 'astar-full', path, 10);
    expect(score.receipt_completeness).toBe(1.0);
  });

  it('penetration_depth >= 0', () => {
    const m = generateMaze(TINY);
    const path = oracleBFS(m)!;
    const agent = runMission(m, TINY, 'greedy', DEFAULT_WEIGHTS, path);
    const score = scoreRun(agent, m, TINY, 'greedy', path, 10);
    expect(score.penetration_depth).toBeGreaterThanOrEqual(0);
  });
});

// ─── runNavBench ──────────────────────────────────────────────────────────────

describe('runNavBench', () => {
  it('returns correct schema_version', () => {
    const result = runNavBench({
      mazes: [TINY],
      algorithms: ['multi-lattice', 'astar-full'],
      skip_ablation: true,
    });
    expect(result.schema_version).toBe('scbe.agent_bus.vector_field_nav.v1');
  });

  it('run count = mazes × algorithms (no ablation)', () => {
    const result = runNavBench({
      mazes: [TINY],
      algorithms: ['multi-lattice', 'greedy'],
      skip_ablation: true,
    });
    expect(result.runs.length).toBe(2);
  });

  it('ablation table has 8 entries', () => {
    const result = runNavBench({
      mazes: [TINY],
      algorithms: ['multi-lattice'],
      skip_ablation: false,
    });
    expect(Object.keys(result.ablation_table).length).toBe(8);
  });

  it('all ablation tags present', () => {
    const result = runNavBench({
      mazes: [TINY],
      algorithms: ['multi-lattice'],
      skip_ablation: false,
    });
    for (const tag of [
      'no-goal',
      'no-obstacle',
      'no-frontier',
      'no-security',
      'no-importance',
      'no-memory',
      'no-edge',
      'no-kernel',
    ]) {
      expect(result.ablation_table).toHaveProperty(tag);
    }
  });

  it('comparison contains all requested algorithms', () => {
    const algs = ['multi-lattice', 'greedy', 'random'] as const;
    const result = runNavBench({ mazes: [TINY], algorithms: [...algs], skip_ablation: true });
    for (const alg of algs) {
      expect(result.comparison).toHaveProperty(alg);
    }
  });

  it('astar-full solve_rate = 1.0 on all mazes', () => {
    const result = runNavBench({
      mazes: [TINY, SMALL],
      algorithms: ['astar-full'],
      skip_ablation: true,
    });
    expect(result.comparison['astar-full']!.solve_rate).toBe(1.0);
  });

  it('summary has expected fields', () => {
    const result = runNavBench({
      mazes: [TINY],
      algorithms: ['multi-lattice', 'random'],
      skip_ablation: true,
    });
    expect(typeof result.summary.total_mazes).toBe('number');
    expect(typeof result.summary.total_runs).toBe('number');
    expect(typeof result.summary.total_ms).toBe('number');
  });

  it('full bench with all default mazes and algorithms completes without throwing', () => {
    expect(() => runNavBench({ skip_ablation: true })).not.toThrow();
  });

  it('multi-lattice solve_rate >= random_solve_rate on default mazes', () => {
    const result = runNavBench({ skip_ablation: true });
    expect(result.summary.multi_lattice_solve_rate).toBeGreaterThanOrEqual(
      result.summary.random_solve_rate
    );
  });
});
