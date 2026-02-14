/**
 * @file sheafCohomology.unit.test.ts
 * @module tests/L2-unit
 * @layer Layer 13, Layer 9-10
 * @component Tarski Sheaf Cohomology Tests
 * @version 1.0.0
 *
 * Tests for cellular sheaf cohomology with Tarski Laplacian, harmonic flow,
 * and consensus analysis over agent network lattices.
 */

import { describe, it, expect } from 'vitest';
import {
  // Lattices
  RiskLattice,
  GovernanceLattice,
  DimensionalLattice,
  createUnitIntervalLattice,
  // Cell complex
  buildComplex,
  // Sheaf
  constantSheaf,
  customSheaf,
  galoisFromMaps,
  identityConnection,
  // Cochains
  cochain0,
  constantCochain0,
  topCochain0,
  // Operators
  tarskiLaplacian0,
  harmonicStep0,
  harmonicFlow,
  tarskiCohomology0,
  pseudoCoboundary,
  tarskiLaplacian1,
  tarskiCohomology1,
  // Consensus
  analyzeConsensus,
  riskConsensusSheaf,
  governanceConsensusSheaf,
  riskConsensus,
  consensusSummary,
  // Types
  type RiskDecision,
  type GovernanceTier,
  type DimensionalState,
  type CompleteLattice,
} from '../../src/harmonic/sheafCohomology.js';

// =============================================================================
// LATTICE TESTS
// =============================================================================

describe('RiskLattice', () => {
  it('has correct element order', () => {
    expect(RiskLattice.elements).toEqual(['ALLOW', 'QUARANTINE', 'ESCALATE', 'DENY']);
  });

  it('has correct top and bottom', () => {
    expect(RiskLattice.top).toBe('DENY');
    expect(RiskLattice.bot).toBe('ALLOW');
  });

  it('leq respects order', () => {
    expect(RiskLattice.leq('ALLOW', 'DENY')).toBe(true);
    expect(RiskLattice.leq('ALLOW', 'ALLOW')).toBe(true);
    expect(RiskLattice.leq('DENY', 'ALLOW')).toBe(false);
    expect(RiskLattice.leq('QUARANTINE', 'ESCALATE')).toBe(true);
    expect(RiskLattice.leq('ESCALATE', 'QUARANTINE')).toBe(false);
  });

  it('meet returns greatest lower bound', () => {
    expect(RiskLattice.meet('ALLOW', 'DENY')).toBe('ALLOW');
    expect(RiskLattice.meet('QUARANTINE', 'ESCALATE')).toBe('QUARANTINE');
    expect(RiskLattice.meet('DENY', 'DENY')).toBe('DENY');
    expect(RiskLattice.meet('ALLOW', 'ALLOW')).toBe('ALLOW');
  });

  it('join returns least upper bound', () => {
    expect(RiskLattice.join('ALLOW', 'DENY')).toBe('DENY');
    expect(RiskLattice.join('QUARANTINE', 'ESCALATE')).toBe('ESCALATE');
    expect(RiskLattice.join('ALLOW', 'ALLOW')).toBe('ALLOW');
  });

  it('meetAll returns meet of array', () => {
    expect(RiskLattice.meetAll(['DENY', 'ESCALATE', 'QUARANTINE'])).toBe('QUARANTINE');
    expect(RiskLattice.meetAll(['DENY', 'DENY'])).toBe('DENY');
    expect(RiskLattice.meetAll([])).toBe('DENY'); // empty meet = top
  });

  it('joinAll returns join of array', () => {
    expect(RiskLattice.joinAll(['ALLOW', 'QUARANTINE', 'ESCALATE'])).toBe('ESCALATE');
    expect(RiskLattice.joinAll([])).toBe('ALLOW'); // empty join = bot
  });

  it('eq checks equality', () => {
    expect(RiskLattice.eq('ALLOW', 'ALLOW')).toBe(true);
    expect(RiskLattice.eq('ALLOW', 'DENY')).toBe(false);
  });
});

describe('GovernanceLattice', () => {
  it('has 6 elements in ascending order', () => {
    expect(GovernanceLattice.elements).toEqual(['KO', 'AV', 'RU', 'CA', 'UM', 'DR']);
  });

  it('KO is bottom, DR is top', () => {
    expect(GovernanceLattice.bot).toBe('KO');
    expect(GovernanceLattice.top).toBe('DR');
  });

  it('leq: KO ≤ everything', () => {
    for (const g of GovernanceLattice.elements) {
      expect(GovernanceLattice.leq('KO', g)).toBe(true);
    }
  });

  it('leq: nothing ≤ KO except KO', () => {
    for (const g of GovernanceLattice.elements) {
      if (g === 'KO') continue;
      expect(GovernanceLattice.leq(g, 'KO')).toBe(false);
    }
  });

  it('meet of non-comparable returns min', () => {
    expect(GovernanceLattice.meet('RU', 'CA')).toBe('RU');
    expect(GovernanceLattice.meet('DR', 'KO')).toBe('KO');
  });

  it('join of non-comparable returns max', () => {
    expect(GovernanceLattice.join('AV', 'UM')).toBe('UM');
  });
});

describe('DimensionalLattice', () => {
  it('has correct ordering', () => {
    expect(DimensionalLattice.elements).toEqual(['COLLAPSED', 'DEMI', 'QUASI', 'POLLY']);
    expect(DimensionalLattice.bot).toBe('COLLAPSED');
    expect(DimensionalLattice.top).toBe('POLLY');
  });

  it('meet/join work correctly', () => {
    expect(DimensionalLattice.meet('POLLY', 'QUASI')).toBe('QUASI');
    expect(DimensionalLattice.join('COLLAPSED', 'DEMI')).toBe('DEMI');
    expect(DimensionalLattice.meet('DEMI', 'DEMI')).toBe('DEMI');
  });
});

describe('UnitIntervalLattice', () => {
  const UIL = createUnitIntervalLattice(11); // 0, 0.1, 0.2, ..., 1.0

  it('has correct bounds', () => {
    expect(UIL.bot).toBe(0);
    expect(UIL.top).toBe(1);
    expect(UIL.elements).toHaveLength(11);
  });

  it('meet = min', () => {
    expect(UIL.meet(0.3, 0.7)).toBeCloseTo(0.3, 5);
    expect(UIL.meet(1, 0)).toBeCloseTo(0, 5);
  });

  it('join = max', () => {
    expect(UIL.join(0.3, 0.7)).toBeCloseTo(0.7, 5);
    expect(UIL.join(0, 1)).toBeCloseTo(1, 5);
  });

  it('leq works', () => {
    expect(UIL.leq(0.2, 0.8)).toBe(true);
    expect(UIL.leq(0.5, 0.5)).toBe(true);
    expect(UIL.leq(0.9, 0.1)).toBe(false);
  });
});

// =============================================================================
// CELL COMPLEX TESTS
// =============================================================================

describe('buildComplex', () => {
  it('builds vertices and edges', () => {
    const cx = buildComplex(['A', 'B', 'C'], [['A', 'B'], ['B', 'C']]);
    expect(cx.vertices).toHaveLength(3);
    expect(cx.edges).toHaveLength(2);
    expect(cx.edges[0].source).toBe('A');
    expect(cx.edges[0].target).toBe('B');
  });

  it('handles empty graph', () => {
    const cx = buildComplex([], []);
    expect(cx.vertices).toHaveLength(0);
    expect(cx.edges).toHaveLength(0);
  });

  it('handles isolated vertices', () => {
    const cx = buildComplex(['A', 'B', 'C'], []);
    expect(cx.vertices).toHaveLength(3);
    expect(cx.edges).toHaveLength(0);
  });
});

// =============================================================================
// GALOIS CONNECTION TESTS
// =============================================================================

describe('GaloisConnection', () => {
  it('identity connection preserves values', () => {
    const conn = identityConnection<RiskDecision>();
    expect(conn.lower('DENY')).toBe('DENY');
    expect(conn.upper('ALLOW')).toBe('ALLOW');
  });

  it('custom Galois connection with floor/ceiling', () => {
    // Example: map 4-level risk to 2-level {low, high}
    // lower: ALLOW/QUARANTINE → 'ALLOW', ESCALATE/DENY → 'DENY'
    // upper: 'ALLOW' → 'QUARANTINE', 'DENY' → 'DENY'
    const conn = galoisFromMaps<RiskDecision, RiskDecision>(
      (a) => (a === 'ALLOW' || a === 'QUARANTINE' ? 'ALLOW' : 'DENY'),
      (b) => (b === 'ALLOW' ? 'QUARANTINE' : 'DENY')
    );

    expect(conn.lower('ALLOW')).toBe('ALLOW');
    expect(conn.lower('QUARANTINE')).toBe('ALLOW');
    expect(conn.lower('ESCALATE')).toBe('DENY');
    expect(conn.lower('DENY')).toBe('DENY');
    expect(conn.upper('ALLOW')).toBe('QUARANTINE');
    expect(conn.upper('DENY')).toBe('DENY');
  });
});

// =============================================================================
// CONSTANT SHEAF TESTS
// =============================================================================

describe('constantSheaf', () => {
  it('creates a sheaf with identity restrictions', () => {
    const cx = buildComplex(['A', 'B'], [['A', 'B']]);
    const sheaf = constantSheaf(RiskLattice, cx);

    expect(sheaf.restrict('A', 'e-A-B', 'DENY')).toBe('DENY');
    expect(sheaf.extend('e-A-B', 'A', 'ALLOW')).toBe('ALLOW');
  });
});

// =============================================================================
// COCHAIN TESTS
// =============================================================================

describe('cochains', () => {
  it('cochain0 creates from record', () => {
    const c = cochain0({ A: 'ALLOW', B: 'DENY' } as Record<string, RiskDecision>);
    expect(c.get('A')).toBe('ALLOW');
    expect(c.get('B')).toBe('DENY');
  });

  it('constantCochain0 assigns same value everywhere', () => {
    const cx = buildComplex(['A', 'B', 'C'], []);
    const c = constantCochain0(cx, 'QUARANTINE' as RiskDecision);
    expect(c.get('A')).toBe('QUARANTINE');
    expect(c.get('B')).toBe('QUARANTINE');
    expect(c.get('C')).toBe('QUARANTINE');
  });

  it('topCochain0 assigns ⊤ everywhere', () => {
    const cx = buildComplex(['A', 'B'], [['A', 'B']]);
    const sheaf = constantSheaf(RiskLattice, cx);
    const c = topCochain0(sheaf);
    expect(c.get('A')).toBe('DENY');
    expect(c.get('B')).toBe('DENY');
  });
});

// =============================================================================
// TARSKI LAPLACIAN TESTS
// =============================================================================

describe('tarskiLaplacian0', () => {
  it('on constant cochain with constant sheaf = identity', () => {
    // All same value, identity restrictions → Laplacian preserves it
    const cx = buildComplex(['A', 'B', 'C'], [['A', 'B'], ['B', 'C']]);
    const sheaf = constantSheaf(RiskLattice, cx);
    const x = constantCochain0(cx, 'ESCALATE' as RiskDecision);

    const lx = tarskiLaplacian0(sheaf, x);
    expect(lx.get('A')).toBe('ESCALATE');
    expect(lx.get('B')).toBe('ESCALATE');
    expect(lx.get('C')).toBe('ESCALATE');
  });

  it('on disagreeing cochain, diffuses via meet', () => {
    // A=DENY, B=ALLOW on edge A-B
    // L_0(A): edge A-B → restrict(A)=DENY, restrict(B)=ALLOW → meet=ALLOW → extend to A=ALLOW
    // L_0(B): edge A-B → restrict(A)=DENY, restrict(B)=ALLOW → meet=ALLOW → extend to B=ALLOW
    const cx = buildComplex(['A', 'B'], [['A', 'B']]);
    const sheaf = constantSheaf(RiskLattice, cx);
    const x = cochain0({ A: 'DENY', B: 'ALLOW' } as Record<string, RiskDecision>);

    const lx = tarskiLaplacian0(sheaf, x);
    expect(lx.get('A')).toBe('ALLOW');
    expect(lx.get('B')).toBe('ALLOW');
  });

  it('isolated vertex gets ⊤', () => {
    const cx = buildComplex(['A'], []);
    const sheaf = constantSheaf(RiskLattice, cx);
    const x = cochain0({ A: 'QUARANTINE' } as Record<string, RiskDecision>);

    const lx = tarskiLaplacian0(sheaf, x);
    expect(lx.get('A')).toBe('DENY'); // ⊤ = DENY (vacuous meet)
  });

  it('triangle graph: all contribute to center vertex', () => {
    // Triangle: A-B, B-C, A-C
    const cx = buildComplex(['A', 'B', 'C'], [['A', 'B'], ['B', 'C'], ['A', 'C']]);
    const sheaf = constantSheaf(RiskLattice, cx);
    const x = cochain0({
      A: 'DENY',
      B: 'ESCALATE',
      C: 'QUARANTINE',
    } as Record<string, RiskDecision>);

    const lx = tarskiLaplacian0(sheaf, x);
    // For vertex A: edges A-B (meet DENY,ESCALATE=ESCALATE), A-C (meet DENY,QUARANTINE=QUARANTINE)
    // → meet of ESCALATE, QUARANTINE = QUARANTINE
    expect(lx.get('A')).toBe('QUARANTINE');
    // For vertex B: edges A-B (meet DENY,ESCALATE=ESCALATE), B-C (meet ESCALATE,QUARANTINE=QUARANTINE)
    // → meet of ESCALATE, QUARANTINE = QUARANTINE
    expect(lx.get('B')).toBe('QUARANTINE');
    // For vertex C: edges A-C (meet DENY,QUARANTINE=QUARANTINE), B-C (meet ESCALATE,QUARANTINE=QUARANTINE)
    // → meet of QUARANTINE, QUARANTINE = QUARANTINE
    expect(lx.get('C')).toBe('QUARANTINE');
  });
});

// =============================================================================
// HARMONIC STEP TESTS
// =============================================================================

describe('harmonicStep0', () => {
  it('step = id ∧ L_0', () => {
    const cx = buildComplex(['A', 'B'], [['A', 'B']]);
    const sheaf = constantSheaf(RiskLattice, cx);
    const x = cochain0({ A: 'DENY', B: 'ALLOW' } as Record<string, RiskDecision>);

    const step = harmonicStep0(sheaf, x);
    // id ∧ L_0: A = meet(DENY, ALLOW) = ALLOW, B = meet(ALLOW, ALLOW) = ALLOW
    expect(step.get('A')).toBe('ALLOW');
    expect(step.get('B')).toBe('ALLOW');
  });

  it('step is monotone descending from ⊤', () => {
    const cx = buildComplex(['A', 'B'], [['A', 'B']]);
    const sheaf = constantSheaf(RiskLattice, cx);
    const x = topCochain0(sheaf); // A=DENY, B=DENY

    const step = harmonicStep0(sheaf, x);
    // Both get meet(DENY, meet(DENY,DENY)) = meet(DENY,DENY) = DENY
    expect(step.get('A')).toBe('DENY');
    expect(step.get('B')).toBe('DENY');
  });
});

// =============================================================================
// HARMONIC FLOW TESTS
// =============================================================================

describe('harmonicFlow', () => {
  it('converges immediately on constant sheaf with constant cochain', () => {
    const cx = buildComplex(['A', 'B', 'C'], [['A', 'B'], ['B', 'C']]);
    const sheaf = constantSheaf(RiskLattice, cx);
    const initial = constantCochain0(cx, 'ESCALATE' as RiskDecision);

    const result = harmonicFlow(sheaf, initial);
    expect(result.converged).toBe(true);
    expect(result.iterations).toBe(1);
    expect(result.fixedPoint.get('A')).toBe('ESCALATE');
  });

  it('converges to meet on disagreeing path graph', () => {
    // Path: A - B - C, values DENY, QUARANTINE, ALLOW
    const cx = buildComplex(['A', 'B', 'C'], [['A', 'B'], ['B', 'C']]);
    const sheaf = constantSheaf(RiskLattice, cx);
    const initial = cochain0({
      A: 'DENY',
      B: 'QUARANTINE',
      C: 'ALLOW',
    } as Record<string, RiskDecision>);

    const result = harmonicFlow(sheaf, initial);
    expect(result.converged).toBe(true);
    // On a constant sheaf, the harmonic flow converges to the global meet
    // because meet-based diffusion propagates the minimum value
    expect(result.fixedPoint.get('A')).toBe('ALLOW');
    expect(result.fixedPoint.get('B')).toBe('ALLOW');
    expect(result.fixedPoint.get('C')).toBe('ALLOW');
  });

  it('converges in ≤ |elements| iterations for finite lattice', () => {
    const cx = buildComplex(
      ['A', 'B', 'C', 'D'],
      [['A', 'B'], ['B', 'C'], ['C', 'D']]
    );
    const sheaf = constantSheaf(RiskLattice, cx);
    const initial = cochain0({
      A: 'DENY',
      B: 'DENY',
      C: 'DENY',
      D: 'ALLOW',
    } as Record<string, RiskDecision>);

    const result = harmonicFlow(sheaf, initial);
    expect(result.converged).toBe(true);
    // At most 4 iterations (lattice height)
    expect(result.iterations).toBeLessThanOrEqual(4);
  });

  it('handles empty complex', () => {
    const cx = buildComplex([], []);
    const sheaf = constantSheaf(RiskLattice, cx);
    const initial = new Map<string, RiskDecision>();

    const result = harmonicFlow(sheaf, initial);
    expect(result.converged).toBe(true);
    expect(result.iterations).toBe(1);
  });
});

// =============================================================================
// TARSKI COHOMOLOGY TH^0 TESTS
// =============================================================================

describe('tarskiCohomology0', () => {
  it('TH^0 from ⊤ on connected graph = ⊤ (constant sheaf)', () => {
    // Constant sheaf: all restrictions are identity, so ⊤ is always a global section
    const cx = buildComplex(['A', 'B'], [['A', 'B']]);
    const sheaf = constantSheaf(RiskLattice, cx);

    const th0 = tarskiCohomology0(sheaf);
    expect(th0.converged).toBe(true);
    // Starting from DENY,DENY with identity restrictions, DENY is a fixed point
    expect(th0.fixedPoint.get('A')).toBe('DENY');
    expect(th0.fixedPoint.get('B')).toBe('DENY');
  });

  it('TH^0 equals global sections (consensus)', () => {
    const cx = buildComplex(['A', 'B', 'C'], [['A', 'B'], ['B', 'C'], ['A', 'C']]);
    const sheaf = constantSheaf(GovernanceLattice, cx);

    const th0 = tarskiCohomology0(sheaf);
    expect(th0.converged).toBe(true);
    // Constant sheaf starting from DR → all stay DR
    expect(th0.fixedPoint.get('A')).toBe('DR');
    expect(th0.fixedPoint.get('B')).toBe('DR');
    expect(th0.fixedPoint.get('C')).toBe('DR');
  });
});

// =============================================================================
// PSEUDO-COBOUNDARY TESTS
// =============================================================================

describe('pseudoCoboundary', () => {
  it('on constant cochain = constant edge values', () => {
    const cx = buildComplex(['A', 'B'], [['A', 'B']]);
    const sheaf = constantSheaf(RiskLattice, cx);
    const x = constantCochain0(cx, 'ESCALATE' as RiskDecision);

    const delta = pseudoCoboundary(sheaf, x);
    expect(delta.get('e-A-B')).toBe('ESCALATE');
  });

  it('on disagreeing cochain = meet of endpoint values', () => {
    const cx = buildComplex(['A', 'B'], [['A', 'B']]);
    const sheaf = constantSheaf(RiskLattice, cx);
    const x = cochain0({ A: 'DENY', B: 'QUARANTINE' } as Record<string, RiskDecision>);

    const delta = pseudoCoboundary(sheaf, x);
    expect(delta.get('e-A-B')).toBe('QUARANTINE'); // meet(DENY, QUARANTINE)
  });
});

// =============================================================================
// TARSKI COHOMOLOGY TH^1 TESTS
// =============================================================================

describe('tarskiCohomology1', () => {
  it('converges on simple graph', () => {
    const cx = buildComplex(['A', 'B', 'C'], [['A', 'B'], ['B', 'C']]);
    const sheaf = constantSheaf(RiskLattice, cx);

    const th1 = tarskiCohomology1(sheaf);
    expect(th1.converged).toBe(true);
  });

  it('TH^1 on triangle = stable edge values', () => {
    const cx = buildComplex(['A', 'B', 'C'], [['A', 'B'], ['B', 'C'], ['A', 'C']]);
    const sheaf = constantSheaf(RiskLattice, cx);

    const th1 = tarskiCohomology1(sheaf);
    expect(th1.converged).toBe(true);
    // All edges should stabilize to DENY (starting from ⊤)
    expect(th1.fixedPoint.get('e-A-B')).toBe('DENY');
    expect(th1.fixedPoint.get('e-B-C')).toBe('DENY');
    expect(th1.fixedPoint.get('e-A-C')).toBe('DENY');
  });
});

// =============================================================================
// CONSENSUS ANALYSIS TESTS
// =============================================================================

describe('analyzeConsensus', () => {
  it('unanimous agreement detected', () => {
    const cx = buildComplex(['A', 'B', 'C'], [['A', 'B'], ['B', 'C']]);
    const sheaf = constantSheaf(RiskLattice, cx);
    const opinions = cochain0({
      A: 'ALLOW',
      B: 'ALLOW',
      C: 'ALLOW',
    } as Record<string, RiskDecision>);

    const analysis = analyzeConsensus(sheaf, opinions);
    expect(analysis.hasConsensus).toBe(true);
    expect(analysis.isUnanimous).toBe(true);
    expect(analysis.unanimousValue).toBe('ALLOW');
    expect(analysis.distinctValues).toBe(1);
    expect(analysis.disagreementEdges).toHaveLength(0);
  });

  it('disagreement converges to meet', () => {
    const cx = buildComplex(['A', 'B'], [['A', 'B']]);
    const sheaf = constantSheaf(RiskLattice, cx);
    const opinions = cochain0({
      A: 'DENY',
      B: 'ALLOW',
    } as Record<string, RiskDecision>);

    const analysis = analyzeConsensus(sheaf, opinions);
    expect(analysis.hasConsensus).toBe(true);
    expect(analysis.isUnanimous).toBe(true);
    expect(analysis.unanimousValue).toBe('ALLOW');
  });

  it('multi-agent star topology converges', () => {
    // Star: center C connected to A, B, D, E
    const cx = buildComplex(
      ['C', 'A', 'B', 'D', 'E'],
      [['C', 'A'], ['C', 'B'], ['C', 'D'], ['C', 'E']]
    );
    const sheaf = constantSheaf(RiskLattice, cx);
    const opinions = cochain0({
      C: 'ESCALATE',
      A: 'DENY',
      B: 'QUARANTINE',
      D: 'ALLOW',
      E: 'ESCALATE',
    } as Record<string, RiskDecision>);

    const analysis = analyzeConsensus(sheaf, opinions);
    expect(analysis.hasConsensus).toBe(true);
    // The center C is connected to everyone, so the meet propagates everywhere
    expect(analysis.isUnanimous).toBe(true);
    expect(analysis.unanimousValue).toBe('ALLOW'); // global meet
  });

  it('disconnected components have independent consensus', () => {
    // Two disconnected pairs: A-B and C-D
    const cx = buildComplex(['A', 'B', 'C', 'D'], [['A', 'B'], ['C', 'D']]);
    const sheaf = constantSheaf(RiskLattice, cx);
    const opinions = cochain0({
      A: 'DENY',
      B: 'DENY',
      C: 'ALLOW',
      D: 'ALLOW',
    } as Record<string, RiskDecision>);

    const analysis = analyzeConsensus(sheaf, opinions);
    expect(analysis.hasConsensus).toBe(true);
    expect(analysis.consensusValues['A']).toBe('DENY');
    expect(analysis.consensusValues['B']).toBe('DENY');
    expect(analysis.consensusValues['C']).toBe('ALLOW');
    expect(analysis.consensusValues['D']).toBe('ALLOW');
    // Not unanimous because components disagree
    expect(analysis.isUnanimous).toBe(false);
    expect(analysis.distinctValues).toBe(2);
  });
});

// =============================================================================
// RISK CONSENSUS HELPER TESTS
// =============================================================================

describe('riskConsensus', () => {
  it('3-agent triangle reaches consensus', () => {
    const result = riskConsensus(
      ['agent-1', 'agent-2', 'agent-3'],
      [['agent-1', 'agent-2'], ['agent-2', 'agent-3'], ['agent-1', 'agent-3']],
      { 'agent-1': 'DENY', 'agent-2': 'ESCALATE', 'agent-3': 'QUARANTINE' }
    );

    expect(result.hasConsensus).toBe(true);
    expect(result.isUnanimous).toBe(true);
    expect(result.unanimousValue).toBe('QUARANTINE');
  });

  it('unanimous agents stay unanimous', () => {
    const result = riskConsensus(
      ['A', 'B', 'C'],
      [['A', 'B'], ['B', 'C']],
      { A: 'ESCALATE', B: 'ESCALATE', C: 'ESCALATE' }
    );

    expect(result.isUnanimous).toBe(true);
    expect(result.unanimousValue).toBe('ESCALATE');
    expect(result.iterations).toBe(1);
  });

  it('single-agent consensus is trivial', () => {
    const result = riskConsensus(
      ['solo'],
      [],
      { solo: 'DENY' }
    );

    expect(result.hasConsensus).toBe(true);
    expect(result.isUnanimous).toBe(true);
    expect(result.unanimousValue).toBe('DENY');
  });
});

// =============================================================================
// GOVERNANCE CONSENSUS TESTS
// =============================================================================

describe('governanceConsensusSheaf', () => {
  it('builds a valid sheaf', () => {
    const sheaf = governanceConsensusSheaf(
      ['agent-KO', 'agent-DR'],
      [['agent-KO', 'agent-DR']]
    );
    expect(sheaf.lattice).toBe(GovernanceLattice);
    expect(sheaf.complex.vertices).toHaveLength(2);
  });

  it('governance consensus converges to meet of tiers', () => {
    const sheaf = governanceConsensusSheaf(
      ['low', 'mid', 'high'],
      [['low', 'mid'], ['mid', 'high']]
    );
    const opinions = cochain0({
      low: 'KO',
      mid: 'RU',
      high: 'DR',
    } as Record<string, GovernanceTier>);

    const analysis = analyzeConsensus(sheaf, opinions);
    expect(analysis.isUnanimous).toBe(true);
    expect(analysis.unanimousValue).toBe('KO');
  });
});

// =============================================================================
// CUSTOM SHEAF (TWISTED) TESTS
// =============================================================================

describe('customSheaf with twisted restrictions', () => {
  it('non-identity restriction changes consensus', () => {
    // Edge A-B with restriction that lowers by one level
    const cx = buildComplex(['A', 'B'], [['A', 'B']]);
    const stepDown = galoisFromMaps<RiskDecision, RiskDecision>(
      (a) => {
        const idx = RISK_ORDER.indexOf(a);
        return RISK_ORDER[Math.max(0, idx - 1)];
      },
      (b) => {
        const idx = RISK_ORDER.indexOf(b);
        return RISK_ORDER[Math.min(RISK_ORDER.length - 1, idx + 1)];
      }
    );

    const restrictions = new Map([['e-A-B', stepDown]]);
    const sheaf = customSheaf(RiskLattice, cx, restrictions);

    // A=ESCALATE, B=ESCALATE
    const x = cochain0({ A: 'ESCALATE', B: 'ESCALATE' } as Record<string, RiskDecision>);
    const lx = tarskiLaplacian0(sheaf, x);

    // Edge A-B: restrict(A)=QUARANTINE, restrict(B)=QUARANTINE → meet=QUARANTINE
    // extend to A = upper(QUARANTINE) = ESCALATE
    // extend to B = upper(QUARANTINE) = ESCALATE
    expect(lx.get('A')).toBe('ESCALATE');
    expect(lx.get('B')).toBe('ESCALATE');
  });
});

const RISK_ORDER: readonly RiskDecision[] = ['ALLOW', 'QUARANTINE', 'ESCALATE', 'DENY'];

// =============================================================================
// CONSENSUS SUMMARY TESTS
// =============================================================================

describe('consensusSummary', () => {
  it('produces readable output', () => {
    const result = riskConsensus(
      ['A', 'B', 'C'],
      [['A', 'B'], ['B', 'C']],
      { A: 'DENY', B: 'ALLOW', C: 'ESCALATE' }
    );

    const summary = consensusSummary(result);
    expect(summary).toContain('Consensus: YES');
    expect(summary).toContain('Unanimous:');
    expect(summary).toContain('Distinct values:');
    expect(summary).toContain('Iterations:');
    expect(summary).toContain('Obstruction (TH^1):');
  });
});

// =============================================================================
// UNIT INTERVAL LATTICE FLOW TESTS
// =============================================================================

describe('harmonicFlow with UnitIntervalLattice', () => {
  it('numeric consensus converges', () => {
    const UIL = createUnitIntervalLattice(101);
    const cx = buildComplex(['A', 'B', 'C'], [['A', 'B'], ['B', 'C']]);
    const sheaf = constantSheaf(UIL, cx);
    const opinions = cochain0({ A: 0.9, B: 0.5, C: 0.1 });

    const result = harmonicFlow(sheaf, opinions);
    expect(result.converged).toBe(true);
    // Should converge to min = 0.1
    expect(result.fixedPoint.get('A')).toBeCloseTo(0.1, 1);
    expect(result.fixedPoint.get('B')).toBeCloseTo(0.1, 1);
    expect(result.fixedPoint.get('C')).toBeCloseTo(0.1, 1);
  });
});

// =============================================================================
// EDGE CASES & ADVERSARIAL SCENARIOS
// =============================================================================

describe('edge cases', () => {
  it('self-loop edge', () => {
    const cx = buildComplex(['A'], [['A', 'A']]);
    const sheaf = constantSheaf(RiskLattice, cx);
    const x = cochain0({ A: 'ESCALATE' } as Record<string, RiskDecision>);

    const lx = tarskiLaplacian0(sheaf, x);
    expect(lx.get('A')).toBe('ESCALATE'); // meet(ESCALATE, ESCALATE) = ESCALATE
  });

  it('parallel edges between same vertices', () => {
    const cx: ReturnType<typeof buildComplex> = {
      vertices: [{ id: 'A' }, { id: 'B' }],
      edges: [
        { id: 'e1', source: 'A', target: 'B' },
        { id: 'e2', source: 'A', target: 'B' },
      ],
    };
    const sheaf = constantSheaf(RiskLattice, cx);
    const x = cochain0({ A: 'DENY', B: 'QUARANTINE' } as Record<string, RiskDecision>);

    const lx = tarskiLaplacian0(sheaf, x);
    // Two edges both contribute same thing → result is the meet
    expect(lx.get('A')).toBe('QUARANTINE');
    expect(lx.get('B')).toBe('QUARANTINE');
  });

  it('complete graph K4 converges', () => {
    const cx = buildComplex(
      ['A', 'B', 'C', 'D'],
      [['A', 'B'], ['A', 'C'], ['A', 'D'], ['B', 'C'], ['B', 'D'], ['C', 'D']]
    );
    const sheaf = constantSheaf(RiskLattice, cx);
    const opinions = cochain0({
      A: 'DENY',
      B: 'ESCALATE',
      C: 'QUARANTINE',
      D: 'ALLOW',
    } as Record<string, RiskDecision>);

    const analysis = analyzeConsensus(sheaf, opinions);
    expect(analysis.hasConsensus).toBe(true);
    expect(analysis.isUnanimous).toBe(true);
    expect(analysis.unanimousValue).toBe('ALLOW');
  });

  it('long chain propagates minimum', () => {
    // Chain: 0-1-2-3-4-5-6-7-8-9
    const ids = Array.from({ length: 10 }, (_, i) => `v${i}`);
    const links: [string, string][] = [];
    for (let i = 0; i < 9; i++) links.push([`v${i}`, `v${i + 1}`]);

    const cx = buildComplex(ids, links);
    const sheaf = constantSheaf(RiskLattice, cx);
    const opinions: Record<string, RiskDecision> = {};
    for (let i = 0; i < 10; i++) opinions[`v${i}`] = 'DENY';
    opinions['v9'] = 'ALLOW'; // One dissenter at the end

    const result = harmonicFlow(sheaf, cochain0(opinions));
    expect(result.converged).toBe(true);
    // ALLOW propagates through the entire chain
    for (let i = 0; i < 10; i++) {
      expect(result.fixedPoint.get(`v${i}`)).toBe('ALLOW');
    }
    expect(result.iterations).toBeLessThanOrEqual(10);
  });
});

// =============================================================================
// LATTICE AXIOM VERIFICATION
// =============================================================================

describe('lattice axioms', () => {
  function verifyLatticeAxioms<T>(L: CompleteLattice<T>, name: string) {
    describe(`${name} lattice axioms`, () => {
      const elems = L.elements;

      it('reflexivity: a ≤ a', () => {
        for (const a of elems) {
          expect(L.leq(a, a)).toBe(true);
        }
      });

      it('antisymmetry: a ≤ b ∧ b ≤ a → a = b', () => {
        for (const a of elems) {
          for (const b of elems) {
            if (L.leq(a, b) && L.leq(b, a)) {
              expect(L.eq(a, b)).toBe(true);
            }
          }
        }
      });

      it('transitivity: a ≤ b ∧ b ≤ c → a ≤ c', () => {
        for (const a of elems) {
          for (const b of elems) {
            for (const c of elems) {
              if (L.leq(a, b) && L.leq(b, c)) {
                expect(L.leq(a, c)).toBe(true);
              }
            }
          }
        }
      });

      it('meet is greatest lower bound', () => {
        for (const a of elems) {
          for (const b of elems) {
            const m = L.meet(a, b);
            expect(L.leq(m, a)).toBe(true);
            expect(L.leq(m, b)).toBe(true);
          }
        }
      });

      it('join is least upper bound', () => {
        for (const a of elems) {
          for (const b of elems) {
            const j = L.join(a, b);
            expect(L.leq(a, j)).toBe(true);
            expect(L.leq(b, j)).toBe(true);
          }
        }
      });

      it('top is greatest: a ≤ ⊤', () => {
        for (const a of elems) {
          expect(L.leq(a, L.top)).toBe(true);
        }
      });

      it('bottom is least: ⊥ ≤ a', () => {
        for (const a of elems) {
          expect(L.leq(L.bot, a)).toBe(true);
        }
      });

      it('meet absorption: a ∧ (a ∨ b) = a', () => {
        for (const a of elems) {
          for (const b of elems) {
            expect(L.eq(L.meet(a, L.join(a, b)), a)).toBe(true);
          }
        }
      });

      it('join absorption: a ∨ (a ∧ b) = a', () => {
        for (const a of elems) {
          for (const b of elems) {
            expect(L.eq(L.join(a, L.meet(a, b)), a)).toBe(true);
          }
        }
      });
    });
  }

  verifyLatticeAxioms(RiskLattice, 'Risk');
  verifyLatticeAxioms(GovernanceLattice, 'Governance');
  verifyLatticeAxioms(DimensionalLattice, 'Dimensional');
});
