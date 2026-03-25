/**
 * @file coordinator.unit.test.ts
 * @module selfHealing/coordinator
 * @component HealingCoordinator, QuickFixBot, DeepHealing
 *
 * Unit tests for the self-healing system covering:
 * - QuickFixBot heuristic actions
 * - DeepHealing diagnostic plans
 * - HealingCoordinator orchestration
 */

import { describe, expect, it } from 'vitest';
import { HealingCoordinator } from '../../src/selfHealing/coordinator';
import { QuickFixBot } from '../../src/selfHealing/quickFixBot';
import { DeepHealing } from '../../src/selfHealing/deepHealing';

describe('QuickFixBot', () => {
  it('returns a result with heuristic actions', async () => {
    const bot = new QuickFixBot();
    const result = await bot.attemptFix({ type: 'timeout', message: 'request timed out' });

    expect(result).toHaveProperty('success');
    expect(result).toHaveProperty('actions');
    expect(result).toHaveProperty('branch');
    expect(Array.isArray(result.actions)).toBe(true);
    expect(result.actions.length).toBeGreaterThan(0);
    expect(result.branch).toMatch(/^hotfix\/quick-/);
  });

  it('includes standard recovery heuristics', async () => {
    const bot = new QuickFixBot();
    const result = await bot.attemptFix({ type: 'error' });

    expect(result.actions).toContain('increase_retry');
    expect(result.actions).toContain('adjust_timeout');
    expect(result.actions).toContain('enable_fallback');
  });
});

describe('DeepHealing', () => {
  it('returns a diagnostic plan with approaches', async () => {
    const deep = new DeepHealing();
    const result = await deep.diagnose({ type: 'data_corruption' });

    expect(result).toHaveProperty('plan');
    expect(result).toHaveProperty('branch');
    expect(Array.isArray(result.plan)).toBe(true);
    expect(result.plan.length).toBeGreaterThan(0);
    expect(result.branch).toMatch(/^fix\/deep-/);
  });

  it('suggests structural fixes', async () => {
    const deep = new DeepHealing();
    const result = await deep.diagnose({ type: 'integration_failure' });

    expect(result.plan).toContain('refactor_logic');
    expect(result.plan).toContain('rewrite_integration');
    expect(result.plan).toContain('add_idempotency');
  });

  it('generates unique branch names per invocation', async () => {
    const deep = new DeepHealing();
    const r1 = await deep.diagnose({ type: 'a' });
    const r2 = await deep.diagnose({ type: 'b' });
    expect(r1.branch).not.toBe(r2.branch);
  });
});

describe('HealingCoordinator', () => {
  it('coordinates quick and deep healing', async () => {
    const coordinator = new HealingCoordinator();
    const result = await coordinator.handleFailure({
      type: 'timeout',
      message: 'service unavailable',
    });

    expect(result).toHaveProperty('quick');
    expect(result).toHaveProperty('deep');
    expect(result).toHaveProperty('decision');
    expect(result.decision).toBe('prefer_deep_if_ready');
  });

  it('returns both quick and deep results', async () => {
    const coordinator = new HealingCoordinator();
    const result = await coordinator.handleFailure({ type: 'error' });

    // Quick fix result
    expect(result.quick).toHaveProperty('actions');
    expect(result.quick).toHaveProperty('branch');

    // Deep healing result
    expect(result.deep).toHaveProperty('plan');
    expect(result.deep).toHaveProperty('branch');
  });

  it('handles various failure types without throwing', async () => {
    const coordinator = new HealingCoordinator();

    const failures = [
      { type: 'timeout' },
      { type: 'crash', stack: 'Error: OOM' },
      { type: 'assertion', expected: 1, actual: 2 },
      null,
      undefined,
      'string error',
    ];

    for (const failure of failures) {
      const result = await coordinator.handleFailure(failure);
      expect(result).toHaveProperty('decision');
    }
  });
});
