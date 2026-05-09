import { describe, expect, it } from 'vitest';
import {
  createTriadicOperatorPlan,
  recommendCompanionPackages,
  TRIADIC_DIMENSIONS,
} from '../../src/operator/index.js';

describe('Triadic Operator Manifold', () => {
  it('builds a local-first plan by default', () => {
    const plan = createTriadicOperatorPlan({
      intent: 'organize local workspace',
      features: ['workspace'],
    });

    expect(plan.schema_version).toBe('scbe-triadic-operator-plan-v1');
    expect(plan.mode).toBe('local_first');
    expect(plan.actors.map((actor) => actor.kind)).toEqual(['human', 'machine', 'ai']);
    expect(plan.dimensions).toContain('context_window');
    expect(plan.receipts).toContain('SCBE_OPERATOR_PLAN_READY=1');
  });

  it('moves large remote-ok tasks into cloud assist without forcing dependencies', () => {
    const plan = createTriadicOperatorPlan({
      intent: 'run a large repository verification job',
      privacy: 'remote_ok',
      workload: 'large',
      preferCloud: true,
      features: ['agent-bus', 'batch-dispatch'],
      availablePackages: ['scbe-aethermoore'],
    });

    expect(plan.mode).toBe('cloud_assist');
    expect(plan.actions.join(' ')).toContain('user-approved cloud lane');
    expect(plan.companionRecommendations).toEqual([
      expect.objectContaining({
        feature: 'agent-bus',
        package: 'scbe-agent-bus',
        install: 'pip install scbe-agent-bus',
      }),
      expect.objectContaining({
        feature: 'batch-dispatch',
        package: 'scbe-agent-bus',
      }),
    ]);
  });

  it('does not recommend already installed companion packages', () => {
    const recommendations = recommendCompanionPackages(
      ['agent-bus', 'python'],
      ['scbe-aethermoore', 'scbe-agent-bus']
    );

    expect(recommendations).toEqual([
      expect.objectContaining({
        feature: 'python',
        package: 'scbe-sixtongues',
      }),
    ]);
  });

  it('keeps the dimension list explicit and bounded', () => {
    expect(TRIADIC_DIMENSIONS.length).toBeGreaterThanOrEqual(10);
    expect(TRIADIC_DIMENSIONS).toContain('cost');
    expect(TRIADIC_DIMENSIONS).toContain('audit_receipts');
  });
});
