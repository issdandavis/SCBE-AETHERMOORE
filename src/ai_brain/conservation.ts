/**
 * @file conservation.ts
 * @module ai_brain/conservation
 * @layer Layer 5, Layer 6, Layer 8, Layer 9, Layer 12
 * @component Conservation Law Enforcement — Maximum Build
 * @version 1.0.0
 * @since 2026-02-11
 *
 * Implements the 6 conservation law projections for the 21D brain state vector,
 * the global invariant I(x), and the RefactorAlign kernel Π(x).
 *
 * Laws:
 *   1. Containment      — Poincaré ball norm clamp (Layer 5)
 *   2. Phase Coherence   — Z_6 snap for Sacred Tongue phases (Layer 6)
 *   3. Energy Balance    — Hamiltonian H = ½‖p‖² + V(q) conservation (Layer 8/12)
 *   4. Lattice Continuity — Valid Hamiltonian path adjacency (Layer 8)
 *   5. Flux Normalization — ν ∈ [0, 1] (Layer 6)
 *   6. Spectral Bounds   — PR ≥ 1, H_entropy ≤ 6.0 (Layer 9)
 *
 * Key result: Π(x) = π₆(π₅(π₄(π₃(π₂(π₁(x))))))
 * is provably idempotent: Π(Π(x)) === Π(x).
 *
 * Each projection operates on disjoint block ranges. π₃ reads BLOCK_HYPER
 * (already clamped by π₁), so a second pass produces no further changes.
 */

import {
  BLOCK_RANGES,
  BRAIN_DIMENSIONS,
  BRAIN_EPSILON,
  type BlockName,
  type ConservationConfig,
  type ConservationLawResult,
  type RefactorAlignResult,
} from './types.js';

import { UnifiedBrainState } from './unified-state.js';

// ═══════════════════════════════════════════════════════════════
// Private Vector Utilities
// ═══════════════════════════════════════════════════════════════

function vecNorm(v: number[]): number {
  let sum = 0;
  for (const x of v) sum += x * x;
  return Math.sqrt(sum);
}

function vecScale(v: number[], s: number): number[] {
  return v.map((x) => x * s);
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

// ═══════════════════════════════════════════════════════════════
// Block Extraction / Replacement
// ═══════════════════════════════════════════════════════════════

/**
 * Extract a named block from the 21D vector.
 */
export function extractBlock(vector: number[], block: BlockName): number[] {
  const range = BLOCK_RANGES[block];
  return vector.slice(range.start, range.end);
}

/**
 * Replace a named block in the 21D vector (returns new vector).
 */
export function replaceBlock(vector: number[], block: BlockName, values: number[]): number[] {
  const range = BLOCK_RANGES[block];
  const expectedLen = range.end - range.start;
  if (values.length !== expectedLen) {
    throw new RangeError(`Block ${block} expects ${expectedLen} values, got ${values.length}`);
  }
  const result = [...vector];
  for (let i = 0; i < values.length; i++) {
    result[range.start + i] = values[i];
  }
  return result;
}

// ═══════════════════════════════════════════════════════════════
// Law 1: Containment (Layer 5)
// ═══════════════════════════════════════════════════════════════

/**
 * Law 1: Containment — clamp ‖u_hyper‖ < 1 in the Poincaré ball.
 *
 * If ‖BLOCK_HYPER‖ ≥ clampNorm, rescale to clampNorm preserving direction.
 * Default clampNorm = 0.95 (matching research report).
 *
 * @param vector - 21D state vector
 * @param clampNorm - Maximum allowed norm (default: 0.95)
 */
export function projectContainment(
  vector: number[],
  clampNorm: number = 0.95
): ConservationLawResult {
  const hyperBlock = extractBlock(vector, 'BLOCK_HYPER');
  const norm = vecNorm(hyperBlock);
  const satisfied = norm < 1.0;
  const violationMagnitude = norm >= clampNorm ? norm - clampNorm : 0;

  let projected: number[];
  if (norm >= clampNorm) {
    const scaled = vecScale(hyperBlock, clampNorm / norm);
    projected = replaceBlock(vector, 'BLOCK_HYPER', scaled);
  } else {
    projected = [...vector];
  }

  return {
    law: 'containment',
    satisfied,
    violationMagnitude: Math.max(0, violationMagnitude),
    projectedVector: projected,
  };
}

// ═══════════════════════════════════════════════════════════════
// Law 2: Phase Coherence (Layer 6)
// ═══════════════════════════════════════════════════════════════

/**
 * Z_6 canonical phases: {0, π/3, 2π/3, π, 4π/3, 5π/3}
 * i.e., {0°, 60°, 120°, 180°, 240°, 300°}
 */
const Z6_PHASES: number[] = Array.from({ length: 6 }, (_, k) => (k * Math.PI) / 3);
const TWO_PI = 2 * Math.PI;

/**
 * Snap a phase angle to the nearest Z_6 element.
 */
function snapToZ6(angle: number): number {
  const normalized = ((angle % TWO_PI) + TWO_PI) % TWO_PI;
  let minDist = Infinity;
  let nearest = 0;
  for (const phi of Z6_PHASES) {
    const dist = Math.min(Math.abs(normalized - phi), TWO_PI - Math.abs(normalized - phi));
    if (dist < minDist) {
      minDist = dist;
      nearest = phi;
    }
  }
  return nearest;
}

/**
 * Compute the angular distance between a phase value and its nearest Z_6 element.
 */
function phaseDeviation(angle: number): number {
  const normalized = ((angle % TWO_PI) + TWO_PI) % TWO_PI;
  let minDist = Infinity;
  for (const phi of Z6_PHASES) {
    const dist = Math.min(Math.abs(normalized - phi), TWO_PI - Math.abs(normalized - phi));
    if (dist < minDist) minDist = dist;
  }
  return minDist;
}

/**
 * Law 2: Phase Coherence — snap all 6 phase dimensions to Z_6.
 *
 * BLOCK_PHASE [6..11] represents phase angles. Each is snapped to the
 * nearest element of Z_6 = {0, 60, 120, 180, 240, 300} degrees.
 *
 * @param vector - 21D state vector
 */
export function projectPhaseCoherence(vector: number[]): ConservationLawResult {
  const phaseBlock = extractBlock(vector, 'BLOCK_PHASE');
  let totalDeviation = 0;

  const snapped = phaseBlock.map((angle) => {
    totalDeviation += phaseDeviation(angle);
    return snapToZ6(angle);
  });

  const satisfied = totalDeviation < BRAIN_EPSILON;
  const projected = replaceBlock(vector, 'BLOCK_PHASE', snapped);

  return {
    law: 'phase_coherence',
    satisfied,
    violationMagnitude: totalDeviation,
    projectedVector: projected,
  };
}

// ═══════════════════════════════════════════════════════════════
// Law 3: Energy Balance (Layer 8/12)
// ═══════════════════════════════════════════════════════════════

/**
 * Law 3: Energy Balance — H = ½‖p‖² + V(q) must be conserved.
 *
 * BLOCK_HAM [12..15] represents momenta p.
 * V(q) is computed from BLOCK_HYPER as a quadratic potential: V(q) = ½‖q‖².
 *
 * If targetEnergy is not provided, the current energy is treated as the
 * target (first call establishes the invariant).
 *
 * @param vector - 21D state vector
 * @param targetEnergy - Target Hamiltonian energy (default: current energy)
 */
export function projectEnergyBalance(
  vector: number[],
  targetEnergy?: number
): ConservationLawResult {
  const hyperBlock = extractBlock(vector, 'BLOCK_HYPER');
  const hamBlock = extractBlock(vector, 'BLOCK_HAM');

  const pNormSq = hamBlock.reduce((s, v) => s + v * v, 0);
  const kinetic = 0.5 * pNormSq;
  const potential = 0.5 * hyperBlock.reduce((s, v) => s + v * v, 0);
  const currentEnergy = kinetic + potential;

  const target = targetEnergy ?? currentEnergy;
  const satisfied = Math.abs(currentEnergy - target) < BRAIN_EPSILON;

  let projected: number[];
  if (!satisfied) {
    const energyDeficit = target - potential;
    if (energyDeficit > BRAIN_EPSILON && pNormSq > BRAIN_EPSILON) {
      // Scale p so that ½‖p'‖² = target - V(q)
      const requiredPNormSq = 2 * Math.max(0, energyDeficit);
      const scaleFactor = Math.sqrt(requiredPNormSq / pNormSq);
      const scaledHam = hamBlock.map((v) => v * scaleFactor);
      projected = replaceBlock(vector, 'BLOCK_HAM', scaledHam);
    } else {
      // Cannot achieve target energy with current potential; zero momenta
      const zeroHam = hamBlock.map(() => 0);
      projected = replaceBlock(vector, 'BLOCK_HAM', zeroHam);
    }
  } else {
    projected = [...vector];
  }

  return {
    law: 'energy_balance',
    satisfied,
    violationMagnitude: Math.abs(currentEnergy - target),
    projectedVector: projected,
  };
}

// ═══════════════════════════════════════════════════════════════
// Law 4: Lattice Continuity (Layer 8)
// ═══════════════════════════════════════════════════════════════

/** Number of canonical polyhedra in the Hamiltonian path */
const LATTICE_SIZE = 16;

/**
 * Law 4: Lattice Continuity — valid Hamiltonian path through adjacency.
 *
 * BLOCK_LATTICE [16..17] represents two indices into the polyhedra lattice.
 * For a valid transition, A[i,j] must equal 1 (adjacent polyhedra).
 *
 * Default adjacency: sequential Hamiltonian path (i adjacent to i±1).
 *
 * @param vector - 21D state vector
 * @param adjacencyMatrix - Custom adjacency (default: sequential path)
 */
export function projectLatticeContinuity(
  vector: number[],
  adjacencyMatrix?: boolean[][]
): ConservationLawResult {
  const latticeBlock = extractBlock(vector, 'BLOCK_LATTICE');

  // Round to integer indices, clamp to [0, N-1]
  const idx0 = clamp(Math.round(latticeBlock[0]), 0, LATTICE_SIZE - 1);
  const idx1 = clamp(Math.round(latticeBlock[1]), 0, LATTICE_SIZE - 1);

  // Check adjacency
  let isAdjacent: boolean;
  if (adjacencyMatrix) {
    isAdjacent = adjacencyMatrix[idx0]?.[idx1] ?? false;
  } else {
    // Default: sequential Hamiltonian path adjacency (self-loop counts as adjacent)
    isAdjacent = Math.abs(idx0 - idx1) <= 1;
  }

  const satisfied = isAdjacent;
  let projectedLattice: number[];

  if (!isAdjacent) {
    // Snap idx1 to nearest neighbor of idx0
    const neighbors = adjacencyMatrix
      ? Array.from({ length: LATTICE_SIZE }, (_, j) => j).filter(
          (j) => adjacencyMatrix[idx0]?.[j]
        )
      : [Math.max(0, idx0 - 1), idx0, Math.min(LATTICE_SIZE - 1, idx0 + 1)];

    const uniqueNeighbors = [...new Set(neighbors)];
    const nearest = uniqueNeighbors.reduce(
      (best, j) => (Math.abs(j - idx1) < Math.abs(best - idx1) ? j : best),
      uniqueNeighbors[0] ?? idx0
    );

    projectedLattice = [idx0, nearest];
  } else {
    projectedLattice = [idx0, idx1];
  }

  const violationMagnitude = isAdjacent ? 0 : Math.abs(idx0 - idx1);
  const projected = replaceBlock(vector, 'BLOCK_LATTICE', projectedLattice);

  return {
    law: 'lattice_continuity',
    satisfied,
    violationMagnitude,
    projectedVector: projected,
  };
}

// ═══════════════════════════════════════════════════════════════
// Law 5: Flux Normalization (Layer 6)
// ═══════════════════════════════════════════════════════════════

/**
 * Law 5: Flux Normalization — ν must be in [0, 1].
 *
 * BLOCK_FLUX [18] is a single scalar representing the breathing/flux value.
 *
 * @param vector - 21D state vector
 */
export function projectFluxNormalization(vector: number[]): ConservationLawResult {
  const fluxBlock = extractBlock(vector, 'BLOCK_FLUX');
  const nu = fluxBlock[0];
  const clamped = clamp(nu, 0, 1);
  const satisfied = nu >= 0 && nu <= 1;
  const violationMagnitude = Math.abs(nu - clamped);

  const projected = replaceBlock(vector, 'BLOCK_FLUX', [clamped]);

  return {
    law: 'flux_normalization',
    satisfied,
    violationMagnitude,
    projectedVector: projected,
  };
}

// ═══════════════════════════════════════════════════════════════
// Law 6: Spectral Bounds (Layer 9)
// ═══════════════════════════════════════════════════════════════

/**
 * Law 6: Spectral Bounds — PR ≥ 1.0, H_entropy ≤ 6.0.
 *
 * BLOCK_SPEC [19..20] represents [participationRatio, spectralEntropy].
 * - PR (participation ratio): must be ≥ 1.0
 * - H (spectral entropy): must be ≤ 6.0 (max for 6 Sacred Tongues system)
 *
 * @param vector - 21D state vector
 * @param prLowerBound - Minimum participation ratio (default: 1.0)
 * @param entropyUpperBound - Maximum spectral entropy (default: 6.0)
 */
export function projectSpectralBounds(
  vector: number[],
  prLowerBound: number = 1.0,
  entropyUpperBound: number = 6.0
): ConservationLawResult {
  const specBlock = extractBlock(vector, 'BLOCK_SPEC');
  const pr = specBlock[0];
  const entropy = specBlock[1];

  const clampedPR = Math.max(prLowerBound, pr);
  const clampedEntropy = Math.min(entropyUpperBound, entropy);

  const prViolation = pr < prLowerBound ? prLowerBound - pr : 0;
  const entropyViolation = entropy > entropyUpperBound ? entropy - entropyUpperBound : 0;
  const violationMagnitude = prViolation + entropyViolation;
  const satisfied = violationMagnitude < BRAIN_EPSILON;

  const projected = replaceBlock(vector, 'BLOCK_SPEC', [clampedPR, clampedEntropy]);

  return {
    law: 'spectral_bounds',
    satisfied,
    violationMagnitude,
    projectedVector: projected,
  };
}

// ═══════════════════════════════════════════════════════════════
// Global Invariant I(x)
// ═══════════════════════════════════════════════════════════════

/**
 * Compute the global invariant I(x) = sum of all violation magnitudes.
 *
 * I(x) = 0 if and only if all 6 conservation laws are satisfied.
 *
 * @param vector - 21D state vector
 * @param config - Conservation configuration
 */
export function computeGlobalInvariant(
  vector: number[],
  config: ConservationConfig = {}
): number {
  const results = [
    projectContainment(vector, config.poincareClampNorm),
    projectPhaseCoherence(vector),
    projectEnergyBalance(vector, config.targetEnergy),
    projectLatticeContinuity(vector, config.adjacencyMatrix),
    projectFluxNormalization(vector),
    projectSpectralBounds(vector, config.prLowerBound, config.entropyUpperBound),
  ];
  return results.reduce((sum, r) => sum + r.violationMagnitude, 0);
}

// ═══════════════════════════════════════════════════════════════
// RefactorAlign Kernel Π(x)
// ═══════════════════════════════════════════════════════════════

/**
 * RefactorAlign kernel Π(x) — composition of all 6 conservation law projections.
 *
 * Π(x) = π₆(π₅(π₄(π₃(π₂(π₁(x))))))
 *
 * Key property: Π is IDEMPOTENT — Π(Π(x)) === Π(x).
 * This holds because each πₖ is a projection onto a convex set,
 * and the blocks are disjoint: πₖ only modifies its own block indices.
 * The sole cross-read (π₃ reads BLOCK_HYPER for potential V(q)) is
 * resolved by applying π₁ first, so BLOCK_HYPER is already stable.
 *
 * @param vector - 21D brain state vector
 * @param config - Conservation configuration
 * @returns RefactorAlignResult with corrected vector and diagnostics
 */
export function refactorAlign(
  vector: number[],
  config: ConservationConfig = {}
): RefactorAlignResult {
  if (vector.length !== BRAIN_DIMENSIONS) {
    throw new RangeError(`Expected ${BRAIN_DIMENSIONS}D vector, got ${vector.length}D`);
  }

  const lawResults: ConservationLawResult[] = [];
  let current = [...vector];

  // π₁: Containment
  const r1 = projectContainment(current, config.poincareClampNorm);
  lawResults.push(r1);
  current = r1.projectedVector;

  // π₂: Phase Coherence
  const r2 = projectPhaseCoherence(current);
  lawResults.push(r2);
  current = r2.projectedVector;

  // π₃: Energy Balance (reads BLOCK_HYPER, already stable from π₁)
  const r3 = projectEnergyBalance(current, config.targetEnergy);
  lawResults.push(r3);
  current = r3.projectedVector;

  // π₄: Lattice Continuity
  const r4 = projectLatticeContinuity(current, config.adjacencyMatrix);
  lawResults.push(r4);
  current = r4.projectedVector;

  // π₅: Flux Normalization
  const r5 = projectFluxNormalization(current);
  lawResults.push(r5);
  current = r5.projectedVector;

  // π₆: Spectral Bounds
  const r6 = projectSpectralBounds(current, config.prLowerBound, config.entropyUpperBound);
  lawResults.push(r6);
  current = r6.projectedVector;

  // Compute global invariant on the OUTPUT (should be 0 after projection)
  const globalInvariant = computeGlobalInvariant(current, config);

  return {
    inputVector: [...vector],
    outputVector: current,
    lawResults,
    globalInvariant,
    allSatisfied: globalInvariant < BRAIN_EPSILON,
  };
}

// ═══════════════════════════════════════════════════════════════
// UnifiedBrainState Integration
// ═══════════════════════════════════════════════════════════════

/**
 * Apply RefactorAlign to a UnifiedBrainState, returning a corrected state.
 *
 * This is the primary integration point: call after any state update
 * to enforce all conservation laws.
 *
 * @param state - UnifiedBrainState to correct
 * @param config - Conservation configuration
 * @returns Corrected state + RefactorAlign diagnostics
 */
export function enforceConservationLaws(
  state: UnifiedBrainState,
  config: ConservationConfig = {}
): { correctedState: UnifiedBrainState; result: RefactorAlignResult } {
  const vector = state.toVector();
  const result = refactorAlign(vector, config);
  const correctedState = UnifiedBrainState.fromVector(result.outputVector);
  return { correctedState, result };
}
