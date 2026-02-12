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
/**
 * Validate and sanitize a PoincarePoint to ensure it's inside the ball
 */
export declare function sanitizePoint(point: PoincarePoint): PoincarePoint;
/**
 * Convert context vector to Poincaré ball point
 * Maps unbounded context to bounded hyperbolic space
 */
export declare function contextToPoincarePoint(ctx: ContextVector): PoincarePoint;
/**
 * Möbius addition in Poincaré ball (6D generalization)
 * u ⊕ v = ((1 + 2⟨u,v⟩ + ‖v‖²)u + (1 - ‖u‖²)v) / (1 + 2⟨u,v⟩ + ‖u‖²‖v‖²)
 */
export declare function mobiusAdd6D(u: PoincarePoint, v: PoincarePoint): PoincarePoint;
/**
 * Hyperbolic distance in 6D Poincaré ball
 * d_H(u,v) = arcosh(1 + 2‖u-v‖²/((1-‖u‖²)(1-‖v‖²)))
 */
export declare function hyperbolicDistance6D(u: PoincarePoint, v: PoincarePoint): number;
/**
 * Exponential map at origin: maps tangent vector to ball
 * exp_0(v) = tanh(‖v‖/2) · v/‖v‖
 */
export declare function expMap0_6D(v: PoincarePoint): PoincarePoint;
/**
 * Logarithmic map at origin: maps ball point to tangent space
 * log_0(p) = 2 · arctanh(‖p‖) · p/‖p‖
 */
export declare function logMap0_6D(p: PoincarePoint): PoincarePoint;
/**
 * Geodesic interpolation between two points in Poincaré ball
 * Uses the geodesic formula: γ(t) = u ⊕ (t · (-u ⊕ v))
 */
export declare function geodesicInterpolate(u: PoincarePoint, v: PoincarePoint, t: number): PoincarePoint;
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
export declare function generateTrajectory(tongue: TongueID, duration: number, fps: number, breathingAmplitude?: number, seed?: number): HyperbolicTrajectory;
/**
 * Validate trajectory for integrity
 * Returns errors if trajectory is invalid
 */
export declare function validateTrajectory(trajectory: HyperbolicTrajectory): string[];
//# sourceMappingURL=trajectory.d.ts.map