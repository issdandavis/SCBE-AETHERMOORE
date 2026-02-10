/**
 * SCBE-AETHERMOORE Fractal Renderer
 * ==================================
 *
 * Hardened fractal rendering with hyperbolic modulation.
 * Supports Mandelbrot, Julia, Burning Ship, and hybrid modes.
 *
 * Security: Input validation, numeric bounds, deterministic output
 */
import type { Complex, TongueFractalConfig, PoincarePoint } from './types.js';
/**
 * Mandelbrot iteration: z_{n+1} = z_n^2 + c
 * Returns normalized iteration count for smooth coloring
 */
export declare function mandelbrotIteration(c: Complex, maxIter: number, bailout: number): number;
/**
 * Julia iteration: z_{n+1} = z_n^2 + c (c is fixed, z_0 varies)
 */
export declare function juliaIteration(z0: Complex, c: Complex, maxIter: number, bailout: number): number;
/**
 * Burning Ship iteration: z_{n+1} = (|Re(z_n)| + i|Im(z_n)|)^2 + c
 * Creates ship-like fractal patterns
 */
export declare function burningShipIteration(c: Complex, maxIter: number, bailout: number): number;
/**
 * Modulate fractal parameters based on Poincaré state
 * Creates hyperbolic breathing effect
 */
export declare function modulateFractalParams(config: TongueFractalConfig, poincareState: PoincarePoint, chaosStrength: number, breathingAmplitude: number, time: number): {
    c: Complex;
    zoom: number;
    rotation: number;
};
/**
 * Render a single fractal frame
 *
 * @param width - Frame width in pixels
 * @param height - Frame height in pixels
 * @param config - Fractal configuration
 * @param poincareState - Current Poincaré ball state
 * @param chaosStrength - How much hyperbolic state affects rendering
 * @param breathingAmplitude - Breathing intensity
 * @param time - Current time in seconds
 * @returns Normalized iteration counts (0-1) for each pixel
 */
export declare function renderFractalFrame(width: number, height: number, config: TongueFractalConfig, poincareState: PoincarePoint, chaosStrength: number, breathingAmplitude: number, time: number): Float32Array;
/**
 * Apply colormap to normalized iteration counts
 * Returns RGBA pixel data
 */
export declare function applyColormap(normalized: Float32Array, colormap: string, width: number, height: number): Uint8ClampedArray;
//# sourceMappingURL=fractal.d.ts.map