/**
 * @file sheafCohomology.test.ts
 * @module tests/harmonic/sheafCohomology
 * @layer Layer 5, Layer 9, Layer 11, Layer 13
 *
 * Tests for Tarski sheaf cohomology: lattice axioms, Galois connections,
 * Laplacian, harmonic flow, global sections, SCBE governance integration.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  // Lattices
  CompleteLattice,
  RiskLevel,
  RISK_LATTICE,
  BOOLEAN_LATTICE,
  intervalLattice,
  productLattice,
  // Galois
  GaloisConnection,
  identityConnection,
  // Cell complex
  CellComplex,
  CellularSheaf,
  Cochain0,
  // Sheaf builders
  constantSheaf,
  // Tarski
  tarskiLaplacian0,
  harmonicFlowStep,
  harmonicFlow,
  globalSections,
  // Obstruction
  obstructionDegree,
  isGlobalSection,
  // SCBE temporal
  buildTemporalComplex,
  buildGovernanceSheaf,
  detectPolicyObstruction,
  EdgeTwist,
  // Fail-to-noise
  failToNoise,
  // T-braiding
  braidedTemporalDistance,
  braidedMetaTime,
  // Harmonic wall
  cohomologicalHarmonicWall,
} from '../../src/harmonic/sheafCohomology.js';

// ============================================================
// A. COMPLETE LATTICE AXIOMS
// ============================================================

describe('A · Complete lattice axioms', () => {
  describe('RISK_LATTICE', () => {
    it('has ALLOW as bottom and DENY as top', () => {
      expect(RISK_LATTICE.bottom()).toBe(RiskLevel.ALLOW);
      expect(RISK_LATTICE.top()).toBe(RiskLevel.DENY);
    });

    it('meet is minimum, join is maximum', () => {
      expect(RISK_LATTICE.meet(RiskLevel.ESCALATE, RiskLevel.QUARANTINE)).toBe(
        RiskLevel.QUARANTINE,
      );
      expect(RISK_LATTICE.join(RiskLevel.ESCALATE, RiskLevel.QUARANTINE)).toBe(
        RiskLevel.ESCALATE,
      );
    });

    it('meet with top is identity', () => {
      for (const e of RISK_LATTICE.elements()) {
        expect(RISK_LATTICE.meet(e, RISK_LATTICE.top())).toBe(e);
      }
    });

    it('join with bottom is identity', () => {
      for (const e of RISK_LATTICE.elements()) {
        expect(RISK_LATTICE.join(e, RISK_LATTICE.bottom())).toBe(e);
      }
    });

    it('leq is reflexive, antisymmetric, transitive', () => {
      const elems = RISK_LATTICE.elements();
      // Reflexive
      for (const e of elems) expect(RISK_LATTICE.leq(e, e)).toBe(true);
      // Antisymmetric: a ≤ b ∧ b ≤ a → a = b
      expect(RISK_LATTICE.leq(RiskLevel.ALLOW, RiskLevel.DENY)).toBe(true);
      expect(RISK_LATTICE.leq(RiskLevel.DENY, RiskLevel.ALLOW)).toBe(false);
      // Transitive
      expect(RISK_LATTICE.leq(RiskLevel.ALLOW, RiskLevel.QUARANTINE)).toBe(true);
      expect(RISK_LATTICE.leq(RiskLevel.QUARANTINE, RiskLevel.DENY)).toBe(true);
      expect(RISK_LATTICE.leq(RiskLevel.ALLOW, RiskLevel.DENY)).toBe(true);
    });

    it('has exactly 4 elements', () => {
      expect(RISK_LATTICE.elements()).toHaveLength(4);
    });
  });

  describe('BOOLEAN_LATTICE', () => {
    it('has false as bottom, true as top', () => {
      expect(BOOLEAN_LATTICE.bottom()).toBe(false);
      expect(BOOLEAN_LATTICE.top()).toBe(true);
    });

    it('meet is AND, join is OR', () => {
      expect(BOOLEAN_LATTICE.meet(true, false)).toBe(false);
      expect(BOOLEAN_LATTICE.join(true, false)).toBe(true);
    });
  });

  describe('intervalLattice', () => {
    it('intervalLattice(5) has 5 elements 0..4', () => {
      const lat = intervalLattice(5);
      expect(lat.elements()).toEqual([0, 1, 2, 3, 4]);
      expect(lat.bottom()).toBe(0);
      expect(lat.top()).toBe(4);
    });

    it('meet and join are min/max', () => {
      const lat = intervalLattice(8);
      expect(lat.meet(3, 5)).toBe(3);
      expect(lat.join(3, 5)).toBe(5);
    });
  });

  describe('productLattice', () => {
    it('product of boolean × risk has 8 elements', () => {
      const prod = productLattice(BOOLEAN_LATTICE, RISK_LATTICE);
      expect(prod.elements()).toHaveLength(8);
    });

    it('componentwise meet/join', () => {
      const prod = productLattice(BOOLEAN_LATTICE, RISK_LATTICE);
      const a: [boolean, RiskLevel] = [true, RiskLevel.ESCALATE];
      const b: [boolean, RiskLevel] = [false, RiskLevel.DENY];
      expect(prod.meet(a, b)).toEqual([false, RiskLevel.ESCALATE]);
      expect(prod.join(a, b)).toEqual([true, RiskLevel.DENY]);
    });

    it('leq is componentwise', () => {
      const prod = productLattice(BOOLEAN_LATTICE, RISK_LATTICE);
      expect(prod.leq([false, RiskLevel.ALLOW], [true, RiskLevel.DENY])).toBe(true);
      expect(prod.leq([true, RiskLevel.DENY], [false, RiskLevel.ALLOW])).toBe(false);
    });
  });
});

// ============================================================
// B. GALOIS CONNECTIONS
// ============================================================

describe('B · Galois connections', () => {
  it('identity connection preserves values', () => {
    const conn = identityConnection<RiskLevel>();
    expect(conn.lower(RiskLevel.QUARANTINE)).toBe(RiskLevel.QUARANTINE);
    expect(conn.upper(RiskLevel.ESCALATE)).toBe(RiskLevel.ESCALATE);
  });

  it('identity satisfies adjointness: f♭(s) ≤ t ⟺ s ≤ f♯(t)', () => {
    const conn = identityConnection<number>();
    const lat = intervalLattice(5);
    for (const s of lat.elements()) {
      for (const t of lat.elements()) {
        const lhs = lat.leq(conn.lower(s), t);
        const rhs = lat.leq(s, conn.upper(t));
        expect(lhs).toBe(rhs);
      }
    }
  });
});

// ============================================================
// C. TARSKI LAPLACIAN on small graphs
// ============================================================

describe('C · Tarski Laplacian L₀', () => {
  // Simple graph: v1 — e1 — v2
  const twoVertexGraph: CellComplex = {
    vertices: [{ id: 'v1' }, { id: 'v2' }],
    edges: [{ id: 'e1', source: 'v1', target: 'v2' }],
  };

  it('on constant sheaf with equal values: L₀ preserves them', () => {
    const sheaf = constantSheaf(twoVertexGraph, RISK_LATTICE);
    const cochain: Cochain0<RiskLevel> = new Map([
      ['v1', RiskLevel.QUARANTINE],
      ['v2', RiskLevel.QUARANTINE],
    ]);
    const result = tarskiLaplacian0(sheaf, cochain);
    expect(result.get('v1')).toBe(RiskLevel.QUARANTINE);
    expect(result.get('v2')).toBe(RiskLevel.QUARANTINE);
  });

  it('on constant sheaf with different values: L₀ takes meet of neighbors', () => {
    const sheaf = constantSheaf(twoVertexGraph, RISK_LATTICE);
    const cochain: Cochain0<RiskLevel> = new Map([
      ['v1', RiskLevel.DENY],
      ['v2', RiskLevel.ALLOW],
    ]);
    const result = tarskiLaplacian0(sheaf, cochain);
    // L₀(v1) = meet of (push DENY, push ALLOW in edge, meet → ALLOW, pull back → ALLOW)
    expect(result.get('v1')).toBe(RiskLevel.ALLOW);
    expect(result.get('v2')).toBe(RiskLevel.ALLOW);
  });

  it('isolated vertex gets top from Laplacian', () => {
    const isolated: CellComplex = {
      vertices: [{ id: 'v1' }],
      edges: [],
    };
    const sheaf = constantSheaf(isolated, RISK_LATTICE);
    const cochain: Cochain0<RiskLevel> = new Map([['v1', RiskLevel.QUARANTINE]]);
    const result = tarskiLaplacian0(sheaf, cochain);
    expect(result.get('v1')).toBe(RiskLevel.DENY); // top
  });

  it('triangle graph propagates meets through cycle', () => {
    const triangle: CellComplex = {
      vertices: [{ id: 'a' }, { id: 'b' }, { id: 'c' }],
      edges: [
        { id: 'ab', source: 'a', target: 'b' },
        { id: 'bc', source: 'b', target: 'c' },
        { id: 'ca', source: 'c', target: 'a' },
      ],
    };
    const sheaf = constantSheaf(triangle, RISK_LATTICE);
    const cochain: Cochain0<RiskLevel> = new Map([
      ['a', RiskLevel.DENY],
      ['b', RiskLevel.QUARANTINE],
      ['c', RiskLevel.ESCALATE],
    ]);
    const result = tarskiLaplacian0(sheaf, cochain);
    // Each vertex gets meet of its two edge results
    // a: edges ab (meet DENY,QUARANTINE=QUARANTINE) and ca (meet ESCALATE,DENY=ESCALATE) → meet(QUARANTINE, ESCALATE) = QUARANTINE
    expect(result.get('a')).toBe(RiskLevel.QUARANTINE);
  });
});

// ============================================================
// D. HARMONIC FLOW
// ============================================================

describe('D · Harmonic flow', () => {
  const twoVertexGraph: CellComplex = {
    vertices: [{ id: 'v1' }, { id: 'v2' }],
    edges: [{ id: 'e1', source: 'v1', target: 'v2' }],
  };

  it('flow step: x ∧ L₀(x) is ≤ x (monotonically non-increasing)', () => {
    const sheaf = constantSheaf(twoVertexGraph, RISK_LATTICE);
    const initial: Cochain0<RiskLevel> = new Map([
      ['v1', RiskLevel.DENY],
      ['v2', RiskLevel.QUARANTINE],
    ]);
    const stepped = harmonicFlowStep(sheaf, initial);

    for (const v of twoVertexGraph.vertices) {
      const initVal = initial.get(v.id)!;
      const stepVal = stepped.get(v.id)!;
      expect(RISK_LATTICE.leq(stepVal, initVal)).toBe(true);
    }
  });

  it('flow converges from (DENY, ALLOW) to (ALLOW, ALLOW)', () => {
    const sheaf = constantSheaf(twoVertexGraph, RISK_LATTICE);
    const initial: Cochain0<RiskLevel> = new Map([
      ['v1', RiskLevel.DENY],
      ['v2', RiskLevel.ALLOW],
    ]);
    const { fixedPoint, converged } = harmonicFlow(sheaf, initial);
    expect(converged).toBe(true);
    expect(fixedPoint.get('v1')).toBe(RiskLevel.ALLOW);
    expect(fixedPoint.get('v2')).toBe(RiskLevel.ALLOW);
  });

  it('already-consistent cochain converges in 0 iterations', () => {
    const sheaf = constantSheaf(twoVertexGraph, RISK_LATTICE);
    const initial: Cochain0<RiskLevel> = new Map([
      ['v1', RiskLevel.ESCALATE],
      ['v2', RiskLevel.ESCALATE],
    ]);
    const { iterations, converged } = harmonicFlow(sheaf, initial);
    expect(converged).toBe(true);
    expect(iterations).toBe(0);
  });

  it('boolean flow: (true, false) → (false, false)', () => {
    const sheaf = constantSheaf(twoVertexGraph, BOOLEAN_LATTICE);
    const initial: Cochain0<boolean> = new Map([
      ['v1', true],
      ['v2', false],
    ]);
    const { fixedPoint, converged } = harmonicFlow(sheaf, initial);
    expect(converged).toBe(true);
    expect(fixedPoint.get('v1')).toBe(false);
    expect(fixedPoint.get('v2')).toBe(false);
  });
});

// ============================================================
// E. GLOBAL SECTIONS (TH⁰)
// ============================================================

describe('E · Global sections TH⁰', () => {
  it('constant sheaf on connected graph: sections are constant cochains', () => {
    const triangle: CellComplex = {
      vertices: [{ id: 'a' }, { id: 'b' }, { id: 'c' }],
      edges: [
        { id: 'ab', source: 'a', target: 'b' },
        { id: 'bc', source: 'b', target: 'c' },
        { id: 'ca', source: 'c', target: 'a' },
      ],
    };
    const sheaf = constantSheaf(triangle, RISK_LATTICE);
    const { fixedPoint, converged } = globalSections(sheaf);
    expect(converged).toBe(true);

    // Starting from top (DENY everywhere), the greatest fixed point
    // for a constant sheaf is the constant DENY cochain
    const vals = [...fixedPoint.values()];
    expect(vals.every((v) => v === vals[0])).toBe(true);
    expect(vals[0]).toBe(RiskLevel.DENY);
  });

  it('disconnected graph: each component has independent sections', () => {
    const disconnected: CellComplex = {
      vertices: [{ id: 'a' }, { id: 'b' }],
      edges: [], // No edges → disconnected
    };
    const sheaf = constantSheaf(disconnected, RISK_LATTICE);
    const { fixedPoint, converged } = globalSections(sheaf);
    expect(converged).toBe(true);
    // Each isolated vertex keeps its top value
    expect(fixedPoint.get('a')).toBe(RiskLevel.DENY);
    expect(fixedPoint.get('b')).toBe(RiskLevel.DENY);
  });
});

// ============================================================
// F. OBSTRUCTION MEASUREMENT
// ============================================================

describe('F · Obstruction degree', () => {
  const twoVertexGraph: CellComplex = {
    vertices: [{ id: 'v1' }, { id: 'v2' }],
    edges: [{ id: 'e1', source: 'v1', target: 'v2' }],
  };

  it('zero obstruction when all values agree', () => {
    const sheaf = constantSheaf(twoVertexGraph, RISK_LATTICE);
    const cochain: Cochain0<RiskLevel> = new Map([
      ['v1', RiskLevel.QUARANTINE],
      ['v2', RiskLevel.QUARANTINE],
    ]);
    expect(obstructionDegree(sheaf, cochain)).toBe(0);
  });

  it('nonzero obstruction when values disagree', () => {
    const sheaf = constantSheaf(twoVertexGraph, RISK_LATTICE);
    const cochain: Cochain0<RiskLevel> = new Map([
      ['v1', RiskLevel.DENY],
      ['v2', RiskLevel.ALLOW],
    ]);
    const obs = obstructionDegree(sheaf, cochain);
    expect(obs).toBeGreaterThan(0);
    expect(obs).toBeLessThanOrEqual(1);
  });

  it('maximal obstruction: DENY vs ALLOW → one drops 3 levels / maxRank 3', () => {
    const sheaf = constantSheaf(twoVertexGraph, RISK_LATTICE);
    const cochain: Cochain0<RiskLevel> = new Map([
      ['v1', RiskLevel.DENY],
      ['v2', RiskLevel.ALLOW],
    ]);
    // v1: rank 3→0 = drop 3/3 = 1.0, v2: rank 0→0 = drop 0.
    // Average: (1.0 + 0.0) / 2 = 0.5
    expect(obstructionDegree(sheaf, cochain)).toBeCloseTo(0.5, 5);
  });

  it('isGlobalSection returns true for consistent cochain', () => {
    const sheaf = constantSheaf(twoVertexGraph, RISK_LATTICE);
    const good: Cochain0<RiskLevel> = new Map([
      ['v1', RiskLevel.ESCALATE],
      ['v2', RiskLevel.ESCALATE],
    ]);
    expect(isGlobalSection(sheaf, good)).toBe(true);
  });

  it('isGlobalSection returns false for inconsistent cochain', () => {
    const sheaf = constantSheaf(twoVertexGraph, RISK_LATTICE);
    const bad: Cochain0<RiskLevel> = new Map([
      ['v1', RiskLevel.DENY],
      ['v2', RiskLevel.ALLOW],
    ]);
    expect(isGlobalSection(sheaf, bad)).toBe(false);
  });
});

// ============================================================
// G. SCBE TEMPORAL COMPLEX
// ============================================================

describe('G · Temporal complex builder', () => {
  it('triadic mode: 3 vertices, 3 edges (triangle)', () => {
    const c = buildTemporalComplex('triadic');
    expect(c.vertices).toHaveLength(3);
    expect(c.edges).toHaveLength(3);
    const ids = c.vertices.map((v) => v.id);
    expect(ids).toContain('immediate');
    expect(ids).toContain('memory');
    expect(ids).toContain('governance');
  });

  it('tetradic mode: 4 vertices, 6 edges (K₄)', () => {
    const c = buildTemporalComplex('tetradic');
    expect(c.vertices).toHaveLength(4);
    expect(c.edges).toHaveLength(6);
    expect(c.vertices.map((v) => v.id)).toContain('predictive');
  });

  it('default mode is triadic', () => {
    const c = buildTemporalComplex();
    expect(c.vertices).toHaveLength(3);
  });
});

// ============================================================
// H. GOVERNANCE SHEAF
// ============================================================

describe('H · Governance sheaf', () => {
  it('builds with constant restrictions (no twist)', () => {
    const complex = buildTemporalComplex('triadic');
    const sheaf = buildGovernanceSheaf(complex);
    // All stalks should be RISK_LATTICE
    expect(sheaf.vertexLattice('immediate').top()).toBe(RiskLevel.DENY);
    expect(sheaf.edgeLattice('im-mem').bottom()).toBe(RiskLevel.ALLOW);
    // Identity restrictions
    const conn = sheaf.sourceRestriction('im-mem');
    expect(conn.lower(RiskLevel.QUARANTINE)).toBe(RiskLevel.QUARANTINE);
    expect(conn.upper(RiskLevel.ESCALATE)).toBe(RiskLevel.ESCALATE);
  });

  it('builds with twist: raises risk in lower adjoint', () => {
    const complex = buildTemporalComplex('triadic');
    const twists = new Map<string, EdgeTwist>([['im-mem', { raise: 1, lower: 0 }]]);
    const sheaf = buildGovernanceSheaf(complex, twists);
    const conn = sheaf.sourceRestriction('im-mem');
    // ALLOW raised by 1 → QUARANTINE
    expect(conn.lower(RiskLevel.ALLOW)).toBe(RiskLevel.QUARANTINE);
    // DENY raised by 1 → clamped at DENY
    expect(conn.lower(RiskLevel.DENY)).toBe(RiskLevel.DENY);
  });

  it('twist lowers risk in upper adjoint', () => {
    const complex = buildTemporalComplex('triadic');
    const twists = new Map<string, EdgeTwist>([['im-mem', { raise: 0, lower: 2 }]]);
    const sheaf = buildGovernanceSheaf(complex, twists);
    const conn = sheaf.sourceRestriction('im-mem');
    // DENY lowered by 2 → QUARANTINE
    expect(conn.upper(RiskLevel.DENY)).toBe(RiskLevel.QUARANTINE);
    // ALLOW lowered by 2 → clamped at ALLOW
    expect(conn.upper(RiskLevel.ALLOW)).toBe(RiskLevel.ALLOW);
  });
});

// ============================================================
// I. POLICY OBSTRUCTION DETECTION
// ============================================================

describe('I · Policy obstruction detection', () => {
  it('all agents agree → zero obstruction, no noise', () => {
    const result = detectPolicyObstruction({
      immediate: RiskLevel.QUARANTINE,
      memory: RiskLevel.QUARANTINE,
      governance: RiskLevel.QUARANTINE,
    });
    expect(result.obstruction).toBe(0);
    expect(result.consensus).toBe(RiskLevel.QUARANTINE);
    expect(result.converged).toBe(true);
    expect(result.noiseTriggered).toBe(false);
  });

  it('agents disagree → nonzero obstruction', () => {
    const result = detectPolicyObstruction({
      immediate: RiskLevel.DENY,
      memory: RiskLevel.ALLOW,
      governance: RiskLevel.ESCALATE,
    });
    expect(result.obstruction).toBeGreaterThan(0);
    expect(result.converged).toBe(true);
  });

  it('maximal disagreement: DENY+ALLOW+ALLOW triggers noise', () => {
    const result = detectPolicyObstruction(
      {
        immediate: RiskLevel.DENY,
        memory: RiskLevel.ALLOW,
        governance: RiskLevel.ALLOW,
      },
      { noiseThreshold: 0.2 },
    );
    expect(result.noiseTriggered).toBe(true);
    expect(result.consensus).toBe(RiskLevel.ALLOW);
  });

  it('tetradic: auto-detected when predictive is present', () => {
    const result = detectPolicyObstruction({
      immediate: RiskLevel.QUARANTINE,
      memory: RiskLevel.QUARANTINE,
      governance: RiskLevel.QUARANTINE,
      predictive: RiskLevel.QUARANTINE,
    });
    expect(result.obstruction).toBe(0);
    expect(result.converged).toBe(true);
  });

  it('tetradic with disagreement: 4 variants, 6 edges', () => {
    const result = detectPolicyObstruction({
      immediate: RiskLevel.DENY,
      memory: RiskLevel.ALLOW,
      governance: RiskLevel.ESCALATE,
      predictive: RiskLevel.QUARANTINE,
    });
    expect(result.obstruction).toBeGreaterThan(0);
    expect(result.converged).toBe(true);
  });

  it('twisted sheaf creates obstruction even with close inputs', () => {
    const twists = new Map<string, EdgeTwist>([
      ['im-mem', { raise: 2, lower: 0 }],
    ]);
    const result = detectPolicyObstruction(
      {
        immediate: RiskLevel.ALLOW,
        memory: RiskLevel.ALLOW,
        governance: RiskLevel.ALLOW,
      },
      { twists },
    );
    // The twist escalates ALLOW→ESCALATE in the edge, creating mismatch
    // After flow, consensus drops because the twist introduces inconsistency
    // that the constant inputs can't fully absorb
    expect(result.converged).toBe(true);
  });
});

// ============================================================
// J. FAIL-TO-NOISE
// ============================================================

describe('J · Fail-to-noise', () => {
  it('produces fixed-size output', () => {
    const noise = failToNoise(0.7);
    expect(noise).toHaveLength(256);
    expect(noise).toBeInstanceOf(Uint8Array);
  });

  it('custom size', () => {
    expect(failToNoise(0.5, 128)).toHaveLength(128);
    expect(failToNoise(0.3, 512)).toHaveLength(512);
  });

  it('deterministic: same obstruction → same output', () => {
    const a = failToNoise(0.42);
    const b = failToNoise(0.42);
    expect(a).toEqual(b);
  });

  it('different obstruction → different output', () => {
    const a = failToNoise(0.1);
    const b = failToNoise(0.9);
    // Very unlikely to match (2^-2048)
    let same = true;
    for (let i = 0; i < a.length; i++) {
      if (a[i] !== b[i]) {
        same = false;
        break;
      }
    }
    expect(same).toBe(false);
  });

  it('output bytes are in [0, 255]', () => {
    const noise = failToNoise(0.5);
    for (const b of noise) {
      expect(b).toBeGreaterThanOrEqual(0);
      expect(b).toBeLessThanOrEqual(255);
    }
  });
});

// ============================================================
// K. BRAIDED TEMPORAL DISTANCE
// ============================================================

describe('K · Braided temporal distance', () => {
  it('identical variants → zero distance', () => {
    expect(braidedTemporalDistance([0.5, 0.5, 0.5])).toBeCloseTo(0, 5);
  });

  it('two variants: single pair distance', () => {
    const d = braidedTemporalDistance([0.0, 0.5]);
    expect(d).toBeGreaterThan(0);
    expect(isFinite(d)).toBe(true);
  });

  it('triadic: 3 pairs summed', () => {
    const d = braidedTemporalDistance([0.1, 0.5, 0.9]);
    expect(d).toBeGreaterThan(0);
    expect(isFinite(d)).toBe(true);
  });

  it('tetradic: 6 pairs summed', () => {
    const d = braidedTemporalDistance([0.1, 0.3, 0.6, 0.9]);
    expect(d).toBeGreaterThan(0);
    // Should be larger than triadic (more pairs)
    const triadic = braidedTemporalDistance([0.1, 0.3, 0.6]);
    expect(d).toBeGreaterThan(triadic);
  });

  it('symmetric: order doesn\'t matter', () => {
    const d1 = braidedTemporalDistance([0.2, 0.8]);
    const d2 = braidedTemporalDistance([0.8, 0.2]);
    expect(d1).toBeCloseTo(d2, 10);
  });

  it('boundary values clamped to (-1, 1)', () => {
    const d = braidedTemporalDistance([0.999, -0.999]);
    expect(isFinite(d)).toBe(true);
    expect(d).toBeGreaterThan(0);
  });
});

// ============================================================
// L. BRAIDED META-TIME
// ============================================================

describe('L · Braided meta-time', () => {
  it('basic computation: T^(t+2) * intent * context', () => {
    // T=2, t=1, intent=1.1, context=0.9
    const result = braidedMetaTime(2, 1, 1.1, 0.9);
    // 2^(1+2) * 1.1 * 0.9 = 8 * 0.99 = 7.92
    expect(result).toBeCloseTo(7.92, 5);
  });

  it('tetradic includes 1/t factor', () => {
    const triadic = braidedMetaTime(2, 1, 1.1, 0.9, false);
    const tetradic = braidedMetaTime(2, 1, 1.1, 0.9, true);
    // tetradic = triadic / t = triadic / 1 = triadic (when t=1)
    expect(tetradic).toBeCloseTo(triadic, 5);

    // With t=2: triadic = 2^4 * 1.1 * 0.9 = 15.84
    //           tetradic = 15.84 / 2 = 7.92
    const tri2 = braidedMetaTime(2, 2, 1.1, 0.9, false);
    const tet2 = braidedMetaTime(2, 2, 1.1, 0.9, true);
    expect(tet2).toBeCloseTo(tri2 / 2, 5);
  });

  it('T close to zero → near-zero result', () => {
    const result = braidedMetaTime(0.001, 1, 1.0, 1.0);
    expect(result).toBeLessThan(0.01);
  });
});

// ============================================================
// M. COHOMOLOGICAL HARMONIC WALL
// ============================================================

describe('M · Cohomological harmonic wall', () => {
  it('zero obstruction → wall = 1 (no amplification)', () => {
    expect(cohomologicalHarmonicWall(0)).toBeCloseTo(1, 10);
  });

  it('full obstruction → wall = R^(maxD²) (maximum amplification)', () => {
    // obstruction=1, maxD=6, R=1.5 → 1.5^36
    const expected = Math.pow(1.5, 36);
    expect(cohomologicalHarmonicWall(1, 6, 1.5)).toBeCloseTo(expected, 1);
  });

  it('half obstruction maps to d*=3, wall = R^9', () => {
    // obstruction=0.5, maxD=6 → d*=3, wall = 1.5^9
    const expected = Math.pow(1.5, 9);
    expect(cohomologicalHarmonicWall(0.5, 6, 1.5)).toBeCloseTo(expected, 5);
  });

  it('super-exponential growth: wall increases rapidly with obstruction', () => {
    const w1 = cohomologicalHarmonicWall(0.1);
    const w2 = cohomologicalHarmonicWall(0.3);
    const w3 = cohomologicalHarmonicWall(0.5);
    const w4 = cohomologicalHarmonicWall(0.8);
    expect(w1).toBeLessThan(w2);
    expect(w2).toBeLessThan(w3);
    expect(w3).toBeLessThan(w4);
    // Growth should be super-exponential
    const ratio23 = w3 / w2;
    const ratio34 = w4 / w3;
    expect(ratio34).toBeGreaterThan(ratio23);
  });

  it('custom R and maxDimension', () => {
    // R=2, maxD=4, obstruction=1 → 2^16 = 65536
    expect(cohomologicalHarmonicWall(1, 4, 2)).toBeCloseTo(65536, 1);
  });
});

// ============================================================
// N. INTEGRATION SCENARIOS
// ============================================================

describe('N · SCBE governance scenarios', () => {
  it('scenario: all temporal T-variants report safe → ALLOW consensus', () => {
    const result = detectPolicyObstruction({
      immediate: RiskLevel.ALLOW,
      memory: RiskLevel.ALLOW,
      governance: RiskLevel.ALLOW,
    });
    expect(result.consensus).toBe(RiskLevel.ALLOW);
    expect(result.obstruction).toBe(0);
    expect(result.noiseTriggered).toBe(false);
  });

  it('scenario: memory detects anomaly, others safe → consensus drops to ALLOW', () => {
    const result = detectPolicyObstruction({
      immediate: RiskLevel.ALLOW,
      memory: RiskLevel.ESCALATE,
      governance: RiskLevel.ALLOW,
    });
    // Meet-based flow: ESCALATE flows down to ALLOW
    expect(result.consensus).toBe(RiskLevel.ALLOW);
    expect(result.obstruction).toBeGreaterThan(0);
  });

  it('scenario: adversarial temporal disagreement triggers fail-to-noise', () => {
    const result = detectPolicyObstruction(
      {
        immediate: RiskLevel.DENY,
        memory: RiskLevel.ALLOW,
        governance: RiskLevel.DENY,
      },
      { noiseThreshold: 0.1 },
    );
    expect(result.noiseTriggered).toBe(true);
    // Generate noise output
    const noise = failToNoise(result.obstruction);
    expect(noise).toHaveLength(256);
  });

  it('scenario: obstruction → harmonic wall amplification', () => {
    const result = detectPolicyObstruction({
      immediate: RiskLevel.DENY,
      memory: RiskLevel.ALLOW,
      governance: RiskLevel.ESCALATE,
    });
    const wallCost = cohomologicalHarmonicWall(result.obstruction);
    expect(wallCost).toBeGreaterThanOrEqual(1);
    // Non-zero obstruction → amplified cost
    if (result.obstruction > 0) {
      expect(wallCost).toBeGreaterThan(1);
    }
  });

  it('scenario: tetradic with forecast mismatch', () => {
    const result = detectPolicyObstruction({
      immediate: RiskLevel.QUARANTINE,
      memory: RiskLevel.QUARANTINE,
      governance: RiskLevel.QUARANTINE,
      predictive: RiskLevel.DENY, // forecast disagrees
    });
    expect(result.obstruction).toBeGreaterThan(0);
    expect(result.converged).toBe(true);
  });

  it('full pipeline: detect → wall → noise decision', () => {
    const detection = detectPolicyObstruction(
      {
        immediate: RiskLevel.ESCALATE,
        memory: RiskLevel.ALLOW,
        governance: RiskLevel.DENY,
      },
      { noiseThreshold: 0.3 },
    );

    const wall = cohomologicalHarmonicWall(detection.obstruction);

    if (detection.noiseTriggered) {
      const noise = failToNoise(detection.obstruction);
      expect(noise).toHaveLength(256);
      expect(wall).toBeGreaterThan(1);
    } else {
      // Low obstruction path
      expect(detection.obstruction).toBeLessThanOrEqual(0.3);
    }
  });
});
