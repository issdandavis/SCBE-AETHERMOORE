"use strict";
/**
 * SCBE-AETHERMOORE Video Generation Module
 * =========================================
 *
 * Hyperbolic video generation with Sacred Tongue fractals,
 * Poincaré trajectories, and lattice watermarking.
 *
 * @module video
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.videoSecurity = exports.renderVisualProof = exports.verifyVisualProof = exports.createVisualProof = exports.streamAuditReelFrames = exports.generateAuditReel = exports.extractJobTrajectory = exports.embedTrajectoryState = exports.verifyFractalFingerprint = exports.generateFractalFingerprint = exports.exportToJson = exports.validateVideo = exports.streamVideoFrames = exports.generateVideo = exports.createWatermarkChain = exports.hashFrameContent = exports.verifyWatermark = exports.embedWatermark = exports.generateWatermarkKeys = exports.audioToWav = exports.validateAudio = exports.generateAudioTrack = exports.generateAudioFrame = exports.validateTrajectory = exports.generateTrajectory = exports.geodesicInterpolate = exports.logMap0_6D = exports.expMap0_6D = exports.hyperbolicDistance6D = exports.mobiusAdd6D = exports.contextToPoincarePoint = exports.sanitizePoint = exports.applyColormap = exports.renderFractalFrame = exports.modulateFractalParams = exports.burningShipIteration = exports.juliaIteration = exports.mandelbrotIteration = exports.DEFAULT_WATERMARK_CONFIG = exports.DEFAULT_AUDIO_CONFIG = exports.DEFAULT_VIDEO_CONFIG = exports.TONGUE_FRACTAL_CONFIGS = void 0;
var types_js_1 = require("./types.js");
Object.defineProperty(exports, "TONGUE_FRACTAL_CONFIGS", { enumerable: true, get: function () { return types_js_1.TONGUE_FRACTAL_CONFIGS; } });
Object.defineProperty(exports, "DEFAULT_VIDEO_CONFIG", { enumerable: true, get: function () { return types_js_1.DEFAULT_VIDEO_CONFIG; } });
Object.defineProperty(exports, "DEFAULT_AUDIO_CONFIG", { enumerable: true, get: function () { return types_js_1.DEFAULT_AUDIO_CONFIG; } });
Object.defineProperty(exports, "DEFAULT_WATERMARK_CONFIG", { enumerable: true, get: function () { return types_js_1.DEFAULT_WATERMARK_CONFIG; } });
// Fractal rendering
var fractal_js_1 = require("./fractal.js");
Object.defineProperty(exports, "mandelbrotIteration", { enumerable: true, get: function () { return fractal_js_1.mandelbrotIteration; } });
Object.defineProperty(exports, "juliaIteration", { enumerable: true, get: function () { return fractal_js_1.juliaIteration; } });
Object.defineProperty(exports, "burningShipIteration", { enumerable: true, get: function () { return fractal_js_1.burningShipIteration; } });
Object.defineProperty(exports, "modulateFractalParams", { enumerable: true, get: function () { return fractal_js_1.modulateFractalParams; } });
Object.defineProperty(exports, "renderFractalFrame", { enumerable: true, get: function () { return fractal_js_1.renderFractalFrame; } });
Object.defineProperty(exports, "applyColormap", { enumerable: true, get: function () { return fractal_js_1.applyColormap; } });
// Trajectory generation
var trajectory_js_1 = require("./trajectory.js");
Object.defineProperty(exports, "sanitizePoint", { enumerable: true, get: function () { return trajectory_js_1.sanitizePoint; } });
Object.defineProperty(exports, "contextToPoincarePoint", { enumerable: true, get: function () { return trajectory_js_1.contextToPoincarePoint; } });
Object.defineProperty(exports, "mobiusAdd6D", { enumerable: true, get: function () { return trajectory_js_1.mobiusAdd6D; } });
Object.defineProperty(exports, "hyperbolicDistance6D", { enumerable: true, get: function () { return trajectory_js_1.hyperbolicDistance6D; } });
Object.defineProperty(exports, "expMap0_6D", { enumerable: true, get: function () { return trajectory_js_1.expMap0_6D; } });
Object.defineProperty(exports, "logMap0_6D", { enumerable: true, get: function () { return trajectory_js_1.logMap0_6D; } });
Object.defineProperty(exports, "geodesicInterpolate", { enumerable: true, get: function () { return trajectory_js_1.geodesicInterpolate; } });
Object.defineProperty(exports, "generateTrajectory", { enumerable: true, get: function () { return trajectory_js_1.generateTrajectory; } });
Object.defineProperty(exports, "validateTrajectory", { enumerable: true, get: function () { return trajectory_js_1.validateTrajectory; } });
// Audio synthesis
var audio_js_1 = require("./audio.js");
Object.defineProperty(exports, "generateAudioFrame", { enumerable: true, get: function () { return audio_js_1.generateAudioFrame; } });
Object.defineProperty(exports, "generateAudioTrack", { enumerable: true, get: function () { return audio_js_1.generateAudioTrack; } });
Object.defineProperty(exports, "validateAudio", { enumerable: true, get: function () { return audio_js_1.validateAudio; } });
Object.defineProperty(exports, "audioToWav", { enumerable: true, get: function () { return audio_js_1.audioToWav; } });
// Watermarking
var watermark_js_1 = require("./watermark.js");
Object.defineProperty(exports, "generateWatermarkKeys", { enumerable: true, get: function () { return watermark_js_1.generateWatermarkKeys; } });
Object.defineProperty(exports, "embedWatermark", { enumerable: true, get: function () { return watermark_js_1.embedWatermark; } });
Object.defineProperty(exports, "verifyWatermark", { enumerable: true, get: function () { return watermark_js_1.verifyWatermark; } });
Object.defineProperty(exports, "hashFrameContent", { enumerable: true, get: function () { return watermark_js_1.hashFrameContent; } });
Object.defineProperty(exports, "createWatermarkChain", { enumerable: true, get: function () { return watermark_js_1.createWatermarkChain; } });
// Main generator
var generator_js_1 = require("./generator.js");
Object.defineProperty(exports, "generateVideo", { enumerable: true, get: function () { return generator_js_1.generateVideo; } });
Object.defineProperty(exports, "streamVideoFrames", { enumerable: true, get: function () { return generator_js_1.streamVideoFrames; } });
Object.defineProperty(exports, "validateVideo", { enumerable: true, get: function () { return generator_js_1.validateVideo; } });
Object.defineProperty(exports, "exportToJson", { enumerable: true, get: function () { return generator_js_1.exportToJson; } });
// Security Integration (v3.1.1)
var security_integration_js_1 = require("./security-integration.js");
Object.defineProperty(exports, "generateFractalFingerprint", { enumerable: true, get: function () { return security_integration_js_1.generateFractalFingerprint; } });
Object.defineProperty(exports, "verifyFractalFingerprint", { enumerable: true, get: function () { return security_integration_js_1.verifyFractalFingerprint; } });
Object.defineProperty(exports, "embedTrajectoryState", { enumerable: true, get: function () { return security_integration_js_1.embedTrajectoryState; } });
Object.defineProperty(exports, "extractJobTrajectory", { enumerable: true, get: function () { return security_integration_js_1.extractJobTrajectory; } });
Object.defineProperty(exports, "generateAuditReel", { enumerable: true, get: function () { return security_integration_js_1.generateAuditReel; } });
Object.defineProperty(exports, "streamAuditReelFrames", { enumerable: true, get: function () { return security_integration_js_1.streamAuditReelFrames; } });
Object.defineProperty(exports, "createVisualProof", { enumerable: true, get: function () { return security_integration_js_1.createVisualProof; } });
Object.defineProperty(exports, "verifyVisualProof", { enumerable: true, get: function () { return security_integration_js_1.verifyVisualProof; } });
Object.defineProperty(exports, "renderVisualProof", { enumerable: true, get: function () { return security_integration_js_1.renderVisualProof; } });
Object.defineProperty(exports, "videoSecurity", { enumerable: true, get: function () { return security_integration_js_1.videoSecurity; } });
//# sourceMappingURL=index.js.map