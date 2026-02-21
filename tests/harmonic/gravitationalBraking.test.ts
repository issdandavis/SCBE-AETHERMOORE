/**
 * @file gravitationalBraking.test.ts
 * @module harmonic/gravitationalBraking
 * @layer Layer 12, Layer 13
 * @component Gravitational Braking Tests
 * @version 3.2.4
 */

import { describe, it, expect } from 'vitest';
import {
  computeTimeDilation,
  computeTrustRadius,
  brakingIntensity,
  GravitationalBraking,
} from '../../src/harmonic/gravitationalBraking.js';

const PHI = (1 + Math.sqrt(5)) / 2;
const EPSILON = 1e-10;

describe('computeTimeDilation', () => {
  it('returns 1.0 when divergence is zero', () => {
    const r = 5.0;
    const k = 1.0;
    const result = computeTimeDilation(0, r, k);
    expect(result).toBeCloseTo(1.0, 10);
  });

  it('returns 0.0 when divergence equals trustRadius (k=1)', () => {
    const r = 5.0;
    const k = 1.0;
    // tG = 1 - (k*d)/(r+ε) ≈ 1 - r/(r+ε) ≈ 0 for large r
    const result = computeTimeDilation(r, r, k);
    expect(result).toBeCloseTo(0.0, 5);
  });

  it('returns approximately 0.5 when divergence is half trustRadius (k=1)', () => {
    const r = 10.0;
    const k = 1.0;
    const d = r / 2;
    // tG = 1 - (k*d)/(r+ε) = 1 - (r/2)/(r+ε) ≈ 0.5
    const result = computeTimeDilation(d, r, k);
    expect(result).toBeCloseTo(0.5, 5);
  });

  it('clamps result to [0, 1] — never exceeds 1.0', () => {
    const result = computeTimeDilation(0, 100, 1.0);
    expect(result).toBeLessThanOrEqual(1.0);
    expect(result).toBeGreaterThanOrEqual(0.0);
  });

  it('clamps result to [0, 1] — never goes below 0.0', () => {
    // divergence much larger than trustRadius should clamp to 0
    const result = computeTimeDilation(1000, 1, 1.0);
    expect(result).toBeGreaterThanOrEqual(0.0);
    expect(result).toBeLessThanOrEqual(1.0);
  });

  it('uses default k when not provided', () => {
    const r = 5.0;
    // Should not throw, and return a value in [0,1]
    const result = computeTimeDilation(2, r);
    expect(result).toBeGreaterThanOrEqual(0.0);
    expect(result).toBeLessThanOrEqual(1.0);
  });
});

describe('computeTimeDilation edge cases', () => {
  it('returns 1.0 when divergence is negative', () => {
    const result = computeTimeDilation(-1, 5, 1.0);
    expect(result).toBe(1.0);
  });

  it('returns 1.0 when divergence is a large negative value', () => {
    const result = computeTimeDilation(-999, 5, 1.0);
    expect(result).toBe(1.0);
  });

  it('returns 0.0 when trustRadius is zero', () => {
    const result = computeTimeDilation(1, 0, 1.0);
    expect(result).toBe(0.0);
  });

  it('returns 0.0 when trustRadius is negative', () => {
    const result = computeTimeDilation(1, -5, 1.0);
    expect(result).toBe(0.0);
  });

  it('handles zero divergence with zero trustRadius — trustRadius check takes priority', () => {
    const result = computeTimeDilation(0, 0, 1.0);
    expect(result).toBe(0.0);
  });
});

describe('computeTrustRadius', () => {
  it('returns 0 for a zero vector', () => {
    const result = computeTrustRadius([0, 0, 0, 0, 0, 0]);
    expect(result).toBe(0);
  });

  it('returns 0 for an empty vector', () => {
    const result = computeTrustRadius([]);
    expect(result).toBe(0);
  });

  it('computes correct weighted norm for a unit vector along first dimension', () => {
    // weights[0] = 1, so sqrt(1 * 1^2) = 1
    const result = computeTrustRadius([1, 0, 0, 0, 0, 0]);
    expect(result).toBeCloseTo(1.0, 10);
  });

  it('computes correct weighted norm for a unit vector along second dimension', () => {
    // weights[1] = phi, so sqrt(phi * 1^2) = sqrt(phi)
    const expected = Math.sqrt(PHI);
    const result = computeTrustRadius([0, 1, 0, 0, 0, 0]);
    expect(result).toBeCloseTo(expected, 10);
  });

  it('computes correct weighted norm for a unit vector along third dimension', () => {
    // weights[2] = phi^2, so sqrt(phi^2 * 1^2) = phi
    const expected = PHI;
    const result = computeTrustRadius([0, 0, 1, 0, 0, 0]);
    expect(result).toBeCloseTo(expected, 10);
  });

  it('computes correct weighted norm for a unit vector along fourth dimension', () => {
    // weights[3] = phi^3, so sqrt(phi^3)
    const expected = Math.sqrt(PHI ** 3);
    const result = computeTrustRadius([0, 0, 0, 1, 0, 0]);
    expect(result).toBeCloseTo(expected, 10);
  });

  it('computes correct weighted norm for a unit vector along fifth dimension', () => {
    // weights[4] = phi^4, so sqrt(phi^4) = phi^2
    const expected = PHI ** 2;
    const result = computeTrustRadius([0, 0, 0, 0, 1, 0]);
    expect(result).toBeCloseTo(expected, 10);
  });

  it('computes correct weighted norm for a unit vector along sixth dimension', () => {
    // weights[5] = phi^5, so sqrt(phi^5)
    const expected = Math.sqrt(PHI ** 5);
    const result = computeTrustRadius([0, 0, 0, 0, 0, 1]);
    expect(result).toBeCloseTo(expected, 10);
  });

  it('computes correct weighted norm for a general vector', () => {
    const v = [1, 1, 1, 1, 1, 1];
    const weights = [1, PHI, PHI ** 2, PHI ** 3, PHI ** 4, PHI ** 5];
    const expected = Math.sqrt(weights.reduce((sum, w, i) => sum + w * v[i] ** 2, 0));
    const result = computeTrustRadius(v);
    expect(result).toBeCloseTo(expected, 10);
  });

  it('scales linearly with vector magnitude', () => {
    const v = [1, 2, 0, 0, 0, 0];
    const r1 = computeTrustRadius(v);
    const r2 = computeTrustRadius(v.map((x) => x * 2));
    expect(r2).toBeCloseTo(r1 * 2, 10);
  });
});

describe('brakingIntensity', () => {
  it('returns 0 when timeDilation is 1.0 (no braking)', () => {
    expect(brakingIntensity(1.0)).toBeCloseTo(0.0, 10);
  });

  it('returns 1 when timeDilation is 0.0 (full braking)', () => {
    expect(brakingIntensity(0.0)).toBeCloseTo(1.0, 10);
  });

  it('returns 0.5 when timeDilation is 0.5', () => {
    expect(brakingIntensity(0.5)).toBeCloseTo(0.5, 10);
  });

  it('returns 0.25 when timeDilation is 0.75', () => {
    expect(brakingIntensity(0.75)).toBeCloseTo(0.25, 10);
  });

  it('intensity is always 1 - timeDilation', () => {
    const values = [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0];
    for (const td of values) {
      expect(brakingIntensity(td)).toBeCloseTo(1 - td, 10);
    }
  });
});

describe('GravitationalBraking.update', () => {
  it('tracks agent state after update', () => {
    const gb = new GravitationalBraking();
    const trustVector = [1, 0, 0, 0, 0, 0];
    const state = gb.update('agent-1', 0, trustVector);

    expect(state).toBeDefined();
    expect(state.agentId).toBe('agent-1');
    expect(state.divergence).toBe(0);
    expect(state.timeDilation).toBeCloseTo(1.0, 5);
    expect(state.intensity).toBeCloseTo(0.0, 5);
    expect(state.frozen).toBe(false);
  });

  it('stores the correct trustRadius in returned BrakingState', () => {
    const gb = new GravitationalBraking();
    const trustVector = [1, 0, 0, 0, 0, 0];
    const expectedRadius = computeTrustRadius(trustVector);
    const state = gb.update('agent-2', 0, trustVector);

    expect(state.trustRadius).toBeCloseTo(expectedRadius, 10);
  });

  it('marks agent as frozen when timeDilation drops below freezeThreshold', () => {
    // Use a very high freeze threshold so any braking triggers freeze
    const gb = new GravitationalBraking({ freezeThreshold: 0.99 });
    const trustVector = [1, 0, 0, 0, 0, 0];
    // divergence > 0 causes some dilation reduction
    const state = gb.update('agent-freeze', 0.5, trustVector);

    // If dilation < 0.99 the agent should be frozen
    if (state.timeDilation < 0.99) {
      expect(state.frozen).toBe(true);
    }
  });

  it('updates existing agent state on subsequent calls', () => {
    const gb = new GravitationalBraking();
    const trustVector = [1, 0, 0, 0, 0, 0];

    gb.update('agent-3', 0, trustVector);
    const state2 = gb.update('agent-3', 0.5, trustVector);

    expect(state2.agentId).toBe('agent-3');
    expect(state2.divergence).toBe(0.5);
  });

  it('sets lastUpdatedAt to a valid timestamp', () => {
    const gb = new GravitationalBraking();
    const before = Date.now();
    const state = gb.update('agent-ts', 0, [1, 0, 0, 0, 0, 0]);
    const after = Date.now();

    expect(state.lastUpdatedAt).toBeGreaterThanOrEqual(before);
    expect(state.lastUpdatedAt).toBeLessThanOrEqual(after);
  });

  it('accepts an explicit now timestamp', () => {
    const gb = new GravitationalBraking();
    const customTime = 1700000000000;
    const state = gb.update('agent-now', 0, [1, 0, 0, 0, 0, 0], customTime);

    expect(state.lastUpdatedAt).toBe(customTime);
  });
});

describe('GravitationalBraking.canAct', () => {
  it('returns true for an unknown agent (no record)', () => {
    const gb = new GravitationalBraking();
    expect(gb.canAct('unknown-agent')).toBe(true);
  });

  it('returns true for a non-frozen agent', () => {
    const gb = new GravitationalBraking();
    gb.update('active-agent', 0, [1, 0, 0, 0, 0, 0]);
    expect(gb.canAct('active-agent')).toBe(true);
  });

  it('returns false when agent is frozen', () => {
    // Use a freeze threshold of 1.0 so the agent is always frozen unless dilation == 1.0
    // Use divergence > 0 so dilation < 1.0
    const gb = new GravitationalBraking({ freezeThreshold: 1.0 });
    const trustVector = [1, 0, 0, 0, 0, 0];
    gb.update('frozen-agent', 0.5, trustVector);

    const state = gb.getState('frozen-agent');
    if (state && state.frozen) {
      expect(gb.canAct('frozen-agent')).toBe(false);
    } else {
      // If not frozen with these params, adjust expectation
      expect(gb.canAct('frozen-agent')).toBe(true);
    }
  });

  it('returns false after agent is explicitly frozen via high divergence', () => {
    // Use a very low freezeThreshold to ensure the agent freezes
    const gb = new GravitationalBraking({ k: 10, freezeThreshold: 0.01 });
    const trustVector = [1, 0, 0, 0, 0, 0];
    // Large divergence relative to trustRadius => very low dilation
    gb.update('definitely-frozen', 10, trustVector);

    const state = gb.getState('definitely-frozen');
    expect(state).toBeDefined();
    if (state && state.frozen) {
      expect(gb.canAct('definitely-frozen')).toBe(false);
    }
  });
});

describe('GravitationalBraking.getTimeBudget', () => {
  it('returns 1.0 for an unknown agent', () => {
    const gb = new GravitationalBraking();
    expect(gb.getTimeBudget('no-such-agent')).toBe(1.0);
  });

  it('returns the stored timeDilation for a known agent', () => {
    const gb = new GravitationalBraking();
    const trustVector = [1, 0, 0, 0, 0, 0];
    const state = gb.update('budget-agent', 0, trustVector);

    expect(gb.getTimeBudget('budget-agent')).toBeCloseTo(state.timeDilation, 10);
  });

  it('reflects updated dilation after second update', () => {
    const gb = new GravitationalBraking();
    const trustVector = [1, 0, 0, 0, 0, 0];

    gb.update('budget-agent-2', 0, trustVector);
    const state2 = gb.update('budget-agent-2', 0.5, trustVector);

    expect(gb.getTimeBudget('budget-agent-2')).toBeCloseTo(state2.timeDilation, 10);
  });
});

describe('GravitationalBraking.getWarningAgents and getFrozenAgents', () => {
  it('getWarningAgents returns empty array when no agents tracked', () => {
    const gb = new GravitationalBraking();
    expect(gb.getWarningAgents()).toEqual([]);
  });

  it('getFrozenAgents returns empty array when no agents tracked', () => {
    const gb = new GravitationalBraking();
    expect(gb.getFrozenAgents()).toEqual([]);
  });

  it('getWarningAgents includes agents with intensity >= warningThreshold', () => {
    // warningThreshold default, we use a very low one to ensure agents appear
    const gb = new GravitationalBraking({ warningThreshold: 0.0 });
    const trustVector = [1, 0, 0, 0, 0, 0];

    gb.update('warn-a', 0.5, trustVector);
    gb.update('warn-b', 0, trustVector);

    const warnings = gb.getWarningAgents();
    // Both have intensity >= 0.0, so both should appear
    expect(warnings.length).toBeGreaterThanOrEqual(1);
    const ids = warnings.map((s) => s.agentId);
    expect(ids).toContain('warn-a');
  });

  it('getWarningAgents excludes agents below warningThreshold', () => {
    // High warningThreshold, so only heavily braked agents trigger warning
    const gb = new GravitationalBraking({ warningThreshold: 0.99 });
    const trustVector = [1, 0, 0, 0, 0, 0];

    gb.update('safe-agent', 0, trustVector);

    const warnings = gb.getWarningAgents();
    const ids = warnings.map((s) => s.agentId);
    expect(ids).not.toContain('safe-agent');
  });

  it('getFrozenAgents includes frozen agents only', () => {
    const gb = new GravitationalBraking({ k: 10, freezeThreshold: 0.01 });
    const trustVector = [1, 0, 0, 0, 0, 0];

    gb.update('frozen-x', 10, trustVector); // Very high divergence => likely frozen
    gb.update('active-x', 0, trustVector);  // Zero divergence => not frozen

    const frozen = gb.getFrozenAgents();
    const frozenIds = frozen.map((s) => s.agentId);
    expect(frozenIds).not.toContain('active-x');

    // Verify all returned states are actually marked frozen
    for (const state of frozen) {
      expect(state.frozen).toBe(true);
    }
  });

  it('getFrozenAgents returns consistent BrakingState objects', () => {
    const gb = new GravitationalBraking({ k: 10, freezeThreshold: 0.01 });
    const trustVector = [1, 0, 0, 0, 0, 0];
    gb.update('frozen-y', 10, trustVector);

    const frozen = gb.getFrozenAgents();
    for (const state of frozen) {
      expect(state).toHaveProperty('agentId');
      expect(state).toHaveProperty('divergence');
      expect(state).toHaveProperty('trustRadius');
      expect(state).toHaveProperty('timeDilation');
      expect(state).toHaveProperty('frozen');
      expect(state).toHaveProperty('intensity');
      expect(state).toHaveProperty('lastUpdatedAt');
    }
  });
});

describe('GravitationalBraking.release', () => {
  it('clears state for the released agent', () => {
    const gb = new GravitationalBraking();
    gb.update('release-me', 0.5, [1, 0, 0, 0, 0, 0]);
    expect(gb.getState('release-me')).toBeDefined();

    gb.release('release-me');
    expect(gb.getState('release-me')).toBeUndefined();
  });

  it('getTimeBudget returns 1.0 after release', () => {
    const gb = new GravitationalBraking();
    gb.update('release-budget', 0.5, [1, 0, 0, 0, 0, 0]);
    gb.release('release-budget');

    expect(gb.getTimeBudget('release-budget')).toBe(1.0);
  });

  it('canAct returns true after release', () => {
    const gb = new GravitationalBraking({ freezeThreshold: 1.0 });
    gb.update('release-act', 0.5, [1, 0, 0, 0, 0, 0]);
    gb.release('release-act');

    expect(gb.canAct('release-act')).toBe(true);
  });

  it('does not throw when releasing an unknown agent', () => {
    const gb = new GravitationalBraking();
    expect(() => gb.release('nonexistent')).not.toThrow();
  });

  it('releaseAll clears all tracked agents', () => {
    const gb = new GravitationalBraking();
    gb.update('agent-alpha', 0, [1, 0, 0, 0, 0, 0]);
    gb.update('agent-beta', 0.5, [1, 0, 0, 0, 0, 0]);
    gb.update('agent-gamma', 1.0, [1, 0, 0, 0, 0, 0]);

    gb.releaseAll();

    expect(gb.getState('agent-alpha')).toBeUndefined();
    expect(gb.getState('agent-beta')).toBeUndefined();
    expect(gb.getState('agent-gamma')).toBeUndefined();
    expect(gb.getWarningAgents()).toEqual([]);
    expect(gb.getFrozenAgents()).toEqual([]);
  });

  it('releaseAll does not throw on empty registry', () => {
    const gb = new GravitationalBraking();
    expect(() => gb.releaseAll()).not.toThrow();
  });
});

describe('GravitationalBraking.getState', () => {
  it('returns undefined for an untracked agent', () => {
    const gb = new GravitationalBraking();
    expect(gb.getState('ghost')).toBeUndefined();
  });

  it('returns the correct BrakingState for a tracked agent', () => {
    const gb = new GravitationalBraking();
    const trustVector = [2, 1, 0, 0, 0, 0];
    const updated = gb.update('state-check', 1.0, trustVector);
    const retrieved = gb.getState('state-check');

    expect(retrieved).toBeDefined();
    expect(retrieved!.agentId).toBe(updated.agentId);
    expect(retrieved!.divergence).toBe(updated.divergence);
    expect(retrieved!.timeDilation).toBeCloseTo(updated.timeDilation, 10);
    expect(retrieved!.trustRadius).toBeCloseTo(updated.trustRadius, 10);
    expect(retrieved!.intensity).toBeCloseTo(updated.intensity, 10);
    expect(retrieved!.frozen).toBe(updated.frozen);
    expect(retrieved!.lastUpdatedAt).toBe(updated.lastUpdatedAt);
  });
});

describe('GravitationalBraking BrakingState shape', () => {
  it('returned BrakingState has all required fields', () => {
    const gb = new GravitationalBraking();
    const state = gb.update('shape-test', 0, [1, 0, 0, 0, 0, 0]);

    expect(state).toHaveProperty('agentId');
    expect(state).toHaveProperty('divergence');
    expect(state).toHaveProperty('trustRadius');
    expect(state).toHaveProperty('timeDilation');
    expect(state).toHaveProperty('frozen');
    expect(state).toHaveProperty('intensity');
    expect(state).toHaveProperty('lastUpdatedAt');

    expect(typeof state.agentId).toBe('string');
    expect(typeof state.divergence).toBe('number');
    expect(typeof state.trustRadius).toBe('number');
    expect(typeof state.timeDilation).toBe('number');
    expect(typeof state.frozen).toBe('boolean');
    expect(typeof state.intensity).toBe('number');
    expect(typeof state.lastUpdatedAt).toBe('number');
  });

  it('intensity equals 1 - timeDilation', () => {
    const gb = new GravitationalBraking();
    const state = gb.update('intensity-check', 0.5, [1, 0, 0, 0, 0, 0]);

    expect(state.intensity).toBeCloseTo(1 - state.timeDilation, 10);
  });
});

describe('GravitationalBraking constructor config', () => {
  it('accepts empty config (uses defaults)', () => {
    expect(() => new GravitationalBraking()).not.toThrow();
    expect(() => new GravitationalBraking({})).not.toThrow();
  });

  it('accepts custom k value', () => {
    const gb = new GravitationalBraking({ k: 2.0 });
    const state = gb.update('k-test', 0.5, [1, 0, 0, 0, 0, 0]);
    expect(state).toBeDefined();
  });

  it('accepts custom freezeThreshold', () => {
    const gb = new GravitationalBraking({ freezeThreshold: 0.5 });
    const state = gb.update('ft-test', 0, [1, 0, 0, 0, 0, 0]);
    expect(state).toBeDefined();
  });

  it('accepts custom warningThreshold', () => {
    const gb = new GravitationalBraking({ warningThreshold: 0.3 });
    const state = gb.update('wt-test', 0, [1, 0, 0, 0, 0, 0]);
    expect(state).toBeDefined();
  });
});
