import { describe, expect, it } from 'vitest';
import {
  BASELINE_RESONANCE_CONFIG,
  EVOLVED_RESONANCE_CONFIG,
  EVOLVED_V2_CONFIG,
  phaseOffsetFromSeed,
  phiInvariantCheck,
  resonanceGate,
  staticEnvelope,
  tongueWave,
} from '../../src/harmonic/resonanceGate.js';

const PRESETS = [
  { name: 'baseline', config: BASELINE_RESONANCE_CONFIG },
  { name: 'evolved_v1', config: EVOLVED_RESONANCE_CONFIG },
  { name: 'evolved_v2', config: EVOLVED_V2_CONFIG },
] as const;

describe('resonanceGate', () => {
  it('keeps the static envelope monotonic in d*', () => {
    expect(staticEnvelope(0.8)).toBeGreaterThan(staticEnvelope(0.2));
  });

  it('maps seed strings deterministically into phase offsets', () => {
    const first = phaseOffsetFromSeed('aligned|human|read|internal');
    const second = phaseOffsetFromSeed('aligned|human|read|internal');
    const other = phaseOffsetFromSeed('reject|human|read|internal');

    expect(first).toBeCloseTo(second, 12);
    expect(first).toBeGreaterThanOrEqual(0);
    expect(first).toBeLessThan(2 * Math.PI);
    expect(first).not.toBeCloseTo(other, 6);
  });

  it('keeps the baseline preset as the implicit default', () => {
    const signalPhaseOffset = phaseOffsetFromSeed('aligned|human|read|internal');
    const implicit = resonanceGate(0.3, 0, { signalPhaseOffset });
    const explicit = resonanceGate(0.3, 0, {
      ...BASELINE_RESONANCE_CONFIG,
      signalPhaseOffset,
    });

    expect(implicit.rho).toBeCloseTo(explicit.rho, 12);
    expect(implicit.geometryAlignment).toBeCloseTo(explicit.geometryAlignment, 12);
    expect(implicit.decision).toBe(explicit.decision);
  });

  it('keeps evolved origin geometry pinned to 1 while remaining opt-in', () => {
    const origin = resonanceGate(0, 0, EVOLVED_RESONANCE_CONFIG);
    const safeSeed = phaseOffsetFromSeed('aligned|human|read|internal');
    const baseline = resonanceGate(0.1, 0, {
      ...BASELINE_RESONANCE_CONFIG,
      signalPhaseOffset: safeSeed,
    });
    const evolved = resonanceGate(0.1, 0, {
      ...EVOLVED_RESONANCE_CONFIG,
      signalPhaseOffset: safeSeed,
    });

    expect(origin.geometryAlignment).toBeCloseTo(1, 12);
    expect(evolved.geometryAlignment).toBeGreaterThan(baseline.geometryAlignment);
    expect(evolved.rho).toBeGreaterThan(baseline.rho);
  });

  it('keeps tongueWave normalized into [-1, 1]', () => {
    const result = tongueWave(0, undefined, phaseOffsetFromSeed('aligned'));
    expect(result.combined).toBeGreaterThanOrEqual(-1);
    expect(result.combined).toBeLessThanOrEqual(1);
    expect(Object.keys(result.contributions)).toEqual(['KO', 'AV', 'RU', 'CA', 'UM', 'DR']);
  });

  it('lets evolved_v2 use matched-filter phase discrimination without changing v1', () => {
    const dStar = 0.3;
    let weightedAlignedAvg = 0;
    let weightedShiftedAvg = 0;
    let matchedAlignedAvg = 0;
    let matchedShiftedAvg = 0;

    for (let i = 0; i < 256; i++) {
      const t = i * 0.0003;
      weightedAlignedAvg += resonanceGate(dStar, t, {
        ...EVOLVED_RESONANCE_CONFIG,
        signalPhaseOffset: 0,
      }).rho;
      weightedShiftedAvg += resonanceGate(dStar, t, {
        ...EVOLVED_RESONANCE_CONFIG,
        signalPhaseOffset: Math.PI,
      }).rho;
      matchedAlignedAvg += resonanceGate(dStar, t, {
        ...EVOLVED_V2_CONFIG,
        signalPhaseOffset: 0,
      }).rho;
      matchedShiftedAvg += resonanceGate(dStar, t, {
        ...EVOLVED_V2_CONFIG,
        signalPhaseOffset: Math.PI,
      }).rho;
    }

    weightedAlignedAvg /= 256;
    weightedShiftedAvg /= 256;
    matchedAlignedAvg /= 256;
    matchedShiftedAvg /= 256;

    const weightedSample = resonanceGate(dStar, 0.001, {
      ...EVOLVED_RESONANCE_CONFIG,
      signalPhaseOffset: 0,
    });
    const matchedSample = resonanceGate(dStar, 0.001, {
      ...EVOLVED_V2_CONFIG,
      signalPhaseOffset: 0,
    });
    const matchedShiftedSample = resonanceGate(dStar, 0.001, {
      ...EVOLVED_V2_CONFIG,
      signalPhaseOffset: Math.PI,
    });

    const weightedDelta = Math.abs(weightedAlignedAvg - weightedShiftedAvg);
    const matchedDelta = Math.abs(matchedAlignedAvg - matchedShiftedAvg);

    expect(weightedSample.phaseStrategy).toBe('weighted_wave');
    expect(matchedSample.phaseStrategy).toBe('matched_filter');
    expect(matchedSample.phaseCorrelation).not.toBeNull();
    expect(matchedDelta).toBeGreaterThan(weightedDelta * 20);
    expect(matchedSample.decision).toBe('PASS');
    expect(matchedShiftedSample.decision).toBe('REJECT');
  });

  describe.each(PRESETS)('$name preset regression suite', ({ config }) => {
    it('makes rho depend on geometry at a fixed phase sample', () => {
      const signalPhaseOffset = phaseOffsetFromSeed('aligned|human|read|internal');
      const near = resonanceGate(0.1, 0, { ...config, signalPhaseOffset });
      const far = resonanceGate(0.8, 0, { ...config, signalPhaseOffset });

      expect(near.waveAlignment).toBeCloseTo(far.waveAlignment, 12);
      expect(near.geometryAlignment).toBeGreaterThan(far.geometryAlignment);
      expect(near.rho).toBeGreaterThan(far.rho);
      expect(near.barrierCost).toBeLessThan(far.barrierCost);
    });

    it('makes rho depend on seeded phase at a fixed geometry sample', () => {
      const aligned = resonanceGate(0.3, 0, {
        ...config,
        signalPhaseOffset: phaseOffsetFromSeed('aligned|human|read|internal'),
      });
      const rejecting = resonanceGate(0.3, 0, {
        ...config,
        signalPhaseOffset: phaseOffsetFromSeed('reject|human|read|internal'),
      });

      expect(aligned.geometryAlignment).toBeCloseTo(rejecting.geometryAlignment, 12);
      expect(aligned.waveAlignment).not.toBeCloseTo(rejecting.waveAlignment, 6);
      expect(aligned.rho).not.toBeCloseTo(rejecting.rho, 6);
    });

    it('produces finite phi-invariant diagnostics', () => {
      const result = phiInvariantCheck(0.2, 16, 0.001, {
        ...config,
        signalPhaseOffset: phaseOffsetFromSeed('aligned|human|read|internal'),
      });

      expect(Number.isFinite(result.fractalDim)).toBe(true);
      expect(typeof result.isPhiAligned).toBe('boolean');
      expect(result.tolerance).toBeGreaterThan(0);
    });
  });
});
