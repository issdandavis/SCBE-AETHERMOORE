/**
 * SCBE HAL - Harmonic Attention Layer
 *
 * Implements attention mechanism with harmonic coupling matrix:
 * - Λ(d)[i,j] = R^(d_i · d_j) harmonic weighting
 * - Softmax attention with harmonic modulation
 * - Batched tensor operations
 */
import { Tensor2D, Tensor3D } from './constants.js';
/**
 * HAL configuration interface
 */
export interface HALConfig {
    /** Model dimension */
    d_model: number;
    /** Number of attention heads */
    n_heads: number;
    /** Base ratio for harmonic coupling (default: R^(1/5)) */
    R?: number;
    /** Maximum dimension for normalization */
    d_max?: number;
    /** Whether to normalize coupling matrix */
    normalize?: boolean;
}
/**
 * Compute harmonic coupling matrix Λ
 *
 * Λ[i,j] = R^((d_Q[i] * d_K[j]) - d_max) when normalized
 * Λ[i,j] = R^(d_Q[i] * d_K[j]) when not normalized
 *
 * @param d_Q - Query dimension vector
 * @param d_K - Key dimension vector
 * @param R - Base ratio
 * @param normalize - Whether to subtract max for numerical stability
 * @returns Coupling matrix
 */
export declare function harmonicCouplingMatrix(d_Q: number[], d_K: number[], R?: number, normalize?: boolean): number[][];
/**
 * HAL Attention: Attention with harmonic coupling
 *
 * Output = softmax((Q × K^T / √d_model) ⊙ Λ) × V
 *
 * Where Λ is the harmonic coupling matrix based on dimension vectors.
 *
 * @param Q - Query tensor [batch, seq_q, d_model]
 * @param K - Key tensor [batch, seq_k, d_model]
 * @param V - Value tensor [batch, seq_k, d_model]
 * @param d_Q - Query dimension vectors [batch, seq_q]
 * @param d_K - Key dimension vectors [batch, seq_k]
 * @param config - HAL configuration
 * @returns Output tensor [batch, seq_q, d_model]
 */
export declare function halAttention(Q: Tensor3D, K: Tensor3D, V: Tensor3D, d_Q: Tensor2D, d_K: Tensor2D, config: HALConfig): Tensor3D;
//# sourceMappingURL=halAttention.d.ts.map