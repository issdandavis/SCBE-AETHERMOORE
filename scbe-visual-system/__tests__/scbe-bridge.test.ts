import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  getDimensionalState,
  getTierFromXP,
  DIMENSIONAL_THRESHOLDS,
  TIER_THRESHOLDS,
  SCBEBridge,
  getSCBEBridge,
  type GovernanceTier,
  type DimensionalState,
  type PollyPad,
  type FleetAgent,
  type PadNote,
  type PadSketch,
  type PadTool
} from '../lib/scbe-bridge';

// ========== DIMENSIONAL STATE TESTS ==========

describe('getDimensionalState', () => {
  it('returns POLLY for nu >= 0.8', () => {
    expect(getDimensionalState(0.8)).toBe('POLLY');
    expect(getDimensionalState(0.9)).toBe('POLLY');
    expect(getDimensionalState(1.0)).toBe('POLLY');
  });

  it('returns QUASI for 0.5 <= nu < 0.8', () => {
    expect(getDimensionalState(0.5)).toBe('QUASI');
    expect(getDimensionalState(0.6)).toBe('QUASI');
    expect(getDimensionalState(0.79)).toBe('QUASI');
  });

  it('returns DEMI for 0.1 <= nu < 0.5', () => {
    expect(getDimensionalState(0.1)).toBe('DEMI');
    expect(getDimensionalState(0.3)).toBe('DEMI');
    expect(getDimensionalState(0.49)).toBe('DEMI');
  });

  it('returns COLLAPSED for nu < 0.1', () => {
    expect(getDimensionalState(0)).toBe('COLLAPSED');
    expect(getDimensionalState(0.05)).toBe('COLLAPSED');
    expect(getDimensionalState(0.09)).toBe('COLLAPSED');
  });

  it('handles edge cases at exact thresholds', () => {
    expect(getDimensionalState(DIMENSIONAL_THRESHOLDS.POLLY)).toBe('POLLY');
    expect(getDimensionalState(DIMENSIONAL_THRESHOLDS.QUASI)).toBe('QUASI');
    expect(getDimensionalState(DIMENSIONAL_THRESHOLDS.DEMI)).toBe('DEMI');
  });

  it('handles negative values', () => {
    expect(getDimensionalState(-0.5)).toBe('COLLAPSED');
    expect(getDimensionalState(-1)).toBe('COLLAPSED');
  });
});

// ========== TIER PROGRESSION TESTS ==========

describe('getTierFromXP', () => {
  it('returns KO for XP < 100', () => {
    expect(getTierFromXP(0)).toBe('KO');
    expect(getTierFromXP(50)).toBe('KO');
    expect(getTierFromXP(99)).toBe('KO');
  });

  it('returns AV for 100 <= XP < 500', () => {
    expect(getTierFromXP(100)).toBe('AV');
    expect(getTierFromXP(250)).toBe('AV');
    expect(getTierFromXP(499)).toBe('AV');
  });

  it('returns RU for 500 <= XP < 2000', () => {
    expect(getTierFromXP(500)).toBe('RU');
    expect(getTierFromXP(1000)).toBe('RU');
    expect(getTierFromXP(1999)).toBe('RU');
  });

  it('returns CA for 2000 <= XP < 10000', () => {
    expect(getTierFromXP(2000)).toBe('CA');
    expect(getTierFromXP(5000)).toBe('CA');
    expect(getTierFromXP(9999)).toBe('CA');
  });

  it('returns UM for 10000 <= XP < 50000', () => {
    expect(getTierFromXP(10000)).toBe('UM');
    expect(getTierFromXP(25000)).toBe('UM');
    expect(getTierFromXP(49999)).toBe('UM');
  });

  it('returns DR for XP >= 50000', () => {
    expect(getTierFromXP(50000)).toBe('DR');
    expect(getTierFromXP(100000)).toBe('DR');
    expect(getTierFromXP(1000000)).toBe('DR');
  });

  it('handles exact threshold values', () => {
    expect(getTierFromXP(TIER_THRESHOLDS.KO.minXP)).toBe('KO');
    expect(getTierFromXP(TIER_THRESHOLDS.AV.minXP)).toBe('AV');
    expect(getTierFromXP(TIER_THRESHOLDS.RU.minXP)).toBe('RU');
    expect(getTierFromXP(TIER_THRESHOLDS.CA.minXP)).toBe('CA');
    expect(getTierFromXP(TIER_THRESHOLDS.UM.minXP)).toBe('UM');
    expect(getTierFromXP(TIER_THRESHOLDS.DR.minXP)).toBe('DR');
  });

  it('handles negative XP', () => {
    expect(getTierFromXP(-100)).toBe('KO');
  });
});

// ========== TIER THRESHOLDS TESTS ==========

describe('TIER_THRESHOLDS', () => {
  it('contains all six governance tiers', () => {
    const tiers: GovernanceTier[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
    tiers.forEach(tier => {
      expect(TIER_THRESHOLDS[tier]).toBeDefined();
      expect(TIER_THRESHOLDS[tier].minXP).toBeTypeOf('number');
      expect(TIER_THRESHOLDS[tier].name).toBeTypeOf('string');
    });
  });

  it('has monotonically increasing XP thresholds', () => {
    const tiers: GovernanceTier[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
    for (let i = 1; i < tiers.length; i++) {
      expect(TIER_THRESHOLDS[tiers[i]].minXP).toBeGreaterThan(
        TIER_THRESHOLDS[tiers[i - 1]].minXP
      );
    }
  });

  it('has correct tier names', () => {
    expect(TIER_THRESHOLDS.KO.name).toBe('Kindergarten');
    expect(TIER_THRESHOLDS.AV.name).toBe('Elementary');
    expect(TIER_THRESHOLDS.RU.name).toBe('Middle School');
    expect(TIER_THRESHOLDS.CA.name).toBe('High School');
    expect(TIER_THRESHOLDS.UM.name).toBe('University');
    expect(TIER_THRESHOLDS.DR.name).toBe('Doctorate');
  });
});

// ========== DIMENSIONAL THRESHOLDS TESTS ==========

describe('DIMENSIONAL_THRESHOLDS', () => {
  it('has correct threshold values', () => {
    expect(DIMENSIONAL_THRESHOLDS.POLLY).toBe(0.8);
    expect(DIMENSIONAL_THRESHOLDS.QUASI).toBe(0.5);
    expect(DIMENSIONAL_THRESHOLDS.DEMI).toBe(0.1);
    expect(DIMENSIONAL_THRESHOLDS.COLLAPSED).toBe(0);
  });

  it('has monotonically decreasing thresholds', () => {
    expect(DIMENSIONAL_THRESHOLDS.POLLY).toBeGreaterThan(DIMENSIONAL_THRESHOLDS.QUASI);
    expect(DIMENSIONAL_THRESHOLDS.QUASI).toBeGreaterThan(DIMENSIONAL_THRESHOLDS.DEMI);
    expect(DIMENSIONAL_THRESHOLDS.DEMI).toBeGreaterThan(DIMENSIONAL_THRESHOLDS.COLLAPSED);
  });
});

// ========== SCBE BRIDGE CLASS TESTS ==========

describe('SCBEBridge', () => {
  let bridge: SCBEBridge;

  beforeEach(() => {
    // Create fresh instance for each test
    bridge = new SCBEBridge('test-swarm');
  });

  describe('constructor', () => {
    it('initializes with a swarm ID', () => {
      const status = bridge.getSwarmStatus();
      expect(status.swarmId).toBe('test-swarm');
    });

    it('initializes with a local agent', () => {
      const agents = bridge.getAllAgents();
      expect(agents.length).toBe(1);
      expect(agents[0].id).toBe('visual-computer-local');
      expect(agents[0].name).toBe('InkOS Visual Computer');
    });

    it('creates a Polly Pad for the local agent', () => {
      const pads = bridge.getAllPads();
      expect(pads.length).toBe(1);
      expect(pads[0].agentId).toBe('visual-computer-local');
    });

    it('uses default swarm ID if not provided', () => {
      const defaultBridge = new SCBEBridge();
      const status = defaultBridge.getSwarmStatus();
      expect(status.swarmId).toBe('visual-computer-swarm');
    });
  });

  describe('agent management', () => {
    it('getAllAgents returns all registered agents', () => {
      const agents = bridge.getAllAgents();
      expect(Array.isArray(agents)).toBe(true);
      expect(agents.length).toBeGreaterThan(0);
    });

    it('getAgent returns agent by ID', () => {
      const agent = bridge.getAgent('visual-computer-local');
      expect(agent).toBeDefined();
      expect(agent?.name).toBe('InkOS Visual Computer');
    });

    it('getAgent returns undefined for non-existent ID', () => {
      const agent = bridge.getAgent('non-existent-id');
      expect(agent).toBeUndefined();
    });

    it('registerAgent creates a new agent', () => {
      const agent = bridge.registerAgent('Test Agent', ['capability1', 'capability2']);

      expect(agent.name).toBe('Test Agent');
      expect(agent.capabilities).toEqual(['capability1', 'capability2']);
      expect(agent.status).toBe('online');
      expect(agent.tier).toBe('KO');
      expect(agent.pad).toBeDefined();
    });

    it('registerAgent generates unique IDs', () => {
      const agent1 = bridge.registerAgent('Agent 1', []);
      const agent2 = bridge.registerAgent('Agent 2', []);

      expect(agent1.id).not.toBe(agent2.id);
    });

    it('registered agent is retrievable', () => {
      const agent = bridge.registerAgent('Retrievable Agent', []);
      const retrieved = bridge.getAgent(agent.id);

      expect(retrieved).toBeDefined();
      expect(retrieved?.name).toBe('Retrievable Agent');
    });
  });

  describe('pad management', () => {
    it('getAllPads returns all pads', () => {
      const pads = bridge.getAllPads();
      expect(Array.isArray(pads)).toBe(true);
    });

    it('getPadByAgent returns pad for existing agent', () => {
      const pad = bridge.getPadByAgent('visual-computer-local');
      expect(pad).toBeDefined();
      expect(pad?.agentId).toBe('visual-computer-local');
    });

    it('getPadByAgent returns undefined for non-existent agent', () => {
      const pad = bridge.getPadByAgent('non-existent');
      expect(pad).toBeUndefined();
    });

    it('createPad creates a new pad', () => {
      const pad = bridge.createPad('test-agent', 'Test Name');

      expect(pad.agentId).toBe('test-agent');
      expect(pad.name).toBe("Test Name's Pad");
      expect(pad.nu).toBe(0.5);
      expect(pad.dimensionalState).toBe('QUASI');
      expect(pad.tier).toBe('KO');
      expect(pad.xp).toBe(0);
    });
  });

  describe('note management', () => {
    it('addNote adds a note to existing pad', () => {
      const pads = bridge.getAllPads();
      const padId = pads[0].id;

      const note = bridge.addNote(padId, 'Test Title', 'Test Content', ['tag1', 'tag2']);

      expect(note).toBeDefined();
      expect(note?.title).toBe('Test Title');
      expect(note?.content).toBe('Test Content');
      expect(note?.tags).toEqual(['tag1', 'tag2']);
    });

    it('addNote returns undefined for non-existent pad', () => {
      const note = bridge.addNote('non-existent-pad', 'Title', 'Content');
      expect(note).toBeUndefined();
    });

    it('addNote adds XP to pad', () => {
      const pads = bridge.getAllPads();
      const padId = pads[0].id;
      const initialXP = pads[0].xp;

      bridge.addNote(padId, 'Title', 'Content');

      const updatedPad = bridge.getAllPads().find(p => p.id === padId);
      expect(updatedPad?.xp).toBe(initialXP + 10);
    });

    it('addNote updates pad timestamp', () => {
      const pads = bridge.getAllPads();
      const padId = pads[0].id;
      const initialUpdate = pads[0].updatedAt;

      // Small delay to ensure timestamp difference
      vi.useFakeTimers();
      vi.advanceTimersByTime(1000);

      bridge.addNote(padId, 'Title', 'Content');

      const updatedPad = bridge.getAllPads().find(p => p.id === padId);
      expect(updatedPad?.updatedAt.getTime()).toBeGreaterThanOrEqual(initialUpdate.getTime());

      vi.useRealTimers();
    });
  });

  describe('sketch management', () => {
    it('addSketch adds a sketch to existing pad', () => {
      const pads = bridge.getAllPads();
      const padId = pads[0].id;

      const sketch = bridge.addSketch(padId, 'Test Sketch', 'svg-data', 'diagram');

      expect(sketch).toBeDefined();
      expect(sketch?.name).toBe('Test Sketch');
      expect(sketch?.data).toBe('svg-data');
      expect(sketch?.sketchType).toBe('diagram');
    });

    it('addSketch defaults to freeform type', () => {
      const pads = bridge.getAllPads();
      const padId = pads[0].id;

      const sketch = bridge.addSketch(padId, 'Sketch', 'data');

      expect(sketch?.sketchType).toBe('freeform');
    });

    it('addSketch returns undefined for non-existent pad', () => {
      const sketch = bridge.addSketch('non-existent', 'Name', 'Data');
      expect(sketch).toBeUndefined();
    });

    it('addSketch adds 15 XP', () => {
      const pads = bridge.getAllPads();
      const padId = pads[0].id;
      const initialXP = pads[0].xp;

      bridge.addSketch(padId, 'Sketch', 'data');

      const updatedPad = bridge.getAllPads().find(p => p.id === padId);
      expect(updatedPad?.xp).toBe(initialXP + 15);
    });
  });

  describe('tool management', () => {
    it('addTool adds a tool to existing pad', () => {
      const pads = bridge.getAllPads();
      const padId = pads[0].id;

      const tool = bridge.addTool(padId, 'Test Tool', 'Description', 'script', 'console.log("hello")');

      expect(tool).toBeDefined();
      expect(tool?.name).toBe('Test Tool');
      expect(tool?.description).toBe('Description');
      expect(tool?.toolType).toBe('script');
      expect(tool?.content).toBe('console.log("hello")');
      expect(tool?.enabled).toBe(true);
    });

    it('addTool returns undefined for non-existent pad', () => {
      const tool = bridge.addTool('non-existent', 'Tool', 'Desc', 'script', 'code');
      expect(tool).toBeUndefined();
    });

    it('addTool adds 25 XP', () => {
      const pads = bridge.getAllPads();
      const padId = pads[0].id;
      const initialXP = pads[0].xp;

      bridge.addTool(padId, 'Tool', 'Desc', 'template', 'content');

      const updatedPad = bridge.getAllPads().find(p => p.id === padId);
      expect(updatedPad?.xp).toBe(initialXP + 25);
    });
  });

  describe('XP and tier progression', () => {
    it('addXP increases pad XP', () => {
      const pads = bridge.getAllPads();
      const padId = pads[0].id;
      const initialXP = pads[0].xp;

      bridge.addXP(padId, 100);

      const updatedPad = bridge.getAllPads().find(p => p.id === padId);
      expect(updatedPad?.xp).toBe(initialXP + 100);
    });

    it('addXP triggers tier upgrade when threshold reached', () => {
      const pad = bridge.createPad('xp-test-agent', 'XP Test');
      expect(pad.tier).toBe('KO');
      expect(pad.xp).toBe(0);

      bridge.addXP(pad.id, 100);
      const updatedPad = bridge.getAllPads().find(p => p.id === pad.id);
      expect(updatedPad?.tier).toBe('AV');
    });

    it('addXP updates level on tier change', () => {
      const pad = bridge.createPad('level-test-agent', 'Level Test');
      expect(pad.level).toBe(1);

      bridge.addXP(pad.id, 500);
      const updatedPad = bridge.getAllPads().find(p => p.id === pad.id);
      expect(updatedPad?.level).toBe(3); // RU is index 2 + 1 = 3
    });

    it('addXP does nothing for non-existent pad', () => {
      // Should not throw
      expect(() => bridge.addXP('non-existent', 100)).not.toThrow();
    });
  });

  describe('dimensional flux', () => {
    it('updateFlux moves nu toward target gradually', () => {
      const pad = bridge.createPad('flux-agent', 'Flux Test');
      expect(pad.nu).toBe(0.5);

      bridge.updateFlux(pad.id, 1.0);

      const updatedPad = bridge.getAllPads().find(p => p.id === pad.id);
      expect(updatedPad?.nu).toBeGreaterThan(0.5);
      expect(updatedPad?.nu).toBeLessThan(1.0);
    });

    it('updateFlux clamps nu between 0 and 1', () => {
      const pad = bridge.createPad('clamp-agent', 'Clamp Test');

      // Try to go above 1
      for (let i = 0; i < 100; i++) {
        bridge.updateFlux(pad.id, 2.0);
      }
      let updatedPad = bridge.getAllPads().find(p => p.id === pad.id);
      expect(updatedPad?.nu).toBeLessThanOrEqual(1);

      // Try to go below 0
      for (let i = 0; i < 100; i++) {
        bridge.updateFlux(pad.id, -1.0);
      }
      updatedPad = bridge.getAllPads().find(p => p.id === pad.id);
      expect(updatedPad?.nu).toBeGreaterThanOrEqual(0);
    });

    it('updateFlux updates dimensional state', () => {
      const pad = bridge.createPad('state-agent', 'State Test');
      expect(pad.dimensionalState).toBe('QUASI'); // nu = 0.5

      // Push nu toward POLLY state
      for (let i = 0; i < 50; i++) {
        bridge.updateFlux(pad.id, 1.0);
      }

      const updatedPad = bridge.getAllPads().find(p => p.id === pad.id);
      expect(updatedPad?.dimensionalState).toBe('POLLY');
    });

    it('updateFlux does nothing for non-existent pad', () => {
      expect(() => bridge.updateFlux('non-existent', 0.8)).not.toThrow();
    });
  });

  describe('security verification', () => {
    it('verifyAction returns valid for authorized tier', () => {
      const result = bridge.verifyAction('test-action', 'KO');

      expect(result.valid).toBe(true);
      expect(result.tier).toBe('KO');
      expect(result.presentSignatures.length).toBeGreaterThan(0);
    });

    it('verifyAction returns invalid when no agents meet tier', () => {
      // Local agent is AV tier, so DR should fail
      const result = bridge.verifyAction('high-security-action', 'DR');

      expect(result.valid).toBe(false);
      expect(result.tier).toBe('DR');
    });

    it('verifyAction includes timestamp', () => {
      const result = bridge.verifyAction('action', 'KO');

      expect(result.timestamp).toBeInstanceOf(Date);
    });

    it('verifyAction lists required signatures', () => {
      const result = bridge.verifyAction('action', 'RU');

      expect(result.requiredSignatures).toContain('RU');
    });
  });

  describe('action classification', () => {
    it('classifies critical actions as DR tier', () => {
      expect(bridge.classifyAction('deploy_production')).toBe('DR');
      expect(bridge.classifyAction('delete_all_data')).toBe('DR');
      expect(bridge.classifyAction('rotate_key_now')).toBe('DR');
      expect(bridge.classifyAction('grant_access_admin')).toBe('DR');
    });

    it('classifies high actions as UM tier', () => {
      expect(bridge.classifyAction('modify_state_active')).toBe('UM');
      expect(bridge.classifyAction('execute_command_ls')).toBe('UM');
      expect(bridge.classifyAction('send_signal_restart')).toBe('UM');
    });

    it('classifies medium actions as CA tier', () => {
      expect(bridge.classifyAction('query_state_health')).toBe('CA');
      expect(bridge.classifyAction('log_event_login')).toBe('CA');
      expect(bridge.classifyAction('update_metadata_tags')).toBe('CA');
    });

    it('classifies low actions as AV tier', () => {
      expect(bridge.classifyAction('read_file')).toBe('AV');
      expect(bridge.classifyAction('view_dashboard')).toBe('AV');
      expect(bridge.classifyAction('list_items')).toBe('AV');
    });

    it('classifies unknown actions as KO tier', () => {
      expect(bridge.classifyAction('unknown_action')).toBe('KO');
      expect(bridge.classifyAction('')).toBe('KO');
    });
  });

  describe('swarm status', () => {
    it('returns correct swarm ID', () => {
      const status = bridge.getSwarmStatus();
      expect(status.swarmId).toBe('test-swarm');
    });

    it('counts total agents', () => {
      const initialStatus = bridge.getSwarmStatus();
      const initialCount = initialStatus.totalAgents;

      bridge.registerAgent('New Agent', []);

      const newStatus = bridge.getSwarmStatus();
      expect(newStatus.totalAgents).toBe(initialCount + 1);
    });

    it('counts online agents', () => {
      const status = bridge.getSwarmStatus();
      expect(status.onlineAgents).toBeGreaterThan(0);
    });

    it('calculates average coherence', () => {
      const status = bridge.getSwarmStatus();
      expect(status.avgCoherence).toBeGreaterThanOrEqual(0);
      expect(status.avgCoherence).toBeLessThanOrEqual(1);
    });

    it('calculates average nu', () => {
      const status = bridge.getSwarmStatus();
      expect(status.avgNu).toBeGreaterThanOrEqual(0);
      expect(status.avgNu).toBeLessThanOrEqual(1);
    });
  });
});

// ========== SINGLETON TESTS ==========

describe('getSCBEBridge', () => {
  it('returns an instance of SCBEBridge', () => {
    const bridge = getSCBEBridge();
    expect(bridge).toBeInstanceOf(SCBEBridge);
  });

  it('returns the same instance on multiple calls', () => {
    const bridge1 = getSCBEBridge();
    const bridge2 = getSCBEBridge();
    expect(bridge1).toBe(bridge2);
  });
});
