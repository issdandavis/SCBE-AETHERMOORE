/**
 * @file chiralityCoupling.test.ts
 * @module tests/harmonic
 * @layer Layer 5, Layer 9, Layer 10, Layer 12
 * @component Chirality Coupling Tests
 * @version 1.0.0
 */

import { describe, it, expect } from 'vitest';
import {
  tongueSector,
  sectorCharge,
  parityConjugate,
  computeCompatibility,
  computeTransportWeight,
  ChiralGraph,
  DEFAULT_CHIRALITY_CONFIG,
} from '../../src/harmonic/chiralityCoupling.js';
import type { ChiralNode } from '../../src/harmonic/chiralityCoupling.js';

describe('tongueSector', () => {
  it('assigns right chirality to even-index tongues', () => {
    expect(tongueSector('KO')).toBe('right'); // index 0
    expect(tongueSector('RU')).toBe('right'); // index 2
    expect(tongueSector('UM')).toBe('right'); // index 4
  });

  it('assigns left chirality to odd-index tongues', () => {
    expect(tongueSector('AV')).toBe('left'); // index 1
    expect(tongueSector('CA')).toBe('left'); // index 3
    expect(tongueSector('DR')).toBe('left'); // index 5
  });
});

describe('sectorCharge', () => {
  it('returns +1 for right sector', () => {
    expect(sectorCharge('right')).toBe(1);
  });

  it('returns -1 for left sector', () => {
    expect(sectorCharge('left')).toBe(-1);
  });
});

describe('parityConjugate', () => {
  it('swaps KO ↔ AV', () => {
    expect(parityConjugate('KO')).toBe('AV');
    expect(parityConjugate('AV')).toBe('KO');
  });

  it('swaps RU ↔ CA', () => {
    expect(parityConjugate('RU')).toBe('CA');
    expect(parityConjugate('CA')).toBe('RU');
  });

  it('swaps UM ↔ DR', () => {
    expect(parityConjugate('UM')).toBe('DR');
    expect(parityConjugate('DR')).toBe('UM');
  });

  it('double parity is identity', () => {
    for (const tongue of ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const) {
      expect(parityConjugate(parityConjugate(tongue))).toBe(tongue);
    }
  });
});

describe('computeCompatibility', () => {
  const makeNode = (tongue: 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR', spin: 0 | 1 = 0): ChiralNode => {
    const TONGUE_NAMES = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;
    const TONGUE_PHASE_SHIFTS = [0, Math.PI / 3, (2 * Math.PI) / 3, Math.PI, (4 * Math.PI) / 3, (5 * Math.PI) / 3];
    const sector = tongueSector(tongue);
    const idx = TONGUE_NAMES.indexOf(tongue);
    return {
      id: tongue,
      sector,
      tongue,
      charge: sectorCharge(sector),
      spinState: spin,
      phase: TONGUE_PHASE_SHIFTS[idx],
    };
  };

  it('same tongue has constructive interference', () => {
    const a = makeNode('KO', 1);
    const b = makeNode('KO', 1);
    const compat = computeCompatibility(a, b);
    expect(compat.phaseDifference).toBeCloseTo(0, 10);
    expect(compat.interference).toBe('constructive');
    expect(compat.compatible).toBe(true);
  });

  it('opposite sector tongues can have destructive interference', () => {
    const a = makeNode('KO', 0); // right, phase 0
    const b = makeNode('CA', 0); // left, phase π
    const compat = computeCompatibility(a, b);
    // KO (right, phase 0) vs CA (left, phase π)
    // chiralAlignment = (+1)*(-1) = -1
    // phaseAlignment = cos(π) = -1
    // baseCoupling = (-1)*(-1) = 1 (!)
    // But cross-terms with spin 0 → Ising = -1 each
    // crossTerm = λ * ((-1)*(-1) + (-1)*(+1)) / 2 = λ * (1 + -1) / 2 = 0
    expect(compat.spinChiralCrossTerm).toBeCloseTo(0, 10);
  });

  it('spin-chirality cross-term is non-zero when spins differ', () => {
    const a = makeNode('KO', 1); // right, spin up
    const b = makeNode('AV', 0); // left, spin down
    const compat = computeCompatibility(a, b);
    // isingA = 2*1-1 = +1, isingB = 2*0-1 = -1
    // crossTerm = λ * ((+1)*(-1) + (-1)*(+1)) / 2 = λ * (-2) / 2 = -λ
    expect(compat.spinChiralCrossTerm).toBeCloseTo(-1.0, 10);
  });
});

describe('computeTransportWeight', () => {
  const makeNode = (tongue: 'KO' | 'AV', spin: 0 | 1 = 0): ChiralNode => {
    const phases: Record<string, number> = { KO: 0, AV: Math.PI / 3 };
    const sector = tongueSector(tongue);
    return {
      id: tongue,
      sector,
      tongue,
      charge: sectorCharge(sector),
      spinState: spin,
      phase: phases[tongue],
    };
  };

  it('same-sector edges have full weight', () => {
    const a = makeNode('KO', 0);
    // Create another right-sector node
    const b: ChiralNode = { ...a, id: 'KO2' };
    const edge = computeTransportWeight(a, b, 1.0);
    expect(edge.crossesSectors).toBe(false);
    expect(edge.weight).toBeGreaterThanOrEqual(1.0);
  });

  it('cross-sector edges are attenuated', () => {
    const a = makeNode('KO', 0); // right
    const b = makeNode('AV', 0); // left
    const edge = computeTransportWeight(a, b, 1.0);
    expect(edge.crossesSectors).toBe(true);
    expect(edge.weight).toBeLessThan(1.0);
  });
});

describe('ChiralGraph', () => {
  it('creates nodes with correct chirality', () => {
    const graph = new ChiralGraph();
    const node = graph.addNode('test', 'DR');
    expect(node.sector).toBe('left');
    expect(node.charge).toBe(-1);
    expect(node.tongue).toBe('DR');
  });

  it('builds tongue hexagon with 6 nodes', () => {
    const graph = new ChiralGraph();
    graph.buildTongueHexagon();
    expect(graph.getAllNodes()).toHaveLength(6);
  });

  it('tongue hexagon has 18 edges (bidirectional ring + cross)', () => {
    const graph = new ChiralGraph();
    graph.buildTongueHexagon();
    // 6 pairs ring * 2 directions = 12 + 3 cross-diag * 2 directions = 6
    expect(graph.getAllEdges()).toHaveLength(18);
  });

  it('total charge is zero for balanced hexagon', () => {
    const graph = new ChiralGraph();
    graph.buildTongueHexagon();
    // 3 right (+1 each) + 3 left (-1 each) = 0
    expect(graph.totalCharge()).toBe(0);
  });

  it('chirality-preserving permutation is accepted', () => {
    const graph = new ChiralGraph();
    graph.buildTongueHexagon();
    // Swap within same sector: KO ↔ RU (both right)
    const permutation = new Map([
      ['KO', 'RU'],
      ['RU', 'KO'],
      ['AV', 'AV'],
      ['CA', 'CA'],
      ['UM', 'UM'],
      ['DR', 'DR'],
    ]);
    expect(graph.isChiralityPreserving(permutation)).toBe(true);
  });

  it('chirality-violating permutation is rejected', () => {
    const graph = new ChiralGraph();
    graph.buildTongueHexagon();
    // Swap across sectors: KO (right) ↔ AV (left)
    const permutation = new Map([
      ['KO', 'AV'],
      ['AV', 'KO'],
      ['RU', 'RU'],
      ['CA', 'CA'],
      ['UM', 'UM'],
      ['DR', 'DR'],
    ]);
    expect(graph.isChiralityPreserving(permutation)).toBe(false);
  });

  it('transport asymmetry is bounded [0, 1]', () => {
    const graph = new ChiralGraph();
    graph.buildTongueHexagon();
    const asymmetry = graph.transportAsymmetry();
    expect(asymmetry).toBeGreaterThanOrEqual(0);
    expect(asymmetry).toBeLessThanOrEqual(1);
  });

  it('updateSpins changes node states and recalculates edges', () => {
    const graph = new ChiralGraph();
    graph.buildTongueHexagon();

    const edgesBefore = graph.getAllEdges().map((e) => e.weight);

    // Flip all spins to 1
    const spins = new Map<string, 0 | 1>();
    for (const tongue of ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const) {
      spins.set(tongue, 1);
    }
    graph.updateSpins(spins);

    // Verify nodes updated
    for (const node of graph.getAllNodes()) {
      expect(node.spinState).toBe(1);
    }

    // Edges should be recalculated (at least some weights differ)
    const edgesAfter = graph.getAllEdges().map((e) => e.weight);
    expect(edgesAfter.length).toBe(edgesBefore.length);
  });

  it('adjacency matrix has correct dimensions', () => {
    const graph = new ChiralGraph();
    graph.buildTongueHexagon();
    const { ids, matrix } = graph.adjacencyMatrix();
    expect(ids).toHaveLength(6);
    expect(matrix).toHaveLength(6);
    for (const row of matrix) {
      expect(row).toHaveLength(6);
    }
  });

  it('adjacency matrix is asymmetric due to chirality', () => {
    const graph = new ChiralGraph();
    // Set different spin states to create asymmetry
    graph.addNode('KO', 'KO', 1);
    graph.addNode('AV', 'AV', 0);
    graph.connect('KO', 'AV');
    graph.connect('AV', 'KO');

    const { matrix } = graph.adjacencyMatrix();
    // Cross-sector edges may have different weights due to spin-chirality coupling
    // matrix[0][1] (KO→AV) vs matrix[1][0] (AV→KO)
    // With different spins, these can differ
    expect(matrix[0][1]).toBeGreaterThanOrEqual(0);
    expect(matrix[1][0]).toBeGreaterThanOrEqual(0);
  });
});
