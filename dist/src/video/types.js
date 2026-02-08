"use strict";
/**
 * SCBE-AETHERMOORE Video Generation Types
 * ========================================
 *
 * Type definitions for hyperbolic video generation pipeline.
 * Integrates Sacred Tongues, Poincaré embeddings, and fractal chaos.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_WATERMARK_CONFIG = exports.DEFAULT_AUDIO_CONFIG = exports.DEFAULT_VIDEO_CONFIG = exports.TONGUE_FRACTAL_CONFIGS = void 0;
/**
 * Default fractal configurations for each Sacred Tongue
 */
exports.TONGUE_FRACTAL_CONFIGS = {
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
/**
 * Default video configuration
 */
exports.DEFAULT_VIDEO_CONFIG = {
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
/**
 * Default audio configuration
 */
exports.DEFAULT_AUDIO_CONFIG = {
    sampleRate: 44100,
    baseFrequency: 220, // A3
    maxFrequency: 880, // A5
    harmonicCount: 8,
    goldenRatioWeight: true,
};
/**
 * Default watermark configuration
 */
exports.DEFAULT_WATERMARK_CONFIG = {
    dimension: 16,
    modulus: 97,
    errorBound: 1,
};
//# sourceMappingURL=types.js.map