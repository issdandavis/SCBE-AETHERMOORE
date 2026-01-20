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
export { CONSTANTS, type Tensor2D, type Tensor3D, type Vector3D, type Vector6D, } from './constants.js';
export { assertFinite, assertIntGE, log2 } from './assertions.js';
export { harmonicDistance, harmonicScale, octaveTranspose, securityBits, securityLevel, } from './harmonicScaling.js';
export { halAttention, harmonicCouplingMatrix, type HALConfig } from './halAttention.js';
export { bottleBeamIntensity, cavityResonance, checkCymaticResonance, fluxRedistribution, nodalSurface, standingWaveAmplitude, type AcousticSource, type VacuumAcousticsConfig, } from './vacuumAcoustics.js';
export { FluxingLanguesMetric, LanguesMetric, TONGUES, getFluxState, type Decision, type DimensionFlux, type FluxState, type LanguesMetricConfig, type Tongue, } from './languesMetric.js';
export { AudioAxisProcessor, generateNoise, generateTestSignal, type AudioAxisConfig, type AudioFeatures, } from './audioAxis.js';
export { ControlFlowGraph, HamiltonianCFI, createVertex, type BipartiteResult, type CFGVertex, type CFIResult, type HamiltonianCheck, } from './hamiltonianCFI.js';
export { applyHyperbolicPipeline, breathTransform, expMap0, hyperbolicDistance, inverseBreathTransform, logMap0, mobiusAdd, multiPhaseModulation, multiWellGradient, multiWellPotential, phaseModulation, projectToBall, type BreathConfig, type Well, } from './hyperbolic.js';
export { AVALI, CASSISIVADAN, DRAUMRIC, KOR_AELIN, RUNETHIC, TONGUES as SACRED_TONGUES, SECTION_TONGUES, UMBROTH, getTongueForSection, type SS1Section, type TongueCode, type TongueSpec, } from './sacredTongues.js';
export { SacredTongueTokenizer, SpiralSealSS1, computeLWSScore, computeLWSWeights, decodeFromSpelltext, encodeToSpelltext, formatSS1Blob, parseSS1Blob, randomBytes, seal, unseal, type SS1Blob, } from './spiralSeal.js';
export { PQCProvider, defaultPQCProvider, invNtt, mldsaKeyGen, mldsaSign, mldsaVerify, mlkemDecapsulate, mlkemEncapsulate, mlkemKeyGen, ntt, secureRandomBytes, shake128, shake256, type EncapsulationResult, type HybridEncryptionResult, type MLDSAKeyPair, type MLDSALevel, type MLKEMKeyPair, type MLKEMLevel, type PQCConfig, } from './pqc.js';
export { PHI, PHI_INV, QCLatticeProvider, SILVER_RATIO, ammannBeenkerRhombus, ammannBeenkerSquare, checkRotationalSymmetry, cutAndProject2D, defaultQCLattice, diffractionPattern, fibonacci1D, fibonacci2D, fibonacciSequence, fibonacciWord, nearestQCVertex, penroseDeflate, penroseInitial, penroseRhombus, penroseTiling, penroseToLattice, quasicrystal4to2, quasicrystal5to2, quasicrystalHash, quasicrystalPotential, scbeToQuasicrystal, type DiffractionPeak, type LatticePoint, type PenroseTile, type PenroseTileType, type Point2D, type QCLatticeConfig, } from './qcLattice.js';
export { CANONICAL_POLYHEDRA, CubicSpline6D, PHDMDeviationDetector, PHDMHamiltonianPath, PolyhedralHamiltonianDefenseManifold, computeCentroid, distance6D, eulerCharacteristic, isValidTopology, serializePolyhedron, topologicalHash, type IntrusionResult, type Point6D, type Polyhedron, } from './phdm.js';
//# sourceMappingURL=index.d.ts.map