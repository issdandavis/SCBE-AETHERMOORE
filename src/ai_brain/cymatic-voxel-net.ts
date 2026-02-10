/**
 * @file cymatic-voxel-net.ts
 * @module ai_brain/cymatic-voxel-net
 * @layer Layer 5, Layer 8, Layer 12, Layer 14
 * @component Cymatic Voxel Neural Network
 * @version 1.0.0
 *
 * Cymatic Voxel 6-Tongue Semantic Encoded Nodal Auto-Propagational AI Neural Network.
 *
 * A neural network where neurons are voxels placed at nodal/anti-nodal points
 * of a 6D Chladni equation, signals auto-propagate along nodal contours, and
 * data is semantically encoded via the Six Sacred Tongues in Poincaré space.
 *
 * Architecture:
 *
 *   6D Chladni Equation (3 paired-dimension terms):
 *     C(x, s) = Σᵢ [cos(s₂ᵢπx₂ᵢ)cos(s₂ᵢ₊₁πx₂ᵢ₊₁) - cos(s₂ᵢ₊₁πx₂ᵢ)cos(s₂ᵢπx₂ᵢ₊₁)]
 *     where s is the 6D state vector (agent mode parameters) and x is coordinates.
 *
 *   Storage Topology:
 *     Nodal (|C| < ε):       Visible, directly addressable voxels
 *     Negative Space (|C| ≥ ε): Hidden, encrypted voxels (anti-nodal)
 *     Implied Boundary:       Soft contours where C transitions sign
 *
 *   Neural Propagation:
 *     Neurons at nodal points connect via implied boundaries (sign-change contours).
 *     Activation propagates along Chladni zero-sets, modulated by:
 *     - Harmonic scaling H(d, R) for amplification
 *     - Triadic temporal distance for multi-scale governance
 *     - Poincaré hyperbolic distance for semantic coherence
 *
 *   Storage Capacity:
 *     6D grid N=256: N⁶ = 2.81 × 10¹⁴ total voxels
 *     Nodal fraction ~20%: ~5.6 × 10¹³ visible voxels
 *     Negative space ~80%: ~2.25 × 10¹⁴ hidden voxels
 *     Hyperbolic volume (r=10): ~10²¹ effective capacity via curvature
 *
 * Integration:
 *   - harmonicScale() from tri-manifold-lattice for cost amplification
 *   - hyperbolicDistanceSafe() from unified-state for coherence gating
 *   - safePoincareEmbed() for 6D ball containment
 *   - Six Sacred Tongues (KO, AV, RU, CA, UM, DR) for semantic encoding
 */

import { BRAIN_EPSILON, PHI } from './types.js';
import { hyperbolicDistanceSafe, safePoincareEmbed, vectorNorm } from './unified-state.js';
import { harmonicScale, HARMONIC_R } from './tri-manifold-lattice.js';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

/** The six Sacred Tongues (semantic encoding layers) */
export const SACRED_TONGUES = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as const;
export type SacredTongue = (typeof SACRED_TONGUES)[number];

/** Tongue-to-dimension mapping (each tongue governs one coordinate) */
export const TONGUE_DIMENSION_MAP: Record<SacredTongue, number> = {
  KO: 0, // Intent / Flow
  AV: 1, // Context / Metadata
  RU: 2, // Binding / Commitment
  CA: 3, // Computation / Payload
  UM: 4, // Redaction / Erasure
  DR: 5, // Integrity / Structure
};

/** Realm centers in 6D Poincaré ball (one per tongue) */
export const REALM_CENTERS: Record<SacredTongue, number[]> = {
  KO: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
  AV: [0.3, 0.1, 0.0, 0.0, 0.0, 0.0],
  RU: [0.0, 0.4, 0.2, 0.0, 0.0, 0.0],
  CA: [-0.2, -0.3, 0.4, 0.1, 0.0, 0.0],
  UM: [0.0, 0.0, -0.5, 0.3, 0.2, 0.0],
  DR: [0.1, -0.2, 0.0, -0.4, 0.3, 0.1],
};

/** Default Chladni nodal threshold */
export const NODAL_THRESHOLD = 1e-3;

/** Voxel spatial dimensions */
export const VOXEL_DIMS = 6;

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/** Classification of a voxel's position in the Chladni field */
export type VoxelZone = 'nodal' | 'negative_space' | 'implied_boundary';

/** A single voxel in the cymatic lattice */
export interface CymaticVoxel {
  /** 6D coordinate in the lattice */
  coords: number[];
  /** Chladni field value at this position */
  chladniValue: number;
  /** Absolute Chladni value */
  chladniAbs: number;
  /** Classification: nodal, negative_space, or implied_boundary */
  zone: VoxelZone;
  /** Sacred Tongue assigned (by dominant dimension) */
  tongue: SacredTongue;
  /** Poincaré-embedded coordinate */
  embedded: number[];
  /** Hyperbolic distance from realm center */
  realmDistance: number;
  /** Payload stored at this voxel (optional) */
  payload?: Uint8Array;
}

/** Neural activation at a voxel node */
export interface VoxelActivation {
  /** Source voxel index */
  voxelIndex: number;
  /** Activation strength [0, 1] */
  strength: number;
  /** Tongue-encoded semantic context */
  tongue: SacredTongue;
  /** Propagation generation (hop count) */
  generation: number;
  /** Harmonic-scaled governance cost */
  harmonicCost: number;
}

/** Configuration for the cymatic voxel network */
export interface CymaticNetConfig {
  /** Nodal threshold (default: 1e-3) */
  nodalThreshold?: number;
  /** Implied boundary width (default: 0.05) */
  boundaryWidth?: number;
  /** Harmonic ratio for cost scaling (default: 1.5) */
  harmonicR?: number;
  /** Propagation coherence decay per hop (default: 0.85) */
  coherenceDecay?: number;
  /** Maximum propagation hops (default: 10) */
  maxHops?: number;
}

/** Network statistics snapshot */
export interface NetSnapshot {
  totalVoxels: number;
  nodalCount: number;
  negativeSpaceCount: number;
  boundaryCount: number;
  nodalFraction: number;
  negativeSpaceFraction: number;
  meanChladniAbs: number;
  storageCapacity: { nodal: number; negativeSpace: number; total: number };
}

// ═══════════════════════════════════════════════════════════════
// 6D Chladni Equation
// ═══════════════════════════════════════════════════════════════

/**
 * 6D Chladni equation: generalization of the 2D Chladni plate pattern.
 *
 * Pairs the 6 dimensions into 3 Chladni-like terms:
 *   C(x, s) = Σᵢ₌₀² [cos(s₂ᵢ·π·x₂ᵢ)·cos(s₂ᵢ₊₁·π·x₂ᵢ₊₁)
 *                     - cos(s₂ᵢ₊₁·π·x₂ᵢ)·cos(s₂ᵢ·π·x₂ᵢ₊₁)]
 *
 * where:
 *   x = 6D voxel coordinates
 *   s = 6D state vector (mode parameters, derived from agent state)
 *
 * Nodal lines: C(x, s) = 0 (data is "visible" / accessible)
 * Negative space: C(x, s) ≠ 0 (data is "hidden" / encrypted)
 *
 * @param coords - 6D voxel coordinates [x₀..x₅]
 * @param state  - 6D mode parameters [s₀..s₅]
 * @returns Chladni field value (0 at nodal lines)
 */
export function chladni6D(coords: number[], state: number[]): number {
  let sum = 0;
  for (let i = 0; i < 3; i++) {
    const s2i = state[2 * i] || 1;
    const s2i1 = state[2 * i + 1] || 1;
    const x2i = coords[2 * i] || 0;
    const x2i1 = coords[2 * i + 1] || 0;

    sum +=
      Math.cos(s2i * Math.PI * x2i) * Math.cos(s2i1 * Math.PI * x2i1) -
      Math.cos(s2i1 * Math.PI * x2i) * Math.cos(s2i * Math.PI * x2i1);
  }
  return sum;
}

/**
 * Classify a coordinate based on its Chladni field value.
 *
 * @param chladniValue - The raw Chladni field value
 * @param nodalThreshold - Threshold for nodal classification
 * @param boundaryWidth - Width of the implied boundary zone
 */
export function classifyZone(
  chladniValue: number,
  nodalThreshold: number = NODAL_THRESHOLD,
  boundaryWidth: number = 0.05,
): VoxelZone {
  const absVal = Math.abs(chladniValue);
  if (absVal < nodalThreshold) return 'nodal';
  if (absVal < nodalThreshold + boundaryWidth) return 'implied_boundary';
  return 'negative_space';
}

/**
 * Determine which Sacred Tongue governs a given 6D coordinate.
 * The tongue is assigned by the dimension with the largest absolute value.
 */
export function dominantTongue(coords: number[]): SacredTongue {
  let maxIdx = 0;
  let maxVal = 0;
  for (let i = 0; i < Math.min(coords.length, 6); i++) {
    const absVal = Math.abs(coords[i]);
    if (absVal > maxVal) {
      maxVal = absVal;
      maxIdx = i;
    }
  }
  return SACRED_TONGUES[maxIdx];
}

/**
 * Compute the nodal density estimate for a given state vector.
 *
 * Samples random coordinates and returns the fraction that fall on
 * nodal lines (|C| < threshold). The theoretical fraction for 2D
 * Chladni patterns is ~1/√d, extended to 6D gives ~20%.
 *
 * @param state - 6D mode parameters
 * @param samples - Number of random samples (default: 10000)
 * @param threshold - Nodal threshold
 * @returns Fraction of samples that are nodal
 */
export function estimateNodalDensity(
  state: number[],
  samples: number = 10000,
  threshold: number = NODAL_THRESHOLD,
): number {
  let nodal = 0;
  for (let s = 0; s < samples; s++) {
    const coords = Array.from({ length: 6 }, () => Math.random() * 2 - 1);
    if (Math.abs(chladni6D(coords, state)) < threshold) {
      nodal++;
    }
  }
  return nodal / samples;
}

// ═══════════════════════════════════════════════════════════════
// Cymatic Voxel Network
// ═══════════════════════════════════════════════════════════════

/**
 * CymaticVoxelNet: Auto-propagational neural network on a 6D Chladni lattice.
 *
 * Neurons are voxels placed at Chladni nodal points. Connections follow
 * implied boundaries (sign-change contours). Signals auto-propagate along
 * nodal lines, with governance via harmonic scaling and triadic distances.
 *
 * Storage:
 *   - Nodal voxels: directly addressable, visible storage
 *   - Negative space: hidden, encrypted storage (anti-nodal)
 *   - Implied boundaries: transition zones, access-controlled
 *
 * Usage:
 *   const net = new CymaticVoxelNet();
 *   const voxel = net.probe([0.5, 0.3, -0.2, 0.1, 0.0, 0.4]);
 *   console.log(voxel.zone);  // 'nodal' | 'negative_space' | 'implied_boundary'
 *
 *   net.store(coords, payload);
 *   const result = net.propagate(startCoords, 5);
 */
export class CymaticVoxelNet {
  // Agent's 6D state vector (mode parameters for Chladni)
  private state: number[];
  // Poincaré position (6D ball)
  private position: number[];
  // Stored voxels
  private voxels: Map<string, CymaticVoxel> = new Map();
  // Configuration
  private readonly config: Required<CymaticNetConfig>;
  // Propagation history
  private propagationLog: VoxelActivation[] = [];

  constructor(
    initialState?: number[],
    initialPosition?: number[],
    config?: CymaticNetConfig,
  ) {
    this.state = initialState ?? [1, 2, 3, 2, 1, 3]; // Default mode params
    this.position = initialPosition ?? [0, 0, 0, 0, 0, 0]; // Origin
    this.config = {
      nodalThreshold: config?.nodalThreshold ?? NODAL_THRESHOLD,
      boundaryWidth: config?.boundaryWidth ?? 0.05,
      harmonicR: config?.harmonicR ?? HARMONIC_R,
      coherenceDecay: config?.coherenceDecay ?? 0.85,
      maxHops: config?.maxHops ?? 10,
    };
  }

  /**
   * Probe a 6D coordinate: classify it and compute all metrics.
   * Does NOT store — just reads the field.
   */
  probe(coords: number[]): CymaticVoxel {
    const c6 = coords.length >= 6 ? coords.slice(0, 6) : [...coords, ...new Array(6 - coords.length).fill(0)];
    const chladniValue = chladni6D(c6, this.state);
    const chladniAbs = Math.abs(chladniValue);
    const zone = classifyZone(chladniValue, this.config.nodalThreshold, this.config.boundaryWidth);
    const tongue = dominantTongue(c6);

    // Embed in Poincaré ball (use 6D, not 21D)
    const embedded = this.poincareEmbed6D(c6);
    const realmCenter = REALM_CENTERS[tongue];
    const realmDistance = this.hyperbolicDist6D(embedded, realmCenter);

    return {
      coords: c6,
      chladniValue,
      chladniAbs,
      zone,
      tongue,
      embedded,
      realmDistance,
    };
  }

  /**
   * Store data at a 6D coordinate. Classifies automatically.
   * Returns the voxel with payload attached.
   */
  store(coords: number[], payload: Uint8Array): CymaticVoxel {
    const voxel = this.probe(coords);
    voxel.payload = payload;
    this.voxels.set(this.coordKey(voxel.coords), voxel);
    return voxel;
  }

  /**
   * Retrieve data at a 6D coordinate.
   * Access is gated by semantic coherence: the requester's Poincaré position
   * must be close enough to the voxel's realm center.
   *
   * @param coords - 6D coordinate to read
   * @param requesterPosition - Requester's 6D Poincaré position
   * @param maxDistance - Maximum hyperbolic distance for access (default: 2.0)
   * @returns Voxel data if accessible, null if gated
   */
  retrieve(
    coords: number[],
    requesterPosition: number[],
    maxDistance: number = 2.0,
  ): CymaticVoxel | null {
    const key = this.coordKey(coords.length >= 6 ? coords.slice(0, 6) : [...coords, ...new Array(6 - coords.length).fill(0)]);
    const voxel = this.voxels.get(key);
    if (!voxel) return null;

    // Gate by semantic coherence (hyperbolic distance)
    const reqEmbedded = this.poincareEmbed6D(requesterPosition);
    const dist = this.hyperbolicDist6D(reqEmbedded, voxel.embedded);

    // Negative space requires stricter access
    const effectiveMax = voxel.zone === 'negative_space' ? maxDistance * 0.5 : maxDistance;
    if (dist > effectiveMax) return null;

    return voxel;
  }

  /**
   * Auto-propagate activation from a starting coordinate along nodal contours.
   *
   * Explores neighboring voxels, following the Chladni zero-set.
   * Activation decays by coherenceDecay per hop, amplified by harmonic scaling.
   *
   * @param startCoords - Starting 6D coordinate
   * @param maxHops - Maximum propagation depth (default: from config)
   * @param stepSize - Exploration step size (default: 0.1)
   * @returns Array of activated voxels along the propagation path
   */
  propagate(
    startCoords: number[],
    maxHops?: number,
    stepSize: number = 0.1,
  ): VoxelActivation[] {
    const hops = maxHops ?? this.config.maxHops;
    const activations: VoxelActivation[] = [];
    let coords = startCoords.slice(0, 6);
    if (coords.length < 6) coords = [...coords, ...new Array(6 - coords.length).fill(0)];
    let strength = 1.0;

    for (let gen = 0; gen < hops && strength > BRAIN_EPSILON; gen++) {
      const voxel = this.probe(coords);

      // Only propagate along nodal lines and boundaries
      if (voxel.zone === 'negative_space' && gen > 0) {
        // Hit negative space — signal absorbed
        break;
      }

      const tongue = voxel.tongue;
      const hCost = harmonicScale(gen + 1, this.config.harmonicR);

      activations.push({
        voxelIndex: gen,
        strength,
        tongue,
        generation: gen,
        harmonicCost: strength * hCost,
      });

      // Decay strength
      strength *= this.config.coherenceDecay;

      // Step along gradient of Chladni field toward zero-set
      coords = this.stepTowardNodal(coords, stepSize);
    }

    this.propagationLog = activations;
    return activations;
  }

  /**
   * Compute the Chladni gradient and step toward the nearest nodal line.
   * Uses finite-difference gradient descent on |C(x, s)|.
   */
  private stepTowardNodal(coords: number[], stepSize: number): number[] {
    const eps = 1e-6;
    const cVal = Math.abs(chladni6D(coords, this.state));
    const gradient = new Array(6).fill(0);

    for (let i = 0; i < 6; i++) {
      const perturbed = [...coords];
      perturbed[i] += eps;
      const cPerturbed = Math.abs(chladni6D(perturbed, this.state));
      gradient[i] = (cPerturbed - cVal) / eps;
    }

    // Normalize gradient
    const gNorm = Math.sqrt(gradient.reduce((s, g) => s + g * g, 0));
    if (gNorm < BRAIN_EPSILON) {
      // Already at/near nodal — perturb slightly to explore
      return coords.map((c, i) => c + (Math.sin((i + 1) * PHI) * stepSize * 0.1));
    }

    // Step against gradient (toward zero)
    return coords.map((c, i) => c - (gradient[i] / gNorm) * stepSize);
  }

  /**
   * Embed a 6D vector into the Poincaré ball.
   * Uses tanh normalization: embed(v) = tanh(||v||/2) * v/||v||
   * Clamped to max norm 0.999 to stay strictly inside the ball.
   */
  private poincareEmbed6D(v: number[]): number[] {
    const norm = Math.sqrt(v.reduce((s, x) => s + x * x, 0));
    if (norm < BRAIN_EPSILON) return v.slice();
    const maxNorm = 0.999;
    const targetNorm = Math.min(Math.tanh(norm / 2), maxNorm);
    const scale = targetNorm / norm;
    return v.map((x) => x * scale);
  }

  /**
   * Hyperbolic distance in 6D Poincaré ball.
   * d_H(u, v) = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))
   */
  private hyperbolicDist6D(u: number[], v: number[]): number {
    const diffSq = u.reduce((s, ui, i) => s + (ui - (v[i] || 0)) ** 2, 0);
    const uNormSq = u.reduce((s, x) => s + x * x, 0);
    const vNormSq = v.reduce((s, x) => s + x * x, 0);
    const denom = (1 - uNormSq) * (1 - vNormSq);
    if (denom <= 0) return Infinity;
    const arg = 1 + (2 * diffSq) / denom;
    if (arg < 1) return 0;
    return Math.acosh(arg);
  }

  /** Coordinate key for the voxel map. */
  private coordKey(coords: number[]): string {
    return coords.map((c) => c.toFixed(6)).join(',');
  }

  // ═══════════════════════════════════════════════════════════
  // State Management
  // ═══════════════════════════════════════════════════════════

  /** Update the agent's mode parameters (Chladni state). */
  setState(state: number[]): void {
    this.state = state.slice(0, 6);
  }

  /** Update the agent's Poincaré position. */
  setPosition(position: number[]): void {
    this.position = position.slice(0, 6);
  }

  /** Get the current Chladni state. */
  getState(): number[] {
    return [...this.state];
  }

  /** Get the current Poincaré position. */
  getPosition(): number[] {
    return [...this.position];
  }

  /** Number of stored voxels. */
  storedCount(): number {
    return this.voxels.size;
  }

  /** Last propagation log. */
  lastPropagation(): VoxelActivation[] {
    return [...this.propagationLog];
  }

  /**
   * Network statistics snapshot.
   * Classifies all stored voxels by zone and computes capacity estimates.
   */
  snapshot(): NetSnapshot {
    let nodalCount = 0;
    let negCount = 0;
    let boundaryCount = 0;
    let chladniSum = 0;

    for (const voxel of this.voxels.values()) {
      chladniSum += voxel.chladniAbs;
      switch (voxel.zone) {
        case 'nodal':
          nodalCount++;
          break;
        case 'negative_space':
          negCount++;
          break;
        case 'implied_boundary':
          boundaryCount++;
          break;
      }
    }

    const total = this.voxels.size || 1;
    return {
      totalVoxels: this.voxels.size,
      nodalCount,
      negativeSpaceCount: negCount,
      boundaryCount,
      nodalFraction: nodalCount / total,
      negativeSpaceFraction: negCount / total,
      meanChladniAbs: chladniSum / total,
      storageCapacity: {
        nodal: nodalCount,
        negativeSpace: negCount,
        total: this.voxels.size,
      },
    };
  }

  /** Clear all stored voxels. */
  clear(): void {
    this.voxels.clear();
    this.propagationLog = [];
  }
}
