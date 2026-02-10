/**
 * SCBE-AETHERMOORE Audio Synthesizer
 * ===================================
 *
 * Generates audio synchronized to hyperbolic trajectories.
 * Pitch and timbre modulated by Poincaré state and Sacred Tongue harmonics.
 *
 * Hardening: Sample bounds, frequency limits, buffer overflow prevention
 */

import type { AudioConfig, AudioFrame, PoincarePoint, TongueFractalConfig } from './types.js';
import { DEFAULT_AUDIO_CONFIG } from './types.js';

/** Golden ratio for harmonic weighting */
const PHI = (1 + Math.sqrt(5)) / 2;

/** Maximum audio amplitude to prevent clipping */
const MAX_AMPLITUDE = 0.95;

/** Minimum frequency to prevent DC offset issues */
const MIN_FREQUENCY = 20;

/** Maximum frequency to prevent aliasing */
const MAX_FREQUENCY_LIMIT = 20000;

/**
 * Clamp value to range
 */
function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

/**
 * Compute Poincaré distance from origin (hyperbolic metric)
 */
function poincareDistanceFromOrigin(point: PoincarePoint): number {
  let normSq = 0;
  for (const v of point) {
    normSq += v * v;
  }
  const norm = Math.sqrt(normSq);
  const clampedNorm = Math.min(norm, 0.999);

  // d_H(0, p) = 2 * arctanh(||p||)
  return 2 * Math.atanh(clampedNorm);
}

/**
 * Generate harmonic weights based on mask and golden ratio
 */
function generateHarmonicWeights(
  harmonicMask: number[],
  count: number,
  useGoldenRatio: boolean
): number[] {
  const weights: number[] = new Array(count).fill(0);

  for (let i = 0; i < count; i++) {
    const harmonic = i + 1;

    // Check if this harmonic is in the mask
    if (harmonicMask.includes(harmonic)) {
      if (useGoldenRatio) {
        // Golden ratio weighting: 1/φ^i
        weights[i] = 1 / Math.pow(PHI, i);
      } else {
        // Standard harmonic falloff: 1/n
        weights[i] = 1 / harmonic;
      }
    }
  }

  // Normalize to sum to 1
  const sum = weights.reduce((a, b) => a + b, 0);
  if (sum > 0) {
    for (let i = 0; i < count; i++) {
      weights[i] /= sum;
    }
  }

  return weights;
}

/**
 * Map Poincaré state to frequency
 * Closer to boundary = higher pitch (tension)
 */
function stateToFrequency(point: PoincarePoint, baseFreq: number, maxFreq: number): number {
  const distance = poincareDistanceFromOrigin(point);

  // Map hyperbolic distance to frequency
  // Use exponential mapping for perceptually linear pitch
  const normalizedDist = Math.min(1, distance / 5); // Normalize to roughly [0, 1]

  // Exponential interpolation between base and max frequency
  const freq = baseFreq * Math.pow(maxFreq / baseFreq, normalizedDist);

  return clamp(freq, MIN_FREQUENCY, MAX_FREQUENCY_LIMIT);
}

/**
 * Map Poincaré state to amplitude envelope
 * Higher entropy dimension = louder
 */
function stateToAmplitude(point: PoincarePoint): number {
  // Use entropy dimension (index 1) for volume
  const entropy = Math.abs(point[1]);

  // Map to [0.3, MAX_AMPLITUDE] - never fully silent
  return 0.3 + entropy * (MAX_AMPLITUDE - 0.3);
}

/**
 * Generate a single audio sample using additive synthesis
 */
function generateSample(
  phase: number,
  frequency: number,
  harmonicWeights: number[],
  amplitude: number
): number {
  let sample = 0;

  for (let i = 0; i < harmonicWeights.length; i++) {
    if (harmonicWeights[i] > 0) {
      const harmonic = i + 1;
      // Add sine wave at harmonic frequency
      sample += harmonicWeights[i] * Math.sin(phase * harmonic);
    }
  }

  // Apply amplitude and soft clip
  sample *= amplitude;

  // Soft clipping to prevent harsh distortion
  if (Math.abs(sample) > MAX_AMPLITUDE) {
    sample =
      Math.sign(sample) * (MAX_AMPLITUDE + Math.tanh(Math.abs(sample) - MAX_AMPLITUDE) * 0.05);
  }

  return sample;
}

/**
 * Apply ADSR envelope to audio segment
 */
function applyEnvelope(
  samples: Float32Array,
  sampleRate: number,
  attackTime: number = 0.01,
  decayTime: number = 0.05,
  sustainLevel: number = 0.8,
  releaseTime: number = 0.05
): void {
  const attackSamples = Math.floor(attackTime * sampleRate);
  const decaySamples = Math.floor(decayTime * sampleRate);
  const releaseSamples = Math.floor(releaseTime * sampleRate);
  const sustainSamples = Math.max(
    0,
    samples.length - attackSamples - decaySamples - releaseSamples
  );

  let idx = 0;

  // Attack
  for (let i = 0; i < attackSamples && idx < samples.length; i++, idx++) {
    samples[idx] *= i / attackSamples;
  }

  // Decay
  for (let i = 0; i < decaySamples && idx < samples.length; i++, idx++) {
    const decayEnv = 1 - (1 - sustainLevel) * (i / decaySamples);
    samples[idx] *= decayEnv;
  }

  // Sustain
  for (let i = 0; i < sustainSamples && idx < samples.length; i++, idx++) {
    samples[idx] *= sustainLevel;
  }

  // Release
  for (let i = 0; i < releaseSamples && idx < samples.length; i++, idx++) {
    samples[idx] *= sustainLevel * (1 - i / releaseSamples);
  }
}

/**
 * Generate audio frame synchronized to video frame
 */
export function generateAudioFrame(
  startTime: number,
  endTime: number,
  poincareState: PoincarePoint,
  fractalConfig: TongueFractalConfig,
  config: AudioConfig = DEFAULT_AUDIO_CONFIG
): AudioFrame {
  const duration = Math.max(0.001, endTime - startTime);
  const sampleCount = Math.ceil(duration * config.sampleRate);
  const samples = new Float32Array(sampleCount);

  // Generate harmonic weights based on tongue's audio mask
  const harmonicWeights = generateHarmonicWeights(
    fractalConfig.audioMask,
    config.harmonicCount,
    config.goldenRatioWeight
  );

  // Map Poincaré state to audio parameters
  const frequency = stateToFrequency(poincareState, config.baseFrequency, config.maxFrequency);
  const amplitude = stateToAmplitude(poincareState);
  const poincareDistance = poincareDistanceFromOrigin(poincareState);

  // Phase accumulator for continuous waveform
  let phase = startTime * 2 * Math.PI * frequency;
  const phaseIncrement = (2 * Math.PI * frequency) / config.sampleRate;

  // Generate samples
  for (let i = 0; i < sampleCount; i++) {
    samples[i] = generateSample(phase, frequency, harmonicWeights, amplitude);
    phase += phaseIncrement;

    // Prevent phase overflow
    if (phase > 2 * Math.PI * 1000) {
      phase -= 2 * Math.PI * 1000;
    }
  }

  // Apply envelope for smooth transitions
  applyEnvelope(samples, config.sampleRate);

  return {
    startTime,
    endTime,
    samples,
    poincareDistance,
  };
}

/**
 * Generate complete audio track for trajectory
 */
export function generateAudioTrack(
  trajectory: { points: PoincarePoint[]; duration: number; fps: number },
  fractalConfig: TongueFractalConfig,
  config: AudioConfig = DEFAULT_AUDIO_CONFIG
): Float32Array {
  const totalSamples = Math.ceil(trajectory.duration * config.sampleRate);
  const audio = new Float32Array(totalSamples);

  const samplesPerFrame = config.sampleRate / trajectory.fps;

  for (let frame = 0; frame < trajectory.points.length; frame++) {
    const startTime = frame / trajectory.fps;
    const endTime = (frame + 1) / trajectory.fps;
    const poincareState = trajectory.points[frame];

    const audioFrame = generateAudioFrame(startTime, endTime, poincareState, fractalConfig, config);

    // Copy frame samples to output buffer
    const startSample = Math.floor(startTime * config.sampleRate);
    for (let i = 0; i < audioFrame.samples.length; i++) {
      const targetIdx = startSample + i;
      if (targetIdx < totalSamples) {
        // Crossfade with existing samples for smooth transitions
        const existingWeight = audio[targetIdx] !== 0 ? 0.5 : 0;
        audio[targetIdx] =
          audio[targetIdx] * existingWeight + audioFrame.samples[i] * (1 - existingWeight);
      }
    }
  }

  // Final normalization to prevent clipping
  let maxAbs = 0;
  for (let i = 0; i < totalSamples; i++) {
    maxAbs = Math.max(maxAbs, Math.abs(audio[i]));
  }

  if (maxAbs > MAX_AMPLITUDE) {
    const scale = MAX_AMPLITUDE / maxAbs;
    for (let i = 0; i < totalSamples; i++) {
      audio[i] *= scale;
    }
  }

  return audio;
}

/**
 * Validate audio samples for integrity
 */
export function validateAudio(samples: Float32Array): string[] {
  const errors: string[] = [];

  if (!samples || samples.length === 0) {
    errors.push('Audio has no samples');
    return errors;
  }

  let hasNonZero = false;
  let maxAbs = 0;

  for (let i = 0; i < samples.length; i++) {
    const sample = samples[i];

    if (!Number.isFinite(sample)) {
      errors.push(`Sample ${i} is not finite: ${sample}`);
      continue;
    }

    if (sample !== 0) hasNonZero = true;
    maxAbs = Math.max(maxAbs, Math.abs(sample));

    if (Math.abs(sample) > 1) {
      errors.push(`Sample ${i} exceeds [-1, 1] range: ${sample}`);
    }
  }

  if (!hasNonZero) {
    errors.push('Audio is completely silent');
  }

  return errors;
}

/**
 * Convert Float32Array audio to WAV format bytes
 */
export function audioToWav(samples: Float32Array, sampleRate: number): Uint8Array {
  const numChannels = 1;
  const bitsPerSample = 16;
  const bytesPerSample = bitsPerSample / 8;
  const blockAlign = numChannels * bytesPerSample;
  const byteRate = sampleRate * blockAlign;
  const dataSize = samples.length * bytesPerSample;
  const fileSize = 36 + dataSize;

  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  // RIFF header
  writeString(view, 0, 'RIFF');
  view.setUint32(4, fileSize, true);
  writeString(view, 8, 'WAVE');

  // fmt chunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // Subchunk1Size
  view.setUint16(20, 1, true); // AudioFormat (PCM)
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);

  // data chunk
  writeString(view, 36, 'data');
  view.setUint32(40, dataSize, true);

  // Audio data (convert float to 16-bit PCM)
  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const sample = clamp(samples[i], -1, 1);
    const intSample = Math.round(sample * 32767);
    view.setInt16(offset, intSample, true);
    offset += 2;
  }

  return new Uint8Array(buffer);
}

function writeString(view: DataView, offset: number, str: string): void {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}
