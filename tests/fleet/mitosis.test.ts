/**
 * @file mitosis.test.ts
 * @module tests/fleet
 * @layer Layer 13 (Governance)
 * @component Agent Mitosis Tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { MitosisManager } from '../../src/fleet/mitosis.js';
import type { FleetAgent, AgentCapability } from '../../src/fleet/types.js';

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

const mockAgent = (overrides?: Partial<FleetAgent>): FleetAgent => ({
  id: 'agent-1',
  name: 'TestAgent',
  description: 'Test',
  provider: 'openai',
  model: 'gpt-4o',
  capabilities: ['code_generation'] as AgentCapability[],
  status: 'idle' as const,
  trustVector: [0.8, 0.7, 0.6, 0.5, 0.4, 0.3],
  maxConcurrentTasks: 3,
  currentTaskCount: 0,
  maxGovernanceTier: 'RU' as const,
  registeredAt: Date.now(),
  lastActiveAt: Date.now(),
  tasksCompleted: 5,
  successRate: 0.9,
  ...overrides,
});

// A flux value that satisfies ν >= 0.8 (POLLY state)
const HIGH_FLUX = 0.9;
// A flux value below 0.8 (QUASI state)
const LOW_FLUX = 0.6;

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('MitosisManager', () => {
  let manager: MitosisManager;

  beforeEach(() => {
    manager = new MitosisManager();
  });

  // -------------------------------------------------------------------------
  // checkEligibility — positive path
  // -------------------------------------------------------------------------

  describe('checkEligibility', () => {
    it('returns eligible=true for a fully qualified agent', () => {
      const agent = mockAgent();
      const result = manager.checkEligibility(agent, HIGH_FLUX);

      expect(result.eligible).toBe(true);
      expect(result.reason).toBeUndefined();
    });

    // -----------------------------------------------------------------------
    // Rejection cases
    // -----------------------------------------------------------------------

    it('rejects non-idle agent', () => {
      const agent = mockAgent({ status: 'busy' });
      const result = manager.checkEligibility(agent, HIGH_FLUX);

      expect(result.eligible).toBe(false);
      expect(result.reason).toMatch(/idle/i);
    });

    it('rejects agent with insufficient completed tasks', () => {
      // Default minTasksForEligibility = 3; give only 2
      const agent = mockAgent({ tasksCompleted: 2 });
      const result = manager.checkEligibility(agent, HIGH_FLUX);

      expect(result.eligible).toBe(false);
      expect(result.reason).toMatch(/task/i);
    });

    it('rejects agent when flux is below POLLY threshold (ν < 0.8)', () => {
      const agent = mockAgent();
      const result = manager.checkEligibility(agent, LOW_FLUX);

      expect(result.eligible).toBe(false);
      expect(result.reason).toMatch(/flux|POLLY/i);
    });

    it('rejects agent that has reached maximum genealogy depth', () => {
      // Create a manager with maxDepth = 5 (default), then simulate depth = 5
      const mgr = new MitosisManager({ maxDepth: 5 });
      const parent = mockAgent({ id: 'deep-agent' });

      // Reach depth 5 by dividing 5 times through a chain of agents
      let currentParentId = 'root';
      // Seed depth 5 directly by finalizing 5 levels of fake records
      // We dive once per level using divide() with unique agents
      const depthMgr = new MitosisManager({ maxDepth: 5, cooldownMs: 0 });

      let prevId = 'root-0';
      for (let i = 0; i < 5; i++) {
        const p = mockAgent({ id: prevId, tasksCompleted: 10 });
        const { record, childDefinition } = depthMgr.divide(p, HIGH_FLUX);
        expect(childDefinition).not.toBeNull();
        const childId = `child-depth-${i + 1}`;
        depthMgr.finalizeRegistration(record.id, childId);
        prevId = childId;
      }

      // prevId is now at depth 5 — further division should be rejected
      const deepAgent = mockAgent({ id: prevId, tasksCompleted: 10 });
      const result = depthMgr.checkEligibility(deepAgent, HIGH_FLUX);

      expect(result.eligible).toBe(false);
      expect(result.reason).toMatch(/depth/i);
    });

    it('rejects agent that has reached maximum children per parent', () => {
      const mgr = new MitosisManager({ maxChildrenPerParent: 3, cooldownMs: 0 });
      const parent = mockAgent({ id: 'busy-parent', tasksCompleted: 10 });

      // Divide 3 times to fill up children slots
      for (let i = 0; i < 3; i++) {
        const { record, childDefinition } = mgr.divide(parent, HIGH_FLUX);
        expect(childDefinition).not.toBeNull();
        mgr.finalizeRegistration(record.id, `child-${i}`);
      }

      // Fourth division attempt should be rejected
      const result = mgr.checkEligibility(parent, HIGH_FLUX);

      expect(result.eligible).toBe(false);
      expect(result.reason).toMatch(/children/i);
    });

    it('rejects agent whose cooldown has not elapsed', () => {
      const mgr = new MitosisManager({ cooldownMs: 60_000 });
      const parent = mockAgent({ id: 'cooldown-parent', tasksCompleted: 10 });
      const now = Date.now();

      // Perform first division at time `now`
      const { childDefinition } = mgr.divide(parent, HIGH_FLUX, undefined, undefined, now);
      expect(childDefinition).not.toBeNull();

      // Attempt second division 30 s later (cooldown = 60 s)
      const result = mgr.checkEligibility(parent, HIGH_FLUX, now + 30_000);

      expect(result.eligible).toBe(false);
      expect(result.reason).toMatch(/cooldown/i);
    });
  });

  // -------------------------------------------------------------------------
  // divide()
  // -------------------------------------------------------------------------

  describe('divide', () => {
    it('produces a child definition with trust vector decayed by the inheritance factor', () => {
      const parent = mockAgent({ trustVector: [0.8, 0.6, 0.4, 0.2, 0.1, 0.05] });
      const { record, childDefinition } = manager.divide(parent, HIGH_FLUX);

      expect(record.phase).toBe('COMPLETE');
      expect(childDefinition).not.toBeNull();

      // Each child trust component should be parent × 0.7 (default factor)
      const expected = parent.trustVector.map((t) => t * 0.7);
      childDefinition!.trustVector!.forEach((v, i) => {
        expect(v).toBeCloseTo(expected[i], 10);
      });
    });

    it('returns null childDefinition and REJECTED phase when eligibility fails', () => {
      const agent = mockAgent({ status: 'busy' });
      const { record, childDefinition } = manager.divide(agent, HIGH_FLUX);

      expect(record.phase).toBe('REJECTED');
      expect(record.rejectionReason).toBeDefined();
      expect(childDefinition).toBeNull();
    });

    it('applies custom specialization capabilities to the child', () => {
      const parent = mockAgent({
        capabilities: ['code_generation', 'testing', 'documentation'] as AgentCapability[],
      });
      const specialization: AgentCapability[] = ['testing'];

      const { childDefinition } = manager.divide(parent, HIGH_FLUX, 'SpecialChild', specialization);

      expect(childDefinition).not.toBeNull();
      expect(childDefinition!.capabilities).toEqual(['testing']);
    });

    it('generates a default child name when none is provided', () => {
      const parent = mockAgent();
      const { childDefinition } = manager.divide(parent, HIGH_FLUX);

      expect(childDefinition).not.toBeNull();
      expect(childDefinition!.name).toContain(parent.name);
    });

    it('uses the provided child name when specified', () => {
      const parent = mockAgent();
      const { childDefinition } = manager.divide(parent, HIGH_FLUX, 'CustomChildName');

      expect(childDefinition).not.toBeNull();
      expect(childDefinition!.name).toBe('CustomChildName');
    });

    it('uses custom trustInheritanceFactor from config', () => {
      const mgr = new MitosisManager({ trustInheritanceFactor: 0.5 });
      const parent = mockAgent({ trustVector: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0] });

      const { childDefinition } = mgr.divide(parent, HIGH_FLUX);

      expect(childDefinition).not.toBeNull();
      childDefinition!.trustVector!.forEach((v) => {
        expect(v).toBeCloseTo(0.5, 10);
      });
    });

    it('records the mitosis event and stores it in getRecords()', () => {
      const parent = mockAgent();
      manager.divide(parent, HIGH_FLUX);

      const records = manager.getRecords();
      expect(records).toHaveLength(1);
      expect(records[0].parentId).toBe(parent.id);
    });
  });

  // -------------------------------------------------------------------------
  // finalizeRegistration()
  // -------------------------------------------------------------------------

  describe('finalizeRegistration', () => {
    it('updates the record with the child ID and links genealogy', () => {
      const parent = mockAgent({ id: 'parent-x', tasksCompleted: 10 });
      const { record } = manager.divide(parent, HIGH_FLUX);

      manager.finalizeRegistration(record.id, 'child-x');

      const records = manager.getRecords();
      expect(records[0].childId).toBe('child-x');
    });

    it('does nothing when an unknown recordId is given', () => {
      // Should not throw
      expect(() => manager.finalizeRegistration('no-such-id', 'child-z')).not.toThrow();
    });

    it('emits an agent_registered event via addEventListener', () => {
      const events: unknown[] = [];
      manager.addEventListener((e) => events.push(e));

      const parent = mockAgent({ id: 'parent-emit', tasksCompleted: 10 });
      const { record } = manager.divide(parent, HIGH_FLUX);
      manager.finalizeRegistration(record.id, 'child-emit');

      expect(events).toHaveLength(1);
      const ev = events[0] as { type: string; agentId: string };
      expect(ev.type).toBe('agent_registered');
      expect(ev.agentId).toBe('child-emit');
    });
  });

  // -------------------------------------------------------------------------
  // getChildren() / getDepth()
  // -------------------------------------------------------------------------

  describe('getChildren and getDepth', () => {
    it('getChildren returns empty array for an agent with no children', () => {
      expect(manager.getChildren('nobody')).toEqual([]);
    });

    it('getDepth returns 0 for an unknown agent (root default)', () => {
      expect(manager.getDepth('unknown')).toBe(0);
    });

    it('getChildren returns registered child IDs after finalizeRegistration', () => {
      const mgr = new MitosisManager({ cooldownMs: 0 });
      const parent = mockAgent({ id: 'parent-gc', tasksCompleted: 10 });

      const { record: r1 } = mgr.divide(parent, HIGH_FLUX);
      mgr.finalizeRegistration(r1.id, 'child-gc-1');

      const { record: r2 } = mgr.divide(parent, HIGH_FLUX);
      mgr.finalizeRegistration(r2.id, 'child-gc-2');

      const children = mgr.getChildren('parent-gc');
      expect(children).toContain('child-gc-1');
      expect(children).toContain('child-gc-2');
      expect(children).toHaveLength(2);
    });

    it('getDepth correctly tracks child depth after finalizeRegistration', () => {
      const mgr = new MitosisManager({ cooldownMs: 0 });
      const parent = mockAgent({ id: 'parent-depth', tasksCompleted: 10 });

      // parent is at depth 0 (default)
      expect(mgr.getDepth('parent-depth')).toBe(0);

      const { record } = mgr.divide(parent, HIGH_FLUX);
      mgr.finalizeRegistration(record.id, 'child-depth-1');

      // child should be at depth 1
      expect(mgr.getDepth('child-depth-1')).toBe(1);
    });

    it('getDepth correctly tracks grandchild depth through two levels', () => {
      const mgr = new MitosisManager({ cooldownMs: 0 });

      // Level 0: root parent
      const root = mockAgent({ id: 'root', tasksCompleted: 10 });
      const { record: r1 } = mgr.divide(root, HIGH_FLUX);
      mgr.finalizeRegistration(r1.id, 'level-1');

      // Level 1: child becomes a parent
      const child = mockAgent({ id: 'level-1', tasksCompleted: 10 });
      const { record: r2 } = mgr.divide(child, HIGH_FLUX);
      mgr.finalizeRegistration(r2.id, 'level-2');

      expect(mgr.getDepth('level-2')).toBe(2);
    });
  });
});
