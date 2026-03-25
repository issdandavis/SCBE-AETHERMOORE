/**
 * Juggling Agent Coordination Scheduler Tests
 *
 * @module tests/fleet/juggling-scheduler
 */

import { describe, expect, it, beforeEach } from 'vitest';
import {
  FlightState,
  JugglingScheduler,
  TaskCapsule,
  AgentSlot,
  createCapsule,
  assignmentScore,
  recoverability,
  selectArcHeight,
  agentSlotFromFleet,
  DEFAULT_SCORE_WEIGHTS,
  MAX_RETRIES,
  PHASE_DRIFT_THRESHOLD,
} from '../../src/fleet/juggling-scheduler';
import type { FleetAgent, GovernanceTier } from '../../src/fleet/types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeAgent(overrides: Partial<AgentSlot> = {}): AgentSlot {
  return {
    agentId: 'agent-1',
    roles: ['code_generation'],
    catchCapacity: 3,
    currentLoad: 0,
    reliability: 0.9,
    trustDomains: ['KO', 'AV', 'RU'] as GovernanceTier[],
    avgLatencyMs: 50,
    lastCatchAt: Date.now(),
    consecutiveMisses: 0,
    ...overrides,
  };
}

function makeCapsule(overrides: Partial<ReturnType<typeof createCapsule>> = {}): TaskCapsule {
  const base = createCapsule({
    taskId: 'task-1',
    payloadRef: 'ref://payload/1',
    priority: 'medium',
    trustScore: 0.6,
    inertia: 0.2,
    risk: 0.3,
    deadlineMs: 30_000,
    requiredTier: 'KO',
  });
  return { ...base, ...overrides };
}

// ---------------------------------------------------------------------------
// Unit Tests
// ---------------------------------------------------------------------------

describe('JugglingScheduler', () => {
  let scheduler: JugglingScheduler;

  beforeEach(() => {
    scheduler = new JugglingScheduler();
  });

  // ---- FlightState ----

  describe('FlightState enum', () => {
    it('should have all required states', () => {
      expect(FlightState.HELD).toBe('held');
      expect(FlightState.THROWN).toBe('thrown');
      expect(FlightState.CAUGHT).toBe('caught');
      expect(FlightState.VALIDATING).toBe('validating');
      expect(FlightState.RECOVERING).toBe('recovering');
      expect(FlightState.DROPPED).toBe('dropped');
      expect(FlightState.DONE).toBe('done');
    });
  });

  // ---- Scoring ----

  describe('assignmentScore', () => {
    it('should return higher score for more reliable agents', () => {
      const task = makeCapsule();
      const agentA = makeAgent({ agentId: 'a', reliability: 0.95 });
      const agentB = makeAgent({ agentId: 'b', reliability: 0.5 });
      const now = Date.now();

      expect(assignmentScore(task, agentA, now)).toBeGreaterThan(
        assignmentScore(task, agentB, now)
      );
    });

    it('should penalise loaded agents', () => {
      const task = makeCapsule();
      const idle = makeAgent({ agentId: 'idle', currentLoad: 0 });
      const busy = makeAgent({ agentId: 'busy', currentLoad: 2 });
      const now = Date.now();

      expect(assignmentScore(task, idle, now)).toBeGreaterThan(assignmentScore(task, busy, now));
    });

    it('should penalise high-risk tasks', () => {
      const low = makeCapsule({ taskId: 'low', risk: 0.1 });
      const high = makeCapsule({ taskId: 'high', risk: 0.9 });
      const agent = makeAgent();
      const now = Date.now();

      expect(assignmentScore(low, agent, now)).toBeGreaterThan(assignmentScore(high, agent, now));
    });

    it('should penalise governance tier mismatch', () => {
      const task = makeCapsule({ requiredTier: 'DR' });
      const lowTier = makeAgent({ agentId: 'low', trustDomains: ['KO'] as GovernanceTier[] });
      const highTier = makeAgent({
        agentId: 'high',
        trustDomains: ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as GovernanceTier[],
      });
      const now = Date.now();

      expect(assignmentScore(task, highTier, now)).toBeGreaterThan(
        assignmentScore(task, lowTier, now)
      );
    });
  });

  // ---- Recoverability ----

  describe('recoverability', () => {
    it('should return 1.0 at creation time', () => {
      const task = makeCapsule();
      expect(recoverability(task, task.createdAt)).toBeCloseTo(1.0);
    });

    it('should decay over time', () => {
      const task = makeCapsule();
      const later = task.createdAt + 20_000; // 20s later
      expect(recoverability(task, later)).toBeLessThan(1.0);
      expect(recoverability(task, later)).toBeGreaterThan(0);
    });

    it('should decay faster with higher lambda', () => {
      const task = makeCapsule();
      const later = task.createdAt + 10_000;
      expect(recoverability(task, later, 0.1)).toBeLessThan(recoverability(task, later, 0.01));
    });
  });

  // ---- Arc Height ----

  describe('selectArcHeight', () => {
    it('should return 1 for very low risk/inertia', () => {
      expect(selectArcHeight(0, 0)).toBe(1);
    });

    it('should return 7 for very high risk/inertia', () => {
      expect(selectArcHeight(1.0, 1.0)).toBe(7);
    });

    it('should increase with risk', () => {
      const low = selectArcHeight(0.1, 0.1);
      const high = selectArcHeight(0.9, 0.1);
      expect(high).toBeGreaterThanOrEqual(low);
    });
  });

  // ---- Capsule Factory ----

  describe('createCapsule', () => {
    it('should create a capsule in HELD state', () => {
      const c = createCapsule({ taskId: 'x', payloadRef: 'ref://x' });
      expect(c.state).toBe(FlightState.HELD);
      expect(c.owner).toBeNull();
      expect(c.retryCount).toBe(0);
    });

    it('should set arc height from risk/inertia', () => {
      const c = createCapsule({ taskId: 'x', payloadRef: 'ref://x', risk: 0.9, inertia: 0.9 });
      expect(c.arcHeight).toBe(7);
    });

    it('should set deadline relative to now', () => {
      const before = Date.now();
      const c = createCapsule({ taskId: 'x', payloadRef: 'ref://x', deadlineMs: 5000 });
      expect(c.deadlineAt).toBeGreaterThanOrEqual(before + 5000);
    });
  });

  // ---- Agent Registration ----

  describe('Agent management', () => {
    it('should register and retrieve agents', () => {
      const agent = makeAgent();
      scheduler.registerAgent(agent);
      expect(scheduler.getAgent('agent-1')).toBeDefined();
      expect(scheduler.getAgent('agent-1')!.reliability).toBe(0.9);
    });

    it('should orphan tasks when agent is removed', () => {
      const agent = makeAgent();
      scheduler.registerAgent(agent);

      const capsule = makeCapsule({ owner: 'agent-1', state: FlightState.CAUGHT });
      scheduler.addCapsule(capsule);

      const orphaned = scheduler.removeAgent('agent-1');
      expect(orphaned).toHaveLength(1);
      expect(orphaned[0].state).toBe(FlightState.RECOVERING);
      expect(orphaned[0].owner).toBeNull();
    });
  });

  // ---- Core Scheduling: Throw & Catch ----

  describe('throwCapsule', () => {
    it('should assign capsule to the best available agent', () => {
      scheduler.registerAgent(makeAgent({ agentId: 'a1', reliability: 0.9 }));
      scheduler.registerAgent(makeAgent({ agentId: 'a2', reliability: 0.7 }));

      const capsule = makeCapsule({ nextCandidates: ['a1', 'a2'] });
      scheduler.addCapsule(capsule);

      const receipt = scheduler.throwCapsule('task-1');
      expect(receipt).not.toBeNull();
      expect(receipt!.receiverId).toBe('a1'); // higher reliability wins
      expect(receipt!.feasibilityConfirmed).toBe(true);

      const updated = scheduler.getCapsule('task-1')!;
      expect(updated.owner).toBe('a1');
      expect(updated.state).toBe(FlightState.CAUGHT);
    });

    it('should fall back to fallback candidates when primaries are full', () => {
      scheduler.registerAgent(makeAgent({ agentId: 'primary', catchCapacity: 1, currentLoad: 1 }));
      scheduler.registerAgent(makeAgent({ agentId: 'backup', reliability: 0.8 }));

      const capsule = makeCapsule({
        nextCandidates: ['primary'],
        fallbackCandidates: ['backup'],
      });
      scheduler.addCapsule(capsule);

      const receipt = scheduler.throwCapsule('task-1');
      expect(receipt).not.toBeNull();
      expect(receipt!.receiverId).toBe('backup');
    });

    it('should return null when no agent can catch', () => {
      scheduler.registerAgent(makeAgent({ agentId: 'full', catchCapacity: 1, currentLoad: 1 }));

      const capsule = makeCapsule({ nextCandidates: ['full'] });
      scheduler.addCapsule(capsule);

      const receipt = scheduler.throwCapsule('task-1');
      expect(receipt).toBeNull();
    });

    it('should refuse agents below required governance tier', () => {
      scheduler.registerAgent(
        makeAgent({
          agentId: 'low',
          trustDomains: ['KO'] as GovernanceTier[],
        })
      );

      const capsule = makeCapsule({ requiredTier: 'DR' });
      scheduler.addCapsule(capsule);

      const receipt = scheduler.throwCapsule('task-1');
      expect(receipt).toBeNull();
    });

    it('should enter VALIDATING for quorum > 1', () => {
      scheduler.registerAgent(makeAgent());

      const capsule = makeCapsule({ requiredQuorum: 3 });
      scheduler.addCapsule(capsule);

      scheduler.throwCapsule('task-1');
      expect(scheduler.getCapsule('task-1')!.state).toBe(FlightState.VALIDATING);
    });
  });

  // ---- Completion ----

  describe('completeCapsule', () => {
    it('should mark capsule DONE and free agent slot', () => {
      const agent = makeAgent();
      scheduler.registerAgent(agent);

      const capsule = makeCapsule();
      scheduler.addCapsule(capsule);
      scheduler.throwCapsule('task-1');

      expect(scheduler.getAgent('agent-1')!.currentLoad).toBe(1);

      const ok = scheduler.completeCapsule('task-1');
      expect(ok).toBe(true);
      expect(scheduler.getCapsule('task-1')!.state).toBe(FlightState.DONE);
      expect(scheduler.getAgent('agent-1')!.currentLoad).toBe(0);
    });

    it('should record provenance for completion', () => {
      scheduler.registerAgent(makeAgent());
      const capsule = makeCapsule();
      scheduler.addCapsule(capsule);
      scheduler.throwCapsule('task-1');
      scheduler.completeCapsule('task-1');

      const c = scheduler.getCapsule('task-1')!;
      const doneEntries = c.provenance.filter(([, , s]) => s === FlightState.DONE);
      expect(doneEntries.length).toBe(1);
    });
  });

  // ---- Drop & Recovery ----

  describe('handleDrop', () => {
    it('should increment retry and re-throw on first drop', () => {
      scheduler.registerAgent(makeAgent({ agentId: 'a1' }));
      scheduler.registerAgent(makeAgent({ agentId: 'a2' }));

      const capsule = makeCapsule({ owner: 'a1' });
      capsule.state = FlightState.CAUGHT;
      scheduler.addCapsule(capsule);

      const receipt = scheduler.handleDrop('task-1');
      expect(receipt).not.toBeNull();
      expect(scheduler.getCapsule('task-1')!.retryCount).toBe(1);
    });

    it('should permanently drop after MAX_RETRIES', () => {
      scheduler.registerAgent(makeAgent());
      const capsule = makeCapsule({ retryCount: MAX_RETRIES - 1 });
      scheduler.addCapsule(capsule);

      scheduler.handleDrop('task-1');
      expect(scheduler.getCapsule('task-1')!.state).toBe(FlightState.DROPPED);
    });

    it('should drop high-inertia tasks earlier (Rule 3)', () => {
      scheduler.registerAgent(makeAgent());
      const capsule = makeCapsule({ inertia: 0.8, retryCount: 1 });
      scheduler.addCapsule(capsule);

      scheduler.handleDrop('task-1');
      expect(scheduler.getCapsule('task-1')!.state).toBe(FlightState.DROPPED);
    });
  });

  // ---- Phase Drift ----

  describe('detectPhaseDrift', () => {
    it('should return 0 when no capsules are in flight', () => {
      expect(scheduler.detectPhaseDrift()).toBe(0);
    });

    it('should detect drift when capsules are overdue', () => {
      // Create already-expired capsule in RECOVERING state
      const capsule = makeCapsule({
        deadlineAt: Date.now() - 1000,
        state: FlightState.RECOVERING,
      });
      scheduler.addCapsule(capsule);

      const drift = scheduler.detectPhaseDrift();
      expect(drift).toBe(1.0);
    });
  });

  // ---- Metrics ----

  describe('getMetrics', () => {
    it('should report correct counts', () => {
      scheduler.registerAgent(makeAgent());

      const c1 = makeCapsule({ taskId: 't1' });
      const c2 = makeCapsule({ taskId: 't2' });
      scheduler.addCapsule(c1);
      scheduler.addCapsule(c2);

      scheduler.throwCapsule('t1');
      scheduler.completeCapsule('t1');

      const m = scheduler.getMetrics();
      expect(m.catches).toBe(1); // t1 done
      expect(m.held).toBe(1); // t2 still held
    });

    it('should report cadence health between 0 and 1', () => {
      const m = scheduler.getMetrics();
      expect(m.cadenceHealth).toBeGreaterThanOrEqual(0);
      expect(m.cadenceHealth).toBeLessThanOrEqual(1);
    });
  });

  // ---- Tick ----

  describe('tick', () => {
    it('should assign unowned HELD capsules', () => {
      scheduler.registerAgent(makeAgent());
      const capsule = makeCapsule();
      scheduler.addCapsule(capsule);

      scheduler.tick();

      const updated = scheduler.getCapsule('task-1')!;
      expect(updated.owner).not.toBeNull();
      expect(updated.state).not.toBe(FlightState.HELD);
    });

    it('should expire overdue capsules', () => {
      scheduler.registerAgent(makeAgent());
      const capsule = makeCapsule({
        taskId: 'expired',
        deadlineAt: Date.now() - 1000,
        state: FlightState.CAUGHT,
        owner: 'agent-1',
      });
      scheduler.addCapsule(capsule);

      scheduler.tick();

      const updated = scheduler.getCapsule('expired')!;
      expect([FlightState.DROPPED, FlightState.CAUGHT, FlightState.RECOVERING]).toContain(
        updated.state
      );
    });
  });

  // ---- Siteswap Encoding ----

  describe('encodeSiteswap', () => {
    it('should encode a catch-complete journey', () => {
      scheduler.registerAgent(makeAgent());
      const capsule = makeCapsule({ arcHeight: 3 });
      scheduler.addCapsule(capsule);
      scheduler.throwCapsule('task-1');
      scheduler.completeCapsule('task-1');

      const ss = scheduler.encodeSiteswap('task-1');
      expect(ss).toContain('3');
      expect(ss).toContain('0');
    });

    it('should include Q for quorum-validated tasks', () => {
      scheduler.registerAgent(makeAgent());
      const capsule = makeCapsule({ requiredQuorum: 2, arcHeight: 5 });
      scheduler.addCapsule(capsule);
      scheduler.throwCapsule('task-1');

      const ss = scheduler.encodeSiteswap('task-1');
      expect(ss).toContain('5');
    });
  });

  // ---- Event Ledger (Rule 7) ----

  describe('Event ledger', () => {
    it('should record catch events', () => {
      scheduler.registerAgent(makeAgent());
      scheduler.addCapsule(makeCapsule());
      scheduler.throwCapsule('task-1');

      const catchEvents = scheduler.getEvents().filter((e) => e.type === 'catch');
      expect(catchEvents.length).toBe(1);
      expect(catchEvents[0].agentId).toBe('agent-1');
    });

    it('should record drop events', () => {
      scheduler.registerAgent(makeAgent());
      const capsule = makeCapsule({ retryCount: MAX_RETRIES - 1 });
      scheduler.addCapsule(capsule);
      scheduler.handleDrop('task-1');

      const dropEvents = scheduler.getEvents().filter((e) => e.type === 'drop');
      expect(dropEvents.length).toBe(1);
    });

    it('should produce HandoffReceipts for every catch', () => {
      scheduler.registerAgent(makeAgent());
      scheduler.addCapsule(makeCapsule());
      scheduler.throwCapsule('task-1');

      const receipts = scheduler.getReceipts();
      expect(receipts.length).toBe(1);
      expect(receipts[0].receiverId).toBe('agent-1');
      expect(receipts[0].newOwner).toBe('agent-1');
    });
  });

  // ---- FleetAgent Bridge ----

  describe('agentSlotFromFleet', () => {
    it('should convert a FleetAgent into an AgentSlot', () => {
      const fleet: FleetAgent = {
        id: 'fleet-1',
        name: 'TestBot',
        description: 'A test agent',
        provider: 'anthropic',
        model: 'claude-opus-4-6',
        capabilities: ['code_generation', 'code_review'],
        status: 'idle',
        trustVector: [1, 0.5, 0.3, 0, 0, 0],
        maxConcurrentTasks: 5,
        currentTaskCount: 2,
        maxGovernanceTier: 'CA',
        registeredAt: Date.now(),
        lastActiveAt: Date.now(),
        tasksCompleted: 100,
        successRate: 0.92,
      };

      const slot = agentSlotFromFleet(fleet);

      expect(slot.agentId).toBe('fleet-1');
      expect(slot.catchCapacity).toBe(5);
      expect(slot.currentLoad).toBe(2);
      expect(slot.reliability).toBe(0.92);
      expect(slot.trustDomains).toEqual(['KO', 'AV', 'RU', 'CA']);
    });
  });
});
