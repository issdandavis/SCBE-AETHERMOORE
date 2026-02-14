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
export { EPSILON as HYPERBOLIC_EPSILON, applyHyperbolicPipeline, artanh, breathTransform, clampToBall, expMap0, exponentialMap, getAuditEpsilon, hyperbolicDistance, inverseBreathTransform, logMap0, logarithmicMap, mobiusAdd, mobiusAddition, multiPhaseModulation, multiWellGradient, multiWellPotential, phaseDeviation as hyperbolicPhaseDeviation, phaseDistanceScore as hyperbolicPhaseDistanceScore, phaseModulation, projectEmbeddingToBall, projectToBall, scoreRetrievals, setAuditEpsilon, type BreathConfig, type Well, } from './hyperbolic.js';
export { AVALI, CASSISIVADAN, DRAUMRIC, KOR_AELIN, RUNETHIC, TONGUES as SACRED_TONGUES, SECTION_TONGUES, UMBROTH, getTongueForSection, type SS1Section, type TongueCode, type TongueSpec, } from './sacredTongues.js';
export { SacredTongueTokenizer, SpiralSealSS1, computeLWSScore, computeLWSWeights, decodeFromSpelltext, encodeToSpelltext, formatSS1Blob, parseSS1Blob, randomBytes, seal, unseal, type SS1Blob, } from './spiralSeal.js';
export { PQCProvider, defaultPQCProvider, invNtt, mldsaKeyGen, mldsaSign, mldsaVerify, mlkemDecapsulate, mlkemEncapsulate, mlkemKeyGen, ntt, secureRandomBytes, shake128, shake256, type EncapsulationResult, type HybridEncryptionResult, type MLDSAKeyPair, type MLDSALevel, type MLKEMKeyPair, type MLKEMLevel, type PQCConfig, } from './pqc.js';
export { PHI, PHI_INV, QCLatticeProvider, SILVER_RATIO, ammannBeenkerRhombus, ammannBeenkerSquare, checkRotationalSymmetry, cutAndProject2D, defaultQCLattice, diffractionPattern, fibonacci1D, fibonacci2D, fibonacciSequence, fibonacciWord, nearestQCVertex, penroseDeflate, penroseInitial, penroseRhombus, penroseTiling, penroseToLattice, quasicrystal4to2, quasicrystal5to2, quasicrystalHash, quasicrystalPotential, scbeToQuasicrystal, type DiffractionPeak, type LatticePoint, type PenroseTile, type PenroseTileType, type Point2D, type QCLatticeConfig, } from './qcLattice.js';
export { CANONICAL_POLYHEDRA, CubicSpline6D, PHDMDeviationDetector, PHDMHamiltonianPath, PolyhedralHamiltonianDefenseManifold, computeCentroid, distance6D, eulerCharacteristic, isValidTopology, serializePolyhedron, topologicalHash, getActivePolyhedra, generateProjectionMatrix, phasonShift, type IntrusionResult, type Point6D, type FluxState as PHDMFluxState, type Polyhedron, type PolyhedronFamily, } from './phdm.js';
export { SPECTRAL_BANDS, SpectralIdentityGenerator, TONGUE_COLORS, spectralGenerator, type HSL, type RGB, type SpectralBand, type SpectralIdentity, } from './spectral-identity.js';
export { createEgg, hatch, predicateTongue, predicateGeo, predicatePath, predicateQuorum, predicateCrypto, deriveKey, getRingLevel, ALL_TONGUES, RING_BOUNDARIES, DEFAULT_TONGUE_WEIGHTS, type SacredEgg, type EggPolicy, type VerifierState, type Approval, type HatchResult, type RingLevel, } from './sacredEggs.js';
export { TriMechanismDetector, computeDriftSignature, driftAuthScore, driftDistanceToBaseline, hyperbolicDistance as triHyperbolicDistance, phaseDeviation, phaseDistanceScore, tonicCoherence, DEFAULT_CONFIG, TONGUE_INDEX, TONGUE_PHASES, type DetectionDecision, type PipelineMetrics, type PositionSample, type TriDetectionResult, type TriDetectorConfig, } from './triMechanismDetector.js';
export { HyperbolicRAGEngine, createHyperbolicRAG, accessCost, trustFromPosition, type HyperbolicRAGConfig, type RAGDocument, type RetrievalResult, type RetrievalSummary, } from './hyperbolicRAG.js';
export { EntropicMonitor, createEntropicMonitor, detectEscape, computeAdaptiveK, computeLocalEntropy, computeTrustDensity, computeExpansionRate, estimateReachableVolume, trackExpansion, defaultBasins, verifyEntropicInvariants, type AdaptiveKResult, type EntropicConfig, type EntropicSample, type EntropicState, type EscapeResult, type ExpansionResult, type TrustBasin, } from './entropic.js';
export { genesis, evaluateGenesis, computeHatchWeight as genesisHatchWeight, geoSealDistance, verifyCertificateSeal, GENESIS_THRESHOLD, DEFAULT_GEOSEAL_MAX_DISTANCE, DEFAULT_GENESIS_CONFIG, type GenesisConfig, type GenesisCertificate, type GenesisResult, type GenesisEvaluation, } from './sacredEggsGenesis.js';
export { DriftTracker, captureStepDrift, estimateFractalDimension, deriveHarmonicKey, assessAuthenticity, sonifyDrift, TONGUE_HARMONICS, DEFAULT_BUFFER_CAPACITY, SYNTHETIC_CV_THRESHOLD, GENUINE_FRACTAL_MIN, type DriftCapture, type ShadowBufferConfig, type FractalEstimate, type HarmonicKey, type DriftAuthenticity, type DriftSonification, type DriftTrackerStats, } from './driftTracker.js';
export { BooleanLattice, IntervalLattice, PowerSetLattice, UnitIntervalLattice, ProductLattice, identityConnection, constantConnection, thresholdConnection, scalingConnection, graphComplex, simplicialComplex, constantSheaf, thresholdSheaf, twistedSheaf, topCochain, bottomCochain, tarskiLaplacian, tarskiCohomology, globalSections, upLaplacian, downLaplacian, hodgeLaplacian, hodgeCohomology, analyseCohomology, detectObstructions, SheafCohomologyEngine, defaultSheafEngine, type CompleteLattice, type GaloisConnection, type Cell, type CellComplex, type CellularSheaf, type Cochain, type CohomologyResult, type CohomologyDiagnostics, type Obstruction, type SheafCohomologyConfig, type SheafAnalysisResult, } from './sheafCohomology.js';
export { PHDMGovernanceRouter, buildPolyhedralGraph, buildGovernanceSheaf, computePolyhedralTrust, polyhedralEulerCharacteristic, trustDistanceMatrix, requiredFluxState, defaultGovernanceRouter, type PolyhedralEdge, type GovernanceDecision, type GovernanceRoutingResult, type GovernanceRouterConfig, } from './phdmSheafLattice.js';
//# sourceMappingURL=index.d.ts.map