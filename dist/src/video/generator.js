"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateVideo = generateVideo;
exports.streamVideoFrames = streamVideoFrames;
exports.validateVideo = validateVideo;
exports.exportToJson = exportToJson;
const types_js_1 = require("./types.js");
const fractal_js_1 = require("./fractal.js");
const trajectory_js_1 = require("./trajectory.js");
const audio_js_1 = require("./audio.js");
const watermark_js_1 = require("./watermark.js");
/** Maximum video dimensions */
const MAX_WIDTH = 4096;
const MAX_HEIGHT = 4096;
/** Maximum duration in seconds */
const MAX_DURATION = 3600;
/** Maximum FPS */
const MAX_FPS = 120;
/** Memory limit per frame in bytes (100MB) */
const MAX_FRAME_MEMORY = 100 * 1024 * 1024;
/**
 * Validate and sanitize video configuration
 */
function validateConfig(config) {
    const validated = { ...types_js_1.DEFAULT_VIDEO_CONFIG, ...config };
    // Clamp dimensions
    validated.width = Math.max(1, Math.min(MAX_WIDTH, Math.floor(validated.width)));
    validated.height = Math.max(1, Math.min(MAX_HEIGHT, Math.floor(validated.height)));
    // Check frame memory
    const frameBytes = validated.width * validated.height * 4; // RGBA
    if (frameBytes > MAX_FRAME_MEMORY) {
        const scale = Math.sqrt(MAX_FRAME_MEMORY / frameBytes);
        validated.width = Math.floor(validated.width * scale);
        validated.height = Math.floor(validated.height * scale);
    }
    // Clamp other parameters
    validated.fps = Math.max(1, Math.min(MAX_FPS, Math.floor(validated.fps)));
    validated.duration = Math.max(0.1, Math.min(MAX_DURATION, validated.duration));
    validated.chaosStrength = Math.max(0, Math.min(1, validated.chaosStrength));
    validated.breathingAmplitude = Math.max(0, Math.min(0.1, validated.breathingAmplitude));
    // Validate tongue
    const validTongues = ['ko', 'av', 'ru', 'ca', 'um', 'dr'];
    if (!validTongues.includes(validated.tongue)) {
        validated.tongue = 'av';
    }
    // Validate fractal mode
    const validModes = ['mandelbrot', 'julia', 'burning_ship', 'hybrid'];
    if (!validModes.includes(validated.fractalMode)) {
        validated.fractalMode = 'mandelbrot';
    }
    // Validate output format
    const validFormats = ['frames', 'raw', 'json'];
    if (!validFormats.includes(validated.outputFormat)) {
        validated.outputFormat = 'frames';
    }
    return validated;
}
/**
 * Generate a single video frame
 */
function generateFrame(index, timestamp, poincareState, fractalConfig, config, watermarkKeys) {
    // Render fractal with hyperbolic modulation
    const normalized = (0, fractal_js_1.renderFractalFrame)(config.width, config.height, fractalConfig, poincareState, config.chaosStrength, config.breathingAmplitude, timestamp);
    // Apply colormap to get RGBA data
    let data = (0, fractal_js_1.applyColormap)(normalized, fractalConfig.colormap, config.width, config.height);
    // Generate and embed watermark if enabled
    let watermarkHash;
    if (config.enableWatermark && watermarkKeys) {
        watermarkHash = (0, watermark_js_1.hashFrameContent)(data, index, timestamp);
        data = (0, watermark_js_1.embedWatermark)(data, watermarkHash, watermarkKeys.publicKey);
    }
    // Convert to raw format if requested
    if (config.outputFormat === 'raw') {
        const rawData = new Float32Array(data.length);
        for (let i = 0; i < data.length; i++) {
            rawData[i] = data[i] / 255;
        }
        data = rawData;
    }
    return {
        index,
        timestamp,
        width: config.width,
        height: config.height,
        data,
        poincareState,
        watermarkHash,
    };
}
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
async function generateVideo(config = {}, watermarkConfig = {}, audioConfig = {}, seed = Date.now(), onProgress) {
    const startTime = performance.now();
    const errors = [];
    let peakMemoryMB = 0;
    // Validate configurations
    const validatedConfig = validateConfig(config);
    const validatedWatermark = { ...types_js_1.DEFAULT_WATERMARK_CONFIG, ...watermarkConfig };
    const validatedAudio = { ...types_js_1.DEFAULT_AUDIO_CONFIG, ...audioConfig };
    // Get fractal config for tongue
    const fractalConfig = types_js_1.TONGUE_FRACTAL_CONFIGS[validatedConfig.tongue];
    // Override fractal mode if specified
    const finalFractalConfig = {
        ...fractalConfig,
        mode: validatedConfig.fractalMode,
    };
    // Phase 1: Generate trajectory
    onProgress?.({
        phase: 'trajectory',
        current: 0,
        total: 1,
        percent: 0,
    });
    const trajectory = (0, trajectory_js_1.generateTrajectory)(validatedConfig.tongue, validatedConfig.duration, validatedConfig.fps, validatedConfig.breathingAmplitude, seed);
    // Validate trajectory
    const trajectoryErrors = (0, trajectory_js_1.validateTrajectory)(trajectory);
    if (trajectoryErrors.length > 0) {
        errors.push(...trajectoryErrors.map((e) => `Trajectory: ${e}`));
    }
    onProgress?.({
        phase: 'trajectory',
        current: 1,
        total: 1,
        percent: 100,
    });
    // Phase 2: Generate watermark keys if enabled
    let watermarkKeys;
    if (validatedConfig.enableWatermark) {
        watermarkKeys = (0, watermark_js_1.generateWatermarkKeys)(validatedWatermark);
    }
    // Phase 3: Generate frames
    const frames = [];
    const frameHashes = [];
    const totalFrames = trajectory.points.length;
    let totalFrameTime = 0;
    for (let i = 0; i < totalFrames; i++) {
        const frameStart = performance.now();
        const timestamp = i / validatedConfig.fps;
        const poincareState = trajectory.points[i];
        try {
            const frame = generateFrame(i, timestamp, poincareState, finalFractalConfig, validatedConfig, watermarkKeys);
            frames.push(frame);
            if (frame.watermarkHash) {
                frameHashes.push(frame.watermarkHash);
            }
            // Track frame generation time
            totalFrameTime += performance.now() - frameStart;
            // Estimate memory usage
            const frameMemory = frame.data.length * (frame.data instanceof Float32Array ? 4 : 1);
            const totalMemory = frames.length * frameMemory;
            peakMemoryMB = Math.max(peakMemoryMB, totalMemory / (1024 * 1024));
        }
        catch (error) {
            errors.push(`Frame ${i}: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
        // Progress callback
        onProgress?.({
            phase: 'frames',
            current: i + 1,
            total: totalFrames,
            percent: Math.round(((i + 1) / totalFrames) * 100),
        });
        // Yield to event loop periodically for responsiveness
        if (i % 10 === 0) {
            await new Promise((resolve) => setTimeout(resolve, 0));
        }
    }
    // Phase 4: Generate audio if enabled
    let audioSamples;
    if (validatedConfig.enableAudio) {
        onProgress?.({
            phase: 'audio',
            current: 0,
            total: 1,
            percent: 0,
        });
        try {
            audioSamples = (0, audio_js_1.generateAudioTrack)(trajectory, finalFractalConfig, validatedAudio);
            // Validate audio
            const audioErrors = (0, audio_js_1.validateAudio)(audioSamples);
            if (audioErrors.length > 0) {
                errors.push(...audioErrors.map((e) => `Audio: ${e}`));
            }
            // Track audio memory
            const audioMemory = audioSamples.length * 4;
            peakMemoryMB = Math.max(peakMemoryMB, peakMemoryMB + audioMemory / (1024 * 1024));
        }
        catch (error) {
            errors.push(`Audio: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
        onProgress?.({
            phase: 'audio',
            current: 1,
            total: 1,
            percent: 100,
        });
    }
    // Phase 5: Create watermark chain
    if (validatedConfig.enableWatermark && frameHashes.length > 0) {
        onProgress?.({
            phase: 'watermark',
            current: 0,
            total: 1,
            percent: 0,
        });
        const { chainHash, merkleRoot } = (0, watermark_js_1.createWatermarkChain)(frameHashes);
        // Store chain info in last frame's watermarkHash
        if (frames.length > 0) {
            frames[frames.length - 1].watermarkHash = `chain:${chainHash},merkle:${merkleRoot}`;
        }
        onProgress?.({
            phase: 'watermark',
            current: 1,
            total: 1,
            percent: 100,
        });
    }
    const endTime = performance.now();
    const totalTimeMs = endTime - startTime;
    return {
        success: errors.length === 0,
        config: validatedConfig,
        trajectory,
        frameCount: frames.length,
        frames: validatedConfig.outputFormat !== 'json' ? frames : undefined,
        audioSamples,
        watermarkKeys,
        metrics: {
            totalTimeMs,
            avgFrameTimeMs: totalFrameTime / Math.max(1, totalFrames),
            peakMemoryMB,
        },
        errors,
    };
}
/**
 * Generate video frames as async iterator (streaming)
 * For memory-efficient processing of large videos
 */
async function* streamVideoFrames(config = {}, watermarkConfig = {}, seed = Date.now()) {
    const validatedConfig = validateConfig(config);
    const validatedWatermark = { ...types_js_1.DEFAULT_WATERMARK_CONFIG, ...watermarkConfig };
    // Get fractal config
    const fractalConfig = types_js_1.TONGUE_FRACTAL_CONFIGS[validatedConfig.tongue];
    const finalFractalConfig = {
        ...fractalConfig,
        mode: validatedConfig.fractalMode,
    };
    // Generate trajectory
    const trajectory = (0, trajectory_js_1.generateTrajectory)(validatedConfig.tongue, validatedConfig.duration, validatedConfig.fps, validatedConfig.breathingAmplitude, seed);
    // Generate watermark keys if enabled
    let watermarkKeys;
    if (validatedConfig.enableWatermark) {
        watermarkKeys = (0, watermark_js_1.generateWatermarkKeys)(validatedWatermark);
    }
    // Stream frames one at a time
    for (let i = 0; i < trajectory.points.length; i++) {
        const timestamp = i / validatedConfig.fps;
        const poincareState = trajectory.points[i];
        const frame = generateFrame(i, timestamp, poincareState, finalFractalConfig, validatedConfig, watermarkKeys);
        yield frame;
        // Yield to event loop
        await new Promise((resolve) => setTimeout(resolve, 0));
    }
}
/**
 * Validate a generated video for integrity
 */
function validateVideo(result) {
    const errors = [...result.errors];
    // Check frame count
    const expectedFrames = Math.ceil(result.config.duration * result.config.fps);
    if (result.frameCount !== expectedFrames) {
        errors.push(`Frame count mismatch: expected ${expectedFrames}, got ${result.frameCount}`);
    }
    // Check trajectory
    if (result.trajectory.points.length !== result.frameCount) {
        errors.push(`Trajectory length mismatch: ${result.trajectory.points.length} vs ${result.frameCount}`);
    }
    // Check frames if present
    if (result.frames) {
        // Check frames array length matches frameCount
        if (result.frames.length !== result.frameCount) {
            errors.push(`Frames array length mismatch: expected ${result.frameCount}, got ${result.frames.length}`);
        }
        for (let i = 0; i < result.frames.length; i++) {
            const frame = result.frames[i];
            // Check dimensions
            if (frame.width !== result.config.width || frame.height !== result.config.height) {
                errors.push(`Frame ${i} dimension mismatch`);
            }
            // Check data size
            const expectedSize = frame.width * frame.height * 4; // RGBA
            if (frame.data.length !== expectedSize) {
                errors.push(`Frame ${i} data size mismatch: expected ${expectedSize}, got ${frame.data.length}`);
            }
            // Check Poincaré state is in ball
            let normSq = 0;
            for (const v of frame.poincareState) {
                normSq += v * v;
            }
            if (normSq >= 1) {
                errors.push(`Frame ${i} Poincaré state outside ball`);
            }
        }
    }
    // Check audio if present
    if (result.audioSamples) {
        const expectedSamples = Math.ceil(result.config.duration * types_js_1.DEFAULT_AUDIO_CONFIG.sampleRate);
        const tolerance = types_js_1.DEFAULT_AUDIO_CONFIG.sampleRate; // 1 second tolerance
        if (Math.abs(result.audioSamples.length - expectedSamples) > tolerance) {
            errors.push(`Audio sample count mismatch: expected ~${expectedSamples}, got ${result.audioSamples.length}`);
        }
    }
    return errors;
}
/**
 * Export video result to JSON format
 */
function exportToJson(result) {
    // Convert typed arrays to regular arrays for JSON serialization
    const exportable = {
        success: result.success,
        config: result.config,
        trajectory: {
            ...result.trajectory,
            points: result.trajectory.points.map((p) => Array.from(p)),
        },
        frameCount: result.frameCount,
        metrics: result.metrics,
        errors: result.errors,
        // Omit frames and audio for JSON (too large)
        watermarkKeys: result.watermarkKeys
            ? {
                publicKey: result.watermarkKeys.publicKey.map((arr) => Array.from(arr)),
                secretKey: Array.from(result.watermarkKeys.secretKey),
            }
            : undefined,
    };
    return JSON.stringify(exportable, null, 2);
}
//# sourceMappingURL=generator.js.map