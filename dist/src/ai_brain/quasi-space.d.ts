/**
 * @file quasi-space.ts
 * @module ai_brain/quasi-space
 * @layer Layer 4, Layer 5, Layer 9
 * @component Quasicrystal Icosahedral Projection
 * @version 1.1.0
 * @since 2026-02-07
 *
 * Implements quasicrystal-based projections for the unified brain manifold.
 * Uses 6D icosahedral symmetry (referencing Shechtman's Nobel-prize-winning
 * discovery of quasicrystals) applied to AI state space.
 *
 * The projection creates aperiodic tiling of the state space, ensuring
 * that adversarial agents cannot predict or reproduce the geometric structure.
 */
/**
 * Project a 6D vector using icosahedral symmetry for aperiodic order.
 *
 * This creates a quasicrystalline structure in the projected space,
 * making it computationally infeasible for adversaries to predict
 * the geometric layout.
 *
 * @param vector6d - Input 6D vector
 * @returns Projected 6D vector with icosahedral symmetry
 */
export declare function icosahedralProjection(vector6d: number[]): number[];
/**
 * Voxel realm classification based on radial distance.
 * - Gold: r < 0.5 (light realm, safe operations)
 * - Purple: 0.5 <= r < 0.95 (shadow realm, monitored operations)
 * - Red: r >= 0.95 (boundary danger zone)
 */
export type VoxelRealm = 'gold' | 'purple' | 'red';
/**
 * Classify a point into a voxel realm based on its distance from origin.
 *
 * @param point - Point in Poincare ball
 * @returns Voxel realm classification
 */
export declare function classifyVoxelRealm(point: number[]): VoxelRealm;
/**
 * Sparse octree node for efficient spatial queries in hyperbolic space.
 * Achieves ~99.96% memory savings over dense grids by only storing
 * occupied voxels (at 64^3 resolution).
 */
export interface OctreeNode {
    /** Center position */
    center: number[];
    /** Half-width of this node */
    halfWidth: number;
    /** Depth level */
    depth: number;
    /** Voxel realm classification */
    realm: VoxelRealm;
    /** Children (8 octants, null if leaf) */
    children: (OctreeNode | null)[];
    /** Points contained in this leaf */
    points: number[][];
    /** Maximum points per leaf before subdivision */
    capacity: number;
}
/**
 * Create a sparse octree root node for the Poincare ball.
 *
 * @param dimensions - Number of dimensions (default: 3 for spatial queries)
 * @param capacity - Max points per leaf before splitting (default: 8)
 * @returns Root octree node
 */
export declare function createOctreeRoot(dimensions?: number, capacity?: number): OctreeNode;
/**
 * Insert a point into the sparse octree.
 * Only allocates nodes where points actually exist.
 *
 * @param node - Octree node to insert into
 * @param point - Point to insert
 * @param maxDepth - Maximum tree depth (default: 6, giving 64^3 resolution)
 */
export declare function octreeInsert(node: OctreeNode, point: number[], maxDepth?: number): void;
/**
 * Generate a 2D Penrose tiling vertex from a 21D brain state.
 *
 * Projects the high-dimensional state through the icosahedral matrix
 * and then applies the cut-and-project method to generate a
 * quasicrystalline coordinate.
 *
 * @param state - 21D brain state vector
 * @returns 2D Penrose tiling coordinate [x, y]
 */
export declare function brainStateToPenrose(state: number[]): [number, number];
/**
 * Compute the quasicrystal potential at a point.
 * V(r) = sum_k cos(G_k . r) where G_k are reciprocal lattice vectors
 * with 5-fold symmetry.
 *
 * @param point - 2D point
 * @returns Potential value
 */
export declare function quasicrystalPotential(point: [number, number]): number;
//# sourceMappingURL=quasi-space.d.ts.map