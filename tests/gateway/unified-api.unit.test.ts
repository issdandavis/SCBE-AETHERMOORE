/**
 * @file unified-api.unit.test.ts
 * @module gateway/unified-api
 * @layer Layer 1-14
 * @component UnifiedSCBEGateway
 *
 * Unit tests for the central SCBE gateway covering:
 * - Authorization pipeline (14-layer risk decisions)
 * - RWP encode/decode (Six Sacred Tongues)
 * - Swarm coordination
 * - Contact graph routing
 * - Quantum key exchange
 */

import { describe, expect, it, beforeEach } from 'vitest';
import {
  UnifiedSCBEGateway,
  type AuthorizationRequest,
  type AgentState,
  type GatewayConfig,
  type RWPEnvelope,
  type TongueID,
} from '../../src/gateway/unified-api';

// ============================================
// HELPERS
// ============================================

function makeRequest(overrides: Partial<AuthorizationRequest> = {}): AuthorizationRequest {
  return {
    agentId: 'agent-001',
    action: 'read',
    target: 'resource-alpha',
    context: { sensitivity: 0.2, urgency: 0.3 },
    tongues: ['KO', 'RU', 'UM'],
    ...overrides,
  };
}

function makeAgent(overrides: Partial<AgentState> = {}): AgentState {
  return {
    id: `agent-${Math.random().toString(36).slice(2, 6)}`,
    position6D: [0.1, 0.2, 0.3, 0.1, 0.2, 0.3],
    trustScore: 0.9,
    trustLevel: 'HIGH',
    trustVector: [0.9, 0.8, 0.85],
    dimensionalState: 'POLLY',
    nu: 1.0,
    ...overrides,
  };
}

// ============================================
// AUTHORIZATION PIPELINE (L1-L14)
// ============================================

describe('UnifiedSCBEGateway', () => {
  let gateway: UnifiedSCBEGateway;

  beforeEach(() => {
    gateway = new UnifiedSCBEGateway();
  });

  describe('authorization pipeline', () => {
    it('returns a valid AuthorizationResponse structure', async () => {
      const res = await gateway.authorize(makeRequest());

      expect(res).toHaveProperty('decision');
      expect(res).toHaveProperty('decisionId');
      expect(res).toHaveProperty('score');
      expect(res).toHaveProperty('riskFactors');
      expect(res).toHaveProperty('explanation');
      expect(['ALLOW', 'QUARANTINE', 'DENY']).toContain(res.decision);
      expect(typeof res.score).toBe('number');
      expect(res.decisionId).toMatch(/^dec_/);
    });

    it('produces a score in [0, 1] range for normal requests', async () => {
      const res = await gateway.authorize(makeRequest());
      expect(res.score).toBeGreaterThanOrEqual(0);
      expect(res.score).toBeLessThanOrEqual(1);
    });

    it('populates all risk factor fields', async () => {
      const res = await gateway.authorize(makeRequest());
      const rf = res.riskFactors;

      expect(typeof rf.hyperbolicDistance).toBe('number');
      expect(typeof rf.spectralCoherence).toBe('number');
      expect(typeof rf.spinCoherence).toBe('number');
      expect(typeof rf.triadicDistance).toBe('number');
      expect(typeof rf.audioStability).toBe('number');
      expect(typeof rf.harmonicMagnification).toBe('number');
      expect(typeof rf.compositeRisk).toBe('number');
    });

    it('issues a token only on ALLOW decisions', async () => {
      // Use very permissive thresholds to force ALLOW
      const permissive = new UnifiedSCBEGateway({
        riskThresholds: { allow: 1.0, deny: 2.0 },
      });

      const res = await permissive.authorize(makeRequest());
      expect(res.decision).toBe('ALLOW');
      expect(res.token).toBeDefined();
      expect(res.token).toMatch(/^scbe_tok_/);
      expect(res.expiresAt).toBeDefined();
    });

    it('does not issue a token on DENY', async () => {
      // Use very strict thresholds to force DENY
      const strict = new UnifiedSCBEGateway({
        riskThresholds: { allow: 0, deny: 0 },
      });

      const res = await strict.authorize(makeRequest());
      expect(res.decision).toBe('DENY');
      expect(res.token).toBeUndefined();
      expect(res.expiresAt).toBeUndefined();
    });

    it('respects custom risk thresholds', async () => {
      const quarantineGateway = new UnifiedSCBEGateway({
        riskThresholds: { allow: 0, deny: 1.0 },
      });

      const res = await quarantineGateway.authorize(makeRequest());
      // With allow=0, any positive risk should be QUARANTINE (not ALLOW)
      expect(['QUARANTINE', 'DENY']).toContain(res.decision);
    });

    it('provides a layer explanation with all 5 factors', async () => {
      const res = await gateway.authorize(makeRequest());
      const layers = res.explanation!.layers;

      expect(layers).toHaveProperty('hyperbolicDistance');
      expect(layers).toHaveProperty('spectralCoherence');
      expect(layers).toHaveProperty('spinCoherence');
      expect(layers).toHaveProperty('triadicDistance');
      expect(layers).toHaveProperty('audioStability');

      // Each layer result has correct structure
      for (const layerResult of Object.values(layers)) {
        expect(layerResult).toHaveProperty('name');
        expect(layerResult).toHaveProperty('value');
        expect(layerResult).toHaveProperty('contribution');
        expect(layerResult).toHaveProperty('status');
        expect(['pass', 'warn', 'fail']).toContain(layerResult.status);
      }
    });

    it('provides a dominant factor and recommendation', async () => {
      const res = await gateway.authorize(makeRequest());

      expect(typeof res.explanation!.dominantFactor).toBe('string');
      expect(typeof res.explanation!.recommendation).toBe('string');
      expect(res.explanation!.recommendation.length).toBeGreaterThan(0);
    });

    it('generates unique decision IDs', async () => {
      const ids = new Set<string>();
      for (let i = 0; i < 10; i++) {
        const res = await gateway.authorize(makeRequest());
        ids.add(res.decisionId);
      }
      expect(ids.size).toBe(10);
    });

    it('handles request with no optional fields', async () => {
      const minimal: AuthorizationRequest = {
        agentId: 'a',
        action: 'x',
        target: 't',
      };
      const res = await gateway.authorize(minimal);
      expect(['ALLOW', 'QUARANTINE', 'DENY']).toContain(res.decision);
    });
  });

  // ============================================
  // RWP ENCODE / DECODE
  // ============================================

  describe('RWP encode/decode', () => {
    it('encodes and decodes a payload roundtrip', async () => {
      const payload = { message: 'hello', count: 42 };
      const envelope = await gateway.encodeRWP(payload);

      expect(envelope.ver).toBe('2.1');
      expect(envelope.primaryTongue).toBe('KO');
      expect(typeof envelope.payload).toBe('string');
      expect(typeof envelope.nonce).toBe('string');
      expect(typeof envelope.timestamp).toBe('number');

      const decoded = await gateway.decodeRWP(envelope);
      expect(decoded.valid).toBe(true);
      expect(decoded.payload).toEqual(payload);
    });

    it('generates signatures for each requested tongue', async () => {
      const tongues: TongueID[] = ['KO', 'AV', 'DR'];
      const envelope = await gateway.encodeRWP({ data: 1 }, tongues);

      expect(Object.keys(envelope.signatures)).toEqual(expect.arrayContaining(tongues));
      for (const t of tongues) {
        expect(envelope.signatures[t]).toMatch(/^sig_/);
      }
    });

    it('uses default tongues when none specified', async () => {
      const envelope = await gateway.encodeRWP({ data: 1 });
      // Default: KO, RU, UM
      expect(envelope.primaryTongue).toBe('KO');
      expect(Object.keys(envelope.signatures)).toEqual(expect.arrayContaining(['KO', 'RU', 'UM']));
    });

    it('rejects envelope with tampered signature', async () => {
      const envelope = await gateway.encodeRWP({ secret: true });
      envelope.signatures.KO = 'sig_KO_tampered';

      const decoded = await gateway.decodeRWP(envelope);
      expect(decoded.valid).toBe(false);
      expect(decoded.error).toMatch(/Invalid KO signature/);
    });

    it('rejects expired envelope', async () => {
      const envelope = await gateway.encodeRWP({ data: 1 });
      // Make envelope appear 10 minutes old (beyond 5-min window)
      envelope.timestamp = Date.now() - 600000;

      const decoded = await gateway.decodeRWP(envelope);
      expect(decoded.valid).toBe(false);
      expect(decoded.error).toMatch(/expired/i);
    });

    it('includes AAD metadata', async () => {
      const envelope = await gateway.encodeRWP({ data: 1 }, ['CA', 'UM']);
      expect(envelope.aad).toContain('gateway=unified');
      expect(envelope.aad).toContain('CA,UM');
    });
  });

  // ============================================
  // SWARM COORDINATION
  // ============================================

  describe('swarm coordination', () => {
    it('registers agents and retrieves swarm state', async () => {
      const a1 = makeAgent({ id: 'a1' });
      const a2 = makeAgent({ id: 'a2' });

      gateway.registerAgent(a1, 'swarm-1');
      gateway.registerAgent(a2, 'swarm-1');

      const state = await gateway.getSwarmState('swarm-1');
      expect(state.swarmId).toBe('swarm-1');
      expect(state.agents).toHaveLength(2);
      expect(state.coherenceScore).toBeGreaterThan(0);
      expect(['POLLY', 'QUASI', 'DEMI', 'COLLAPSED']).toContain(state.dominantState);
    });

    it('computes trust matrix with correct dimensions', async () => {
      gateway.registerAgent(makeAgent({ id: 'a1' }), 'swarm-2');
      gateway.registerAgent(makeAgent({ id: 'a2' }), 'swarm-2');
      gateway.registerAgent(makeAgent({ id: 'a3' }), 'swarm-2');

      const state = await gateway.getSwarmState('swarm-2');
      expect(state.trustMatrix).toHaveLength(3);
      for (const row of state.trustMatrix) {
        expect(row).toHaveLength(3);
      }
      // Diagonal should be 1
      expect(state.trustMatrix[0][0]).toBe(1);
      expect(state.trustMatrix[1][1]).toBe(1);
      expect(state.trustMatrix[2][2]).toBe(1);
    });

    it('returns empty swarm for unknown swarmId', async () => {
      const state = await gateway.getSwarmState('nonexistent');
      expect(state.agents).toHaveLength(0);
      expect(state.coherenceScore).toBe(1); // Single/empty swarm = perfect coherence
    });

    it('updates agent state', () => {
      const agent = makeAgent({ id: 'updatable', trustScore: 0.5 });
      gateway.registerAgent(agent);

      const updated = gateway.updateAgent('updatable', { trustScore: 0.95 });
      expect(updated).toBe(true);
    });

    it('returns false when updating nonexistent agent', () => {
      expect(gateway.updateAgent('ghost', { trustScore: 0.1 })).toBe(false);
    });

    it('registers agent without swarm', () => {
      const agent = makeAgent({ id: 'lone-wolf' });
      gateway.registerAgent(agent);

      // Should not throw, agent exists but no swarm
      expect(gateway.updateAgent('lone-wolf', { nu: 2.0 })).toBe(true);
    });

    it('computes dominant state from agent populations', async () => {
      gateway.registerAgent(makeAgent({ id: 'q1', dimensionalState: 'QUASI' }), 's');
      gateway.registerAgent(makeAgent({ id: 'q2', dimensionalState: 'QUASI' }), 's');
      gateway.registerAgent(makeAgent({ id: 'p1', dimensionalState: 'POLLY' }), 's');

      const state = await gateway.getSwarmState('s');
      expect(state.dominantState).toBe('QUASI');
    });

    it('coherence decreases with divergent nu values', async () => {
      gateway.registerAgent(makeAgent({ id: 'x1', nu: 1.0 }), 'coh');
      gateway.registerAgent(makeAgent({ id: 'x2', nu: 1.0 }), 'coh');
      const uniform = await gateway.getSwarmState('coh');

      const gw2 = new UnifiedSCBEGateway();
      gw2.registerAgent(makeAgent({ id: 'y1', nu: 0.1 }), 'coh2');
      gw2.registerAgent(makeAgent({ id: 'y2', nu: 10.0 }), 'coh2');
      const divergent = await gw2.getSwarmState('coh2');

      expect(uniform.coherenceScore).toBeGreaterThan(divergent.coherenceScore);
    });
  });

  // ============================================
  // CONTACT GRAPH ROUTING
  // ============================================

  describe('contact graph routing', () => {
    it('rebuilds contact graph from registered agents', () => {
      gateway.registerAgent(makeAgent({ id: 'n1', position6D: [0, 0, 0, 0, 0, 0] }));
      gateway.registerAgent(makeAgent({ id: 'n2', position6D: [0.1, 0.1, 0, 0, 0, 0] }));

      // Should not throw
      gateway.rebuildContactGraph();
    });

    it('findPath returns null for unregistered agents', () => {
      const path = gateway.findPath('unknown-1', 'unknown-2');
      expect(path).toBeNull();
    });
  });

  // ============================================
  // QUANTUM KEY EXCHANGE
  // ============================================

  describe('quantum key exchange', () => {
    it('returns valid key exchange response with ML-KEM-768', async () => {
      const kex = await gateway.initiateQuantumKeyExchange('peer-1');

      expect(kex.sessionId).toMatch(/^qkex_/);
      expect(typeof kex.publicKey).toBe('string');
      expect(kex.publicKey.length).toBeGreaterThan(100);
      expect(kex.algorithm).toBe('ML-KEM-768');
      expect(typeof kex.timestamp).toBe('number');
    });

    it('supports ML-KEM-1024 algorithm', async () => {
      const kex = await gateway.initiateQuantumKeyExchange('peer-2', 'ML-KEM-1024');
      expect(kex.algorithm).toBe('ML-KEM-1024');
      // ML-KEM-1024 key should be larger than ML-KEM-768
      const kex768 = await gateway.initiateQuantumKeyExchange('peer-3', 'ML-KEM-768');
      expect(kex.publicKey.length).toBeGreaterThan(kex768.publicKey.length);
    });

    it('generates unique session IDs', async () => {
      const ids = new Set<string>();
      for (let i = 0; i < 5; i++) {
        const kex = await gateway.initiateQuantumKeyExchange(`peer-${i}`);
        ids.add(kex.sessionId);
      }
      expect(ids.size).toBe(5);
    });
  });

  // ============================================
  // CONFIGURATION
  // ============================================

  describe('configuration', () => {
    it('uses sensible defaults', () => {
      const gw = new UnifiedSCBEGateway();
      // Should not throw — defaults are applied
      expect(gw).toBeDefined();
    });

    it('accepts custom configuration', () => {
      const config: GatewayConfig = {
        scbeEndpoint: 'http://custom:8000',
        riskThresholds: { allow: 0.1, deny: 0.5 },
        defaultTongues: ['DR', 'CA'],
      };
      const gw = new UnifiedSCBEGateway(config);
      expect(gw).toBeDefined();
    });
  });
});
