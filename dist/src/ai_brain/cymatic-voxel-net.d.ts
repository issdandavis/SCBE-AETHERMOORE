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
/** The six Sacred Tongues (semantic encoding layers) */
export declare const SACRED_TONGUES: readonly ["KO", "AV", "RU", "CA", "UM", "DR"];
export type SacredTongue = (typeof SACRED_TONGUES)[number];
/** Tongue-to-dimension mapping (each tongue governs one coordinate) */
export declare const TONGUE_DIMENSION_MAP: Record<SacredTongue, number>;
/** Realm centers in 6D Poincaré ball (one per tongue) */
export declare const REALM_CENTERS: Record<SacredTongue, number[]>;
/** Default Chladni nodal threshold */
export declare const NODAL_THRESHOLD = 0.001;
/** Voxel spatial dimensions */
export declare const VOXEL_DIMS = 6;
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
    storageCapacity: {
        nodal: number;
        negativeSpace: number;
        total: number;
    };
}
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
export declare function chladni6D(coords: number[], state: number[]): number;
/**
 * Classify a coordinate based on its Chladni field value.
 *
 * @param chladniValue - The raw Chladni field value
 * @param nodalThreshold - Threshold for nodal classification
 * @param boundaryWidth - Width of the implied boundary zone
 */
export declare function classifyZone(chladniValue: number, nodalThreshold?: number, boundaryWidth?: number): VoxelZone;
/**
 * Determine which Sacred Tongue governs a given 6D coordinate.
 * The tongue is assigned by the dimension with the largest absolute value.
 */
export declare function dominantTongue(coords: number[]): SacredTongue;
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
export declare function estimateNodalDensity(state: number[], samples?: number, threshold?: number): number;
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
export declare class CymaticVoxelNet {
    private state;
    private position;
    private voxels;
    private readonly config;
    private propagationLog;
    constructor(initialState?: number[], initialPosition?: number[], config?: CymaticNetConfig);
    /**
     * Probe a 6D coordinate: classify it and compute all metrics.
     * Does NOT store — just reads the field.
     */
    probe(coords: number[]): CymaticVoxel;
    /**
     * Store data at a 6D coordinate. Classifies automatically.
     * Returns the voxel with payload attached.
     */
    store(coords: number[], payload: Uint8Array): CymaticVoxel;
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
    retrieve(coords: number[], requesterPosition: number[], maxDistance?: number): CymaticVoxel | null;
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
    propagate(startCoords: number[], maxHops?: number, stepSize?: number): VoxelActivation[];
    /**
     * Compute the Chladni gradient and step toward the nearest nodal line.
     * Uses finite-difference gradient descent on |C(x, s)|.
     */
    private stepTowardNodal;
    /**
     * Embed a 6D vector into the Poincaré ball.
     * Uses tanh normalization: embed(v) = tanh(||v||/2) * v/||v||
     * Clamped to max norm 0.999 to stay strictly inside the ball.
     */
    private poincareEmbed6D;
    /**
     * Hyperbolic distance in 6D Poincaré ball.
     * d_H(u, v) = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))
     */
    private hyperbolicDist6D;
    /** Coordinate key for the voxel map. */
    private coordKey;
    /** Update the agent's mode parameters (Chladni state). */
    setState(state: number[]): void;
    /** Update the agent's Poincaré position. */
    setPosition(position: number[]): void;
    /** Get the current Chladni state. */
    getState(): number[];
    /** Get the current Poincaré position. */
    getPosition(): number[];
    /** Number of stored voxels. */
    storedCount(): number;
    /** Last propagation log. */
    lastPropagation(): VoxelActivation[];
    /**
     * Network statistics snapshot.
     * Classifies all stored voxels by zone and computes capacity estimates.
     */
    snapshot(): NetSnapshot;
    /** Clear all stored voxels. */
    clear(): void;
}
//# sourceMappingURL=cymatic-voxel-net.d.ts.map