/**
 * @file test_dtn_bundle.ts
 * @module tests/fleet/dtn-bundle
 * @layer L7, L11, L13
 *
 * DTN Bundle Protocol — Nodal network simulation tests.
 * Validates store-and-forward, occlusion survival, custody transfer,
 * FEC recovery, and the P_DTN vs P_TCP survival math.
 */

import { describe, expect, it } from 'vitest';
import {
  BundleStore,
  ContactGraph,
  DTNNetworkSimulator,
  DTNRelayNode,
  createBundle,
} from '../../src/fleet/dtn-bundle.js';

describe('DTN Bundle Protocol', () => {
  // ──── Bundle Creation ────

  describe('createBundle', () => {
    it('creates a bundle with all required fields', () => {
      const bundle = createBundle('L1-input', 'L13-governance', { task: 'test' }, 'CA');

      expect(bundle.id).toMatch(/^bndl-/);
      expect(bundle.sourceEndpoint).toBe('L1-input');
      expect(bundle.destinationEndpoint).toBe('L13-governance');
      expect(bundle.tongue).toBe('CA');
      expect(bundle.status).toBe('CREATED');
      expect(bundle.payload).toEqual({ task: 'test' });
      expect(bundle.fecBlocks).toHaveLength(6); // All 6 tongues
      expect(bundle.custodyChain).toHaveLength(0);
      expect(bundle.governanceScore).toBeGreaterThan(0);
      expect(bundle.governanceScore).toBeLessThanOrEqual(1);
    });

    it('scales lifetime by governance score and tongue weight', () => {
      // Safe bundle (low distance) should have longer lifetime
      const safe = createBundle('src', 'dst', {}, 'KO', {
        hyperbolicDistance: 0.1,
        lifetime: 10,
      });
      // Adversarial bundle (high distance) should expire faster
      const adversarial = createBundle('src', 'dst', {}, 'KO', {
        hyperbolicDistance: 5.0,
        perturbationDensity: 2.0,
        lifetime: 10,
      });

      expect(safe.lifetime).toBeGreaterThan(adversarial.lifetime);
    });

    it('packs assumptions and contingencies', () => {
      const bundle = createBundle('src', 'dst', {}, 'RU', {
        assumptions: ['DB is available', 'Auth token is valid'],
        contingencies: ['Retry with backoff', 'Fallback to cache'],
      });

      expect(bundle.assumptions).toHaveLength(2);
      expect(bundle.contingencies).toHaveLength(2);
    });

    it('generates FEC blocks for all 6 tongues', () => {
      const bundle = createBundle('src', 'dst', { data: 'important' }, 'DR');

      expect(bundle.fecBlocks).toHaveLength(6);
      const tongues = bundle.fecBlocks.map((b) => b.tongue);
      expect(tongues).toContain('KO');
      expect(tongues).toContain('AV');
      expect(tongues).toContain('RU');
      expect(tongues).toContain('CA');
      expect(tongues).toContain('UM');
      expect(tongues).toContain('DR');

      // Each block should have a hash
      for (const block of bundle.fecBlocks) {
        expect(block.hash).toBeTruthy();
        expect(block.encoding).toContain(block.tongue);
      }
    });
  });

  // ──── Bundle Store ────

  describe('BundleStore', () => {
    it('stores and retrieves bundles', () => {
      const store = new BundleStore(10);
      const bundle = createBundle('src', 'dst', {}, 'KO');

      expect(store.store(bundle)).toBe(true);
      expect(store.size).toBe(1);
      expect(store.get(bundle.id)).toBe(bundle);
    });

    it('respects capacity limits', () => {
      const store = new BundleStore(2);
      const b1 = createBundle('src', 'dst', {}, 'KO');
      const b2 = createBundle('src', 'dst', {}, 'AV');
      const b3 = createBundle('src', 'dst', {}, 'RU');

      expect(store.store(b1)).toBe(true);
      expect(store.store(b2)).toBe(true);
      expect(store.store(b3)).toBe(false); // At capacity
      expect(store.size).toBe(2);
    });

    it('evicts expired bundles to make room', () => {
      const store = new BundleStore(2);
      const b1 = createBundle('src', 'dst', {}, 'KO');
      b1.remainingLifetime = 0; // Expired
      const b2 = createBundle('src', 'dst', {}, 'AV');
      const b3 = createBundle('src', 'dst', {}, 'RU');

      store.store(b1);
      store.store(b2);
      // b3 should succeed after b1 is evicted
      expect(store.store(b3)).toBe(true);
      expect(store.size).toBe(2);
      expect(store.get(b1.id)).toBeUndefined();
    });

    it('retrieves bundles by destination ordered by priority', () => {
      const store = new BundleStore(10);
      const low = createBundle('src', 'target', {}, 'KO', { priority: 'low' });
      const high = createBundle('src', 'target', {}, 'AV', { priority: 'high' });
      const critical = createBundle('src', 'target', {}, 'RU', { priority: 'critical' });

      store.store(low);
      store.store(high);
      store.store(critical);

      const forTarget = store.getForDestination('target');
      expect(forTarget[0].priority).toBe('critical');
      expect(forTarget[1].priority).toBe('high');
      expect(forTarget[2].priority).toBe('low');
    });
  });

  // ──── Contact Graph ────

  describe('ContactGraph', () => {
    it('finds available windows', () => {
      const graph = new ContactGraph();
      graph.addWindow({ from: 'A', to: 'B', opensAt: 0, closesAt: 10, bandwidth: 5 });
      graph.addWindow({ from: 'A', to: 'C', opensAt: 5, closesAt: 15, bandwidth: 3 });

      const atTime3 = graph.getAvailableWindows('A', 3);
      expect(atTime3).toHaveLength(1);
      expect(atTime3[0].to).toBe('B');

      const atTime7 = graph.getAvailableWindows('A', 7);
      expect(atTime7).toHaveLength(2);
    });

    it('finds next window after a time', () => {
      const graph = new ContactGraph();
      graph.addWindow({ from: 'A', to: 'B', opensAt: 10, closesAt: 20, bandwidth: 5 });
      graph.addWindow({ from: 'A', to: 'B', opensAt: 30, closesAt: 40, bandwidth: 5 });

      const next = graph.getNextWindow('A', 'B', 5);
      expect(next?.opensAt).toBe(10);

      const afterFirst = graph.getNextWindow('A', 'B', 15);
      expect(afterFirst?.opensAt).toBe(30);
    });

    it('checks multi-hop route existence', () => {
      const graph = new ContactGraph();
      graph.addWindow({ from: 'A', to: 'B', opensAt: 0, closesAt: 100, bandwidth: 5 });
      graph.addWindow({ from: 'B', to: 'C', opensAt: 0, closesAt: 100, bandwidth: 5 });

      expect(graph.hasRoute('A', 'C', 5)).toBe(true);
      expect(graph.hasRoute('A', 'D', 5)).toBe(false);
      expect(graph.hasRoute('C', 'A', 5)).toBe(false); // Directed
    });
  });

  // ──── DTN Relay Node ────

  describe('DTNRelayNode', () => {
    it('receives and delivers bundles at destination', () => {
      const graph = new ContactGraph();
      const node = new DTNRelayNode('L13-governance', graph);
      const bundle = createBundle('L1-input', 'L13-governance', { thought: 'test' }, 'RU');

      const received = node.receive(bundle);
      expect(received).toBe(true);
      expect(bundle.status).toBe('DELIVERED');
      expect(bundle.custodyChain).toHaveLength(1);
      expect(bundle.custodyChain[0].nodeId).toBe('L13-governance');
    });

    it('stores bundles when not the destination', () => {
      const graph = new ContactGraph();
      const node = new DTNRelayNode('L5-symmetry', graph);
      const bundle = createBundle('L1-input', 'L13-governance', {}, 'CA');

      const received = node.receive(bundle);
      expect(received).toBe(true);
      expect(bundle.status).toBe('STORED');
      expect(node.store.size).toBe(1);
    });

    it('rejects expired bundles', () => {
      const graph = new ContactGraph();
      const node = new DTNRelayNode('L5-symmetry', graph);
      const bundle = createBundle('src', 'dst', {}, 'KO');
      bundle.remainingLifetime = 0;

      const received = node.receive(bundle);
      expect(received).toBe(false);
      expect(bundle.status).toBe('EXPIRED');
    });

    it('does not forward during occlusion', () => {
      const graph = new ContactGraph();
      graph.addWindow({ from: 'relay', to: 'dst', opensAt: 0, closesAt: 100, bandwidth: 5 });
      const node = new DTNRelayNode('relay', graph);
      const bundle = createBundle('src', 'dst', {}, 'AV');
      node.receive(bundle);

      node.setOccluded(true);
      const forwarded = node.forward(5);
      expect(forwarded).toHaveLength(0);

      node.setOccluded(false);
      const afterOcclusion = node.forward(5);
      expect(afterOcclusion).toHaveLength(1);
    });

    it('tracks telemetry correctly', () => {
      const graph = new ContactGraph();
      const node = new DTNRelayNode('test-node', graph);
      const bundle = createBundle('src', 'test-node', {}, 'UM');

      node.receive(bundle);
      node.setOccluded(true);
      node.setOccluded(false);

      const telem = node.getTelemetry();
      expect(telem.bundlesReceived).toBe(1);
      expect(telem.custodyTransfers).toBe(1);
      expect(telem.occlusionEvents).toBe(1);
    });
  });

  // ──── Network Simulator ────

  describe('DTNNetworkSimulator', () => {
    it('simulates a 3-node relay network', () => {
      const sim = new DTNNetworkSimulator();

      sim.addNode('source');
      sim.addNode('relay');
      sim.addNode('destination');

      // Contact windows: source→relay (steps 1-5), relay→destination (steps 3-10)
      sim.addContactWindow('source', 'relay', 1, 5, 5);
      sim.addContactWindow('relay', 'destination', 3, 10, 5);

      const bundle = createBundle('source', 'destination', { thought: 'hello mars' }, 'CA');
      sim.inject(bundle, 'source');

      const results = sim.run(10);
      const final = results[results.length - 1];

      expect(final.bundlesDelivered).toBe(1);
      expect(final.deliveryRate).toBe(1.0);
    });

    it('survives occlusion via store-and-forward', () => {
      const sim = new DTNNetworkSimulator();

      sim.addNode('earth');
      sim.addNode('relay');
      sim.addNode('mars');

      // earth→relay always open, relay→mars opens at step 6
      sim.addContactWindow('earth', 'relay', 1, 100, 5);
      sim.addContactWindow('relay', 'mars', 6, 100, 5);

      const bundle = createBundle('earth', 'mars', { data: 'science' }, 'DR', { lifetime: 20 });
      sim.inject(bundle, 'earth');

      // Occlude relay for steps 1-5 (Mars behind the Sun)
      sim.setOcclusion('relay', true);
      sim.run(5);
      sim.setOcclusion('relay', false);
      sim.run(5);

      const final = sim.getHistory()[sim.getHistory().length - 1];
      expect(final.bundlesDelivered).toBe(1);
    });

    it('validates P_DTN vs P_TCP math', () => {
      const cases = [
        { p: 0.3, n: 10 },
        { p: 0.5, n: 5 },
        { p: 0.1, n: 20 },
      ];

      for (const { p, n } of cases) {
        const result = DTNNetworkSimulator.survivalComparison(p, n);

        // DTN should always beat TCP under occlusion
        expect(result.dtn).toBeGreaterThan(result.tcp);

        // Verify formulas
        const expectedTcp = Math.pow(1 - p, n);
        const expectedDtn = 1 - Math.pow(p, n);
        expect(result.tcp).toBeCloseTo(expectedTcp, 4);
        expect(result.dtn).toBeCloseTo(expectedDtn, 4);
      }
    });

    it('handles 14-layer pipeline as a DTN network', () => {
      const sim = new DTNNetworkSimulator();

      // Create all 14 pipeline layers as relay nodes
      for (let i = 1; i <= 14; i++) {
        sim.addNode(`L${i}`);
      }

      // Contact windows between consecutive layers (always open)
      for (let i = 1; i < 14; i++) {
        sim.addContactWindow(`L${i}`, `L${i + 1}`, 1, 100, 10);
      }

      // Inject a thought bundle at L1
      const bundle = createBundle('L1', 'L14', { thought: 'full pipeline test' }, 'DR', {
        lifetime: 30,
        assumptions: ['Input validated', 'Auth verified'],
        contingencies: ['Retry at L8 if Hamiltonian check fails'],
      });
      sim.inject(bundle, 'L1');

      // Run for enough steps to traverse all 14 layers
      sim.run(20);

      const final = sim.getHistory()[sim.getHistory().length - 1];
      expect(final.bundlesDelivered).toBe(1);

      // Check custody chain shows intermediate hops
      expect(bundle.custodyChain.length).toBeGreaterThanOrEqual(2);
    });
  });

  // ──── Harmonic Governance Score ────

  describe('Harmonic Governance', () => {
    it('safe bundles score higher than adversarial', () => {
      const safe = createBundle('src', 'dst', {}, 'KO', {
        hyperbolicDistance: 0.1,
        perturbationDensity: 0.0,
      });
      const risky = createBundle('src', 'dst', {}, 'KO', {
        hyperbolicDistance: 2.0,
        perturbationDensity: 1.0,
      });
      const adversarial = createBundle('src', 'dst', {}, 'KO', {
        hyperbolicDistance: 10.0,
        perturbationDensity: 5.0,
      });

      expect(safe.governanceScore).toBeGreaterThan(risky.governanceScore);
      expect(risky.governanceScore).toBeGreaterThan(adversarial.governanceScore);
      expect(adversarial.governanceScore).toBeLessThan(0.05);
    });
  });
});
