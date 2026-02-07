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
/**
 * Generate audio frame synchronized to video frame
 */
export declare function generateAudioFrame(startTime: number, endTime: number, poincareState: PoincarePoint, fractalConfig: TongueFractalConfig, config?: AudioConfig): AudioFrame;
/**
 * Generate complete audio track for trajectory
 */
export declare function generateAudioTrack(trajectory: {
    points: PoincarePoint[];
    duration: number;
    fps: number;
}, fractalConfig: TongueFractalConfig, config?: AudioConfig): Float32Array;
/**
 * Validate audio samples for integrity
 */
export declare function validateAudio(samples: Float32Array): string[];
/**
 * Convert Float32Array audio to WAV format bytes
 */
export declare function audioToWav(samples: Float32Array, sampleRate: number): Uint8Array;
//# sourceMappingURL=audio.d.ts.map