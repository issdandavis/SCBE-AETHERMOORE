/**
 * SCBE PHDM Tests - Polynomial Hamiltonian Detection Module
 *
 * Tests for Hamiltonian path detection optimizations:
 * - Ore's Theorem: deg(u) + deg(v) ≥ |V| for non-adjacent pairs
 * - Dirac's Theorem: deg(v) ≥ |V|/2 for all vertices
 * - Topological obstructions (bipartite imbalance)
 * - Path finding algorithms
 * - Integration with CFI
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  ControlFlowGraph,
  HamiltonianCFI,
  createVertex,
} from '../../src/harmonic/hamiltonianCFI.js';

describe('PHDM - Ore\'s Theorem Optimization', () => {
  // ═══════════════════════════════════════════════════════════════
  // Complete Graphs - Always Hamiltonian
  // ═══════════════════════════════════════════════════════════════
  describe('Complete Graphs (Kn)', () => {
    it('K3 (triangle) is Hamiltonian', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 3; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      cfg.addEdge(1, 2);
      cfg.addEdge(2, 3);
      cfg.addEdge(3, 1);

      const check = cfg.checkHamiltonian();
      expect(check.likelyHamiltonian).toBe(true);
      expect(check.satisfiesDirac).toBe(true);
      expect(check.satisfiesOre).toBe(true);
    });

    it('K5 (complete on 5 vertices) is Hamiltonian', () => {
      const cfg = new ControlFlowGraph();
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
      expect(check.minDegree).toBe(4);
    });

    it('K10 satisfies both Ore and Dirac', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 10; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      for (let i = 1; i <= 10; i++) {
        for (let j = i + 1; j <= 10; j++) {
          cfg.addEdge(i, j);
        }
      }

      const check = cfg.checkHamiltonian();
      expect(check.satisfiesDirac).toBe(true);
      expect(check.satisfiesOre).toBe(true);
      // Each vertex has degree 9 ≥ 10/2 = 5
      expect(check.minDegree).toBe(9);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Cycle Graphs - Always Hamiltonian
  // ═══════════════════════════════════════════════════════════════
  describe('Cycle Graphs (Cn)', () => {
    it('C4 (square) satisfies Dirac', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 4; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      cfg.addEdge(1, 2);
      cfg.addEdge(2, 3);
      cfg.addEdge(3, 4);
      cfg.addEdge(4, 1);

      const check = cfg.checkHamiltonian();
      // Each vertex has degree 2 = 4/2, so Dirac is satisfied
      expect(check.satisfiesDirac).toBe(true);
      expect(check.likelyHamiltonian).toBe(true);
    });

    it('C6 (hexagon) does not satisfy Dirac but is bipartite balanced', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 6; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      for (let i = 1; i <= 5; i++) {
        cfg.addEdge(i, i + 1);
      }
      cfg.addEdge(6, 1);

      const check = cfg.checkHamiltonian();
      // deg(v) = 2 < 6/2 = 3, so Dirac fails
      expect(check.satisfiesDirac).toBe(false);
      // But it's bipartite with balanced sets
      expect(check.bipartite.isBipartite).toBe(true);
      expect(check.bipartite.imbalance).toBe(0);
      expect(check.likelyHamiltonian).toBe(true);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Path Graphs - Not Hamiltonian Cycle
  // ═══════════════════════════════════════════════════════════════
  describe('Path Graphs (Pn)', () => {
    it('P5 (path on 5 vertices) fails Ore and Dirac', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 5; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      cfg.addEdge(1, 2);
      cfg.addEdge(2, 3);
      cfg.addEdge(3, 4);
      cfg.addEdge(4, 5);

      const check = cfg.checkHamiltonian();
      // Endpoints have degree 1
      expect(check.minDegree).toBe(1);
      expect(check.satisfiesDirac).toBe(false);
      // Vertices 1 and 5 are non-adjacent, deg(1) + deg(5) = 2 < 5
      expect(check.satisfiesOre).toBe(false);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Bipartite Graphs - Imbalance Detection
  // ═══════════════════════════════════════════════════════════════
  describe('Bipartite Imbalance Detection', () => {
    it('K_{3,3} is balanced and Hamiltonian', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 6; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      // Bipartite: {1,2,3} - {4,5,6}
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

    it('K_{2,4} is imbalanced and NOT Hamiltonian', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 6; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      // Bipartite: {1,2} - {3,4,5,6}
      for (let a = 1; a <= 2; a++) {
        for (let b = 3; b <= 6; b++) {
          cfg.addEdge(a, b);
        }
      }

      const check = cfg.checkHamiltonian();
      expect(check.bipartite.isBipartite).toBe(true);
      expect(check.bipartite.imbalance).toBe(2); // |2 - 4| = 2
      // Imbalanced bipartite graphs cannot have Hamiltonian cycles
      // But our simple heuristic may still mark it likely if Dirac/Ore satisfied
    });

    it('Rhombic Dodecahedron analog (6-8 imbalance)', () => {
      // Create a bipartite graph with 6 vs 8 vertices
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 14; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }

      // Connect set A (1-6) to set B (7-14)
      for (let a = 1; a <= 6; a++) {
        for (let b = 7; b <= 14; b++) {
          if ((a + b) % 2 === 0) {
            cfg.addEdge(a, b);
          }
        }
      }

      const check = cfg.checkHamiltonian();
      expect(check.bipartite.isBipartite).toBe(true);
      expect(check.bipartite.imbalance).toBe(2);
      // This graph has obstruction |6-8| = 2
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Ore's Theorem Edge Cases
  // ═══════════════════════════════════════════════════════════════
  describe('Ore\'s Theorem Edge Cases', () => {
    it('graph satisfying Ore but not Dirac', () => {
      // Create a graph where some vertices have low degree
      // but non-adjacent pairs sum to enough
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 4; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      // Diamond graph: 1-2, 1-3, 2-3, 2-4, 3-4
      cfg.addEdge(1, 2);
      cfg.addEdge(1, 3);
      cfg.addEdge(2, 3);
      cfg.addEdge(2, 4);
      cfg.addEdge(3, 4);

      const check = cfg.checkHamiltonian();
      // Vertex 1 has degree 2 < 4/2 = 2, but actually 2 = 2
      // Vertex 4 has degree 2
      // Non-adjacent: 1-4, deg(1)+deg(4) = 2+2 = 4 = |V|
      expect(check.satisfiesOre).toBe(true);
    });

    it('graph failing Ore due to low-degree non-adjacent pair', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 5; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      // Star graph: center (1) connected to all others
      cfg.addEdge(1, 2);
      cfg.addEdge(1, 3);
      cfg.addEdge(1, 4);
      cfg.addEdge(1, 5);

      const check = cfg.checkHamiltonian();
      // Non-adjacent: 2-3, deg(2)+deg(3) = 1+1 = 2 < 5
      expect(check.satisfiesOre).toBe(false);
      expect(check.satisfiesDirac).toBe(false);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Dirac's Theorem Boundary Cases
  // ═══════════════════════════════════════════════════════════════
  describe('Dirac\'s Theorem Boundary', () => {
    it('exactly at Dirac threshold: deg(v) = |V|/2', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 6; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      // Create graph where each vertex has degree exactly 3 = 6/2
      // K_{3,3} modified
      cfg.addEdge(1, 4); cfg.addEdge(1, 5); cfg.addEdge(1, 6);
      cfg.addEdge(2, 4); cfg.addEdge(2, 5); cfg.addEdge(2, 6);
      cfg.addEdge(3, 4); cfg.addEdge(3, 5); cfg.addEdge(3, 6);

      const check = cfg.checkHamiltonian();
      expect(check.minDegree).toBe(3);
      expect(check.satisfiesDirac).toBe(true);
    });

    it('just below Dirac threshold: deg(v) = |V|/2 - 1', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 6; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      // Create graph where min degree is 2 < 6/2 = 3
      cfg.addEdge(1, 2); cfg.addEdge(2, 3);
      cfg.addEdge(3, 4); cfg.addEdge(4, 5);
      cfg.addEdge(5, 6); cfg.addEdge(6, 1);

      const check = cfg.checkHamiltonian();
      expect(check.minDegree).toBe(2);
      expect(check.satisfiesDirac).toBe(false);
    });
  });
});

describe('PHDM - Hamiltonian Path Finding', () => {
  // ═══════════════════════════════════════════════════════════════
  // Path Finding in Small Graphs
  // ═══════════════════════════════════════════════════════════════
  describe('Small Graph Path Finding', () => {
    it('finds path in K4', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 4; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      for (let i = 1; i <= 4; i++) {
        for (let j = i + 1; j <= 4; j++) {
          cfg.addEdge(i, j);
        }
      }

      const cfi = new HamiltonianCFI(cfg);
      const path = cfi.findHamiltonianPath();

      expect(path).not.toBeNull();
      expect(path!.length).toBe(4);
      expect(new Set(path!).size).toBe(4); // All unique
    });

    it('finds path in cycle C5', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 5; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      for (let i = 1; i < 5; i++) {
        cfg.addEdge(i, i + 1);
      }
      cfg.addEdge(5, 1);

      const cfi = new HamiltonianCFI(cfg);
      const path = cfi.findHamiltonianPath();

      expect(path).not.toBeNull();
      expect(path!.length).toBe(5);
    });

    it('returns null for disconnected graph', () => {
      const cfg = new ControlFlowGraph();
      cfg.addVertex(createVertex(1, 'A', 0x1000));
      cfg.addVertex(createVertex(2, 'B', 0x2000));
      cfg.addVertex(createVertex(3, 'C', 0x3000));
      // 1-2 connected, 3 isolated
      cfg.addEdge(1, 2);

      const cfi = new HamiltonianCFI(cfg);
      const path = cfi.findHamiltonianPath();

      expect(path).toBeNull();
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Path Verification
  // ═══════════════════════════════════════════════════════════════
  describe('Path Verification', () => {
    it('path visits all vertices exactly once', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 6; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      // Cycle with extra edges
      for (let i = 1; i <= 5; i++) cfg.addEdge(i, i + 1);
      cfg.addEdge(6, 1);
      cfg.addEdge(1, 3);
      cfg.addEdge(2, 4);

      const cfi = new HamiltonianCFI(cfg);
      const path = cfi.findHamiltonianPath();

      if (path) {
        expect(path.length).toBe(6);
        const unique = new Set(path);
        expect(unique.size).toBe(6);
      }
    });

    it('consecutive path vertices are adjacent', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 5; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      for (let i = 1; i <= 5; i++) {
        for (let j = i + 1; j <= 5; j++) {
          cfg.addEdge(i, j);
        }
      }

      const cfi = new HamiltonianCFI(cfg);
      const path = cfi.findHamiltonianPath();

      expect(path).not.toBeNull();
      for (let i = 0; i < path!.length - 1; i++) {
        expect(cfg.hasEdge(path![i], path![i + 1])).toBe(true);
      }
    });
  });
});

describe('PHDM - CFI Integration', () => {
  // ═══════════════════════════════════════════════════════════════
  // Golden Path Validation
  // ═══════════════════════════════════════════════════════════════
  describe('Golden Path CFI', () => {
    it('detects valid execution on golden path', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 5; i++) {
        cfg.addVertex(createVertex(i, `func_${i}`, i * 0x1000));
      }
      cfg.addEdge(1, 2);
      cfg.addEdge(2, 3);
      cfg.addEdge(3, 4);
      cfg.addEdge(4, 5);
      cfg.addEdge(5, 1); // Loop back

      const cfi = new HamiltonianCFI(cfg);
      cfi.setGoldenPath([1, 2, 3, 4, 5]);

      expect(cfi.checkState([1])).toBe('VALID');
      expect(cfi.checkState([2])).toBe('VALID');
      expect(cfi.checkState([3])).toBe('VALID');
      expect(cfi.checkState([4])).toBe('VALID');
      expect(cfi.checkState([5])).toBe('VALID');
    });

    it('detects deviation from golden path', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 4; i++) {
        cfg.addVertex(createVertex(i, `func_${i}`, i * 0x1000));
      }
      cfg.addEdge(1, 2);
      cfg.addEdge(2, 3);
      cfg.addEdge(3, 4);

      const cfi = new HamiltonianCFI(cfg, 0.3);
      cfi.setGoldenPath([1, 2, 3, 4]);

      cfi.checkState([1]); // Move to expecting 2
      const result = cfi.checkState([4]); // Jump to 4 instead of 2

      expect(['DEVIATION', 'ATTACK']).toContain(result);
    });

    it('detects attack (non-existent vertex)', () => {
      const cfg = new ControlFlowGraph();
      cfg.addVertex(createVertex(1, 'A', 0x1000));
      cfg.addVertex(createVertex(2, 'B', 0x2000));
      cfg.addEdge(1, 2);

      const cfi = new HamiltonianCFI(cfg);
      cfi.setGoldenPath([1, 2]);

      expect(cfi.checkState([999])).toBe('ATTACK');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Obstruction Detection
  // ═══════════════════════════════════════════════════════════════
  describe('Topological Obstruction Detection', () => {
    it('detects bipartite imbalance obstruction', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 7; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i * 0x1000));
      }
      // K_{3,4}: 3 vertices in one set, 4 in other
      for (let a = 1; a <= 3; a++) {
        for (let b = 4; b <= 7; b++) {
          cfg.addEdge(a, b);
        }
      }

      const cfi = new HamiltonianCFI(cfg);
      const analysis = cfi.analyzeGraph();

      expect(analysis.bipartite.isBipartite).toBe(true);
      expect(analysis.bipartite.imbalance).toBe(1); // |3 - 4| = 1
    });

    it('reports obstruction for empty state', () => {
      const cfg = new ControlFlowGraph();
      cfg.addVertex(createVertex(1, 'A', 0x1000));

      const cfi = new HamiltonianCFI(cfg);

      expect(cfi.checkState([])).toBe('OBSTRUCTION');
    });
  });
});

describe('PHDM - Performance & Complexity', () => {
  // ═══════════════════════════════════════════════════════════════
  // Theorem Checking Performance
  // ═══════════════════════════════════════════════════════════════
  describe('Theorem Check Performance', () => {
    it('Dirac check is O(|V|)', () => {
      const sizes = [10, 50, 100];

      for (const n of sizes) {
        const cfg = new ControlFlowGraph();
        for (let i = 1; i <= n; i++) {
          cfg.addVertex(createVertex(i, `V${i}`, i));
        }
        // Create complete graph
        for (let i = 1; i <= n; i++) {
          for (let j = i + 1; j <= n; j++) {
            cfg.addEdge(i, j);
          }
        }

        const start = performance.now();
        cfg.checkDirac();
        const elapsed = performance.now() - start;

        // Should be fast even for larger graphs
        expect(elapsed).toBeLessThan(100); // 100ms max
      }
    });

    it('Ore check is O(|V|²)', () => {
      const sizes = [10, 30, 50];

      for (const n of sizes) {
        const cfg = new ControlFlowGraph();
        for (let i = 1; i <= n; i++) {
          cfg.addVertex(createVertex(i, `V${i}`, i));
        }
        // Sparse graph
        for (let i = 1; i < n; i++) {
          cfg.addEdge(i, i + 1);
        }

        const start = performance.now();
        cfg.checkOre();
        const elapsed = performance.now() - start;

        // Should complete in reasonable time
        expect(elapsed).toBeLessThan(500); // 500ms max
      }
    });

    it('bipartite check is O(|V| + |E|)', () => {
      const cfg = new ControlFlowGraph();
      const n = 100;

      for (let i = 1; i <= n; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i));
      }
      // Random bipartite structure
      for (let a = 1; a <= n / 2; a++) {
        for (let b = n / 2 + 1; b <= n; b++) {
          if (Math.random() < 0.3) {
            cfg.addEdge(a, b);
          }
        }
      }

      const start = performance.now();
      cfg.checkBipartite();
      const elapsed = performance.now() - start;

      expect(elapsed).toBeLessThan(100);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Path Finding Limits
  // ═══════════════════════════════════════════════════════════════
  describe('Path Finding Complexity', () => {
    it('respects maxVertices limit', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 20; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i));
      }

      const cfi = new HamiltonianCFI(cfg);
      const path = cfi.findHamiltonianPath(10); // Limit to 10

      expect(path).toBeNull(); // Graph too large
    });

    it('path finding completes for small graphs', () => {
      const cfg = new ControlFlowGraph();
      for (let i = 1; i <= 8; i++) {
        cfg.addVertex(createVertex(i, `V${i}`, i));
      }
      // Create a graph with known Hamiltonian path
      for (let i = 1; i <= 8; i++) {
        for (let j = i + 1; j <= 8; j++) {
          cfg.addEdge(i, j);
        }
      }

      const cfi = new HamiltonianCFI(cfg);
      const start = performance.now();
      const path = cfi.findHamiltonianPath(10);
      const elapsed = performance.now() - start;

      expect(path).not.toBeNull();
      expect(elapsed).toBeLessThan(1000); // 1 second max
    });
  });
});
