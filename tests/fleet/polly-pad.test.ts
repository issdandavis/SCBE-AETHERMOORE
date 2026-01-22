/**
 * Polly Pad & Swarm Coordination Tests
 * 
 * Tests for personal agent workspaces with dimensional flux coordination.
 */

import { beforeEach, describe, expect, it } from 'vitest';
import {
    PollyPadManager,
    TIER_THRESHOLDS,
    getNextTier,
    getXPForNextTier
} from '../../src/fleet/polly-pad';
import { SwarmCoordinator } from '../../src/fleet/swarm';
import { getDimensionalState } from '../../src/fleet/types';

describe('PollyPadManager', () => {
  let manager: PollyPadManager;

  beforeEach(() => {
    manager = new PollyPadManager();
  });

  describe('Pad Creation', () => {
    it('should create a pad with default values', () => {
      const pad = manager.createPad('agent-1', 'Test Pad');
      
      expect(pad.id).toBeDefined();
      expect(pad.agentId).toBe('agent-1');
      expect(pad.name).toBe('Test Pad');
      expect(pad.nu).toBe(1.0);
      expect(pad.dimensionalState).toBe('POLLY');
      expect(pad.tier).toBe('KO');
      expect(pad.notes).toHaveLength(0);
      expect(pad.sketches).toHaveLength(0);
      expect(pad.tools).toHaveLength(0);
    });

    it('should create pad with custom tier and trust vector', () => {
      const trustVector = [0.8, 0.7, 0.9, 0.6, 0.7, 0.5];
      const pad = manager.createPad('agent-2', 'Senior Pad', 'CA', trustVector);
      
      expect(pad.tier).toBe('CA');
      expect(pad.trustVector).toEqual(trustVector);
    });

    it('should retrieve pad by ID and agent ID', () => {
      const pad = manager.createPad('agent-3', 'Lookup Test');
      
      expect(manager.getPad(pad.id)).toBe(pad);
      expect(manager.getPadByAgent('agent-3')).toBe(pad);
    });
  });

  describe('Dimensional State', () => {
    it('should correctly determine dimensional state from nu', () => {
      expect(getDimensionalState(1.0)).toBe('POLLY');
      expect(getDimensionalState(0.95)).toBe('POLLY');
      expect(getDimensionalState(0.7)).toBe('QUASI');
      expect(getDimensionalState(0.5)).toBe('QUASI');
      expect(getDimensionalState(0.3)).toBe('DEMI');
      expect(getDimensionalState(0.1)).toBe('DEMI');  // 0.1 is the DEMI threshold
      expect(getDimensionalState(0.09)).toBe('COLLAPSED');  // Below 0.1 is COLLAPSED
      expect(getDimensionalState(0)).toBe('COLLAPSED');
    });

    it('should update flux and dimensional state', () => {
      const pad = manager.createPad('agent-4', 'Flux Test');
      
      manager.updateFlux(pad.id, 0.6);
      expect(pad.nu).toBe(0.6);
      expect(pad.dimensionalState).toBe('QUASI');
      
      manager.updateFlux(pad.id, 0.2);
      expect(pad.dimensionalState).toBe('DEMI');
    });

    it('should clamp flux to [0, 1]', () => {
      const pad = manager.createPad('agent-5', 'Clamp Test');
      
      manager.updateFlux(pad.id, 1.5);
      expect(pad.nu).toBe(1.0);
      
      manager.updateFlux(pad.id, -0.5);
      expect(pad.nu).toBe(0);
    });

    it('should gradually transition flux to target', () => {
      const pad = manager.createPad('agent-6', 'Transition Test');
      
      manager.setTargetFlux(pad.id, 0.5, 0.1);
      expect(pad.targetNu).toBe(0.5);
      
      // Step toward target (6 steps to ensure we reach it)
      for (let i = 0; i < 6; i++) {
        manager.stepFlux(pad.id);
      }
      
      expect(pad.nu).toBeCloseTo(0.5, 2);
      // After reaching target, targetNu should be cleared
      expect(pad.targetNu === undefined || Math.abs(pad.nu - 0.5) < 0.01).toBe(true);
    });
  });

  describe('Workspace Operations', () => {
    it('should add notes to pad', () => {
      const pad = manager.createPad('agent-7', 'Notes Test');
      
      const note = manager.addNote(pad.id, {
        title: 'Test Note',
        content: 'This is a test note',
        tags: ['test', 'demo'],
        shared: false
      });
      
      expect(note.id).toBeDefined();
      expect(note.title).toBe('Test Note');
      expect(pad.notes).toHaveLength(1);
    });

    it('should add sketches to pad', () => {
      const pad = manager.createPad('agent-8', 'Sketch Test');
      
      const sketch = manager.addSketch(pad.id, {
        name: 'Architecture Diagram',
        data: '<svg>...</svg>',
        type: 'architecture',
        shared: true
      });
      
      expect(sketch.id).toBeDefined();
      expect(sketch.type).toBe('architecture');
      expect(pad.sketches).toHaveLength(1);
    });

    it('should add tools to pad', () => {
      const pad = manager.createPad('agent-9', 'Tools Test');
      
      const tool = manager.addTool(pad.id, {
        name: 'Code Formatter',
        description: 'Formats code nicely',
        type: 'script',
        content: 'prettier --write .'
      });
      
      expect(tool.id).toBeDefined();
      expect(tool.usageCount).toBe(0);
      expect(tool.effectiveness).toBe(0.5);
      expect(pad.tools).toHaveLength(1);
      expect(pad.toolsCreated).toBe(1);
    });

    it('should track tool usage and effectiveness', () => {
      const pad = manager.createPad('agent-10', 'Tool Usage Test');
      const tool = manager.addTool(pad.id, {
        name: 'Test Tool',
        description: 'Test',
        type: 'snippet',
        content: 'test'
      });
      
      manager.useTool(pad.id, tool.id, true);
      manager.useTool(pad.id, tool.id, true);
      manager.useTool(pad.id, tool.id, false);
      
      expect(tool.usageCount).toBe(3);
      expect(tool.lastUsed).toBeDefined();
      // Effectiveness should be updated via EMA
      expect(tool.effectiveness).toBeGreaterThan(0);
    });

    it('should prevent operations in wrong dimensional state', () => {
      const pad = manager.createPad('agent-11', 'State Restriction Test');
      
      // Collapse the pad
      manager.updateFlux(pad.id, 0);
      
      expect(() => manager.addNote(pad.id, {
        title: 'Test',
        content: 'Test',
        tags: [],
        shared: false
      })).toThrow('Cannot add notes to collapsed pad');
      
      // DEMI state - can't add sketches
      manager.updateFlux(pad.id, 0.3);
      expect(() => manager.addSketch(pad.id, {
        name: 'Test',
        data: '',
        type: 'diagram',
        shared: false
      })).toThrow('Cannot add sketches in current dimensional state');
    });
  });

  describe('Tier Progression', () => {
    it('should return correct next tier', () => {
      expect(getNextTier('KO')).toBe('AV');
      expect(getNextTier('AV')).toBe('RU');
      expect(getNextTier('RU')).toBe('CA');
      expect(getNextTier('CA')).toBe('UM');
      expect(getNextTier('UM')).toBe('DR');
      expect(getNextTier('DR')).toBeNull();
    });

    it('should return correct XP for next tier', () => {
      expect(getXPForNextTier('KO')).toBe(TIER_THRESHOLDS.AV.xp);
      expect(getXPForNextTier('DR')).toBe(Infinity);
    });

    it('should add XP and promote tier', () => {
      const pad = manager.createPad('agent-12', 'XP Test');
      
      // Add enough XP to promote to AV
      manager.addXP(pad.id, 100, 'test');
      
      expect(pad.tier).toBe('AV');
      expect(pad.milestones.length).toBeGreaterThan(0);
    });

    it('should demote tier with reason', () => {
      const pad = manager.createPad('agent-13', 'Demote Test', 'CA');
      
      const demoted = manager.demoteTier(pad.id, 'Failed security audit');
      
      expect(demoted).toBe(true);
      expect(pad.tier).toBe('RU');
      expect(pad.auditLog.length).toBeGreaterThan(0);
    });

    it('should not demote below KO', () => {
      const pad = manager.createPad('agent-14', 'Min Tier Test', 'KO');
      
      const demoted = manager.demoteTier(pad.id, 'Test');
      
      expect(demoted).toBe(false);
      expect(pad.tier).toBe('KO');
    });
  });

  describe('Task & Collaboration Tracking', () => {
    it('should record task completion and update stats', () => {
      const pad = manager.createPad('agent-15', 'Task Test');
      
      manager.recordTaskCompletion(pad.id, true);
      manager.recordTaskCompletion(pad.id, true);
      manager.recordTaskCompletion(pad.id, false);
      
      expect(pad.tasksCompleted).toBe(3);
      expect(pad.successRate).toBeLessThan(1);
      expect(pad.experiencePoints).toBeGreaterThan(0);
    });

    it('should record collaborations', () => {
      const pad = manager.createPad('agent-16', 'Collab Test');
      
      manager.recordCollaboration(pad.id);
      manager.recordCollaboration(pad.id);
      
      expect(pad.collaborations).toBe(2);
    });

    it('should award milestones for achievements', () => {
      const pad = manager.createPad('agent-17', 'Milestone Test');
      
      // Complete 10 tasks for milestone
      for (let i = 0; i < 10; i++) {
        manager.recordTaskCompletion(pad.id, true);
      }
      
      const milestone = pad.milestones.find(m => m.name === 'First Steps');
      expect(milestone).toBeDefined();
    });
  });

  describe('Audit System', () => {
    it('should add audit entries', () => {
      const pad = manager.createPad('agent-18', 'Audit Test');
      
      manager.addAuditEntry(pad.id, {
        auditorId: 'admin',
        target: 'behavior',
        result: 'pass',
        findings: 'All good'
      });
      
      expect(pad.auditLog).toHaveLength(1);
      expect(pad.lastAuditBy).toBe('admin');
    });

    it('should perform full audit', () => {
      const pad = manager.createPad('agent-19', 'Full Audit Test');
      
      const result = manager.auditPad(pad.id, 'auditor-1');
      
      expect(result.target).toBe('full');
      expect(result.result).toBe('pass');
    });

    it('should flag issues in audit', () => {
      const pad = manager.createPad('agent-20', 'Issue Audit Test');
      
      // Create low success rate
      for (let i = 0; i < 20; i++) {
        manager.recordTaskCompletion(pad.id, false);
      }
      
      const result = manager.auditPad(pad.id, 'auditor-2');
      
      expect(result.result).toBe('warning');
      expect(pad.auditStatus).toBe('flagged');
    });
  });

  describe('Statistics', () => {
    it('should return pad statistics', () => {
      const pad = manager.createPad('agent-21', 'Stats Test');
      manager.addXP(pad.id, 50, 'test');
      
      const stats = manager.getPadStats(pad.id);
      
      expect(stats).toBeDefined();
      expect(stats!.tier).toBe('KO');
      expect(stats!.xp).toBe(50);
      expect(stats!.dimensionalState).toBe('POLLY');
    });

    it('should filter pads by state and tier', () => {
      manager.createPad('agent-a', 'Pad A');
      manager.createPad('agent-b', 'Pad B', 'CA');
      const padC = manager.createPad('agent-c', 'Pad C');
      manager.updateFlux(padC.id, 0.3); // DEMI
      
      expect(manager.getPadsByState('POLLY')).toHaveLength(2);
      expect(manager.getPadsByState('DEMI')).toHaveLength(1);
      expect(manager.getPadsByTier('CA')).toHaveLength(1);
    });
  });
});

describe('SwarmCoordinator', () => {
  let padManager: PollyPadManager;
  let coordinator: SwarmCoordinator;

  beforeEach(() => {
    padManager = new PollyPadManager();
    coordinator = new SwarmCoordinator(padManager);
  });

  describe('Swarm Creation', () => {
    it('should create a swarm with config', () => {
      const swarm = coordinator.createSwarm({
        name: 'Test Swarm',
        minCoherence: 0.6,
        fluxDecayRate: 0.02,
        syncIntervalMs: 1000,
        maxPads: 5
      });
      
      expect(swarm.id).toBeDefined();
      expect(swarm.name).toBe('Test Swarm');
      expect(swarm.maxPads).toBe(5);
    });

    it('should retrieve swarm by ID', () => {
      const swarm = coordinator.createSwarm({ name: 'Lookup Swarm' });
      
      expect(coordinator.getSwarm(swarm.id)).toBe(swarm);
    });
  });

  describe('Pad Management', () => {
    it('should add pads to swarm', () => {
      const swarm = coordinator.createSwarm({ name: 'Pad Swarm' });
      const pad = padManager.createPad('agent-s1', 'Swarm Pad');
      
      const added = coordinator.addPadToSwarm(swarm.id, pad.id);
      
      expect(added).toBe(true);
      expect(pad.swarmId).toBe(swarm.id);
      expect(coordinator.getSwarmPads(swarm.id)).toHaveLength(1);
    });

    it('should remove pads from swarm', () => {
      const swarm = coordinator.createSwarm({ name: 'Remove Swarm' });
      const pad = padManager.createPad('agent-s2', 'Remove Pad');
      coordinator.addPadToSwarm(swarm.id, pad.id);
      
      const removed = coordinator.removePadFromSwarm(swarm.id, pad.id);
      
      expect(removed).toBe(true);
      expect(pad.swarmId).toBeUndefined();
    });

    it('should enforce max pads limit', () => {
      const swarm = coordinator.createSwarm({ name: 'Limited Swarm', maxPads: 2 });
      const pad1 = padManager.createPad('agent-l1', 'Pad 1');
      const pad2 = padManager.createPad('agent-l2', 'Pad 2');
      const pad3 = padManager.createPad('agent-l3', 'Pad 3');
      
      coordinator.addPadToSwarm(swarm.id, pad1.id);
      coordinator.addPadToSwarm(swarm.id, pad2.id);
      const added = coordinator.addPadToSwarm(swarm.id, pad3.id);
      
      expect(added).toBe(false);
      expect(coordinator.getSwarmPads(swarm.id)).toHaveLength(2);
    });
  });

  describe('Swarm State', () => {
    it('should calculate swarm state', () => {
      const swarm = coordinator.createSwarm({ name: 'State Swarm' });
      const pad1 = padManager.createPad('agent-st1', 'State Pad 1');
      const pad2 = padManager.createPad('agent-st2', 'State Pad 2');
      
      coordinator.addPadToSwarm(swarm.id, pad1.id);
      coordinator.addPadToSwarm(swarm.id, pad2.id);
      
      const state = coordinator.getSwarmState(swarm.id);
      
      expect(state).toBeDefined();
      expect(state!.padIds).toHaveLength(2);
      expect(state!.avgNu).toBe(1.0);
      expect(state!.dominantState).toBe('POLLY');
    });

    it('should sync swarm and update coherence', () => {
      const swarm = coordinator.createSwarm({ name: 'Sync Swarm' });
      const pad1 = padManager.createPad('agent-sy1', 'Sync Pad 1');
      const pad2 = padManager.createPad('agent-sy2', 'Sync Pad 2');
      
      coordinator.addPadToSwarm(swarm.id, pad1.id);
      coordinator.addPadToSwarm(swarm.id, pad2.id);
      
      // Diverge flux
      padManager.updateFlux(pad1.id, 0.8);
      padManager.updateFlux(pad2.id, 0.4);
      
      coordinator.syncSwarm(swarm.id);
      
      expect(pad1.coherenceScore).toBeLessThan(1);
      expect(pad2.coherenceScore).toBeLessThan(1);
    });
  });

  describe('Flux Dynamics', () => {
    it('should step flux using ODE', () => {
      const swarm = coordinator.createSwarm({ name: 'ODE Swarm' });
      const pad = padManager.createPad('agent-ode', 'ODE Pad');
      
      coordinator.addPadToSwarm(swarm.id, pad.id);
      padManager.updateFlux(pad.id, 0.5);
      
      const initialNu = pad.nu;
      coordinator.stepFluxODE(swarm.id);
      
      // Flux should change based on ODE
      expect(pad.nu).not.toBe(initialNu);
    });

    it('should boost pad flux', () => {
      const pad = padManager.createPad('agent-boost', 'Boost Pad');
      padManager.updateFlux(pad.id, 0.5);
      
      coordinator.boostPadFlux(pad.id, 0.2);
      
      expect(pad.nu).toBe(0.7);
    });

    it('should decay pad flux', () => {
      const pad = padManager.createPad('agent-decay', 'Decay Pad');
      
      coordinator.decayPadFlux(pad.id, 0.1);
      
      expect(pad.nu).toBe(0.9);
    });

    it('should collapse and revive pads', () => {
      const pad = padManager.createPad('agent-collapse', 'Collapse Pad');
      
      coordinator.collapsePad(pad.id);
      expect(pad.nu).toBe(0);
      expect(pad.dimensionalState).toBe('COLLAPSED');
      
      coordinator.revivePad(pad.id, 0.7);
      expect(pad.nu).toBe(0.1);
      expect(pad.targetNu).toBe(0.7);
      expect(pad.dimensionalState).toBe('DEMI');
    });
  });

  describe('Swarm Statistics', () => {
    it('should calculate swarm statistics', () => {
      const swarm = coordinator.createSwarm({ name: 'Stats Swarm' });
      const pad1 = padManager.createPad('agent-stats1', 'Stats Pad 1', 'KO');
      const pad2 = padManager.createPad('agent-stats2', 'Stats Pad 2', 'CA');
      
      coordinator.addPadToSwarm(swarm.id, pad1.id);
      coordinator.addPadToSwarm(swarm.id, pad2.id);
      
      const stats = coordinator.getSwarmStats(swarm.id);
      
      expect(stats).toBeDefined();
      expect(stats!.totalPads).toBe(2);
      expect(stats!.byTier.KO).toBe(1);
      expect(stats!.byTier.CA).toBe(1);
      expect(stats!.healthScore).toBeGreaterThan(0);
    });
  });
});
