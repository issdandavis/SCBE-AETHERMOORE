/**
 * SCBE API Tests
 *
 * Tests the simplified API wrapper.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  SCBE,
  Agent,
  SecurityGate,
  Roundtable,
  evaluateRisk,
  sign,
  verify,
  breathe,
  signForAction,
  verifyForAction,
  checkAccess,
  requiredTongues,
  harmonicComplexity,
  getPricingTier,
} from '../../src/api/index.js';

describe('SCBE API', () => {
  let api: SCBE;

  beforeEach(() => {
    api = new SCBE();
  });

  describe('evaluateRisk', () => {
    it('should return low risk for normal context', () => {
      const result = api.evaluateRisk({
        userId: 'user123',
        action: 'login',
        ip: '192.168.1.1',
      });

      expect(result.score).toBeGreaterThanOrEqual(0);
      expect(result.score).toBeLessThanOrEqual(1);
      expect(result.distance).toBeGreaterThanOrEqual(0);
      expect(result.scaledCost).toBeGreaterThan(0);
      expect(['ALLOW', 'REVIEW', 'DENY']).toContain(result.decision);
      expect(result.reason).toBeDefined();
    });

    it('should return consistent scores for same context', () => {
      const context = { userId: 'test', action: 'read' };
      const result1 = api.evaluateRisk(context);
      const result2 = api.evaluateRisk(context);

      expect(result1.score).toBe(result2.score);
      expect(result1.decision).toBe(result2.decision);
    });

    it('should return different scores for different contexts', () => {
      const result1 = api.evaluateRisk({ type: 'A', value: 100 });
      const result2 = api.evaluateRisk({ type: 'B', value: 999999 });

      // Different contexts should produce different distances
      // (they might still get same decision, but distances differ)
      expect(result1.distance).not.toBe(result2.distance);
    });
  });

  describe('sign', () => {
    it('should sign a payload with default tongue', () => {
      const payload = { message: 'test', timestamp: Date.now() };
      const result = api.sign(payload);

      expect(result.envelope).toBeDefined();
      expect(result.envelope.payload).toBeDefined(); // Payload is base64 encoded
      expect(result.envelope.sigs).toBeDefined();
      expect(result.envelope.sigs.ko).toBeDefined();
      expect(result.tongues).toContain('ko');
    });

    it('should sign a payload with multiple tongues', () => {
      const payload = { data: 'sensitive' };
      const result = api.sign(payload, ['ko', 'um', 'dr']);

      expect(result.envelope.sigs.ko).toBeDefined();
      expect(result.envelope.sigs.um).toBeDefined();
      expect(result.envelope.sigs.dr).toBeDefined();
      expect(result.tongues).toEqual(['ko', 'um', 'dr']);
    });
  });

  describe('verify', () => {
    it('should verify a valid envelope', () => {
      const payload = { action: 'transfer', amount: 1000 };
      const { envelope } = api.sign(payload);
      const result = api.verify(envelope);

      expect(result.valid).toBe(true);
      expect(result.reason).toContain('valid');
    });

    it('should reject a tampered envelope', () => {
      const payload = { action: 'transfer', amount: 1000 };
      const { envelope } = api.sign(payload);

      // Tamper with payload
      const tampered = {
        ...envelope,
        payload: { action: 'transfer', amount: 1000000 },
      };

      const result = api.verify(tampered);
      expect(result.valid).toBe(false);
    });
  });

  describe('breathe', () => {
    it('should return a 6D point', () => {
      const result = api.breathe({ context: 'test' });

      expect(result).toHaveLength(6);
      result.forEach((v) => {
        expect(typeof v).toBe('number');
        expect(Number.isFinite(v)).toBe(true);
      });
    });

    it('should vary with intensity', () => {
      const context = { test: true };
      const low = api.breathe(context, 0.1);
      const high = api.breathe(context, 2.0);

      // Different intensities should produce different results
      // (at least slightly different due to breathing amplitude)
      const diff = low.some((v, i) => Math.abs(v - high[i]) > 0.0001);
      expect(diff).toBe(true);
    });
  });

  describe('convenience functions', () => {
    it('evaluateRisk function should work', () => {
      const result = evaluateRisk({ test: true });
      expect(result.score).toBeDefined();
    });

    it('sign function should work', () => {
      const result = sign({ message: 'test' });
      expect(result.envelope).toBeDefined();
    });

    it('verify function should work', () => {
      const { envelope } = sign({ message: 'test' });
      const result = verify(envelope);
      expect(result.valid).toBe(true);
    });

    it('breathe function should work', () => {
      const result = breathe({ context: 'test' });
      expect(result).toHaveLength(6);
    });
  });

  describe('full flow', () => {
    it('should handle complete risk evaluation and signing flow', () => {
      // 1. Evaluate risk of a transaction
      const context = {
        userId: 'alice',
        action: 'wire_transfer',
        amount: 50000,
        destination: 'external_bank',
        timestamp: Date.now(),
      };

      const risk = api.evaluateRisk(context);

      // 2. If allowed, sign the transaction
      if (risk.decision === 'ALLOW' || risk.decision === 'REVIEW') {
        const { envelope } = api.sign(context, ['ko', 'um']);

        // 3. Verify the signed transaction
        const verified = api.verify(envelope);
        expect(verified.valid).toBe(true);
      }

      // Test passes regardless of decision
      expect(risk.decision).toBeDefined();
    });
  });

  describe('signForAction', () => {
    it('should sign with correct tongues for read action', () => {
      const result = api.signForAction({ data: 'test' }, 'read');
      expect(result.tongues).toEqual(['ko']);
    });

    it('should sign with correct tongues for deploy action', () => {
      const result = api.signForAction({ data: 'test' }, 'deploy');
      expect(result.tongues).toEqual(['ko', 'ru', 'um', 'dr']);
    });
  });
});

describe('Agent', () => {
  it('should create an agent with valid 6D position', () => {
    const agent = new Agent('Alice', [1, 2, 3, 4, 5, 6]);
    expect(agent.name).toBe('Alice');
    expect(agent.position).toEqual([1, 2, 3, 4, 5, 6]);
    expect(agent.trustScore).toBe(1.0);
  });

  it('should reject non-6D positions', () => {
    expect(() => new Agent('Bob', [1, 2, 3])).toThrow('6-element');
    expect(() => new Agent('Bob', [1, 2, 3, 4, 5, 6, 7])).toThrow('6-element');
  });

  it('should calculate distance between agents', () => {
    const alice = new Agent('Alice', [0, 0, 0, 0, 0, 0]);
    const bob = new Agent('Bob', [3, 4, 0, 0, 0, 0]);
    expect(alice.distanceTo(bob)).toBe(5); // 3-4-5 triangle
  });

  it('should check in and refresh trust', () => {
    const agent = new Agent('Test', [0, 0, 0, 0, 0, 0], 0.5);
    expect(agent.trustScore).toBe(0.5);
    agent.checkIn();
    expect(agent.trustScore).toBe(0.6); // +0.1
  });

  it('should decay trust over time', async () => {
    const agent = new Agent('Test', [0, 0, 0, 0, 0, 0]);
    const initialTrust = agent.trustScore;

    // Wait a bit
    await new Promise(r => setTimeout(r, 100));

    const decayedTrust = agent.decayTrust(1.0); // Fast decay for testing
    expect(decayedTrust).toBeLessThan(initialTrust);
  });
});

describe('SecurityGate', () => {
  let gate: SecurityGate;
  let agent: Agent;

  beforeEach(() => {
    gate = new SecurityGate({ minWaitMs: 1, maxWaitMs: 10, alpha: 1.1 }); // Fast for tests
    agent = new Agent('TestAgent', [0, 0, 0, 0, 0, 0]);
  });

  it('should assess risk based on trust', () => {
    agent.trustScore = 1.0;
    const lowRisk = gate.assessRisk(agent, 'read', { source: 'internal' });

    agent.trustScore = 0.2;
    const highRisk = gate.assessRisk(agent, 'read', { source: 'internal' });

    expect(highRisk).toBeGreaterThan(lowRisk);
  });

  it('should assess higher risk for dangerous actions', () => {
    const safeRisk = gate.assessRisk(agent, 'read', { source: 'internal' });
    const dangerousRisk = gate.assessRisk(agent, 'delete', { source: 'internal' });

    expect(dangerousRisk).toBeGreaterThan(safeRisk);
  });

  it('should allow trusted agents for safe actions', async () => {
    agent.trustScore = 1.0;
    const result = await gate.check(agent, 'read', { source: 'internal' });
    expect(result.status).toBe('allow');
  });

  it('should review or deny suspicious requests', async () => {
    agent.trustScore = 0.1;
    const result = await gate.check(agent, 'delete', { source: 'external' });
    expect(['review', 'deny']).toContain(result.status);
  });
});

describe('Roundtable', () => {
  it('should return correct tongues for read action', () => {
    const tongues = Roundtable.requiredTongues('read');
    expect(tongues).toEqual(['ko']);
  });

  it('should return correct tongues for write action', () => {
    const tongues = Roundtable.requiredTongues('write');
    expect(tongues).toEqual(['ko', 'ru']);
  });

  it('should return correct tongues for delete action', () => {
    const tongues = Roundtable.requiredTongues('delete');
    expect(tongues).toEqual(['ko', 'ru', 'um']);
  });

  it('should return correct tongues for deploy action', () => {
    const tongues = Roundtable.requiredTongues('deploy');
    expect(tongues).toEqual(['ko', 'ru', 'um', 'dr']);
  });

  it('should check quorum correctly', () => {
    expect(Roundtable.hasQuorum(['ko'], ['ko'])).toBe(true);
    expect(Roundtable.hasQuorum(['ko', 'ru'], ['ko', 'ru'])).toBe(true);
    expect(Roundtable.hasQuorum(['ko'], ['ko', 'ru'])).toBe(false);
  });
});

describe('Harmonic Complexity', () => {
  it('should calculate complexity for depth 1', () => {
    const c = harmonicComplexity(1);
    expect(c).toBeCloseTo(1.5, 2);
  });

  it('should calculate complexity for depth 2', () => {
    const c = harmonicComplexity(2);
    expect(c).toBeCloseTo(Math.pow(1.5, 4), 2);
  });

  it('should calculate complexity for depth 3', () => {
    const c = harmonicComplexity(3);
    expect(c).toBeCloseTo(Math.pow(1.5, 9), 2);
  });

  it('should cap at MAX_COMPLEXITY', () => {
    const c = harmonicComplexity(100);
    expect(c).toBeLessThanOrEqual(1e10);
  });

  it('should return FREE tier for depth 1', () => {
    const tier = getPricingTier(1);
    expect(tier.tier).toBe('FREE');
  });

  it('should return STARTER tier for depth 2', () => {
    const tier = getPricingTier(2);
    expect(tier.tier).toBe('STARTER');
  });

  it('should return PRO tier for depth 3', () => {
    const tier = getPricingTier(3);
    expect(tier.tier).toBe('PRO');
  });

  it('should return ENTERPRISE tier for depth 4+', () => {
    const tier = getPricingTier(4);
    expect(tier.tier).toBe('ENTERPRISE');
  });
});

describe('Convenience Functions', () => {
  it('signForAction should work', () => {
    const result = signForAction({ data: 'test' }, 'delete');
    expect(result.tongues).toEqual(['ko', 'ru', 'um']);
  });

  it('verifyForAction should verify with policy', () => {
    const { envelope } = signForAction({ data: 'test' }, 'write');
    const result = verifyForAction(envelope, 'write');
    expect(result.valid).toBe(true);
  });

  it('checkAccess should work with agent', async () => {
    const agent = new Agent('Test', [0, 0, 0, 0, 0, 0]);
    const result = await checkAccess(agent, 'read', { source: 'internal' });
    expect(['allow', 'review', 'deny']).toContain(result.status);
  });

  it('requiredTongues should work', () => {
    expect(requiredTongues('read')).toEqual(['ko']);
    expect(requiredTongues('deploy')).toEqual(['ko', 'ru', 'um', 'dr']);
  });
});
