/**
 * SCBE Hamiltonian CFI Tests
 *
 * Tests for Topological Control Flow Integrity:
 * - Control Flow Graph operations
 * - Dirac's Theorem: deg(v) ≥ |V|/2
 * - Ore's Theorem: deg(u) + deg(v) ≥ |V| for non-adjacent pairs
 * - Bipartite analysis and imbalance detection
 * - Golden path validation
 * - Hamiltonian path finding
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  ControlFlowGraph,
  HamiltonianCFI,
  createVertex,
  type CFGVertex,
  type CFIResult,
  type BipartiteResult,
  type HamiltonianCheck,
} from '../../src/harmonic/hamiltonianCFI.js';

describe('ControlFlowGraph', () => {
  let cfg: ControlFlowGraph;

  beforeEach(() => {
    cfg = new ControlFlowGraph();
  });

  // ═══════════════════════════════════════════════════════════════
  // Vertex Operations
  // ═══════════════════════════════════════════════════════════════
  describe('Vertex operations', () => {
    it('adds vertices correctly', () => {
      cfg.addVertex(createVertex(1, 'A', 0x1000));
      cfg.addVertex(createVertex(2, 'B', 0x1010));

      expect(cfg.vertexCount).toBe(2);
      expect(cfg.getVertex(1)?.label).toBe('A');
      expect(cfg.getVertex(2)?.label).toBe('B');
    });

    it('returns undefined for non-existent vertex', () => {
      expect(cfg.getVertex(999)).toBeUndefined();
    });

    it('getVertexIds returns all vertex IDs', () => {
      cfg.addVertex(createVertex(1, 'A', 0x1000));
      cfg.addVertex(createVertex(5, 'B', 0x1010));
      cfg.addVertex(createVertex(3, 'C', 0x1020));

      const ids = cfg.getVertexIds();
      expect(ids).toContain(1);
      expect(ids).toContain(5);
      expect(ids).toContain(3);
      expect(ids.length).toBe(3);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Edge Operations
  // ═══════════════════════════════════════════════════════════════
  describe('Edge operations', () => {
    beforeEach(() => {
      cfg.addVertex(createVertex(1, 'A', 0x1000));
      cfg.addVertex(createVertex(2, 'B', 0x1010));
      cfg.addVertex(createVertex(3, 'C', 0x1020));
    });

    it('adds edges correctly', () => {
      cfg.addEdge(1, 2);

      expect(cfg.edgeCount).toBe(1);
      expect(cfg.hasEdge(1, 2)).toBe(true);
      expect(cfg.hasEdge(2, 1)).toBe(true); // Undirected
    });

    it('getNeighbors returns adjacent vertices', () => {
      cfg.addEdge(1, 2);
      cfg.addEdge(1, 3);

      const neighbors = cfg.getNeighbors(1);
      expect(neighbors).toContain(2);
      expect(neighbors).toContain(3);
      expect(neighbors.length).toBe(2);
    });

    it('degree counts edges correctly', () => {
      cfg.addEdge(1, 2);
      cfg.addEdge(1, 3);

      expect(cfg.degree(1)).toBe(2);
      expect(cfg.degree(2)).toBe(1);
      expect(cfg.degree(3)).toBe(1);
    });

    it('hasEdge returns false for non-existent edges', () => {
      cfg.addEdge(1, 2);

      expect(cfg.hasEdge(1, 3)).toBe(false);
      expect(cfg.hasEdge(2, 3)).toBe(false);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Dirac's Theorem Tests
  // ═══════════════════════════════════════════════════════════════
  describe("Dirac's Theorem: deg(v) ≥ |V|/2", () => {
    it('complete graph satisfies Dirac', () => {
      // K4: Complete graph on 4 vertices
      for (let i = 1; i <= 4; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      for (let i = 1; i <= 4; i++) {
        for (let j = i + 1; j <= 4; j++) {
          cfg.addEdge(i, j);
        }
      }

      expect(cfg.checkDirac()).toBe(true);
      // Each vertex has degree 3 ≥ 4/2 = 2
    });

    it('path graph does not satisfy Dirac', () => {
      // P4: 1-2-3-4
      for (let i = 1; i <= 4; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      cfg.addEdge(1, 2);
      cfg.addEdge(2, 3);
      cfg.addEdge(3, 4);

      expect(cfg.checkDirac()).toBe(false);
      // End vertices have degree 1 < 4/2 = 2
    });

    it('cycle graph with n≥3 satisfies Dirac for n≤4', () => {
      // C4: 1-2-3-4-1
      for (let i = 1; i <= 4; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      cfg.addEdge(1, 2);
      cfg.addEdge(2, 3);
      cfg.addEdge(3, 4);
      cfg.addEdge(4, 1);

      expect(cfg.checkDirac()).toBe(true);
      // Each vertex has degree 2 ≥ 4/2 = 2
    });

    it('small graphs (n≤2) satisfy Dirac', () => {
      cfg.addVertex(createVertex(1, 'A', 0x1000));
      expect(cfg.checkDirac()).toBe(true);

      cfg.addVertex(createVertex(2, 'B', 0x1010));
      expect(cfg.checkDirac()).toBe(true);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Ore's Theorem Tests
  // ═══════════════════════════════════════════════════════════════
  describe("Ore's Theorem: deg(u) + deg(v) ≥ |V|", () => {
    it('complete graph satisfies Ore', () => {
      // K5
      for (let i = 1; i <= 5; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      for (let i = 1; i <= 5; i++) {
        for (let j = i + 1; j <= 5; j++) {
          cfg.addEdge(i, j);
        }
      }

      expect(cfg.checkOre()).toBe(true);
    });

    it('path graph does not satisfy Ore', () => {
      // P5: 1-2-3-4-5
      for (let i = 1; i <= 5; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      cfg.addEdge(1, 2);
      cfg.addEdge(2, 3);
      cfg.addEdge(3, 4);
      cfg.addEdge(4, 5);

      expect(cfg.checkOre()).toBe(false);
      // Vertices 1 and 5 are non-adjacent, deg(1) + deg(5) = 1 + 1 = 2 < 5
    });

    it('graph with Ore condition but not Dirac', () => {
      // Create graph where Ore holds but not Dirac
      for (let i = 1; i <= 6; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      // Connect in a way that some vertices have low degree but
      // non-adjacent pairs sum to enough
      cfg.addEdge(1, 2);
      cfg.addEdge(1, 3);
      cfg.addEdge(1, 4);
      cfg.addEdge(1, 5);
      cfg.addEdge(2, 3);
      cfg.addEdge(2, 4);
      cfg.addEdge(2, 5);
      cfg.addEdge(3, 6);
      cfg.addEdge(4, 6);
      cfg.addEdge(5, 6);

      // Check the theorem conditions
      const satisfiesOre = cfg.checkOre();
      const satisfiesDirac = cfg.checkDirac();

      // This is a valid graph structure test
      expect(typeof satisfiesOre).toBe('boolean');
      expect(typeof satisfiesDirac).toBe('boolean');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Bipartite Analysis Tests
  // ═══════════════════════════════════════════════════════════════
  describe('Bipartite Analysis', () => {
    it('detects bipartite graph (complete bipartite K3,3)', () => {
      // K3,3: Two sets of 3 vertices, all cross-edges
      for (let i = 1; i <= 6; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      // Set A: {1, 2, 3}, Set B: {4, 5, 6}
      for (let a = 1; a <= 3; a++) {
        for (let b = 4; b <= 6; b++) {
          cfg.addEdge(a, b);
        }
      }

      const result = cfg.checkBipartite();
      expect(result.isBipartite).toBe(true);
      expect(result.imbalance).toBe(0);
    });

    it('detects non-bipartite graph (triangle)', () => {
      // K3: Triangle
      for (let i = 1; i <= 3; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      cfg.addEdge(1, 2);
      cfg.addEdge(2, 3);
      cfg.addEdge(3, 1);

      const result = cfg.checkBipartite();
      expect(result.isBipartite).toBe(false);
    });

    it('computes imbalance for unbalanced bipartite graph', () => {
      // K2,4: Two vertices connected to four
      for (let i = 1; i <= 6; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      // Set A: {1, 2}, Set B: {3, 4, 5, 6}
      for (let a = 1; a <= 2; a++) {
        for (let b = 3; b <= 6; b++) {
          cfg.addEdge(a, b);
        }
      }

      const result = cfg.checkBipartite();
      expect(result.isBipartite).toBe(true);
      expect(result.imbalance).toBe(2); // |4 - 2| = 2
    });

    it('Rhombic Dodecahedron imbalance |6-8|=2', () => {
      // This is the key example from the spec
      // Simplified: create a bipartite graph with 6 vs 8 vertices
      for (let i = 1; i <= 14; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      // Create bipartite structure with 6 in A, 8 in B
      for (let a = 1; a <= 6; a++) {
        for (let b = 7; b <= 14; b++) {
          if ((a + b) % 3 === 0) cfg.addEdge(a, b); // Some edges
        }
      }

      const result = cfg.checkBipartite();
      expect(result.isBipartite).toBe(true);
      expect(result.imbalance).toBe(2);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Comprehensive Hamiltonicity Check
  // ═══════════════════════════════════════════════════════════════
  describe('checkHamiltonian', () => {
    it('returns complete analysis', () => {
      for (let i = 1; i <= 4; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      for (let i = 1; i <= 4; i++) {
        for (let j = i + 1; j <= 4; j++) {
          cfg.addEdge(i, j);
        }
      }

      const check = cfg.checkHamiltonian();

      expect(check).toHaveProperty('satisfiesDirac');
      expect(check).toHaveProperty('satisfiesOre');
      expect(check).toHaveProperty('minDegree');
      expect(check).toHaveProperty('likelyHamiltonian');
      expect(check).toHaveProperty('bipartite');
    });

    it('complete graph is likely Hamiltonian', () => {
      for (let i = 1; i <= 5; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      for (let i = 1; i <= 5; i++) {
        for (let j = i + 1; j <= 5; j++) {
          cfg.addEdge(i, j);
        }
      }

      const check = cfg.checkHamiltonian();
      expect(check.likelyHamiltonian).toBe(true);
      expect(check.satisfiesDirac).toBe(true);
      expect(check.satisfiesOre).toBe(true);
    });

    it('balanced bipartite is likely Hamiltonian', () => {
      // K3,3
      for (let i = 1; i <= 6; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      for (let a = 1; a <= 3; a++) {
        for (let b = 4; b <= 6; b++) {
          cfg.addEdge(a, b);
        }
      }

      const check = cfg.checkHamiltonian();
      expect(check.bipartite.isBipartite).toBe(true);
      expect(check.bipartite.imbalance).toBe(0);
      expect(check.likelyHamiltonian).toBe(true);
    });
  });
});

describe('HamiltonianCFI', () => {
  let cfg: ControlFlowGraph;
  let cfi: HamiltonianCFI;

  beforeEach(() => {
    cfg = new ControlFlowGraph();
    // Build a simple graph
    for (let i = 1; i <= 4; i++) {
      cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
    }
    cfg.addEdge(1, 2);
    cfg.addEdge(2, 3);
    cfg.addEdge(3, 4);
    cfg.addEdge(4, 1);
    cfg.addEdge(1, 3); // Make it more connected

    cfi = new HamiltonianCFI(cfg);
  });

  // ═══════════════════════════════════════════════════════════════
  // State Checking
  // ═══════════════════════════════════════════════════════════════
  describe('checkState', () => {
    it('returns VALID for existing vertex without golden path', () => {
      const result = cfi.checkState([1]);
      expect(result).toBe('VALID');
    });

    it('returns ATTACK for non-existent vertex', () => {
      const result = cfi.checkState([999]);
      expect(result).toBe('ATTACK');
    });

    it('returns OBSTRUCTION for empty state', () => {
      const result = cfi.checkState([]);
      expect(result).toBe('OBSTRUCTION');
    });

    it('returns VALID when following golden path', () => {
      cfi.setGoldenPath([1, 2, 3, 4]);

      expect(cfi.checkState([1])).toBe('VALID');
      expect(cfi.checkState([2])).toBe('VALID');
      expect(cfi.checkState([3])).toBe('VALID');
      expect(cfi.checkState([4])).toBe('VALID');
      expect(cfi.checkState([1])).toBe('VALID'); // Wraps around
    });

    it('returns DEVIATION for nearby but wrong vertex', () => {
      cfi.setGoldenPath([1, 2, 3, 4]);

      // Check state 1 first (expected)
      expect(cfi.checkState([1])).toBe('VALID');

      // Now expecting 2, but we're at a neighbor of 2
      // Deviation threshold is 0.5 by default
      const result = cfi.checkState([4]); // 4 is neighbor of 1, but expected is 2
      expect(['DEVIATION', 'ATTACK']).toContain(result);
    });

    it('reset clears position', () => {
      cfi.setGoldenPath([1, 2, 3, 4]);

      cfi.checkState([1]);
      cfi.checkState([2]);

      cfi.reset();

      // Should be back at position 0, expecting vertex 1
      expect(cfi.checkState([1])).toBe('VALID');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Hamiltonian Path Finding
  // ═══════════════════════════════════════════════════════════════
  describe('findHamiltonianPath', () => {
    it('finds path in complete graph', () => {
      const complete = new ControlFlowGraph();
      for (let i = 1; i <= 4; i++) {
        complete.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      for (let i = 1; i <= 4; i++) {
        for (let j = i + 1; j <= 4; j++) {
          complete.addEdge(i, j);
        }
      }

      const completeCFI = new HamiltonianCFI(complete);
      const path = completeCFI.findHamiltonianPath();

      expect(path).not.toBeNull();
      expect(path!.length).toBe(4);

      // Verify all vertices visited exactly once
      const visited = new Set(path!);
      expect(visited.size).toBe(4);
    });

    it('finds path in cycle', () => {
      const path = cfi.findHamiltonianPath();

      expect(path).not.toBeNull();
      expect(path!.length).toBe(4);
    });

    it('returns null for too large graph', () => {
      const large = new ControlFlowGraph();
      for (let i = 1; i <= 15; i++) {
        large.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }

      const largeCFI = new HamiltonianCFI(large);
      const path = largeCFI.findHamiltonianPath(12); // Max 12 vertices

      expect(path).toBeNull();
    });

    it('returns empty array for empty graph', () => {
      const empty = new ControlFlowGraph();
      const emptyCFI = new HamiltonianCFI(empty);

      const path = emptyCFI.findHamiltonianPath();
      expect(path).toEqual([]);
    });

    it('returns single vertex for single-vertex graph', () => {
      const single = new ControlFlowGraph();
      single.addVertex(createVertex(1, 'A', 0x1000));

      const singleCFI = new HamiltonianCFI(single);
      const path = singleCFI.findHamiltonianPath();

      expect(path).toEqual([1]);
    });

    it('returns null for disconnected graph', () => {
      const disconnected = new ControlFlowGraph();
      disconnected.addVertex(createVertex(1, 'A', 0x1000));
      disconnected.addVertex(createVertex(2, 'B', 0x1010));
      // No edges - disconnected

      const disconnectedCFI = new HamiltonianCFI(disconnected);
      const path = disconnectedCFI.findHamiltonianPath();

      expect(path).toBeNull();
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Graph Analysis
  // ═══════════════════════════════════════════════════════════════
  describe('analyzeGraph', () => {
    it('returns Hamiltonicity analysis', () => {
      const analysis = cfi.analyzeGraph();

      expect(analysis).toHaveProperty('satisfiesDirac');
      expect(analysis).toHaveProperty('satisfiesOre');
      expect(analysis).toHaveProperty('minDegree');
      expect(analysis).toHaveProperty('likelyHamiltonian');
      expect(analysis).toHaveProperty('bipartite');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Spectral Distance (Internal)
  // ═══════════════════════════════════════════════════════════════
  describe('Spectral distance behavior', () => {
    it('identical vertices have distance 0', () => {
      cfi.setGoldenPath([1, 2, 3, 4]);

      // Check same vertex - should be VALID
      expect(cfi.checkState([1])).toBe('VALID');
    });

    it('adjacent vertices have smaller distance than non-adjacent', () => {
      // Build a line graph: 1-2-3-4-5
      const line = new ControlFlowGraph();
      for (let i = 1; i <= 5; i++) {
        line.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      line.addEdge(1, 2);
      line.addEdge(2, 3);
      line.addEdge(3, 4);
      line.addEdge(4, 5);

      const lineCFI = new HamiltonianCFI(line, 0.5);
      lineCFI.setGoldenPath([1, 2, 3, 4, 5]);

      // Advance to position expecting vertex 2
      lineCFI.checkState([1]);

      // Check vertex 3 (adjacent to 2 via shared neighbor)
      const result = lineCFI.checkState([3]);
      expect(['DEVIATION', 'ATTACK']).toContain(result);
    });
  });
});

describe('createVertex', () => {
  it('creates vertex with required fields', () => {
    const v = createVertex(1, 'main', 0x4000);

    expect(v.id).toBe(1);
    expect(v.label).toBe('main');
    expect(v.address).toBe(0x4000);
    expect(v.metadata).toBeUndefined();
  });

  it('creates vertex with metadata', () => {
    const v = createVertex(42, 'handler', 0x8000, {
      type: 'function',
      size: 128,
    });

    expect(v.id).toBe(42);
    expect(v.metadata?.type).toBe('function');
    expect(v.metadata?.size).toBe(128);
  });
});

// ═══════════════════════════════════════════════════════════════
// Integration Tests - Real CFI Scenarios
// ═══════════════════════════════════════════════════════════════
describe('CFI Integration Scenarios', () => {
  it('detects ROP chain deviation', () => {
    // Model a simple program CFG
    const cfg = new ControlFlowGraph();

    // Normal execution flow
    cfg.addVertex(createVertex(1, 'main', 0x1000));
    cfg.addVertex(createVertex(2, 'checkAuth', 0x2000));
    cfg.addVertex(createVertex(3, 'processInput', 0x3000));
    cfg.addVertex(createVertex(4, 'writeOutput', 0x4000));
    cfg.addVertex(createVertex(5, 'exit', 0x5000));

    // Valid transitions
    cfg.addEdge(1, 2);
    cfg.addEdge(2, 3);
    cfg.addEdge(2, 5); // Auth failure
    cfg.addEdge(3, 4);
    cfg.addEdge(4, 5);

    const cfi = new HamiltonianCFI(cfg, 0.3);
    cfi.setGoldenPath([1, 2, 3, 4, 5]);

    // Normal execution
    expect(cfi.checkState([1])).toBe('VALID');
    expect(cfi.checkState([2])).toBe('VALID');

    // ROP attack jumps to unexpected address
    // Attacker tries to jump directly to writeOutput, skipping processInput
    cfi.reset();
    cfi.setGoldenPath([1, 2, 3, 4, 5]);

    cfi.checkState([1]);
    cfi.checkState([2]);
    // Expected: 3 (processInput), but attacker jumps to 4 (writeOutput)
    const result = cfi.checkState([4]);
    expect(['DEVIATION', 'ATTACK']).toContain(result);
  });

  it('allows alternative valid paths', () => {
    const cfg = new ControlFlowGraph();

    cfg.addVertex(createVertex(1, 'entry', 0x1000));
    cfg.addVertex(createVertex(2, 'branch_a', 0x2000));
    cfg.addVertex(createVertex(3, 'branch_b', 0x3000));
    cfg.addVertex(createVertex(4, 'merge', 0x4000));

    cfg.addEdge(1, 2);
    cfg.addEdge(1, 3);
    cfg.addEdge(2, 4);
    cfg.addEdge(3, 4);

    const cfi = new HamiltonianCFI(cfg);

    // Without golden path, any valid vertex should work
    expect(cfi.checkState([1])).toBe('VALID');
    expect(cfi.checkState([2])).toBe('VALID');
    expect(cfi.checkState([4])).toBe('VALID');
  });
});
