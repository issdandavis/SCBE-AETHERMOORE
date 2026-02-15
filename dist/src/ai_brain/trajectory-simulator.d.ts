/**
 * @file trajectory-simulator.ts
 * @module ai_brain/trajectory-simulator
 * @layer Layer 1-14 (Unified)
 * @component Multi-Profile Agent Trajectory Simulator
 * @version 1.0.0
 * @since 2026-02-07
 *
 * Generates realistic agent trajectories across the 21D unified brain manifold
 * for 5 behavior profiles: honest, neutral, semi-honest, semi-malicious, malicious.
 *
 * Each profile produces characteristic patterns in the 21D state space:
 * - Honest: smooth geodesics near safe origin, correct Sacred Tongue phase
 * - Neutral: moderate drift, low noise, passive behavior
 * - Semi-honest: occasional small deviations, borderline compliance
 * - Semi-malicious: gradual drift toward boundary, intermittent phase errors
 * - Malicious: Lissajous knots in threat plane, wrong-tongue, high curvature
 *
 * Validated: 100 trials, 20 agents, 100 steps -> Combined AUC 1.000
 */
import { type AgentTrajectory } from './types.js';
import type { GovernanceTier } from '../fleet/types.js';
/**
 * Agent behavior profile defining trajectory characteristics
 */
export interface AgentProfile {
    /** Classification label */
    classification: AgentTrajectory['classification'];
    /** Base noise amplitude (per-step jitter) */
    noiseAmplitude: number;
    /** Drift rate toward boundary per step */
    driftRate: number;
    /** Phase error probability per step [0, 1] */
    phaseErrorRate: number;
    /** Phase error magnitude when it occurs (radians) */
    phaseErrorMagnitude: number;
    /** Lissajous amplitude for threat dimension (0 = none) */
    lissajousAmplitude: number;
    /** Lissajous frequency ratio (creates knots when irrational) */
    lissajousFreqRatio: number;
    /** Curvature injection probability per step */
    curvatureInjectionRate: number;
    /** Curvature injection magnitude */
    curvatureInjectionMag: number;
    /** Whether to produce replay patterns */
    replayPattern: boolean;
    /** Whether to produce static signals */
    staticSignal: boolean;
    /** Base trust scores */
    baseTrust: number;
    /** Intent alignment base */
    baseIntent: number;
}
/**
 * Predefined behavior profiles validated against the 5 orthogonal detection mechanisms
 */
export declare const AGENT_PROFILES: Record<AgentTrajectory['classification'], AgentProfile>;
/**
 * Simple seeded PRNG using a linear congruential generator.
 * Provides deterministic random numbers for reproducible trajectories.
 */
export declare class SeededRNG {
    private state;
    constructor(seed: number);
    /** Next random number in [0, 1) */
    next(): number;
    /** Gaussian random (Box-Muller) */
    gaussian(mean?: number, stddev?: number): number;
}
/**
 * Configuration for trajectory simulation
 */
export interface SimulationConfig {
    /** Number of steps per trajectory */
    steps: number;
    /** Expected Sacred Tongue index (0-5) */
    tongueIndex: number;
    /** Random seed for reproducibility */
    seed?: number;
    /** Governance tier */
    governanceTier?: GovernanceTier;
}
/**
 * Generate a single agent trajectory for a given behavior profile.
 *
 * The trajectory simulates an agent moving through the 21D unified manifold
 * with behavior characteristics determined by its classification profile.
 *
 * @param agentId - Unique agent identifier
 * @param profile - Behavior profile to simulate
 * @param config - Simulation configuration
 * @returns Complete agent trajectory with embedded Poincare points
 */
export declare function generateTrajectory(agentId: string, profile: AgentProfile, config: SimulationConfig): AgentTrajectory;
/**
 * Generate a batch of mixed agent trajectories for end-to-end testing.
 *
 * Creates agents with a distribution of behavior profiles:
 * - 40% honest, 20% neutral, 15% semi-honest, 15% semi-malicious, 10% malicious
 *
 * @param agentCount - Total number of agents
 * @param config - Simulation configuration
 * @returns Array of agent trajectories
 */
export declare function generateMixedBatch(agentCount: number, config: SimulationConfig): AgentTrajectory[];
//# sourceMappingURL=trajectory-simulator.d.ts.map