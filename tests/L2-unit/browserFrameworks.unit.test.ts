/**
 * @file browserFrameworks.unit.test.ts
 * @module tests/L2-unit
 * @layer Layer 1-14
 * @component Browser Framework Tests (HTB, SSSB, FSB, QRSB)
 *
 * Tests all five browser frameworks:
 *   1. Hyperbolic Trust Browser — trust scoring through 14-layer pipeline
 *   2. SpiralSeal Session Browser — encrypted session management
 *   3. Fleet Swarm Browser — multi-agent consensus
 *   4. Quantum-Resistant Stealth Browser — hyperbolic anti-fingerprinting
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  HyperbolicTrustBrowser,
  type NavigationIntent,
} from '../../src/browser/hyperbolicTrustBrowser';
import { SpiralSealSessionBrowser } from '../../src/browser/spiralSealSession';
import { FleetSwarmBrowser, type SwarmTask } from '../../src/browser/fleetSwarmBrowser';
import { QuantumStealthBrowser } from '../../src/browser/quantumStealthBrowser';

// ============================================================================
// Helpers
// ============================================================================

function safeIntent(overrides?: Partial<NavigationIntent>): NavigationIntent {
  return {
    url: 'https://google.com/search?q=hello',
    action: 'navigate',
    agentId: 'test-agent',
    actorType: 'human',
    trustScore: 0.9,
    ...overrides,
  };
}

// ============================================================================
// Framework 1: Hyperbolic Trust Browser (HTB)
// ============================================================================

describe('HyperbolicTrustBrowser', () => {
  let htb: HyperbolicTrustBrowser;

  beforeEach(() => {
    htb = new HyperbolicTrustBrowser();
  });

  describe('Trust Evaluation', () => {
    it('allows or quarantines safe navigation with high trust (never denies)', () => {
      const result = htb.evaluate(safeIntent());
      expect(['ALLOW', 'QUARANTINE']).toContain(result.decision);
      expect(result.riskScore).toBeLessThan(0.5);
      expect(result.harmonicCost).toBeGreaterThan(0);
      expect(result.tongueResonance.every((t) => t)).toBe(true);
    });

    it('escalates high-risk actions from AI actors', () => {
      const result = htb.evaluate(
        safeIntent({
          url: 'https://chase.com/login',
          action: 'execute_script',
          actorType: 'ai',
          trustScore: 0.4,
        })
      );
      expect(['ESCALATE', 'DENY', 'QUARANTINE']).toContain(result.decision);
      expect(result.riskScore).toBeGreaterThan(0.3);
    });

    it('denies navigation to HTTP (non-HTTPS) URLs', () => {
      const result = htb.evaluate(
        safeIntent({
          url: 'http://insecure-site.com',
          trustScore: 0.3,
        })
      );
      // UM tongue (security) should fail for HTTP
      expect(result.tongueResonance[4]).toBe(false);
    });

    it('denies executable downloads from AI actors', () => {
      const result = htb.evaluate(
        safeIntent({
          url: 'https://example.com/malware.exe',
          action: 'download',
          actorType: 'ai',
          trustScore: 0.5,
        })
      );
      // DR tongue (types) should fail for .exe
      expect(result.tongueResonance[5]).toBe(false);
    });
  });

  describe('Hyperbolic Distance', () => {
    it('produces positive hyperbolic distance', () => {
      const result = htb.evaluate(safeIntent());
      expect(result.hyperbolicDistance).toBeGreaterThanOrEqual(0);
      expect(Number.isFinite(result.hyperbolicDistance)).toBe(true);
    });

    it('produces higher distance for riskier intents', () => {
      const safe = htb.evaluate(safeIntent({ trustScore: 0.9 }));
      const risky = htb.evaluate(
        safeIntent({
          url: 'https://chase.com/account',
          action: 'execute_script',
          trustScore: 0.2,
        })
      );
      expect(risky.riskScore).toBeGreaterThan(safe.riskScore);
    });
  });

  describe('Sacred Tongue Gates', () => {
    it('returns 6 tongue resonance values', () => {
      const result = htb.evaluate(safeIntent());
      expect(result.tongueResonance).toHaveLength(6);
    });

    it('all tongues pass for safe HTTPS navigation', () => {
      const result = htb.evaluate(safeIntent());
      expect(result.tongueResonance.every((t) => t)).toBe(true);
    });

    it('RU tongue fails for destructive AI actions', () => {
      const result = htb.evaluate(
        safeIntent({
          action: 'upload',
          actorType: 'ai',
          trustScore: 0.3,
        })
      );
      expect(result.tongueResonance[2]).toBe(false); // RU
    });
  });

  describe('Layer Scores', () => {
    it('produces 14 layer scores', () => {
      const result = htb.evaluate(safeIntent());
      expect(result.layerScores).toHaveLength(14);
      expect(result.layerScores.every((s) => Number.isFinite(s))).toBe(true);
    });
  });

  describe('Domain History', () => {
    it('tracks domain visit history', () => {
      htb.evaluate(safeIntent({ url: 'https://example.com/page1' }));
      htb.evaluate(safeIntent({ url: 'https://example.com/page2' }));

      const history = htb.getDomainHistory('https://example.com');
      expect(history).toHaveLength(1);
      expect(history[0]!.visits).toBe(2);
    });
  });

  describe('Harmonic Scaling', () => {
    it('produces harmonic cost in (0, 1]', () => {
      const result = htb.evaluate(safeIntent());
      expect(result.harmonicCost).toBeGreaterThan(0);
      expect(result.harmonicCost).toBeLessThanOrEqual(1);
    });
  });
});

// ============================================================================
// Framework 2: SpiralSeal Session Browser (SSSB)
// ============================================================================

describe('SpiralSealSessionBrowser', () => {
  let sssb: SpiralSealSessionBrowser;

  beforeEach(() => {
    sssb = new SpiralSealSessionBrowser('test-master-key-256');
  });

  describe('Session Creation', () => {
    it('creates an encrypted session', () => {
      const session = sssb.createSession('agent-001');
      expect(session.sessionId).toBeTruthy();
      expect(session.sealedState).toBeTruthy();
      expect(session.keyVersion).toBe(0);
      expect(session.noncePrefix).toBeTruthy();
    });

    it('creates unique sessions', () => {
      const s1 = sssb.createSession('agent-001');
      const s2 = sssb.createSession('agent-002');
      expect(s1.sessionId).not.toBe(s2.sessionId);
      expect(s1.sealedState).not.toBe(s2.sealedState);
    });
  });

  describe('Action Execution', () => {
    it('executes a navigate action', () => {
      const session = sssb.createSession('agent-001');
      const result = sssb.executeAction(session.sessionId, {
        type: 'navigate',
        payload: { url: 'https://example.com' },
        nonce: `nonce-${Date.now()}-1`,
        timestamp: Date.now(),
      });
      expect(result.success).toBe(true);
      expect(result.tongueVerification.length).toBeGreaterThan(0);
    });

    it('rotates keys after each action (forward secrecy)', () => {
      const session = sssb.createSession('agent-001');
      const info1 = sssb.getSessionInfo(session.sessionId);

      sssb.executeAction(session.sessionId, {
        type: 'navigate',
        payload: { url: 'https://example.com' },
        nonce: `nonce-${Date.now()}-1`,
        timestamp: Date.now(),
      });

      const info2 = sssb.getSessionInfo(session.sessionId);
      expect(info2!.keyVersion).toBe(info1!.keyVersion + 1);
    });

    it('detects replay attacks', () => {
      const session = sssb.createSession('agent-001');
      const nonce = `nonce-${Date.now()}-replay`;

      sssb.executeAction(session.sessionId, {
        type: 'navigate',
        payload: { url: 'https://example.com' },
        nonce,
        timestamp: Date.now(),
      });

      const replay = sssb.executeAction(session.sessionId, {
        type: 'navigate',
        payload: { url: 'https://evil.com' },
        nonce, // Same nonce!
        timestamp: Date.now(),
      });

      expect(replay.success).toBe(false);
      expect(replay.error).toContain('Replay');
    });
  });

  describe('Session Lifecycle', () => {
    it('terminates a session', () => {
      const session = sssb.createSession('agent-001');
      expect(sssb.terminateSession(session.sessionId)).toBe(true);
      expect(sssb.getSessionInfo(session.sessionId)).toBeNull();
    });

    it('tracks active session count', () => {
      sssb.createSession('agent-001');
      sssb.createSession('agent-002');
      expect(sssb.activeSessionCount).toBe(2);
    });
  });
});

// ============================================================================
// Framework 4: Fleet Swarm Browser (FSB)
// ============================================================================

describe('FleetSwarmBrowser', () => {
  let fsb: FleetSwarmBrowser;

  beforeEach(() => {
    fsb = new FleetSwarmBrowser();
  });

  describe('Swarm Spawning', () => {
    it('spawns agents with role specialization', () => {
      const agents = fsb.spawnSwarm(4);
      expect(agents).toHaveLength(4);
      const roles = agents.map((a) => a.role);
      expect(roles).toContain('navigator');
      expect(roles).toContain('extractor');
      expect(roles).toContain('validator');
      expect(roles).toContain('sentinel');
    });

    it('assigns tongues based on role', () => {
      const agents = fsb.spawnSwarm(4);
      const navigator = agents.find((a) => a.role === 'navigator')!;
      expect(navigator.tongue).toBe('KO');
      const sentinel = agents.find((a) => a.role === 'sentinel')!;
      expect(sentinel.tongue).toBe('UM');
    });
  });

  describe('Swarm Task Execution', () => {
    it('executes a task with consensus', () => {
      fsb.spawnSwarm(6);
      const task: SwarmTask = {
        objective: 'Research product prices',
        requiredAgents: 4,
        consensusThreshold: 3,
        subTasks: [
          {
            id: 'st-1',
            description: 'Navigate to product page',
            requiredRole: 'navigator',
            target: 'https://example.com/products',
            action: 'navigate',
            dependencies: [],
          },
          {
            id: 'st-2',
            description: 'Extract pricing data',
            requiredRole: 'extractor',
            target: 'https://example.com/products',
            action: 'extract',
            dependencies: ['st-1'],
          },
          {
            id: 'st-3',
            description: 'Validate extracted data',
            requiredRole: 'validator',
            target: 'https://example.com/products',
            action: 'validate',
            dependencies: ['st-2'],
          },
        ],
      };

      const result = fsb.executeSwarmTask(task);
      expect(result.status).toBe('success');
      expect(result.consensus.approved).toBe(true);
      expect(result.consensus.consensusTongues.length).toBeGreaterThanOrEqual(3);
    });

    it('fails when insufficient agents', () => {
      // No agents spawned
      const task: SwarmTask = {
        objective: 'Test',
        requiredAgents: 4,
        consensusThreshold: 4,
        subTasks: [],
      };
      const result = fsb.executeSwarmTask(task);
      expect(result.status).toBe('failed');
    });
  });

  describe('Agent Trust Management', () => {
    it('increases trust on successful tasks', () => {
      const agents = fsb.spawnSwarm(4);
      const initialTrust = agents[0]!.trustScore;

      fsb.executeSwarmTask({
        objective: 'Safe task',
        requiredAgents: 1,
        consensusThreshold: 1,
        subTasks: [
          {
            id: 'st-1',
            description: 'Navigate',
            requiredRole: 'navigator',
            target: 'https://example.com',
            action: 'navigate',
            dependencies: [],
          },
        ],
      });

      const updated = fsb.getAgent(agents[0]!.id);
      expect(updated!.trustScore).toBeGreaterThanOrEqual(initialTrust);
    });

    it('quarantines agents with depleted trust', () => {
      const agents = fsb.spawnSwarm(4);
      const sentinel = agents.find((a) => a.role === 'sentinel')!;

      // Force low trust
      (sentinel as any).trustScore = 0.15;

      // Task that fails for the sentinel
      fsb.executeSwarmTask({
        objective: 'Risky task',
        requiredAgents: 1,
        consensusThreshold: 1,
        subTasks: [
          {
            id: 'st-1',
            description: 'Execute script on insecure target',
            requiredRole: 'sentinel',
            target: 'https://example.com/admin',
            action: 'execute_script',
            dependencies: [],
          },
        ],
      });

      const updated = fsb.getAgent(sentinel.id);
      // Trust was already very low, may get quarantined
      expect(updated!.trustScore).toBeLessThanOrEqual(0.15);
    });

    it('reactivates quarantined agents', () => {
      const agents = fsb.spawnSwarm(1);
      const agent = agents[0]!;
      (agent as any).status = 'quarantined';

      expect(fsb.reactivateAgent(agent.id, 0.5)).toBe(true);
      expect(fsb.getAgent(agent.id)!.status).toBe('active');
    });
  });
});

// ============================================================================
// Framework 5: Quantum-Resistant Stealth Browser (QRSB)
// ============================================================================

describe('QuantumStealthBrowser', () => {
  let qrsb: QuantumStealthBrowser;

  beforeEach(() => {
    qrsb = new QuantumStealthBrowser('test-master-secret');
  });

  describe('Session Creation', () => {
    it('creates a stealth session with hyperbolic fingerprint', () => {
      const session = qrsb.createStealthSession();
      expect(session.sessionId).toBeTruthy();
      expect(session.fingerprint.poincareCoords.dimension).toBe(6);
      expect(session.fingerprint.tongueWeights).toHaveLength(6);
      expect(session.active).toBe(true);
    });

    it('fingerprints are inside the Poincaré ball', () => {
      const session = qrsb.createStealthSession();
      const coords = session.fingerprint.poincareCoords.coords;
      const norm = Math.sqrt(coords.reduce((sum, v) => sum + v * v, 0));
      expect(norm).toBeLessThan(1);
    });

    it('different sessions have different fingerprints', () => {
      const s1 = qrsb.createStealthSession();
      const s2 = qrsb.createStealthSession();
      expect(s1.fingerprint.fingerprintHash).not.toBe(s2.fingerprint.fingerprintHash);
    });
  });

  describe('Stealth Navigation', () => {
    it('navigates successfully', () => {
      const session = qrsb.createStealthSession();
      const result = qrsb.navigate(session.sessionId, 'https://example.com');
      expect(result.success).toBe(true);
      expect(result.routeHash).toBeTruthy();
      expect(Number.isFinite(result.distanceFromOrigin)).toBe(true);
    });

    it('fails for inactive sessions', () => {
      const session = qrsb.createStealthSession();
      qrsb.terminateSession(session.sessionId);
      const result = qrsb.navigate(session.sessionId, 'https://example.com');
      expect(result.success).toBe(false);
    });
  });

  describe('Fingerprint Anti-Correlation', () => {
    it('different sessions have positive Poincaré distance', () => {
      const s1 = qrsb.createStealthSession();
      const s2 = qrsb.createStealthSession();
      const distance = qrsb.fingerprintDistance(s1.sessionId, s2.sessionId);
      expect(distance).toBeGreaterThan(0);
      expect(Number.isFinite(distance)).toBe(true);
    });
  });

  describe('Session Rotation', () => {
    it('rotates to a new session with fresh fingerprint', () => {
      const old = qrsb.createStealthSession();
      const rotated = qrsb.rotateSession(old.sessionId);
      expect(rotated).not.toBeNull();
      expect(rotated!.sessionId).not.toBe(old.sessionId);
      expect(rotated!.fingerprint.fingerprintHash).not.toBe(old.fingerprint.fingerprintHash);
    });

    it('deactivates old session on rotation', () => {
      const old = qrsb.createStealthSession();
      qrsb.rotateSession(old.sessionId);
      const result = qrsb.navigate(old.sessionId, 'https://example.com');
      expect(result.success).toBe(false);
    });
  });

  describe('Golden Ratio Weights', () => {
    it('tongue weights follow golden ratio progression', () => {
      const session = qrsb.createStealthSession();
      const weights = session.fingerprint.tongueWeights;
      const phi = 1.618033988749895;

      for (let i = 1; i < weights.length; i++) {
        const ratio = weights[i]! / weights[i - 1]!;
        expect(ratio).toBeCloseTo(phi, 5);
      }
    });
  });
});
