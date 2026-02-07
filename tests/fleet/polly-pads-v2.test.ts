/**
 * Polly Pads v2 Tests — Mode Switching, Closed Network, Mission Coordinator
 *
 * Validates:
 * - ModeRegistry: 6 specialist modes with state persistence
 * - ClosedNetwork: Air-gapped messaging with HMAC integrity
 * - Squad: Byzantine fault-tolerant voting (4/6 quorum)
 * - MissionCoordinator: Crisis-driven mode reassignment
 */

import { describe, expect, it, beforeEach } from 'vitest';
import {
  ModeRegistry,
  ALL_MODE_IDS,
  type SpecialistModeId,
} from '../../src/fleet/polly-pads/specialist-modes';
import { ClosedNetwork } from '../../src/fleet/polly-pads/closed-network';
import {
  Squad,
  MissionCoordinator,
  BFT,
  type Vote,
} from '../../src/fleet/polly-pads/mission-coordinator';

// ═══════════════════════════════════════════════════════════════
// Mode Registry Tests
// ═══════════════════════════════════════════════════════════════

describe('ModeRegistry', () => {
  let registry: ModeRegistry;

  beforeEach(() => {
    registry = new ModeRegistry('pad-alpha');
  });

  it('should initialize all 6 specialist modes', () => {
    expect(registry.getAllModes()).toHaveLength(6);
    for (const id of ALL_MODE_IDS) {
      expect(registry.getMode(id)).toBeDefined();
    }
  });

  it('should start with no active mode', () => {
    expect(registry.currentModeId).toBeNull();
    expect(registry.currentMode).toBeNull();
  });

  it('should switch modes and track history', () => {
    const event = registry.switchMode('engineering', 'system startup');

    expect(registry.currentModeId).toBe('engineering');
    expect(event.fromMode).toBeNull();
    expect(event.toMode).toBe('engineering');
    expect(event.reason).toBe('system startup');
    expect(registry.switchCount).toBe(1);
  });

  it('should preserve state across mode switches', () => {
    registry.switchMode('science', 'normal ops');
    registry.saveData('samples', ['MARS-001', 'MARS-002']);
    registry.saveData('hypothesis', 'iron oxide formation');

    registry.switchMode('engineering', 'crisis');
    registry.saveData('repair_target', 'wheel_motor_2');

    // Switch back to science — state preserved
    registry.switchMode('science', 'crisis resolved');
    expect(registry.loadData<string[]>('samples')).toEqual(['MARS-001', 'MARS-002']);
    expect(registry.loadData<string>('hypothesis')).toBe('iron oxide formation');

    // Engineering state also preserved
    registry.switchMode('engineering', 'check repair');
    expect(registry.loadData<string>('repair_target')).toBe('wheel_motor_2');
  });

  it('should return available tools based on tier', () => {
    registry.switchMode('communications', 'test');

    // KO tier: only basic tools
    const koTools = registry.getAvailableTools('KO');
    expect(koTools.length).toBeGreaterThanOrEqual(1);
    expect(koTools.every((t) => t.minTier === 'KO')).toBe(true);

    // DR tier: all tools
    const drTools = registry.getAvailableTools('DR');
    expect(drTools.length).toBeGreaterThan(koTools.length);
  });

  it('should throw on unknown mode', () => {
    expect(() => registry.switchMode('warp_drive' as SpecialistModeId, 'test')).toThrow(
      'Unknown mode'
    );
  });

  it('should track full switch history', () => {
    registry.switchMode('science', 'start');
    registry.switchMode('engineering', 'crisis');
    registry.switchMode('mission_planning', 'planning');
    registry.switchMode('science', 'resolved');

    expect(registry.switchHistory).toHaveLength(4);
    expect(registry.switchHistory[0].toMode).toBe('science');
    expect(registry.switchHistory[1].toMode).toBe('engineering');
    expect(registry.switchHistory[2].toMode).toBe('mission_planning');
    expect(registry.switchHistory[3].toMode).toBe('science');
  });

  it('should serialize to JSON', () => {
    registry.switchMode('navigation', 'patrol');
    registry.saveData('route', [1, 2, 3]);

    const json = registry.toJSON() as Record<string, unknown>;
    expect(json).toHaveProperty('padId', 'pad-alpha');
    expect(json).toHaveProperty('currentMode', 'navigation');
    expect(json).toHaveProperty('modes');
    expect(json).toHaveProperty('switchHistory');
  });
});

// ═══════════════════════════════════════════════════════════════
// Closed Network Tests
// ═══════════════════════════════════════════════════════════════

describe('ClosedNetwork', () => {
  let network: ClosedNetwork;

  beforeEach(() => {
    network = new ClosedNetwork();
    network.registerPad('alpha');
    network.registerPad('beta');
    network.registerPad('gamma');
  });

  it('should send messages between pads on local mesh', () => {
    const msg = network.send('alpha', 'beta', 'local_squad_mesh', { type: 'hello' });
    expect(msg).not.toBeNull();
    expect(msg!.fromPadId).toBe('alpha');
    expect(msg!.toPadId).toBe('beta');
    expect(msg!.channel).toBe('local_squad_mesh');
  });

  it('should receive messages', () => {
    network.send('alpha', 'beta', 'local_squad_mesh', { data: 'test' });
    const messages = network.receive('beta');
    expect(messages).toHaveLength(1);
    expect(messages[0].payload).toEqual({ data: 'test' });
  });

  it('should broadcast to all other pads', () => {
    network.send('alpha', 'broadcast', 'local_squad_mesh', { alert: 'crisis' });

    const betaMessages = network.receive('beta');
    const gammaMessages = network.receive('gamma');
    const alphaMessages = network.receive('alpha');

    expect(betaMessages).toHaveLength(1);
    expect(gammaMessages).toHaveLength(1);
    expect(alphaMessages).toHaveLength(0); // sender doesn't receive own broadcast
  });

  it('should verify message integrity via HMAC', () => {
    const msg = network.send('alpha', 'beta', 'local_squad_mesh', { secure: true });
    expect(msg).not.toBeNull();
    expect(network.verifyMessage(msg!)).toBe(true);

    // Tamper with payload
    const tampered = { ...msg!, payload: { secure: false } };
    expect(network.verifyMessage(tampered)).toBe(false);
  });

  it('should reject messages from unregistered pads', () => {
    const msg = network.send('unknown', 'beta', 'local_squad_mesh', { hack: true });
    expect(msg).toBeNull();
  });

  it('should queue earth messages when contact unavailable', () => {
    network.setEarthContact(false);
    const msg = network.send('alpha', 'beta', 'earth_deep_space', { report: 'status' });

    // Message created but queued
    expect(msg).not.toBeNull();
    // Not delivered to beta
    expect(network.receive('beta')).toHaveLength(0);
    // Queued in alpha's outbound
    expect(network.getStatus('alpha').outboundQueueSize).toBe(1);
  });

  it('should deliver earth messages when contact restored', () => {
    network.setEarthContact(true);
    const msg = network.send('alpha', 'beta', 'earth_deep_space', { report: 'ok' });
    expect(msg).not.toBeNull();
    expect(network.receive('beta')).toHaveLength(1);
  });

  it('should track network statistics', () => {
    network.send('alpha', 'beta', 'local_squad_mesh', { a: 1 });
    network.send('alpha', 'gamma', 'local_squad_mesh', { a: 2 });
    network.send('beta', 'alpha', 'local_squad_mesh', { b: 1 });

    const alphaStatus = network.getStatus('alpha');
    expect(alphaStatus.totalSent).toBe(2);
    expect(alphaStatus.totalReceived).toBe(1);
  });

  it('should enable/disable channels', () => {
    network.setChannelEnabled('local_squad_mesh', false);
    const msg = network.send('alpha', 'beta', 'local_squad_mesh', { blocked: true });
    expect(msg).toBeNull();

    network.setChannelEnabled('local_squad_mesh', true);
    const msg2 = network.send('alpha', 'beta', 'local_squad_mesh', { unblocked: true });
    expect(msg2).not.toBeNull();
  });
});

// ═══════════════════════════════════════════════════════════════
// Squad & Byzantine Voting Tests
// ═══════════════════════════════════════════════════════════════

describe('Squad', () => {
  let squad: Squad;
  const padIds = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta'];

  beforeEach(() => {
    squad = new Squad('squad-1');
    for (const id of padIds) {
      squad.addMember(id);
    }
  });

  it('should create a 6-member squad', () => {
    expect(squad.getMembers()).toHaveLength(6);
    expect(squad.healthyCount).toBe(6);
    expect(squad.hasBftQuorum).toBe(true);
  });

  it('should enforce max squad size', () => {
    expect(() => squad.addMember('extra')).toThrow('full');
  });

  it('should assign modes to members', () => {
    squad.assignMode('alpha', 'engineering');
    squad.assignMode('beta', 'navigation');

    expect(squad.getAssignedMode('alpha')).toBe('engineering');
    expect(squad.getAssignedMode('beta')).toBe('navigation');
    expect(squad.getAssignedMode('gamma')).toBeNull();
  });

  describe('Byzantine Voting', () => {
    it('should approve with 4/6 votes on critical', () => {
      const session = squad.createVotingSession('deploy fix', 'alpha', 'critical');

      for (let i = 0; i < 4; i++) {
        squad.castVote(session.id, {
          padId: padIds[i],
          decision: 'APPROVE',
          confidence: 0.8,
          timestamp: Date.now(),
        });
      }

      const result = squad.checkConsensus(session.id);
      expect(result.approved).toBe(true);
      expect(result.approveCount).toBe(4);
      expect(result.quorumRequired).toBe(BFT.QUORUM.critical);
    });

    it('should reject when too many reject votes', () => {
      const session = squad.createVotingSession('risky action', 'alpha', 'critical');

      // 3 reject = more than 6 - 4 = 2 allowed rejections
      for (let i = 0; i < 3; i++) {
        squad.castVote(session.id, {
          padId: padIds[i],
          decision: 'REJECT',
          confidence: 0.9,
          timestamp: Date.now(),
        });
      }

      const result = squad.checkConsensus(session.id);
      expect(result.approved).toBe(false);
      expect(result.rejectCount).toBe(3);
      expect(squad.getSession(session.id)?.status).toBe('rejected');
    });

    it('should require 3/6 for routine', () => {
      const session = squad.createVotingSession('log data', 'alpha', 'routine');

      for (let i = 0; i < 3; i++) {
        squad.castVote(session.id, {
          padId: padIds[i],
          decision: 'APPROVE',
          confidence: 0.7,
          timestamp: Date.now(),
        });
      }

      const result = squad.checkConsensus(session.id);
      expect(result.approved).toBe(true);
      expect(result.quorumRequired).toBe(3);
    });

    it('should require 5/6 for destructive', () => {
      const session = squad.createVotingSession('abort mission', 'alpha', 'destructive');

      // 4 approvals — not enough
      for (let i = 0; i < 4; i++) {
        squad.castVote(session.id, {
          padId: padIds[i],
          decision: 'APPROVE',
          confidence: 0.9,
          timestamp: Date.now(),
        });
      }

      let result = squad.checkConsensus(session.id);
      expect(result.approved).toBe(false);

      // 5th approval — now it passes
      squad.castVote(session.id, {
        padId: padIds[4],
        decision: 'APPROVE',
        confidence: 0.8,
        timestamp: Date.now(),
      });

      result = squad.checkConsensus(session.id);
      expect(result.approved).toBe(true);
    });

    it('should prevent double-voting', () => {
      const session = squad.createVotingSession('test', 'alpha', 'routine');
      squad.castVote(session.id, {
        padId: 'alpha',
        decision: 'APPROVE',
        confidence: 1,
        timestamp: Date.now(),
      });

      expect(() =>
        squad.castVote(session.id, {
          padId: 'alpha',
          decision: 'REJECT',
          confidence: 1,
          timestamp: Date.now(),
        })
      ).toThrow('already voted');
    });

    it('should handle DEFER votes', () => {
      const session = squad.createVotingSession('wait for earth', 'alpha', 'critical');

      // 3 approve, 3 defer — not enough for quorum
      for (let i = 0; i < 3; i++) {
        squad.castVote(session.id, {
          padId: padIds[i],
          decision: 'APPROVE',
          confidence: 0.6,
          timestamp: Date.now(),
        });
      }
      for (let i = 3; i < 6; i++) {
        squad.castVote(session.id, {
          padId: padIds[i],
          decision: 'DEFER',
          confidence: 0.5,
          timestamp: Date.now(),
        });
      }

      const result = squad.checkConsensus(session.id);
      expect(result.approved).toBe(false);
      expect(result.deferCount).toBe(3);
    });
  });

  describe('Health Tracking', () => {
    it('should detect unhealthy members', () => {
      // Simulate stale heartbeat
      const member = squad.getMembers().find((m) => m.padId === 'alpha')!;
      member.lastHeartbeat = Date.now() - 120_000; // 2 minutes ago

      const unhealthy = squad.checkHealth(60_000);
      expect(unhealthy).toContain('alpha');
      expect(squad.healthyCount).toBe(5);
    });

    it('should reject votes from unhealthy members', () => {
      const member = squad.getMembers().find((m) => m.padId === 'alpha')!;
      member.healthy = false;

      const session = squad.createVotingSession('test', 'beta', 'routine');
      expect(() =>
        squad.castVote(session.id, {
          padId: 'alpha',
          decision: 'APPROVE',
          confidence: 1,
          timestamp: Date.now(),
        })
      ).toThrow('not a healthy');
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// Mission Coordinator Tests
// ═══════════════════════════════════════════════════════════════

describe('MissionCoordinator', () => {
  let coordinator: MissionCoordinator;
  let squad: Squad;
  const padIds = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta'];

  beforeEach(() => {
    coordinator = new MissionCoordinator();
    squad = new Squad('squad-1');
    for (const id of padIds) {
      squad.addMember(id);
    }
    coordinator.registerSquad(squad);
  });

  it('should assign default modes', () => {
    coordinator.assignDefaultModes('squad-1', 'science');

    for (const id of padIds) {
      expect(squad.getAssignedMode(id)).toBe('science');
    }
  });

  it('should generate crisis mode assignments', () => {
    const assignment = coordinator.getRecommendedAssignment('squad-1', 'equipment_failure');

    expect(assignment.size).toBe(6);
    // First pad should be engineering for equipment_failure
    expect(assignment.get('alpha')).toBe('engineering');
    expect(assignment.get('beta')).toBe('systems');
    expect(assignment.get('gamma')).toBe('mission_planning');
  });

  it('should generate novel_discovery assignments (3 science)', () => {
    const assignment = coordinator.getRecommendedAssignment('squad-1', 'novel_discovery');

    const modes = Array.from(assignment.values());
    const scienceCount = modes.filter((m) => m === 'science').length;
    expect(scienceCount).toBe(3);
  });

  it('should execute immediate crisis reassignment', () => {
    coordinator.assignDefaultModes('squad-1', 'science');

    const { assignment } = coordinator.executeCrisisReassignment(
      'squad-1',
      'equipment_failure',
      true // immediate
    );

    // Modes should be applied immediately
    expect(squad.getAssignedMode('alpha')).toBe('engineering');
    expect(squad.getAssignedMode('beta')).toBe('systems');
  });

  it('should create voting session for non-immediate crisis', () => {
    const { assignment, session } = coordinator.executeCrisisReassignment(
      'squad-1',
      'navigation_lost',
      false // requires vote
    );

    expect(session).toBeDefined();
    expect(session!.severity).toBe('critical');
    expect(session!.status).toBe('open');
    expect(assignment.size).toBe(6);

    // Modes not yet applied
    expect(squad.getAssignedMode('alpha')).toBeNull();
  });

  it('should apply assignment after vote approval', () => {
    const { assignment, session } = coordinator.executeCrisisReassignment(
      'squad-1',
      'power_emergency',
      false
    );

    // 4 approve → quorum met
    for (let i = 0; i < 4; i++) {
      squad.castVote(session!.id, {
        padId: padIds[i],
        decision: 'APPROVE',
        confidence: 0.8,
        timestamp: Date.now(),
      });
    }

    const result = squad.checkConsensus(session!.id);
    expect(result.approved).toBe(true);

    // Now apply
    coordinator.applyAssignment('squad-1', assignment);
    expect(squad.getAssignedMode('alpha')).toBe('systems');
    expect(squad.getAssignedMode('beta')).toBe('systems');
    expect(squad.getAssignedMode('gamma')).toBe('engineering');
  });

  it('should skip unhealthy members in assignment', () => {
    // Make alpha unhealthy
    const member = squad.getMembers().find((m) => m.padId === 'alpha')!;
    member.healthy = false;

    const assignment = coordinator.getRecommendedAssignment('squad-1', 'equipment_failure');

    // Alpha should not be assigned (unhealthy)
    expect(assignment.has('alpha')).toBe(false);
    expect(assignment.size).toBe(5);
  });
});

// ═══════════════════════════════════════════════════════════════
// Integration: Full Mars Scenario
// ═══════════════════════════════════════════════════════════════

describe('Mars Equipment Failure Scenario', () => {
  it('should handle a complete crisis cycle', () => {
    // Setup: 6 pads in science mode on closed network
    const network = new ClosedNetwork();
    const squad = new Squad('mars-squad');
    const coordinator = new MissionCoordinator();
    const padIds = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta'];
    const registries: Record<string, ModeRegistry> = {};

    for (const id of padIds) {
      squad.addMember(id);
      network.registerPad(id);
      registries[id] = new ModeRegistry(id);
      registries[id].switchMode('science', 'normal ops');
    }
    coordinator.registerSquad(squad);
    coordinator.assignDefaultModes('mars-squad', 'science');
    network.setEarthContact(false); // Behind Mars

    // Step 1: Equipment failure detected
    const { assignment, session } = coordinator.executeCrisisReassignment(
      'mars-squad',
      'equipment_failure',
      false
    );
    expect(session).toBeDefined();

    // Step 2: Broadcast crisis alert
    const alert = network.send('alpha', 'broadcast', 'local_squad_mesh', {
      type: 'crisis',
      crisisType: 'equipment_failure',
      sessionId: session!.id,
    });
    expect(alert).not.toBeNull();

    // Step 3: Squad votes (4 approve triggers consensus at critical quorum)
    for (let i = 0; i < 4; i++) {
      squad.castVote(session!.id, {
        padId: padIds[i],
        decision: 'APPROVE',
        confidence: 0.7 + i * 0.05,
        timestamp: Date.now(),
      });
    }

    // Step 4: Check consensus (4/6 approve = critical quorum met)
    const result = squad.checkConsensus(session!.id);
    expect(result.approved).toBe(true);
    expect(result.approveCount).toBe(4);

    // Step 5: Apply mode assignments
    coordinator.applyAssignment('mars-squad', assignment);
    for (const [padId, mode] of assignment) {
      registries[padId].switchMode(mode, `crisis: equipment_failure`);
    }

    // Step 6: Verify mode switches
    expect(registries['alpha'].currentModeId).toBe('engineering');
    expect(registries['beta'].currentModeId).toBe('systems');
    expect(registries['gamma'].currentModeId).toBe('mission_planning');

    // Step 7: Crisis resolved — switch back
    coordinator.assignDefaultModes('mars-squad', 'science');
    for (const id of padIds) {
      registries[id].switchMode('science', 'crisis resolved');
    }

    // Step 8: Earth contact restored
    network.setEarthContact(true);
    registries['gamma'].switchMode('communications', 'report to Earth');
    const report = network.send('gamma', 'broadcast', 'earth_deep_space', {
      type: 'crisis_report',
      status: 'resolved',
      crisisType: 'equipment_failure',
    });
    expect(report).not.toBeNull();

    // Verify full switch history
    expect(registries['alpha'].switchHistory).toHaveLength(3); // science → engineering → science
    expect(registries['gamma'].switchHistory).toHaveLength(4); // science → planning → science → comms
  });
});
