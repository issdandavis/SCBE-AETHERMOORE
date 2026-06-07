/**
 * @file simTelemetryAdapter.ts
 * @module harmonic/simTelemetryAdapter
 *
 * Adapters from reduced research-simulation metric JSON into the richer
 * TetherTelemetry shape consumed by mechanicalBundle.ts.
 *
 * These functions deliberately avoid file IO. Research scripts can read JSON
 * however they want, then pass parsed metrics here for deterministic governance.
 */

import type { TetherTelemetry, TetherMode } from './mechanicalBundle.js';

function clamp(v: number, lo = 0, hi = 1): number {
  return Math.max(lo, Math.min(hi, v));
}

function finite(v: unknown, fallback = 0): number {
  return typeof v === 'number' && Number.isFinite(v) ? v : fallback;
}

export interface JansenLayoutMetrics {
  peak_response: number;
  p95_response: number;
  spectral_flatness_power: number;
  q_proxy?: number;
  band_max?: Record<string, number>;
}

export interface JansenEngineeringSweepMetrics {
  n_brackets?: number;
  metrics: Record<string, JansenLayoutMetrics>;
  best_weighted_layout?: string;
}

export interface JansenTelemetryOptions {
  layout?: string;
  mode?: TetherMode;
  pressureBackflow?: number;
  tempGradient?: number;
  activeBrackets?: number;
}

export interface MemsControllerRunMetrics {
  profile?: { name?: string };
  allow_fraction: number;
  review_fraction: number;
  quarantine_fraction: number;
  window_fraction?: number;
  film_violation_fraction?: number;
  backflow_violation_fraction?: number;
  sensor_unavailable_fraction?: number;
  mean_abs_margin_error?: number;
}

export interface MemsControllerMetrics {
  runs: MemsControllerRunMetrics[];
}

export interface MemsTelemetryOptions {
  profileName?: string;
  mode?: TetherMode;
  bracketPhaseSpread?: number;
  totalBrackets?: number;
}

export interface JansenLoopClosureProfileMetrics {
  decision?: 'ALLOW' | 'QUARANTINE' | 'DENY' | string;
  convergence_rate: number;
  p95_residual_norm: number;
  max_residual_norm: number;
  p95_nfev: number;
  max_nfev: number;
  p95_angle_deviation_from_nominal: number;
  max_angle_deviation_from_nominal?: number;
}

export interface JansenLoopClosureMetrics {
  profiles: Record<string, JansenLoopClosureProfileMetrics>;
}

export interface LoopClosureTelemetryOptions {
  profileName?: string;
  mode?: TetherMode;
  totalBrackets?: number;
}

/**
 * Convert one Jansen bracket-layout frequency response into a telemetry frame.
 *
 * Mapping intent:
 * - spectral flatness becomes bracketPhaseSpread: flat spectrum = no coherent lock.
 * - p95 response above 0.5 becomes curvatureProxy: persistent broadband response.
 * - peak response above 0.75 becomes positive curvatureDelta: sharp emerging mode.
 * - per-band maxima become normalized bracket torque samples.
 */
export function jansenMetricsToTelemetry(
  sweep: JansenEngineeringSweepMetrics,
  options: JansenTelemetryOptions = {}
): TetherTelemetry {
  const layout = options.layout ?? sweep.best_weighted_layout ?? Object.keys(sweep.metrics)[0];
  const metric = sweep.metrics[layout];
  if (!metric) {
    throw new Error(`Unknown Jansen layout metric: ${layout}`);
  }

  const totalBrackets = Math.max(1, Math.trunc(finite(sweep.n_brackets, 10)));
  const activeBrackets = Math.max(
    0,
    Math.min(totalBrackets, Math.trunc(finite(options.activeBrackets, totalBrackets)))
  );

  const bandValues = Object.values(metric.band_max ?? {});
  const bracketTorques = (bandValues.length > 0 ? bandValues : [metric.peak_response])
    .slice(0, 8)
    .map((v) => clamp(finite(v)));

  const peak = clamp(finite(metric.peak_response));
  const p95 = clamp(finite(metric.p95_response));
  const phaseSpread = clamp(finite(metric.spectral_flatness_power));

  return {
    mode: options.mode ?? 'stable_orbit',
    strainReadings: [0.08, 0.1, 0.09, 0.07],
    strainTimestamps: [240, 180, 120, 60],
    bracketTorques,
    bracketPhaseSpread: phaseSpread,
    curvatureProxy: clamp((p95 - 0.5) / 0.5),
    curvatureDelta: clamp((peak - 0.75) / 0.25),
    plasmaCurrent: 0.08,
    dischargeActive: false,
    tempGradient: clamp(options.tempGradient ?? 0.12),
    manifoldPressure: 0.5,
    poreBackflow: clamp(options.pressureBackflow ?? 0),
    chirality: 'NEUTRAL',
    spineSeamTwisted: false,
    activeBrackets,
    totalBrackets,
    phiLatticeIntact: activeBrackets === totalBrackets && phaseSpread >= 0.2,
  };
}

/**
 * Convert a closed-loop MEMS pressure-controller run into mechanical telemetry.
 *
 * The controller profile becomes a hardware health frame:
 * - quarantine fraction is the primary curvatureProxy.
 * - review + quarantine is positive curvature growth.
 * - backflow violation becomes poreBackflow.
 * - window loss becomes phase-spread loss unless the caller provides spread.
 * - stuck/unavailable sensor profiles fail closed by driving delta/temp high.
 */
export function memsControllerRunToTelemetry(
  run: MemsControllerRunMetrics,
  options: MemsTelemetryOptions = {}
): TetherTelemetry {
  const totalBrackets = Math.max(1, Math.trunc(finite(options.totalBrackets, 8)));
  const quarantine = clamp(finite(run.quarantine_fraction));
  const review = clamp(finite(run.review_fraction));
  const window = clamp(finite(run.window_fraction, 1));
  const sensorUnavailable = clamp(finite(run.sensor_unavailable_fraction));
  const profileName = options.profileName ?? run.profile?.name ?? 'unknown';
  const stuckProfile = profileName.toLowerCase().includes('stuck');

  const bracketPhaseSpread = clamp(
    options.bracketPhaseSpread ?? window * (1 - quarantine) * (1 - sensorUnavailable)
  );

  const failClosed = stuckProfile || sensorUnavailable >= 0.5 || quarantine >= 0.95;

  return {
    mode: options.mode ?? (failClosed ? 'emergency_damping' : 'stable_orbit'),
    strainReadings: failClosed ? [0.9, 0.86, 0.82, 0.78] : [0.1, 0.12, 0.1, 0.09],
    strainTimestamps: [240, 180, 120, 60],
    bracketTorques: failClosed ? [0.08, 0.04, 0.02] : [0.42, 0.36, 0.31],
    bracketPhaseSpread,
    curvatureProxy: quarantine,
    curvatureDelta: failClosed ? 1 : clamp(review + quarantine),
    plasmaCurrent: failClosed ? 0.6 : 0.12,
    dischargeActive: failClosed,
    tempGradient: failClosed ? 1 : clamp(finite(run.mean_abs_margin_error) * 4),
    manifoldPressure: clamp(1 - window),
    poreBackflow: clamp(finite(run.backflow_violation_fraction)),
    chirality: 'NEUTRAL',
    spineSeamTwisted: false,
    activeBrackets: failClosed ? 0 : totalBrackets,
    totalBrackets,
    phiLatticeIntact: !failClosed && bracketPhaseSpread >= 0.2,
  };
}

export function memsControllerMetricsToTelemetry(
  metrics: MemsControllerMetrics,
  options: MemsTelemetryOptions = {}
): TetherTelemetry[] {
  return metrics.runs.map((run) => memsControllerRunToTelemetry(run, options));
}

/**
 * Convert fsolve loop-closure health into mechanical telemetry.
 *
 * Residual alone is not enough: mild strain can still close the triangle.
 * The angle-deviation-from-nominal metric is the mechanical anomaly signal.
 */
export function jansenLoopClosureToTelemetry(
  metrics: JansenLoopClosureMetrics,
  options: LoopClosureTelemetryOptions = {}
): TetherTelemetry {
  const profileName = options.profileName ?? Object.keys(metrics.profiles)[0];
  const profile = metrics.profiles[profileName];
  if (!profile) {
    throw new Error(`Unknown Jansen loop-closure profile: ${profileName}`);
  }

  const totalBrackets = Math.max(1, Math.trunc(finite(options.totalBrackets, 8)));
  const convergenceLoss = clamp(1 - finite(profile.convergence_rate, 1));
  const angleDeviation = clamp(finite(profile.p95_angle_deviation_from_nominal) / 0.14);
  const residualRisk = clamp(Math.log10(finite(profile.p95_residual_norm, 1e-14) / 1e-14) / 8);
  const effortRisk = clamp((finite(profile.max_nfev, 0) - 12) / 33);
  const decision = profile.decision ?? 'ALLOW';
  const failClosed = decision === 'DENY' || convergenceLoss >= 0.5;
  const quarantineLike = decision === 'QUARANTINE' || angleDeviation >= 0.35 || effortRisk >= 0.35;

  return {
    mode: options.mode ?? (failClosed ? 'emergency_damping' : 'stable_orbit'),
    strainReadings: failClosed
      ? [0.92, 0.88, 0.82, 0.77]
      : quarantineLike
        ? [0.32, 0.29, 0.24, 0.2]
        : [0.1, 0.11, 0.1, 0.09],
    strainTimestamps: [240, 180, 120, 60],
    bracketTorques: failClosed ? [0.1, 0.04, 0.02] : [0.42, 0.35, 0.28],
    bracketPhaseSpread: clamp(1 - angleDeviation),
    curvatureProxy: clamp(Math.max(angleDeviation, residualRisk, convergenceLoss)),
    curvatureDelta: clamp(Math.max(effortRisk, angleDeviation - 0.25)),
    plasmaCurrent: failClosed ? 0.62 : quarantineLike ? 0.25 : 0.08,
    dischargeActive: failClosed,
    tempGradient: failClosed ? 1 : quarantineLike ? 0.38 : 0.12,
    manifoldPressure: 0.5,
    poreBackflow: failClosed ? 0.55 : 0.03,
    chirality: 'NEUTRAL',
    spineSeamTwisted: failClosed || quarantineLike,
    activeBrackets: failClosed ? 0 : totalBrackets,
    totalBrackets,
    phiLatticeIntact: !failClosed && !quarantineLike,
  };
}
