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
import { type BlockName, type ConservationConfig, type ConservationLawResult, type RefactorAlignResult } from './types.js';
import { UnifiedBrainState } from './unified-state.js';
/**
 * Extract a named block from the 21D vector.
 */
export declare function extractBlock(vector: number[], block: BlockName): number[];
/**
 * Replace a named block in the 21D vector (returns new vector).
 */
export declare function replaceBlock(vector: number[], block: BlockName, values: number[]): number[];
/**
 * Law 1: Containment — clamp ‖u_hyper‖ < 1 in the Poincaré ball.
 *
 * If ‖BLOCK_HYPER‖ ≥ clampNorm, rescale to clampNorm preserving direction.
 * Default clampNorm = 0.95 (matching research report).
 *
 * @param vector - 21D state vector
 * @param clampNorm - Maximum allowed norm (default: 0.95)
 */
export declare function projectContainment(vector: number[], clampNorm?: number): ConservationLawResult;
/**
 * Law 2: Phase Coherence — snap all 6 phase dimensions to Z_6.
 *
 * BLOCK_PHASE [6..11] represents phase angles. Each is snapped to the
 * nearest element of Z_6 = {0, 60, 120, 180, 240, 300} degrees.
 *
 * @param vector - 21D state vector
 */
export declare function projectPhaseCoherence(vector: number[]): ConservationLawResult;
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
export declare function projectEnergyBalance(vector: number[], targetEnergy?: number): ConservationLawResult;
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
export declare function projectLatticeContinuity(vector: number[], adjacencyMatrix?: boolean[][]): ConservationLawResult;
/**
 * Law 5: Flux Normalization — ν must be in [0, 1].
 *
 * BLOCK_FLUX [18] is a single scalar representing the breathing/flux value.
 *
 * @param vector - 21D state vector
 */
export declare function projectFluxNormalization(vector: number[]): ConservationLawResult;
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
export declare function projectSpectralBounds(vector: number[], prLowerBound?: number, entropyUpperBound?: number): ConservationLawResult;
/**
 * Compute the global invariant I(x) = sum of all violation magnitudes.
 *
 * I(x) = 0 if and only if all 6 conservation laws are satisfied.
 *
 * @param vector - 21D state vector
 * @param config - Conservation configuration
 */
export declare function computeGlobalInvariant(vector: number[], config?: ConservationConfig): number;
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
export declare function refactorAlign(vector: number[], config?: ConservationConfig): RefactorAlignResult;
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
export declare function enforceConservationLaws(state: UnifiedBrainState, config?: ConservationConfig): {
    correctedState: UnifiedBrainState;
    result: RefactorAlignResult;
};
//# sourceMappingURL=conservation.d.ts.map