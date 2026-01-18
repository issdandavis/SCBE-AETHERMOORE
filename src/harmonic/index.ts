/**
 * SCBE Harmonic Module
 *
 * Complete TypeScript implementation of the SCBE 14-layer hyperbolic
 * governance pipeline, including:
 *
 * - Layer 5: Invariant Hyperbolic Metric
 * - Layer 6: Breath Transform
 * - Layer 7: Phase Modulation
 * - Layer 8: Multi-Well Potential / SpiralSeal SS1 Envelope Encoding
 * - Layer 12: Harmonic Scaling H(d, R) = R^(d²)
 * - Layer 14: Audio Axis / Vacuum Acoustics
 *
 * Plus: Langues Metric, HAL Attention, Hamiltonian CFI, Sacred Tongue Tokenizer
 *
 * @module harmonic
 */

// ═══════════════════════════════════════════════════════════════
// Constants and Types
// ═══════════════════════════════════════════════════════════════

export {
  CONSTANTS,
  type Vector3D,
  type Vector6D,
  type Tensor2D,
  type Tensor3D,
} from './constants.js';

export { assertIntGE, assertFinite, log2 } from './assertions.js';

// ═══════════════════════════════════════════════════════════════
// Layer 12: Harmonic Scaling
// ═══════════════════════════════════════════════════════════════

export {
  harmonicScale,
  securityBits,
  securityLevel,
  harmonicDistance,
  octaveTranspose,
} from './harmonicScaling.js';

// ═══════════════════════════════════════════════════════════════
// HAL - Harmonic Attention Layer
// ═══════════════════════════════════════════════════════════════

export {
  type HALConfig,
  harmonicCouplingMatrix,
  halAttention,
} from './halAttention.js';

// ═══════════════════════════════════════════════════════════════
// Layer 14: Vacuum-Acoustics Kernel
// ═══════════════════════════════════════════════════════════════

export {
  type VacuumAcousticsConfig,
  type AcousticSource,
  nodalSurface,
  checkCymaticResonance,
  bottleBeamIntensity,
  fluxRedistribution,
  standingWaveAmplitude,
  cavityResonance,
} from './vacuumAcoustics.js';

// ═══════════════════════════════════════════════════════════════
// Langues Metric - 6D Governance Cost Function
// ═══════════════════════════════════════════════════════════════

export {
  TONGUES,
  type Tongue,
  type FluxState,
  type Decision,
  type DimensionFlux,
  type LanguesMetricConfig,
  getFluxState,
  LanguesMetric,
  FluxingLanguesMetric,
} from './languesMetric.js';

// ═══════════════════════════════════════════════════════════════
// Layer 14: Audio Axis (FFT Telemetry)
// ═══════════════════════════════════════════════════════════════

export {
  type AudioFeatures,
  type AudioAxisConfig,
  AudioAxisProcessor,
  generateTestSignal,
  generateNoise,
} from './audioAxis.js';

// ═══════════════════════════════════════════════════════════════
// Hamiltonian CFI - Control Flow Integrity
// ═══════════════════════════════════════════════════════════════

export {
  type CFIResult,
  type CFGVertex,
  type BipartiteResult,
  type HamiltonianCheck,
  ControlFlowGraph,
  HamiltonianCFI,
  createVertex,
} from './hamiltonianCFI.js';

// ═══════════════════════════════════════════════════════════════
// Layers 5-8: Hyperbolic Geometry (Poincaré Ball)
// ═══════════════════════════════════════════════════════════════

export {
  // Layer 5: Invariant Metric
  hyperbolicDistance,
  mobiusAdd,
  projectToBall,
  expMap0,
  logMap0,

  // Layer 6: Breath Transform
  type BreathConfig,
  breathTransform,
  inverseBreathTransform,

  // Layer 7: Phase Modulation
  phaseModulation,
  multiPhaseModulation,

  // Layer 8: Multi-Well Potential
  type Well,
  multiWellPotential,
  multiWellGradient,

  // Pipeline utility
  applyHyperbolicPipeline,
} from './hyperbolic.js';

// ═══════════════════════════════════════════════════════════════
// Sacred Tongues - Definitions
// ═══════════════════════════════════════════════════════════════

export {
  type TongueSpec,
  type TongueCode,
  type SS1Section,
  KOR_AELIN,
  AVALI,
  RUNETHIC,
  CASSISIVADAN,
  UMBROTH,
  DRAUMRIC,
  TONGUES as SACRED_TONGUES,
  SECTION_TONGUES,
  getTongueForSection,
} from './sacredTongues.js';

// ═══════════════════════════════════════════════════════════════
// SpiralSeal SS1 - Sacred Tongue Cryptographic Encoding
// ═══════════════════════════════════════════════════════════════

export {
  // Tokenizer
  SacredTongueTokenizer,
  encodeToSpelltext,
  decodeFromSpelltext,

  // SS1 Format
  type SS1Blob,
  formatSS1Blob,
  parseSS1Blob,

  // Crypto
  randomBytes,
  seal,
  unseal,
  SpiralSealSS1,

  // LWS Integration
  computeLWSWeights,
  computeLWSScore,
} from './spiralSeal.js';
