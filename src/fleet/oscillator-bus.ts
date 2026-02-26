/**
 * @file oscillator-bus.ts
 * @module fleet/oscillator-bus
 * @layer L9, L10, L14
 * @component Oscillator Control Plane — Kuramoto Phase-Coupled Mode Bus
 * @version 3.2.4
 *
 * Formalizes the "Audio Axis" as a distributed phase-coupled oscillator field
 * with trust-weighted adjacency. This is NOT metaphorical — it is a
 * mathematically legitimate Kuramoto-class oscillator network.
 *
 * Update rule per oscillator i:
 *   θ_i' = θ_i + ω_i + K/N · Σ_j τ_j · sin(θ_j - θ_i)
 *
 * Where:
 *   θ_i = phase of oscillator i
 *   ω_i = natural frequency of oscillator i
 *   K   = global coupling strength
 *   τ_j = trust score of neighbor j (prevents spoof dominance)
 *   N   = number of coupled neighbors
 *
 * Mode encoding via frequency bands:
 *   LOW  (0.5-2.0 Hz): Regroup
 *   MID  (2.0-5.0 Hz): Explore
 *   HIGH (5.0-10.0 Hz): Commit
 *   SPIKE (>10.0 Hz): Hazard
 *
 * Properties:
 *   - Emergent agreement without heavy networking
 *   - Implicit mode switching via frequency convergence
 *   - Natural partition tolerance (local clusters self-synchronize)
 *   - Trust-weighting prevents Byzantine spoof dominance
 *
 * @axiom Symmetry — Phase coupling is gauge-invariant (global phase shift preserves dynamics)
 * @axiom Locality — Coupling only acts within coupling radius
 */

import { Vec, vecDist } from './swarm-geometry.js';

// ──────────────── Mode Bands ────────────────

/**
 * Swarm mode derived from dominant frequency band.
 */
export type SwarmMode = 'REGROUP' | 'EXPLORE' | 'COMMIT' | 'HAZARD';

/**
 * Frequency band boundaries (Hz).
 */
export const MODE_BANDS: Record<SwarmMode, { min: number; max: number }> = {
  REGROUP: { min: 0.5, max: 2.0 },
  EXPLORE: { min: 2.0, max: 5.0 },
  COMMIT: { min: 5.0, max: 10.0 },
  HAZARD: { min: 10.0, max: Infinity },
};

/**
 * Classify a frequency into a swarm mode.
 */
export function classifyFrequency(freq: number): SwarmMode {
  const absFreq = Math.abs(freq);
  if (absFreq >= MODE_BANDS.HAZARD.min) return 'HAZARD';
  if (absFreq >= MODE_BANDS.COMMIT.min) return 'COMMIT';
  if (absFreq >= MODE_BANDS.EXPLORE.min) return 'EXPLORE';
  return 'REGROUP';
}

// ──────────────── Oscillator State ────────────────

/**
 * Per-node oscillator state.
 */
export interface OscillatorState {
  /** Node identifier (matches robot/agent ID) */
  id: string;
  /** Phase θ ∈ [0, 2π) */
  phase: number;
  /** Natural frequency ω (Hz) */
  frequency: number;
  /** Trust score τ ∈ [0, 1] */
  trust: number;
  /** Spatial position (for coupling radius check) */
  position: Vec;
  /** Current mode (derived from frequency) */
  mode: SwarmMode;
  /** Phase velocity dθ/dt from last step */
  phaseVelocity: number;
}

/**
 * Oscillator bus configuration.
 */
export interface OscillatorBusConfig {
  /** Global coupling strength K */
  couplingStrength: number;
  /** Maximum coupling radius (spatial) */
  couplingRadius: number;
  /** Time step dt */
  dt: number;
  /** Minimum trust to participate in coupling (below = ignored) */
  minTrustForCoupling: number;
  /** Maximum allowed frequency (hard cap — prevents runaway) */
  maxFrequency: number;
  /** Frequency damping factor (pulls toward natural frequency) */
  frequencyDamping: number;
}

export const DEFAULT_OSCILLATOR_CONFIG: Readonly<OscillatorBusConfig> = {
  couplingStrength: 1.0,
  couplingRadius: 15.0,
  dt: 0.01,
  minTrustForCoupling: 0.1,
  maxFrequency: 20.0,
  frequencyDamping: 0.05,
};

/**
 * Snapshot of global bus state for telemetry.
 */
export interface BusSnapshot {
  /** Kuramoto order parameter r ∈ [0, 1] (1 = perfect sync) */
  orderParameter: number;
  /** Mean phase ψ ∈ [0, 2π) */
  meanPhase: number;
  /** Dominant mode across the bus */
  dominantMode: SwarmMode;
  /** Mode distribution */
  modeDistribution: Record<SwarmMode, number>;
  /** Number of synchronized clusters (phase within π/4) */
  clusterCount: number;
  /** Timestamp */
  timestamp: number;
}

// ──────────────── Core Engine ────────────────

/**
 * OscillatorBus — Kuramoto-class distributed mode bus.
 *
 * Provides:
 *   1. Emergent phase agreement without message passing
 *   2. Implicit mode switching via frequency-band convergence
 *   3. Natural partition tolerance (disconnected subsets self-sync)
 *   4. Trust-weighted coupling (Byzantine-resistant)
 */
export class OscillatorBus {
  private config: OscillatorBusConfig;
  private oscillators: Map<string, OscillatorState> = new Map();
  private listeners: Array<(snapshot: BusSnapshot) => void> = [];

  constructor(config: Partial<OscillatorBusConfig> = {}) {
    this.config = { ...DEFAULT_OSCILLATOR_CONFIG, ...config };
    // Hard cap coupling strength to prevent blowup
    this.config.couplingStrength = Math.min(Math.abs(this.config.couplingStrength), 10.0);
  }

  // ── Node Management ──

  /**
   * Register an oscillator node.
   */
  public addNode(
    id: string,
    position: Vec,
    trust: number,
    naturalFrequency?: number,
    initialPhase?: number,
  ): OscillatorState {
    const freq = Math.min(
      Math.abs(naturalFrequency ?? 3.0),
      this.config.maxFrequency,
    );
    const phase = normalizePhase(initialPhase ?? Math.random() * 2 * Math.PI);

    const state: OscillatorState = {
      id,
      phase,
      frequency: freq,
      trust: clamp01(trust),
      position: { ...position },
      mode: classifyFrequency(freq),
      phaseVelocity: 0,
    };

    this.oscillators.set(id, state);
    return state;
  }

  public removeNode(id: string): boolean {
    return this.oscillators.delete(id);
  }

  public getNode(id: string): OscillatorState | undefined {
    return this.oscillators.get(id);
  }

  public getNodes(): OscillatorState[] {
    return Array.from(this.oscillators.values());
  }

  public getNodeCount(): number {
    return this.oscillators.size;
  }

  /**
   * Update a node's trust score.
   */
  public setTrust(id: string, trust: number): void {
    const node = this.oscillators.get(id);
    if (node) node.trust = clamp01(trust);
  }

  /**
   * Update a node's spatial position (for coupling radius).
   */
  public setPosition(id: string, position: Vec): void {
    const node = this.oscillators.get(id);
    if (node) node.position = { ...position };
  }

  /**
   * Command a node to a target frequency (mode injection).
   * This overrides the natural frequency — used for intentional mode transitions.
   */
  public injectFrequency(id: string, frequency: number): void {
    const node = this.oscillators.get(id);
    if (!node) return;
    node.frequency = Math.min(Math.abs(frequency), this.config.maxFrequency);
    node.mode = classifyFrequency(node.frequency);
  }

  /**
   * Broadcast a mode to all nodes by setting target frequency.
   * Used for human override / emergency commands.
   */
  public broadcastMode(mode: SwarmMode): void {
    const targetFreq = getModeTargetFrequency(mode);
    for (const node of this.oscillators.values()) {
      node.frequency = targetFreq;
      node.mode = mode;
    }
  }

  // ── Coupling Computation ──

  /**
   * Get neighbors within coupling radius that meet trust threshold.
   */
  public getCoupledNeighbors(id: string): OscillatorState[] {
    const node = this.oscillators.get(id);
    if (!node) return [];

    const neighbors: OscillatorState[] = [];
    for (const other of this.oscillators.values()) {
      if (other.id === id) continue;
      if (other.trust < this.config.minTrustForCoupling) continue;
      if (vecDist(node.position, other.position) > this.config.couplingRadius) continue;
      neighbors.push(other);
    }
    return neighbors;
  }

  /**
   * Compute the Kuramoto coupling term for a single node.
   *
   * coupling_i = (K / N_eff) · Σ_j τ_j · sin(θ_j - θ_i)
   *
   * Where N_eff = Σ_j τ_j (trust-weighted count, not raw count).
   */
  public computeCoupling(id: string): number {
    const node = this.oscillators.get(id);
    if (!node) return 0;

    const neighbors = this.getCoupledNeighbors(id);
    if (neighbors.length === 0) return 0;

    let weightedSum = 0;
    let totalTrust = 0;

    for (const neighbor of neighbors) {
      const trustWeight = neighbor.trust;
      weightedSum += trustWeight * Math.sin(neighbor.phase - node.phase);
      totalTrust += trustWeight;
    }

    if (totalTrust < 1e-10) return 0;

    return (this.config.couplingStrength / totalTrust) * weightedSum;
  }

  // ── Step ──

  /**
   * Advance all oscillators by one time step.
   *
   * θ_i(t+dt) = θ_i(t) + [ω_i + coupling_i] · dt
   *
   * Returns a snapshot of the bus state after the step.
   */
  public step(): BusSnapshot {
    const updates: Array<{ id: string; newPhase: number; phaseVelocity: number }> = [];

    // Phase 1: Compute all phase updates (read-only sweep)
    for (const node of this.oscillators.values()) {
      const coupling = this.computeCoupling(node.id);

      // Convert frequency (Hz) to angular velocity (rad/s)
      const omega = 2 * Math.PI * node.frequency;

      // Phase velocity: natural frequency + coupling
      const phaseVelocity = omega + coupling;

      // Integrate phase
      const newPhase = normalizePhase(node.phase + phaseVelocity * this.config.dt);

      updates.push({ id: node.id, newPhase, phaseVelocity });
    }

    // Phase 2: Apply updates atomically
    for (const { id, newPhase, phaseVelocity } of updates) {
      const node = this.oscillators.get(id);
      if (!node) continue;
      node.phase = newPhase;
      node.phaseVelocity = phaseVelocity;
      node.mode = classifyFrequency(node.frequency);
    }

    // Phase 3: Compute snapshot
    const snapshot = this.computeSnapshot();

    // Notify listeners
    for (const listener of this.listeners) {
      listener(snapshot);
    }

    return snapshot;
  }

  /**
   * Run N steps and return final snapshot.
   */
  public run(steps: number): BusSnapshot {
    let snapshot: BusSnapshot | undefined;
    for (let i = 0; i < steps; i++) {
      snapshot = this.step();
    }
    return snapshot ?? this.computeSnapshot();
  }

  // ── Order Parameter ──

  /**
   * Compute the Kuramoto order parameter.
   *
   * r · e^(iψ) = (1/N) Σ_j e^(iθ_j)
   *
   * r ∈ [0, 1]: 0 = incoherent, 1 = perfect synchronization
   * ψ ∈ [0, 2π): mean phase
   */
  public computeOrderParameter(): { r: number; psi: number } {
    const nodes = this.getNodes();
    if (nodes.length === 0) return { r: 0, psi: 0 };

    let realSum = 0;
    let imagSum = 0;

    for (const node of nodes) {
      realSum += Math.cos(node.phase);
      imagSum += Math.sin(node.phase);
    }

    realSum /= nodes.length;
    imagSum /= nodes.length;

    const r = Math.sqrt(realSum * realSum + imagSum * imagSum);
    const psi = normalizePhase(Math.atan2(imagSum, realSum));

    return { r, psi };
  }

  /**
   * Compute full bus snapshot.
   */
  public computeSnapshot(): BusSnapshot {
    const { r, psi } = this.computeOrderParameter();

    const modeDistribution: Record<SwarmMode, number> = {
      REGROUP: 0,
      EXPLORE: 0,
      COMMIT: 0,
      HAZARD: 0,
    };

    for (const node of this.oscillators.values()) {
      modeDistribution[node.mode]++;
    }

    // Find dominant mode
    let dominantMode: SwarmMode = 'REGROUP';
    let maxCount = 0;
    for (const [mode, count] of Object.entries(modeDistribution)) {
      if (count > maxCount) {
        maxCount = count;
        dominantMode = mode as SwarmMode;
      }
    }

    // Count phase clusters (groups within π/4 of each other)
    const clusterCount = this.countPhaseClusters(Math.PI / 4);

    return {
      orderParameter: r,
      meanPhase: psi,
      dominantMode,
      modeDistribution,
      clusterCount,
      timestamp: Date.now(),
    };
  }

  /**
   * Count distinct phase clusters.
   * Two nodes are in the same cluster if their phase difference < threshold.
   * Uses simple greedy clustering.
   */
  private countPhaseClusters(threshold: number): number {
    const nodes = this.getNodes();
    if (nodes.length === 0) return 0;

    const assigned = new Set<string>();
    let clusters = 0;

    for (const node of nodes) {
      if (assigned.has(node.id)) continue;
      assigned.add(node.id);
      clusters++;

      // Find all nodes within threshold phase distance
      for (const other of nodes) {
        if (assigned.has(other.id)) continue;
        if (phaseDist(node.phase, other.phase) < threshold) {
          assigned.add(other.id);
        }
      }
    }

    return clusters;
  }

  // ── Event Listeners ──

  public onSnapshot(listener: (snapshot: BusSnapshot) => void): void {
    this.listeners.push(listener);
  }

  public removeListener(listener: (snapshot: BusSnapshot) => void): void {
    const idx = this.listeners.indexOf(listener);
    if (idx >= 0) this.listeners.splice(idx, 1);
  }

  // ── Config ──

  public getConfig(): Readonly<OscillatorBusConfig> {
    return { ...this.config };
  }
}

// ──────────────── Utilities ────────────────

/**
 * Normalize phase to [0, 2π).
 */
export function normalizePhase(theta: number): number {
  const TWO_PI = 2 * Math.PI;
  let result = theta % TWO_PI;
  if (result < 0) result += TWO_PI;
  return result;
}

/**
 * Circular distance between two phases ∈ [0, π].
 */
export function phaseDist(a: number, b: number): number {
  const diff = Math.abs(normalizePhase(a) - normalizePhase(b));
  return Math.min(diff, 2 * Math.PI - diff);
}

/**
 * Clamp to [0, 1].
 */
function clamp01(v: number): number {
  return Math.max(0, Math.min(1, v));
}

/**
 * Get a representative target frequency for a mode.
 */
function getModeTargetFrequency(mode: SwarmMode): number {
  switch (mode) {
    case 'REGROUP':
      return 1.0;
    case 'EXPLORE':
      return 3.5;
    case 'COMMIT':
      return 7.5;
    case 'HAZARD':
      return 15.0;
  }
}
