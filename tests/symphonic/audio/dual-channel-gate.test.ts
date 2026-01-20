/**
 * Dual-Channel Consensus Gate Tests
 * 
 * Part of SCBE-AETHERMOORE v3.0.0
 * Patent: USPTO #63/961,403
 */

import * as crypto from 'crypto';
import { describe, expect, it } from 'vitest';
import {
    DualChannelGate,
    PROFILE_16K,
    PROFILE_44K,
    PROFILE_48K,
    computeProjections,
    generateWatermark,
    selectBinsAndPhases,
    verifyWatermark
} from '../../../src/symphonic/audio';

describe('Dual-Channel Consensus Gate', () => {
  describe('Bin Selection', () => {
    it('should select correct number of bins', () => {
      const seed = crypto.randomBytes(32);
      const { bins, phases } = selectBinsAndPhases(seed, 32, 100, 1000, 10);
      
      expect(bins).toHaveLength(32);
      expect(phases).toHaveLength(32);
    });

    it('should enforce minimum spacing', () => {
      const seed = crypto.randomBytes(32);
      const { bins } = selectBinsAndPhases(seed, 32, 100, 1000, 10);
      
      for (let i = 0; i < bins.length; i++) {
        for (let j = i + 1; j < bins.length; j++) {
          expect(Math.abs(bins[i] - bins[j])).toBeGreaterThanOrEqual(10);
        }
      }
    });

    it('should be deterministic from seed', () => {
      const seed = crypto.randomBytes(32);
      const result1 = selectBinsAndPhases(seed, 32, 100, 1000, 10);
      const result2 = selectBinsAndPhases(seed, 32, 100, 1000, 10);
      
      expect(result1.bins).toEqual(result2.bins);
      expect(result1.phases).toEqual(result2.phases);
    });
  });

  describe('Watermark Generation', () => {
    it('should generate watermark of correct length', () => {
      const challenge = new Uint8Array(32).fill(0);
      const bins = Array.from({ length: 32 }, (_, i) => 100 + i * 20);
      const phases = Array.from({ length: 32 }, () => Math.random() * 2 * Math.PI);
      
      const waveform = generateWatermark(challenge, bins, phases, 4096, 0.02);
      
      expect(waveform).toHaveLength(4096);
    });

    it('should respect gamma scaling', () => {
      const challenge = new Uint8Array(32).fill(0);
      const bins = Array.from({ length: 32 }, (_, i) => 100 + i * 20);
      const phases = Array.from({ length: 32 }, () => 0);
      
      const waveform1 = generateWatermark(challenge, bins, phases, 4096, 0.01);
      const waveform2 = generateWatermark(challenge, bins, phases, 4096, 0.02);
      
      // Second should be roughly 2x larger
      const max1 = Math.max(...Array.from(waveform1).map(Math.abs));
      const max2 = Math.max(...Array.from(waveform2).map(Math.abs));
      
      expect(max2 / max1).toBeCloseTo(2, 0);
    });

    it('should encode challenge in phase signs', () => {
      const challenge1 = new Uint8Array(32).fill(0);
      const challenge2 = new Uint8Array(32).fill(1);
      const bins = Array.from({ length: 32 }, (_, i) => 100 + i * 20);
      const phases = Array.from({ length: 32 }, () => 0);
      
      const waveform1 = generateWatermark(challenge1, bins, phases, 4096, 0.02);
      const waveform2 = generateWatermark(challenge2, bins, phases, 4096, 0.02);
      
      // Should be negatives of each other
      for (let i = 0; i < 100; i++) {
        expect(waveform1[i]).toBeCloseTo(-waveform2[i], 5);
      }
    });
  });

  describe('Matched Filter Verification', () => {
    it('should compute correct projections', () => {
      const challenge = new Uint8Array(32).fill(0);
      const bins = Array.from({ length: 32 }, (_, i) => 100 + i * 20);
      const phases = Array.from({ length: 32 }, () => 0);
      
      const watermark = generateWatermark(challenge, bins, phases, 4096, 0.02);
      const projections = computeProjections(watermark, bins, phases, 4096);
      
      expect(projections).toHaveLength(32);
      // All projections should be positive (challenge = 0 → sign = +1)
      projections.forEach(p => expect(p).toBeGreaterThan(0));
    });

    it('should verify correct watermark', () => {
      const challenge = new Uint8Array(32).fill(0);
      const bins = Array.from({ length: 32 }, (_, i) => 100 + i * 20);
      const phases = Array.from({ length: 32 }, () => 0);
      
      // Use higher gamma for clean test
      const testProfile = { ...PROFILE_16K, gamma: 0.1 };
      const watermark = generateWatermark(challenge, bins, phases, 4096, testProfile.gamma);
      const result = verifyWatermark(watermark, challenge, bins, phases, testProfile);
      
      expect(result.passed).toBe(true);
      expect(result.correlation).toBeGreaterThan(0);
      
      // Verify correlation is close to expected
      const expected = testProfile.gamma * Math.sqrt(testProfile.b);
      expect(result.correlation).toBeCloseTo(expected, 1);
    });

    it('should reject wrong challenge', () => {
      const challenge1 = new Uint8Array(32).fill(0);
      const challenge2 = new Uint8Array(32).fill(1);
      const bins = Array.from({ length: 32 }, (_, i) => 100 + i * 20);
      const phases = Array.from({ length: 32 }, () => 0);
      
      const watermark = generateWatermark(challenge1, bins, phases, 4096, 0.02);
      const result = verifyWatermark(watermark, challenge2, bins, phases, PROFILE_16K);
      
      expect(result.passed).toBe(false);
      expect(result.correlation).toBeLessThan(0);
    });

    it('should detect clipping', () => {
      const challenge = new Uint8Array(32).fill(0);
      const bins = Array.from({ length: 32 }, (_, i) => 100 + i * 20);
      const phases = Array.from({ length: 32 }, () => 0);
      
      const audio = new Float32Array(4096);
      audio[100] = 0.99; // Above clip threshold
      
      const result = verifyWatermark(audio, challenge, bins, phases, PROFILE_16K);
      
      expect(result.clipped).toBe(true);
      expect(result.passed).toBe(false);
    });
  });

  describe('DualChannelGate', () => {
    it('should generate valid challenges', () => {
      const K = crypto.randomBytes(32);
      const gate = new DualChannelGate(PROFILE_16K, K);
      
      const challenge = gate.generateChallenge();
      
      expect(challenge).toHaveLength(PROFILE_16K.b);
      challenge.forEach(bit => expect([0, 1]).toContain(bit));
    });

    it('should accept valid request', () => {
      const K = crypto.randomBytes(32);
      const gate = new DualChannelGate(PROFILE_16K, K, 60);
      
      const challenge = gate.generateChallenge();
      const timestamp = Date.now() / 1000;
      const nonce = crypto.randomBytes(16).toString('hex');
      const AAD = Buffer.from('test');
      const payload = Buffer.from('payload');
      
      // Generate crypto tag
      const C = Buffer.concat([
        Buffer.from('scbe.v1'),
        AAD,
        Buffer.from(timestamp.toString()),
        Buffer.from(nonce),
        payload
      ]);
      const tag = crypto.createHmac('sha256', K).update(C).digest();
      
      // Generate audio with watermark
      const seed = crypto.createHmac('sha256', K)
        .update(Buffer.from('bins'))
        .update(Buffer.from(timestamp.toString()))
        .update(Buffer.from(nonce))
        .update(Buffer.from(challenge))
        .digest();
      
      const { bins, phases } = selectBinsAndPhases(
        seed,
        PROFILE_16K.b,
        PROFILE_16K.k_min,
        PROFILE_16K.k_max,
        PROFILE_16K.delta_k_min
      );
      
      const watermark = generateWatermark(challenge, bins, phases, PROFILE_16K.N, 0.1); // Higher gamma
      const audio = new Float32Array(PROFILE_16K.N);
      for (let i = 0; i < audio.length; i++) {
        audio[i] = watermark[i]; // Pure watermark for test
      }
      
      const result = gate.verify({
        AAD,
        payload,
        timestamp,
        nonce,
        tag,
        audio,
        challenge
      });
      
      expect(result).toBe('ALLOW');
    });

    it('should deny replay attack', () => {
      const K = crypto.randomBytes(32);
      const gate = new DualChannelGate(PROFILE_16K, K, 60);
      
      const challenge = gate.generateChallenge();
      const timestamp = Date.now() / 1000;
      const nonce = crypto.randomBytes(16).toString('hex');
      const AAD = Buffer.from('test');
      const payload = Buffer.from('payload');
      
      const C = Buffer.concat([
        Buffer.from('scbe.v1'),
        AAD,
        Buffer.from(timestamp.toString()),
        Buffer.from(nonce),
        payload
      ]);
      const tag = crypto.createHmac('sha256', K).update(C).digest();
      
      const seed = crypto.createHmac('sha256', K)
        .update(Buffer.from('bins'))
        .update(Buffer.from(timestamp.toString()))
        .update(Buffer.from(nonce))
        .update(Buffer.from(challenge))
        .digest();
      
      const { bins, phases } = selectBinsAndPhases(
        seed,
        PROFILE_16K.b,
        PROFILE_16K.k_min,
        PROFILE_16K.k_max,
        PROFILE_16K.delta_k_min
      );
      
      const watermark = generateWatermark(challenge, bins, phases, PROFILE_16K.N, 0.1); // Higher gamma
      const audio = new Float32Array(PROFILE_16K.N);
      for (let i = 0; i < audio.length; i++) {
        audio[i] = watermark[i];
      }
      
      // First attempt should succeed
      const result1 = gate.verify({
        AAD,
        payload,
        timestamp,
        nonce,
        tag,
        audio,
        challenge
      });
      expect(result1).toBe('ALLOW');
      
      // Replay should fail (same nonce)
      const result2 = gate.verify({
        AAD,
        payload,
        timestamp,
        nonce,
        tag,
        audio,
        challenge
      });
      expect(result2).toBe('DENY');
    });

    it('should quarantine wrong audio', () => {
      const K = crypto.randomBytes(32);
      const gate = new DualChannelGate(PROFILE_16K, K, 60);
      
      const challenge = gate.generateChallenge();
      const timestamp = Date.now() / 1000;
      const nonce = crypto.randomBytes(16).toString('hex');
      const AAD = Buffer.from('test');
      const payload = Buffer.from('payload');
      
      const C = Buffer.concat([
        Buffer.from('scbe.v1'),
        AAD,
        Buffer.from(timestamp.toString()),
        Buffer.from(nonce),
        payload
      ]);
      const tag = crypto.createHmac('sha256', K).update(C).digest();
      
      // Wrong audio (random noise)
      const audio = new Float32Array(PROFILE_16K.N);
      for (let i = 0; i < audio.length; i++) {
        audio[i] = 0.01 * (Math.random() - 0.5);
      }
      
      const result = gate.verify({
        AAD,
        payload,
        timestamp,
        nonce,
        tag,
        audio,
        challenge
      });
      
      expect(result).toBe('QUARANTINE');
    });

    it('should deny expired timestamp', () => {
      const K = crypto.randomBytes(32);
      const gate = new DualChannelGate(PROFILE_16K, K, 60);
      
      const challenge = gate.generateChallenge();
      const timestamp = Date.now() / 1000 - 120; // 2 minutes ago
      const nonce = crypto.randomBytes(16).toString('hex');
      const AAD = Buffer.from('test');
      const payload = Buffer.from('payload');
      
      const C = Buffer.concat([
        Buffer.from('scbe.v1'),
        AAD,
        Buffer.from(timestamp.toString()),
        Buffer.from(nonce),
        payload
      ]);
      const tag = crypto.createHmac('sha256', K).update(C).digest();
      
      const audio = new Float32Array(PROFILE_16K.N);
      
      const result = gate.verify({
        AAD,
        payload,
        timestamp,
        nonce,
        tag,
        audio,
        challenge
      });
      
      expect(result).toBe('DENY');
    });
  });

  describe('Audio Profiles', () => {
    it('should have valid 16K profile', () => {
      expect(PROFILE_16K.SR).toBe(16000);
      expect(PROFILE_16K.N).toBe(4096);
      expect(PROFILE_16K.b).toBe(32);
      expect(PROFILE_16K.betaFactor).toBeGreaterThan(0);
      expect(PROFILE_16K.betaFactor).toBeLessThan(1);
    });

    it('should have valid 44K profile', () => {
      expect(PROFILE_44K.SR).toBe(44100);
      expect(PROFILE_44K.N).toBe(8192);
      expect(PROFILE_44K.b).toBe(48);
      expect(PROFILE_44K.betaFactor).toBeGreaterThan(0);
      expect(PROFILE_44K.betaFactor).toBeLessThan(1);
    });

    it('should have valid 48K profile', () => {
      expect(PROFILE_48K.SR).toBe(48000);
      expect(PROFILE_48K.N).toBe(8192);
      expect(PROFILE_48K.b).toBe(64);
      expect(PROFILE_48K.betaFactor).toBeGreaterThan(0);
      expect(PROFILE_48K.betaFactor).toBeLessThan(1);
    });
  });
});
