/**
 * Tests for Dual Lattice Architecture
 *
 * Covers:
 * - Static lattice projection (6D → 3D)
 * - Dynamic lattice transform (3D → 6D → 3D)
 * - Phason shifts and topology rearrangement
 * - Dual lattice cross-verification
 * - Aperiodic mesh generation
 * - Fractal dimension estimation
 * - Threat-responsive phason creation
 * - Edge cases and invariants
 *
 * @module tests/ai_brain/dual-lattice
 */

import { describe, expect, it, beforeEach } from 'vitest';
import {
  DualLatticeSystem,
  staticProjection,
  dynamicTransform,
  generateAperiodicMesh,
  applyPhasonShift,
  estimateFractalDimension,
  latticeNorm6D,
  latticeDistance3D,
  DEFAULT_DUAL_LATTICE_CONFIG,
  type Lattice6D,
  type Lattice3D,
  type PhasonShift,
} from '../../src/ai_brain/dual-lattice';

// ═══════════════════════════════════════════════════════════════
// Test Helpers
// ═══════════════════════════════════════════════════════════════

function safeState21D(base: number = 0.5): number[] {
  return new Array(21).fill(base);
}

function zeroBrainState(): number[] {
  return new Array(21).fill(0);
}

function origin6D(): Lattice6D {
  return { components: [0, 0, 0, 0, 0, 0] };
}

function unitLattice6D(): Lattice6D {
  return { components: [1, 0, 0, 0, 0, 0] };
}

function zeroPhason(): PhasonShift {
  return { perpShift: [0, 0, 0], magnitude: 0, phase: 0 };
}

function smallPhason(): PhasonShift {
  return { perpShift: [0.1, 0.1, 0.1], magnitude: 0.05, phase: 0 };
}

function largePhason(): PhasonShift {
  return { perpShift: [1, 0, 0], magnitude: 1.0, phase: 0 };
}

// ═══════════════════════════════════════════════════════════════
// Static Lattice Projection (6D → 3D)
// ═══════════════════════════════════════════════════════════════

describe('Static Lattice Projection', () => {
  it('should project origin to near-origin in 3D', () => {
    const result = staticProjection(origin6D());
    expect(Math.abs(result.point3D.x)).toBeLessThan(1e-10);
    expect(Math.abs(result.point3D.y)).toBeLessThan(1e-10);
  });

  it('should accept points within acceptance domain', () => {
    const result = staticProjection(origin6D());
    expect(result.accepted).toBe(true);
    expect(result.boundaryDistance).toBeGreaterThan(0);
  });

  it('should classify tile types', () => {
    const result = staticProjection(origin6D());
    expect(['thick', 'thin']).toContain(result.tileType);
  });

  it('should compute perpendicular component', () => {
    const result = staticProjection(unitLattice6D());
    expect(result.perpComponent).toHaveLength(3);
  });

  it('should produce different projections for different inputs', () => {
    const a = staticProjection({ components: [1, 0, 0, 0, 0, 0] });
    const b = staticProjection({ components: [0, 1, 0, 0, 0, 0] });
    const dist = latticeDistance3D(a.point3D, b.point3D);
    expect(dist).toBeGreaterThan(0);
  });

  it('should have non-negative boundary distance for accepted points', () => {
    const result = staticProjection(origin6D());
    if (result.accepted) {
      expect(result.boundaryDistance).toBeGreaterThanOrEqual(0);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Dynamic Lattice Transform (3D → 6D → 3D)
// ═══════════════════════════════════════════════════════════════

describe('Dynamic Lattice Transform', () => {
  it('should round-trip 3D point with zero phason', () => {
    const point: Lattice3D = { x: 0.5, y: 0.3, z: 0.1 };
    const result = dynamicTransform(point, zeroPhason());
    // With zero phason, displacement should be very small
    expect(result.displacement).toBeLessThan(1e-8);
  });

  it('should produce displacement with non-zero phason', () => {
    const point: Lattice3D = { x: 0.5, y: 0.3, z: 0.1 };
    const result = dynamicTransform(point, smallPhason());
    expect(result.displacement).toBeGreaterThan(0);
  });

  it('should lift to 6D with correct dimensionality', () => {
    const point: Lattice3D = { x: 1, y: 0, z: 0 };
    const result = dynamicTransform(point, zeroPhason());
    expect(result.lifted6D.components).toHaveLength(6);
  });

  it('should detect structure breaking with large phason', () => {
    const point: Lattice3D = { x: 0.5, y: 0.3, z: 0.1 };
    const result = dynamicTransform(point, largePhason());
    expect(result.structurePreserved).toBe(false);
  });

  it('should preserve structure with small phason', () => {
    const point: Lattice3D = { x: 0.5, y: 0.3, z: 0.1 };
    const result = dynamicTransform(point, smallPhason());
    expect(result.structurePreserved).toBe(true);
  });

  it('should compute interference value in [-1, 1]', () => {
    const point: Lattice3D = { x: 0.5, y: 0.3, z: 0.1 };
    const result = dynamicTransform(point, smallPhason());
    expect(result.interferenceValue).toBeGreaterThanOrEqual(-1);
    expect(result.interferenceValue).toBeLessThanOrEqual(1);
  });

  it('should handle origin point gracefully', () => {
    const point: Lattice3D = { x: 0, y: 0, z: 0 };
    const result = dynamicTransform(point, smallPhason());
    expect(isFinite(result.displacement)).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// Phason Shifts
// ═══════════════════════════════════════════════════════════════

describe('Phason Shifts', () => {
  it('should not modify point with zero magnitude', () => {
    const point6D: Lattice6D = { components: [1, 2, 3, 4, 5, 6] };
    const shifted = applyPhasonShift(point6D, zeroPhason());
    for (let i = 0; i < 6; i++) {
      expect(shifted.components[i]).toBeCloseTo(point6D.components[i], 10);
    }
  });

  it('should modify point with non-zero phason', () => {
    const point6D: Lattice6D = { components: [1, 2, 3, 4, 5, 6] };
    const shifted = applyPhasonShift(point6D, smallPhason());
    let anyDifferent = false;
    for (let i = 0; i < 6; i++) {
      if (Math.abs(shifted.components[i] - point6D.components[i]) > 1e-10) {
        anyDifferent = true;
      }
    }
    expect(anyDifferent).toBe(true);
  });

  it('should scale shift by magnitude', () => {
    const point6D: Lattice6D = { components: [1, 0, 0, 0, 0, 0] };
    const shift1: PhasonShift = { perpShift: [1, 0, 0], magnitude: 0.1, phase: 0 };
    const shift2: PhasonShift = { perpShift: [1, 0, 0], magnitude: 0.2, phase: 0 };

    const r1 = applyPhasonShift(point6D, shift1);
    const r2 = applyPhasonShift(point6D, shift2);

    // Larger magnitude → larger displacement
    const d1 = latticeNorm6D({ components: [
      r1.components[0] - 1, r1.components[1], r1.components[2],
      r1.components[3], r1.components[4], r1.components[5],
    ] as [number, number, number, number, number, number] });
    const d2 = latticeNorm6D({ components: [
      r2.components[0] - 1, r2.components[1], r2.components[2],
      r2.components[3], r2.components[4], r2.components[5],
    ] as [number, number, number, number, number, number] });

    expect(d2).toBeGreaterThan(d1);
  });
});

// ═══════════════════════════════════════════════════════════════
// Aperiodic Mesh Generation
// ═══════════════════════════════════════════════════════════════

describe('Aperiodic Mesh Generation', () => {
  it('should generate mesh with accepted vertices', () => {
    const mesh = generateAperiodicMesh(2);
    expect(mesh.length).toBeGreaterThan(0);
    for (const vertex of mesh) {
      expect(vertex.accepted).toBe(true);
    }
  });

  it('should classify all tiles and have at least one type', () => {
    const mesh = generateAperiodicMesh(3);
    const thick = mesh.filter((v) => v.tileType === 'thick');
    const thin = mesh.filter((v) => v.tileType === 'thin');
    // All vertices must have a tile classification
    expect(thick.length + thin.length).toBe(mesh.length);
    // Integer lattice scanning first 3 dims produces valid tile types
    expect(mesh.length).toBeGreaterThan(0);
  });

  it('should grow with radius', () => {
    const mesh2 = generateAperiodicMesh(1);
    const mesh3 = generateAperiodicMesh(2);
    expect(mesh3.length).toBeGreaterThanOrEqual(mesh2.length);
  });

  it('should have non-negative boundary distances', () => {
    const mesh = generateAperiodicMesh(2);
    for (const vertex of mesh) {
      expect(vertex.boundaryDistance).toBeGreaterThanOrEqual(0);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// Dual Lattice System (Both Modes)
// ═══════════════════════════════════════════════════════════════

describe('DualLatticeSystem', () => {
  let system: DualLatticeSystem;

  beforeEach(() => {
    system = new DualLatticeSystem();
  });

  it('should process a 21D state through both lattices', () => {
    const phason = system.createThreatPhason(0);
    const result = system.process(safeState21D(), phason);

    expect(result.static).toBeDefined();
    expect(result.dynamic).toBeDefined();
    expect(result.coherence).toBeGreaterThanOrEqual(0);
    expect(result.coherence).toBeLessThanOrEqual(1);
  });

  it('should validate safe states with zero threat', () => {
    const phason = system.createThreatPhason(0);
    const result = system.process(safeState21D(0.1), phason);
    expect(result.validated).toBe(true);
  });

  it('should compute coherence between static and dynamic', () => {
    const phason = system.createThreatPhason(0.1);
    const result = system.process(safeState21D(), phason);
    expect(result.coherence).toBeGreaterThan(0);
  });

  it('should report triple frequency interference', () => {
    const phason = system.createThreatPhason(0.3);
    const result = system.process(safeState21D(), phason);
    expect(result.tripleFrequencyInterference).toBeDefined();
    expect(isFinite(result.tripleFrequencyInterference)).toBe(true);
  });

  it('should create larger phasons for higher threats', () => {
    const low = system.createThreatPhason(0.1);
    const high = system.createThreatPhason(0.9);
    expect(high.magnitude).toBeGreaterThan(low.magnitude);
  });

  it('should use anomaly dimensions for phason direction', () => {
    const phason1 = system.createThreatPhason(0.5, [0, 1]);
    const phason2 = system.createThreatPhason(0.5, [10, 11]);

    // Different anomaly dimensions → different shift directions
    const dirDiff = Math.abs(phason1.perpShift[0] - phason2.perpShift[0]) +
      Math.abs(phason1.perpShift[1] - phason2.perpShift[1]);
    expect(dirDiff).toBeGreaterThan(0);
  });

  it('should increment step counter', () => {
    expect(system.getStep()).toBe(0);
    system.process(safeState21D(), system.createThreatPhason(0));
    expect(system.getStep()).toBe(1);
    system.process(safeState21D(), system.createThreatPhason(0));
    expect(system.getStep()).toBe(2);
  });

  it('should initialize aperiodic mesh', () => {
    const mesh = system.initializeMesh(2);
    expect(mesh.length).toBeGreaterThan(0);
    expect(system.getMesh()).toBe(mesh);
  });

  it('should reset properly', () => {
    system.process(safeState21D(), system.createThreatPhason(0));
    system.initializeMesh(1);
    system.reset();
    expect(system.getStep()).toBe(0);
    // Mesh survives soft reset
    expect(system.getMesh()).not.toBeNull();
  });

  it('should full reset including mesh', () => {
    system.initializeMesh(1);
    system.fullReset();
    expect(system.getStep()).toBe(0);
    expect(system.getMesh()).toBeNull();
  });

  it('should throw on too-short state', () => {
    expect(() => {
      system.process([0.1, 0.2, 0.3], system.createThreatPhason(0));
    }).toThrow(/at least 6D/);
  });

  it('should handle zero brain state', () => {
    const result = system.process(zeroBrainState(), system.createThreatPhason(0));
    expect(result.static).toBeDefined();
    expect(result.dynamic).toBeDefined();
  });
});

// ═══════════════════════════════════════════════════════════════
// Fractal Dimension Estimation
// ═══════════════════════════════════════════════════════════════

describe('Fractal Dimension Estimation', () => {
  it('should return 0 for too few points', () => {
    const dim = estimateFractalDimension([{ x: 0, y: 0, z: 0 }]);
    expect(dim).toBe(0);
  });

  it('should estimate dimension for a lattice set', () => {
    const mesh = generateAperiodicMesh(3);
    const points = mesh.map((v) => v.point3D);
    if (points.length >= 2) {
      const dim = estimateFractalDimension(points);
      expect(dim).toBeGreaterThan(0);
    }
  });

  it('should estimate dimension from custom scales', () => {
    const points: Lattice3D[] = [];
    for (let i = 0; i < 100; i++) {
      points.push({
        x: Math.cos(i * 0.618) * i * 0.1,
        y: Math.sin(i * 0.618) * i * 0.1,
        z: i * 0.01,
      });
    }
    const dim = estimateFractalDimension(points, [2.0, 1.0, 0.5, 0.25]);
    expect(dim).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Utility Functions
// ═══════════════════════════════════════════════════════════════

describe('Lattice Utilities', () => {
  it('should compute 6D norm', () => {
    expect(latticeNorm6D({ components: [3, 4, 0, 0, 0, 0] })).toBeCloseTo(5, 10);
  });

  it('should compute 3D distance', () => {
    const a: Lattice3D = { x: 0, y: 0, z: 0 };
    const b: Lattice3D = { x: 3, y: 4, z: 0 };
    expect(latticeDistance3D(a, b)).toBeCloseTo(5, 10);
  });

  it('should return 0 for identical points', () => {
    const p: Lattice3D = { x: 1, y: 2, z: 3 };
    expect(latticeDistance3D(p, p)).toBeCloseTo(0, 10);
  });

  it('should compute norm of zero vector as 0', () => {
    expect(latticeNorm6D(origin6D())).toBeCloseTo(0, 10);
  });
});

// ═══════════════════════════════════════════════════════════════
// Cross-Verification & Edge Cases
// ═══════════════════════════════════════════════════════════════

describe('Cross-Verification & Edge Cases', () => {
  it('should produce higher coherence for safe operations', () => {
    const system = new DualLatticeSystem();
    const safePh = system.createThreatPhason(0);
    const safeResult = system.process(safeState21D(0.1), safePh);

    const dangerPh = system.createThreatPhason(0.95);
    const dangerResult = system.process(safeState21D(0.1), dangerPh);

    // Safe operations should have higher coherence
    expect(safeResult.coherence).toBeGreaterThanOrEqual(dangerResult.coherence);
  });

  it('should handle repeated processing', () => {
    const system = new DualLatticeSystem();
    for (let i = 0; i < 20; i++) {
      const ph = system.createThreatPhason(i * 0.05);
      const result = system.process(safeState21D(), ph);
      expect(isFinite(result.coherence)).toBe(true);
    }
  });

  it('should handle custom configuration', () => {
    const system = new DualLatticeSystem({
      acceptanceRadius: 2.0,
      phasonCoupling: 0.5,
      coherenceThreshold: 0.3,
    });
    const ph = system.createThreatPhason(0.5);
    const result = system.process(safeState21D(), ph);
    expect(result).toBeDefined();
  });

  it('should handle exactly 6D state', () => {
    const system = new DualLatticeSystem();
    const state = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5];
    const result = system.process(state, system.createThreatPhason(0));
    expect(result.static).toBeDefined();
  });
});
