/**
 * SCBE-AETHERMOORE Video Generation Types
 * ========================================
 *
 * Type definitions for hyperbolic video generation pipeline.
 * Integrates Sacred Tongues, Poincaré embeddings, and fractal chaos.
 */

import type { TongueID } from '../spiralverse/types.js';

// ============================================================================
// FRACTAL TYPES
// ============================================================================

/**
 * Fractal rendering mode
 */
export type FractalMode = 'mandelbrot' | 'julia' | 'burning_ship' | 'hybrid';

/**
 * Complex number for fractal iteration
 */
export interface Complex {
  re: number;
  im: number;
}

/**
 * Fractal configuration for a Sacred Tongue
 */
export interface TongueFractalConfig {
  tongue: TongueID;
  c: Complex; // Julia/Mandelbrot c parameter
  colormap: string;
  maxIterations: number;
  bailout: number;
  mode: FractalMode;
  audioMask: number[]; // Harmonic indices for this intent
}

/**
 * Default fractal configurations for each Sacred Tongue
 */
export const TONGUE_FRACTAL_CONFIGS: Record<TongueID, TongueFractalConfig> = {
  ko: {
    tongue: 'ko',
    c: { re: -0.4, im: 0.6 },
    colormap: 'plasma',
    maxIterations: 200,
    bailout: 2,
    mode: 'mandelbrot',
    audioMask: [1, 3, 5], // Odd harmonics - pure, consonant
  },
  av: {
    tongue: 'av',
    c: { re: -0.8, im: 0.156 },
    colormap: 'viridis',
    maxIterations: 200,
    bailout: 2,
    mode: 'mandelbrot',
    audioMask: [1, 2, 3, 4, 5], // Full series - rich, complex
  },
  ru: {
    tongue: 'ru',
    c: { re: -0.123, im: 0.745 },
    colormap: 'inferno',
    maxIterations: 250,
    bailout: 2,
    mode: 'julia',
    audioMask: [2, 4, 6, 8], // Even harmonics - dissonant, tense
  },
  ca: {
    tongue: 'ca',
    c: { re: 0.285, im: 0.01 },
    colormap: 'magma',
    maxIterations: 200,
    bailout: 10,
    mode: 'burning_ship',
    audioMask: [1, 5, 7, 11], // Prime harmonics - alien, otherworldly
  },
  um: {
    tongue: 'um',
    c: { re: -1.0, im: 0 },
    colormap: 'bone',
    maxIterations: 300,
    bailout: 2,
    mode: 'mandelbrot',
    audioMask: [1, 2, 4, 8], // Power of 2 - mysterious
  },
  dr: {
    tongue: 'dr',
    c: { re: -0.75, im: 0.11 },
    colormap: 'twilight',
    maxIterations: 200,
    bailout: 2,
    mode: 'mandelbrot',
    audioMask: [1, 3, 5, 7, 9], // Odd series - structured
  },
};

// ============================================================================
// HYPERBOLIC TYPES
// ============================================================================

/**
 * 6D context vector for Poincaré embedding
 */
export interface ContextVector {
  time: number;
  entropy: number;
  threatLevel: number;
  userId: number;
  behavioralStability: number;
  audioPhase: number;
}

/**
 * Poincaré ball point (6D, bounded)
 */
export type PoincarePoint = [number, number, number, number, number, number];

/**
 * Hyperbolic trajectory - sequence of points over time
 */
export interface HyperbolicTrajectory {
  points: PoincarePoint[];
  duration: number;
  fps: number;
  tongue: TongueID;
}

// ============================================================================
// VIDEO TYPES
// ============================================================================

/**
 * Single video frame with metadata
 */
export interface VideoFrame {
  index: number;
  timestamp: number;
  width: number;
  height: number;
  data: Uint8ClampedArray | Float32Array;
  poincareState: PoincarePoint;
  watermarkHash?: string;
}

/**
 * Video generation configuration
 */
export interface VideoConfig {
  width: number;
  height: number;
  fps: number;
  duration: number;
  tongue: TongueID;
  fractalMode: FractalMode;
  enableWatermark: boolean;
  enableAudio: boolean;
  chaosStrength: number; // 0-1, how much Poincaré state affects fractal
  breathingAmplitude: number; // 0-1, hyperbolic breathing intensity
  outputFormat: 'frames' | 'raw' | 'json';
}

/**
 * Default video configuration
 */
export const DEFAULT_VIDEO_CONFIG: VideoConfig = {
  width: 800,
  height: 800,
  fps: 30,
  duration: 10,
  tongue: 'av',
  fractalMode: 'mandelbrot',
  enableWatermark: true,
  enableAudio: true,
  chaosStrength: 0.3,
  breathingAmplitude: 0.2,
  outputFormat: 'frames',
};

// ============================================================================
// AUDIO TYPES
// ============================================================================

/**
 * Audio synthesis configuration
 */
export interface AudioConfig {
  sampleRate: number;
  baseFrequency: number; // Hz
  maxFrequency: number; // Hz
  harmonicCount: number;
  goldenRatioWeight: boolean;
}

/**
 * Default audio configuration
 */
export const DEFAULT_AUDIO_CONFIG: AudioConfig = {
  sampleRate: 44100,
  baseFrequency: 220, // A3
  maxFrequency: 880, // A5
  harmonicCount: 8,
  goldenRatioWeight: true,
};

/**
 * Audio frame synchronized to video
 */
export interface AudioFrame {
  startTime: number;
  endTime: number;
  samples: Float32Array;
  poincareDistance: number; // Distance from origin affects pitch
}

// ============================================================================
// WATERMARK TYPES
// ============================================================================

/**
 * Lattice watermark configuration
 */
export interface WatermarkConfig {
  dimension: number; // Lattice dimension (e.g., 16)
  modulus: number; // q parameter (e.g., 97)
  errorBound: number; // Max error coefficient
}

/**
 * Default watermark configuration
 */
export const DEFAULT_WATERMARK_CONFIG: WatermarkConfig = {
  dimension: 16,
  modulus: 97,
  errorBound: 1,
};

/**
 * Watermark verification result
 */
export interface WatermarkVerification {
  valid: boolean;
  extractedHash: string;
  expectedHash: string;
  confidence: number; // 0-1
}

// ============================================================================
// GENERATION RESULT
// ============================================================================

/**
 * Complete video generation result
 */
export interface VideoGenerationResult {
  success: boolean;
  config: VideoConfig;
  trajectory: HyperbolicTrajectory;
  frameCount: number;
  frames?: VideoFrame[];
  audioSamples?: Float32Array;
  watermarkKeys?: {
    publicKey: number[][];
    secretKey: number[];
  };
  metrics: {
    totalTimeMs: number;
    avgFrameTimeMs: number;
    peakMemoryMB: number;
  };
  errors: string[];
}
