/**
 * SCBE-AETHERMOORE Video Generator
 * =================================
 *
 * Main orchestrator for hyperbolic video generation pipeline.
 * Integrates fractal rendering, trajectory generation, audio synthesis,
 * and lattice watermarking into a unified, hardened system.
 *
 * Hardening: Memory limits, streaming output, progress callbacks, error recovery
 */
import type { VideoConfig, VideoFrame, VideoGenerationResult, WatermarkConfig, AudioConfig } from './types.js';
/**
 * Progress callback type for long-running generation
 */
export type ProgressCallback = (progress: {
    phase: 'trajectory' | 'frames' | 'audio' | 'watermark';
    current: number;
    total: number;
    percent: number;
}) => void;
/**
 * Generate complete video with all components
 *
 * @param config - Video configuration
 * @param watermarkConfig - Watermark configuration
 * @param audioConfig - Audio configuration
 * @param seed - Random seed for deterministic generation
 * @param onProgress - Progress callback for long operations
 * @returns Complete generation result
 */
export declare function generateVideo(config?: Partial<VideoConfig>, watermarkConfig?: Partial<WatermarkConfig>, audioConfig?: Partial<AudioConfig>, seed?: number, onProgress?: ProgressCallback): Promise<VideoGenerationResult>;
/**
 * Generate video frames as async iterator (streaming)
 * For memory-efficient processing of large videos
 */
export declare function streamVideoFrames(config?: Partial<VideoConfig>, watermarkConfig?: Partial<WatermarkConfig>, seed?: number): AsyncGenerator<VideoFrame, void, unknown>;
/**
 * Validate a generated video for integrity
 */
export declare function validateVideo(result: VideoGenerationResult): string[];
/**
 * Export video result to JSON format
 */
export declare function exportToJson(result: VideoGenerationResult): string;
//# sourceMappingURL=generator.d.ts.map