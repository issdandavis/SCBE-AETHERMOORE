/**
 * SCBE-AETHERMOORE Video Generation Module
 * =========================================
 *
 * Hyperbolic video generation with Sacred Tongue fractals,
 * Poincaré trajectories, and lattice watermarking.
 *
 * @module video
 */
export type { FractalMode, Complex, TongueFractalConfig, ContextVector, PoincarePoint, HyperbolicTrajectory, VideoFrame, VideoConfig, AudioConfig, AudioFrame, WatermarkConfig, WatermarkVerification, VideoGenerationResult, } from './types.js';
export { TONGUE_FRACTAL_CONFIGS, DEFAULT_VIDEO_CONFIG, DEFAULT_AUDIO_CONFIG, DEFAULT_WATERMARK_CONFIG, } from './types.js';
export { mandelbrotIteration, juliaIteration, burningShipIteration, modulateFractalParams, renderFractalFrame, applyColormap, } from './fractal.js';
export { sanitizePoint, contextToPoincarePoint, mobiusAdd6D, hyperbolicDistance6D, expMap0_6D, logMap0_6D, geodesicInterpolate, generateTrajectory, validateTrajectory, } from './trajectory.js';
export { generateAudioFrame, generateAudioTrack, validateAudio, audioToWav } from './audio.js';
export { generateWatermarkKeys, embedWatermark, verifyWatermark, hashFrameContent, createWatermarkChain, } from './watermark.js';
export { generateVideo, streamVideoFrames, validateVideo, exportToJson } from './generator.js';
export type { ProgressCallback } from './generator.js';
export { generateFractalFingerprint, verifyFractalFingerprint, embedTrajectoryState, extractJobTrajectory, generateAuditReel, streamAuditReelFrames, createVisualProof, verifyVisualProof, renderVisualProof, videoSecurity, } from './security-integration.js';
export type { FractalFingerprint, TrajectoryJobData, AuditReelConfig, AuditReelResult, VisualProof, } from './security-integration.js';
//# sourceMappingURL=index.d.ts.map