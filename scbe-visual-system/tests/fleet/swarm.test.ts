/**
 * Fleet Module Tests
 *
 * Tests for SwarmCoordinator, PollyPadManager, and flux dynamics
 *
 * @module tests/fleet
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  createSwarmCoordinator,
  createTieredSwarm,
  DEFAULT_FLUX_CONFIG,
  DIMENSIONAL_THRESHOLDS,
  DimensionalState,
  getDimensionalState,
  getStateRange,
  GovernanceTier,
  governanceToDimensionIndex,
  dimensionToGovernanceTier,
  PollyPadManager,
  SwarmCoordinator,
  SwarmEvent,
} from '../../src/fleet';

describe('Dimensional State Utilities', () => {
  describe('getDimensionalState', () => {
    it('should return POLLY for high flux', () => {
      expect(getDimensionalState(0.95)).toBe('POLLY');
      expect(getDimensionalState(1.0)).toBe('POLLY');
    });

    it('should return QUASI for moderate-high flux', () => {
      expect(getDimensionalState(0.7)).toBe('QUASI');
      expect(getDimensionalState(0.5)).toBe('QUASI');
    });

    it('should return DEMI for low flux', () => {
      expect(getDimensionalState(0.3)).toBe('DEMI');
      expect(getDimensionalState(0.15)).toBe('DEMI');
    });

    it('should return COLLAPSED for minimal flux', () => {
      expect(getDimensionalState(0.05)).toBe('COLLAPSED');
      expect(getDimensionalState(0)).toBe('COLLAPSED');
    });

    it('should throw for invalid flux', () => {
      expect(() => getDimensionalState(-0.1)).toThrow();
      expect(() => getDimensionalState(1.1)).toThrow();
    });
  });

  describe('getStateRange', () => {
    it('should return correct ranges for each state', () => {
      expect(getStateRange('POLLY')).toEqual({
        min: DIMENSIONAL_THRESHOLDS.POLLY_MIN,
        max: 1.0,
      });
      expect(getStateRange('QUASI').min).toBe(DIMENSIONAL_THRESHOLDS.QUASI_MIN);
      expect(getStateRange('DEMI').min).toBe(DIMENSIONAL_THRESHOLDS.DEMI_MIN);
      expect(getStateRange('COLLAPSED').max).toBe(DIMENSIONAL_THRESHOLDS.DEMI_MIN);
    });
  });

  describe('governance tier mapping', () => {
    it('should map governance tiers to dimension indices', () => {
      expect(governanceToDimensionIndex('KO')).toBe(0);
      expect(governanceToDimensionIndex('AV')).toBe(1);
      expect(governanceToDimensionIndex('RU')).toBe(2);
      expect(governanceToDimensionIndex('CA')).toBe(3);
      expect(governanceToDimensionIndex('UM')).toBe(4);
      expect(governanceToDimensionIndex('DR')).toBe(5);
    });

    it('should map dimension indices to governance tiers', () => {
      expect(dimensionToGovernanceTier(0)).toBe('KO');
      expect(dimensionToGovernanceTier(5)).toBe('DR');
    });

    it('should throw for invalid dimension index', () => {
      expect(() => dimensionToGovernanceTier(-1)).toThrow();
      expect(() => dimensionToGovernanceTier(6)).toThrow();
    });
  });
});

describe('PollyPadManager', () => {
  let manager: PollyPadManager;

  beforeEach(() => {
    manager = new PollyPadManager();
  });

  describe('pad creation', () => {
    it('should create a pad with default config', () => {
      const pad = manager.createPad('Test Pad', 'KO');

      expect(pad.id).toBeDefined();
      expect(pad.name).toBe('Test Pad');
      expect(pad.governanceTier).toBe('KO');
      expect(pad.active).toBe(true);
      expect(pad.members.size).toBe(0);
    });

    it('should position pad at governance dimension vertex', () => {
      const padKO = manager.createPad('KO Pad', 'KO');
      const padDR = manager.createPad('DR Pad', 'DR');

      expect(padKO.config.position6D[0]).toBe(1.0);
      expect(padDR.config.position6D[5]).toBe(1.0);
    });

    it('should create pad with custom config', () => {
      const pad = manager.createPad('Custom Pad', 'CA', {
        capacity: 10,
        coherenceThreshold: 0.8,
      });

      expect(pad.config.capacity).toBe(10);
      expect(pad.config.coherenceThreshold).toBe(0.8);
    });
  });

  describe('member management', () => {
    it('should add member to pad', () => {
      const pad = manager.createPad('Test Pad', 'KO');
      const member = {
        id: 'member1',
        fluxCoefficient: 0.95,
        dimensionalState: 'POLLY' as DimensionalState,
        governanceTier: 'KO' as GovernanceTier,
        coherence: 0.9,
        lastUpdate: Date.now(),
      };

      const added = manager.addMember(pad.id, member);

      expect(added).toBe(true);
      expect(pad.members.has('member1')).toBe(true);
    });

    it('should reject member with low coherence', () => {
      const pad = manager.createPad('Test Pad', 'KO');
      const member = {
        id: 'member1',
        fluxCoefficient: 0.95,
        dimensionalState: 'POLLY' as DimensionalState,
        governanceTier: 'KO' as GovernanceTier,
        coherence: 0.5, // Below threshold
        lastUpdate: Date.now(),
      };

      const added = manager.addMember(pad.id, member);

      expect(added).toBe(false);
    });

    it('should reject member when pad is full', () => {
      const pad = manager.createPad('Small Pad', 'KO', { capacity: 1 });
      const member1 = {
        id: 'member1',
        fluxCoefficient: 0.95,
        dimensionalState: 'POLLY' as DimensionalState,
        governanceTier: 'KO' as GovernanceTier,
        coherence: 0.9,
        lastUpdate: Date.now(),
      };
      const member2 = {
        id: 'member2',
        fluxCoefficient: 0.95,
        dimensionalState: 'POLLY' as DimensionalState,
        governanceTier: 'KO' as GovernanceTier,
        coherence: 0.9,
        lastUpdate: Date.now(),
      };

      manager.addMember(pad.id, member1);
      const added = manager.addMember(pad.id, member2);

      expect(added).toBe(false);
    });

    it('should remove member from pad', () => {
      const pad = manager.createPad('Test Pad', 'KO');
      const member = {
        id: 'member1',
        fluxCoefficient: 0.95,
        dimensionalState: 'POLLY' as DimensionalState,
        governanceTier: 'KO' as GovernanceTier,
        coherence: 0.9,
        lastUpdate: Date.now(),
      };

      manager.addMember(pad.id, member);
      const removed = manager.removeMember(pad.id, 'member1');

      expect(removed).toBe(true);
      expect(pad.members.has('member1')).toBe(false);
    });
  });

  describe('flux and coherence boosts', () => {
    it('should calculate flux boost for member in pad', () => {
      const pad = manager.createPad('Test Pad', 'KO');
      const member = {
        id: 'member1',
        fluxCoefficient: 0.95,
        dimensionalState: 'POLLY' as DimensionalState,
        governanceTier: 'KO' as GovernanceTier,
        coherence: 0.9,
        lastUpdate: Date.now(),
      };

      manager.addMember(pad.id, member);
      const boost = manager.calculateFluxBoost('member1');

      expect(boost).toBeGreaterThan(0);
    });

    it('should return zero boost for member not in pad', () => {
      const boost = manager.calculateFluxBoost('nonexistent');
      expect(boost).toBe(0);
    });
  });

  describe('statistics', () => {
    it('should provide accurate statistics', () => {
      manager.createPad('KO Pad', 'KO');
      manager.createPad('CA Pad', 'CA');

      const stats = manager.getStatistics();

      expect(stats.totalPads).toBe(2);
      expect(stats.activePads).toBe(2);
      expect(stats.tierDistribution.KO).toBe(1);
      expect(stats.tierDistribution.CA).toBe(1);
    });
  });

  describe('events', () => {
    it('should emit events for pad operations', () => {
      const events: any[] = [];
      manager.onEvent((e) => events.push(e));

      const pad = manager.createPad('Test Pad', 'KO');
      const member = {
        id: 'member1',
        fluxCoefficient: 0.95,
        dimensionalState: 'POLLY' as DimensionalState,
        governanceTier: 'KO' as GovernanceTier,
        coherence: 0.9,
        lastUpdate: Date.now(),
      };
      manager.addMember(pad.id, member);

      expect(events.some((e) => e.type === 'pad_created')).toBe(true);
      expect(events.some((e) => e.type === 'member_joined')).toBe(true);
    });
  });
});

describe('SwarmCoordinator', () => {
  let coordinator: SwarmCoordinator;

  beforeEach(() => {
    coordinator = new SwarmCoordinator();
  });

  describe('member management', () => {
    it('should add member with initial flux', () => {
      const member = coordinator.addMember('agent1', 'KO', 0.95);

      expect(member.id).toBe('agent1');
      expect(member.fluxCoefficient).toBe(0.95);
      expect(member.dimensionalState).toBe('POLLY');
      expect(member.governanceTier).toBe('KO');
    });

    it('should add member with default position', () => {
      const member = coordinator.addMember('agent1', 'CA');

      expect(member.position6D).toBeDefined();
      expect(member.position6D![3]).toBe(0.5); // CA is index 3
    });

    it('should throw for invalid initial flux', () => {
      expect(() => coordinator.addMember('agent1', 'KO', 1.5)).toThrow();
      expect(() => coordinator.addMember('agent1', 'KO', -0.1)).toThrow();
    });

    it('should remove member', () => {
      coordinator.addMember('agent1', 'KO');
      const removed = coordinator.removeMember('agent1');

      expect(removed).toBe(true);
      expect(coordinator.getMember('agent1')).toBeUndefined();
    });

    it('should return false when removing nonexistent member', () => {
      const removed = coordinator.removeMember('nonexistent');
      expect(removed).toBe(false);
    });
  });

  describe('flux dynamics', () => {
    it('should set target flux', () => {
      coordinator.addMember('agent1', 'KO', 0.5);
      coordinator.setTargetFlux('agent1', 0.9);

      // Evolve and check movement toward target
      for (let i = 0; i < 50; i++) {
        coordinator.evolveFluxEuler('agent1');
      }

      const member = coordinator.getMember('agent1');
      expect(member!.fluxCoefficient).toBeGreaterThan(0.5);
    });

    it('should evolve flux using Euler method', () => {
      coordinator.addMember('agent1', 'KO', 0.5);
      coordinator.setTargetFlux('agent1', 0.95);

      const initialFlux = coordinator.getMember('agent1')!.fluxCoefficient;
      coordinator.evolveFluxEuler('agent1');
      const newFlux = coordinator.getMember('agent1')!.fluxCoefficient;

      expect(newFlux).not.toBe(initialFlux);
    });

    it('should evolve flux using RK4 method', () => {
      coordinator.addMember('agent1', 'KO', 0.5);
      coordinator.setTargetFlux('agent1', 0.95);

      const initialFlux = coordinator.getMember('agent1')!.fluxCoefficient;
      coordinator.evolveFluxRK4('agent1');
      const newFlux = coordinator.getMember('agent1')!.fluxCoefficient;

      expect(newFlux).not.toBe(initialFlux);
    });

    it('should keep flux bounded [0, 1]', () => {
      coordinator.addMember('agent1', 'KO', 0.01);
      coordinator.setTargetFlux('agent1', 0);

      for (let i = 0; i < 100; i++) {
        coordinator.evolveFluxEuler('agent1');
      }

      const member = coordinator.getMember('agent1');
      expect(member!.fluxCoefficient).toBeGreaterThanOrEqual(0);
      expect(member!.fluxCoefficient).toBeLessThanOrEqual(1);
    });
  });

  describe('coherence', () => {
    it('should update coherence', () => {
      coordinator.addMember('agent1', 'KO');
      coordinator.updateCoherence('agent1', 0.7);

      const member = coordinator.getMember('agent1');
      expect(member!.coherence).toBe(0.7);
    });

    it('should throw for invalid coherence', () => {
      coordinator.addMember('agent1', 'KO');
      expect(() => coordinator.updateCoherence('agent1', 1.5)).toThrow();
    });
  });

  describe('state transitions', () => {
    it('should emit state change event when crossing threshold', () => {
      const events: SwarmEvent[] = [];
      coordinator.onEvent((e) => events.push(e));

      coordinator.addMember('agent1', 'KO', 0.92); // POLLY
      coordinator.setTargetFlux('agent1', 0.4); // Will drop to QUASI

      for (let i = 0; i < 200; i++) {
        coordinator.evolveFluxEuler('agent1');
      }

      const stateChanges = events.filter((e) => e.type === 'state_change');
      expect(stateChanges.length).toBeGreaterThan(0);
    });
  });

  describe('bulk operations', () => {
    it('should evolve all members', () => {
      coordinator.addMember('agent1', 'KO', 0.5);
      coordinator.addMember('agent2', 'CA', 0.6);

      coordinator.setTargetFlux('agent1', 0.9);
      coordinator.setTargetFlux('agent2', 0.9);

      const initial1 = coordinator.getMember('agent1')!.fluxCoefficient;
      const initial2 = coordinator.getMember('agent2')!.fluxCoefficient;

      coordinator.evolveAll();

      expect(coordinator.getMember('agent1')!.fluxCoefficient).not.toBe(initial1);
      expect(coordinator.getMember('agent2')!.fluxCoefficient).not.toBe(initial2);
    });

    it('should get members by state', () => {
      coordinator.addMember('agent1', 'KO', 0.95);
      coordinator.addMember('agent2', 'CA', 0.7);
      coordinator.addMember('agent3', 'RU', 0.3);

      const pollyMembers = coordinator.getMembersByState('POLLY');
      const quasiMembers = coordinator.getMembersByState('QUASI');
      const demiMembers = coordinator.getMembersByState('DEMI');

      expect(pollyMembers).toHaveLength(1);
      expect(quasiMembers).toHaveLength(1);
      expect(demiMembers).toHaveLength(1);
    });

    it('should get members by tier', () => {
      coordinator.addMember('agent1', 'KO', 0.95);
      coordinator.addMember('agent2', 'KO', 0.7);
      coordinator.addMember('agent3', 'CA', 0.3);

      const koMembers = coordinator.getMembersByTier('KO');
      const caMembers = coordinator.getMembersByTier('CA');

      expect(koMembers).toHaveLength(2);
      expect(caMembers).toHaveLength(1);
    });
  });

  describe('statistics', () => {
    it('should provide accurate statistics', () => {
      coordinator.addMember('agent1', 'KO', 0.95);
      coordinator.addMember('agent2', 'CA', 0.7);

      const stats = coordinator.getStatistics();

      expect(stats.totalMembers).toBe(2);
      expect(stats.averageFlux).toBeCloseTo(0.825, 2);
      expect(stats.stateDistribution.POLLY).toBe(1);
      expect(stats.stateDistribution.QUASI).toBe(1);
      expect(stats.tierDistribution.KO).toBe(1);
      expect(stats.tierDistribution.CA).toBe(1);
    });
  });

  describe('simulation', () => {
    it('should start and stop simulation', () => {
      vi.useFakeTimers();

      coordinator.addMember('agent1', 'KO', 0.5);
      coordinator.setTargetFlux('agent1', 0.9);

      const initial = coordinator.getMember('agent1')!.fluxCoefficient;

      coordinator.startSimulation(100);
      vi.advanceTimersByTime(500);
      coordinator.stopSimulation();

      const final = coordinator.getMember('agent1')!.fluxCoefficient;
      expect(final).not.toBe(initial);

      vi.useRealTimers();
    });
  });
});

describe('Factory Functions', () => {
  it('should create swarm coordinator with factory', () => {
    const coordinator = createSwarmCoordinator();
    expect(coordinator).toBeInstanceOf(SwarmCoordinator);
  });

  it('should create tiered swarm with all governance pads', () => {
    const { coordinator, pads } = createTieredSwarm();

    expect(coordinator).toBeInstanceOf(SwarmCoordinator);
    expect(Object.keys(pads)).toHaveLength(6);
    expect(pads.KO).toBeDefined();
    expect(pads.DR).toBeDefined();
  });
});
