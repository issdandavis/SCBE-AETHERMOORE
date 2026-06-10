/**
 * @file index.ts
 * @module fleet/drone-fleet
 * @layer Layer 3-14
 * @component Drone Fleet Architecture Upgrades
 * @version 1.0.0
 *
 * Six simulation-oriented autonomous fleet modules that exercise
 * SCBE-AETHERMOORE geometric security primitives, Harmonic Wall-style
 * scoring, and Six Sacred Tongues protocol architecture.
 *
 * 1. Gravitational Braking — simulated control-rate reduction for off-path agents
 * 2. Sphere-in-Cube Topology — mission bounds via GeoSeal pattern
 * 3. Harmonic Camouflage — harmonic carrier selection simulation
 * 4. Sacred Tongues Flight Dynamics — tongue-to-maneuver mapping
 * 5. Acoustic Bottle Beams — capture-response interference simulation
 * 6. Dimensional Lifting — CFI-inspired graph lifting heuristics
 *
 * Patent: USPTO Provisional #63/961,403
 */

// ── 1. Gravitational Braking ────────────────────────────────────
export {
  computeDivergence,
  computeGravitationalBraking,
  criticalDivergence,
  DEFAULT_BRAKING_CONFIG,
  monitorAndBrake,
  type BrakingResult,
  type DroneFlightState,
  type FlightPathWaypoint,
  type GravitationalBrakingConfig,
} from './gravitationalBraking.js';

// ── 2. Sphere-in-Cube Topology ──────────────────────────────────
export {
  classifyManeuver,
  createManeuver,
  DEFAULT_SPHERE_CUBE_CONFIG,
  harmonicWallCost,
  isInsideBounds,
  penetrationDepth,
  sampleGeodesic,
  type ManeuverClassification,
  type ManeuverProjection,
  type MissionBounds,
  type PathType,
  type SphereCubeConfig,
} from './sphereCubeTopology.js';

// ── 3. Harmonic Camouflage ──────────────────────────────────────
export {
  createCamouflageState,
  DEFAULT_CAMOUFLAGE_CONFIG,
  deriveCamouflageFrequency,
  estimateDetectability,
  generateDecoys,
  generatePhase,
  modulateSignal,
  STELLAR_P_MODES,
  type CamouflageConfig,
  type CamouflagedSignal,
  type CamouflageState,
} from './harmonicCamouflage.js';

// ── 4. Sacred Tongues Flight Dynamics ───────────────────────────
export {
  bandwidthSavings,
  computeDynamics,
  decodeCommand,
  encodeCommand,
  parseCommandString,
  resolveInstruction,
  TONGUE_FLIGHT_MAP,
  type FlightBehavior,
  type FlightCommand,
  type FlightDynamicsState,
  type FlightInstruction,
  type TongueCode as FlightTongueCode,
  type TongueFlightMapping,
} from './sacredTonguesFlight.js';

// ── 5. Acoustic Bottle Beams ────────────────────────────────────
export {
  activateBottleBeam,
  computeCoreInterference,
  computeCornerRedistribution,
  DEFAULT_BOTTLE_BEAM_CONFIG,
  DEFAULT_ENCLOSURE,
  generateSourcePositions,
  getProtectionStatus,
  shouldActivate,
  type BottleBeamConfig,
  type BottleBeamResult,
  type CFIViolation,
  type DataProtectionStatus,
  type StorageEnclosure,
} from './acousticBottleBeam.js';

// ── 6. Dimensional Lifting ──────────────────────────────────────
export {
  DEFAULT_LIFTING_CONFIG,
  detectROP,
  liftGraph,
  validateLifting,
  type LiftDimension,
  type LiftingConfig,
  type LiftResult,
  type ROPDetectionResult,
} from './dimensionalLifting.js';
