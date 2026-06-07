import { describe, expect, it } from 'vitest';
import { bundleToFeatures, BUNDLE_TOTAL_DIM } from '../../src/harmonic/contextBundle.js';
import {
  bundleWithTetherTelemetry,
  calculateTetherCurvature,
  evaluateTetherGovernance,
} from '../../src/harmonic/tetherTelemetry.js';

describe('tetherTelemetry', () => {
  it('encodes physical lane in last eight imaginary features', () => {
    const base = bundleToFeatures({ intentText: 'ping' });
    expect(base.length).toBe(BUNDLE_TOTAL_DIM);
    expect(base.slice(-8).every((v) => v === 0)).toBe(true);

    const withPhys = bundleToFeatures(
      bundleWithTetherTelemetry(
        { intentText: 'ping' },
        {
          vibration_amplitude: 0.001,
          tension_strain: 0.05,
          magnetic_flux_drift: 0.01,
          rectified_torque: 0.08,
        }
      )
    );
    expect(withPhys.length).toBe(BUNDLE_TOTAL_DIM);
    expect(withPhys.slice(-8).some((v) => v > 0)).toBe(true);
  });

  it('flags QUARANTINE on elevated vibration', () => {
    const r = calculateTetherCurvature({
      vibration_amplitude: 0.005,
      tension_strain: 0.1,
      magnetic_flux_drift: 0.02,
      rectified_torque: 0.05,
    });
    expect(r.decision).toBe('QUARANTINE');
    expect(r.curvature).toBeGreaterThan(0.45);
  });

  it('flags DENY on whip-level vibration', () => {
    const r = calculateTetherCurvature({
      vibration_amplitude: 0.01,
      tension_strain: 0.2,
      magnetic_flux_drift: 0.2,
      rectified_torque: 0.01,
    });
    expect(r.decision).toBe('DENY');
  });

  it('evaluateTetherGovernance returns feature dim', () => {
    const r = evaluateTetherGovernance({
      vibration_amplitude: 0.0005,
      tension_strain: 0.02,
      magnetic_flux_drift: 0.001,
      rectified_torque: 0.12,
    });
    expect(r.decision).toBe('ALLOW');
    expect(r.featuresDim).toBe(BUNDLE_TOTAL_DIM);
  });
});
