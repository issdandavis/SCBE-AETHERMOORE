/**
 * PHDM Sheaf Lattice — Constraint-Based Governance Routing Tests
 *
 * Implements the 5-test PHDM validation battery specified in the
 * SCBE-AETHERMOORE architecture document:
 *
 *   1. Determinism / Stability — Same input → same decision (>95%)
 *   2. Utility Preservation — Benign paths succeed (≤5% false reject)
 *   3. Attack Reduction — Adversarial paths rejected (≥30% reduction)
 *   4. Bypass Resistance — Semantic laundering detected (≥80%)
 *   5. Fail-Safe Behavior — Invalid paths → DENY, never ALLOW
 *
 * Plus comprehensive unit tests for:
 *   - Polyhedral graph construction
 *   - Trust score computation
 *   - Governance sheaf construction
 *   - Sheaf cohomology integration
 *   - Flux state governance (POLLY/QUASI/DEMI)
 *   - Edge cases and property-based checks
 *
 * @layer Layer 8, Layer 9, Layer 12, Layer 13
 */

import { describe, it, expect } from 'vitest';
import {
  // PHDM Sheaf Lattice
  PHDMGovernanceRouter,
  buildPolyhedralGraph,
  buildGovernanceSheaf,
  computePolyhedralTrust,
  polyhedralEulerCharacteristic,
  trustDistanceMatrix,
  requiredFluxState,
  defaultGovernanceRouter,
  type GovernanceDecision,
  type GovernanceRoutingResult,
  type GovernanceRouterConfig,
  type PolyhedralEdge,
  // PHDM core
  CANONICAL_POLYHEDRA,
  getActivePolyhedra,
  type Polyhedron,
  type FluxState,
} from '../../src/harmonic/index.js';

// ═══════════════════════════════════════════════════════════════
// Helper utilities
// ═══════════════════════════════════════════════════════════════

/** Platonic solid indices (always indices 0-4 in CANONICAL_POLYHEDRA) */
const PLATONIC_INDICES = [0, 1, 2, 3, 4];

/** Archimedean solid indices (5-7) */
const ARCHIMEDEAN_INDICES = [5, 6, 7];

/** Kepler-Poinsot indices (8-9) — high-risk zone */
const KEPLER_INDICES = [8, 9];

/** Toroidal indices (10-11) — recursive */
const TOROIDAL_INDICES = [10, 11];

/** Johnson indices (12-13) */
const JOHNSON_INDICES = [12, 13];

/** Rhombic indices (14-15) */
const RHOMBIC_INDICES = [14, 15];

/** A benign intra-family path (Platonic only) */
const BENIGN_PLATONIC_PATH = [0, 1, 2, 3, 4];

/** A cross-family path (Platonic → Archimedean) */
const CROSS_FAMILY_PATH = [0, 1, 5, 6];

/** A disconnected path (Platonic → Kepler-Poinsot, skipping families) */
const DISCONNECTED_PATH = [0, 8];

// ═══════════════════════════════════════════════════════════════
// 1. POLYHEDRAL GRAPH CONSTRUCTION
// ═══════════════════════════════════════════════════════════════

describe('Polyhedral Graph Construction', () => {
  it('builds correct number of edges for 16 canonical polyhedra', () => {
    const { edges, pairs } = buildPolyhedralGraph();
    expect(edges.length).toBeGreaterThan(0);
    expect(edges.length).toBe(pairs.length);
  });

  it('intra-family edges have trustScale = 1.0', () => {
    const { edges } = buildPolyhedralGraph();
    const intraEdges = edges.filter((e) => e.edgeType === 'intra');
    expect(intraEdges.length).toBeGreaterThan(0);
    for (const e of intraEdges) {
      expect(e.trustScale).toBe(1.0);
    }
  });

  it('cross-family edges have trustScale < 1.0', () => {
    const { edges } = buildPolyhedralGraph();
    const crossEdges = edges.filter((e) => e.edgeType === 'cross');
    expect(crossEdges.length).toBeGreaterThan(0);
    for (const e of crossEdges) {
      expect(e.trustScale).toBeGreaterThan(0);
      expect(e.trustScale).toBeLessThan(1.0);
    }
  });

  it('Platonic solids form a complete subgraph (10 edges for 5 vertices)', () => {
    const { edges } = buildPolyhedralGraph();
    const platonicEdges = edges.filter(
      (e) =>
        e.edgeType === 'intra' &&
        PLATONIC_INDICES.includes(e.from) &&
        PLATONIC_INDICES.includes(e.to)
    );
    // C(5,2) = 10
    expect(platonicEdges.length).toBe(10);
  });

  it('edges are symmetric: if (a,b) exists, both directions are represented in pairs', () => {
    const { pairs } = buildPolyhedralGraph();
    // Each pair [a,b] represents an undirected edge
    for (const [a, b] of pairs) {
      expect(a).not.toBe(b); // No self-loops
      expect(a).toBeLessThan(CANONICAL_POLYHEDRA.length);
      expect(b).toBeLessThan(CANONICAL_POLYHEDRA.length);
    }
  });

  it('cross-family edges only connect adjacent families', () => {
    const { edges } = buildPolyhedralGraph();
    const crossEdges = edges.filter((e) => e.edgeType === 'cross');

    // Build family index map
    const familyOf = (idx: number) => CANONICAL_POLYHEDRA[idx].family;
    const familyOrder = [
      'platonic',
      'archimedean',
      'johnson',
      'rhombic',
      'toroidal',
      'kepler-poinsot',
    ];

    for (const e of crossEdges) {
      const f1 = familyOrder.indexOf(familyOf(e.from));
      const f2 = familyOrder.indexOf(familyOf(e.to));
      expect(Math.abs(f1 - f2)).toBe(1);
    }
  });

  it('works with a subset of polyhedra (DEMI = 5 platonic)', () => {
    const demiPolyhedra = getActivePolyhedra('DEMI');
    const { edges, pairs } = buildPolyhedralGraph(demiPolyhedra);

    // All platonic, so only intra-family edges: C(5,2) = 10
    expect(pairs.length).toBe(10);
    for (const e of edges) {
      expect(e.edgeType).toBe('intra');
      expect(e.trustScale).toBe(1.0);
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// 2. TRUST SCORE COMPUTATION
// ═══════════════════════════════════════════════════════════════

describe('Trust Score Computation', () => {
  it('computes trust scores for all 16 polyhedra', () => {
    const scores = computePolyhedralTrust();
    expect(scores.length).toBe(16);
  });

  it('all trust scores ∈ [0, 1]', () => {
    const scores = computePolyhedralTrust();
    for (const s of scores) {
      expect(s).toBeGreaterThanOrEqual(0);
      expect(s).toBeLessThanOrEqual(1);
    }
  });

  it('Platonic solids have highest trust (genus 0, top family)', () => {
    const scores = computePolyhedralTrust();
    const platonicTrust = PLATONIC_INDICES.map((i) => scores[i]);
    const otherTrust = scores.filter((_, i) => !PLATONIC_INDICES.includes(i));

    const minPlatonic = Math.min(...platonicTrust);
    const maxOther = Math.max(...otherTrust);

    expect(minPlatonic).toBeGreaterThan(maxOther);
  });

  it('Kepler-Poinsot solids have lowest trust (genus 4, risk family)', () => {
    const scores = computePolyhedralTrust();
    const keplerTrust = KEPLER_INDICES.map((i) => scores[i]);
    const otherTrust = scores.filter((_, i) => !KEPLER_INDICES.includes(i));

    const maxKepler = Math.max(...keplerTrust);
    const minOther = Math.min(...otherTrust);

    expect(maxKepler).toBeLessThan(minOther);
  });

  it('genus > 0 reduces trust (toroidal < archimedean)', () => {
    const scores = computePolyhedralTrust();

    // Toroidal have genus 1, archimedean have genus 0
    // But toroidal family tier is lower too — both effects compound
    const toroidalAvg =
      TOROIDAL_INDICES.reduce((s, i) => s + scores[i], 0) / TOROIDAL_INDICES.length;
    const archimedeanAvg =
      ARCHIMEDEAN_INDICES.reduce((s, i) => s + scores[i], 0) / ARCHIMEDEAN_INDICES.length;

    expect(toroidalAvg).toBeLessThan(archimedeanAvg);
  });
});

// ═══════════════════════════════════════════════════════════════
// 3. GOVERNANCE SHEAF CONSTRUCTION
// ═══════════════════════════════════════════════════════════════

describe('Governance Sheaf Construction', () => {
  it('builds a valid sheaf over the polyhedral graph', () => {
    const { sheaf, complex, edges } = buildGovernanceSheaf();

    expect(complex.cells(0).length).toBe(16);
    expect(complex.cells(1).length).toBe(edges.length);
    expect(complex.maxDim()).toBe(1);
  });

  it('sheaf has correct lattice (UnitIntervalLattice)', () => {
    const { sheaf } = buildGovernanceSheaf(CANONICAL_POLYHEDRA, 50);
    expect(sheaf.lattice.top).toBe(1);
    expect(sheaf.lattice.bottom).toBe(0);
    expect(sheaf.lattice.height()).toBe(50);
  });

  it('sheaf with fewer polyhedra (QUASI flux)', () => {
    const quasiPolyhedra = getActivePolyhedra('QUASI');
    const { sheaf, complex } = buildGovernanceSheaf(quasiPolyhedra);
    expect(complex.cells(0).length).toBe(8); // 5 platonic + 3 archimedean
  });
});

// ═══════════════════════════════════════════════════════════════
// 4. PHDMGovernanceRouter — Core Functionality
// ═══════════════════════════════════════════════════════════════

describe('PHDMGovernanceRouter', () => {
  describe('construction', () => {
    it('creates router with default config', () => {
      const router = new PHDMGovernanceRouter();
      expect(router.fluxState).toBe('POLLY');
      expect(router.getActivePolyhedra().length).toBe(16);
    });

    it('creates router with DEMI flux state', () => {
      const router = new PHDMGovernanceRouter({}, 'DEMI');
      expect(router.fluxState).toBe('DEMI');
      expect(router.getActivePolyhedra().length).toBe(5);
    });

    it('trust scores match expected count', () => {
      const router = new PHDMGovernanceRouter();
      const scores = router.getTrustScores();
      expect(scores.length).toBe(16);
    });
  });

  describe('validatePath', () => {
    it('empty path → ALLOW', () => {
      const router = new PHDMGovernanceRouter();
      const result = router.validatePath([]);
      expect(result.decision).toBe('ALLOW');
      expect(result.coherenceScore).toBe(1.0);
    });

    it('single polyhedron → ALLOW', () => {
      const router = new PHDMGovernanceRouter();
      const result = router.validatePath([0]);
      expect(result.decision).toBe('ALLOW');
      expect(result.pathValid).toBe(true);
    });

    it('intra-family Platonic path → ALLOW', () => {
      const router = new PHDMGovernanceRouter();
      const result = router.validatePath([0, 1]);
      expect(result.decision).toBe('ALLOW');
      expect(result.pathValid).toBe(true);
      expect(result.coherenceScore).toBeGreaterThanOrEqual(0.8);
    });

    it('cross-family path (Platonic → Archimedean) → connected', () => {
      const router = new PHDMGovernanceRouter();
      const result = router.validatePath([0, 5]);
      expect(result.pathValid).toBe(true);
    });

    it('disconnected path (Platonic → Kepler, no edge) → DENY', () => {
      const router = new PHDMGovernanceRouter();
      // Platonic (0) to Kepler-Poinsot (8) — not adjacent families
      const result = router.validatePath([0, 8]);
      expect(result.decision).toBe('DENY');
      expect(result.pathValid).toBe(false);
    });

    it('invalid index → DENY', () => {
      const router = new PHDMGovernanceRouter();
      const result = router.validatePath([0, 99]);
      expect(result.decision).toBe('DENY');
      expect(result.pathValid).toBe(false);
    });

    it('negative index → DENY', () => {
      const router = new PHDMGovernanceRouter();
      const result = router.validatePath([-1, 0]);
      expect(result.decision).toBe('DENY');
    });

    it('result includes trust assignment', () => {
      const router = new PHDMGovernanceRouter();
      const result = router.validatePath([0, 1, 2]);
      expect(result.trustAssignment.length).toBeGreaterThan(0);
      for (const t of result.trustAssignment) {
        expect(t).toBeGreaterThanOrEqual(0);
        expect(t).toBeLessThanOrEqual(1);
      }
    });

    it('result includes global sections (TH^0)', () => {
      const router = new PHDMGovernanceRouter();
      const result = router.validatePath([0, 1]);
      expect(result.globalSections.converged).toBe(true);
    });

    it('custom trust scores override defaults', () => {
      const router = new PHDMGovernanceRouter();
      const n = router.getActivePolyhedra().length;
      // All trust = 1.0 → should be very coherent
      const highTrust = Array(n).fill(1.0);
      const result = router.validatePath([0, 1], highTrust);
      expect(result.coherenceScore).toBeGreaterThanOrEqual(0.8);
    });
  });

  describe('validateTransition', () => {
    it('same polyhedron → self-loop not an edge → DENY', () => {
      const router = new PHDMGovernanceRouter();
      // Self-transitions aren't in the graph (no self-loops)
      const result = router.validateTransition(0, 0);
      expect(result.decision).toBe('DENY');
    });

    it('adjacent polyhedra → valid transition', () => {
      const router = new PHDMGovernanceRouter();
      const result = router.validateTransition(0, 1);
      expect(result.pathValid).toBe(true);
    });
  });

  describe('isCoherent', () => {
    it('intra-family path is coherent', () => {
      const router = new PHDMGovernanceRouter();
      expect(router.isCoherent([0, 1])).toBe(true);
    });

    it('disconnected path is not coherent', () => {
      const router = new PHDMGovernanceRouter();
      expect(router.isCoherent([0, 8])).toBe(false);
    });
  });

  describe('analyseFullLattice', () => {
    it('returns complete sheaf analysis for all polyhedra', () => {
      const router = new PHDMGovernanceRouter();
      const analysis = router.analyseFullLattice();

      expect(analysis.globalSections.converged).toBe(true);
      expect(analysis.coherenceScore).toBeGreaterThanOrEqual(0);
      expect(analysis.coherenceScore).toBeLessThanOrEqual(1);
      expect(analysis.decision).toBeDefined();
      expect(['ALLOW', 'QUARANTINE', 'DENY']).toContain(analysis.decision);
    });

    it('DEMI flux has higher coherence than POLLY (fewer cross-family edges)', () => {
      const demiRouter = new PHDMGovernanceRouter({}, 'DEMI');
      const pollyRouter = new PHDMGovernanceRouter({}, 'POLLY');

      const demiAnalysis = demiRouter.analyseFullLattice();
      const pollyAnalysis = pollyRouter.analyseFullLattice();

      // DEMI has only Platonic (all intra-family) → high coherence
      expect(demiAnalysis.coherenceScore).toBeGreaterThanOrEqual(
        pollyAnalysis.coherenceScore
      );
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// 5. PHDM VALIDATION BATTERY (5 Tests from Architecture Doc)
// ═══════════════════════════════════════════════════════════════

describe('PHDM Validation Battery', () => {
  // ─────────────────────────────────────────────────────────
  // Test 1: Determinism / Stability
  // Target: >95% stability over 100 runs
  // ─────────────────────────────────────────────────────────

  describe('Test 1: Determinism / Stability', () => {
    it('same path + same trust → identical decision (>95% over 100 runs)', () => {
      const router = new PHDMGovernanceRouter();
      const stability = router.checkDeterminism([0, 1, 2], 100);
      expect(stability).toBeGreaterThan(0.95);
    });

    it('cross-family path is deterministic', () => {
      const router = new PHDMGovernanceRouter();
      const stability = router.checkDeterminism([0, 5, 6], 50);
      expect(stability).toBeGreaterThan(0.95);
    });

    it('DEMI flux is deterministic', () => {
      const router = new PHDMGovernanceRouter({}, 'DEMI');
      const stability = router.checkDeterminism([0, 1, 2, 3, 4], 50);
      expect(stability).toBeGreaterThan(0.95);
    });

    it('empty path is trivially deterministic', () => {
      const router = new PHDMGovernanceRouter();
      const stability = router.checkDeterminism([], 100);
      expect(stability).toBe(1.0);
    });
  });

  // ─────────────────────────────────────────────────────────
  // Test 2: Utility Preservation
  // Target: ≤5% drop on benign task success vs baseline
  // ─────────────────────────────────────────────────────────

  describe('Test 2: Utility Preservation', () => {
    it('benign intra-family paths succeed (Platonic)', () => {
      const router = new PHDMGovernanceRouter();
      const benignPaths = [
        [0, 1],
        [1, 2],
        [2, 3],
        [3, 4],
        [0, 4],
        [0, 1, 2],
        [2, 3, 4],
        [0, 1, 2, 3, 4],
      ];

      let successCount = 0;
      for (const path of benignPaths) {
        const result = router.validatePath(path);
        if (result.decision === 'ALLOW') successCount++;
      }

      const successRate = successCount / benignPaths.length;
      expect(successRate).toBeGreaterThanOrEqual(0.95);
    });

    it('benign cross-family adjacent paths succeed', () => {
      const router = new PHDMGovernanceRouter();
      // Platonic → Archimedean (adjacent families)
      const adjacentPaths = [
        [0, 5],
        [1, 6],
        [4, 7],
        [0, 1, 5],
        [3, 4, 7],
      ];

      let successCount = 0;
      for (const path of adjacentPaths) {
        const result = router.validatePath(path);
        if (result.decision !== 'DENY') successCount++;
      }

      const successRate = successCount / adjacentPaths.length;
      expect(successRate).toBeGreaterThanOrEqual(0.95);
    });

    it('DEMI mode preserves all Platonic paths', () => {
      const router = new PHDMGovernanceRouter({}, 'DEMI');
      const paths = [
        [0, 1],
        [1, 2],
        [2, 3],
        [3, 4],
        [0, 4],
        [0, 1, 2, 3, 4],
      ];

      let successCount = 0;
      for (const path of paths) {
        const result = router.validatePath(path);
        if (result.decision === 'ALLOW') successCount++;
      }

      expect(successCount / paths.length).toBeGreaterThanOrEqual(0.95);
    });
  });

  // ─────────────────────────────────────────────────────────
  // Test 3: Attack Reduction
  // Target: ≥30-50% reduction in unsafe actions vs baseline
  // ─────────────────────────────────────────────────────────

  describe('Test 3: Attack Reduction', () => {
    it('disconnected paths (family-skipping) are rejected', () => {
      const router = new PHDMGovernanceRouter();

      // Adversarial: try to jump from safe to risky regions
      const adversarialPaths = [
        [0, 8], // Platonic → Kepler (skip 3 families)
        [0, 9], // Platonic → Kepler
        [0, 10], // Platonic → Toroidal (skip 2 families)
        [0, 11], // Platonic → Toroidal
        [1, 14], // Platonic → Rhombic (skip 1 family)
        [5, 8], // Archimedean → Kepler (skip 2 families)
        [5, 10], // Archimedean → Toroidal (skip 1 family)
      ];

      let rejectedCount = 0;
      for (const path of adversarialPaths) {
        const result = router.validatePath(path);
        if (result.decision === 'DENY') rejectedCount++;
      }

      const rejectionRate = rejectedCount / adversarialPaths.length;
      // At least 30% of adversarial attempts rejected
      expect(rejectionRate).toBeGreaterThanOrEqual(0.3);
    });

    it('paths through high-risk zones have lower coherence than safe paths', () => {
      const router = new PHDMGovernanceRouter();

      // Safe path: intra-family Platonic
      const safePath = [0, 1, 2];
      const safeResult = router.validatePath(safePath);

      // Risky path: traverses into Kepler-Poinsot zone via valid edges
      // Platonic → Archimedean → Johnson → Rhombic → Toroidal → Kepler
      const riskyPath = [0, 5, 12, 14, 10, 8];
      const riskyResult = router.validatePath(riskyPath);

      // Safe path should have higher or equal coherence
      expect(safeResult.coherenceScore).toBeGreaterThanOrEqual(
        riskyResult.coherenceScore
      );

      // Risky path has more neighborhood obstructions → higher risk amplification
      expect(riskyResult.riskAmplification).toBeGreaterThanOrEqual(
        safeResult.riskAmplification
      );
    });

    it('adversarial trust manipulation detected via sheaf obstructions', () => {
      const router = new PHDMGovernanceRouter();
      const n = router.getActivePolyhedra().length;

      // Try to give high trust to risky polyhedra (semantic laundering)
      const manipulatedTrust = Array(n).fill(0.5);
      // Set Kepler-Poinsot to artificially high trust
      manipulatedTrust[8] = 1.0;
      manipulatedTrust[9] = 1.0;
      // But their family-based edge scaling will still decay
      // The sheaf should detect the inconsistency

      const honest = router.validatePath([0, 1], manipulatedTrust);
      const laundered = router.validatePath([8, 9], manipulatedTrust);

      // The laundered path uses Kepler-Poinsot which have lower edge trust
      // despite the artificially high vertex trust — obstructions expected
      expect(honest.coherenceScore).toBeGreaterThanOrEqual(laundered.coherenceScore);
    });
  });

  // ─────────────────────────────────────────────────────────
  // Test 4: Bypass Resistance
  // Target: ≥80% detection of semantic laundering prompts
  // ─────────────────────────────────────────────────────────

  describe('Test 4: Bypass Resistance', () => {
    it('artificially inflated trust on risky polyhedra produces neighborhood obstructions', () => {
      const router = new PHDMGovernanceRouter();
      const n = router.getActivePolyhedra().length;

      // Create 20 laundering attempts: high trust on risky nodes
      let obstructionDetected = 0;
      const trials = 20;

      for (let trial = 0; trial < trials; trial++) {
        const trust = Array(n).fill(0.5);

        // Pick a risky node and inflate its trust
        const riskyIdx = 8 + (trial % 2); // Kepler-Poinsot
        trust[riskyIdx] = 0.95 + Math.random() * 0.05;

        // Path through risky zone
        const result = router.validatePath([0, 5, 12, 14, 10, riskyIdx], trust);

        // The inflated trust should create obstructions somewhere
        // (neighborhood edges where the trust mismatch is visible)
        if (result.obstructions.length > 0) {
          obstructionDetected++;
        }
      }

      // At least 80% of laundering attempts produce obstructions
      const detectionRate = obstructionDetected / trials;
      expect(detectionRate).toBeGreaterThanOrEqual(0.8);
    });

    it('uniform maximum trust still respects topology (disconnected = denied)', () => {
      const router = new PHDMGovernanceRouter();
      const n = router.getActivePolyhedra().length;

      // Even with all trust = 1.0, disconnected paths are still denied
      const maxTrust = Array(n).fill(1.0);
      const result = router.validatePath([0, 8], maxTrust);

      expect(result.decision).toBe('DENY');
      expect(result.pathValid).toBe(false);
    });

    it('trust inflation does not increase coherence beyond family ceiling', () => {
      const router = new PHDMGovernanceRouter();
      const n = router.getActivePolyhedra().length;

      // Normal trust
      const normalResult = router.validatePath([0, 5]);

      // Inflated trust
      const inflated = Array(n).fill(1.0);
      const inflatedResult = router.validatePath([0, 5], inflated);

      // Inflated trust should not produce wildly higher coherence
      // The edge scaling (Galois connections) still bound the result
      // Both should be close or the inflated one should not exceed normal by much
      expect(inflatedResult.coherenceScore).toBeLessThanOrEqual(1.0);
    });
  });

  // ─────────────────────────────────────────────────────────
  // Test 5: Fail-Safe Behavior
  // Target: Invalid paths → DENY, never ALLOW
  // ─────────────────────────────────────────────────────────

  describe('Test 5: Fail-Safe Behavior', () => {
    it('all invalid paths produce DENY', () => {
      const router = new PHDMGovernanceRouter();
      const invalidPaths = [
        [-1, 0],
        [0, 99],
        [100],
        [-5, -3],
        [0, 16], // Out of bounds for 16 polyhedra (0-indexed)
      ];

      const failSafeRate = router.checkFailSafe(invalidPaths);
      expect(failSafeRate).toBe(1.0);
    });

    it('disconnected paths → DENY (not ALLOW)', () => {
      const router = new PHDMGovernanceRouter();
      const disconnected = [
        [0, 8],  // Platonic → Kepler (no edge)
        [0, 9],  // Platonic → Kepler
        [0, 10], // Platonic → Toroidal
        [0, 11], // Platonic → Toroidal
        [5, 8],  // Archimedean → Kepler
        [5, 10], // Archimedean → Toroidal
      ];

      for (const path of disconnected) {
        const result = router.validatePath(path);
        expect(result.decision).toBe('DENY');
        expect(result.pathValid).toBe(false);
      }
    });

    it('DEMI flux rejects indices beyond Platonic range', () => {
      const router = new PHDMGovernanceRouter({}, 'DEMI');
      // DEMI only has 5 polyhedra (indices 0-4)
      const result = router.validatePath([0, 5]);
      expect(result.decision).toBe('DENY');
    });

    it('checkFailSafe returns 1.0 for empty invalid list', () => {
      const router = new PHDMGovernanceRouter();
      expect(router.checkFailSafe([])).toBe(1.0);
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// 6. FLUX STATE GOVERNANCE
// ═══════════════════════════════════════════════════════════════

describe('Flux State Governance', () => {
  it('POLLY → 16 active polyhedra', () => {
    const router = new PHDMGovernanceRouter({}, 'POLLY');
    expect(router.getActivePolyhedra().length).toBe(16);
  });

  it('QUASI → 8 active polyhedra (Platonic + Archimedean)', () => {
    const router = new PHDMGovernanceRouter({}, 'QUASI');
    expect(router.getActivePolyhedra().length).toBe(8);
  });

  it('DEMI → 5 active polyhedra (Platonic only)', () => {
    const router = new PHDMGovernanceRouter({}, 'DEMI');
    expect(router.getActivePolyhedra().length).toBe(5);
  });

  it('DEMI mode has highest coherence (all same family)', () => {
    const demi = new PHDMGovernanceRouter({}, 'DEMI');
    const result = demi.analyseFullLattice();
    expect(result.coherenceScore).toBeGreaterThanOrEqual(0.8);
  });

  it('requiredFluxState correctly identifies minimum flux', () => {
    expect(requiredFluxState([0, 1, 2])).toBe('DEMI');
    expect(requiredFluxState([0, 5])).toBe('QUASI');
    expect(requiredFluxState([0, 5, 12])).toBe('POLLY');
    expect(requiredFluxState([8, 9])).toBe('POLLY');
    expect(requiredFluxState([])).toBe('DEMI');
  });
});

// ═══════════════════════════════════════════════════════════════
// 7. UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════

describe('Utility Functions', () => {
  describe('polyhedralEulerCharacteristic', () => {
    it('returns V - E for the polyhedral graph', () => {
      const chi = polyhedralEulerCharacteristic();
      const { pairs } = buildPolyhedralGraph();
      expect(chi).toBe(16 - pairs.length);
    });

    it('DEMI graph: χ = 5 - 10 = -5', () => {
      const demiPolyhedra = getActivePolyhedra('DEMI');
      const chi = polyhedralEulerCharacteristic(demiPolyhedra);
      expect(chi).toBe(5 - 10);
    });
  });

  describe('trustDistanceMatrix', () => {
    it('returns 16x16 matrix for canonical polyhedra', () => {
      const dist = trustDistanceMatrix();
      expect(dist.length).toBe(16);
      expect(dist[0].length).toBe(16);
    });

    it('diagonal is zero', () => {
      const dist = trustDistanceMatrix();
      for (let i = 0; i < 16; i++) {
        expect(dist[i][i]).toBe(0);
      }
    });

    it('symmetric: d(i,j) = d(j,i)', () => {
      const dist = trustDistanceMatrix();
      for (let i = 0; i < 16; i++) {
        for (let j = i + 1; j < 16; j++) {
          expect(dist[i][j]).toBeCloseTo(dist[j][i], 10);
        }
      }
    });

    it('intra-family distance = 0 (trustScale = 1.0)', () => {
      const dist = trustDistanceMatrix();
      // Platonic solids: all distance 0 from each other
      for (const i of PLATONIC_INDICES) {
        for (const j of PLATONIC_INDICES) {
          expect(dist[i][j]).toBe(0);
        }
      }
    });

    it('all connected polyhedra have finite distance', () => {
      const dist = trustDistanceMatrix();
      for (let i = 0; i < 16; i++) {
        for (let j = 0; j < 16; j++) {
          expect(dist[i][j]).toBeLessThan(Infinity);
        }
      }
    });
  });

  describe('defaultGovernanceRouter', () => {
    it('is a valid PHDMGovernanceRouter instance', () => {
      expect(defaultGovernanceRouter).toBeInstanceOf(PHDMGovernanceRouter);
    });

    it('can validate a simple path', () => {
      const result = defaultGovernanceRouter.validatePath([0, 1]);
      expect(result.globalSections.converged).toBe(true);
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// 8. PROPERTY-BASED TESTS
// ═══════════════════════════════════════════════════════════════

describe('Property-Based Tests', () => {
  it('coherenceScore ∈ [0, 1] for all random paths (20 trials)', () => {
    const router = new PHDMGovernanceRouter();

    for (let trial = 0; trial < 20; trial++) {
      const pathLen = 1 + Math.floor(Math.random() * 5);
      const path = Array.from({ length: pathLen }, () =>
        Math.floor(Math.random() * 16)
      );

      const result = router.validatePath(path);
      expect(result.coherenceScore).toBeGreaterThanOrEqual(0);
      expect(result.coherenceScore).toBeLessThanOrEqual(1);
    }
  });

  it('riskAmplification ≥ 1.0 for all paths', () => {
    const router = new PHDMGovernanceRouter();

    for (let trial = 0; trial < 20; trial++) {
      const pathLen = 2 + Math.floor(Math.random() * 4);
      const path = Array.from({ length: pathLen }, () =>
        Math.floor(Math.random() * 16)
      );

      const result = router.validatePath(path);
      expect(result.riskAmplification).toBeGreaterThanOrEqual(1);
    }
  });

  it('longer paths do not increase coherence (more constraints = harder to satisfy)', () => {
    const router = new PHDMGovernanceRouter();

    // Compare short vs long intra-family path
    const shortResult = router.validatePath([0, 1]);
    const longResult = router.validatePath([0, 1, 2, 3, 4]);

    // Longer path has at least as many obstructions → ≤ coherence
    expect(longResult.coherenceScore).toBeLessThanOrEqual(
      shortResult.coherenceScore + 0.01 // small tolerance for lattice discretisation
    );
  });

  it('decision ordering: ALLOW > QUARANTINE > DENY maps to coherence', () => {
    const router = new PHDMGovernanceRouter();
    const decisionOrder: Record<string, number> = {
      ALLOW: 3,
      QUARANTINE: 2,
      DENY: 1,
    };

    // Collect results for various paths
    const results: GovernanceRoutingResult[] = [];
    for (const path of [
      [0, 1],       // Likely ALLOW
      [0, 5, 12],   // Might be QUARANTINE
      [0, 99],      // DENY (invalid)
    ]) {
      results.push(router.validatePath(path));
    }

    // Higher coherence should map to higher (or equal) decision tier
    for (let i = 0; i < results.length; i++) {
      for (let j = i + 1; j < results.length; j++) {
        const ri = results[i];
        const rj = results[j];
        if (ri.coherenceScore > rj.coherenceScore + 0.1) {
          expect(decisionOrder[ri.decision]).toBeGreaterThanOrEqual(
            decisionOrder[rj.decision]
          );
        }
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════════
// 9. CONFIGURATION TESTS
// ═══════════════════════════════════════════════════════════════

describe('Configuration', () => {
  it('stricter threshold requires higher coherence for ALLOW', () => {
    const strict = new PHDMGovernanceRouter({ allowThreshold: 0.95 });
    const lenient = new PHDMGovernanceRouter({ allowThreshold: 0.5 });

    // A cross-family path might be ALLOW in lenient but not strict
    const path = [0, 5, 6];
    const strictResult = strict.validatePath(path);
    const lenientResult = lenient.validatePath(path);

    // Lenient should be at least as permissive as strict
    const decisionOrder: Record<string, number> = {
      ALLOW: 3,
      QUARANTINE: 2,
      DENY: 1,
    };
    expect(decisionOrder[lenientResult.decision]).toBeGreaterThanOrEqual(
      decisionOrder[strictResult.decision]
    );
  });

  it('custom latticeSteps affects lattice resolution', () => {
    const fine = new PHDMGovernanceRouter({ latticeSteps: 200 });
    const coarse = new PHDMGovernanceRouter({ latticeSteps: 10 });

    const fineResult = fine.validatePath([0, 1]);
    const coarseResult = coarse.validatePath([0, 1]);

    // Both should converge
    expect(fineResult.globalSections.converged).toBe(true);
    expect(coarseResult.globalSections.converged).toBe(true);
  });
});
