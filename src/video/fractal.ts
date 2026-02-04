/**
 * SCBE-AETHERMOORE Fractal Renderer
 * ==================================
 *
 * Hardened fractal rendering with hyperbolic modulation.
 * Supports Mandelbrot, Julia, Burning Ship, and hybrid modes.
 *
 * Security: Input validation, numeric bounds, deterministic output
 */

import type { Complex, FractalMode, TongueFractalConfig, PoincarePoint } from './types.js';

/** Maximum iteration limit to prevent DoS */
const MAX_ITERATIONS_LIMIT = 10000;

/** Minimum bailout to ensure convergence detection */
const MIN_BAILOUT = 1.5;

/** Maximum bailout to prevent overflow */
const MAX_BAILOUT = 1e6;

/**
 * Validate and clamp complex number to safe bounds
 */
function clampComplex(c: Complex, maxMagnitude: number = 4): Complex {
  const mag = Math.sqrt(c.re * c.re + c.im * c.im);
  if (mag > maxMagnitude) {
    const scale = maxMagnitude / mag;
    return { re: c.re * scale, im: c.im * scale };
  }
  if (!Number.isFinite(c.re) || !Number.isFinite(c.im)) {
    return { re: 0, im: 0 };
  }
  return c;
}

/**
 * Complex multiplication: (a + bi)(c + di) = (ac - bd) + (ad + bc)i
 */
function complexMul(a: Complex, b: Complex): Complex {
  return {
    re: a.re * b.re - a.im * b.im,
    im: a.re * b.im + a.im * b.re,
  };
}

/**
 * Complex addition
 */
function complexAdd(a: Complex, b: Complex): Complex {
  return { re: a.re + b.re, im: a.im + b.im };
}

/**
 * Complex magnitude squared (avoids sqrt for performance)
 */
function complexMagSq(c: Complex): number {
  return c.re * c.re + c.im * c.im;
}

/**
 * Mandelbrot iteration: z_{n+1} = z_n^2 + c
 * Returns normalized iteration count for smooth coloring
 */
export function mandelbrotIteration(c: Complex, maxIter: number, bailout: number): number {
  // Validate inputs
  maxIter = Math.min(Math.max(1, Math.floor(maxIter)), MAX_ITERATIONS_LIMIT);
  bailout = Math.min(Math.max(MIN_BAILOUT, bailout), MAX_BAILOUT);
  const bailoutSq = bailout * bailout;

  let z: Complex = { re: 0, im: 0 };

  // Cardioid/bulb check for optimization
  const q = (c.re - 0.25) ** 2 + c.im * c.im;
  if (q * (q + (c.re - 0.25)) <= 0.25 * c.im * c.im) {
    return maxIter; // In main cardioid
  }
  if ((c.re + 1) ** 2 + c.im * c.im <= 0.0625) {
    return maxIter; // In period-2 bulb
  }

  for (let i = 0; i < maxIter; i++) {
    // z = z^2 + c
    const zRe = z.re * z.re - z.im * z.im + c.re;
    const zIm = 2 * z.re * z.im + c.im;
    z = { re: zRe, im: zIm };

    const magSq = complexMagSq(z);
    if (magSq > bailoutSq) {
      // Smooth iteration count using continuous potential
      const log_zn = Math.log(magSq) / 2;
      const nu = Math.log(log_zn / Math.log(bailout)) / Math.log(2);
      return Math.max(0, i + 1 - nu);
    }
  }

  return maxIter;
}

/**
 * Julia iteration: z_{n+1} = z_n^2 + c (c is fixed, z_0 varies)
 */
export function juliaIteration(z0: Complex, c: Complex, maxIter: number, bailout: number): number {
  maxIter = Math.min(Math.max(1, Math.floor(maxIter)), MAX_ITERATIONS_LIMIT);
  bailout = Math.min(Math.max(MIN_BAILOUT, bailout), MAX_BAILOUT);
  const bailoutSq = bailout * bailout;

  let z = clampComplex(z0);
  c = clampComplex(c);

  for (let i = 0; i < maxIter; i++) {
    const zRe = z.re * z.re - z.im * z.im + c.re;
    const zIm = 2 * z.re * z.im + c.im;
    z = { re: zRe, im: zIm };

    const magSq = complexMagSq(z);
    if (magSq > bailoutSq) {
      const log_zn = Math.log(magSq) / 2;
      const nu = Math.log(log_zn / Math.log(bailout)) / Math.log(2);
      return Math.max(0, i + 1 - nu);
    }
  }

  return maxIter;
}

/**
 * Burning Ship iteration: z_{n+1} = (|Re(z_n)| + i|Im(z_n)|)^2 + c
 * Creates ship-like fractal patterns
 */
export function burningShipIteration(c: Complex, maxIter: number, bailout: number): number {
  maxIter = Math.min(Math.max(1, Math.floor(maxIter)), MAX_ITERATIONS_LIMIT);
  bailout = Math.min(Math.max(MIN_BAILOUT, bailout), MAX_BAILOUT);
  const bailoutSq = bailout * bailout;

  let z: Complex = { re: 0, im: 0 };

  for (let i = 0; i < maxIter; i++) {
    // Take absolute values before squaring
    const absRe = Math.abs(z.re);
    const absIm = Math.abs(z.im);

    const zRe = absRe * absRe - absIm * absIm + c.re;
    const zIm = 2 * absRe * absIm + c.im;
    z = { re: zRe, im: zIm };

    const magSq = complexMagSq(z);
    if (magSq > bailoutSq) {
      const log_zn = Math.log(magSq) / 2;
      const nu = Math.log(log_zn / Math.log(bailout)) / Math.log(2);
      return Math.max(0, i + 1 - nu);
    }
  }

  return maxIter;
}

/**
 * Modulate fractal parameters based on Poincaré state
 * Creates hyperbolic breathing effect
 */
export function modulateFractalParams(
  config: TongueFractalConfig,
  poincareState: PoincarePoint,
  chaosStrength: number,
  breathingAmplitude: number,
  time: number
): { c: Complex; zoom: number; rotation: number } {
  // Clamp inputs
  chaosStrength = Math.max(0, Math.min(1, chaosStrength));
  breathingAmplitude = Math.max(0, Math.min(0.1, breathingAmplitude)); // A4: bounded amplitude

  // Compute Poincaré distance from origin (hyperbolic metric)
  let normSq = 0;
  for (const v of poincareState) {
    normSq += v * v;
  }
  const norm = Math.sqrt(normSq);
  const clampedNorm = Math.min(norm, 0.99); // Stay inside ball

  // Hyperbolic distance from origin: 2 * arctanh(||p||)
  const hyperbolicDist = 2 * Math.atanh(clampedNorm);

  // Breathing modulation (L6 transform)
  const breathPhase = Math.sin(2 * Math.PI * time) * breathingAmplitude;
  const modulatedDist = Math.tanh(hyperbolicDist + breathPhase);

  // Modulate c parameter based on hyperbolic state
  const angle = Math.atan2(poincareState[1], poincareState[0]);
  const cModulation = chaosStrength * modulatedDist * 0.1;

  const c: Complex = {
    re: config.c.re + cModulation * Math.cos(angle),
    im: config.c.im + cModulation * Math.sin(angle),
  };

  // Zoom based on distance (closer to boundary = deeper zoom)
  const zoom = 1 + modulatedDist * chaosStrength;

  // Rotation based on phase dimension
  const rotation = poincareState[5] * Math.PI * chaosStrength;

  return { c: clampComplex(c), zoom, rotation };
}

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
export function renderFractalFrame(
  width: number,
  height: number,
  config: TongueFractalConfig,
  poincareState: PoincarePoint,
  chaosStrength: number,
  breathingAmplitude: number,
  time: number
): Float32Array {
  // Validate dimensions
  width = Math.max(1, Math.min(4096, Math.floor(width)));
  height = Math.max(1, Math.min(4096, Math.floor(height)));

  const { c, zoom, rotation } = modulateFractalParams(
    config,
    poincareState,
    chaosStrength,
    breathingAmplitude,
    time
  );

  const pixels = new Float32Array(width * height);
  const maxIter = config.maxIterations;
  const bailout = config.bailout;

  // Coordinate mapping with zoom and rotation
  const cosR = Math.cos(rotation);
  const sinR = Math.sin(rotation);
  const scale = 3.0 / (Math.min(width, height) * zoom);

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      // Map pixel to complex plane
      let re = (x - width / 2) * scale;
      let im = (y - height / 2) * scale;

      // Apply rotation
      const rotRe = re * cosR - im * sinR;
      const rotIm = re * sinR + im * cosR;

      let iterCount: number;

      switch (config.mode) {
        case 'mandelbrot':
          iterCount = mandelbrotIteration({ re: rotRe, im: rotIm }, maxIter, bailout);
          break;
        case 'julia':
          iterCount = juliaIteration({ re: rotRe, im: rotIm }, c, maxIter, bailout);
          break;
        case 'burning_ship':
          iterCount = burningShipIteration({ re: rotRe, im: rotIm }, maxIter, bailout);
          break;
        case 'hybrid':
          // Blend Mandelbrot and Julia based on hyperbolic distance
          const mIter = mandelbrotIteration({ re: rotRe, im: rotIm }, maxIter, bailout);
          const jIter = juliaIteration({ re: rotRe, im: rotIm }, c, maxIter, bailout);
          const blend = chaosStrength;
          iterCount = mIter * (1 - blend) + jIter * blend;
          break;
        default:
          iterCount = mandelbrotIteration({ re: rotRe, im: rotIm }, maxIter, bailout);
      }

      // Normalize to [0, 1]
      pixels[y * width + x] = iterCount / maxIter;
    }
  }

  return pixels;
}

/**
 * Apply colormap to normalized iteration counts
 * Returns RGBA pixel data
 */
export function applyColormap(
  normalized: Float32Array,
  colormap: string,
  width: number,
  height: number
): Uint8ClampedArray {
  const rgba = new Uint8ClampedArray(width * height * 4);

  for (let i = 0; i < normalized.length; i++) {
    const t = normalized[i];
    let r: number, g: number, b: number;

    switch (colormap) {
      case 'plasma':
        r = Math.floor(255 * plasmaR(t));
        g = Math.floor(255 * plasmaG(t));
        b = Math.floor(255 * plasmaB(t));
        break;
      case 'viridis':
        r = Math.floor(255 * viridisR(t));
        g = Math.floor(255 * viridisG(t));
        b = Math.floor(255 * viridisB(t));
        break;
      case 'inferno':
        r = Math.floor(255 * infernoR(t));
        g = Math.floor(255 * infernoG(t));
        b = Math.floor(255 * infernoB(t));
        break;
      case 'magma':
        r = Math.floor(255 * magmaR(t));
        g = Math.floor(255 * magmaG(t));
        b = Math.floor(255 * magmaB(t));
        break;
      case 'bone':
        // Grayscale with slight blue tint
        const gray = Math.floor(255 * t);
        r = Math.floor(gray * 0.9);
        g = Math.floor(gray * 0.95);
        b = gray;
        break;
      case 'twilight':
        // Cyclic colormap
        const phase = t * 2 * Math.PI;
        r = Math.floor(127.5 * (1 + Math.sin(phase)));
        g = Math.floor(127.5 * (1 + Math.sin(phase + (2 * Math.PI) / 3)));
        b = Math.floor(127.5 * (1 + Math.sin(phase + (4 * Math.PI) / 3)));
        break;
      default:
        // Default grayscale
        r = g = b = Math.floor(255 * t);
    }

    const idx = i * 4;
    rgba[idx] = r;
    rgba[idx + 1] = g;
    rgba[idx + 2] = b;
    rgba[idx + 3] = 255; // Full opacity
  }

  return rgba;
}

// Plasma colormap approximations
function plasmaR(t: number): number {
  return Math.min(1, Math.max(0, 0.05 + 0.93 * t + 0.5 * Math.sin(t * 3.14)));
}
function plasmaG(t: number): number {
  return Math.min(1, Math.max(0, t * t * 0.8));
}
function plasmaB(t: number): number {
  return Math.min(1, Math.max(0, 0.53 - 0.12 * t + 0.55 * t * t));
}

// Viridis colormap approximations
function viridisR(t: number): number {
  return Math.min(1, Math.max(0, 0.27 + 0.005 * t + 0.33 * t * t));
}
function viridisG(t: number): number {
  return Math.min(1, Math.max(0, t * 0.87));
}
function viridisB(t: number): number {
  return Math.min(1, Math.max(0, 0.33 + 0.45 * t - 0.48 * t * t));
}

// Inferno colormap approximations
function infernoR(t: number): number {
  return Math.min(1, Math.max(0, t * 1.5 - 0.4 * t * t));
}
function infernoG(t: number): number {
  return Math.min(1, Math.max(0, t * t * 0.75));
}
function infernoB(t: number): number {
  return Math.min(1, Math.max(0, 0.3 - 0.7 * t + 1.4 * t * t - 0.7 * t * t * t));
}

// Magma colormap approximations
function magmaR(t: number): number {
  return Math.min(1, Math.max(0, t + 0.1 * Math.sin(t * 6)));
}
function magmaG(t: number): number {
  return Math.min(1, Math.max(0, t * t * 0.6));
}
function magmaB(t: number): number {
  return Math.min(1, Math.max(0, 0.3 + 0.6 * t - 0.3 * t * t));
}
