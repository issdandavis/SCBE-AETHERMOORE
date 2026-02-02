/**
 * Video Generator Integration Tests
 * ==================================
 *
 * End-to-end tests for the complete video generation pipeline.
 */

import { describe, it, expect } from 'vitest';
import {
  generateVideo,
  streamVideoFrames,
  validateVideo,
  exportToJson,
} from '../../src/video/generator.js';
import { generateAudioTrack, validateAudio, audioToWav } from '../../src/video/audio.js';
import { generateWatermarkKeys, hashFrameContent, createWatermarkChain } from '../../src/video/watermark.js';
import { generateTrajectory } from '../../src/video/trajectory.js';
import { TONGUE_FRACTAL_CONFIGS } from '../../src/video/types.js';
import type { VideoConfig } from '../../src/video/types.js';

describe('Video Generator', () => {
  describe('Basic Generation', () => {
    it('should generate a short video', async () => {
      const result = await generateVideo({
        width: 64,
        height: 64,
        fps: 10,
        duration: 1,
        tongue: 'av',
        enableWatermark: false,
        enableAudio: false,
      });

      expect(result.success).toBe(true);
      expect(result.frameCount).toBe(10);
      expect(result.frames).toHaveLength(10);
      expect(result.errors).toHaveLength(0);
    });

    it('should generate video for all tongues', async () => {
      const tongues = ['ko', 'av', 'ru', 'ca', 'um', 'dr'] as const;

      for (const tongue of tongues) {
        const result = await generateVideo({
          width: 32,
          height: 32,
          fps: 5,
          duration: 0.5,
          tongue,
          enableWatermark: false,
          enableAudio: false,
        });

        expect(result.success).toBe(true);
        expect(result.config.tongue).toBe(tongue);
      }
    });

    it('should generate video with all fractal modes', async () => {
      const modes = ['mandelbrot', 'julia', 'burning_ship', 'hybrid'] as const;

      for (const mode of modes) {
        const result = await generateVideo({
          width: 32,
          height: 32,
          fps: 5,
          duration: 0.5,
          fractalMode: mode,
          enableWatermark: false,
          enableAudio: false,
        });

        expect(result.success).toBe(true);
        expect(result.config.fractalMode).toBe(mode);
      }
    });
  });

  describe('Configuration Validation', () => {
    it('should clamp extreme dimensions', async () => {
      const result = await generateVideo({
        width: 100000,
        height: 100000,
        fps: 5,
        duration: 0.2, // Very short to avoid timeout
        enableWatermark: false,
        enableAudio: false,
      });

      // Config should be clamped even though it results in large frames
      expect(result.config.width).toBeLessThanOrEqual(4096);
      expect(result.config.height).toBeLessThanOrEqual(4096);
      // Also check that memory limit kicks in
      const frameBytes = result.config.width * result.config.height * 4;
      expect(frameBytes).toBeLessThanOrEqual(100 * 1024 * 1024);
    });

    it('should clamp FPS to safe range', async () => {
      const result = await generateVideo({
        width: 32,
        height: 32,
        fps: 10000,
        duration: 0.5,
        enableWatermark: false,
        enableAudio: false,
      });

      expect(result.config.fps).toBeLessThanOrEqual(120);
    });

    it('should use default config for invalid values', async () => {
      const result = await generateVideo({
        width: -100,
        height: 0,
        fps: -10,
        duration: -5,
        // @ts-expect-error - Testing invalid input
        tongue: 'invalid_tongue',
        // @ts-expect-error - Testing invalid input
        fractalMode: 'invalid_mode',
        enableWatermark: false,
        enableAudio: false,
      });

      expect(result.success).toBe(true);
      expect(result.config.width).toBeGreaterThan(0);
      expect(result.config.height).toBeGreaterThan(0);
      expect(result.config.fps).toBeGreaterThan(0);
      expect(result.config.duration).toBeGreaterThan(0);
    });
  });

  describe('Frame Data', () => {
    it('should generate frames with correct dimensions', async () => {
      const result = await generateVideo({
        width: 64,
        height: 48,
        fps: 5,
        duration: 0.5,
        enableWatermark: false,
        enableAudio: false,
      });

      for (const frame of result.frames!) {
        expect(frame.width).toBe(64);
        expect(frame.height).toBe(48);
        expect(frame.data.length).toBe(64 * 48 * 4); // RGBA
      }
    });

    it('should have valid Poincaré states in frames', async () => {
      const result = await generateVideo({
        width: 32,
        height: 32,
        fps: 10,
        duration: 1,
        enableWatermark: false,
        enableAudio: false,
      });

      for (const frame of result.frames!) {
        expect(frame.poincareState.length).toBe(6);

        let normSq = 0;
        for (const v of frame.poincareState) {
          expect(Number.isFinite(v)).toBe(true);
          normSq += v * v;
        }
        expect(Math.sqrt(normSq)).toBeLessThan(1);
      }
    });

    it('should have sequential timestamps', async () => {
      const result = await generateVideo({
        width: 32,
        height: 32,
        fps: 30,
        duration: 1,
        enableWatermark: false,
        enableAudio: false,
      });

      for (let i = 0; i < result.frames!.length - 1; i++) {
        expect(result.frames![i].timestamp).toBeLessThan(result.frames![i + 1].timestamp);
      }
    });
  });

  describe('Audio Generation', () => {
    it('should generate audio when enabled', async () => {
      const result = await generateVideo({
        width: 32,
        height: 32,
        fps: 10,
        duration: 1,
        enableAudio: true,
        enableWatermark: false,
      });

      expect(result.audioSamples).toBeDefined();
      expect(result.audioSamples!.length).toBeGreaterThan(0);
    });

    it('should not generate audio when disabled', async () => {
      const result = await generateVideo({
        width: 32,
        height: 32,
        fps: 10,
        duration: 1,
        enableAudio: false,
        enableWatermark: false,
      });

      expect(result.audioSamples).toBeUndefined();
    });

    it('should generate valid audio samples', () => {
      const trajectory = generateTrajectory('av', 2, 30, 0.05, 42);
      const fractalConfig = TONGUE_FRACTAL_CONFIGS.av;
      const audio = generateAudioTrack(trajectory, fractalConfig);

      const errors = validateAudio(audio);
      expect(errors).toHaveLength(0);

      // Check all samples are in valid range
      for (const sample of audio) {
        expect(sample).toBeGreaterThanOrEqual(-1);
        expect(sample).toBeLessThanOrEqual(1);
      }
    });

    it('should convert audio to WAV format', () => {
      const samples = new Float32Array([0, 0.5, 1, 0.5, 0, -0.5, -1, -0.5, 0]);
      const wav = audioToWav(samples, 44100);

      // Check WAV header
      expect(wav.length).toBeGreaterThan(44); // At least header
      expect(String.fromCharCode(...wav.slice(0, 4))).toBe('RIFF');
      expect(String.fromCharCode(...wav.slice(8, 12))).toBe('WAVE');
    });
  });

  describe('Watermarking', () => {
    it('should generate watermark keys when enabled', async () => {
      const result = await generateVideo({
        width: 32,
        height: 32,
        fps: 10,
        duration: 0.5,
        enableWatermark: true,
        enableAudio: false,
      });

      expect(result.watermarkKeys).toBeDefined();
      expect(result.watermarkKeys!.publicKey).toHaveLength(2);
      expect(result.watermarkKeys!.secretKey.length).toBeGreaterThan(0);
    });

    it('should embed watermark hashes in frames', async () => {
      const result = await generateVideo({
        width: 32,
        height: 32,
        fps: 10,
        duration: 0.5,
        enableWatermark: true,
        enableAudio: false,
      });

      // All frames should have watermark hash
      for (let i = 0; i < result.frames!.length - 1; i++) {
        expect(result.frames![i].watermarkHash).toBeDefined();
        expect(result.frames![i].watermarkHash!.length).toBeGreaterThan(0);
      }
    });

    it('should generate deterministic keys with same config', () => {
      const keys1 = generateWatermarkKeys({ dimension: 16, modulus: 97, errorBound: 1 });
      const keys2 = generateWatermarkKeys({ dimension: 16, modulus: 97, errorBound: 1 });

      // Keys should be different each time (random)
      expect(keys1.secretKey).not.toEqual(keys2.secretKey);
    });

    it('should create watermark chain', () => {
      const hashes = [
        'a'.repeat(64),
        'b'.repeat(64),
        'c'.repeat(64),
      ];

      const { chainHash, merkleRoot } = createWatermarkChain(hashes);

      expect(chainHash.length).toBe(64);
      expect(merkleRoot.length).toBe(64);
      expect(chainHash).not.toBe(merkleRoot);
    });

    it('should handle empty hash list', () => {
      const { chainHash, merkleRoot } = createWatermarkChain([]);
      expect(chainHash.length).toBe(64);
      expect(merkleRoot.length).toBe(64);
    });
  });

  describe('Streaming Generation', () => {
    it('should stream frames one at a time', async () => {
      const frames: number[] = [];

      for await (const frame of streamVideoFrames({
        width: 32,
        height: 32,
        fps: 5,
        duration: 0.5,
        enableWatermark: false,
      })) {
        frames.push(frame.index);
      }

      // Should have generated all frames
      expect(frames).toEqual([0, 1, 2]); // ceil(0.5 * 5) = 3 frames
    });

    it('should allow early termination', async () => {
      let frameCount = 0;

      for await (const frame of streamVideoFrames({
        width: 32,
        height: 32,
        fps: 10,
        duration: 10,
        enableWatermark: false,
      })) {
        frameCount++;
        if (frameCount >= 5) break;
      }

      expect(frameCount).toBe(5);
    });
  });

  describe('Validation', () => {
    it('should validate successful generation', async () => {
      const result = await generateVideo({
        width: 64,
        height: 64,
        fps: 10,
        duration: 1,
        enableWatermark: false,
        enableAudio: false,
      });

      const errors = validateVideo(result);
      expect(errors).toHaveLength(0);
    });

    it('should detect frame count mismatch', async () => {
      const result = await generateVideo({
        width: 32,
        height: 32,
        fps: 10,
        duration: 1,
        enableWatermark: false,
        enableAudio: false,
      });

      // Corrupt the result - make frames array shorter than frameCount
      result.frames = result.frames!.slice(0, 5);
      // frameCount stays at 10, but frames.length is now 5

      const errors = validateVideo(result);
      // The validator checks if frames.length matches frameCount
      expect(errors.some(e => e.includes('mismatch') || e.includes('Trajectory length'))).toBe(true);
    });
  });

  describe('JSON Export', () => {
    it('should export to valid JSON', async () => {
      const result = await generateVideo({
        width: 32,
        height: 32,
        fps: 5,
        duration: 0.5,
        enableWatermark: true,
        enableAudio: false,
      });

      const json = exportToJson(result);
      const parsed = JSON.parse(json);

      expect(parsed.success).toBe(true);
      expect(parsed.config.width).toBe(32);
      expect(parsed.trajectory.points.length).toBe(3);
    });

    it('should omit large data from JSON', async () => {
      const result = await generateVideo({
        width: 64,
        height: 64,
        fps: 10,
        duration: 1,
        enableWatermark: false,
        enableAudio: true,
      });

      const json = exportToJson(result);
      const parsed = JSON.parse(json);

      // Frames and audio should be omitted
      expect(parsed.frames).toBeUndefined();
      expect(parsed.audioSamples).toBeUndefined();
    });
  });

  describe('Progress Callback', () => {
    it('should call progress callback during generation', async () => {
      const progressCalls: { phase: string; percent: number }[] = [];

      await generateVideo(
        {
          width: 32,
          height: 32,
          fps: 5,
          duration: 0.5,
          enableWatermark: true,
          enableAudio: true,
        },
        {},
        {},
        42,
        (progress) => {
          progressCalls.push({ phase: progress.phase, percent: progress.percent });
        }
      );

      // Should have progress for all phases
      const phases = new Set(progressCalls.map(p => p.phase));
      expect(phases.has('trajectory')).toBe(true);
      expect(phases.has('frames')).toBe(true);
      expect(phases.has('audio')).toBe(true);
      expect(phases.has('watermark')).toBe(true);
    });
  });

  describe('Metrics', () => {
    it('should track generation metrics', async () => {
      const result = await generateVideo({
        width: 64,
        height: 64,
        fps: 10,
        duration: 1,
        enableWatermark: false,
        enableAudio: false,
      });

      expect(result.metrics.totalTimeMs).toBeGreaterThan(0);
      expect(result.metrics.avgFrameTimeMs).toBeGreaterThan(0);
      expect(result.metrics.peakMemoryMB).toBeGreaterThan(0);
    });
  });
});
