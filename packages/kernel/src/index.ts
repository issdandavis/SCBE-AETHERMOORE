/**
 * @file index.ts
 * @module kernel
 * @layer Layer 1-14
 * @component SCBE Kernel — Pure Math Engine
 * @version 3.2.4
 *
 * The kernel is the "seed" of SCBE-AETHERMOORE.
 *
 * Zero npm dependencies. Zero Node.js APIs. Pure mathematics.
 * Can run in any JavaScript runtime: Node, browser, Deno, Bun, edge workers.
 *
 * Note: Individual modules should be imported directly for full access.
 * This barrel exports a curated subset to avoid name collisions.
 * For modules with overlapping names (triMechanismDetector, sacredEggs,
 * fluxState, etc.), import directly from the specific file.
 */

// ═══════════════════════════════════════════════════════════════
// Foundation — no conflicts, safe to re-export
// ═══════════════════════════════════════════════════════════════

export * from './constants.js';
export * from './assertions.js';
export * from './governance-types.js';
// scbe_voxel_types.js excluded from barrel — Decision type conflicts
// with pipeline14. Import directly.
// export * from './scbe_voxel_types.js';

// ═══════════════════════════════════════════════════════════════
// Core Geometry (L5-L8)
// ═══════════════════════════════════════════════════════════════

export * from './hyperbolic.js';
export * from './adaptiveNavigator.js';
export * from './hamiltonianCFI.js';

// ═══════════════════════════════════════════════════════════════
// 14-Layer Pipeline
// ═══════════════════════════════════════════════════════════════

// pipeline14.js excluded from barrel — exports conflicting aliases
// (hyperbolicDistance, mobiusAdd, Decision). Import directly.
export * from './harmonicScaling.js';
export * from './halAttention.js';
export * from './audioAxis.js';
export * from './vacuumAcoustics.js';

// ═══════════════════════════════════════════════════════════════
// Temporal System
// ═══════════════════════════════════════════════════════════════

export * from './temporalIntent.js';
export * from './temporalPhase.js';

// ═══════════════════════════════════════════════════════════════
// CHSFN & Voxel (no conflicts with above)
// ═══════════════════════════════════════════════════════════════

export * from './chsfn.js';
export * from './quasiSphereOverlap.js';
export * from './securityInvariants.js';
export * from './triDirectionalPlanner.js';
// hyperbolicRAG.js excluded from barrel — projectToBall conflicts
// with hyperbolic.js. Import directly.
// export * from './hyperbolicRAG.js';
export * from './entropicLayer.js';
export * from './quasiSphereSlice.js';

// ═══════════════════════════════════════════════════════════════
// PQC & Quasicrystal
// ═══════════════════════════════════════════════════════════════

export * from './pqc.js';
export * from './qcLattice.js';
export * from './spectral-identity.js';

// ═══════════════════════════════════════════════════════════════
// Modules with name collisions — import directly from file:
//   ./sacredTongues.js      (TONGUES conflicts with languesMetric)
//   ./languesMetric.js      (Decision, Tongue, FluxState conflicts)
//   ./spiralSeal.js         (imports sacredTongues)
//   ./triMechanismDetector.js (hyperbolicDistance, DEFAULT_CONFIG conflicts)
//   ./sacredEggs.js         (deriveKey conflicts with pqc)
//   ./trustCone.js          (imports hyperbolic)
//   ./fluxState.js          (FluxState conflicts with languesMetric)
// ═══════════════════════════════════════════════════════════════
