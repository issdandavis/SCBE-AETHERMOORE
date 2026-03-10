/**
 * @file ccs-connector.unit.test.ts
 * @module fleet/ccs-connector
 * @layer Layer 13, Layer 14
 * @tier L2-unit
 *
 * Unit tests for the Claude Code Studio → SCBE governance bridge.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  CCSConnector,
  classifyTaskTier,
  computeHarmonicCost,
  type CCSTask,
} from '../../src/fleet/ccs-connector';

describe('classifyTaskTier', () => {
  it('classifies read-only operations as KO', () => {
    expect(classifyTaskTier('read the config file')).toBe('KO');
    expect(classifyTaskTier('search for the function definition')).toBe('KO');
    expect(classifyTaskTier('check status of the server')).toBe('KO');
  });

  it('classifies write operations as AV', () => {
    expect(classifyTaskTier('edit the README')).toBe('AV');
    expect(classifyTaskTier('create a new component')).toBe('AV');
    expect(classifyTaskTier('fix the authentication bug')).toBe('AV');
    expect(classifyTaskTier('implement the new feature')).toBe('AV');
  });

  it('classifies execute operations as RU', () => {
    expect(classifyTaskTier('run the test suite')).toBe('RU');
    expect(classifyTaskTier('build the project')).toBe('RU');
    expect(classifyTaskTier('lint all files')).toBe('RU');
    expect(classifyTaskTier('execute npm install')).toBe('RU');
  });

  it('classifies deploy operations as CA', () => {
    expect(classifyTaskTier('push to remote')).toBe('CA');
    expect(classifyTaskTier('create PR for the feature')).toBe('CA');
    expect(classifyTaskTier('deploy to staging')).toBe('CA');
  });

  it('classifies admin operations as UM', () => {
    expect(classifyTaskTier('merge to main branch')).toBe('UM');
    expect(classifyTaskTier('modify CI pipeline')).toBe('UM');
  });

  it('classifies critical operations as DR', () => {
    expect(classifyTaskTier('deploy prod release')).toBe('DR');
    expect(classifyTaskTier('force push to origin')).toBe('DR');
    expect(classifyTaskTier('reset --hard to clean state')).toBe('DR');
    expect(classifyTaskTier('delete branch feature-x')).toBe('DR');
  });

  it('defaults to KO for ambiguous descriptions', () => {
    expect(classifyTaskTier('hello world')).toBe('KO');
    expect(classifyTaskTier('')).toBe('KO');
  });
});

describe('computeHarmonicCost', () => {
  it('returns values bounded in (0, 1]', () => {
    const tiers = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;
    for (const tier of tiers) {
      for (const trust of [0, 0.25, 0.5, 0.75, 1.0]) {
        const cost = computeHarmonicCost(tier, trust);
        expect(cost).toBeGreaterThan(0);
        expect(cost).toBeLessThanOrEqual(1);
      }
    }
  });

  // A2: Unitarity — output bounded
  it('decreases as tier increases (higher tiers cost more)', () => {
    const trust = 0.8;
    const koCost = computeHarmonicCost('KO', trust);
    const drCost = computeHarmonicCost('DR', trust);
    expect(koCost).toBeGreaterThan(drCost);
  });

  // A4: Symmetry — deterministic
  it('is deterministic for same inputs', () => {
    const a = computeHarmonicCost('RU', 0.6);
    const b = computeHarmonicCost('RU', 0.6);
    expect(a).toBe(b);
  });

  it('increases with higher trust (lower policy distance)', () => {
    const lowTrust = computeHarmonicCost('CA', 0.2);
    const highTrust = computeHarmonicCost('CA', 0.9);
    expect(highTrust).toBeGreaterThan(lowTrust);
  });
});

describe('CCSConnector', () => {
  let connector: CCSConnector;

  beforeEach(() => {
    connector = new CCSConnector({ ccsBaseUrl: 'http://localhost:3000' });
  });

  const makeTask = (overrides: Partial<CCSTask> = {}): CCSTask => ({
    id: 'test-task-1',
    title: 'Test Task',
    description: 'read the config file',
    status: 'todo',
    ...overrides,
  });

  describe('evaluateTask', () => {
    it('ALLOWs low-tier tasks with sufficient trust', () => {
      connector.setAgentTrust('default', 0.5);
      const decision = connector.evaluateTask(makeTask({ description: 'read the README' }));
      expect(decision.action).toBe('ALLOW');
      expect(decision.tier).toBe('KO');
    });

    it('QUARANTINEs tasks when trust is below tier threshold', () => {
      connector.setAgentTrust('default', 0.05); // Below KO threshold of 0.1
      const decision = connector.evaluateTask(makeTask({ description: 'read the README' }));
      expect(decision.action).toBe('QUARANTINE');
    });

    it('ESCALATEs UM-tier tasks even with high trust', () => {
      connector.setAgentTrust('default', 0.95);
      const decision = connector.evaluateTask(makeTask({ description: 'merge to main branch' }));
      expect(decision.action).toBe('ESCALATE');
      expect(decision.tier).toBe('UM');
    });

    it('DENYs DR-tier tasks with insufficient trust', () => {
      connector.setAgentTrust('default', 0.5);
      const decision = connector.evaluateTask(makeTask({ description: 'deploy prod release' }));
      expect(decision.action).toBe('DENY');
      expect(decision.tier).toBe('DR');
    });

    it('produces a full 14-layer pipeline trace', () => {
      const decision = connector.evaluateTask(makeTask());
      expect(decision.pipelineTrace.length).toBeGreaterThanOrEqual(10);
      // Verify layer coverage
      const layers = decision.pipelineTrace.map(t => t.layer);
      expect(layers).toContain(1);
      expect(layers).toContain(5);
      expect(layers).toContain(12);
      expect(layers).toContain(13);
      expect(layers).toContain(14);
    });

    it('emits a decision event', () => {
      let emitted = false;
      connector.on('decision', () => { emitted = true; });
      connector.evaluateTask(makeTask());
      expect(emitted).toBe(true);
    });

    it('logs decisions to the audit trail', () => {
      connector.evaluateTask(makeTask());
      connector.evaluateTask(makeTask({ id: 'task-2' }));
      const log = connector.getDecisionLog();
      expect(log).toHaveLength(2);
    });
  });

  describe('evaluateDispatchPlan', () => {
    it('ALLOWs a plan of all low-tier tasks', () => {
      connector.setAgentTrust('default', 0.5);
      const tasks = [
        makeTask({ id: '1', description: 'read file A' }),
        makeTask({ id: '2', description: 'read file B' }),
      ];
      const { aggregate } = connector.evaluateDispatchPlan(tasks);
      expect(aggregate).toBe('ALLOW');
    });

    it('DENYs a plan if any task is denied', () => {
      connector.setAgentTrust('default', 0.3);
      const tasks = [
        makeTask({ id: '1', description: 'read file A' }),
        makeTask({ id: '2', description: 'deploy prod release' }), // DR tier, trust too low
      ];
      const { aggregate } = connector.evaluateDispatchPlan(tasks);
      expect(aggregate).toBe('DENY');
    });

    it('ESCALATEs a plan containing UM-tier tasks with sufficient trust', () => {
      connector.setAgentTrust('default', 0.95);
      const tasks = [
        makeTask({ id: '1', description: 'edit the component' }),
        makeTask({ id: '2', description: 'merge to main branch' }),
      ];
      const { aggregate, perTask } = connector.evaluateDispatchPlan(tasks);
      expect(aggregate).toBe('ESCALATE');
      expect(perTask.get('1')?.action).toBe('ALLOW');
      expect(perTask.get('2')?.action).toBe('ESCALATE');
    });
  });

  describe('trust management', () => {
    it('defaults to 0.5 trust for unknown agents', () => {
      expect(connector.getAgentTrust('unknown-agent')).toBe(0.5);
    });

    it('clamps trust to [0, 1]', () => {
      connector.setAgentTrust('agent-1', 1.5);
      expect(connector.getAgentTrust('agent-1')).toBe(1);

      connector.setAgentTrust('agent-2', -0.5);
      expect(connector.getAgentTrust('agent-2')).toBe(0);
    });

    it('adjusts trust on success/failure', () => {
      connector.setAgentTrust('agent-1', 0.5);
      connector.recordOutcome('agent-1', true);
      expect(connector.getAgentTrust('agent-1')).toBeCloseTo(0.51);

      connector.recordOutcome('agent-1', false);
      expect(connector.getAgentTrust('agent-1')).toBeCloseTo(0.46);
    });
  });

  describe('getStats', () => {
    it('returns zero stats when no decisions logged', () => {
      const stats = connector.getStats();
      expect(stats.total).toBe(0);
      expect(stats.avgHarmonicCost).toBe(0);
    });

    it('computes accurate statistics', () => {
      connector.setAgentTrust('default', 0.5);
      // Two ALLOWs
      connector.evaluateTask(makeTask({ id: '1', description: 'read file' }));
      connector.evaluateTask(makeTask({ id: '2', description: 'search code' }));
      // One QUARANTINE
      connector.setAgentTrust('default', 0.05);
      connector.evaluateTask(makeTask({ id: '3', description: 'read file' }));

      const stats = connector.getStats();
      expect(stats.total).toBe(3);
      expect(stats.allow).toBe(2);
      expect(stats.quarantine).toBe(1);
      expect(stats.avgHarmonicCost).toBeGreaterThan(0);
    });
  });
});
