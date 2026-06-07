import { describe, expect, it } from 'vitest';
import { bundleToFeatures, BUNDLE_TOTAL_DIM } from '../../src/harmonic/contextBundle.js';
import {
  jansenMetricsToTelemetry,
  jansenLoopClosureToTelemetry,
  memsControllerRunToTelemetry,
} from '../../src/harmonic/simTelemetryAdapter.js';
import {
  mechanicalCurvatureScore,
  mechanicalCurvatureTier,
  tetherAuditLine,
  tetherTelemetryToBundle,
  type TetherTelemetry,
} from '../../src/harmonic/mechanicalBundle.js';

function baseTelemetry(overrides: Partial<TetherTelemetry> = {}): TetherTelemetry {
  return {
    mode: 'stable_orbit',
    strainReadings: [0.08, 0.1, 0.09],
    strainTimestamps: [180, 120, 60],
    bracketTorques: [0.35, 0.31, 0.28],
    bracketPhaseSpread: 0.9,
    curvatureProxy: 0.05,
    curvatureDelta: -0.1,
    plasmaCurrent: 0.05,
    dischargeActive: false,
    tempGradient: 0.05,
    manifoldPressure: 0.4,
    poreBackflow: 0,
    chirality: 'NEUTRAL',
    spineSeamTwisted: false,
    activeBrackets: 8,
    totalBrackets: 8,
    phiLatticeIntact: true,
    ...overrides,
  };
}

describe('mechanicalBundle', () => {
  it('keeps high phase spread and low strain in ALLOW', () => {
    const telemetry = baseTelemetry({ bracketPhaseSpread: 0.9 });
    const score = mechanicalCurvatureScore(telemetry);

    expect(score).toBeLessThan(0.2);
    expect(mechanicalCurvatureTier(score)).toBe('ALLOW');
    expect(tetherAuditLine(telemetry)).toContain('tier=ALLOW');
  });

  it('quarantines a low-spread high-curvature bracket jam', () => {
    const telemetry = baseTelemetry({
      bracketPhaseSpread: 0.1,
      curvatureProxy: 0.65,
      tempGradient: 0.4,
      phiLatticeIntact: false,
      activeBrackets: 7,
    });
    const score = mechanicalCurvatureScore(telemetry);
    const bundle = tetherTelemetryToBundle(telemetry);

    expect(score).toBeGreaterThanOrEqual(0.2);
    expect(mechanicalCurvatureTier(score)).toBe('QUARANTINE');
    expect(bundle.environment?.activeEnvGroups).toContain('resonance_risk');
    expect(bundleToFeatures(bundle).length).toBe(BUNDLE_TOTAL_DIM);
  });

  it('denies backflow plus low spread plus growing curvature', () => {
    const telemetry = baseTelemetry({
      mode: 'emergency_damping',
      bracketPhaseSpread: 0.05,
      curvatureProxy: 0.95,
      curvatureDelta: 0.9,
      poreBackflow: 0.9,
      tempGradient: 0.8,
      activeBrackets: 1,
      totalBrackets: 8,
    });
    const score = mechanicalCurvatureScore(telemetry);

    expect(score).toBeGreaterThanOrEqual(0.72);
    expect(mechanicalCurvatureTier(score)).toBe('DENY');
  });

  it('adapts Jansen sweep metrics into ALLOW and QUARANTINE telemetry', () => {
    const sweep = {
      n_brackets: 10,
      best_weighted_layout: 'jittered_uniform',
      metrics: {
        uniform: {
          peak_response: 1,
          p95_response: 0.842,
          spectral_flatness_power: 0.107,
          band_max: { mech_libration: 0.567, bracket_acoustic: 1, plasma_control: 1 },
        },
        jittered_uniform: {
          peak_response: 0.696,
          p95_response: 0.478,
          spectral_flatness_power: 0.593,
          band_max: { mech_libration: 0.556, bracket_acoustic: 0.696, plasma_control: 0.566 },
        },
      },
    };

    const healthy = jansenMetricsToTelemetry(sweep);
    const locked = jansenMetricsToTelemetry(sweep, { layout: 'uniform' });

    expect(healthy.bracketPhaseSpread).toBeCloseTo(0.593, 3);
    expect(mechanicalCurvatureTier(mechanicalCurvatureScore(healthy))).toBe('ALLOW');
    expect(locked.bracketPhaseSpread).toBeCloseTo(0.107, 3);
    expect(mechanicalCurvatureTier(mechanicalCurvatureScore(locked))).toBe('ESCALATE');
  });

  it('adapts stuck MEMS controller telemetry to fail closed', () => {
    const telemetry = memsControllerRunToTelemetry({
      profile: { name: 'one_failed_stuck' },
      allow_fraction: 0,
      review_fraction: 0,
      quarantine_fraction: 1,
      window_fraction: 0.466,
      film_violation_fraction: 0.276,
      backflow_violation_fraction: 0.114,
      sensor_unavailable_fraction: 0,
      mean_abs_margin_error: 0.048,
    });
    const score = mechanicalCurvatureScore(telemetry);

    expect(telemetry.mode).toBe('emergency_damping');
    expect(telemetry.phiLatticeIntact).toBe(false);
    expect(mechanicalCurvatureTier(score)).toBe('DENY');
  });

  it('adapts fsolve loop-closure metrics into stable and deformed telemetry', () => {
    const closureMetrics = {
      profiles: {
        nominal: {
          decision: 'ALLOW',
          convergence_rate: 1,
          p95_residual_norm: 1.78e-14,
          max_residual_norm: 3.01e-14,
          p95_nfev: 11,
          max_nfev: 11,
          p95_angle_deviation_from_nominal: 0,
          max_angle_deviation_from_nominal: 0,
        },
        tether_drift_5pct: {
          decision: 'QUARANTINE',
          convergence_rate: 1,
          p95_residual_norm: 1.78e-14,
          max_residual_norm: 2.56e-14,
          p95_nfev: 11,
          max_nfev: 12,
          p95_angle_deviation_from_nominal: 0.087,
          max_angle_deviation_from_nominal: 0.087,
        },
      },
    };

    const nominal = jansenLoopClosureToTelemetry(closureMetrics, { profileName: 'nominal' });
    const drifted = jansenLoopClosureToTelemetry(closureMetrics, {
      profileName: 'tether_drift_5pct',
    });

    expect(nominal.bracketPhaseSpread).toBe(1);
    expect(mechanicalCurvatureTier(mechanicalCurvatureScore(nominal))).toBe('ALLOW');
    expect(drifted.bracketPhaseSpread).toBeLessThan(0.4);
    expect(drifted.phiLatticeIntact).toBe(false);
    expect(mechanicalCurvatureTier(mechanicalCurvatureScore(drifted))).toBe('QUARANTINE');
  });
});
