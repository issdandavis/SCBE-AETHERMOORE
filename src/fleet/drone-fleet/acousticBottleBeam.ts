/**
 * @file acousticBottleBeam.ts
 * @module fleet/drone-fleet/acousticBottleBeam
 * @layer Layer 14
 * @component Vacuum-Acoustic Bottle Beams for Data Security
 *
 * When a drone is physically captured and an adversary attempts data
 * extraction, the Vacuum-Acoustics Kernel generates an Acoustic Bottle
 * Beam within the storage enclosure.
 *
 * Trigger: Hamiltonian CFI violation (unauthorized access pattern)
 * Response: Destructive interference (W₂ = -W₁) → Φ_total = 0
 *
 * Data bus is scrambled before read; energy redistributed to
 * "nodal corners" (harmless dissipation).
 *
 * A1: Unitarity — energy is conserved (redistributed, not destroyed)
 */

import type { Vector3D } from '../../harmonic/constants.js';

/** Data storage enclosure geometry */
export interface StorageEnclosure {
  /** Enclosure dimensions [width, height, depth] in mm */
  dimensions: Vector3D;
  /** Center position of data core within enclosure */
  dataCoreCenter: Vector3D;
  /** Data core radius in mm */
  dataCoreRadius: number;
}

/** Bottle beam configuration */
export interface BottleBeamConfig {
  /** Number of acoustic sources around enclosure */
  sourceCount: number;
  /** Base wavelength (mm) */
  wavelength: number;
  /** Scramble intensity [0, 1] */
  scrambleIntensity: number;
  /** Time-to-erase threshold (ms) — how long scramble buys */
  timeToEraseMs: number;
}

/** CFI violation trigger */
export interface CFIViolation {
  /** Type of violation */
  type: 'DEVIATION' | 'ATTACK' | 'OBSTRUCTION';
  /** Severity [0, 1] */
  severity: number;
  /** Violating state vector */
  stateVector: number[];
  /** Timestamp of detection */
  timestamp: number;
}

/** Bottle beam activation result */
export interface BottleBeamResult {
  /** Whether bottle beam was activated */
  activated: boolean;
  /** Destructive interference achieved at data core */
  coreInterference: number;
  /** Energy redistributed to corners */
  cornerEnergy: [number, number, number, number];
  /** Total energy canceled at core */
  canceledEnergy: number;
  /** Data bus readable? (false = scrambled) */
  dataBusReadable: boolean;
  /** Estimated time before data can be extracted (ms) */
  timeToExtractMs: number;
  /** Zone of silence radius (mm) */
  silenceRadius: number;
}

/** Data protection status */
export interface DataProtectionStatus {
  /** Current protection level */
  level: 'UNPROTECTED' | 'ARMED' | 'ACTIVE' | 'ERASING';
  /** Whether data is currently scrambled */
  isScrambled: boolean;
  /** Time remaining before self-destruct (ms), or Infinity */
  selfDestructCountdown: number;
  /** Number of active acoustic sources */
  activeSources: number;
}

export const DEFAULT_ENCLOSURE: StorageEnclosure = {
  dimensions: [50, 30, 20],
  dataCoreCenter: [25, 15, 10],
  dataCoreRadius: 5,
};

export const DEFAULT_BOTTLE_BEAM_CONFIG: BottleBeamConfig = {
  sourceCount: 8,
  wavelength: 2.0,
  scrambleIntensity: 0.95,
  timeToEraseMs: 5000,
};

/**
 * Generate acoustic source positions around the enclosure perimeter.
 *
 * Sources are placed at equal angular intervals on the enclosure
 * midplane, pointing inward toward the data core.
 *
 * @param enclosure - Storage enclosure geometry
 * @param sourceCount - Number of sources
 * @returns Array of source positions
 */
export function generateSourcePositions(
  enclosure: StorageEnclosure,
  sourceCount: number
): Vector3D[] {
  const sources: Vector3D[] = [];
  const [w, h, d] = enclosure.dimensions;
  const cx = w / 2;
  const cy = h / 2;
  const cz = d / 2;
  const radius = Math.max(w, h) / 2;

  for (let i = 0; i < sourceCount; i++) {
    const angle = (2 * Math.PI * i) / sourceCount;
    sources.push([cx + radius * Math.cos(angle), cy + radius * Math.sin(angle), cz]);
  }

  return sources;
}

/**
 * Compute destructive interference at the data core center.
 *
 * W₂ = -W₁ → Φ_total = Φ₁ + Φ₂ = 0
 *
 * Pairs of sources are phase-inverted to create destructive
 * interference at the core while constructive interference
 * occurs at the corners.
 *
 * @param sources - Source positions
 * @param coreCenter - Data core center
 * @param wavelength - Acoustic wavelength
 * @returns Interference value at core (0 = perfect cancellation)
 */
export function computeCoreInterference(
  sources: Vector3D[],
  coreCenter: Vector3D,
  wavelength: number
): number {
  const k = (2 * Math.PI) / wavelength;
  let reTotal = 0;
  let imTotal = 0;

  for (let i = 0; i < sources.length; i++) {
    const dx = coreCenter[0] - sources[i][0];
    const dy = coreCenter[1] - sources[i][1];
    const dz = coreCenter[2] - sources[i][2];
    const r = Math.sqrt(dx * dx + dy * dy + dz * dz) + 1e-12;
    const theta = k * r;

    // Alternate phase: even sources at 0, odd sources at π (destructive)
    const phase = i % 2 === 0 ? 0 : Math.PI;
    reTotal += Math.cos(theta + phase);
    imTotal += Math.sin(theta + phase);
  }

  return Math.sqrt(reTotal * reTotal + imTotal * imTotal);
}

/**
 * Compute energy redistribution to enclosure corners.
 *
 * Energy canceled at core is redistributed to 4 corners
 * (conservation of energy — A1: Unitarity).
 *
 * @param totalEnergy - Total acoustic energy
 * @param canceledFraction - Fraction canceled at core
 * @returns Energy at each corner
 */
export function computeCornerRedistribution(
  totalEnergy: number,
  canceledFraction: number
): [number, number, number, number] {
  const canceled = totalEnergy * canceledFraction;
  const perCorner = canceled / 4;
  return [perCorner, perCorner, perCorner, perCorner];
}

/**
 * Activate bottle beam defense in response to a CFI violation.
 *
 * @param violation - The detected CFI violation
 * @param enclosure - Storage enclosure geometry
 * @param config - Bottle beam configuration
 * @returns BottleBeamResult
 */
export function activateBottleBeam(
  violation: CFIViolation,
  enclosure: StorageEnclosure = DEFAULT_ENCLOSURE,
  config: BottleBeamConfig = DEFAULT_BOTTLE_BEAM_CONFIG
): BottleBeamResult {
  const sources = generateSourcePositions(enclosure, config.sourceCount);
  const coreInterference = computeCoreInterference(
    sources,
    enclosure.dataCoreCenter,
    config.wavelength
  );

  // Normalize interference: lower = better cancellation
  const maxPossibleField = config.sourceCount;
  const cancelRatio = 1 - coreInterference / maxPossibleField;
  const effectiveCancellation = cancelRatio * config.scrambleIntensity;

  const totalEnergy = config.sourceCount; // Normalized
  const cornerEnergy = computeCornerRedistribution(totalEnergy, effectiveCancellation);

  const dataBusReadable = effectiveCancellation < 0.5;
  const timeToExtractMs = dataBusReadable ? 0 : Infinity;
  const silenceRadius = enclosure.dataCoreRadius * (1 + effectiveCancellation);

  return {
    activated: true,
    coreInterference,
    cornerEnergy,
    canceledEnergy: totalEnergy * effectiveCancellation,
    dataBusReadable,
    timeToExtractMs,
    silenceRadius,
  };
}

/**
 * Check if a CFI violation should trigger bottle beam activation.
 *
 * Only ATTACK and high-severity DEVIATION trigger activation.
 *
 * @param violation - CFI violation to evaluate
 * @returns Whether to activate bottle beam
 */
export function shouldActivate(violation: CFIViolation): boolean {
  if (violation.type === 'ATTACK') return true;
  if (violation.type === 'DEVIATION' && violation.severity > 0.7) return true;
  return false;
}

/**
 * Get current data protection status.
 *
 * @param isArmed - Whether bottle beam is armed
 * @param activeResult - Active bottle beam result (if any)
 * @param config - Bottle beam config
 * @returns DataProtectionStatus
 */
export function getProtectionStatus(
  isArmed: boolean,
  activeResult: BottleBeamResult | null,
  config: BottleBeamConfig = DEFAULT_BOTTLE_BEAM_CONFIG
): DataProtectionStatus {
  if (activeResult?.activated) {
    return {
      level: activeResult.dataBusReadable ? 'ARMED' : 'ACTIVE',
      isScrambled: !activeResult.dataBusReadable,
      selfDestructCountdown: config.timeToEraseMs,
      activeSources: config.sourceCount,
    };
  }

  return {
    level: isArmed ? 'ARMED' : 'UNPROTECTED',
    isScrambled: false,
    selfDestructCountdown: Infinity,
    activeSources: 0,
  };
}
