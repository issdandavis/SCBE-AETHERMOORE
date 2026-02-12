/**
 * SCBE-AETHERMOORE Video Generation Types
 * ========================================
 *
 * Type definitions for hyperbolic video generation pipeline.
 * Integrates Sacred Tongues, Poincaré embeddings, and fractal chaos.
 */
import type { TongueID } from '../spiralverse/types.js';
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
    c: Complex;
    colormap: string;
    maxIterations: number;
    bailout: number;
    mode: FractalMode;
    audioMask: number[];
}
/**
 * Default fractal configurations for each Sacred Tongue
 */
export declare const TONGUE_FRACTAL_CONFIGS: Record<TongueID, TongueFractalConfig>;
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
    chaosStrength: number;
    breathingAmplitude: number;
    outputFormat: 'frames' | 'raw' | 'json';
}
/**
 * Default video configuration
 */
export declare const DEFAULT_VIDEO_CONFIG: VideoConfig;
/**
 * Audio synthesis configuration
 */
export interface AudioConfig {
    sampleRate: number;
    baseFrequency: number;
    maxFrequency: number;
    harmonicCount: number;
    goldenRatioWeight: boolean;
}
/**
 * Default audio configuration
 */
export declare const DEFAULT_AUDIO_CONFIG: AudioConfig;
/**
 * Audio frame synchronized to video
 */
export interface AudioFrame {
    startTime: number;
    endTime: number;
    samples: Float32Array;
    poincareDistance: number;
}
/**
 * Lattice watermark configuration
 */
export interface WatermarkConfig {
    dimension: number;
    modulus: number;
    errorBound: number;
}
/**
 * Default watermark configuration
 */
export declare const DEFAULT_WATERMARK_CONFIG: WatermarkConfig;
/**
 * Watermark verification result
 */
export interface WatermarkVerification {
    valid: boolean;
    extractedHash: string;
    expectedHash: string;
    confidence: number;
}
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
//# sourceMappingURL=types.d.ts.map