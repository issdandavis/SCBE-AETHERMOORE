/**
 * SCBE-AETHERMOORE Hyperbolic Trajectory Generator
 * =================================================
 *
 * Generates smooth trajectories in the 6D Poincaré ball.
 * Trajectories represent semantic intent evolution over time.
 *
 * Hardening: Bounds enforcement, numeric stability, deterministic paths
 */

import type { PoincarePoint, ContextVector, HyperbolicTrajectory } from './types.js';
import type { TongueID } from '../spiralverse/types.js';

/** Small epsilon for numerical stability */
const EPSILON = 1e-10;

/** Maximum norm inside Poincaré ball */
const MAX_BALL_NORM = 0.999;

/** Minimum FPS for trajectory generation */
const MIN_FPS = 1;

/** Maximum FPS for trajectory generation */
const MAX_FPS = 120;

/** Maximum duration in seconds */
const MAX_DURATION = 3600;

/**
 * Clamp a value to [min, max]
 */
function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

/**
 * Validate and sanitize a PoincarePoint to ensure it's inside the ball
 */
export function sanitizePoint(point: PoincarePoint): PoincarePoint {
  const result: PoincarePoint = [0, 0, 0, 0, 0, 0];

  // Copy and sanitize each component
  for (let i = 0; i < 6; i++) {
    const v = point[i];
    result[i] = Number.isFinite(v) ? v : 0;
  }

  // Compute norm
  let normSq = 0;
  for (const v of result) {
    normSq += v * v;
  }
  const norm = Math.sqrt(normSq);

  // Project onto ball if outside
  if (norm >= MAX_BALL_NORM) {
    const scale = MAX_BALL_NORM / (norm + EPSILON);
    for (let i = 0; i < 6; i++) {
      result[i] *= scale;
    }
  }

  return result;
}

/**
 * Convert context vector to Poincaré ball point
 * Maps unbounded context to bounded hyperbolic space
 */
export function contextToPoincarePoint(ctx: ContextVector): PoincarePoint {
  // Normalize each dimension using tanh to map ℝ → (-1, 1)
  const point: PoincarePoint = [
    Math.tanh(ctx.time / 100), // Time scaled
    Math.tanh(ctx.entropy * 2), // Entropy typically [0, 1]
    Math.tanh(ctx.threatLevel * 3), // Threat typically [0, 1]
    Math.tanh((ctx.userId % 1000) / 500 - 1), // User ID modulo mapped
    Math.tanh(ctx.behavioralStability * 2 - 1), // Stability [0, 1] → centered
    Math.tanh(ctx.audioPhase), // Phase typically [-π, π]
  ];

  return sanitizePoint(point);
}

/**
 * Möbius addition in Poincaré ball (6D generalization)
 * u ⊕ v = ((1 + 2⟨u,v⟩ + ‖v‖²)u + (1 - ‖u‖²)v) / (1 + 2⟨u,v⟩ + ‖u‖²‖v‖²)
 */
export function mobiusAdd6D(u: PoincarePoint, v: PoincarePoint): PoincarePoint {
  let uv = 0; // dot product
  let uNormSq = 0;
  let vNormSq = 0;

  for (let i = 0; i < 6; i++) {
    uv += u[i] * v[i];
    uNormSq += u[i] * u[i];
    vNormSq += v[i] * v[i];
  }

  const numeratorCoeffU = 1 + 2 * uv + vNormSq;
  const numeratorCoeffV = 1 - uNormSq;
  const denominator = 1 + 2 * uv + uNormSq * vNormSq + EPSILON;

  const result: PoincarePoint = [0, 0, 0, 0, 0, 0];
  for (let i = 0; i < 6; i++) {
    result[i] = (numeratorCoeffU * u[i] + numeratorCoeffV * v[i]) / denominator;
  }

  return sanitizePoint(result);
}

/**
 * Hyperbolic distance in 6D Poincaré ball
 * d_H(u,v) = arcosh(1 + 2‖u-v‖²/((1-‖u‖²)(1-‖v‖²)))
 */
export function hyperbolicDistance6D(u: PoincarePoint, v: PoincarePoint): number {
  let diffNormSq = 0;
  let uNormSq = 0;
  let vNormSq = 0;

  for (let i = 0; i < 6; i++) {
    const diff = u[i] - v[i];
    diffNormSq += diff * diff;
    uNormSq += u[i] * u[i];
    vNormSq += v[i] * v[i];
  }

  const uFactor = Math.max(EPSILON, 1 - uNormSq);
  const vFactor = Math.max(EPSILON, 1 - vNormSq);

  const arg = 1 + (2 * diffNormSq) / (uFactor * vFactor);
  return Math.acosh(Math.max(1, arg));
}

/**
 * Exponential map at origin: maps tangent vector to ball
 * exp_0(v) = tanh(‖v‖/2) · v/‖v‖
 */
export function expMap0_6D(v: PoincarePoint): PoincarePoint {
  let normSq = 0;
  for (const x of v) normSq += x * x;
  const norm = Math.sqrt(normSq);

  if (norm < EPSILON) {
    return [0, 0, 0, 0, 0, 0];
  }

  const factor = Math.tanh(norm / 2) / norm;
  const result: PoincarePoint = [0, 0, 0, 0, 0, 0];
  for (let i = 0; i < 6; i++) {
    result[i] = v[i] * factor;
  }

  return sanitizePoint(result);
}

/**
 * Logarithmic map at origin: maps ball point to tangent space
 * log_0(p) = 2 · arctanh(‖p‖) · p/‖p‖
 */
export function logMap0_6D(p: PoincarePoint): PoincarePoint {
  let normSq = 0;
  for (const x of p) normSq += x * x;
  const norm = Math.sqrt(normSq);

  if (norm < EPSILON) {
    return [0, 0, 0, 0, 0, 0];
  }

  const atanh = 0.5 * Math.log((1 + norm) / (1 - norm + EPSILON));
  const factor = (2 * atanh) / norm;

  const result: PoincarePoint = [0, 0, 0, 0, 0, 0];
  for (let i = 0; i < 6; i++) {
    result[i] = p[i] * factor;
  }

  return result; // Don't sanitize - this is in tangent space, unbounded
}

/**
 * Geodesic interpolation between two points in Poincaré ball
 * Uses the geodesic formula: γ(t) = u ⊕ (t · (-u ⊕ v))
 */
export function geodesicInterpolate(
  u: PoincarePoint,
  v: PoincarePoint,
  t: number
): PoincarePoint {
  t = clamp(t, 0, 1);

  // Compute -u
  const negU: PoincarePoint = [0, 0, 0, 0, 0, 0];
  for (let i = 0; i < 6; i++) {
    negU[i] = -u[i];
  }

  // Compute -u ⊕ v (gyrovector from u to v)
  const gyro = mobiusAdd6D(negU, v);

  // Scale by t (in tangent space)
  const logGyro = logMap0_6D(gyro);
  const scaledLog: PoincarePoint = [0, 0, 0, 0, 0, 0];
  for (let i = 0; i < 6; i++) {
    scaledLog[i] = logGyro[i] * t;
  }

  // Map back to ball
  const scaledGyro = expMap0_6D(scaledLog);

  // u ⊕ (scaled gyro)
  return mobiusAdd6D(u, scaledGyro);
}

/**
 * Generate breathing modulation for trajectory
 * Implements Layer 6 breathing transform
 */
function breathingModulation(
  point: PoincarePoint,
  time: number,
  amplitude: number,
  omega: number
): PoincarePoint {
  amplitude = clamp(amplitude, 0, 0.1); // A4: bounded amplitude

  let normSq = 0;
  for (const x of point) normSq += x * x;
  const norm = Math.sqrt(normSq);

  if (norm < EPSILON) return point;

  // New radius with breathing
  const newRadius = Math.tanh(norm + amplitude * Math.sin(omega * time));

  const result: PoincarePoint = [0, 0, 0, 0, 0, 0];
  const scale = newRadius / norm;
  for (let i = 0; i < 6; i++) {
    result[i] = point[i] * scale;
  }

  return sanitizePoint(result);
}

/**
 * Generate phase modulation (rotation in dimension pairs)
 * Implements Layer 7 phase transform
 */
function phaseModulation(
  point: PoincarePoint,
  theta: number,
  plane: [number, number] = [0, 1]
): PoincarePoint {
  const [i, j] = plane;
  if (i < 0 || i >= 6 || j < 0 || j >= 6 || i === j) {
    return point;
  }

  const result: PoincarePoint = [...point] as PoincarePoint;
  const cos = Math.cos(theta);
  const sin = Math.sin(theta);

  result[i] = point[i] * cos - point[j] * sin;
  result[j] = point[i] * sin + point[j] * cos;

  return sanitizePoint(result);
}

/**
 * Generate waypoints for trajectory based on Sacred Tongue
 * Each tongue has characteristic movement patterns
 */
function generateWaypoints(
  tongue: TongueID,
  duration: number,
  seed: number
): PoincarePoint[] {
  const waypoints: PoincarePoint[] = [];

  // Tongue-specific seed offset to ensure different tongues produce different patterns
  const tongueOffsets: Record<TongueID, number> = {
    ko: 0,
    av: 100000,
    ru: 200000,
    ca: 300000,
    um: 400000,
    dr: 500000,
  };

  // Seeded random for determinism, incorporating tongue
  let rng = seed + tongueOffsets[tongue];
  const random = (): number => {
    rng = (rng * 1103515245 + 12345) & 0x7fffffff;
    return rng / 0x7fffffff;
  };

  // Number of waypoints based on duration
  const waypointCount = Math.max(2, Math.floor(duration / 2));

  // Tongue-specific patterns
  const patterns: Record<TongueID, () => PoincarePoint> = {
    ko: () => {
      // Kor'aelin: Pure, centered, minimal movement
      return sanitizePoint([
        0.1 * (random() - 0.5),
        0.1 * (random() - 0.5),
        0.05 * random(), // Low threat
        0.1 * (random() - 0.5),
        0.7 + 0.2 * random(), // High stability
        random() * Math.PI,
      ]);
    },
    av: () => {
      // Avali: Rich, exploratory, moderate depth
      return sanitizePoint([
        0.4 * (random() - 0.5),
        0.4 * (random() - 0.5),
        0.3 * random(),
        0.3 * (random() - 0.5),
        0.5 + 0.3 * random(),
        random() * 2 * Math.PI,
      ]);
    },
    ru: () => {
      // Runethic: Dissonant, tense, sharp movements
      return sanitizePoint([
        0.6 * (random() - 0.5),
        0.6 * (random() - 0.5),
        0.5 + 0.3 * random(), // Higher threat
        0.5 * (random() - 0.5),
        0.3 + 0.3 * random(), // Lower stability
        random() * 2 * Math.PI,
      ]);
    },
    ca: () => {
      // Cassisivadan: Alien, boundary-seeking
      return sanitizePoint([
        0.8 * (random() - 0.5),
        0.8 * (random() - 0.5),
        0.4 + 0.4 * random(),
        0.7 * (random() - 0.5),
        0.2 + 0.4 * random(),
        random() * 2 * Math.PI,
      ]);
    },
    um: () => {
      // Umbroth: Mysterious, deep, slow
      return sanitizePoint([
        0.3 * (random() - 0.5),
        0.3 * (random() - 0.5),
        0.2 + 0.2 * random(),
        0.2 * (random() - 0.5),
        0.4 + 0.4 * random(),
        random() * Math.PI / 2,
      ]);
    },
    dr: () => {
      // Draumric: Structured, rhythmic
      const angle = (waypoints.length / waypointCount) * 2 * Math.PI;
      return sanitizePoint([
        0.4 * Math.cos(angle),
        0.4 * Math.sin(angle),
        0.3,
        0.3 * Math.sin(angle * 2),
        0.6,
        angle,
      ]);
    },
  };

  const generator = patterns[tongue] || patterns.av;

  // Starting point near origin
  waypoints.push(sanitizePoint([0.1, 0, 0, 0, 0.8, 0]));

  // Generate intermediate waypoints
  for (let i = 1; i < waypointCount - 1; i++) {
    waypoints.push(generator());
  }

  // Ending point - return toward center
  waypoints.push(sanitizePoint([0.05, 0.05, 0, 0, 0.9, 0]));

  return waypoints;
}

/**
 * Generate complete hyperbolic trajectory
 *
 * @param tongue - Sacred Tongue determining movement character
 * @param duration - Duration in seconds
 * @param fps - Frames per second
 * @param breathingAmplitude - L6 breathing intensity [0, 0.1]
 * @param seed - Random seed for determinism
 * @returns Trajectory with all frame points
 */
export function generateTrajectory(
  tongue: TongueID,
  duration: number,
  fps: number,
  breathingAmplitude: number = 0.05,
  seed: number = Date.now()
): HyperbolicTrajectory {
  // Validate and clamp inputs
  duration = clamp(duration, 0.1, MAX_DURATION);
  fps = clamp(Math.floor(fps), MIN_FPS, MAX_FPS);
  breathingAmplitude = clamp(breathingAmplitude, 0, 0.1);

  const totalFrames = Math.ceil(duration * fps);
  const points: PoincarePoint[] = [];

  // Generate waypoints
  const waypoints = generateWaypoints(tongue, duration, seed);

  // Interpolate between waypoints with geodesic paths
  for (let frame = 0; frame < totalFrames; frame++) {
    const time = frame / fps;
    const progress = time / duration;

    // Find which waypoint segment we're in
    const waypointProgress = progress * (waypoints.length - 1);
    const waypointIdx = Math.floor(waypointProgress);
    const segmentT = waypointProgress - waypointIdx;

    const startWaypoint = waypoints[Math.min(waypointIdx, waypoints.length - 1)];
    const endWaypoint = waypoints[Math.min(waypointIdx + 1, waypoints.length - 1)];

    // Geodesic interpolation with easing
    const easedT = segmentT * segmentT * (3 - 2 * segmentT); // Smoothstep
    let point = geodesicInterpolate(startWaypoint, endWaypoint, easedT);

    // Apply breathing (L6)
    point = breathingModulation(point, time, breathingAmplitude, 2 * Math.PI);

    // Apply phase modulation (L7) - rotate in different planes over time
    const phaseAngle = time * 0.5;
    point = phaseModulation(point, phaseAngle, [0, 1]);
    point = phaseModulation(point, phaseAngle * 0.7, [2, 3]);
    point = phaseModulation(point, phaseAngle * 0.3, [4, 5]);

    points.push(point);
  }

  return {
    points,
    duration,
    fps,
    tongue,
  };
}

/**
 * Validate trajectory for integrity
 * Returns errors if trajectory is invalid
 */
export function validateTrajectory(trajectory: HyperbolicTrajectory): string[] {
  const errors: string[] = [];

  if (!trajectory.points || trajectory.points.length === 0) {
    errors.push('Trajectory has no points');
    return errors;
  }

  const expectedFrames = Math.ceil(trajectory.duration * trajectory.fps);
  if (trajectory.points.length !== expectedFrames) {
    errors.push(
      `Frame count mismatch: expected ${expectedFrames}, got ${trajectory.points.length}`
    );
  }

  // Validate each point is inside the ball
  for (let i = 0; i < trajectory.points.length; i++) {
    const point = trajectory.points[i];
    if (point.length !== 6) {
      errors.push(`Point ${i} has wrong dimension: ${point.length}`);
      continue;
    }

    let normSq = 0;
    for (const v of point) {
      if (!Number.isFinite(v)) {
        errors.push(`Point ${i} contains non-finite value`);
        break;
      }
      normSq += v * v;
    }

    if (normSq >= 1) {
      errors.push(`Point ${i} is outside Poincaré ball: norm=${Math.sqrt(normSq)}`);
    }
  }

  return errors;
}
