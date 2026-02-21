/**
 * @file governed-drift.test.ts
 * @module tests/fleet/governed-drift
 * @layer L5, L12, L13
 * @component GovernedDrift — Bounded Stochastic Exploration Tests
 * @version 3.2.4
 *
 * Comprehensive tests for the GovernedDrift class covering auto-zero conditions,
 * budget computation, drift computation, emergency stop, analysis, and hard caps.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { GovernedDrift, DEFAULT_DRIFT_CONFIG } from '../../src/fleet/governed-drift.js';
import type { DriftInputs, DriftResult, DriftGovernanceConfig } from '../../src/fleet/governed-drift.js';
import { vecMag } from '../../src/fleet/swarm-geometry.js';
import type { Vec } from '../../src/fleet/swarm-geometry.js';
import type { SwarmMode } from '../../src/fleet/oscillator-bus.js';

// ──────────────── Test Helpers ────────────────

/**
 * Create DriftInputs with sensible defaults, overridable per test.
 */
function makeInputs(overrides: Partial<DriftInputs> = {}): DriftInputs {
  return {
    uncertainty: 0.5,
    energy: 0.8,
    risk: 0.2,
    trust: 0.7,
    currentMode: 'EXPLORE',
    ...overrides,
  };
}

// ──────────────── Tests ────────────────

describe('GovernedDrift', () => {
  let drift: GovernedDrift;

  beforeEach(() => {
    drift = new GovernedDrift();
  });

  // ════════════════════════════════════════════
  // Auto-Zero Conditions
  // ════════════════════════════════════════════

  describe('auto-zero conditions', () => {
    it('HAZARD mode -> drift zeroed with reason containing "mode_suppressed"', () => {
      const inputs = makeInputs({ currentMode: 'HAZARD' });
      const reason = drift.checkAutoZero(inputs);
      expect(reason).not.toBeNull();
      expect(reason).toContain('mode_suppressed');
    });

    it('REGROUP mode -> drift zeroed (default suppression mode)', () => {
      const inputs = makeInputs({ currentMode: 'REGROUP' });
      const reason = drift.checkAutoZero(inputs);
      expect(reason).not.toBeNull();
      expect(reason).toContain('mode_suppressed');
      expect(reason).toContain('REGROUP');
    });

    it('trust below threshold -> drift zeroed with reason containing "trust_below_threshold"', () => {
      const inputs = makeInputs({ trust: 0.05 }); // well below default threshold of 0.2
      const reason = drift.checkAutoZero(inputs);
      expect(reason).not.toBeNull();
      expect(reason).toContain('trust_below_threshold');
    });

    it('energy below floor -> drift zeroed with reason containing "energy_below_floor"', () => {
      const inputs = makeInputs({ energy: 0.01 }); // well below default floor of 0.1
      const reason = drift.checkAutoZero(inputs);
      expect(reason).not.toBeNull();
      expect(reason).toContain('energy_below_floor');
    });

    it('risk above ceiling -> drift zeroed with reason containing "risk_above_ceiling"', () => {
      const inputs = makeInputs({ risk: 0.95 }); // well above default ceiling of 0.8
      const reason = drift.checkAutoZero(inputs);
      expect(reason).not.toBeNull();
      expect(reason).toContain('risk_above_ceiling');
    });

    it('EXPLORE mode with good trust/energy/risk -> drift NOT zeroed (returns null)', () => {
      const inputs = makeInputs({
        currentMode: 'EXPLORE',
        trust: 0.7,
        energy: 0.8,
        risk: 0.2,
      });
      const reason = drift.checkAutoZero(inputs);
      expect(reason).toBeNull();
    });
  });

  // ════════════════════════════════════════════
  // Budget Computation
  // ════════════════════════════════════════════

  describe('budget computation', () => {
    it('zero uncertainty, energy, trust -> budget approximately 0', () => {
      const inputs = makeInputs({
        uncertainty: 0,
        energy: 0,
        trust: 0,
        risk: 0,
        currentMode: 'EXPLORE',
      });
      // checkAutoZero will fire for trust < threshold, so call computeBudget directly
      const { budget } = drift.computeBudget(inputs);
      expect(budget).toBeCloseTo(0, 10);
    });

    it('max uncertainty, energy, trust with zero risk -> budget near maximum', () => {
      const inputs = makeInputs({
        uncertainty: 1.0,
        energy: 1.0,
        trust: 1.0,
        risk: 0,
      });
      const { budget, factors } = drift.computeBudget(inputs);
      // With risk=0, riskSuppression = exp(0) = 1.0
      // Raw = (0.5*1 + 0.3*1 + 0.4*1) * 1.0 = 1.2
      // Capped to maxDriftMagnitude = 1.0
      expect(factors.riskSuppression).toBeCloseTo(1.0, 10);
      expect(budget).toBeCloseTo(1.0, 10); // capped at maxDriftMagnitude
    });

    it('high risk -> budget exponentially suppressed (riskSuppression < 1)', () => {
      const lowRiskInputs = makeInputs({ risk: 0.1 });
      const highRiskInputs = makeInputs({ risk: 0.9 });

      const lowRisk = drift.computeBudget(lowRiskInputs);
      const highRisk = drift.computeBudget(highRiskInputs);

      // riskSuppression = exp(-riskDecay * risk)
      // With riskDecay=2.0: exp(-2*0.1) = 0.818... vs exp(-2*0.9) = 0.165...
      expect(highRisk.factors.riskSuppression).toBeLessThan(1.0);
      expect(highRisk.factors.riskSuppression).toBeLessThan(lowRisk.factors.riskSuppression);
      expect(highRisk.budget).toBeLessThan(lowRisk.budget);
    });

    it('budget never exceeds maxDriftMagnitude (hard cap)', () => {
      // Use a very low maxDriftMagnitude to ensure capping
      const cappedDrift = new GovernedDrift({ maxDriftMagnitude: 0.1 });
      const inputs = makeInputs({
        uncertainty: 1.0,
        energy: 1.0,
        trust: 1.0,
        risk: 0,
      });
      const { budget } = cappedDrift.computeBudget(inputs);
      expect(budget).toBeLessThanOrEqual(0.1);
    });

    it('each factor contribution is individually correct', () => {
      const inputs = makeInputs({
        uncertainty: 0.6,
        energy: 0.4,
        trust: 0.8,
        risk: 0.3,
      });
      const { factors } = drift.computeBudget(inputs);
      const config = drift.getConfig();

      // Individual contributions: scale * clamped_value
      expect(factors.uncertaintyContribution).toBeCloseTo(config.uncertaintyScale * 0.6, 10);
      expect(factors.energyContribution).toBeCloseTo(config.energyScale * 0.4, 10);
      expect(factors.trustContribution).toBeCloseTo(config.trustScale * 0.8, 10);

      // Risk suppression: exp(-riskDecay * risk)
      expect(factors.riskSuppression).toBeCloseTo(Math.exp(-config.riskDecay * 0.3), 10);

      // Computed budget: sum of contributions * riskSuppression, capped to maxDriftMagnitude
      const expectedRaw =
        (factors.uncertaintyContribution + factors.energyContribution + factors.trustContribution) *
        factors.riskSuppression;
      const expectedBudget = Math.min(Math.max(expectedRaw, 0), config.maxDriftMagnitude);
      expect(factors.computedBudget).toBeCloseTo(expectedBudget, 10);
    });
  });

  // ════════════════════════════════════════════
  // Drift Computation
  // ════════════════════════════════════════════

  describe('drift computation', () => {
    it('with direction: drift vector along normalized direction with budget magnitude', () => {
      const inputs = makeInputs();
      const direction: Vec = { x: 3, y: 4, z: 0 }; // magnitude 5
      const result = drift.computeDrift('node-1', inputs, direction);

      // Should not be zeroed
      expect(result.wasZeroed).toBe(false);
      expect(result.zeroReason).toBeNull();

      // Direction should be normalized (3/5, 4/5, 0)
      const mag = vecMag(result.vector);
      expect(mag).toBeCloseTo(result.cappedMagnitude, 10);

      // Check direction is normalized correctly
      if (mag > 1e-12) {
        expect(result.vector.x / mag).toBeCloseTo(3 / 5, 10);
        expect(result.vector.y / mag).toBeCloseTo(4 / 5, 10);
        expect(result.vector.z / mag).toBeCloseTo(0, 10);
      }
    });

    it('without direction and no existing drift: returns zero', () => {
      const inputs = makeInputs();
      const result = drift.computeDrift('node-fresh', inputs);

      expect(vecMag(result.vector)).toBeCloseTo(0, 10);
      expect(result.rawMagnitude).toBe(0);
      expect(result.cappedMagnitude).toBe(0);
      expect(result.wasZeroed).toBe(false);
    });

    it('without direction and existing drift: decays by naturalDecay', () => {
      const inputs = makeInputs();
      const direction: Vec = { x: 1, y: 0, z: 0 };

      // First call: establish drift with a direction
      const first = drift.computeDrift('node-decay', inputs, direction);
      const firstMag = vecMag(first.vector);
      expect(firstMag).toBeGreaterThan(0);

      // Second call: no direction -> should decay
      const second = drift.computeDrift('node-decay', inputs);
      const secondMag = vecMag(second.vector);
      const config = drift.getConfig();

      // Decayed magnitude = max(0, existingMag - naturalDecay)
      const expectedDecayed = Math.max(0, firstMag - config.naturalDecay);
      expect(secondMag).toBeCloseTo(expectedDecayed, 10);
    });

    it('auto-zero: returns zero vector and wasZeroed=true', () => {
      const inputs = makeInputs({ currentMode: 'HAZARD' });
      const direction: Vec = { x: 1, y: 1, z: 1 };
      const result = drift.computeDrift('node-hazard', inputs, direction);

      expect(result.wasZeroed).toBe(true);
      expect(result.zeroReason).not.toBeNull();
      expect(vecMag(result.vector)).toBe(0);
      expect(result.rawMagnitude).toBe(0);
      expect(result.cappedMagnitude).toBe(0);
    });

    it('result has correct factor breakdown', () => {
      const inputs = makeInputs({
        uncertainty: 0.7,
        energy: 0.5,
        trust: 0.9,
        risk: 0.1,
      });
      const direction: Vec = { x: 0, y: 1, z: 0 };
      const result = drift.computeDrift('node-factors', inputs, direction);
      const config = drift.getConfig();

      expect(result.factors.uncertaintyContribution).toBeCloseTo(config.uncertaintyScale * 0.7, 10);
      expect(result.factors.energyContribution).toBeCloseTo(config.energyScale * 0.5, 10);
      expect(result.factors.trustContribution).toBeCloseTo(config.trustScale * 0.9, 10);
      expect(result.factors.riskSuppression).toBeCloseTo(Math.exp(-config.riskDecay * 0.1), 10);
    });

    it('multiple calls accumulate history', () => {
      const inputs = makeInputs();
      const direction: Vec = { x: 1, y: 0, z: 0 };

      drift.computeDrift('node-hist', inputs, direction);
      drift.computeDrift('node-hist', inputs, direction);
      drift.computeDrift('node-hist', inputs, direction);

      const history = drift.getHistory('node-hist');
      expect(history.length).toBe(3);
    });

    it('zeroDrift forces a node to zero', () => {
      const inputs = makeInputs();
      const direction: Vec = { x: 1, y: 0, z: 0 };

      // Establish drift
      drift.computeDrift('node-force-zero', inputs, direction);
      const before = drift.getDrift('node-force-zero');
      expect(vecMag(before)).toBeGreaterThan(0);

      // Force zero
      drift.zeroDrift('node-force-zero');
      const after = drift.getDrift('node-force-zero');
      expect(vecMag(after)).toBe(0);

      // History should record the zeroed event
      const history = drift.getHistory('node-force-zero');
      const lastEntry = history[history.length - 1];
      expect(lastEntry.zeroed).toBe(true);
      expect(lastEntry.magnitude).toBe(0);
    });
  });

  // ════════════════════════════════════════════
  // Emergency Stop
  // ════════════════════════════════════════════

  describe('emergency stop', () => {
    it('zeroAll zeroes all tracked nodes', () => {
      const inputs = makeInputs();
      const direction: Vec = { x: 1, y: 0, z: 0 };

      // Establish drift for multiple nodes
      drift.computeDrift('node-a', inputs, direction);
      drift.computeDrift('node-b', inputs, direction);
      drift.computeDrift('node-c', inputs, direction);

      // Verify they have drift
      expect(vecMag(drift.getDrift('node-a'))).toBeGreaterThan(0);
      expect(vecMag(drift.getDrift('node-b'))).toBeGreaterThan(0);
      expect(vecMag(drift.getDrift('node-c'))).toBeGreaterThan(0);

      // Emergency stop
      drift.zeroAll();

      // All should be zeroed
      expect(vecMag(drift.getDrift('node-a'))).toBe(0);
      expect(vecMag(drift.getDrift('node-b'))).toBe(0);
      expect(vecMag(drift.getDrift('node-c'))).toBe(0);
    });

    it('after zeroAll, getTotalDriftEnergy() === 0', () => {
      const inputs = makeInputs();
      const direction: Vec = { x: 1, y: 0, z: 0 };

      // Establish drift for multiple nodes
      drift.computeDrift('node-x', inputs, direction);
      drift.computeDrift('node-y', inputs, { x: 0, y: 1, z: 0 });
      drift.computeDrift('node-z', inputs, { x: 0, y: 0, z: 1 });

      // Before zero, energy should be positive
      expect(drift.getTotalDriftEnergy()).toBeGreaterThan(0);

      // Emergency stop
      drift.zeroAll();

      // After zero, energy must be exactly 0
      expect(drift.getTotalDriftEnergy()).toBe(0);
    });
  });

  // ════════════════════════════════════════════
  // Analysis
  // ════════════════════════════════════════════

  describe('analysis', () => {
    it('getTotalDriftEnergy sums squared magnitudes', () => {
      const inputs = makeInputs();

      // Establish drift for two nodes with known directions
      drift.computeDrift('node-e1', inputs, { x: 1, y: 0, z: 0 });
      drift.computeDrift('node-e2', inputs, { x: 0, y: 1, z: 0 });

      const d1 = drift.getDrift('node-e1');
      const d2 = drift.getDrift('node-e2');
      const m1 = vecMag(d1);
      const m2 = vecMag(d2);

      const expectedEnergy = m1 * m1 + m2 * m2;
      expect(drift.getTotalDriftEnergy()).toBeCloseTo(expectedEnergy, 10);
    });

    it('getAverageDriftMagnitude returns correct average', () => {
      const inputs = makeInputs();

      drift.computeDrift('node-avg1', inputs, { x: 1, y: 0, z: 0 });
      drift.computeDrift('node-avg2', inputs, { x: 0, y: 1, z: 0 });

      const d1 = drift.getDrift('node-avg1');
      const d2 = drift.getDrift('node-avg2');
      const m1 = vecMag(d1);
      const m2 = vecMag(d2);

      const expectedAvg = (m1 + m2) / 2;
      expect(drift.getAverageDriftMagnitude()).toBeCloseTo(expectedAvg, 10);
    });

    it('getHistory returns recorded entries', () => {
      const inputs = makeInputs();
      const direction: Vec = { x: 1, y: 0, z: 0 };

      drift.computeDrift('node-h', inputs, direction);
      drift.computeDrift('node-h', inputs, direction);

      // Third call with hazard mode to create a zeroed entry
      drift.computeDrift('node-h', makeInputs({ currentMode: 'HAZARD' }), direction);

      const history = drift.getHistory('node-h');
      expect(history.length).toBe(3);

      // First two should not be zeroed
      expect(history[0].zeroed).toBe(false);
      expect(history[1].zeroed).toBe(false);

      // Third should be zeroed
      expect(history[2].zeroed).toBe(true);
      expect(history[2].magnitude).toBe(0);

      // All entries should have timestamps
      for (const entry of history) {
        expect(entry.timestamp).toBeGreaterThan(0);
      }
    });

    it('getZeroRatio computes fraction of zeroed steps correctly', () => {
      const safeInputs = makeInputs();
      const hazardInputs = makeInputs({ currentMode: 'HAZARD' });
      const direction: Vec = { x: 1, y: 0, z: 0 };

      // 3 normal + 2 zeroed = 5 total, 2/5 = 0.4 zero ratio
      drift.computeDrift('node-ratio', safeInputs, direction);
      drift.computeDrift('node-ratio', safeInputs, direction);
      drift.computeDrift('node-ratio', safeInputs, direction);
      drift.computeDrift('node-ratio', hazardInputs, direction);
      drift.computeDrift('node-ratio', hazardInputs, direction);

      const ratio = drift.getZeroRatio('node-ratio');
      expect(ratio).toBeCloseTo(2 / 5, 10);
    });
  });

  // ════════════════════════════════════════════
  // Hard Caps
  // ════════════════════════════════════════════

  describe('hard caps', () => {
    it('drift magnitude never exceeds maxDriftMagnitude even with extreme inputs', () => {
      const smallCap = new GovernedDrift({ maxDriftMagnitude: 0.05 });
      const inputs = makeInputs({
        uncertainty: 1.0,
        energy: 1.0,
        trust: 1.0,
        risk: 0,
      });
      const direction: Vec = { x: 100, y: 200, z: 300 };
      const result = smallCap.computeDrift('node-extreme', inputs, direction);

      expect(vecMag(result.vector)).toBeLessThanOrEqual(0.05 + 1e-10);
      expect(result.cappedMagnitude).toBeLessThanOrEqual(0.05);
    });

    it('maxDriftMagnitude is enforced at construction (must be >= 0.01)', () => {
      // Attempt to create with zero or negative maxDriftMagnitude
      const zeroCap = new GovernedDrift({ maxDriftMagnitude: 0 });
      const config1 = zeroCap.getConfig();
      expect(config1.maxDriftMagnitude).toBeGreaterThanOrEqual(0.01);

      const negativeCap = new GovernedDrift({ maxDriftMagnitude: -5 });
      const config2 = negativeCap.getConfig();
      expect(config2.maxDriftMagnitude).toBeGreaterThanOrEqual(0.01);

      // A tiny positive value below 0.01 should be clamped to 0.01
      const tinyCap = new GovernedDrift({ maxDriftMagnitude: 0.001 });
      const config3 = tinyCap.getConfig();
      expect(config3.maxDriftMagnitude).toBeGreaterThanOrEqual(0.01);
    });

    it('custom config overrides defaults correctly', () => {
      const customConfig: Partial<DriftGovernanceConfig> = {
        maxDriftMagnitude: 2.0,
        trustThreshold: 0.5,
        energyFloor: 0.3,
        riskCeiling: 0.6,
        uncertaintyScale: 1.0,
        energyScale: 0.5,
        trustScale: 0.8,
        riskDecay: 3.0,
        naturalDecay: 0.1,
        suppressionModes: ['HAZARD'],
      };

      const customDrift = new GovernedDrift(customConfig);
      const config = customDrift.getConfig();

      expect(config.maxDriftMagnitude).toBe(2.0);
      expect(config.trustThreshold).toBe(0.5);
      expect(config.energyFloor).toBe(0.3);
      expect(config.riskCeiling).toBe(0.6);
      expect(config.uncertaintyScale).toBe(1.0);
      expect(config.energyScale).toBe(0.5);
      expect(config.trustScale).toBe(0.8);
      expect(config.riskDecay).toBe(3.0);
      expect(config.naturalDecay).toBe(0.1);
      expect(config.suppressionModes).toEqual(['HAZARD']);

      // REGROUP should no longer trigger suppression with custom config
      const regroupInputs = makeInputs({ currentMode: 'REGROUP' });
      const reason = customDrift.checkAutoZero(regroupInputs);
      expect(reason).toBeNull();

      // Trust at 0.4 should trigger suppression (threshold is 0.5)
      const lowTrustInputs = makeInputs({ trust: 0.4 });
      const trustReason = customDrift.checkAutoZero(lowTrustInputs);
      expect(trustReason).toContain('trust_below_threshold');
    });
  });
});
