/**
 * Combat Network Tests
 *
 * Tests for the CombatNetwork class implementing multipath routing
 * with disjoint paths for combat scenario redundancy.
 *
 * Covers:
 * - Standard routing mode
 * - Combat mode with disjoint paths
 * - Path health monitoring
 * - Acknowledgment handling with retries
 * - Network statistics
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { CombatNetwork, TransmissionResult, PathHealth } from '../../src/network/combat-network.js';
import { SpaceTorRouter, RelayNode } from '../../src/network/space-tor-router.js';
import { HybridSpaceCrypto } from '../../src/network/hybrid-crypto.js';

describe('CombatNetwork', () => {
  let router: SpaceTorRouter;
  let crypto: HybridSpaceCrypto;
  let combatNet: CombatNetwork;

  // Test coordinates (in AU)
  const earthCoords = { x: 1.0, y: 0, z: 0 };
  const marsCoords = { x: 1.5, y: 0.1, z: 0 };
  const jupiterCoords = { x: 5.2, y: 0, z: 0 };

  // Helper to create RelayNode with required fields
  const createNode = (
    id: string,
    coords: { x: number; y: number; z: number },
    trustScore: number,
    load: number,
    quantumCapable: boolean
  ): RelayNode => ({
    id,
    coords,
    trustScore,
    load,
    quantumCapable,
    lastSeen: Date.now(),
    bandwidth: 1000
  });

  beforeEach(() => {
    // Create test nodes
    const testNodes: RelayNode[] = [
      // Inner solar system relays
      createNode('RELAY-EARTH-1', { x: 1.0, y: 0.05, z: 0 }, 95, 0.2, true),
      createNode('RELAY-EARTH-2', { x: 1.0, y: -0.05, z: 0 }, 90, 0.3, true),
      createNode('RELAY-VENUS', { x: 0.7, y: 0, z: 0.02 }, 85, 0.1, false),

      // Mid-range relays
      createNode('RELAY-BELT-1', { x: 2.5, y: 0.1, z: 0 }, 88, 0.4, true),
      createNode('RELAY-BELT-2', { x: 2.5, y: -0.1, z: 0 }, 82, 0.2, false),
      createNode('RELAY-BELT-3', { x: 2.8, y: 0, z: 0.1 }, 78, 0.5, true),

      // Mars relays
      createNode('RELAY-MARS-1', { x: 1.5, y: 0.15, z: 0 }, 92, 0.3, true),
      createNode('RELAY-MARS-2', { x: 1.5, y: 0.05, z: 0.05 }, 87, 0.2, true),

      // Outer solar system
      createNode('RELAY-JUPITER-1', { x: 5.0, y: 0.1, z: 0 }, 80, 0.1, true),
      createNode('RELAY-JUPITER-2', { x: 5.0, y: -0.1, z: 0.05 }, 75, 0.3, false),
    ];

    router = new SpaceTorRouter(testNodes);
    crypto = new HybridSpaceCrypto();

    combatNet = new CombatNetwork(router, crypto, {
      acknowledgment: {
        enabled: true,
        timeoutMs: 1000, // Short timeout for tests
        maxRetries: 2
      },
      minDisjointPaths: 2,
      healthTrackingWindow: 50
    });
  });

  // ============================================================================
  // Standard Routing Tests
  // ============================================================================

  describe('Standard Routing Mode', () => {
    it('should route via single path in standard mode', async () => {
      const results = await combatNet.send('Test message', earthCoords, marsCoords, false);

      expect(results).toHaveLength(1);
      expect(results[0].pathId).toBe('STANDARD');
      expect(results[0].success).toBe(true);
    });

    it('should calculate transmission latency', async () => {
      const results = await combatNet.send('Test', earthCoords, marsCoords, false);

      expect(results[0].latencyMs).toBeGreaterThan(0);
    });

    it('should handle acknowledgments in standard mode', async () => {
      const results = await combatNet.send('Test', earthCoords, marsCoords, false);

      // Acknowledgment should be processed (may be true or false based on simulation)
      expect(typeof results[0].acknowledged).toBe('boolean');
    });
  });

  // ============================================================================
  // Combat Mode Tests
  // ============================================================================

  describe('Combat Mode (Multipath Routing)', () => {
    it('should route via multiple disjoint paths in combat mode', async () => {
      const results = await combatNet.send('Combat message', earthCoords, marsCoords, true);

      expect(results.length).toBeGreaterThanOrEqual(2);
      expect(results[0].pathId).toBe('PRIMARY');
      expect(results[1].pathId).toBe('BACKUP-1');
    });

    it('should ensure paths are fully disjoint (no shared nodes)', () => {
      const paths = combatNet.generateDisjointPaths(earthCoords, marsCoords, 70, 2);

      expect(paths.length).toBeGreaterThanOrEqual(1);

      if (paths.length >= 2) {
        const path1Nodes = new Set(paths[0].map(n => n.id));
        const path2Nodes = new Set(paths[1].map(n => n.id));

        // No node should appear in both paths
        for (const nodeId of path1Nodes) {
          expect(path2Nodes.has(nodeId)).toBe(false);
        }
      }
    });

    it('should handle reduced path availability gracefully', () => {
      // Request more paths than available
      const paths = combatNet.generateDisjointPaths(earthCoords, marsCoords, 70, 10);

      // Should return at least 1 path, possibly fewer than requested
      expect(paths.length).toBeGreaterThanOrEqual(1);
      expect(paths.length).toBeLessThanOrEqual(10);
    });

    it('should throw if no primary path can be established', () => {
      // Use coordinates with no reachable nodes (very high trust threshold)
      expect(() => {
        combatNet.generateDisjointPaths(earthCoords, marsCoords, 99, 2);
      }).toThrow();
    });
  });

  // ============================================================================
  // Path Health Monitoring Tests
  // ============================================================================

  describe('Path Health Monitoring', () => {
    it('should track path health statistics', async () => {
      // Send multiple messages to build health history
      await combatNet.send('Msg 1', earthCoords, marsCoords, false);
      await combatNet.send('Msg 2', earthCoords, marsCoords, false);
      await combatNet.send('Msg 3', earthCoords, marsCoords, false);

      const healthStats = combatNet.getPathHealthStats();

      expect(healthStats.length).toBeGreaterThan(0);
      expect(healthStats[0]).toHaveProperty('successRate');
      expect(healthStats[0]).toHaveProperty('averageLatencyMs');
      expect(healthStats[0]).toHaveProperty('successCount');
      expect(healthStats[0]).toHaveProperty('failureCount');
    });

    it('should return health for specific path', async () => {
      await combatNet.send('Test', earthCoords, marsCoords, false);

      const health = combatNet.getPathHealth(['STANDARD']);

      expect(health).toBeDefined();
      expect(health.pathId).toBe('STANDARD');
    });

    it('should sort paths by success rate', async () => {
      // Generate some traffic
      await combatNet.send('Test 1', earthCoords, marsCoords, true);
      await combatNet.send('Test 2', earthCoords, marsCoords, true);

      const healthStats = combatNet.getPathHealthStats();

      // Should be sorted by success rate (descending)
      for (let i = 1; i < healthStats.length; i++) {
        expect(healthStats[i - 1].successRate).toBeGreaterThanOrEqual(healthStats[i].successRate);
      }
    });

    it('should clear health history', async () => {
      await combatNet.send('Test', earthCoords, marsCoords, false);

      let healthStats = combatNet.getPathHealthStats();
      expect(healthStats.length).toBeGreaterThan(0);

      combatNet.clearHealthHistory();

      healthStats = combatNet.getPathHealthStats();
      expect(healthStats.length).toBe(0);
    });
  });

  // ============================================================================
  // Acknowledgment Handling Tests
  // ============================================================================

  describe('Acknowledgment Handling', () => {
    it('should receive acknowledgments', async () => {
      const results = await combatNet.send('Test', earthCoords, marsCoords, false);

      // The simulation has 80% ack success rate
      expect(typeof results[0].acknowledged).toBe('boolean');
    });

    it('should track retry count', async () => {
      const results = await combatNet.send('Test', earthCoords, marsCoords, false);

      expect(results[0].retries).toBeGreaterThanOrEqual(0);
      expect(results[0].retries).toBeLessThanOrEqual(2); // maxRetries = 2
    });

    it('should allow manual acknowledgment', () => {
      // Set up pending ack
      const pathId = 'TEST-PATH';

      // This tests the public receiveAck method
      // In real usage, this would be called by the network layer
      combatNet.receiveAck(pathId, true);

      // Should not throw
      expect(true).toBe(true);
    });

    it('should handle disabled acknowledgments', async () => {
      const noAckNet = new CombatNetwork(router, crypto, {
        acknowledgment: {
          enabled: false,
          timeoutMs: 1000,
          maxRetries: 0
        }
      });

      const results = await noAckNet.send('Test', earthCoords, marsCoords, false);

      // When acks disabled, should still report acknowledged: true
      expect(results[0].acknowledged).toBe(true);
    });
  });

  // ============================================================================
  // Network Statistics Tests
  // ============================================================================

  describe('Network Statistics', () => {
    it('should report network stats', () => {
      const stats = combatNet.getNetworkStats();

      expect(stats.totalNodes).toBe(10);
      expect(stats.quantumCapableNodes).toBe(7);
      expect(stats.averageLoad).toBeGreaterThan(0);
      expect(stats.averageTrust).toBeGreaterThan(0);
    });

    it('should handle empty network', () => {
      const emptyRouter = new SpaceTorRouter();
      const emptyNet = new CombatNetwork(emptyRouter, crypto);

      const stats = emptyNet.getNetworkStats();

      expect(stats.totalNodes).toBe(0);
      expect(stats.quantumCapableNodes).toBe(0);
      expect(stats.averageLoad).toBe(0);
      expect(stats.averageTrust).toBe(0);
    });

    it('should check healthy redundancy', () => {
      const hasRedundancy = combatNet.hasHealthyRedundancy(earthCoords, marsCoords, 70, 2);

      expect(typeof hasRedundancy).toBe('boolean');
    });

    it('should return false for unreachable redundancy', () => {
      const hasRedundancy = combatNet.hasHealthyRedundancy(
        earthCoords,
        marsCoords,
        99, // Very high trust threshold
        5
      );

      expect(hasRedundancy).toBe(false);
    });
  });

  // ============================================================================
  // Edge Cases and Error Handling
  // ============================================================================

  describe('Edge Cases', () => {
    it('should handle empty message', async () => {
      const results = await combatNet.send('', earthCoords, marsCoords, false);

      expect(results).toHaveLength(1);
      expect(results[0].success).toBe(true);
    });

    it('should handle large messages', async () => {
      const largeMessage = 'X'.repeat(10000);
      const results = await combatNet.send(largeMessage, earthCoords, marsCoords, false);

      expect(results[0].success).toBe(true);
    });

    it('should handle same origin and destination', async () => {
      const results = await combatNet.send('Test', earthCoords, earthCoords, false);

      expect(results).toHaveLength(1);
    });

    it('should update node load after transmission', async () => {
      const initialStats = combatNet.getNetworkStats();
      const initialLoad = initialStats.averageLoad;

      await combatNet.send('Test', earthCoords, marsCoords, false);

      const newStats = combatNet.getNetworkStats();
      expect(newStats.averageLoad).toBeGreaterThanOrEqual(initialLoad);
    });
  });

  // ============================================================================
  // Configuration Tests
  // ============================================================================

  describe('Configuration', () => {
    it('should use default config when not provided', () => {
      const defaultNet = new CombatNetwork(router, crypto);

      const stats = defaultNet.getNetworkStats();
      expect(stats.totalNodes).toBe(10);
    });

    it('should allow partial config override', () => {
      const partialNet = new CombatNetwork(router, crypto, {
        minDisjointPaths: 3
      });

      // Should use provided value
      const paths = partialNet.generateDisjointPaths(earthCoords, marsCoords, 70, 3);
      expect(paths.length).toBeGreaterThanOrEqual(1);
    });

    it('should use custom health tracking window', async () => {
      const smallWindowNet = new CombatNetwork(router, crypto, {
        healthTrackingWindow: 5
      });

      // Send more messages than the window size
      for (let i = 0; i < 10; i++) {
        await smallWindowNet.send(`Msg ${i}`, earthCoords, marsCoords, false);
      }

      const health = smallWindowNet.getPathHealthStats();
      // Health should still be tracked
      expect(health.length).toBeGreaterThan(0);
    });
  });

  // ============================================================================
  // Concurrent Operations Tests
  // ============================================================================

  describe('Concurrent Operations', () => {
    it('should handle concurrent transmissions', async () => {
      const transmissions = [
        combatNet.send('Msg 1', earthCoords, marsCoords, false),
        combatNet.send('Msg 2', earthCoords, marsCoords, false),
        combatNet.send('Msg 3', earthCoords, marsCoords, false),
      ];

      const results = await Promise.all(transmissions);

      expect(results).toHaveLength(3);
      results.forEach(result => {
        expect(result).toHaveLength(1);
        expect(result[0].success).toBe(true);
      });
    });

    it('should handle concurrent combat mode transmissions', async () => {
      const transmissions = [
        combatNet.send('Combat 1', earthCoords, marsCoords, true),
        combatNet.send('Combat 2', earthCoords, marsCoords, true),
      ];

      const results = await Promise.all(transmissions);

      expect(results).toHaveLength(2);
      results.forEach(result => {
        expect(result.length).toBeGreaterThanOrEqual(1);
      });
    });
  });
});

// ============================================================================
// SpaceTorRouter Tests
// ============================================================================

describe('SpaceTorRouter', () => {
  let router: SpaceTorRouter;

  // Helper to create RelayNode with required fields
  const createNode = (
    id: string,
    coords: { x: number; y: number; z: number },
    trustScore: number,
    load: number,
    quantumCapable: boolean
  ): RelayNode => ({
    id,
    coords,
    trustScore,
    load,
    quantumCapable,
    lastSeen: Date.now(),
    bandwidth: 1000
  });

  beforeEach(() => {
    router = new SpaceTorRouter();
  });

  describe('Node Management', () => {
    it('should register nodes', () => {
      router.registerNode(createNode('TEST-1', { x: 1, y: 0, z: 0 }, 80, 0.5, true));

      expect(router.getNodes()).toHaveLength(1);
    });

    it('should remove nodes', () => {
      router.registerNode(createNode('TEST-1', { x: 1, y: 0, z: 0 }, 80, 0.5, true));

      router.removeNode('TEST-1');
      expect(router.getNodes()).toHaveLength(0);
    });

    it('should update node load', () => {
      router.registerNode(createNode('TEST-1', { x: 1, y: 0, z: 0 }, 80, 0.5, true));

      router.updateNodeLoad('TEST-1', 0.8);

      const nodes = router.getNodes();
      expect(nodes[0].load).toBe(0.8);
    });

    it('should get specific node by ID', () => {
      router.registerNode(createNode('TEST-1', { x: 1, y: 0, z: 0 }, 80, 0.5, true));

      const node = router.getNode('TEST-1');
      expect(node).toBeDefined();
      expect(node?.id).toBe('TEST-1');
    });

    it('should update node trust score', () => {
      router.registerNode(createNode('TEST-1', { x: 1, y: 0, z: 0 }, 80, 0.5, true));

      router.updateNodeTrust('TEST-1', 95);

      const node = router.getNode('TEST-1');
      expect(node?.trustScore).toBe(95);
    });
  });

  describe('Path Calculation', () => {
    beforeEach(() => {
      // Add test nodes
      router.registerNode(createNode('N1', { x: 1, y: 0, z: 0 }, 90, 0.2, true));
      router.registerNode(createNode('N2', { x: 2, y: 0, z: 0 }, 85, 0.3, true));
      router.registerNode(createNode('N3', { x: 3, y: 0, z: 0 }, 80, 0.4, false));
      router.registerNode(createNode('N4', { x: 2, y: 0.5, z: 0 }, 88, 0.2, true));
    });

    it('should calculate path', () => {
      const path = router.calculatePath(
        { x: 0, y: 0, z: 0 },
        { x: 4, y: 0, z: 0 },
        70
      );

      expect(path.length).toBeGreaterThanOrEqual(3); // Entry, Middle, Exit
    });

    it('should respect minimum trust', () => {
      const path = router.calculatePath(
        { x: 0, y: 0, z: 0 },
        { x: 4, y: 0, z: 0 },
        70
      );

      path.forEach(node => {
        expect(node.trustScore).toBeGreaterThanOrEqual(70);
      });
    });

    it('should calculate disjoint path', () => {
      const excludeNodes = new Set(['N1']);
      const path = router.calculateDisjointPath(
        { x: 0, y: 0, z: 0 },
        { x: 4, y: 0, z: 0 },
        70,
        excludeNodes
      );

      // Path should not include excluded nodes
      path.forEach(node => {
        expect(excludeNodes.has(node.id)).toBe(false);
      });
    });

    it('should throw when insufficient nodes', () => {
      const smallRouter = new SpaceTorRouter([
        createNode('ONLY-1', { x: 1, y: 0, z: 0 }, 90, 0.2, true)
      ]);

      expect(() => {
        smallRouter.calculatePath(
          { x: 0, y: 0, z: 0 },
          { x: 2, y: 0, z: 0 },
          70
        );
      }).toThrow('Insufficient eligible nodes');
    });
  });
});

// ============================================================================
// HybridSpaceCrypto Tests
// ============================================================================

describe('HybridSpaceCrypto', () => {
  let crypto: HybridSpaceCrypto;

  // Helper to create RelayNode with required fields
  const createNode = (
    id: string,
    coords: { x: number; y: number; z: number },
    trustScore: number,
    load: number,
    quantumCapable: boolean
  ): RelayNode => ({
    id,
    coords,
    trustScore,
    load,
    quantumCapable,
    lastSeen: Date.now(),
    bandwidth: 1000
  });

  beforeEach(() => {
    crypto = new HybridSpaceCrypto();
  });

  describe('Onion Encryption', () => {
    it('should build onion packet', async () => {
      const nodes: RelayNode[] = [
        createNode('N1', { x: 1, y: 0, z: 0 }, 90, 0.2, true),
        createNode('N2', { x: 2, y: 0, z: 0 }, 85, 0.3, true),
      ];

      const payload = Buffer.from('Secret message');
      const onion = await crypto.buildOnion(payload, nodes);

      expect(onion).toBeInstanceOf(Buffer);
      expect(onion.length).toBeGreaterThan(payload.length);
    });

    it('should peel onion layers', async () => {
      const nodes: RelayNode[] = [
        createNode('N1', { x: 1, y: 0, z: 0 }, 90, 0.2, true),
        createNode('N2', { x: 2, y: 0, z: 0 }, 85, 0.3, true),
      ];

      const payload = Buffer.from('Secret message');
      const onion = await crypto.buildOnion(payload, nodes);

      // Peel first layer
      const { payload: nextPayload, nextHop } = await crypto.peelOnion(onion, 'N1');

      expect(nextPayload).toBeInstanceOf(Buffer);
      expect(nextHop).toBe('N2');
    });

    it('should handle empty path', async () => {
      const payload = Buffer.from('Test');
      const onion = await crypto.buildOnion(payload, []);

      expect(onion).toEqual(payload);
    });

    it('should generate key pair', () => {
      const keyPair = crypto.generateKeyPair();

      expect(keyPair.publicKey).toBeInstanceOf(Buffer);
      expect(keyPair.privateKey).toBeInstanceOf(Buffer);
      expect(keyPair.publicKey.length).toBe(32);
      expect(keyPair.privateKey.length).toBe(32);
    });

    it('should create and verify MAC', () => {
      const data = Buffer.from('Test data');
      const key = Buffer.from('0'.repeat(64), 'hex');

      const mac = crypto.createMAC(data, key);
      expect(mac).toBeInstanceOf(Buffer);

      const isValid = crypto.verifyMAC(data, mac, key);
      expect(isValid).toBe(true);
    });

    it('should detect tampered data with MAC', () => {
      const data = Buffer.from('Test data');
      const key = Buffer.from('0'.repeat(64), 'hex');

      const mac = crypto.createMAC(data, key);

      // Tamper with data
      const tamperedData = Buffer.from('Tampered data');
      const isValid = crypto.verifyMAC(tamperedData, mac, key);
      expect(isValid).toBe(false);
    });
  });
});
