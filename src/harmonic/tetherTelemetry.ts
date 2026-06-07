/**
 * @file tetherTelemetry.ts
 * @module harmonic/tetherTelemetry
 *
 * Curvature proxy + governance decision from physical tether simulation frames.
 * Feature encoding lives in contextBundle.physicalTelemetryFeatures().
 */

import type { ContextBundle, PhysicalTelemetryContext } from './contextBundle.js';
import { bundleToFeatures } from './contextBundle.js';

/** One frame from scripts/sim_tether_rectifier.py */
export interface TetherTelemetryFrame {
  ts_ms?: number;
  sim_time_s?: number;
  step?: number;
  vibration_amplitude: number;
  tension_strain: number;
  magnetic_flux_drift: number;
  rectified_torque: number;
  /** Present when sim runs with --harmonic */
  harmonic_field_rms?: number;
  ferro_viscosity_proxy?: number;
  ferro_damping_factor?: number;
}

export type TetherGovernanceDecision = 'ALLOW' | 'QUARANTINE' | 'DENY';

export interface TetherCurvatureResult {
  curvature: number;
  decision: TetherGovernanceDecision;
  reasons: string[];
}

const VIB_QUARANTINE = 0.0035;
const VIB_DENY = 0.008;
const TORQUE_FLOOR = 0.02;
const FLUX_DRIFT_QUARANTINE = 0.15;

function clamp(v: number, lo = 0, hi = 1): number {
  return Math.max(lo, Math.min(hi, v));
}

export function tetherFrameToPhysical(frame: TetherTelemetryFrame): PhysicalTelemetryContext {
  return {
    vibrationAmplitude: Math.max(0, frame.vibration_amplitude),
    tensionStrain: Math.max(0, frame.tension_strain),
    magneticFluxDrift: frame.magnetic_flux_drift,
    rectifiedTorque: frame.rectified_torque,
  };
}

export function calculateTetherCurvature(
  frame: TetherTelemetryFrame,
  prev?: TetherTelemetryFrame
): TetherCurvatureResult {
  const reasons: string[] = [];
  let score = 0;

  const vib = frame.vibration_amplitude;
  if (vib >= VIB_DENY) {
    score = Math.max(score, 0.95);
    reasons.push('vibration_denial_threshold');
  } else if (vib >= VIB_QUARANTINE) {
    score = Math.max(
      score,
      0.55 + (0.35 * (vib - VIB_QUARANTINE)) / Math.max(VIB_DENY - VIB_QUARANTINE, 1e-9)
    );
    reasons.push('vibration_elevated');
  }

  if (frame.rectified_torque < TORQUE_FLOOR) {
    score = Math.max(score, 0.72);
    reasons.push('rectifier_torque_collapse');
  }

  if (Math.abs(frame.magnetic_flux_drift) > FLUX_DRIFT_QUARANTINE) {
    score = Math.max(score, 0.6);
    reasons.push('magnetic_flux_drift');
  }

  if (prev) {
    const dv = Math.abs(frame.vibration_amplitude - prev.vibration_amplitude);
    const dt = Math.max((frame.ts_ms ?? 0) - (prev.ts_ms ?? 0), 1);
    const jerk = (dv / dt) * 1000;
    if (jerk > 0.001) {
      score = Math.max(score, clamp(0.4 + jerk * 80));
      reasons.push('vibration_jerk');
    }
  }

  score = clamp(score);
  let decision: TetherGovernanceDecision = 'ALLOW';
  if (score >= 0.88) decision = 'DENY';
  else if (score >= 0.45) decision = 'QUARANTINE';

  return { curvature: score, decision, reasons };
}

export function bundleWithTetherTelemetry(
  base: ContextBundle,
  frame: TetherTelemetryFrame
): ContextBundle {
  return { ...base, physical: tetherFrameToPhysical(frame) };
}

export function evaluateTetherGovernance(
  frame: TetherTelemetryFrame,
  prev?: TetherTelemetryFrame
): TetherCurvatureResult & { featuresDim: number } {
  const result = calculateTetherCurvature(frame, prev);
  const bundle = bundleWithTetherTelemetry({ intentText: 'tether.telemetry.ingest' }, frame);
  return { ...result, featuresDim: bundleToFeatures(bundle).length };
}

/** Alias for blueprint naming. */
export const calculateTetherCurvatureProxy = calculateTetherCurvature;
