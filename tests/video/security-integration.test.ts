/**
 * Video-Security Integration Tests
 * =================================
 *
 * Tests for the integration between video generation and the SCBE
 * security/governance layer.
 */

import { describe, it, expect } from 'vitest';
import {
  generateFractalFingerprint,
  verifyFractalFingerprint,
  embedTrajectoryState,
  extractJobTrajectory,
  generateAuditReel,
  createVisualProof,
  verifyVisualProof,
} from '../../src/video/security-integration.js';
import type { AAD, Envelope } from '../../src/crypto/envelope.js';
import type { TrajectoryJobData } from '../../src/video/security-integration.js';
import type { AgentRole } from '../../src/fleet/redis-orchestrator.js';

// Mock AAD for testing
function createMockAAD(overrides: Partial<AAD> = {}): AAD {
  return {
    envelope_version: 'scbe-v1',
    env: 'test',
    provider_id: 'test-provider',
    model_id: 'test-model',
    intent_id: 'test-intent',
    phase: 'request',
    ts: Date.now(),
    ttl: 60000,
    content_type: 'application/json',
    schema_hash: 'a'.repeat(64),
    canonical_body_hash: 'b'.repeat(64),
    request_id: 'c'.repeat(32),
    replay_nonce: 'd'.repeat(32),
    ...overrides,
  };
}

// Mock Envelope for testing
function createMockEnvelope(aadOverrides: Partial<AAD> = {}): Envelope {
  return {
    aad: createMockAAD(aadOverrides),
    kid: 'test-key',
    nonce: 'dGVzdC1ub25jZQ',
    tag: 'dGVzdC10YWc',
    ciphertext: 'dGVzdC1jaXBoZXJ0ZXh0',
    salt: 'dGVzdC1zYWx0',
  };
}

describe('Video-Security Integration', () => {
  describe('Fractal Fingerprinting', () => {
    it('should generate fingerprint from AAD', () => {
      const aad = createMockAAD();
      const fingerprint = generateFractalFingerprint(aad);

      expect(fingerprint.hash).toHaveLength(64);
      expect(fingerprint.width).toBe(64);
      expect(fingerprint.height).toBe(64);
      expect(fingerprint.imageData.length).toBe(64 * 64 * 4);
      expect(fingerprint.poincareState.length).toBe(6);
    });

    it('should generate deterministic fingerprints for same AAD', () => {
      const aad = createMockAAD({ ts: 1000000 });
      const fp1 = generateFractalFingerprint(aad);
      const fp2 = generateFractalFingerprint(aad);

      expect(fp1.hash).toBe(fp2.hash);
      for (let i = 0; i < 6; i++) {
        expect(fp1.poincareState[i]).toBeCloseTo(fp2.poincareState[i], 10);
      }
    });

    it('should generate different fingerprints for different AADs', () => {
      const aad1 = createMockAAD({ provider_id: 'provider-a' });
      const aad2 = createMockAAD({ provider_id: 'provider-b' });

      const fp1 = generateFractalFingerprint(aad1);
      const fp2 = generateFractalFingerprint(aad2);

      expect(fp1.hash).not.toBe(fp2.hash);
    });

    it('should clamp fingerprint size to safe range', () => {
      const aad = createMockAAD();

      const small = generateFractalFingerprint(aad, 1);
      expect(small.width).toBeGreaterThanOrEqual(16);

      const large = generateFractalFingerprint(aad, 10000);
      expect(large.width).toBeLessThanOrEqual(512);
    });

    it('should verify valid fingerprint', () => {
      const aad = createMockAAD({ ts: 1000000 });
      const fingerprint = generateFractalFingerprint(aad);

      expect(verifyFractalFingerprint(fingerprint, aad)).toBe(true);
    });

    it('should reject fingerprint from different AAD', () => {
      const aad1 = createMockAAD({ ts: 1000000, provider_id: 'provider-a' });
      const aad2 = createMockAAD({ ts: 1000000, provider_id: 'provider-b' });

      const fingerprint = generateFractalFingerprint(aad1);

      expect(verifyFractalFingerprint(fingerprint, aad2)).toBe(false);
    });

    it('should map different providers to different tongues', () => {
      // Provider IDs that hash to different tongue indices
      const tongues = new Set<string>();

      for (let i = 0; i < 100; i++) {
        const aad = createMockAAD({ provider_id: `provider-${i}` });
        const fp = generateFractalFingerprint(aad);
        tongues.add(fp.tongue);
      }

      // Should have used multiple tongues
      expect(tongues.size).toBeGreaterThan(1);
    });
  });

  describe('Agent Trajectory Embedding', () => {
    it('should embed trajectory state in job data', () => {
      const job = {
        task: 'implement feature',
        context: { feature: 'auth' },
      };

      const enhanced = embedTrajectoryState(job, 'developer', Date.now());

      expect(enhanced.poincareState).toBeDefined();
      expect(enhanced.poincareState!.length).toBe(6);
      expect(enhanced.trajectoryHistory).toBeDefined();
      expect(enhanced.trajectoryHistory!.length).toBe(1);
    });

    it('should preserve Poincaré state inside ball', () => {
      const job = {
        task: 'security audit',
        context: {},
        requiredCapabilities: ['security'],
      };

      const enhanced = embedTrajectoryState(job, 'security', Date.now());

      let normSq = 0;
      for (const v of enhanced.poincareState!) {
        expect(Number.isFinite(v)).toBe(true);
        normSq += v * v;
      }
      expect(Math.sqrt(normSq)).toBeLessThan(1);
    });

    it('should accumulate trajectory history', () => {
      let job: TrajectoryJobData = {
        task: 'test task',
        context: {},
      };

      // Embed multiple times
      for (let i = 0; i < 5; i++) {
        job = embedTrajectoryState(job, 'developer', Date.now() + i * 1000);
      }

      expect(job.trajectoryHistory!.length).toBe(5);
    });

    it('should limit trajectory history length', () => {
      let job: TrajectoryJobData = {
        task: 'test task',
        context: {},
        maxHistoryLength: 3,
      };

      // Embed more times than max history
      for (let i = 0; i < 10; i++) {
        job = embedTrajectoryState(job, 'developer', Date.now() + i * 1000);
      }

      expect(job.trajectoryHistory!.length).toBe(3);
    });

    it('should map agent roles to tongues', () => {
      const roles: AgentRole[] = ['captain', 'architect', 'researcher', 'developer', 'qa', 'security'];
      const tongues = new Set<string>();

      for (const role of roles) {
        const job = { task: 'test', context: {} };
        const enhanced = embedTrajectoryState(job, role, Date.now());
        tongues.add(enhanced.metadata?.tongue as string);
      }

      // Different roles should use different tongues
      expect(tongues.size).toBeGreaterThan(1);
    });

    it('should extract trajectory from multiple jobs', () => {
      const jobs: TrajectoryJobData[] = [];

      for (let i = 0; i < 5; i++) {
        const job = embedTrajectoryState(
          { task: `task-${i}`, context: {} },
          'developer',
          Date.now() + i * 1000
        );
        jobs.push(job);
      }

      const trajectory = extractJobTrajectory(jobs);
      expect(trajectory.length).toBeGreaterThanOrEqual(5);

      // All points should be in ball
      for (const point of trajectory) {
        let normSq = 0;
        for (const v of point) normSq += v * v;
        expect(Math.sqrt(normSq)).toBeLessThan(1);
      }
    });
  });

  describe('Visual Proof', () => {
    it('should create visual proof from trajectory jobs', () => {
      const jobs: TrajectoryJobData[] = [];

      for (let i = 0; i < 3; i++) {
        jobs.push(embedTrajectoryState(
          { task: `task-${i}`, context: {} },
          'developer',
          1000000 + i * 1000
        ));
      }

      const proof = createVisualProof(jobs, 'av');

      expect(proof.trajectory.length).toBeGreaterThanOrEqual(3);
      expect(proof.tongue).toBe('av');
      expect(proof.proofHash).toHaveLength(64);
      expect(proof.startTime).toBeDefined();
      expect(proof.endTime).toBeDefined();
    });

    it('should verify valid visual proof', () => {
      const jobs: TrajectoryJobData[] = [];

      for (let i = 0; i < 3; i++) {
        jobs.push(embedTrajectoryState(
          { task: `task-${i}`, context: {} },
          'developer',
          1000000 + i * 1000
        ));
      }

      const proof = createVisualProof(jobs, 'av');
      expect(verifyVisualProof(proof)).toBe(true);
    });

    it('should reject tampered visual proof', () => {
      const jobs: TrajectoryJobData[] = [];

      for (let i = 0; i < 3; i++) {
        jobs.push(embedTrajectoryState(
          { task: `task-${i}`, context: {} },
          'developer',
          1000000 + i * 1000
        ));
      }

      const proof = createVisualProof(jobs, 'av');

      // Tamper with trajectory
      proof.trajectory[0][0] = 0.999;

      expect(verifyVisualProof(proof)).toBe(false);
    });

    it('should reject proof with points outside ball', () => {
      const jobs: TrajectoryJobData[] = [];

      for (let i = 0; i < 3; i++) {
        jobs.push(embedTrajectoryState(
          { task: `task-${i}`, context: {} },
          'developer',
          1000000 + i * 1000
        ));
      }

      const proof = createVisualProof(jobs, 'av');

      // Set point outside ball (norm > 1)
      proof.trajectory[0] = [0.8, 0.8, 0.8, 0.8, 0.8, 0.8]; // norm ≈ 1.96

      expect(verifyVisualProof(proof)).toBe(false);
    });

    it('should auto-detect tongue from job metadata', () => {
      const jobs: TrajectoryJobData[] = [];

      for (let i = 0; i < 3; i++) {
        jobs.push(embedTrajectoryState(
          { task: `task-${i}`, context: {} },
          'security', // Maps to 'dr'
          1000000 + i * 1000
        ));
      }

      const proof = createVisualProof(jobs); // No tongue specified

      expect(proof.tongue).toBe('dr');
    });

    it('should throw on empty trajectory', () => {
      expect(() => createVisualProof([])).toThrow('Cannot create visual proof from empty trajectory');
    });
  });

  describe('Audit Reel Generation', () => {
    it('should generate audit reel from envelopes', async () => {
      const envelopes = [
        createMockEnvelope({ ts: 1000000 }),
        createMockEnvelope({ ts: 1001000, provider_id: 'provider-2' }),
        createMockEnvelope({ ts: 1002000, provider_id: 'provider-3' }),
      ];

      const result = await generateAuditReel(envelopes, {
        width: 32,
        height: 32,
        fps: 5,
        duration: 1,
        enableWatermark: false,
        enableAudio: false,
      });

      expect(result.success).toBe(true);
      expect(result.envelopeHashes).toHaveLength(3);
      expect(result.fingerprints).toHaveLength(3);
      expect(result.chainOfCustodyHash).toHaveLength(64);
    });

    it('should throw on empty envelope list', async () => {
      await expect(generateAuditReel([])).rejects.toThrow('Cannot generate audit reel from empty envelope history');
    });

    it('should auto-calculate duration from envelope count', async () => {
      const envelopes = [];
      for (let i = 0; i < 10; i++) {
        envelopes.push(createMockEnvelope({ ts: 1000000 + i * 1000 }));
      }

      const result = await generateAuditReel(envelopes, {
        width: 32,
        height: 32,
        fps: 5,
        enableWatermark: false,
        enableAudio: false,
      });

      // 10 envelopes * 0.5s = 5s duration
      expect(result.config.duration).toBeGreaterThanOrEqual(5);
    });

    it('should select dominant tongue from envelopes', async () => {
      // Create envelopes with provider IDs that hash to specific tongues
      const envelopes = [];
      for (let i = 0; i < 5; i++) {
        envelopes.push(createMockEnvelope({
          ts: 1000000 + i * 1000,
          provider_id: `same-provider-${i % 2}`,
        }));
      }

      const result = await generateAuditReel(envelopes, {
        width: 32,
        height: 32,
        fps: 5,
        duration: 1,
        enableWatermark: false,
        enableAudio: false,
      });

      // Should have selected a valid tongue
      const validTongues = ['ko', 'av', 'ru', 'ca', 'um', 'dr'];
      expect(validTongues).toContain(result.config.tongue);
    });

    it('should generate deterministic results with same envelopes', async () => {
      const envelopes = [
        createMockEnvelope({ ts: 1000000, canonical_body_hash: 'x'.repeat(64) }),
        createMockEnvelope({ ts: 1001000, canonical_body_hash: 'y'.repeat(64) }),
      ];

      const result1 = await generateAuditReel(envelopes, {
        width: 32,
        height: 32,
        fps: 5,
        duration: 1,
        enableWatermark: false,
        enableAudio: false,
      });

      const result2 = await generateAuditReel(envelopes, {
        width: 32,
        height: 32,
        fps: 5,
        duration: 1,
        enableWatermark: false,
        enableAudio: false,
      });

      // Fingerprints should be deterministic (same AADs)
      expect(result1.fingerprints.length).toBe(result2.fingerprints.length);
      for (let i = 0; i < result1.fingerprints.length; i++) {
        expect(result1.fingerprints[i].hash).toBe(result2.fingerprints[i].hash);
      }

      // Envelope hashes should match
      expect(result1.envelopeHashes).toEqual(result2.envelopeHashes);
    });

    it('should enable watermarking by default', async () => {
      const envelopes = [createMockEnvelope()];

      const result = await generateAuditReel(envelopes, {
        width: 32,
        height: 32,
        fps: 5,
        duration: 1,
        enableAudio: false,
      });

      expect(result.watermarkKeys).toBeDefined();
    });
  });

  describe('Integration with Envelope Types', () => {
    it('should handle all AAD fields', () => {
      const aad: AAD = {
        envelope_version: 'scbe-v1',
        env: 'production',
        provider_id: 'anthropic',
        model_id: 'claude-3-opus',
        intent_id: 'chat-completion',
        phase: 'response',
        ts: Date.now(),
        ttl: 300000,
        content_type: 'application/json',
        schema_hash: crypto.randomUUID().replace(/-/g, '') + crypto.randomUUID().replace(/-/g, ''),
        canonical_body_hash: crypto.randomUUID().replace(/-/g, '') + crypto.randomUUID().replace(/-/g, ''),
        request_id: crypto.randomUUID().replace(/-/g, ''),
        replay_nonce: crypto.randomUUID().replace(/-/g, ''),
      };

      const fingerprint = generateFractalFingerprint(aad);

      expect(fingerprint.hash).toHaveLength(64);
      expect(fingerprint.poincareState.length).toBe(6);
    });

    it('should handle special characters in AAD fields', () => {
      const aad = createMockAAD({
        provider_id: 'test/provider:special',
        intent_id: 'intent#with$special@chars',
      });

      // Should not throw
      const fingerprint = generateFractalFingerprint(aad);
      expect(fingerprint).toBeDefined();
    });
  });
});
