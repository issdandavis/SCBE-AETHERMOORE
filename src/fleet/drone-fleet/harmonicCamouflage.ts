/**
 * @file harmonicCamouflage.ts
 * @module fleet/drone-fleet/harmonicCamouflage
 * @layer Layer 9, Layer 14
 * @component Harmonic Camouflage via Stellar Pulse Protocol
 *
 * Modulates fleet control signals at frequencies derived from celestial
 * body natural oscillation modes (p-modes) via 2ⁿ multiplication, making
 * coordination signals indistinguishable from background stellar/environmental
 * entropy.
 *
 * camouflage_freq = base_freq * 2^n
 *
 * Each signal is phase-randomized so the aggregate looks like noise.
 *
 * A4: Symmetry — gauge invariance preserved through frequency domain operations
 */

/** Known stellar p-mode reference frequencies (Hz) */
export const STELLAR_P_MODES: Record<string, number> = {
  SOL: 3.05e-3, // Sun ~5 min oscillation (3.05 mHz)
  ALPHA_CEN_A: 2.2e-3, // Alpha Centauri A
  PROCYON: 1.0e-3, // Procyon (F5 IV)
  BETA_HYI: 1.0e-3, // Beta Hydri
  ETA_BOO: 0.7e-3, // Eta Bootis
};

/** Configuration for harmonic camouflage */
export interface CamouflageConfig {
  /** Base stellar p-mode frequency in Hz */
  baseFrequency: number;
  /** Harmonic multiplier n (camouflage_freq = base * 2^n) */
  harmonicMultiplier: number;
  /** Whether to randomize phase per signal */
  randomizePhase: boolean;
  /** Signal-to-noise ratio target (dB) — lower = stealthier */
  targetSNR: number;
  /** Number of decoy carriers to generate */
  decoyCount: number;
}

/** A control signal with camouflage modulation applied */
export interface CamouflagedSignal {
  /** Original signal payload (arbitrary data) */
  payload: number[];
  /** Carrier frequency after camouflage (Hz) */
  carrierFrequency: number;
  /** Phase offset (radians) */
  phase: number;
  /** Amplitude (normalized 0-1) */
  amplitude: number;
  /** Whether this is a decoy (carries no real payload) */
  isDecoy: boolean;
  /** Timestamp */
  timestamp: number;
}

/** Fleet camouflage state */
export interface CamouflageState {
  /** Active carrier frequency */
  carrierFrequency: number;
  /** Number of active signals */
  activeSignals: number;
  /** Number of decoy signals */
  decoySignals: number;
  /** Estimated detectability [0, 1] — 0 = undetectable */
  detectability: number;
  /** Stellar body used for base frequency */
  stellarSource: string;
}

export const DEFAULT_CAMOUFLAGE_CONFIG: CamouflageConfig = {
  baseFrequency: STELLAR_P_MODES.SOL,
  harmonicMultiplier: 10,
  randomizePhase: true,
  targetSNR: -20,
  decoyCount: 4,
};

/**
 * Derive camouflage frequency from a stellar p-mode.
 *
 * camouflage_freq = base_freq * 2^n
 *
 * @param baseFreq - Stellar p-mode frequency (Hz)
 * @param n - Harmonic multiplier
 * @returns Camouflage carrier frequency (Hz)
 */
export function deriveCamouflageFrequency(baseFreq: number, n: number): number {
  return baseFreq * Math.pow(2, n);
}

/**
 * Generate a pseudo-random phase offset.
 * Uses a simple deterministic hash for reproducibility in tests.
 *
 * @param seed - Seed value
 * @returns Phase in [0, 2π)
 */
export function generatePhase(seed: number): number {
  const x = Math.sin(seed * 12.9898 + 78.233) * 43758.5453;
  return (x - Math.floor(x)) * 2 * Math.PI;
}

/**
 * Modulate a control signal for camouflage.
 *
 * @param payload - Signal data
 * @param config - Camouflage configuration
 * @param signalIndex - Index for phase generation
 * @returns Camouflaged signal
 */
export function modulateSignal(
  payload: number[],
  config: CamouflageConfig = DEFAULT_CAMOUFLAGE_CONFIG,
  signalIndex: number = 0
): CamouflagedSignal {
  const carrierFrequency = deriveCamouflageFrequency(
    config.baseFrequency,
    config.harmonicMultiplier
  );

  const phase = config.randomizePhase ? generatePhase(signalIndex + Date.now() * 0.001) : 0;

  // Amplitude derived from target SNR: lower SNR = lower amplitude
  const snrLinear = Math.pow(10, config.targetSNR / 20);
  const amplitude = Math.min(1, snrLinear);

  return {
    payload,
    carrierFrequency,
    phase,
    amplitude,
    isDecoy: false,
    timestamp: Date.now(),
  };
}

/**
 * Generate decoy signals that mimic real control signals but carry no payload.
 *
 * @param count - Number of decoys
 * @param config - Camouflage configuration
 * @returns Array of decoy signals
 */
export function generateDecoys(
  count: number,
  config: CamouflageConfig = DEFAULT_CAMOUFLAGE_CONFIG
): CamouflagedSignal[] {
  const decoys: CamouflagedSignal[] = [];
  const carrierFrequency = deriveCamouflageFrequency(
    config.baseFrequency,
    config.harmonicMultiplier
  );

  for (let i = 0; i < count; i++) {
    decoys.push({
      payload: [],
      carrierFrequency,
      phase: generatePhase(i * 7 + 31),
      amplitude: Math.random() * 0.1,
      isDecoy: true,
      timestamp: Date.now(),
    });
  }

  return decoys;
}

/**
 * Estimate detectability of camouflaged signals.
 *
 * Lower values = harder to detect. Uses ratio of signal power
 * to background stellar entropy power.
 *
 * @param signalAmplitude - Signal amplitude
 * @param decoyCount - Number of active decoys
 * @param backgroundPower - Estimated background noise power
 * @returns Detectability score [0, 1]
 */
export function estimateDetectability(
  signalAmplitude: number,
  decoyCount: number,
  backgroundPower: number = 1.0
): number {
  const signalPower = signalAmplitude * signalAmplitude;
  const decoyNoise = decoyCount * 0.01; // Each decoy adds noise
  const totalNoise = backgroundPower + decoyNoise;
  const snr = signalPower / totalNoise;
  // Map SNR to detectability: low SNR → low detectability
  return Math.min(1, snr);
}

/**
 * Create a full camouflage state for a fleet.
 *
 * @param realSignals - Number of real control signals
 * @param config - Camouflage configuration
 * @param stellarSource - Name of stellar body used
 * @returns CamouflageState
 */
export function createCamouflageState(
  realSignals: number,
  config: CamouflageConfig = DEFAULT_CAMOUFLAGE_CONFIG,
  stellarSource: string = 'SOL'
): CamouflageState {
  const carrierFrequency = deriveCamouflageFrequency(
    config.baseFrequency,
    config.harmonicMultiplier
  );
  const snrLinear = Math.pow(10, config.targetSNR / 20);
  const amplitude = Math.min(1, snrLinear);
  const detectability = estimateDetectability(amplitude, config.decoyCount);

  return {
    carrierFrequency,
    activeSignals: realSignals,
    decoySignals: config.decoyCount,
    detectability,
    stellarSource,
  };
}
