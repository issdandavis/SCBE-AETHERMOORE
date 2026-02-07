/**
 * Polly Pad Mode Switching, Closed Network, Squad, and Mission Coordinator Tests
 *
 * Tests for the personal AI workspace mode switching system designed for
 * autonomous operations (Mars missions, disaster response, submarine ops).
 *
 * @layer L13
 */

import { beforeEach, describe, expect, it } from 'vitest';
import { ModePad } from '../../src/fleet/polly-pads/mode-pad';
import {
  EngineeringMode,
  NavigationMode,
  SystemsMode,
  ScienceMode,
  CommunicationsMode,
  MissionPlanningMode,
  createMode,
  createAllModes,
} from '../../src/fleet/polly-pads/modes/index';
import { MODE_CONFIGS, SpecialistMode } from '../../src/fleet/polly-pads/modes/types';
import { ClosedNetwork } from '../../src/fleet/polly-pads/closed-network';
import { Squad } from '../../src/fleet/polly-pads/squad';
import { MissionCoordinator } from '../../src/fleet/polly-pads/mission-coordinator';

// ============================================================================
// Mode Switching Tests
// ============================================================================

describe('Specialist Modes', () => {
  describe('Mode Creation', () => {
    it('should create all 6 modes via factory', () => {
      const modes: SpecialistMode[] = [
        'engineering',
        'navigation',
        'systems',
        'science',
        'communications',
        'mission_planning',
      ];

      for (const modeName of modes) {
        const mode = createMode(modeName);
        expect(mode).toBeDefined();
        expect(mode.mode).toBe(modeName);
        expect(mode.active).toBe(false);
      }
    });

    it('should create all modes as a map', () => {
      const modes = createAllModes();
      expect(modes.size).toBe(6);
      expect(modes.has('engineering')).toBe(true);
      expect(modes.has('navigation')).toBe(true);
      expect(modes.has('systems')).toBe(true);
      expect(modes.has('science')).toBe(true);
      expect(modes.has('communications')).toBe(true);
      expect(modes.has('mission_planning')).toBe(true);
    });

    it('should have correct config for each mode', () => {
      const engineering = new EngineeringMode();
      expect(engineering.displayName).toBe('Engineering');
      expect(engineering.tools.length).toBeGreaterThan(0);
      expect(MODE_CONFIGS.engineering.category).toBe('tech');

      const science = new ScienceMode();
      expect(science.displayName).toBe('Science');
      expect(MODE_CONFIGS.science.category).toBe('non_tech');
    });
  });

  describe('Mode Activation/Deactivation', () => {
    it('should activate and deactivate', () => {
      const mode = new EngineeringMode();
      expect(mode.active).toBe(false);

      mode.activate();
      expect(mode.active).toBe(true);

      mode.deactivate();
      expect(mode.active).toBe(false);
    });

    it('should track activation count', () => {
      const mode = new ScienceMode();

      mode.activate();
      mode.deactivate();
      mode.activate();
      mode.deactivate();

      const state = mode.saveState();
      expect(state.activationCount).toBe(2);
    });

    it('should track cumulative time', () => {
      const mode = new NavigationMode();
      mode.activate();
      // Time passes (immediate deactivation gives ~0ms, but totalTimeMs includes it)
      mode.deactivate();

      const state = mode.saveState();
      expect(state.totalTimeMs).toBeGreaterThanOrEqual(0);
    });
  });

  describe('Mode Actions', () => {
    it('should reject actions when not active', () => {
      const mode = new EngineeringMode();
      const result = mode.executeAction('diagnose', { component: 'motor' });

      expect(result.success).toBe(false);
      expect(result.error).toContain('not active');
    });

    it('engineering: should diagnose and generate repair plan', () => {
      const mode = new EngineeringMode();
      mode.activate();

      const diagResult = mode.executeAction('diagnose', {
        component: 'wheel_motor_2',
        severity: 'degraded',
      });
      expect(diagResult.success).toBe(true);
      expect(diagResult.data.component).toBe('wheel_motor_2');

      const planResult = mode.executeAction('generate_repair_plan', {
        component: 'wheel_motor_2',
      });
      expect(planResult.success).toBe(true);
      expect(planResult.data.options).toBeDefined();
    });

    it('navigation: should plan route and detect obstacles', () => {
      const mode = new NavigationMode();
      mode.activate();

      const routeResult = mode.executeAction('plan_route', {
        destination: { x: 100, y: 0, z: 50 },
      });
      expect(routeResult.success).toBe(true);
      expect(routeResult.data.distance).toBeGreaterThan(0);

      const obstacleResult = mode.executeAction('detect_obstacles', { radius: 50 });
      expect(obstacleResult.success).toBe(true);
      expect(obstacleResult.data.obstacles).toBeDefined();
    });

    it('systems: should check power and sensor health', () => {
      const mode = new SystemsMode();
      mode.activate();

      const powerResult = mode.executeAction('check_power', {});
      expect(powerResult.success).toBe(true);
      expect(powerResult.data.totalWh).toBeDefined();
      expect(powerResult.data.reserveOk).toBe(true);

      const sensorResult = mode.executeAction('sensor_health', { sensorId: 'all' });
      expect(sensorResult.success).toBe(true);
      expect(sensorResult.data.sensors).toBeDefined();
    });

    it('science: should collect and analyze samples', () => {
      const mode = new ScienceMode();
      mode.activate();

      const collectResult = mode.executeAction('collect_sample', {
        location: 'crater_rim',
        type: 'soil',
      });
      expect(collectResult.success).toBe(true);
      expect(collectResult.data.id).toBeDefined();

      const sampleId = collectResult.data.id as string;
      const analyzeResult = mode.executeAction('analyze_sample', { sampleId });
      expect(analyzeResult.success).toBe(true);
      expect(analyzeResult.data.composition).toBeDefined();
    });

    it('communications: should queue messages and check Earth contact', () => {
      const mode = new CommunicationsMode();
      mode.activate();

      const queueResult = mode.executeAction('queue_message', {
        recipient: 'earth',
        content: 'Status report',
        priority: 'normal',
      });
      expect(queueResult.success).toBe(true);
      expect(queueResult.data.status).toBe('queued');

      const contactResult = mode.executeAction('check_earth_contact', {});
      expect(contactResult.success).toBe(true);
      expect(contactResult.data.available).toBeDefined();
    });

    it('mission_planning: should assess risk and validate decisions', () => {
      const mode = new MissionPlanningMode();
      mode.activate();

      const riskResult = mode.executeAction('assess_risk', {
        proposal: 'Continue on 5 wheels',
        likelihood: 0.3,
        impact: 0.6,
      });
      expect(riskResult.success).toBe(true);
      expect(riskResult.data.riskScore).toBeDefined();
      expect(riskResult.data.level).toBe('low');

      const validateResult = mode.executeAction('validate_decision', {
        decision: 'proceed',
        constraints: [],
      });
      expect(validateResult.success).toBe(true);
      expect(validateResult.data.valid).toBe(true);
    });

    it('should return error for unknown actions', () => {
      const mode = new EngineeringMode();
      mode.activate();

      const result = mode.executeAction('nonexistent_action', {});
      expect(result.success).toBe(false);
      expect(result.error).toContain('Unknown');
    });
  });

  describe('Mode State Persistence', () => {
    it('should save and restore state', () => {
      const mode = new ScienceMode();
      mode.activate();
      mode.executeAction('collect_sample', { location: 'test_site' });

      const savedState = mode.saveState();
      expect(savedState.mode).toBe('science');
      expect(savedState.activationCount).toBe(1);

      // Create new instance and restore
      const mode2 = new ScienceMode();
      mode2.loadState(savedState);

      const state2 = mode2.saveState();
      expect(state2.activationCount).toBe(1);
    });

    it('should maintain action history', () => {
      const mode = new EngineeringMode();
      mode.activate();

      mode.executeAction('diagnose', { component: 'a' });
      mode.executeAction('diagnose', { component: 'b' });
      mode.executeAction('check_parts', { component: 'c' });

      const history = mode.getActionHistory();
      expect(history).toHaveLength(3);
      expect(history[0].action).toBe('diagnose');
    });
  });
});

// ============================================================================
// ModePad Tests
// ============================================================================

describe('ModePad', () => {
  let pad: ModePad;

  beforeEach(() => {
    pad = new ModePad({ agentId: 'ALPHA-001', tongue: 'KO' });
  });

  describe('Initialization', () => {
    it('should create pad with correct identity', () => {
      expect(pad.agentId).toBe('ALPHA-001');
      expect(pad.tongue).toBe('KO');
      expect(pad.name).toBe('Pad-ALPHA-001');
      expect(pad.tier).toBe('KO');
      expect(pad.currentMode).toBeNull();
    });

    it('should create with default mode', () => {
      const sciPad = new ModePad({
        agentId: 'BETA-001',
        tongue: 'AV',
        defaultMode: 'science',
      });
      expect(sciPad.currentMode).toBe('science');
    });

    it('should have 6 available modes', () => {
      const modes = pad.getAvailableModes();
      expect(modes).toHaveLength(6);
    });
  });

  describe('Mode Switching', () => {
    it('should switch modes', () => {
      pad.switchMode('science', 'Normal operations');
      expect(pad.currentMode).toBe('science');

      pad.switchMode('engineering', 'Crisis response');
      expect(pad.currentMode).toBe('engineering');
    });

    it('should preserve state across switches', () => {
      pad.switchMode('science', 'Starting');
      pad.executeAction('collect_sample', { location: 'site_a' });

      pad.switchMode('engineering', 'Crisis');
      pad.executeAction('diagnose', { component: 'motor' });

      // Switch back to science — state should be preserved
      pad.switchMode('science', 'Resuming');
      const sciMode = pad.getMode('science');
      expect(sciMode).toBeDefined();
      const state = sciMode!.saveState();
      expect(state.activationCount).toBe(2); // Activated twice
    });

    it('should record switch history', () => {
      pad.switchMode('science', 'First');
      pad.switchMode('engineering', 'Crisis');
      pad.switchMode('science', 'Back');

      const history = pad.getSwitchHistory();
      expect(history).toHaveLength(3);
      expect(history[0].from).toBeNull();
      expect(history[0].to).toBe('science');
      expect(history[1].from).toBe('science');
      expect(history[1].to).toBe('engineering');
      expect(history[2].from).toBe('engineering');
      expect(history[2].to).toBe('science');
    });

    it('should throw on unknown mode', () => {
      expect(() => pad.switchMode('invalid' as SpecialistMode, 'test')).toThrow('Unknown mode');
    });
  });

  describe('Action Execution', () => {
    it('should execute actions in current mode', () => {
      pad.switchMode('engineering', 'Test');
      const result = pad.executeAction('diagnose', { component: 'test' });
      expect(result.success).toBe(true);
    });

    it('should fail if no mode active', () => {
      const result = pad.executeAction('diagnose', {});
      expect(result.success).toBe(false);
      expect(result.error).toContain('No mode is currently active');
    });
  });

  describe('Memory', () => {
    it('should store and search memory', () => {
      pad.switchMode('science', 'Test');
      pad.storeMemory('Found interesting mineral at crater rim', {
        type: 'observation',
      });
      pad.storeMemory('Soil sample collected from landing site', {
        type: 'sample',
      });

      const results = pad.searchMemory('crater');
      expect(results.length).toBeGreaterThanOrEqual(1);
      expect(results[0].content).toContain('crater');
    });

    it('should persist memory across mode switches', () => {
      pad.switchMode('science', 'Science');
      pad.storeMemory('Science observation');

      pad.switchMode('engineering', 'Engineering');
      pad.storeMemory('Engineering note');

      // Memory includes entries from both modes + switch events
      const recent = pad.getRecentMemory(10);
      expect(recent.length).toBeGreaterThanOrEqual(2);
    });

    it('should track memory count', () => {
      pad.switchMode('science', 'Test');
      const initialCount = pad.memoryCount;

      pad.storeMemory('New memory');
      expect(pad.memoryCount).toBe(initialCount + 1);
    });
  });

  describe('Squad Integration', () => {
    it('should join and leave squads', () => {
      expect(pad.squadId).toBeNull();

      pad.joinSquad('SQUAD-1');
      expect(pad.squadId).toBe('SQUAD-1');

      pad.leaveSquad();
      expect(pad.squadId).toBeNull();
    });
  });

  describe('Serialization', () => {
    it('should serialize and deserialize', () => {
      pad.switchMode('engineering', 'Test');
      pad.executeAction('diagnose', { component: 'motor' });
      pad.storeMemory('Test memory');
      pad.joinSquad('SQUAD-1');

      const json = pad.toJSON();
      const restored = ModePad.fromJSON(json);

      expect(restored.agentId).toBe('ALPHA-001');
      expect(restored.tongue).toBe('KO');
      expect(restored.currentMode).toBe('engineering');
      expect(restored.squadId).toBe('SQUAD-1');
    });
  });

  describe('Mode Statistics', () => {
    it('should track mode statistics', () => {
      pad.switchMode('science', 'First');
      pad.switchMode('engineering', 'Second');
      pad.switchMode('science', 'Third');

      const stats = pad.getModeStats();
      const sciStats = stats.find((s) => s.mode === 'science');
      const engStats = stats.find((s) => s.mode === 'engineering');

      expect(sciStats).toBeDefined();
      expect(sciStats!.activations).toBe(2);
      expect(engStats).toBeDefined();
      expect(engStats!.activations).toBe(1);
    });
  });
});

// ============================================================================
// Closed Network Tests
// ============================================================================

describe('ClosedNetwork', () => {
  let network: ClosedNetwork;

  beforeEach(() => {
    network = new ClosedNetwork();
  });

  describe('Channel Access', () => {
    it('should allow valid channels', () => {
      expect(network.canUseChannel('local_squad_mesh')).toBe(true);
      expect(network.canUseChannel('earth_deep_space')).toBe(true);
      expect(network.canUseChannel('onboard_sensors')).toBe(true);
      expect(network.canUseChannel('emergency_beacon')).toBe(true);
    });

    it('should block unauthorized channels', () => {
      expect(network.canUseChannel('internet')).toBe(false);
      expect(network.canUseChannel('external_apis')).toBe(false);
      expect(network.canUseChannel('social_media')).toBe(false);
      expect(network.canUseChannel('unauthorized_devices')).toBe(false);
    });

    it('should report channel status', () => {
      const status = network.getChannelStatus();
      expect(status).toHaveLength(4);

      const earthChannel = status.find((s) => s.channel === 'earth_deep_space');
      expect(earthChannel).toBeDefined();
      expect(earthChannel!.available).toBe(false); // Default: no contact
    });
  });

  describe('Pad Verification', () => {
    it('should register and verify pads', () => {
      expect(network.isPadVerified('ALPHA-001')).toBe(false);

      network.registerPad('ALPHA-001');
      expect(network.isPadVerified('ALPHA-001')).toBe(true);
    });

    it('should deregister pads', () => {
      network.registerPad('ALPHA-001');
      network.deregisterPad('ALPHA-001');
      expect(network.isPadVerified('ALPHA-001')).toBe(false);
    });

    it('should list verified pads', () => {
      network.registerPad('ALPHA-001');
      network.registerPad('BETA-001');

      const pads = network.getVerifiedPads();
      expect(pads).toHaveLength(2);
      expect(pads).toContain('ALPHA-001');
      expect(pads).toContain('BETA-001');
    });
  });

  describe('Messaging', () => {
    it('should send messages between verified pads', () => {
      network.registerPad('ALPHA-001');
      network.registerPad('BETA-001');

      const msg = network.sendMessage('ALPHA-001', 'BETA-001', 'local_squad_mesh', {
        type: 'hello',
      });
      expect(msg.delivered).toBe(true);
      expect(msg.error).toBeUndefined();
    });

    it('should reject messages from unverified senders', () => {
      network.registerPad('BETA-001');

      const msg = network.sendMessage('UNKNOWN', 'BETA-001', 'local_squad_mesh', {
        type: 'hello',
      });
      expect(msg.delivered).toBe(false);
      expect(msg.error).toContain('not a verified pad');
    });

    it('should reject messages to unverified recipients on mesh', () => {
      network.registerPad('ALPHA-001');

      const msg = network.sendMessage('ALPHA-001', 'UNKNOWN', 'local_squad_mesh', {
        type: 'hello',
      });
      expect(msg.delivered).toBe(false);
      expect(msg.error).toContain('not a verified pad');
    });

    it('should allow broadcast messages', () => {
      network.registerPad('ALPHA-001');

      const msg = network.broadcast('ALPHA-001', { type: 'alert' });
      expect(msg.delivered).toBe(true);
    });

    it('should queue Earth messages when no contact', () => {
      network.registerPad('ALPHA-001');

      const msg = network.sendMessage('ALPHA-001', 'earth', 'earth_deep_space', {
        type: 'report',
      });
      expect(msg.delivered).toBe(false);
      expect(msg.error).toContain('queued');

      expect(network.getEarthQueue()).toHaveLength(1);
    });

    it('should flush Earth queue when contact restored', () => {
      network.registerPad('ALPHA-001');
      network.sendMessage('ALPHA-001', 'earth', 'earth_deep_space', { type: 'report' });

      expect(network.getEarthQueue()).toHaveLength(1);

      network.setEarthContact(true, 12);
      expect(network.getEarthQueue()).toHaveLength(0);
    });
  });

  describe('Statistics', () => {
    it('should track network stats', () => {
      network.registerPad('ALPHA-001');
      network.registerPad('BETA-001');

      network.sendMessage('ALPHA-001', 'BETA-001', 'local_squad_mesh', { data: 1 });
      network.sendMessage('ALPHA-001', 'broadcast', 'local_squad_mesh', { data: 2 });

      const stats = network.getStats();
      expect(stats.verifiedPads).toBe(2);
      expect(stats.totalMessages).toBe(2);
      expect(stats.deliveredMessages).toBe(2);
      expect(stats.failedMessages).toBe(0);
    });
  });
});

// ============================================================================
// Squad (Byzantine Consensus) Tests
// ============================================================================

describe('Squad', () => {
  let squad: Squad;
  let pads: ModePad[];

  beforeEach(() => {
    squad = new Squad({ id: 'MARS-1', name: 'Mars Rover Squad' });
    pads = [
      new ModePad({ agentId: 'ALPHA-001', tongue: 'KO', defaultMode: 'science' }),
      new ModePad({ agentId: 'BETA-001', tongue: 'AV', defaultMode: 'science' }),
      new ModePad({ agentId: 'GAMMA-001', tongue: 'RU', defaultMode: 'science' }),
      new ModePad({ agentId: 'DELTA-001', tongue: 'CA', defaultMode: 'science' }),
      new ModePad({ agentId: 'EPSILON-001', tongue: 'UM', defaultMode: 'science' }),
      new ModePad({ agentId: 'ZETA-001', tongue: 'DR', defaultMode: 'science' }),
    ];
    for (const pad of pads) {
      squad.addPad(pad);
    }
  });

  describe('BFT Constraints', () => {
    it('should enforce n >= 3f + 1', () => {
      expect(() => new Squad({
        id: 'BAD',
        name: 'Bad Squad',
        maxPads: 3,
        maxFaulty: 1,
      })).toThrow('BFT constraint violated');
    });

    it('should allow valid configurations', () => {
      const validSquad = new Squad({
        id: 'GOOD',
        name: 'Good Squad',
        maxPads: 7,
        maxFaulty: 2,
        quorum: 5,
      });
      expect(validSquad.maxPads).toBe(7);
      expect(validSquad.quorum).toBe(5);
    });
  });

  describe('Pad Management', () => {
    it('should have 6 pads', () => {
      expect(squad.size).toBe(6);
    });

    it('should not exceed max pads', () => {
      const extraPad = new ModePad({ agentId: 'EXTRA', tongue: 'KO' });
      const added = squad.addPad(extraPad);
      expect(added).toBe(false);
      expect(squad.size).toBe(6);
    });

    it('should remove pads', () => {
      squad.removePad('ZETA-001');
      expect(squad.size).toBe(5);
      expect(squad.getPad('ZETA-001')).toBeUndefined();
    });

    it('should filter pads by mode', () => {
      const sciencePads = squad.getPadsByMode('science');
      expect(sciencePads).toHaveLength(6); // All start in science
    });
  });

  describe('Consensus', () => {
    it('should approve with quorum (4/6)', () => {
      const proposal = squad.propose('ALPHA-001', {
        description: 'Continue on 5 wheels',
        category: 'repair',
        data: { component: 'wheel_motor_2' },
      });

      squad.vote(proposal.id, 'ALPHA-001', 'APPROVE', 0.8);
      squad.vote(proposal.id, 'BETA-001', 'APPROVE', 0.7);
      squad.vote(proposal.id, 'GAMMA-001', 'APPROVE', 0.6);

      // Not decided yet (only 3/4)
      expect(squad.getProposal(proposal.id)!.decision).toBeNull();

      squad.vote(proposal.id, 'DELTA-001', 'APPROVE', 0.9);

      // Now decided: 4/6 = quorum met
      expect(squad.getProposal(proposal.id)!.decision).toBe('APPROVED');
    });

    it('should deny with majority denial', () => {
      const proposal = squad.propose('ALPHA-001', {
        description: 'Risky maneuver',
        category: 'navigation',
        data: {},
      });

      squad.vote(proposal.id, 'ALPHA-001', 'DENY', 0.8);
      squad.vote(proposal.id, 'BETA-001', 'DENY', 0.7);
      squad.vote(proposal.id, 'GAMMA-001', 'DENY', 0.6);

      // 3 denials is not > 3 (half of 6), need 4 to deny
      expect(squad.getProposal(proposal.id)!.decision).toBeNull();

      squad.vote(proposal.id, 'DELTA-001', 'DENY', 0.9);

      // 4 denials > 3 = majority denial
      expect(squad.getProposal(proposal.id)!.decision).toBe('DENIED');
    });

    it('should deny when all votes in but insufficient approvals', () => {
      const proposal = squad.propose('ALPHA-001', {
        description: 'Moderate risk action',
        category: 'action',
        data: {},
      });

      squad.vote(proposal.id, 'ALPHA-001', 'APPROVE', 0.8);
      squad.vote(proposal.id, 'BETA-001', 'APPROVE', 0.7);
      squad.vote(proposal.id, 'GAMMA-001', 'DENY', 0.6);
      squad.vote(proposal.id, 'DELTA-001', 'DENY', 0.5);
      squad.vote(proposal.id, 'EPSILON-001', 'DEFER', 0.4);
      squad.vote(proposal.id, 'ZETA-001', 'DEFER', 0.3);

      // All votes in: 2 approve (< quorum 4), 2 deny, 2 defer
      // Not enough approvals = denied
      expect(squad.getProposal(proposal.id)!.decision).toBe('DENIED');
    });

    it('should defer when deferrals are dominant', () => {
      const proposal = squad.propose('ALPHA-001', {
        description: 'Uncertain action',
        category: 'action',
        data: {},
      });

      squad.vote(proposal.id, 'ALPHA-001', 'APPROVE', 0.5);
      squad.vote(proposal.id, 'BETA-001', 'DENY', 0.5);
      squad.vote(proposal.id, 'GAMMA-001', 'DEFER', 0.5);
      squad.vote(proposal.id, 'DELTA-001', 'DEFER', 0.4);
      squad.vote(proposal.id, 'EPSILON-001', 'DEFER', 0.3);
      squad.vote(proposal.id, 'ZETA-001', 'DEFER', 0.2);

      // 1 approve, 1 deny, 4 defer — deferrals dominate
      expect(squad.getProposal(proposal.id)!.decision).toBe('DEFERRED');
    });

    it('should prevent duplicate votes', () => {
      const proposal = squad.propose('ALPHA-001', {
        description: 'Test',
        category: 'action',
        data: {},
      });

      squad.vote(proposal.id, 'ALPHA-001', 'APPROVE', 0.8);
      expect(() =>
        squad.vote(proposal.id, 'ALPHA-001', 'APPROVE', 0.9)
      ).toThrow('already voted');
    });

    it('should prevent votes from non-members', () => {
      const proposal = squad.propose('ALPHA-001', {
        description: 'Test',
        category: 'action',
        data: {},
      });

      expect(() =>
        squad.vote(proposal.id, 'OUTSIDER', 'APPROVE', 0.8)
      ).toThrow('not in this squad');
    });

    it('should prevent voting on decided proposals', () => {
      const proposal = squad.propose('ALPHA-001', {
        description: 'Test',
        category: 'action',
        data: {},
      });

      // Get 4 approvals
      squad.vote(proposal.id, 'ALPHA-001', 'APPROVE', 0.8);
      squad.vote(proposal.id, 'BETA-001', 'APPROVE', 0.7);
      squad.vote(proposal.id, 'GAMMA-001', 'APPROVE', 0.6);
      squad.vote(proposal.id, 'DELTA-001', 'APPROVE', 0.9);

      expect(() =>
        squad.vote(proposal.id, 'EPSILON-001', 'APPROVE', 0.5)
      ).toThrow('already decided');
    });
  });

  describe('Statistics', () => {
    it('should report squad statistics', () => {
      const proposal = squad.propose('ALPHA-001', {
        description: 'Test',
        category: 'action',
        data: {},
      });
      squad.vote(proposal.id, 'ALPHA-001', 'APPROVE', 0.8);
      squad.vote(proposal.id, 'BETA-001', 'APPROVE', 0.7);
      squad.vote(proposal.id, 'GAMMA-001', 'APPROVE', 0.6);
      squad.vote(proposal.id, 'DELTA-001', 'APPROVE', 0.9);

      const stats = squad.getStats();
      expect(stats.padCount).toBe(6);
      expect(stats.quorum).toBe(4);
      expect(stats.totalProposals).toBe(1);
      expect(stats.approved).toBe(1);
      expect(stats.modeDistribution.science).toBe(6);
    });
  });
});

// ============================================================================
// Mission Coordinator Tests
// ============================================================================

describe('MissionCoordinator', () => {
  let squad: Squad;
  let coordinator: MissionCoordinator;
  let pads: ModePad[];

  beforeEach(() => {
    squad = new Squad({ id: 'MARS-1', name: 'Mars Rover Squad' });
    pads = [
      new ModePad({ agentId: 'ALPHA', tongue: 'KO', defaultMode: 'science' }),
      new ModePad({ agentId: 'BETA', tongue: 'AV', defaultMode: 'science' }),
      new ModePad({ agentId: 'GAMMA', tongue: 'RU', defaultMode: 'science' }),
      new ModePad({ agentId: 'DELTA', tongue: 'CA', defaultMode: 'science' }),
      new ModePad({ agentId: 'EPSILON', tongue: 'UM', defaultMode: 'science' }),
      new ModePad({ agentId: 'ZETA', tongue: 'DR', defaultMode: 'science' }),
    ];
    for (const pad of pads) {
      squad.addPad(pad);
    }
    coordinator = new MissionCoordinator(squad);
  });

  describe('Phase Management', () => {
    it('should set science_ops phase', () => {
      const assignments = coordinator.setPhase('science_ops');
      expect(assignments).toHaveLength(6);
      expect(coordinator.currentPhase).toBe('science_ops');

      // Science-heavy assignment
      const sciencePads = assignments.filter((a) => a.mode === 'science');
      expect(sciencePads.length).toBe(4);
    });

    it('should set transit phase', () => {
      const assignments = coordinator.setPhase('transit');
      expect(coordinator.currentPhase).toBe('transit');

      const navPads = assignments.filter((a) => a.mode === 'navigation');
      expect(navPads.length).toBe(2);
    });

    it('should track phase history', () => {
      coordinator.setPhase('science_ops');
      coordinator.setPhase('transit');
      coordinator.setPhase('maintenance');

      const history = coordinator.getPhaseHistory();
      expect(history).toHaveLength(3);
    });
  });

  describe('Crisis Handling', () => {
    it('should handle equipment_failure crisis', () => {
      const assessment = coordinator.handleCrisis('equipment_failure', 0.7);

      expect(assessment.type).toBe('equipment_failure');
      expect(assessment.severity).toBe(0.7);
      expect(assessment.assignments).toHaveLength(6);
      expect(coordinator.currentPhase).toBe('crisis');
      expect(coordinator.activeCrisis).toBe(assessment);

      // Should have engineering-heavy assignment
      const engPads = assessment.assignments.filter((a) => a.mode === 'engineering');
      expect(engPads.length).toBeGreaterThanOrEqual(2);
    });

    it('should handle novel_discovery crisis', () => {
      const assessment = coordinator.handleCrisis('novel_discovery', 0.5);

      expect(assessment.type).toBe('novel_discovery');
      expect(assessment.requiresEarthContact).toBe(true);

      // Should have science-heavy assignment
      const sciPads = assessment.assignments.filter((a) => a.mode === 'science');
      expect(sciPads.length).toBe(3);
    });

    it('should handle navigation_lost crisis', () => {
      const assessment = coordinator.handleCrisis('navigation_lost', 0.8);

      const navPads = assessment.assignments.filter((a) => a.mode === 'navigation');
      expect(navPads.length).toBe(2);
    });

    it('should assess crisis without applying', () => {
      coordinator.setPhase('science_ops');

      const assessment = coordinator.assessCrisis('power_critical', 0.9);
      expect(assessment.type).toBe('power_critical');

      // Phase should NOT have changed
      expect(coordinator.currentPhase).toBe('science_ops');
      expect(coordinator.activeCrisis).toBeNull();
    });

    it('should resolve crisis and return to phase', () => {
      coordinator.handleCrisis('equipment_failure', 0.7);
      expect(coordinator.currentPhase).toBe('crisis');

      const assignments = coordinator.resolveCrisis('science_ops');
      expect(coordinator.currentPhase).toBe('science_ops');
      expect(coordinator.activeCrisis).toBeNull();
      expect(assignments).toHaveLength(6);
    });

    it('should track crisis history', () => {
      coordinator.handleCrisis('equipment_failure', 0.7);
      coordinator.resolveCrisis('science_ops');
      coordinator.handleCrisis('navigation_lost', 0.4);

      const history = coordinator.getCrisisHistory();
      expect(history).toHaveLength(2);
    });
  });

  describe('Mars Equipment Failure Scenario (from design doc)', () => {
    it('should replicate the full Mars crisis scenario', () => {
      // Morning: Normal science operations
      coordinator.setPhase('science_ops');
      for (const pad of pads) {
        expect(pad.currentMode).toBeDefined();
      }

      // Pad Alpha collects a sample
      pads[0].executeAction('collect_sample', { location: 'crater_rim' });

      // Crisis: Wheel motor fails (behind Mars, no Earth contact)
      const assessment = coordinator.handleCrisis('equipment_failure', 0.7);

      // Alpha should be in engineering mode
      expect(pads[0].currentMode).toBe('engineering');

      // Alpha generates repair plan
      const plan = pads[0].executeAction('generate_repair_plan', {
        component: 'wheel_motor_2',
      });
      expect(plan.success).toBe(true);

      // Gamma (mission_planning) assesses risk
      const gammaMode = pads[2].currentMode;
      expect(gammaMode).toBe('mission_planning');
      const risk = pads[2].executeAction('assess_risk', {
        proposal: 'Continue on 5 wheels',
        likelihood: 0.3,
        impact: 0.5,
      });
      expect(risk.success).toBe(true);

      // Squad votes on the repair decision
      const proposal = squad.propose('ALPHA', {
        description: 'Continue on 5 wheels',
        category: 'repair',
        data: { plan: plan.data },
      });

      squad.vote(proposal.id, 'ALPHA', 'APPROVE', 0.8);
      squad.vote(proposal.id, 'BETA', 'APPROVE', 0.7);
      squad.vote(proposal.id, 'GAMMA', 'APPROVE', 0.6);
      squad.vote(proposal.id, 'DELTA', 'DEFER', 0.5);
      squad.vote(proposal.id, 'EPSILON', 'APPROVE', 0.9);
      // 4 approvals: consensus reached!

      expect(squad.getProposal(proposal.id)!.decision).toBe('APPROVED');

      // Execute repair
      const repair = pads[0].executeAction('execute_repair', {
        optionId: 'option_a',
      });
      expect(repair.success).toBe(true);

      // Crisis resolved — return to science
      coordinator.resolveCrisis('science_ops');
      expect(coordinator.currentPhase).toBe('science_ops');

      // One pad switches to comms to report to Earth
      const commsPads = squad.getPadsByMode('communications');
      expect(commsPads.length).toBeGreaterThanOrEqual(1);
    });
  });
});
