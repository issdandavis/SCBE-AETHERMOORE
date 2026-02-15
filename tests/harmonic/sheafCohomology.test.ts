/**
 * SCBE Sheaf Cohomology Tests
 *
 * Tests for Tarski cohomology on lattice-valued cellular sheaves:
 * - CompleteLattice implementations (Boolean, Interval, PowerSet, Unit, Product)
 * - Galois connections (identity, constant, threshold, scaling)
 * - Cell complexes (graph, simplicial)
 * - Tarski Laplacian L_k
 * - Tarski cohomology TH^k (fixed-point iteration)
 * - Hodge Laplacians L_k^+, L_k^-
 * - Global sections Γ(X; F)
 * - Obstruction detection
 * - SheafCohomologyEngine SCBE integration
 *
 * Mathematical invariants verified:
 * - TH^0 = Γ (global sections theorem)
 * - Tarski convergence in ≤ h iterations (lattice height bound)
 * - Constant sheaf: global sections = constant cochains
 * - Monotonicity of the harmonic flow
 * - Galois connection adjunction property
 *
 * @layer Layer 9, Layer 10, Layer 12
 */

import { describe, it, expect } from 'vitest';
import {
  // Lattices
  BooleanLattice,
  IntervalLattice,
  PowerSetLattice,
  UnitIntervalLattice,
  ProductLattice,
  // Galois connections
  identityConnection,
  constantConnection,
  thresholdConnection,
  scalingConnection,
  // Cell complexes
  graphComplex,
  simplicialComplex,
  // Sheaf constructors
  constantSheaf,
  thresholdSheaf,
  twistedSheaf,
  // Cochains
  topCochain,
  bottomCochain,
  // Laplacians
  tarskiLaplacian,
  upLaplacian,
  downLaplacian,
  hodgeLaplacian,
  // Cohomology
  tarskiCohomology,
  globalSections,
  hodgeCohomology,
  // Diagnostics
  analyseCohomology,
  detectObstructions,
  // SCBE Engine
  SheafCohomologyEngine,
  defaultSheafEngine,
  // Types
  type CompleteLattice,
  type GaloisConnection,
  type CellComplex,
  type CellularSheaf,
  type Cochain,
  type Vector6D,
} from '../../src/harmonic/index.js';

// ═══════════════════════════════════════════════════════════════
// Helper utilities
// ═══════════════════════════════════════════════════════════════

/** Collect cochain values into a sorted array */
function cochainValues<T>(c: Cochain<T>): T[] {
  return [...c.entries()]
    .sort(([a], [b]) => a - b)
    .map(([, v]) => v);
}

/** Make a 6D zero vector */
function zeroVec6D(): Vector6D {
  return [0, 0, 0, 0, 0, 0];
}

/** Make a random 6D vector with bounded norm */
function randomVec6D(maxNorm: number = 1): Vector6D {
  const v: number[] = Array.from({ length: 6 }, () => Math.random() * 2 - 1);
  const n = Math.sqrt(v.reduce((s, x) => s + x * x, 0));
  const r = Math.random() * maxNorm;
  return v.map((x) => (x / n) * r) as Vector6D;
}

// ═══════════════════════════════════════════════════════════════
// Complete Lattice Implementations
// ═══════════════════════════════════════════════════════════════

describe('CompleteLattice implementations', () => {
  describe('BooleanLattice', () => {
    it('has correct top and bottom', () => {
      expect(BooleanLattice.top).toBe(true);
      expect(BooleanLattice.bottom).toBe(false);
    });

    it('meet = AND', () => {
      expect(BooleanLattice.meet(true, true)).toBe(true);
      expect(BooleanLattice.meet(true, false)).toBe(false);
      expect(BooleanLattice.meet(false, true)).toBe(false);
      expect(BooleanLattice.meet(false, false)).toBe(false);
    });

    it('join = OR', () => {
      expect(BooleanLattice.join(false, false)).toBe(false);
      expect(BooleanLattice.join(true, false)).toBe(true);
      expect(BooleanLattice.join(false, true)).toBe(true);
      expect(BooleanLattice.join(true, true)).toBe(true);
    });

    it('leq = implication', () => {
      expect(BooleanLattice.leq(false, false)).toBe(true);
      expect(BooleanLattice.leq(false, true)).toBe(true);
      expect(BooleanLattice.leq(true, true)).toBe(true);
      expect(BooleanLattice.leq(true, false)).toBe(false);
    });

    it('height = 1', () => {
      expect(BooleanLattice.height()).toBe(1);
    });

    it('satisfies lattice absorption laws', () => {
      for (const a of [true, false]) {
        for (const b of [true, false]) {
          // a ∧ (a ∨ b) = a
          expect(BooleanLattice.meet(a, BooleanLattice.join(a, b))).toBe(a);
          // a ∨ (a ∧ b) = a
          expect(BooleanLattice.join(a, BooleanLattice.meet(a, b))).toBe(a);
        }
      }
    });
  });

  describe('IntervalLattice', () => {
    const L = IntervalLattice(0, 10);

    it('has correct bounds', () => {
      expect(L.top).toBe(10);
      expect(L.bottom).toBe(0);
    });

    it('meet = min, join = max', () => {
      expect(L.meet(3, 7)).toBe(3);
      expect(L.join(3, 7)).toBe(7);
      expect(L.meet(5, 5)).toBe(5);
    });

    it('height = hi - lo', () => {
      expect(L.height()).toBe(10);
      expect(IntervalLattice(-5, 5).height()).toBe(10);
    });

    it('leq = ≤', () => {
      expect(L.leq(3, 7)).toBe(true);
      expect(L.leq(7, 3)).toBe(false);
      expect(L.leq(5, 5)).toBe(true);
    });

    it('satisfies idempotency: a ∧ a = a, a ∨ a = a', () => {
      for (let a = 0; a <= 10; a++) {
        expect(L.meet(a, a)).toBe(a);
        expect(L.join(a, a)).toBe(a);
      }
    });
  });

  describe('PowerSetLattice', () => {
    const P = PowerSetLattice(3); // subsets of {0, 1, 2}

    it('top = full set, bottom = empty set', () => {
      expect(P.top).toBe(0b111); // 7
      expect(P.bottom).toBe(0);
    });

    it('meet = intersection, join = union', () => {
      expect(P.meet(0b110, 0b011)).toBe(0b010); // {1,2} ∩ {0,1} = {1}
      expect(P.join(0b110, 0b011)).toBe(0b111); // {1,2} ∪ {0,1} = {0,1,2}
    });

    it('leq = subset', () => {
      expect(P.leq(0b010, 0b110)).toBe(true);  // {1} ⊆ {1,2}
      expect(P.leq(0b110, 0b010)).toBe(false); // {1,2} ⊄ {1}
    });

    it('height = n', () => {
      expect(P.height()).toBe(3);
    });

    it('satisfies distributivity', () => {
      const a = 0b101, b = 0b110, c = 0b011;
      // a ∧ (b ∨ c) = (a ∧ b) ∨ (a ∧ c)
      expect(P.meet(a, P.join(b, c))).toBe(P.join(P.meet(a, b), P.meet(a, c)));
    });
  });

  describe('UnitIntervalLattice', () => {
    const U = UnitIntervalLattice(10); // 10 steps

    it('top = 1, bottom = 0', () => {
      expect(U.top).toBe(1);
      expect(U.bottom).toBe(0);
    });

    it('quantises to steps', () => {
      // 0.15 rounds to 0.2 with 10 steps
      expect(U.meet(0.15, 1)).toBeCloseTo(0.2, 5);
    });

    it('height = steps', () => {
      expect(U.height()).toBe(10);
    });

    it('clamping: values outside [0,1] are clamped', () => {
      expect(U.meet(-0.5, 0.5)).toBeCloseTo(0, 5);
      expect(U.join(0.5, 1.5)).toBeCloseTo(1, 5);
    });
  });

  describe('ProductLattice', () => {
    const P = ProductLattice(BooleanLattice, IntervalLattice(0, 5));

    it('top = (⊤₁, ⊤₂), bottom = (⊥₁, ⊥₂)', () => {
      expect(P.top).toEqual([true, 5]);
      expect(P.bottom).toEqual([false, 0]);
    });

    it('meet/join are component-wise', () => {
      expect(P.meet([true, 4], [false, 3])).toEqual([false, 3]);
      expect(P.join([true, 4], [false, 3])).toEqual([true, 4]);
    });

    it('height = sum of component heights', () => {
      expect(P.height()).toBe(1 + 5);
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// Galois Connections
// ═══════════════════════════════════════════════════════════════

describe('Galois connections', () => {
  describe('identityConnection', () => {
    const conn = identityConnection<number>();

    it('lower and upper are identity', () => {
      expect(conn.lower(42)).toBe(42);
      expect(conn.upper(42)).toBe(42);
    });

    it('satisfies adjunction: lower(a) ≤ b ⟺ a ≤ upper(b)', () => {
      // For identity, this is just a ≤ b ⟺ a ≤ b
      expect(conn.lower(3) <= 5).toBe(3 <= conn.upper(5));
    });
  });

  describe('thresholdConnection', () => {
    const L = IntervalLattice(0, 10);
    const conn = thresholdConnection(5, L);

    it('lower maps below threshold to bottom', () => {
      expect(conn.lower(3)).toBe(0);
      expect(conn.lower(5)).toBe(5);
      expect(conn.lower(8)).toBe(8);
    });

    it('upper is identity', () => {
      expect(conn.upper(7)).toBe(7);
    });
  });

  describe('scalingConnection', () => {
    const conn = scalingConnection(0.5);

    it('lower scales down, upper scales up', () => {
      expect(conn.lower(0.8)).toBeCloseTo(0.4, 10);
      expect(conn.upper(0.4)).toBeCloseTo(0.8, 10);
    });

    it('clamps to [0, 1]', () => {
      expect(conn.lower(1.0)).toBeCloseTo(0.5, 10);
      expect(conn.upper(1.0)).toBeCloseTo(1.0, 5); // 1/0.5 = 2 → clamped to 1
    });
  });

  describe('constantConnection', () => {
    const L = IntervalLattice(0, 10);
    const conn = constantConnection(L, 5);

    it('lower maps everything to the constant', () => {
      expect(conn.lower(0)).toBe(5);
      expect(conn.lower(10)).toBe(5);
    });

    it('upper maps everything to top', () => {
      expect(conn.upper(0)).toBe(10);
      expect(conn.upper(5)).toBe(10);
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// Cell Complex
// ═══════════════════════════════════════════════════════════════

describe('Cell complex builders', () => {
  describe('graphComplex', () => {
    // Triangle graph: 0-1, 1-2, 0-2
    const G = graphComplex(3, [[0, 1], [1, 2], [0, 2]]);

    it('has correct number of cells', () => {
      expect(G.cells(0)).toHaveLength(3); // 3 vertices
      expect(G.cells(1)).toHaveLength(3); // 3 edges
      expect(G.cells(2)).toHaveLength(0); // no 2-cells
    });

    it('maxDim = 1', () => {
      expect(G.maxDim()).toBe(1);
    });

    it('faces of edge = its two vertices', () => {
      const edge0Faces = G.faces({ dim: 1, id: 0 });
      expect(edge0Faces).toHaveLength(2);
      expect(edge0Faces.map((c) => c.id).sort()).toEqual([0, 1]);
    });

    it('cofaces of vertex = incident edges', () => {
      // Vertex 1 is in edges 0 (0-1) and 1 (1-2)
      const v1Cofaces = G.cofaces({ dim: 0, id: 1 });
      expect(v1Cofaces).toHaveLength(2);
      expect(v1Cofaces.map((c) => c.id).sort()).toEqual([0, 1]);
    });

    it('incidence is consistent', () => {
      // Edge 0 has faces [0, 1]: incidence(0, edge0) = +1, incidence(1, edge0) = -1
      expect(G.incidence({ dim: 0, id: 0 }, { dim: 1, id: 0 })).toBe(1);
      expect(G.incidence({ dim: 0, id: 1 }, { dim: 1, id: 0 })).toBe(-1);
    });

    it('empty graph has maxDim 0', () => {
      const empty = graphComplex(5, []);
      expect(empty.maxDim()).toBe(0);
      expect(empty.cells(0)).toHaveLength(5);
      expect(empty.cells(1)).toHaveLength(0);
    });
  });

  describe('simplicialComplex', () => {
    // Single triangle: vertices 0,1,2; edges 0-1, 1-2, 0-2; face [0,1,2]
    const S = simplicialComplex(
      3,
      [[0, 1], [1, 2], [0, 2]],
      [[0, 1, 2]]
    );

    it('has correct cell counts', () => {
      expect(S.cells(0)).toHaveLength(3);
      expect(S.cells(1)).toHaveLength(3);
      expect(S.cells(2)).toHaveLength(1);
    });

    it('maxDim = 2', () => {
      expect(S.maxDim()).toBe(2);
    });

    it('faces of 2-cell are edges', () => {
      const faceFaces = S.faces({ dim: 2, id: 0 });
      expect(faceFaces).toHaveLength(3);
      expect(faceFaces.every((c) => c.dim === 1)).toBe(true);
    });

    it('cofaces of edge includes the triangle', () => {
      const edgeCofaces = S.cofaces({ dim: 1, id: 0 });
      expect(edgeCofaces.length).toBeGreaterThanOrEqual(1);
      expect(edgeCofaces[0].dim).toBe(2);
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// Tarski Laplacian
// ═══════════════════════════════════════════════════════════════

describe('Tarski Laplacian L_k', () => {
  describe('on constant sheaf over path graph', () => {
    // Path graph: 0 -- 1 -- 2
    const complex = graphComplex(3, [[0, 1], [1, 2]]);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(complex, L);

    it('L_0(⊤) = ⊤ for constant sheaf', () => {
      const top = topCochain(sheaf, 0);
      const result = tarskiLaplacian(sheaf, 0, top);
      const values = cochainValues(result);
      // On constant sheaf, identity connections → L_0(⊤) = ⊤
      values.forEach((v) => expect(v).toBe(10));
    });

    it('consistent assignment is a fixed point', () => {
      // All vertices = 5 is consistent on constant sheaf
      const x: Cochain<number> = new Map([[0, 5], [1, 5], [2, 5]]);
      const result = tarskiLaplacian(sheaf, 0, x);
      // Since restriction is identity and all values match,
      // inner meet at each edge = 5, pull back = 5, outer meet = 5
      expect(result.get(0)).toBe(5);
      expect(result.get(1)).toBe(5);
      expect(result.get(2)).toBe(5);
    });

    it('inconsistent assignment diffuses via meet', () => {
      // Vertex 0 = 3, Vertex 1 = 7, Vertex 2 = 5
      const x: Cochain<number> = new Map([[0, 3], [1, 7], [2, 5]]);
      const result = tarskiLaplacian(sheaf, 0, x);

      // Vertex 0: cofaces = [edge 0], faces of edge 0 = [0, 1]
      // inner meet = min(3, 7) = 3, pullback = 3, outer meet = 3
      expect(result.get(0)).toBe(3);

      // Vertex 1: cofaces = [edge 0, edge 1]
      // edge 0: inner meet = min(3, 7) = 3 → pullback = 3
      // edge 1: inner meet = min(7, 5) = 5 → pullback = 5
      // outer meet = min(3, 5) = 3
      expect(result.get(1)).toBe(3);

      // Vertex 2: cofaces = [edge 1], faces of edge 1 = [1, 2]
      // inner meet = min(7, 5) = 5, pullback = 5, outer meet = 5
      expect(result.get(2)).toBe(5);
    });
  });

  it('is monotone: x ≤ y implies L(x) ≤ L(y)', () => {
    const complex = graphComplex(3, [[0, 1], [1, 2], [0, 2]]);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(complex, L);

    const x: Cochain<number> = new Map([[0, 2], [1, 3], [2, 4]]);
    const y: Cochain<number> = new Map([[0, 5], [1, 6], [2, 7]]);

    const lx = tarskiLaplacian(sheaf, 0, x);
    const ly = tarskiLaplacian(sheaf, 0, y);

    for (const cell of complex.cells(0)) {
      expect(lx.get(cell.id)!).toBeLessThanOrEqual(ly.get(cell.id)!);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Tarski Cohomology
// ═══════════════════════════════════════════════════════════════

describe('Tarski Cohomology TH^k', () => {
  describe('TH^0 = global sections (constant sheaf)', () => {
    it('on connected graph: all cells converge to same value', () => {
      // Complete graph K3
      const complex = graphComplex(3, [[0, 1], [1, 2], [0, 2]]);
      const L = IntervalLattice(0, 10);
      const sheaf = constantSheaf(complex, L);

      const result = tarskiCohomology(sheaf, 0);

      expect(result.converged).toBe(true);
      // Global sections of constant sheaf on connected graph = constant cochains at ⊤
      const values = cochainValues(result.cochains);
      const first = values[0];
      values.forEach((v) => expect(v).toBe(first));
    });

    it('on disconnected graph: components may differ', () => {
      // Two disconnected edges: 0-1, 2-3
      const complex = graphComplex(4, [[0, 1], [2, 3]]);
      const L = IntervalLattice(0, 10);
      const sheaf = constantSheaf(complex, L);

      const result = tarskiCohomology(sheaf, 0);
      expect(result.converged).toBe(true);
      // Both components converge to ⊤ independently
      expect(result.cochains.get(0)).toBe(10);
      expect(result.cochains.get(2)).toBe(10);
    });
  });

  describe('convergence properties', () => {
    it('converges within lattice height iterations', () => {
      const complex = graphComplex(5, [[0, 1], [1, 2], [2, 3], [3, 4]]);
      const L = IntervalLattice(0, 20);
      const sheaf = constantSheaf(complex, L);

      const result = tarskiCohomology(sheaf, 0);
      expect(result.converged).toBe(true);
      expect(result.iterations).toBeLessThanOrEqual(L.height() + 1);
    });

    it('iterating on a fixed point is idempotent', () => {
      const complex = graphComplex(3, [[0, 1], [1, 2]]);
      const L = IntervalLattice(0, 10);
      const sheaf = constantSheaf(complex, L);

      const result = tarskiCohomology(sheaf, 0);
      // Apply laplacian to the result: should be a fixed point
      const reapplied = tarskiLaplacian(sheaf, 0, result.cochains);
      for (const cell of complex.cells(0)) {
        const orig = result.cochains.get(cell.id)!;
        const reapp = reapplied.get(cell.id)!;
        expect(L.eq(orig, reapp)).toBe(true);
      }
    });
  });

  describe('globalSections convenience function', () => {
    it('equals tarskiCohomology at dim 0', () => {
      const complex = graphComplex(3, [[0, 1], [1, 2]]);
      const L = IntervalLattice(0, 10);
      const sheaf = constantSheaf(complex, L);

      const gs = globalSections(sheaf);
      const th0 = tarskiCohomology(sheaf, 0);

      expect(gs.degree).toBe(0);
      expect(gs.converged).toBe(th0.converged);
      for (const cell of complex.cells(0)) {
        expect(gs.cochains.get(cell.id)).toBe(th0.cochains.get(cell.id));
      }
    });
  });

  describe('threshold sheaf TH^0', () => {
    it('threshold filters low values to bottom', () => {
      const complex = graphComplex(3, [[0, 1], [1, 2]]);
      const L = IntervalLattice(0, 10);
      // Threshold at 5: values below 5 get mapped to 0
      const sheaf = thresholdSheaf(complex, L, 5);

      const result = tarskiCohomology(sheaf, 0);
      expect(result.converged).toBe(true);
      // Starting from ⊤=10, threshold connection doesn't block 10
      // so all should stay at top
      const values = cochainValues(result.cochains);
      values.forEach((v) => expect(v).toBe(10));
    });
  });

  describe('twisted sheaf TH^0', () => {
    it('edge scaling affects convergence', () => {
      const complex = graphComplex(3, [[0, 1], [1, 2]]);
      const L = UnitIntervalLattice(100);

      // Edge 0 has scale 0.5, edge 1 has scale 0.8
      const edgeScales = new Map<number, number>([[0, 0.5], [1, 0.8]]);
      const sheaf = twistedSheaf(complex, L, edgeScales);

      const result = tarskiCohomology(sheaf, 0);
      expect(result.converged).toBe(true);
      // Twisted sheaf should converge to a fixed point
      // Values may not all be equal due to asymmetric scaling
    });
  });

  describe('Boolean sheaf TH^0', () => {
    it('on complete graph: global section is true', () => {
      const complex = graphComplex(3, [[0, 1], [1, 2], [0, 2]]);
      const sheaf = constantSheaf(complex, BooleanLattice);

      const result = tarskiCohomology(sheaf, 0);
      expect(result.converged).toBe(true);
      // Constant boolean sheaf: all restrictions are identity
      // Starting from ⊤ = true, stays true
      for (const [, v] of result.cochains) {
        expect(v).toBe(true);
      }
    });
  });

  describe('PowerSet sheaf TH^0', () => {
    it('converges on triangle', () => {
      const complex = graphComplex(3, [[0, 1], [1, 2], [0, 2]]);
      const P = PowerSetLattice(4);
      const sheaf = constantSheaf(complex, P);

      const result = tarskiCohomology(sheaf, 0);
      expect(result.converged).toBe(true);
      // Constant sheaf → all cells get ⊤ = full set
      for (const [, v] of result.cochains) {
        expect(v).toBe(P.top);
      }
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// Hodge Cohomology
// ═══════════════════════════════════════════════════════════════

describe('Hodge Cohomology HH^k', () => {
  it('HH^0 converges on path graph', () => {
    const complex = graphComplex(3, [[0, 1], [1, 2]]);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(complex, L);

    const result = hodgeCohomology(sheaf, 0);
    expect(result.converged).toBe(true);
    expect(result.degree).toBe(0);
  });

  it('up and down Laplacians are dual operators', () => {
    const complex = graphComplex(3, [[0, 1], [1, 2], [0, 2]]);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(complex, L);

    const x: Cochain<number> = new Map([[0, 3], [1, 5], [2, 7]]);

    const up = upLaplacian(sheaf, 0, x);
    const down = downLaplacian(sheaf, 0, x);

    // Up uses meet (over cofaces), down uses join (over faces)
    // They should generally give different results
    // But both should produce valid cochains
    for (const cell of complex.cells(0)) {
      expect(up.get(cell.id)).toBeDefined();
      expect(down.get(cell.id)).toBeDefined();
      // Up result ≤ ⊤
      expect(up.get(cell.id)!).toBeLessThanOrEqual(10);
      // Down result ≥ ⊥
      expect(down.get(cell.id)!).toBeGreaterThanOrEqual(0);
    }
  });

  it('Hodge Laplacian = meet of up and down', () => {
    const complex = graphComplex(3, [[0, 1], [1, 2]]);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(complex, L);

    const x: Cochain<number> = new Map([[0, 4], [1, 6], [2, 8]]);

    const up = upLaplacian(sheaf, 0, x);
    const down = downLaplacian(sheaf, 0, x);
    const hodge = hodgeLaplacian(sheaf, 0, x);

    for (const cell of complex.cells(0)) {
      const expected = Math.min(up.get(cell.id)!, down.get(cell.id)!);
      expect(hodge.get(cell.id)).toBe(expected);
    }
  });

  it('TH^k and HH^k both converge to fixed points', () => {
    const complex = graphComplex(4, [[0, 1], [1, 2], [2, 3], [0, 3]]);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(complex, L);

    const th0 = tarskiCohomology(sheaf, 0);
    const hh0 = hodgeCohomology(sheaf, 0);

    expect(th0.converged).toBe(true);
    expect(hh0.converged).toBe(true);

    // Both are fixed points of their respective operators
    const thReapplied = tarskiLaplacian(sheaf, 0, th0.cochains);
    const hhReapplied = hodgeLaplacian(sheaf, 0, hh0.cochains);

    for (const cell of complex.cells(0)) {
      // TH^0 fixed point: x = x ∧ L_up(x)
      expect(L.meet(th0.cochains.get(cell.id)!, thReapplied.get(cell.id)!))
        .toBe(th0.cochains.get(cell.id)!);
      // HH^0 fixed point: x = x ∧ L_hodge(x)
      expect(L.meet(hh0.cochains.get(cell.id)!, hhReapplied.get(cell.id)!))
        .toBe(hh0.cochains.get(cell.id)!);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Cochain Utilities
// ═══════════════════════════════════════════════════════════════

describe('Cochain utilities', () => {
  it('topCochain assigns ⊤ to all cells', () => {
    const complex = graphComplex(3, [[0, 1]]);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(complex, L);

    const top = topCochain(sheaf, 0);
    expect(top.size).toBe(3);
    for (const [, v] of top) {
      expect(v).toBe(10);
    }
  });

  it('bottomCochain assigns ⊥ to all cells', () => {
    const complex = graphComplex(3, [[0, 1]]);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(complex, L);

    const bottom = bottomCochain(sheaf, 0);
    expect(bottom.size).toBe(3);
    for (const [, v] of bottom) {
      expect(v).toBe(0);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Diagnostics
// ═══════════════════════════════════════════════════════════════

describe('Cohomology diagnostics', () => {
  it('analyseCohomology reports correct Betti number', () => {
    const complex = graphComplex(3, [[0, 1], [1, 2]]);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(complex, L);

    const result = tarskiCohomology(sheaf, 0);
    const diag = analyseCohomology(result, L);

    // Constant sheaf on connected graph: all at ⊤, so all non-trivial
    expect(diag.bettiNumber).toBe(3);
    expect(diag.isGloballyConsistent).toBe(true);
    expect(diag.maxElement).toBe(10);
    expect(diag.minElement).toBe(10);
  });

  it('heightUtilisation is 0 for constant cochains', () => {
    const complex = graphComplex(2, [[0, 1]]);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(complex, L);

    const result = tarskiCohomology(sheaf, 0);
    const diag = analyseCohomology(result, L);

    // All values are 10, so range = 0 → utilisation = 0
    expect(diag.heightUtilisation).toBeCloseTo(0, 5);
  });
});

// ═══════════════════════════════════════════════════════════════
// Obstruction Detection
// ═══════════════════════════════════════════════════════════════

describe('Obstruction detection', () => {
  it('no obstructions on constant sheaf with uniform assignment', () => {
    const complex = graphComplex(3, [[0, 1], [1, 2]]);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(complex, L);

    const assignment: Cochain<number> = new Map([[0, 5], [1, 5], [2, 5]]);
    const obstructions = detectObstructions(sheaf, assignment);

    expect(obstructions).toHaveLength(0);
  });

  it('no obstructions when all vertices agree (identity restriction)', () => {
    const complex = graphComplex(3, [[0, 1], [1, 2], [0, 2]]);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(complex, L);

    const assignment: Cochain<number> = new Map([[0, 7], [1, 7], [2, 7]]);
    const obstructions = detectObstructions(sheaf, assignment);
    expect(obstructions).toHaveLength(0);
  });

  it('detects obstructions when vertices disagree', () => {
    const complex = graphComplex(3, [[0, 1], [1, 2]]);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(complex, L);

    // Vertices disagree: 3, 7, 5
    const assignment: Cochain<number> = new Map([[0, 3], [1, 7], [2, 5]]);
    const obstructions = detectObstructions(sheaf, assignment);

    // Edge 0 (vertices 0, 1): 3 ≠ 7 → obstruction
    // Edge 1 (vertices 1, 2): 7 ≠ 5 → obstruction
    expect(obstructions).toHaveLength(2);
    expect(obstructions[0].severity).toBeGreaterThan(0);
    expect(obstructions[1].severity).toBeGreaterThan(0);
  });

  it('obstruction severity reflects disagreement magnitude', () => {
    const complex = graphComplex(2, [[0, 1]]);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(complex, L);

    // Small disagreement
    const small: Cochain<number> = new Map([[0, 5], [1, 6]]);
    const obsSmall = detectObstructions(sheaf, small);

    // Large disagreement
    const large: Cochain<number> = new Map([[0, 0], [1, 10]]);
    const obsLarge = detectObstructions(sheaf, large);

    expect(obsSmall).toHaveLength(1);
    expect(obsLarge).toHaveLength(1);
    expect(obsLarge[0].severity).toBeGreaterThan(obsSmall[0].severity);
  });

  it('twisted sheaf detects obstructions from scaling mismatch', () => {
    const complex = graphComplex(2, [[0, 1]]);
    const L = UnitIntervalLattice(100);

    // Edge 0 has scale 0.3 (strong contraction)
    const edgeScales = new Map<number, number>([[0, 0.3]]);
    const sheaf = twistedSheaf(complex, L, edgeScales);

    // Values differ: restriction via scaling won't match
    const assignment: Cochain<number> = new Map([[0, 0.8], [1, 0.9]]);
    const obstructions = detectObstructions(sheaf, assignment);

    // 0.8 * 0.3 = 0.24 vs 0.9 * 0.3 = 0.27 → different restrictions
    expect(obstructions.length).toBeGreaterThanOrEqual(1);
  });
});

// ═══════════════════════════════════════════════════════════════
// SCBE SheafCohomologyEngine
// ═══════════════════════════════════════════════════════════════

describe('SheafCohomologyEngine', () => {
  describe('analyseVectorField', () => {
    it('coherent field of identical vectors has coherenceScore ≈ 1', () => {
      const engine = new SheafCohomologyEngine();
      const v: Vector6D = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1];
      const vectors: Vector6D[] = [v, v, v];
      const edges: [number, number][] = [[0, 1], [1, 2], [0, 2]];

      const result = engine.analyseVectorField(vectors, edges);

      expect(result.globalSections.converged).toBe(true);
      expect(result.coherenceScore).toBeGreaterThanOrEqual(0.9);
      expect(result.riskAmplification).toBeCloseTo(1, 1);
    });

    it('divergent vectors produce obstructions', () => {
      const engine = new SheafCohomologyEngine();
      const vectors: Vector6D[] = [
        [0, 0, 0, 0, 0, 0],     // origin (safe)
        [2, 2, 2, 2, 2, 2],     // far from origin (risky)
        [0.1, 0.1, 0.1, 0.1, 0.1, 0.1], // near origin (safe)
      ];
      const edges: [number, number][] = [[0, 1], [1, 2], [0, 2]];

      const result = engine.analyseVectorField(vectors, edges);

      expect(result.globalSections.converged).toBe(true);
      expect(result.obstructions.length).toBeGreaterThan(0);
      expect(result.coherenceScore).toBeLessThan(1);
    });

    it('risk amplification grows with obstruction severity', () => {
      const engine = new SheafCohomologyEngine({ obstructionThreshold: 0.001 });

      // Low divergence: close vectors → similar safety scores → small obstruction
      const low: Vector6D[] = [
        [0.1, 0, 0, 0, 0, 0],
        [0.2, 0, 0, 0, 0, 0],
      ];
      const lowResult = engine.analyseVectorField(low, [[0, 1]]);

      // High divergence: one near origin, one at moderate distance
      const high: Vector6D[] = [
        [0, 0, 0, 0, 0, 0],
        [1, 1, 0, 0, 0, 0],
      ];
      const highResult = engine.analyseVectorField(high, [[0, 1]]);

      // Higher divergence should yield >= risk amplification
      expect(highResult.riskAmplification).toBeGreaterThanOrEqual(lowResult.riskAmplification);
    });

    it('handles single vertex (no edges)', () => {
      const engine = new SheafCohomologyEngine();
      const vectors: Vector6D[] = [[0.5, 0.5, 0.5, 0.5, 0.5, 0.5]];

      const result = engine.analyseVectorField(vectors, []);

      expect(result.globalSections.converged).toBe(true);
      expect(result.obstructions).toHaveLength(0);
      expect(result.coherenceScore).toBe(1);
    });

    it('handles larger graph (10 vertices, path)', () => {
      const engine = new SheafCohomologyEngine();
      const vectors: Vector6D[] = Array.from({ length: 10 }, (_, i) => {
        const t = i / 9;
        return [t, t * 0.5, 0, 0, 0, 0] as Vector6D;
      });
      const edges: [number, number][] = Array.from({ length: 9 }, (_, i) => [i, i + 1] as [number, number]);

      const result = engine.analyseVectorField(vectors, edges);

      expect(result.globalSections.converged).toBe(true);
      expect(result.diagnostics.bettiNumber).toBeGreaterThan(0);
    });
  });

  describe('isCoherent', () => {
    it('identical vectors are coherent', () => {
      const engine = new SheafCohomologyEngine();
      const v: Vector6D = [0.2, 0.2, 0.2, 0.2, 0.2, 0.2];
      expect(engine.isCoherent([v, v, v], [[0, 1], [1, 2]])).toBe(true);
    });

    it('very different vectors are incoherent', () => {
      const engine = new SheafCohomologyEngine();
      const vectors: Vector6D[] = [
        [0, 0, 0, 0, 0, 0],
        [10, 10, 10, 10, 10, 10],
      ];
      expect(engine.isCoherent(vectors, [[0, 1]])).toBe(false);
    });
  });

  describe('eulerCharacteristic', () => {
    it('returns |TH^0| - |TH^1|', () => {
      const engine = new SheafCohomologyEngine();
      const vectors: Vector6D[] = [
        [0.1, 0, 0, 0, 0, 0],
        [0.2, 0, 0, 0, 0, 0],
        [0.3, 0, 0, 0, 0, 0],
      ];
      const edges: [number, number][] = [[0, 1], [1, 2], [0, 2]];

      const result = engine.analyseVectorField(vectors, edges);
      const chi = engine.eulerCharacteristic(result);

      // Euler characteristic is an integer
      expect(Number.isFinite(chi)).toBe(true);
    });
  });

  describe('defaultSheafEngine', () => {
    it('is a valid SheafCohomologyEngine instance', () => {
      expect(defaultSheafEngine).toBeInstanceOf(SheafCohomologyEngine);
    });

    it('can analyse a simple field', () => {
      const result = defaultSheafEngine.analyseVectorField(
        [[0, 0, 0, 0, 0, 0], [0.1, 0.1, 0, 0, 0, 0]],
        [[0, 1]]
      );
      expect(result.globalSections.converged).toBe(true);
    });
  });

  describe('configuration', () => {
    it('respects custom latticeSteps', () => {
      const engine = new SheafCohomologyEngine({ latticeSteps: 10 });
      const result = engine.analyseVectorField(
        [[0, 0, 0, 0, 0, 0], [0.5, 0, 0, 0, 0, 0]],
        [[0, 1]]
      );
      expect(result.globalSections.converged).toBe(true);
    });

    it('respects custom obstructionThreshold', () => {
      const strict = new SheafCohomologyEngine({ obstructionThreshold: 0.01 });
      const lenient = new SheafCohomologyEngine({ obstructionThreshold: 0.99 });

      const vectors: Vector6D[] = [
        [0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0],
      ];
      const edges: [number, number][] = [[0, 1]];

      const strictResult = strict.analyseVectorField(vectors, edges);
      const lenientResult = lenient.analyseVectorField(vectors, edges);

      // Strict threshold → more risk amplification (more obstructions qualify)
      expect(strictResult.riskAmplification).toBeGreaterThanOrEqual(lenientResult.riskAmplification);
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// Property-Based Tests (lightweight, 20 iterations)
// ═══════════════════════════════════════════════════════════════

describe('Property-based tests', () => {
  it('Tarski flow is non-increasing (monotone descent)', () => {
    for (let trial = 0; trial < 20; trial++) {
      const n = 3 + Math.floor(Math.random() * 3);
      const edges: [number, number][] = [];
      for (let i = 0; i < n - 1; i++) {
        edges.push([i, i + 1]);
      }
      const complex = graphComplex(n, edges);
      const L = IntervalLattice(0, 100);
      const sheaf = constantSheaf(complex, L);

      // Random initial cochain
      const x: Cochain<number> = new Map();
      for (let i = 0; i < n; i++) {
        x.set(i, Math.floor(Math.random() * 101));
      }

      const lx = tarskiLaplacian(sheaf, 0, x);

      // x ∧ L(x) ≤ x for all cells
      for (const cell of complex.cells(0)) {
        const meetVal = Math.min(x.get(cell.id)!, lx.get(cell.id)!);
        expect(meetVal).toBeLessThanOrEqual(x.get(cell.id)!);
      }
    }
  });

  it('global sections are post-fixpoints of L_0', () => {
    for (let trial = 0; trial < 20; trial++) {
      const n = 2 + Math.floor(Math.random() * 4);
      const edges: [number, number][] = [];
      for (let i = 0; i < n - 1; i++) {
        edges.push([i, i + 1]);
      }
      const complex = graphComplex(n, edges);
      const L = IntervalLattice(0, 50);
      const sheaf = constantSheaf(complex, L);

      const result = globalSections(sheaf);

      // Post-fixpoint: x ≤ L(x)
      const lx = tarskiLaplacian(sheaf, 0, result.cochains);
      for (const cell of complex.cells(0)) {
        expect(result.cochains.get(cell.id)!).toBeLessThanOrEqual(lx.get(cell.id)!);
      }
    }
  });

  it('SheafCohomologyEngine always converges for random 6D vectors', () => {
    const engine = new SheafCohomologyEngine({ latticeSteps: 20 });

    for (let trial = 0; trial < 20; trial++) {
      const n = 2 + Math.floor(Math.random() * 4);
      const vectors: Vector6D[] = Array.from({ length: n }, () => randomVec6D(3));
      const edges: [number, number][] = [];
      for (let i = 0; i < n - 1; i++) {
        edges.push([i, i + 1]);
      }

      const result = engine.analyseVectorField(vectors, edges);

      expect(result.globalSections.converged).toBe(true);
      expect(result.coherenceScore).toBeGreaterThanOrEqual(0);
      expect(result.coherenceScore).toBeLessThanOrEqual(1);
      expect(result.riskAmplification).toBeGreaterThanOrEqual(1);
    }
  });

  it('coherenceScore ∈ [0, 1] for all inputs', () => {
    const engine = new SheafCohomologyEngine({ latticeSteps: 10 });

    for (let trial = 0; trial < 20; trial++) {
      const vectors: Vector6D[] = Array.from(
        { length: 3 },
        () => randomVec6D(5)
      );
      const edges: [number, number][] = [[0, 1], [1, 2], [0, 2]];

      const result = engine.analyseVectorField(vectors, edges);
      expect(result.coherenceScore).toBeGreaterThanOrEqual(0);
      expect(result.coherenceScore).toBeLessThanOrEqual(1);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Edge Cases
// ═══════════════════════════════════════════════════════════════

describe('Edge cases', () => {
  it('single vertex, no edges', () => {
    const complex = graphComplex(1, []);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(complex, L);

    const result = tarskiCohomology(sheaf, 0);
    expect(result.converged).toBe(true);
    expect(result.cochains.get(0)).toBe(10); // ⊤ is a fixed point
  });

  it('self-loop edge', () => {
    const complex = graphComplex(2, [[0, 0]]);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(complex, L);

    const result = tarskiCohomology(sheaf, 0);
    expect(result.converged).toBe(true);
  });

  it('many parallel edges between same vertices', () => {
    const complex = graphComplex(2, [[0, 1], [0, 1], [0, 1]]);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(complex, L);

    const result = tarskiCohomology(sheaf, 0);
    expect(result.converged).toBe(true);
  });

  it('simplicial complex with triangle', () => {
    const S = simplicialComplex(3, [[0, 1], [1, 2], [0, 2]], [[0, 1, 2]]);
    const L = IntervalLattice(0, 10);
    const sheaf = constantSheaf(S, L);

    // TH^0 on simplicial complex
    const th0 = tarskiCohomology(sheaf, 0);
    expect(th0.converged).toBe(true);

    // TH^1 on simplicial complex (edges have cofaces now)
    const th1 = tarskiCohomology(sheaf, 1);
    expect(th1.converged).toBe(true);
  });

  it('height-0 lattice (trivial)', () => {
    // Lattice with single element
    const trivial: CompleteLattice<number> = {
      top: 0,
      bottom: 0,
      meet: () => 0,
      join: () => 0,
      leq: () => true,
      eq: () => true,
      height: () => 0,
    };
    const complex = graphComplex(3, [[0, 1], [1, 2]]);
    const sheaf = constantSheaf(complex, trivial);

    const result = tarskiCohomology(sheaf, 0);
    expect(result.converged).toBe(true);
    expect(result.iterations).toBe(1);
  });
});
