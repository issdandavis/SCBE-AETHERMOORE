/**
 * SCBE-AETHERMOORE Video Generation Module
 * =========================================
 *
 * Hyperbolic video generation with Sacred Tongue fractals,
 * Poincaré trajectories, and lattice watermarking.
 *
 * @module video
 */

// Types
export type {
  FractalMode,
  Complex,
  TongueFractalConfig,
  ContextVector,
  PoincarePoint,
  HyperbolicTrajectory,
  VideoFrame,
  VideoConfig,
  AudioConfig,
  AudioFrame,
  WatermarkConfig,
  WatermarkVerification,
  VideoGenerationResult,
} from './types.js';

export {
  TONGUE_FRACTAL_CONFIGS,
  DEFAULT_VIDEO_CONFIG,
  DEFAULT_AUDIO_CONFIG,
  DEFAULT_WATERMARK_CONFIG,
} from './types.js';

// Fractal rendering
export {
  mandelbrotIteration,
  juliaIteration,
  burningShipIteration,
  modulateFractalParams,
  renderFractalFrame,
  applyColormap,
} from './fractal.js';

// Trajectory generation
export {
  sanitizePoint,
  contextToPoincarePoint,
  mobiusAdd6D,
  hyperbolicDistance6D,
  expMap0_6D,
  logMap0_6D,
  geodesicInterpolate,
  generateTrajectory,
  validateTrajectory,
} from './trajectory.js';

// Audio synthesis
export { generateAudioFrame, generateAudioTrack, validateAudio, audioToWav } from './audio.js';

// Watermarking
export {
  generateWatermarkKeys,
  embedWatermark,
  verifyWatermark,
  hashFrameContent,
  createWatermarkChain,
} from './watermark.js';

// Main generator
export { generateVideo, streamVideoFrames, validateVideo, exportToJson } from './generator.js';

export type { ProgressCallback } from './generator.js';

// Security Integration (v3.1.1)
export {
  generateFractalFingerprint,
  verifyFractalFingerprint,
  embedTrajectoryState,
  extractJobTrajectory,
  generateAuditReel,
  streamAuditReelFrames,
  createVisualProof,
  verifyVisualProof,
  renderVisualProof,
  videoSecurity,
} from './security-integration.js';

export type {
  FractalFingerprint,
  TrajectoryJobData,
  AuditReelConfig,
  AuditReelResult,
  VisualProof,
} from './security-integration.js';
