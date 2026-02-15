/**
 * @file polly-pad-runtime.unit.test.ts
 * @tier L2-unit
 * @axiom 2 (Locality), 5 (Composition)
 * @category unit
 *
 * Unit tests for Polly Pad Runtime: dual zones, squad space, proximity, tool gating.
 */

import { describe, it, expect } from 'vitest';
import {
  createUnitState,
  createPadRuntime,
  canPromoteToSafe,
  promotePad,
  demotePad,
  getAvailableTools,
  routeTask,
  unitDistance,
  SquadSpace,
  createUnitRuntime,
  padNamespaceKey,
  PAD_TOOL_MATRIX,
  type UnitState,
} from '../../src/fleet/polly-pad-runtime.js';
import { PAD_MODES } from '../../src/harmonic/scbe_voxel_types.js';

// ═══════════════════════════════════════════════════════════════
// UnitState Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: createUnitState', () => {
  it('should create a unit with default values', () => {
    const unit = createUnitState('u1');
    expect(unit.unitId).toBe('u1');
    expect(unit.x).toBe(0);
    expect(unit.coherence).toBe(1.0);
    expect(unit.dStar).toBe(0);
    expect(unit.hEff).toBe(0);
  });

  it('should accept position overrides', () => {
    const unit = createUnitState('u2', 5, 10, 15);
    expect(unit.x).toBe(5);
    expect(unit.y).toBe(10);
    expect(unit.z).toBe(15);
  });

  it('should accept partial overrides', () => {
    const unit = createUnitState('u3', 0, 0, 0, { coherence: 0.5, hEff: 200 });
    expect(unit.coherence).toBe(0.5);
    expect(unit.hEff).toBe(200);
  });
});

// ═══════════════════════════════════════════════════════════════
// Dual Zone Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: Pad Dual Zones', () => {
  it('should start in HOT zone', () => {
    const pad = createPadRuntime('u1', 'ENGINEERING');
    expect(pad.zone).toBe('HOT');
  });

  it('should have HOT tools initially', () => {
    const pad = createPadRuntime('u1', 'ENGINEERING');
    expect(pad.tools).toContain('plan_only');
    expect(pad.tools).not.toContain('deploy');
  });

  it('should promote to SAFE when conditions are met', () => {
    const pad = createPadRuntime('u1', 'ENGINEERING');
    const state = createUnitState('u1', 0, 0, 0, { coherence: 0.9, dStar: 0.2, hEff: 100 });
    const promoted = promotePad(pad, state);
    expect(promoted).not.toBeNull();
    expect(promoted!.zone).toBe('SAFE');
    expect(promoted!.tools).toContain('deploy');
  });

  it('should NOT promote when coherence is low', () => {
    const pad = createPadRuntime('u1', 'ENGINEERING');
    const state = createUnitState('u1', 0, 0, 0, { coherence: 0.1, dStar: 5.0, hEff: 1e7 });
    const promoted = promotePad(pad, state);
    expect(promoted).toBeNull();
  });

  it('should NOT promote when quorum insufficient', () => {
    const pad = createPadRuntime('u1', 'ENGINEERING');
    const state = createUnitState('u1', 0, 0, 0, { coherence: 0.9, dStar: 0.2, hEff: 100 });
    const promoted = promotePad(pad, state, 3);
    expect(promoted).toBeNull();
  });

  it('should promote with quorum of 4', () => {
    const pad = createPadRuntime('u1', 'ENGINEERING');
    const state = createUnitState('u1', 0, 0, 0, { coherence: 0.9, dStar: 0.2, hEff: 100 });
    const promoted = promotePad(pad, state, 4);
    expect(promoted).not.toBeNull();
  });

  it('should demote back to HOT', () => {
    const pad = createPadRuntime('u1', 'NAVIGATION');
    const state = createUnitState('u1', 0, 0, 0, { coherence: 0.9, dStar: 0.1, hEff: 10 });
    const promoted = promotePad(pad, state)!;
    const demoted = demotePad(promoted);
    expect(demoted.zone).toBe('HOT');
  });
});

// ═══════════════════════════════════════════════════════════════
// Tool Gating Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: Tool Gating', () => {
  it('all modes should have both zone tool sets', () => {
    for (const mode of PAD_MODES) {
      expect(PAD_TOOL_MATRIX[mode].SAFE.length).toBeGreaterThan(0);
      expect(PAD_TOOL_MATRIX[mode].HOT.length).toBeGreaterThan(0);
    }
  });

  it('HOT zone should always include plan_only', () => {
    for (const mode of PAD_MODES) {
      expect(PAD_TOOL_MATRIX[mode].HOT).toContain('plan_only');
    }
  });

  it('SAFE zone should NOT include plan_only', () => {
    for (const mode of PAD_MODES) {
      expect(PAD_TOOL_MATRIX[mode].SAFE).not.toContain('plan_only');
    }
  });

  it('ENGINEERING SAFE should have build and deploy', () => {
    expect(PAD_TOOL_MATRIX.ENGINEERING.SAFE).toContain('build');
    expect(PAD_TOOL_MATRIX.ENGINEERING.SAFE).toContain('deploy');
  });

  it('COMMS SAFE should have radio and encrypt', () => {
    expect(PAD_TOOL_MATRIX.COMMS.SAFE).toContain('radio');
    expect(PAD_TOOL_MATRIX.COMMS.SAFE).toContain('encrypt');
  });

  it('routeTask should return tools: prefixed string', () => {
    const pad = createPadRuntime('u1', 'NAVIGATION');
    const route = routeTask(pad);
    expect(route).toContain('tools:');
  });
});

// ═══════════════════════════════════════════════════════════════
// Squad Space Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: SquadSpace', () => {
  it('should start empty', () => {
    const squad = new SquadSpace('squad-1');
    expect(squad.size).toBe(0);
    expect(squad.getUnitIds()).toHaveLength(0);
  });

  it('should register units', () => {
    const squad = new SquadSpace('squad-1');
    squad.setUnit(createUnitState('u1', 0, 0, 0));
    squad.setUnit(createUnitState('u2', 5, 0, 0));
    expect(squad.size).toBe(2);
  });

  it('should remove units', () => {
    const squad = new SquadSpace('squad-1');
    squad.setUnit(createUnitState('u1'));
    squad.removeUnit('u1');
    expect(squad.size).toBe(0);
  });

  it('should compute correct neighbors within radius', () => {
    const squad = new SquadSpace('squad-1');
    squad.setUnit(createUnitState('a', 0, 0, 0));
    squad.setUnit(createUnitState('b', 1, 0, 0));
    squad.setUnit(createUnitState('c', 10, 0, 0));

    const nb = squad.neighbors(2.0);
    expect(nb.get('a')).toContain('b');
    expect(nb.get('b')).toContain('a');
    expect(nb.get('c')).toHaveLength(0);
  });

  it('should return empty neighbors for empty squad', () => {
    const squad = new SquadSpace('empty');
    const nb = squad.neighbors(5.0);
    expect(nb.size).toBe(0);
  });

  it('should find leader as unit with best score', () => {
    const squad = new SquadSpace('squad-1');
    squad.setUnit(createUnitState('a', 0, 0, 0, { coherence: 0.5, hEff: 100 }));
    squad.setUnit(createUnitState('b', 0, 0, 0, { coherence: 0.9, hEff: 10 }));
    expect(squad.findLeader()).toBe('b');
  });

  it('should compute average coherence', () => {
    const squad = new SquadSpace('squad-1');
    squad.setUnit(createUnitState('a', 0, 0, 0, { coherence: 0.6 }));
    squad.setUnit(createUnitState('b', 0, 0, 0, { coherence: 0.8 }));
    expect(squad.averageCoherence()).toBeCloseTo(0.7, 10);
  });

  it('should return 0 average coherence for empty squad', () => {
    const squad = new SquadSpace('empty');
    expect(squad.averageCoherence()).toBe(0);
  });

  it('should validate Byzantine quorum correctly', () => {
    const squad = new SquadSpace('q');
    expect(squad.quorumOk(4)).toBe(true);
    expect(squad.quorumOk(3)).toBe(false);
    expect(squad.quorumOk(6)).toBe(true);
  });

  it('should compute risk field per unit', () => {
    const squad = new SquadSpace('risk');
    squad.setUnit(createUnitState('safe', 0, 0, 0, { coherence: 0.9, dStar: 0.1, hEff: 10 }));
    squad.setUnit(
      createUnitState('danger', 0, 0, 0, { coherence: 0.1, dStar: 5.0, hEff: 1e7 })
    );
    const field = squad.riskField();
    expect(field.get('safe')).toBe('ALLOW');
    expect(field.get('danger')).toBe('DENY');
  });
});

// ═══════════════════════════════════════════════════════════════
// Unit Distance Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: unitDistance', () => {
  it('should be 0 for same position', () => {
    const a = createUnitState('a', 5, 5, 5);
    expect(unitDistance(a, a)).toBe(0);
  });

  it('should compute Euclidean distance', () => {
    const a = createUnitState('a', 0, 0, 0);
    const b = createUnitState('b', 3, 4, 0);
    expect(unitDistance(a, b)).toBeCloseTo(5, 10);
  });

  it('should be symmetric', () => {
    const a = createUnitState('a', 1, 2, 3);
    const b = createUnitState('b', 4, 6, 3);
    expect(unitDistance(a, b)).toBeCloseTo(unitDistance(b, a), 10);
  });
});

// ═══════════════════════════════════════════════════════════════
// Unit Runtime Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: createUnitRuntime', () => {
  it('should create a unit with 6 pads', () => {
    const runtime = createUnitRuntime('u1', 'squad-1');
    expect(runtime.pads.size).toBe(6);
    expect(runtime.squadId).toBe('squad-1');
  });

  it('should have all pad modes', () => {
    const runtime = createUnitRuntime('u1', 'squad-1');
    for (const mode of PAD_MODES) {
      expect(runtime.pads.has(mode)).toBe(true);
    }
  });

  it('should start all pads in HOT zone', () => {
    const runtime = createUnitRuntime('u1', 'squad-1');
    for (const pad of runtime.pads.values()) {
      expect(pad.zone).toBe('HOT');
    }
  });

  it('should accept custom position', () => {
    const runtime = createUnitRuntime('u1', 'squad-1', [10, 20, 30]);
    expect(runtime.state.x).toBe(10);
    expect(runtime.state.y).toBe(20);
    expect(runtime.state.z).toBe(30);
  });
});

// ═══════════════════════════════════════════════════════════════
// Namespace Key Tests
// ═══════════════════════════════════════════════════════════════

describe('L2-UNIT: padNamespaceKey', () => {
  it('should generate correct format', () => {
    expect(padNamespaceKey('u1', 'ENGINEERING', 'CA', 0)).toBe('u1:ENGINEERING:CA:0');
  });

  it('should be unique for different inputs', () => {
    const k1 = padNamespaceKey('u1', 'ENGINEERING', 'CA', 0);
    const k2 = padNamespaceKey('u1', 'NAVIGATION', 'AV', 0);
    const k3 = padNamespaceKey('u1', 'ENGINEERING', 'CA', 1);
    expect(k1).not.toBe(k2);
    expect(k1).not.toBe(k3);
  });
});
