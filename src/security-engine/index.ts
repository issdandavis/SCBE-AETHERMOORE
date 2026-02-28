/**
 * @file index.ts
 * @module security-engine
 * @layer L1-L14
 * @component AI Security Engine — Unified Module Exports
 *
 * SCBE-AETHERMOORE AI Security Engine
 *
 * A machine-science control framework that uses physics-like invariants
 * as cross-platform coordination constants. This is NOT a physics simulation —
 * it defines a shared hyperspace where time, intention, and policy form
 * explicit dimensions. Tokens, agents, and flows are embedded into this space
 * and governed by configurable "fields" derived from machine constants.
 *
 * Modules:
 *   - machine-constants: Registry of configurable physics-like invariants
 *   - hyperspace:        9D state space with weighted Riemannian metric
 *   - policy-fields:     Overlapping policy regimes as constraint fields
 *   - context-engine:    Unified security gate (Grand Unified Governance)
 *   - digital-twin:      Deterministic control oracle at 144.72 Hz
 */

// Machine Constants
export {
  // Q16.16 fixed-point
  toQ16,
  fromQ16,
  mulQ16,
  divQ16,
  // Types
  type GeometricConstants,
  type HarmonicConstants,
  type TemporalConstants,
  type TrustConstants,
  type PolicyConstants,
  type EntropyConstants,
  type MachineConstants,
  // Defaults
  DEFAULT_GEOMETRIC,
  DEFAULT_HARMONIC,
  DEFAULT_TEMPORAL,
  DEFAULT_TRUST,
  DEFAULT_POLICY,
  DEFAULT_ENTROPY,
  DEFAULT_MACHINE_CONSTANTS,
  // Registry
  MachineConstantsRegistry,
  getGlobalRegistry,
  resetGlobalRegistry,
} from './machine-constants.js';

// Hyperspace
export {
  // Dimension enum
  HyperDim,
  HYPER_DIMS,
  DIMENSION_NAMES,
  // Types
  type HyperspaceCoord,
  type HyperspacePoint,
  type DimensionWeights,
  type EmbeddingInputs,
  // Defaults
  DEFAULT_DIMENSION_WEIGHTS,
  // Functions
  hyperspaceDistance,
  hyperspaceDistanceQ16,
  safeOrigin,
  distanceFromSafe,
  embedInHyperspace,
  // Manifold
  HyperspaceManifold,
} from './hyperspace.js';

// Policy Fields
export {
  // Types
  type PolicyField,
  PolicyCategory,
  type PolicyEvaluation,
  // Built-in fields
  SafetyField,
  ComplianceField,
  ResourceField,
  TrustField,
  RoleField,
  TemporalField,
  // Evaluator
  PolicyFieldEvaluator,
} from './policy-fields.js';

// Context-Coupled Security Engine
export {
  // Types
  SecurityDecision,
  type SecurityEvaluation,
  type ActionRequest,
  // Engine
  ContextCoupledSecurityEngine,
} from './context-engine.js';

// Digital Twin Governor
export {
  // Types
  type ManifoldStats,
  type ControlOutputs,
  // Governor
  DigitalTwinGovernor,
} from './digital-twin.js';
