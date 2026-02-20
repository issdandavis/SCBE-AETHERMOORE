/**
 * @file oscillator-bus.test.ts
 * @module tests/fleet/oscillator-bus
 * @layer L9, L10, L14
 * @component OscillatorBus — Kuramoto Phase-Coupled Mode Bus Tests
 * @version 3.2.4
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  OscillatorBus,
  classifyFrequency,
  normalizePhase,
  phaseDist,
  MODE_BANDS,
} from '../../src/fleet/oscillator-bus.js';
import type { OscillatorState, BusSnapshot, SwarmMode } from '../../src/fleet/oscillator-bus.js';
import type { Vec } from '../../src/fleet/swarm-geometry.js';

// ──────────────── Helpers ────────────────

const TWO_PI = 2 * Math.PI;

/** Create a position vector at origin or at given coordinates. */
function pos(x = 0, y = 0, z = 0): Vec {
  return { x, y, z };
}

/**
 * Add multiple nodes to a bus with deterministic phases and positions
 * all within coupling radius of each other.
 */
function addClusteredNodes(
  bus: OscillatorBus,
  count: number,
  options: {
    frequency?: number;
    trust?: number;
    phase?: number;
    phaseSpread?: number;
  } = {},
): string[] {
  const { frequency = 3.5, trust = 1.0, phase = 0, phaseSpread = 0 } = options;
  const ids: string[] = [];
  for (let i = 0; i < count; i++) {
    const id = `node-${i}`;
    const nodePhase = phase + i * phaseSpread;
    // Place nodes close together (within default couplingRadius of 15)
    bus.addNode(id, pos(i * 0.5, 0, 0), trust, frequency, nodePhase);
    ids.push(id);
  }
  return ids;
}

// ──────────────── Tests ────────────────

describe('classifyFrequency', () => {
  it('classifies 1.0 Hz as REGROUP', () => {
    expect(classifyFrequency(1.0)).toBe('REGROUP');
  });

  it('classifies 3.5 Hz as EXPLORE', () => {
    expect(classifyFrequency(3.5)).toBe('EXPLORE');
  });

  it('classifies 7.5 Hz as COMMIT', () => {
    expect(classifyFrequency(7.5)).toBe('COMMIT');
  });

  it('classifies 15.0 Hz as HAZARD', () => {
    expect(classifyFrequency(15.0)).toBe('HAZARD');
  });

  it('classifies 0.0 Hz as REGROUP (lowest band)', () => {
    expect(classifyFrequency(0.0)).toBe('REGROUP');
  });
});

describe('normalizePhase', () => {
  it('leaves an already-normalized phase unchanged', () => {
    const phase = 1.5;
    expect(normalizePhase(phase)).toBeCloseTo(1.5, 10);
  });

  it('wraps a negative phase to [0, 2pi)', () => {
    const result = normalizePhase(-Math.PI / 2);
    expect(result).toBeGreaterThanOrEqual(0);
    expect(result).toBeLessThan(TWO_PI);
    expect(result).toBeCloseTo(TWO_PI - Math.PI / 2, 10);
  });

  it('wraps a phase > 2pi correctly', () => {
    const result = normalizePhase(TWO_PI + 1.0);
    expect(result).toBeGreaterThanOrEqual(0);
    expect(result).toBeLessThan(TWO_PI);
    expect(result).toBeCloseTo(1.0, 10);
  });

  it('wraps a very large phase correctly', () => {
    const result = normalizePhase(100 * TWO_PI + 0.5);
    expect(result).toBeGreaterThanOrEqual(0);
    expect(result).toBeLessThan(TWO_PI);
    expect(result).toBeCloseTo(0.5, 8);
  });
});

describe('phaseDist', () => {
  it('returns 0 for same phase', () => {
    expect(phaseDist(1.0, 1.0)).toBeCloseTo(0, 10);
  });

  it('returns pi for opposite phases', () => {
    expect(phaseDist(0, Math.PI)).toBeCloseTo(Math.PI, 10);
  });

  it('is symmetric: phaseDist(a, b) === phaseDist(b, a)', () => {
    const a = 0.7;
    const b = 4.2;
    expect(phaseDist(a, b)).toBeCloseTo(phaseDist(b, a), 10);
  });
});

describe('node management', () => {
  let bus: OscillatorBus;

  beforeEach(() => {
    bus = new OscillatorBus();
  });

  it('addNode stores node with correct state', () => {
    const state = bus.addNode('alpha', pos(1, 2, 3), 0.8, 5.0, Math.PI / 4);

    expect(state.id).toBe('alpha');
    expect(state.phase).toBeCloseTo(Math.PI / 4, 10);
    expect(state.frequency).toBe(5.0);
    expect(state.trust).toBe(0.8);
    expect(state.position).toEqual({ x: 1, y: 2, z: 3 });
    expect(state.mode).toBe('COMMIT'); // 5.0 Hz is in COMMIT band
    expect(state.phaseVelocity).toBe(0);

    // Verify it can be retrieved
    expect(bus.getNode('alpha')).toBeDefined();
    expect(bus.getNodeCount()).toBe(1);
  });

  it('addNode clamps trust to [0, 1]', () => {
    const overTrust = bus.addNode('high', pos(), 5.0, 3.0, 0);
    expect(overTrust.trust).toBe(1.0);

    const underTrust = bus.addNode('low', pos(), -2.0, 3.0, 0);
    expect(underTrust.trust).toBe(0.0);
  });

  it('addNode caps frequency to maxFrequency', () => {
    // Default maxFrequency is 20.0
    const state = bus.addNode('fast', pos(), 0.5, 999.0, 0);
    expect(state.frequency).toBe(20.0);
  });

  it('removeNode removes correctly', () => {
    bus.addNode('temp', pos(), 0.5, 3.0, 0);
    expect(bus.getNodeCount()).toBe(1);

    const removed = bus.removeNode('temp');
    expect(removed).toBe(true);
    expect(bus.getNodeCount()).toBe(0);
    expect(bus.getNode('temp')).toBeUndefined();

    // Removing a non-existent node returns false
    expect(bus.removeNode('ghost')).toBe(false);
  });

  it('setTrust updates trust', () => {
    bus.addNode('agent', pos(), 0.5, 3.0, 0);
    bus.setTrust('agent', 0.9);
    expect(bus.getNode('agent')!.trust).toBe(0.9);

    // Clamped to [0, 1]
    bus.setTrust('agent', 1.5);
    expect(bus.getNode('agent')!.trust).toBe(1.0);
  });
});

describe('coupling computation', () => {
  let bus: OscillatorBus;

  beforeEach(() => {
    bus = new OscillatorBus({
      couplingStrength: 1.0,
      couplingRadius: 15.0,
      minTrustForCoupling: 0.1,
    });
  });

  it('two nodes at same phase produce coupling near 0 (sin(0) = 0)', () => {
    bus.addNode('a', pos(0, 0, 0), 1.0, 3.0, 0);
    bus.addNode('b', pos(1, 0, 0), 1.0, 3.0, 0);

    const coupling = bus.computeCoupling('a');
    expect(Math.abs(coupling)).toBeLessThan(1e-10);
  });

  it('two nodes at phase difference pi/2 produce positive coupling', () => {
    bus.addNode('a', pos(0, 0, 0), 1.0, 3.0, 0);
    bus.addNode('b', pos(1, 0, 0), 1.0, 3.0, Math.PI / 2);

    // sin(pi/2 - 0) = 1, coupling for 'a' should be > 0
    const coupling = bus.computeCoupling('a');
    expect(coupling).toBeGreaterThan(0);
    // K=1, N_eff=1 (one neighbor with trust=1), coupling = 1/1 * 1 * sin(pi/2) = 1.0
    expect(coupling).toBeCloseTo(1.0, 10);
  });

  it('excludes node with trust below minTrustForCoupling', () => {
    bus.addNode('a', pos(0, 0, 0), 1.0, 3.0, 0);
    bus.addNode('untrusted', pos(1, 0, 0), 0.01, 3.0, Math.PI / 2); // trust < 0.1

    const coupling = bus.computeCoupling('a');
    expect(Math.abs(coupling)).toBeLessThan(1e-10);
  });

  it('excludes node beyond couplingRadius', () => {
    bus.addNode('a', pos(0, 0, 0), 1.0, 3.0, 0);
    bus.addNode('far', pos(100, 0, 0), 1.0, 3.0, Math.PI / 2); // distance = 100 > 15

    const coupling = bus.computeCoupling('a');
    expect(Math.abs(coupling)).toBeLessThan(1e-10);
  });

  it('high-trust neighbor has more coupling influence than low-trust', () => {
    // Two scenarios: one with high trust neighbor, one with low trust neighbor
    // Both at the same phase offset

    // Scenario 1: high trust neighbor
    const bus1 = new OscillatorBus({ couplingStrength: 1.0, couplingRadius: 15.0 });
    bus1.addNode('a', pos(0, 0, 0), 1.0, 3.0, 0);
    bus1.addNode('high', pos(1, 0, 0), 0.9, 3.0, Math.PI / 2);
    const couplingHigh = bus1.computeCoupling('a');

    // Scenario 2: low trust neighbor
    const bus2 = new OscillatorBus({ couplingStrength: 1.0, couplingRadius: 15.0 });
    bus2.addNode('a', pos(0, 0, 0), 1.0, 3.0, 0);
    bus2.addNode('low', pos(1, 0, 0), 0.2, 3.0, Math.PI / 2);
    const couplingLow = bus2.computeCoupling('a');

    // With a single neighbor, coupling = K/tau * tau * sin(delta) = K * sin(delta)
    // Both should be equal since K * sin(pi/2) = 1 in both cases.
    // BUT with multiple neighbors at different trusts, the weighting matters.
    // Let's test with two neighbors to show the trust difference.

    const bus3 = new OscillatorBus({ couplingStrength: 1.0, couplingRadius: 15.0 });
    bus3.addNode('target', pos(0, 0, 0), 1.0, 3.0, 0);
    bus3.addNode('highTrust', pos(1, 0, 0), 0.9, 3.0, Math.PI / 2); // pulls toward pi/2
    bus3.addNode('lowTrust', pos(2, 0, 0), 0.1, 3.0, -Math.PI / 2); // pulls toward -pi/2

    const coupling3 = bus3.computeCoupling('target');
    // High trust neighbor (0.9) should dominate, so net coupling should be positive
    expect(coupling3).toBeGreaterThan(0);
  });

  it('isolated node (no neighbors) has coupling of 0', () => {
    bus.addNode('lonely', pos(0, 0, 0), 1.0, 3.0, 0);
    const coupling = bus.computeCoupling('lonely');
    expect(coupling).toBe(0);
  });
});

describe('step dynamics', () => {
  let bus: OscillatorBus;

  beforeEach(() => {
    bus = new OscillatorBus({ dt: 0.01, couplingStrength: 1.0, couplingRadius: 15.0 });
  });

  it('single node: phase advances by omega * dt (no coupling)', () => {
    const freq = 3.0;
    const initialPhase = 0;
    bus.addNode('solo', pos(), 1.0, freq, initialPhase);

    bus.step();

    const node = bus.getNode('solo')!;
    // omega = 2 * PI * freq, expected advance = omega * dt
    const expectedPhase = normalizePhase(initialPhase + 2 * Math.PI * freq * 0.01);
    expect(node.phase).toBeCloseTo(expectedPhase, 10);
  });

  it('two identical-frequency same-phase nodes: phases stay synchronized', () => {
    const freq = 5.0;
    const phase = 1.0;
    bus.addNode('a', pos(0, 0, 0), 1.0, freq, phase);
    bus.addNode('b', pos(1, 0, 0), 1.0, freq, phase);

    // Step multiple times
    for (let i = 0; i < 100; i++) {
      bus.step();
    }

    const nodeA = bus.getNode('a')!;
    const nodeB = bus.getNode('b')!;
    // Same frequency, same initial phase, coupling sin(0) = 0 => phases remain equal
    expect(phaseDist(nodeA.phase, nodeB.phase)).toBeLessThan(1e-8);
  });

  it('phase values stay in [0, 2pi) after stepping', () => {
    addClusteredNodes(bus, 5, { frequency: 8.0, phase: 5.5, phaseSpread: 0.7 });

    // Run many steps to accumulate large phase
    for (let i = 0; i < 500; i++) {
      bus.step();
    }

    for (const node of bus.getNodes()) {
      expect(node.phase).toBeGreaterThanOrEqual(0);
      expect(node.phase).toBeLessThan(TWO_PI);
    }
  });

  it('step returns a BusSnapshot', () => {
    addClusteredNodes(bus, 3, { frequency: 3.5, phase: 0.5, phaseSpread: 0.1 });

    const snapshot = bus.step();

    expect(snapshot).toBeDefined();
    expect(typeof snapshot.orderParameter).toBe('number');
    expect(typeof snapshot.meanPhase).toBe('number');
    expect(typeof snapshot.dominantMode).toBe('string');
    expect(snapshot.modeDistribution).toBeDefined();
    expect(typeof snapshot.clusterCount).toBe('number');
    expect(typeof snapshot.timestamp).toBe('number');
  });

  it('run(N) advances N steps', () => {
    const freq = 4.0;
    bus.addNode('runner', pos(), 1.0, freq, 0);

    const snapshot = bus.run(10);

    // After 10 steps, phase should have advanced by 10 * omega * dt
    const expectedPhase = normalizePhase(10 * 2 * Math.PI * freq * 0.01);
    const node = bus.getNode('runner')!;
    expect(node.phase).toBeCloseTo(expectedPhase, 8);

    // run() returns a valid snapshot
    expect(snapshot).toBeDefined();
    expect(snapshot.orderParameter).toBeGreaterThanOrEqual(0);
  });
});

describe('order parameter', () => {
  let bus: OscillatorBus;

  beforeEach(() => {
    bus = new OscillatorBus();
  });

  it('all nodes at same phase produce r near 1.0', () => {
    const samePhase = 1.0;
    for (let i = 0; i < 10; i++) {
      bus.addNode(`n${i}`, pos(i, 0, 0), 1.0, 3.0, samePhase);
    }

    const { r } = bus.computeOrderParameter();
    expect(r).toBeCloseTo(1.0, 8);
  });

  it('nodes uniformly spread produce r near 0', () => {
    const n = 100;
    for (let i = 0; i < n; i++) {
      const phase = (TWO_PI * i) / n;
      bus.addNode(`n${i}`, pos(i * 0.1, 0, 0), 1.0, 3.0, phase);
    }

    const { r } = bus.computeOrderParameter();
    expect(r).toBeLessThan(0.05);
  });

  it('two nodes at same phase produce r = 1.0', () => {
    bus.addNode('a', pos(0, 0, 0), 1.0, 3.0, 2.0);
    bus.addNode('b', pos(1, 0, 0), 1.0, 3.0, 2.0);

    const { r } = bus.computeOrderParameter();
    expect(r).toBeCloseTo(1.0, 10);
  });

  it('empty bus produces r = 0', () => {
    const { r } = bus.computeOrderParameter();
    expect(r).toBe(0);
  });
});

describe('mode broadcasting', () => {
  let bus: OscillatorBus;

  beforeEach(() => {
    bus = new OscillatorBus();
    addClusteredNodes(bus, 5, { frequency: 3.0, phase: 0, phaseSpread: 0.2 });
  });

  it('broadcastMode(HAZARD) sets all nodes to HAZARD', () => {
    bus.broadcastMode('HAZARD');

    for (const node of bus.getNodes()) {
      expect(node.mode).toBe('HAZARD');
    }
  });

  it('broadcastMode sets correct target frequency', () => {
    bus.broadcastMode('COMMIT');

    for (const node of bus.getNodes()) {
      // getModeTargetFrequency('COMMIT') = 7.5
      expect(node.frequency).toBe(7.5);
      expect(node.mode).toBe('COMMIT');
    }
  });

  it('injectFrequency changes a single node frequency', () => {
    const ids = bus.getNodes().map((n) => n.id);
    bus.injectFrequency(ids[0], 12.0);

    const injected = bus.getNode(ids[0])!;
    expect(injected.frequency).toBe(12.0);
    expect(injected.mode).toBe('HAZARD');

    // Other nodes remain unchanged
    for (let i = 1; i < ids.length; i++) {
      const node = bus.getNode(ids[i])!;
      expect(node.frequency).toBe(3.0);
      expect(node.mode).toBe('EXPLORE');
    }
  });
});

describe('synchronization', () => {
  it('nodes with same frequency and coupling converge over many steps', () => {
    const bus = new OscillatorBus({
      couplingStrength: 5.0,
      couplingRadius: 50.0,
      dt: 0.01,
    });

    // Start with varied phases but same frequency
    const n = 8;
    for (let i = 0; i < n; i++) {
      const phase = (TWO_PI * i) / n; // uniformly spread
      bus.addNode(`s${i}`, pos(i, 0, 0), 1.0, 3.0, phase);
    }

    // Measure initial order parameter
    const initialR = bus.computeOrderParameter().r;

    // Run many steps to allow synchronization
    bus.run(5000);

    // Measure final order parameter
    const finalR = bus.computeOrderParameter().r;

    // The order parameter should increase (convergence toward synchronization)
    expect(finalR).toBeGreaterThan(initialR);
    // With strong coupling and many steps, should be close to synchronized
    expect(finalR).toBeGreaterThan(0.8);
  });

  it('snapshot contains correct mode distribution', () => {
    const bus = new OscillatorBus();

    // Add nodes in different mode bands
    bus.addNode('regroup1', pos(0, 0, 0), 1.0, 1.0, 0); // REGROUP
    bus.addNode('regroup2', pos(1, 0, 0), 1.0, 1.5, 0); // REGROUP
    bus.addNode('explore1', pos(2, 0, 0), 1.0, 3.5, 0); // EXPLORE
    bus.addNode('commit1', pos(3, 0, 0), 1.0, 7.0, 0); // COMMIT
    bus.addNode('hazard1', pos(4, 0, 0), 1.0, 15.0, 0); // HAZARD

    const snapshot = bus.computeSnapshot();

    expect(snapshot.modeDistribution.REGROUP).toBe(2);
    expect(snapshot.modeDistribution.EXPLORE).toBe(1);
    expect(snapshot.modeDistribution.COMMIT).toBe(1);
    expect(snapshot.modeDistribution.HAZARD).toBe(1);
    expect(snapshot.dominantMode).toBe('REGROUP');
  });
});
