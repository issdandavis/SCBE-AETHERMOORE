/**
 * Tests for Polyhedral Hamiltonian Defense Manifold (PHDM)
 *
 * Covers:
 * - Polyhedron topology (Euler characteristic, validity, hashing)
 * - Canonical polyhedra catalogue (16 entries, families)
 * - Hamiltonian path with HMAC key chain
 * - 6D geometry (distance, centroid)
 * - Cubic spline interpolation
 * - Intrusion detection (deviation, skip, curvature attacks)
 * - Flux governance (POLLY / QUASI / DEMI)
 * - Phason shift (6D projection rotation)
 * - Complete PHDM system integration
 */

import { describe, expect, it } from 'vitest';
import {
  CANONICAL_POLYHEDRA,
  CubicSpline6D,
  PHDMDeviationDetector,
  PHDMHamiltonianPath,
  Point6D,
  PolyhedralHamiltonianDefenseManifold,
  Polyhedron,
  computeCentroid,
  distance6D,
  eulerCharacteristic,
  getActivePolyhedra,
  generateProjectionMatrix,
  isValidTopology,
  phasonShift,
  serializePolyhedron,
  topologicalHash,
} from '../../src/harmonic/phdm';

describe('Polyhedron Topology', () => {
  it('should compute Euler characteristic correctly', () => {
    const tetrahedron: Polyhedron = {
      name: 'Tetrahedron',
      vertices: 4,
      edges: 6,
      faces: 4,
      genus: 0,
      family: 'platonic',
    };

    const chi = eulerCharacteristic(tetrahedron);
    expect(chi).toBe(2); // χ = 4 - 6 + 4 = 2
  });

  it('should validate topology for genus 0 polyhedra', () => {
    const cube: Polyhedron = {
      name: 'Cube',
      vertices: 8,
      edges: 12,
      faces: 6,
      genus: 0,
      family: 'platonic',
    };

    expect(isValidTopology(cube)).toBe(true);
    // χ = 8 - 12 + 6 = 2 = 2(1-0) ✓
  });

  it('should validate topology for genus 1 polyhedra', () => {
    const szilassi: Polyhedron = {
      name: 'Szilassi',
      vertices: 7,
      edges: 21,
      faces: 14,
      genus: 1,
      family: 'toroidal',
    };

    expect(isValidTopology(szilassi)).toBe(true);
    // χ = 7 - 21 + 14 = 0 = 2(1-1) ✓
  });

  it('should generate consistent topological hash', () => {
    const dodecahedron: Polyhedron = {
      name: 'Dodecahedron',
      vertices: 20,
      edges: 30,
      faces: 12,
      genus: 0,
      family: 'platonic',
    };

    const hash1 = topologicalHash(dodecahedron);
    const hash2 = topologicalHash(dodecahedron);

    expect(hash1).toBe(hash2);
    expect(hash1).toHaveLength(64); // SHA256 hex = 64 chars
  });

  it('should serialize polyhedron correctly', () => {
    const octahedron: Polyhedron = {
      name: 'Octahedron',
      vertices: 6,
      edges: 12,
      faces: 8,
      genus: 0,
      family: 'platonic',
    };

    const serialized = serializePolyhedron(octahedron);
    const str = serialized.toString('utf-8');

    expect(str).toContain('Octahedron');
    expect(str).toContain('V=6');
    expect(str).toContain('E=12');
    expect(str).toContain('F=8');
    expect(str).toContain('χ=2');
    expect(str).toContain('g=0');
  });
});

describe('Canonical Polyhedra', () => {
  it('should have 16 canonical polyhedra', () => {
    expect(CANONICAL_POLYHEDRA).toHaveLength(16);
  });

  it('should have all Platonic solids', () => {
    const platonicNames = ['Tetrahedron', 'Cube', 'Octahedron', 'Dodecahedron', 'Icosahedron'];

    const names = CANONICAL_POLYHEDRA.map((p) => p.name);
    platonicNames.forEach((name) => {
      expect(names).toContain(name);
    });
  });

  it('should validate all canonical polyhedra', () => {
    CANONICAL_POLYHEDRA.forEach((poly) => {
      expect(isValidTopology(poly)).toBe(true);
    });
  });

  it('should have correct genus values', () => {
    const genus0 = CANONICAL_POLYHEDRA.filter((p) => p.genus === 0);
    const genus1 = CANONICAL_POLYHEDRA.filter((p) => p.genus === 1);
    const genus4 = CANONICAL_POLYHEDRA.filter((p) => p.genus === 4);

    expect(genus0).toHaveLength(12); // Most are genus 0
    expect(genus1).toHaveLength(2); // Szilassi and Csaszar
    expect(genus4).toHaveLength(2); // Kepler-Poinsot stars
  });
});

describe('Hamiltonian Path', () => {
  it('should compute path with HMAC chaining', () => {
    const path = new PHDMHamiltonianPath();
    const masterKey = Buffer.alloc(32); // Proper 32-byte key
    Buffer.from('test-master-key').copy(masterKey);

    const keys = path.computePath(masterKey);

    // Should have 17 keys (initial + 16 polyhedra)
    expect(keys).toHaveLength(17);

    // First key should be master key
    expect(keys[0]).toEqual(masterKey);

    // All keys should be 32 bytes (SHA256)
    keys.forEach((key) => {
      expect(key).toHaveLength(32);
    });
  });

  it('should produce deterministic keys', () => {
    const path1 = new PHDMHamiltonianPath();
    const path2 = new PHDMHamiltonianPath();
    const masterKey = Buffer.from('deterministic-test-key-32-byte!');

    const keys1 = path1.computePath(masterKey);
    const keys2 = path2.computePath(masterKey);

    expect(keys1).toHaveLength(keys2.length);
    keys1.forEach((key, i) => {
      expect(key.equals(keys2[i])).toBe(true);
    });
  });

  it('should verify path integrity', () => {
    const path = new PHDMHamiltonianPath();
    const masterKey = Buffer.from('verification-test-key-32-bytes!');

    const keys = path.computePath(masterKey);
    const finalKey = keys[keys.length - 1];

    expect(path.verifyPath(masterKey, finalKey)).toBe(true);
  });

  it('should reject invalid final key', () => {
    const path = new PHDMHamiltonianPath();
    const masterKey = Buffer.from('rejection-test-key-32-bytes-now');

    path.computePath(masterKey);
    const wrongKey = Buffer.alloc(32, 0xff);

    expect(path.verifyPath(masterKey, wrongKey)).toBe(false);
  });

  it('should get key at specific step', () => {
    const path = new PHDMHamiltonianPath();
    const masterKey = Buffer.from('step-test-key-32-bytes-long-now!');

    path.computePath(masterKey);

    const key0 = path.getKey(0);
    expect(key0).toEqual(masterKey);

    const key5 = path.getKey(5);
    expect(key5).not.toBeNull();
    expect(key5).toHaveLength(32);
  });

  it('should get polyhedron at specific step', () => {
    const path = new PHDMHamiltonianPath();

    const poly0 = path.getPolyhedron(0);
    expect(poly0).not.toBeNull();
    expect(poly0?.name).toBe('Tetrahedron');

    const poly4 = path.getPolyhedron(4);
    expect(poly4?.name).toBe('Icosahedron');
  });
});

describe('6D Geometry', () => {
  it('should compute distance in 6D space', () => {
    const p1: Point6D = { x1: 0, x2: 0, x3: 0, x4: 0, x5: 0, x6: 0 };
    const p2: Point6D = { x1: 1, x2: 0, x3: 0, x4: 0, x5: 0, x6: 0 };

    const dist = distance6D(p1, p2);
    expect(dist).toBeCloseTo(1.0, 5);
  });

  it('should compute distance for diagonal', () => {
    const p1: Point6D = { x1: 0, x2: 0, x3: 0, x4: 0, x5: 0, x6: 0 };
    const p2: Point6D = { x1: 1, x2: 1, x3: 1, x4: 1, x5: 1, x6: 1 };

    const dist = distance6D(p1, p2);
    expect(dist).toBeCloseTo(Math.sqrt(6), 5);
  });

  it('should compute centroid for polyhedron', () => {
    const cube: Polyhedron = {
      name: 'Cube',
      vertices: 8,
      edges: 12,
      faces: 6,
      genus: 0,
      family: 'platonic',
    };

    const centroid = computeCentroid(cube);

    expect(centroid.x1).toBeCloseTo(8 / 30, 5); // vertices / 30
    expect(centroid.x2).toBeCloseTo(12 / 60, 5); // edges / 60
    expect(centroid.x3).toBeCloseTo(6 / 32, 5); // faces / 32
    expect(centroid.x4).toBeCloseTo(2 / 2, 5); // chi / 2
    expect(centroid.x5).toBe(0); // genus
  });
});

describe('Cubic Spline Interpolation', () => {
  it('should interpolate through control points', () => {
    const points: Point6D[] = [
      { x1: 0, x2: 0, x3: 0, x4: 0, x5: 0, x6: 0 },
      { x1: 1, x2: 1, x3: 1, x4: 1, x5: 1, x6: 1 },
      { x1: 2, x2: 0, x3: 2, x4: 0, x5: 2, x6: 0 },
    ];

    const spline = new CubicSpline6D(points);

    // Should pass through first point
    const p0 = spline.evaluate(0);
    expect(p0.x1).toBeCloseTo(0, 2);

    // Should pass through last point
    const p1 = spline.evaluate(1);
    expect(p1.x1).toBeCloseTo(2, 2);
  });

  it('should compute derivatives', () => {
    const points: Point6D[] = [
      { x1: 0, x2: 0, x3: 0, x4: 0, x5: 0, x6: 0 },
      { x1: 1, x2: 1, x3: 1, x4: 1, x5: 1, x6: 1 },
    ];

    const spline = new CubicSpline6D(points);
    const derivative = spline.derivative(0.5);

    // Derivative should be positive (moving forward)
    expect(derivative.x1).toBeGreaterThan(0);
  });

  it('should compute curvature', () => {
    const points: Point6D[] = [
      { x1: 0, x2: 0, x3: 0, x4: 0, x5: 0, x6: 0 },
      { x1: 1, x2: 0, x3: 0, x4: 0, x5: 0, x6: 0 },
      { x1: 2, x2: 0, x3: 0, x4: 0, x5: 0, x6: 0 },
    ];

    const spline = new CubicSpline6D(points);
    const curvature = spline.curvature(0.5);

    // Straight line should have near-zero curvature
    expect(curvature).toBeLessThan(0.1);
  });
});

describe('Intrusion Detection', () => {
  it('should detect deviation attack', () => {
    const detector = new PHDMDeviationDetector(CANONICAL_POLYHEDRA, 0.05, 0.5); // Lower threshold

    // Normal state (on geodesic)
    const normalState = computeCentroid(CANONICAL_POLYHEDRA[0]);
    const normalResult = detector.detect(normalState, 0);
    expect(normalResult.deviation).toBeLessThan(0.05);

    // Attacked state (off geodesic)
    const attackedState: Point6D = {
      x1: normalState.x1 + 1.0, // Large deviation
      x2: normalState.x2,
      x3: normalState.x3,
      x4: normalState.x4,
      x5: normalState.x5,
      x6: normalState.x6,
    };
    const attackResult = detector.detect(attackedState, 0);
    expect(attackResult.isIntrusion).toBe(true);
    expect(attackResult.deviation).toBeGreaterThan(0.05);
  });

  it('should compute threat velocity', () => {
    const detector = new PHDMDeviationDetector();
    const state = computeCentroid(CANONICAL_POLYHEDRA[0]);

    // First detection
    const result1 = detector.detect(state, 0);
    expect(result1.threatVelocity).toBe(0); // No history yet

    // Second detection with deviation
    const attackedState: Point6D = {
      ...state,
      x1: state.x1 + 0.5,
    };
    const result2 = detector.detect(attackedState, 0.1);
    expect(Math.abs(result2.threatVelocity)).toBeGreaterThan(0);
  });

  it('should generate rhythm pattern', () => {
    const detector = new PHDMDeviationDetector();
    const results = detector.simulateAttack('deviation', 0.5);

    const pattern = PHDMDeviationDetector.getRhythmPattern(results);

    expect(pattern).toHaveLength(16);
    expect(pattern).toMatch(/^[01]+$/); // Only 0s and 1s
    expect(pattern).toContain('0'); // Should detect some attacks
  });

  it('should detect skip attack', () => {
    const detector = new PHDMDeviationDetector();
    const results = detector.simulateAttack('skip', 1.0);

    // Should detect intrusion at skip point
    const hasIntrusion = results.some((r) => r.isIntrusion);
    expect(hasIntrusion).toBe(true);
  });

  it('should detect curvature attack', () => {
    const detector = new PHDMDeviationDetector();
    const results = detector.simulateAttack('curvature', 1.0);

    // Should detect high curvature
    const hasHighCurvature = results.some((r) => r.curvature > 0.5);
    expect(hasHighCurvature).toBe(true);
  });
});

describe('Complete PHDM System', () => {
  it('should initialize with master key', () => {
    const phdm = new PolyhedralHamiltonianDefenseManifold();
    const masterKey = Buffer.from('phdm-test-key-32-bytes-long-now!');

    const keys = phdm.initialize(masterKey);

    expect(keys).toHaveLength(17);
    expect(keys[0]).toEqual(masterKey);
  });

  it('should monitor state', () => {
    const phdm = new PolyhedralHamiltonianDefenseManifold();
    phdm.initialize(Buffer.from('monitor-test-key-32-bytes-long!!'));

    const state = computeCentroid(CANONICAL_POLYHEDRA[0]);
    const result = phdm.monitor(state, 0);

    expect(result).toHaveProperty('isIntrusion');
    expect(result).toHaveProperty('deviation');
    expect(result).toHaveProperty('threatVelocity');
    expect(result).toHaveProperty('curvature');
    expect(result).toHaveProperty('rhythmPattern');
  });

  it('should simulate attacks', () => {
    const phdm = new PolyhedralHamiltonianDefenseManifold();

    const deviationResults = phdm.simulateAttack('deviation', 0.5);
    const skipResults = phdm.simulateAttack('skip', 1.0);
    const curvatureResults = phdm.simulateAttack('curvature', 1.0);

    expect(deviationResults).toHaveLength(16);
    expect(skipResults).toHaveLength(16);
    expect(curvatureResults).toHaveLength(16);

    // All should detect some intrusions
    expect(deviationResults.some((r) => r.isIntrusion)).toBe(true);
    expect(skipResults.some((r) => r.isIntrusion)).toBe(true);
    expect(curvatureResults.some((r) => r.isIntrusion)).toBe(true);
  });

  it('should get polyhedra', () => {
    const phdm = new PolyhedralHamiltonianDefenseManifold();
    const polyhedra = phdm.getPolyhedra();

    expect(polyhedra).toHaveLength(16);
    expect(polyhedra[0].name).toBe('Tetrahedron');
  });
});

describe('Property-Based Tests', () => {
  it('should maintain Euler characteristic invariance', () => {
    CANONICAL_POLYHEDRA.forEach((poly) => {
      const chi = eulerCharacteristic(poly);
      const expected = 2 * (1 - poly.genus);
      expect(chi).toBe(expected);
    });
  });

  it('should produce deterministic HMAC chains', () => {
    const masterKey = Buffer.from('property-test-key-32-bytes-now!!');

    const path1 = new PHDMHamiltonianPath();
    const path2 = new PHDMHamiltonianPath();

    const keys1 = path1.computePath(masterKey);
    const keys2 = path2.computePath(masterKey);

    keys1.forEach((key, i) => {
      expect(key.equals(keys2[i])).toBe(true);
    });
  });

  it('should have smooth geodesic (C² continuity)', () => {
    const centroids = CANONICAL_POLYHEDRA.map(computeCentroid);
    const spline = new CubicSpline6D(centroids);

    // Sample curvature at multiple points
    const curvatures: number[] = [];
    for (let t = 0; t <= 1; t += 0.1) {
      curvatures.push(spline.curvature(t));
    }

    // Curvature should be finite (no discontinuities)
    curvatures.forEach((k) => {
      expect(Number.isFinite(k)).toBe(true);
      expect(k).toBeGreaterThanOrEqual(0);
    });
  });

  it('should have all canonical polyhedra with family classification', () => {
    CANONICAL_POLYHEDRA.forEach((poly) => {
      expect(poly.family).toBeDefined();
      expect([
        'platonic', 'archimedean', 'kepler-poinsot', 'toroidal', 'johnson', 'rhombic',
      ]).toContain(poly.family);
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// Flux Governance
// ═══════════════════════════════════════════════════════════════

describe('Flux Governance', () => {
  it('should return all 16 polyhedra in POLLY mode', () => {
    const active = getActivePolyhedra('POLLY');
    expect(active).toHaveLength(16);
  });

  it('should return only Platonic + Archimedean (8) in QUASI mode', () => {
    const active = getActivePolyhedra('QUASI');
    expect(active).toHaveLength(8);
    active.forEach((p) => {
      expect(['platonic', 'archimedean']).toContain(p.family);
    });
  });

  it('should return only Platonic (5) in DEMI mode', () => {
    const active = getActivePolyhedra('DEMI');
    expect(active).toHaveLength(5);
    active.forEach((p) => {
      expect(p.family).toBe('platonic');
    });
  });

  it('should preserve containment hierarchy: DEMI ⊂ QUASI ⊂ POLLY', () => {
    const demi = getActivePolyhedra('DEMI');
    const quasi = getActivePolyhedra('QUASI');
    const polly = getActivePolyhedra('POLLY');

    expect(demi.length).toBeLessThan(quasi.length);
    expect(quasi.length).toBeLessThan(polly.length);

    // All DEMI polyhedra should be in QUASI
    const quasiNames = new Set(quasi.map((p) => p.name));
    demi.forEach((p) => {
      expect(quasiNames.has(p.name)).toBe(true);
    });

    // All QUASI polyhedra should be in POLLY
    const pollyNames = new Set(polly.map((p) => p.name));
    quasi.forEach((p) => {
      expect(pollyNames.has(p.name)).toBe(true);
    });
  });

  it('should work with custom polyhedra list', () => {
    const subset: Polyhedron[] = [
      { name: 'A', vertices: 4, edges: 6, faces: 4, genus: 0, family: 'platonic' },
      { name: 'B', vertices: 12, edges: 18, faces: 8, genus: 0, family: 'archimedean' },
    ];
    expect(getActivePolyhedra('DEMI', subset)).toHaveLength(1);
    expect(getActivePolyhedra('QUASI', subset)).toHaveLength(2);
  });
});

// ═══════════════════════════════════════════════════════════════
// Phason Shift
// ═══════════════════════════════════════════════════════════════

describe('Phason Shift', () => {
  it('should generate a 3x6 projection matrix', () => {
    const matrix = generateProjectionMatrix();
    expect(matrix).toHaveLength(3);
    matrix.forEach((row) => {
      expect(row).toHaveLength(6);
      row.forEach((val) => expect(Number.isFinite(val)).toBe(true));
    });
  });

  it('should produce identity-like result for theta=0', () => {
    const matrix = generateProjectionMatrix();
    const shifted = phasonShift(matrix, 0);
    // theta=0 → cos=1, sin=0 → identity rotation → no change
    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 6; c++) {
        expect(shifted[r][c]).toBeCloseTo(matrix[r][c], 10);
      }
    }
  });

  it('should change the projection for non-zero theta', () => {
    const matrix = generateProjectionMatrix();
    const shifted = phasonShift(matrix, Math.PI / 4);

    // At least some entries should differ
    let anyDifferent = false;
    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 6; c++) {
        if (Math.abs(shifted[r][c] - matrix[r][c]) > 1e-10) {
          anyDifferent = true;
        }
      }
    }
    expect(anyDifferent).toBe(true);
  });

  it('should preserve row norms (rotation is norm-preserving)', () => {
    const matrix = generateProjectionMatrix();
    const shifted = phasonShift(matrix, Math.PI / 3, 2, 4);

    for (let r = 0; r < 3; r++) {
      const origNorm = Math.sqrt(matrix[r].reduce((s, v) => s + v * v, 0));
      const shiftNorm = Math.sqrt(shifted[r].reduce((s, v) => s + v * v, 0));
      expect(shiftNorm).toBeCloseTo(origNorm, 8);
    }
  });

  it('should compose: two half-rotations ≈ one full rotation', () => {
    const matrix = generateProjectionMatrix();
    const half1 = phasonShift(matrix, Math.PI / 6);
    const half2 = phasonShift(half1, Math.PI / 6);
    const full = phasonShift(matrix, Math.PI / 3);

    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 6; c++) {
        expect(half2[r][c]).toBeCloseTo(full[r][c], 8);
      }
    }
  });

  it('should support rotation in different planes', () => {
    const matrix = generateProjectionMatrix();
    const shift01 = phasonShift(matrix, Math.PI / 4, 0, 1);
    const shift34 = phasonShift(matrix, Math.PI / 4, 3, 4);

    // Different planes → different results
    let anyDifferent = false;
    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 6; c++) {
        if (Math.abs(shift01[r][c] - shift34[r][c]) > 1e-10) {
          anyDifferent = true;
        }
      }
    }
    expect(anyDifferent).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// PHDM System — Flux + Phason Integration
// ═══════════════════════════════════════════════════════════════

describe('PHDM Flux + Phason Integration', () => {
  it('should start in POLLY mode with all 16 polyhedra', () => {
    const phdm = new PolyhedralHamiltonianDefenseManifold();
    expect(phdm.fluxState).toBe('POLLY');
    expect(phdm.activeCount).toBe(16);
  });

  it('should switch to QUASI mode (8 polyhedra)', () => {
    const phdm = new PolyhedralHamiltonianDefenseManifold();
    phdm.setFluxState('QUASI');
    expect(phdm.fluxState).toBe('QUASI');
    expect(phdm.activeCount).toBe(8);
    phdm.getActivePolyhedra().forEach((p) => {
      expect(['platonic', 'archimedean']).toContain(p.family);
    });
  });

  it('should switch to DEMI mode (5 polyhedra)', () => {
    const phdm = new PolyhedralHamiltonianDefenseManifold();
    phdm.setFluxState('DEMI');
    expect(phdm.fluxState).toBe('DEMI');
    expect(phdm.activeCount).toBe(5);
  });

  it('should rebuild path after flux state change', () => {
    const phdm = new PolyhedralHamiltonianDefenseManifold();
    const masterKey = Buffer.from('flux-rekey-test-32-bytes-long!!X');

    // Initialize in POLLY (17 keys: master + 16)
    const pollyKeys = phdm.initialize(masterKey);
    expect(pollyKeys).toHaveLength(17);

    // Switch to DEMI and re-initialize (6 keys: master + 5)
    phdm.setFluxState('DEMI');
    const demiKeys = phdm.initialize(masterKey);
    expect(demiKeys).toHaveLength(6);
  });

  it('should execute phason shift', () => {
    const phdm = new PolyhedralHamiltonianDefenseManifold();
    const before = phdm.getProjectionMatrix();

    phdm.executePhasonShift(Math.PI / 4);
    const after = phdm.getProjectionMatrix();

    // Matrix should change
    let anyDifferent = false;
    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 6; c++) {
        if (Math.abs(before[r][c] - after[r][c]) > 1e-10) {
          anyDifferent = true;
        }
      }
    }
    expect(anyDifferent).toBe(true);
  });

  it('should project 6D points to 3D', () => {
    const phdm = new PolyhedralHamiltonianDefenseManifold();
    const point: Point6D = { x1: 1, x2: 0, x3: 0, x4: 0, x5: 0, x6: 0 };

    const proj = phdm.projectTo3D(point);
    expect(proj).toHaveLength(3);
    proj.forEach((v) => expect(Number.isFinite(v)).toBe(true));
  });

  it('should change projections after phason shift', () => {
    const phdm = new PolyhedralHamiltonianDefenseManifold();
    const point: Point6D = { x1: 0.5, x2: 0.3, x3: 0.1, x4: 0.2, x5: 0.4, x6: 0.6 };

    const before = phdm.projectTo3D(point);
    phdm.executePhasonShift(Math.PI / 3);
    const after = phdm.projectTo3D(point);

    // At least one coordinate should differ
    const anyDifferent = before.some((v, i) => Math.abs(v - after[i]) > 1e-10);
    expect(anyDifferent).toBe(true);
  });

  it('should monitor state after flux state change', () => {
    const phdm = new PolyhedralHamiltonianDefenseManifold();
    phdm.setFluxState('QUASI');
    phdm.initialize(Buffer.from('monitor-after-flux-test-32bytes!'));

    const state = computeCentroid(CANONICAL_POLYHEDRA[0]); // Tetrahedron
    const result = phdm.monitor(state, 0);

    expect(result).toHaveProperty('isIntrusion');
    expect(result).toHaveProperty('deviation');
  });
});
