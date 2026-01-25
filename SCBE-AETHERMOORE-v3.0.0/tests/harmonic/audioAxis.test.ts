/**
 * SCBE Audio Axis Tests (Layer 14)
 *
 * Tests for FFT-based telemetry:
 * - Ea = log(ε + Σₙ a[n]²) — Frame energy
 * - Ca = (Σₖ fₖ·Pₐ[k]) / (Σₖ Pₐ[k]) — Spectral centroid
 * - Fa = Σₖ (√Pₐ[k] - √Pₐ_prev[k])² — Spectral flux
 * - rHF,a = Σₖ∈Khigh Pₐ[k] / Σₖ Pₐ[k] — High-frequency ratio
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  AudioAxisProcessor,
  generateTestSignal,
  generateNoise,
  type AudioFeatures,
  type AudioAxisConfig,
} from '../../src/harmonic/audioAxis.js';

describe('AudioAxisProcessor', () => {
  let processor: AudioAxisProcessor;

  beforeEach(() => {
    processor = new AudioAxisProcessor();
  });

  // ═══════════════════════════════════════════════════════════════
  // Configuration Tests
  // ═══════════════════════════════════════════════════════════════
  describe('Configuration', () => {
    it('uses default configuration', () => {
      const config = processor.getConfig();
      expect(config.sampleRate).toBe(44100);
      expect(config.fftSize).toBe(2048);
      expect(config.hfCutoff).toBe(0.5);
      expect(config.riskWeight).toBe(0.1);
    });

    it('accepts custom configuration', () => {
      const customConfig: AudioAxisConfig = {
        sampleRate: 48000,
        fftSize: 4096,
        hfCutoff: 0.7,
        riskWeight: 0.2,
      };
      const customProcessor = new AudioAxisProcessor(customConfig);
      const config = customProcessor.getConfig();

      expect(config.sampleRate).toBe(48000);
      expect(config.fftSize).toBe(4096);
      expect(config.hfCutoff).toBe(0.7);
      expect(config.riskWeight).toBe(0.2);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Energy Tests
  // ═══════════════════════════════════════════════════════════════
  describe('Frame Energy (Ea)', () => {
    it('computes energy for sine wave', () => {
      const signal = generateTestSignal(440, 0.1, 44100);
      const features = processor.processFrame(signal);

      // Sine wave with amplitude 1 has energy ~N/2
      expect(features.energy).toBeGreaterThan(0);
      expect(Number.isFinite(features.energy)).toBe(true);
    });

    it('energy increases with amplitude', () => {
      const lowAmp = generateTestSignal(440, 0.05, 44100).map(x => x * 0.5);
      const highAmp = generateTestSignal(440, 0.05, 44100);

      processor.reset();
      const lowFeatures = processor.processFrame(lowAmp);
      processor.reset();
      const highFeatures = processor.processFrame(highAmp);

      expect(highFeatures.energy).toBeGreaterThan(lowFeatures.energy);
    });

    it('handles silence (near-zero signal)', () => {
      const silence = new Array(1024).fill(0);
      const features = processor.processFrame(silence);

      // log(ε) ≈ -23 for ε = 1e-10
      expect(features.energy).toBeLessThan(-20);
      expect(Number.isFinite(features.energy)).toBe(true);
    });

    it('energy formula: Ea = log(ε + Σₙ a[n]²)', () => {
      const signal = [0.5, 0.5, 0.5, 0.5]; // Simple signal
      const features = processor.processFrame(signal);

      const EPSILON = 1e-10;
      const sumSquares = signal.reduce((sum, x) => sum + x * x, 0);
      const expectedEnergy = Math.log(EPSILON + sumSquares);

      expect(features.energy).toBeCloseTo(expectedEnergy, 6);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Spectral Centroid Tests
  // ═══════════════════════════════════════════════════════════════
  describe('Spectral Centroid (Ca)', () => {
    it('centroid near 440Hz for 440Hz sine', () => {
      const processor48k = new AudioAxisProcessor({
        sampleRate: 48000,
        fftSize: 4096,
      });
      const signal = generateTestSignal(440, 0.1, 48000);
      const features = processor48k.processFrame(signal);

      // Centroid should be close to 440Hz (within tolerance)
      expect(features.centroid).toBeGreaterThan(300);
      expect(features.centroid).toBeLessThan(600);
    });

    it('higher frequency signals have higher centroid', () => {
      const lowFreq = generateTestSignal(200, 0.1, 44100);
      const highFreq = generateTestSignal(2000, 0.1, 44100);

      processor.reset();
      const lowFeatures = processor.processFrame(lowFreq);
      processor.reset();
      const highFeatures = processor.processFrame(highFreq);

      expect(highFeatures.centroid).toBeGreaterThan(lowFeatures.centroid);
    });

    it('centroid is non-negative', () => {
      const signal = generateNoise(2048);
      const features = processor.processFrame(signal);

      expect(features.centroid).toBeGreaterThanOrEqual(0);
    });

    it('centroid bounded by Nyquist frequency', () => {
      const signal = generateNoise(2048);
      const features = processor.processFrame(signal);

      const nyquist = 44100 / 2;
      expect(features.centroid).toBeLessThan(nyquist);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Spectral Flux Tests
  // ═══════════════════════════════════════════════════════════════
  describe('Spectral Flux (Fa)', () => {
    it('flux is zero for first frame', () => {
      processor.reset();
      const signal = generateTestSignal(440, 0.1, 44100);
      const features = processor.processFrame(signal);

      expect(features.flux).toBe(0);
    });

    it('flux is zero for identical consecutive frames', () => {
      const signal = generateTestSignal(440, 0.05, 44100);

      processor.processFrame(signal);
      const features = processor.processFrame(signal);

      expect(features.flux).toBeCloseTo(0, 6);
    });

    it('flux is non-zero for different consecutive frames', () => {
      const signal1 = generateTestSignal(440, 0.05, 44100);
      const signal2 = generateTestSignal(880, 0.05, 44100);

      processor.processFrame(signal1);
      const features = processor.processFrame(signal2);

      expect(features.flux).toBeGreaterThan(0);
    });

    it('reset clears previous spectrum', () => {
      const signal = generateTestSignal(440, 0.05, 44100);

      processor.processFrame(signal);
      processor.reset();
      const features = processor.processFrame(signal);

      expect(features.flux).toBe(0);
    });

    it('flux is non-negative (formula uses squared differences)', () => {
      for (let i = 0; i < 10; i++) {
        const signal = generateNoise(2048);
        const features = processor.processFrame(signal);
        expect(features.flux).toBeGreaterThanOrEqual(0);
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // High-Frequency Ratio Tests
  // ═══════════════════════════════════════════════════════════════
  describe('High-Frequency Ratio (rHF)', () => {
    it('rHF in range [0, 1]', () => {
      const signal = generateNoise(2048);
      const features = processor.processFrame(signal);

      expect(features.hfRatio).toBeGreaterThanOrEqual(0);
      expect(features.hfRatio).toBeLessThanOrEqual(1);
    });

    it('low frequency signal has low rHF', () => {
      const lowFreq = generateTestSignal(100, 0.1, 44100);
      const features = processor.processFrame(lowFreq);

      expect(features.hfRatio).toBeLessThan(0.3);
    });

    it('high frequency signal has higher rHF', () => {
      const processor1 = new AudioAxisProcessor({ hfCutoff: 0.3 });
      const processor2 = new AudioAxisProcessor({ hfCutoff: 0.3 });

      const lowFreq = generateTestSignal(500, 0.1, 44100);
      const highFreq = generateTestSignal(10000, 0.1, 44100);

      const lowFeatures = processor1.processFrame(lowFreq);
      const highFeatures = processor2.processFrame(highFreq);

      expect(highFeatures.hfRatio).toBeGreaterThan(lowFeatures.hfRatio);
    });

    it('custom hfCutoff affects ratio calculation', () => {
      const lowCutoff = new AudioAxisProcessor({ hfCutoff: 0.3 });
      const highCutoff = new AudioAxisProcessor({ hfCutoff: 0.7 });

      const signal = generateNoise(2048);

      const lowFeatures = lowCutoff.processFrame(signal);
      const highFeatures = highCutoff.processFrame(signal);

      // Lower cutoff means more spectrum counts as "high frequency"
      expect(lowFeatures.hfRatio).toBeGreaterThan(highFeatures.hfRatio);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Stability Score Tests
  // ═══════════════════════════════════════════════════════════════
  describe('Audio Stability (Saudio)', () => {
    it('stability = 1 - hfRatio', () => {
      const signal = generateNoise(2048);
      const features = processor.processFrame(signal);

      expect(features.stability).toBeCloseTo(1 - features.hfRatio, 10);
    });

    it('stability in range [0, 1]', () => {
      for (let i = 0; i < 20; i++) {
        const signal = generateNoise(2048);
        const features = processor.processFrame(signal);

        expect(features.stability).toBeGreaterThanOrEqual(0);
        expect(features.stability).toBeLessThanOrEqual(1);
      }
    });

    it('low frequency signals have high stability', () => {
      const lowFreq = generateTestSignal(100, 0.1, 44100);
      const features = processor.processFrame(lowFreq);

      expect(features.stability).toBeGreaterThan(0.7);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Risk Integration Tests
  // ═══════════════════════════════════════════════════════════════
  describe('Risk Integration', () => {
    it('risk formula: Risk + wa*(1 - Saudio)', () => {
      const signal = generateNoise(2048);
      const features = processor.processFrame(signal);

      const baseRisk = 0.5;
      const adjustedRisk = processor.integrateRisk(baseRisk, features);

      const expected = baseRisk + 0.1 * (1 - features.stability);
      expect(adjustedRisk).toBeCloseTo(expected, 10);
    });

    it('high stability adds minimal risk', () => {
      // Low frequency = high stability = minimal risk addition
      const lowFreq = generateTestSignal(100, 0.1, 44100);
      const features = processor.processFrame(lowFreq);

      const baseRisk = 0.5;
      const adjustedRisk = processor.integrateRisk(baseRisk, features);

      // With stability close to 1, risk addition should be minimal
      expect(adjustedRisk - baseRisk).toBeLessThan(0.05);
    });

    it('custom risk weight affects integration', () => {
      const highWeight = new AudioAxisProcessor({ riskWeight: 0.5 });
      const signal = generateNoise(2048);
      const features = highWeight.processFrame(signal);

      const baseRisk = 0.3;
      const adjustedRisk = highWeight.integrateRisk(baseRisk, features);

      const expected = baseRisk + 0.5 * (1 - features.stability);
      expect(adjustedRisk).toBeCloseTo(expected, 10);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // DFT Correctness Tests
  // ═══════════════════════════════════════════════════════════════
  describe('DFT Implementation', () => {
    it('pure tone has peak at correct frequency', () => {
      const freq = 1000;
      const sampleRate = 8000;
      const fftSize = 256;

      const customProcessor = new AudioAxisProcessor({
        sampleRate,
        fftSize,
      });

      // Generate exactly one period of samples
      const signal = generateTestSignal(freq, fftSize / sampleRate, sampleRate);
      const features = customProcessor.processFrame(signal);

      // Centroid should be near the test frequency
      expect(features.centroid).toBeGreaterThan(freq * 0.7);
      expect(features.centroid).toBeLessThan(freq * 1.3);
    });

    it('DC signal has zero centroid', () => {
      const dcSignal = new Array(2048).fill(0.5);
      const features = processor.processFrame(dcSignal);

      // DC is at bin 0, so centroid should be near 0
      expect(features.centroid).toBeLessThan(100);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Property-Based Tests
  // ═══════════════════════════════════════════════════════════════
  describe('Property-based tests', () => {
    it('all features are finite (100 random signals)', () => {
      for (let i = 0; i < 100; i++) {
        const signal = generateNoise(2048);
        const features = processor.processFrame(signal);

        expect(Number.isFinite(features.energy)).toBe(true);
        expect(Number.isFinite(features.centroid)).toBe(true);
        expect(Number.isFinite(features.flux)).toBe(true);
        expect(Number.isFinite(features.hfRatio)).toBe(true);
        expect(Number.isFinite(features.stability)).toBe(true);
      }
    });

    it('processing is deterministic', () => {
      const signal = generateTestSignal(440, 0.05, 44100);

      processor.reset();
      const features1 = processor.processFrame(signal);

      processor.reset();
      const features2 = processor.processFrame(signal);

      expect(features1.energy).toBe(features2.energy);
      expect(features1.centroid).toBe(features2.centroid);
      expect(features1.hfRatio).toBe(features2.hfRatio);
      expect(features1.stability).toBe(features2.stability);
    });
  });
});

describe('generateTestSignal', () => {
  it('generates correct number of samples', () => {
    const signal = generateTestSignal(440, 0.5, 44100);
    expect(signal.length).toBe(22050);
  });

  it('amplitude is bounded [-1, 1]', () => {
    const signal = generateTestSignal(440, 0.1, 44100);

    for (const s of signal) {
      expect(s).toBeGreaterThanOrEqual(-1);
      expect(s).toBeLessThanOrEqual(1);
    }
  });

  it('generates sine wave with correct period', () => {
    const freq = 100;
    const sampleRate = 1000;
    const signal = generateTestSignal(freq, 0.1, sampleRate);

    // At 100Hz with 1000Hz sample rate, period is 10 samples
    // Check that signal[0] ≈ signal[10] ≈ signal[20]
    expect(signal[0]).toBeCloseTo(signal[10], 5);
    expect(signal[10]).toBeCloseTo(signal[20], 5);
  });
});

describe('generateNoise', () => {
  it('generates correct number of samples', () => {
    const noise = generateNoise(1024);
    expect(noise.length).toBe(1024);
  });

  it('amplitude is bounded [-1, 1]', () => {
    const noise = generateNoise(10000);

    for (const s of noise) {
      expect(s).toBeGreaterThanOrEqual(-1);
      expect(s).toBeLessThanOrEqual(1);
    }
  });

  it('has non-zero variance', () => {
    const noise = generateNoise(1000);
    const mean = noise.reduce((a, b) => a + b, 0) / noise.length;
    const variance = noise.reduce((sum, x) => sum + (x - mean) ** 2, 0) / noise.length;

    expect(variance).toBeGreaterThan(0.1);
  });

  it('approximately zero mean (uniform distribution)', () => {
    const noise = generateNoise(100000);
    const mean = noise.reduce((a, b) => a + b, 0) / noise.length;

    // Mean should be close to 0 for uniform [-1, 1]
    expect(Math.abs(mean)).toBeLessThan(0.05);
  });
});
