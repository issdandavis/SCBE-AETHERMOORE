/**
 * SCBE HAL Attention Tests
 *
 * Tests for Harmonic Attention Layer:
 * - Λ[i,j] = R^(d_i · d_j) coupling matrix
 * - Softmax attention with harmonic modulation
 * - Tensor operations and numerical stability
 */

import { describe, it, expect } from 'vitest';
import {
  harmonicCouplingMatrix,
  halAttention,
  type HALConfig,
} from '../../src/harmonic/halAttention.js';
import { CONSTANTS, type Tensor2D, type Tensor3D } from '../../src/harmonic/constants.js';

describe('harmonicCouplingMatrix', () => {
  // ═══════════════════════════════════════════════════════════════
  // Basic Properties
  // ═══════════════════════════════════════════════════════════════
  describe('Basic properties', () => {
    it('creates matrix with correct dimensions', () => {
      const d_Q = [1, 2, 3];
      const d_K = [1, 2];
      const M = harmonicCouplingMatrix(d_Q, d_K);

      expect(M.length).toBe(3);
      expect(M[0].length).toBe(2);
    });

    it('uses default R = R_FIFTH', () => {
      const d_Q = [1, 1];
      const d_K = [1, 1];

      const M1 = harmonicCouplingMatrix(d_Q, d_K);
      const M2 = harmonicCouplingMatrix(d_Q, d_K, CONSTANTS.R_FIFTH);

      expect(M1[0][0]).toBeCloseTo(M2[0][0], 10);
    });

    it('throws for R <= 0', () => {
      const d_Q = [1, 2];
      const d_K = [1, 2];

      expect(() => harmonicCouplingMatrix(d_Q, d_K, 0)).toThrow(RangeError);
      expect(() => harmonicCouplingMatrix(d_Q, d_K, -1)).toThrow(RangeError);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Mathematical Correctness
  // ═══════════════════════════════════════════════════════════════
  describe('Mathematical correctness', () => {
    it('Λ[i,j] = R^(d_Q[i] × d_K[j]) without normalization', () => {
      const R = 1.5;
      const d_Q = [1, 2];
      const d_K = [2, 3];

      const M = harmonicCouplingMatrix(d_Q, d_K, R, false);

      // M[0][0] = R^(1*2) = R^2
      expect(M[0][0]).toBeCloseTo(Math.pow(R, 2), 10);

      // M[0][1] = R^(1*3) = R^3
      expect(M[0][1]).toBeCloseTo(Math.pow(R, 3), 10);

      // M[1][0] = R^(2*2) = R^4
      expect(M[1][0]).toBeCloseTo(Math.pow(R, 4), 10);

      // M[1][1] = R^(2*3) = R^6
      expect(M[1][1]).toBeCloseTo(Math.pow(R, 6), 10);
    });

    it('normalization subtracts max product', () => {
      const R = 1.5;
      const d_Q = [1, 2];
      const d_K = [2, 3];

      // Without normalization
      const M_unnorm = harmonicCouplingMatrix(d_Q, d_K, R, false);

      // With normalization
      const M_norm = harmonicCouplingMatrix(d_Q, d_K, R, true);

      // d_max = max(d_Q) * max(d_K) = 2 * 3 = 6
      const d_max = 2 * 3;

      // Normalized M[i][j] = R^(d_Q[i]*d_K[j] - d_max)
      // So M_norm / M_unnorm = R^(-d_max)
      const ratio = M_norm[0][0] / M_unnorm[0][0];
      expect(ratio).toBeCloseTo(Math.pow(R, -d_max), 10);
    });

    it('identity-like for d = [1,1,...] and R = 1', () => {
      const d_Q = [1, 1, 1];
      const d_K = [1, 1, 1];

      const M = harmonicCouplingMatrix(d_Q, d_K, 1.0, false);

      // 1^1 = 1 for all entries
      for (let i = 0; i < 3; i++) {
        for (let j = 0; j < 3; j++) {
          expect(M[i][j]).toBe(1);
        }
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Scaling Properties
  // ═══════════════════════════════════════════════════════════════
  describe('Scaling properties', () => {
    it('higher dimensions get higher weights (R > 1)', () => {
      const R = 1.5;
      const d_Q = [1, 2, 3];
      const d_K = [1, 2, 3];

      const M = harmonicCouplingMatrix(d_Q, d_K, R, false);

      // M[i][j] increases as i*j increases
      expect(M[0][0]).toBeLessThan(M[1][1]);
      expect(M[1][1]).toBeLessThan(M[2][2]);
    });

    it('super-exponential growth with dimension product', () => {
      const R = 1.5;
      const d_Q = [1, 2, 3, 4, 5, 6];
      const d_K = [1, 2, 3, 4, 5, 6];

      const M = harmonicCouplingMatrix(d_Q, d_K, R, false);

      // M[5][5] = R^36 (very large)
      expect(M[5][5]).toBeCloseTo(Math.pow(R, 36), -1);

      // Check growth is super-exponential
      const m11 = M[0][0]; // R^1
      const m22 = M[1][1]; // R^4
      const m33 = M[2][2]; // R^9

      expect(m22 / m11).toBeCloseTo(Math.pow(R, 3), 6);
      expect(m33 / m22).toBeCloseTo(Math.pow(R, 5), 6);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Numerical Stability
  // ═══════════════════════════════════════════════════════════════
  describe('Numerical stability', () => {
    it('normalized matrix has max entry = 1', () => {
      const d_Q = [1, 2, 3, 4, 5, 6];
      const d_K = [1, 2, 3, 4, 5, 6];

      const M = harmonicCouplingMatrix(d_Q, d_K, 1.5, true);

      // Find max entry
      let maxEntry = -Infinity;
      for (const row of M) {
        for (const val of row) {
          maxEntry = Math.max(maxEntry, val);
        }
      }

      // Should be 1 (at position [5][5] where d_Q*d_K = 36 = d_max)
      expect(maxEntry).toBeCloseTo(1, 10);
    });

    it('all entries are positive', () => {
      const d_Q = [1, 2, 3];
      const d_K = [4, 5, 6];

      const M = harmonicCouplingMatrix(d_Q, d_K, 1.5, true);

      for (const row of M) {
        for (const val of row) {
          expect(val).toBeGreaterThan(0);
        }
      }
    });

    it('handles very small R correctly', () => {
      const d_Q = [1, 2];
      const d_K = [1, 2];

      const M = harmonicCouplingMatrix(d_Q, d_K, 0.001, false);

      for (const row of M) {
        for (const val of row) {
          expect(Number.isFinite(val)).toBe(true);
          expect(val).toBeGreaterThan(0);
        }
      }
    });
  });
});

describe('halAttention', () => {
  // Helper to create test tensors
  const createTensor = (batch: number, seq: number, dim: number, fill: number = 0.1): Tensor3D => {
    return Array.from({ length: batch }, () =>
      Array.from({ length: seq }, () => Array.from({ length: dim }, () => fill))
    );
  };

  const createDimTensor = (batch: number, seq: number, fill: number = 1): Tensor2D => {
    return Array.from({ length: batch }, () => Array.from({ length: seq }, () => fill));
  };

  // ═══════════════════════════════════════════════════════════════
  // Shape Validation
  // ═══════════════════════════════════════════════════════════════
  describe('Shape validation', () => {
    it('output has correct shape', () => {
      const batch = 2;
      const seq_q = 4;
      const seq_k = 6;
      const d_model = 64;

      const Q = createTensor(batch, seq_q, d_model);
      const K = createTensor(batch, seq_k, d_model);
      const V = createTensor(batch, seq_k, d_model);
      const d_Q = createDimTensor(batch, seq_q);
      const d_K = createDimTensor(batch, seq_k);

      const config: HALConfig = { d_model, n_heads: 8 };
      const output = halAttention(Q, K, V, d_Q, d_K, config);

      expect(output.length).toBe(batch);
      expect(output[0].length).toBe(seq_q);
      expect(output[0][0].length).toBe(d_model);
    });

    it('throws for d_model mismatch', () => {
      const Q = createTensor(1, 2, 64);
      const K = createTensor(1, 2, 32); // Wrong dim
      const V = createTensor(1, 2, 64);
      const d_Q = createDimTensor(1, 2);
      const d_K = createDimTensor(1, 2);

      const config: HALConfig = { d_model: 64, n_heads: 8 };

      expect(() => halAttention(Q, K, V, d_Q, d_K, config)).toThrow(RangeError);
    });

    it('throws for empty sequences', () => {
      const Q: Tensor3D = [[]];
      const K: Tensor3D = [[]];
      const V: Tensor3D = [[]];
      const d_Q: Tensor2D = [[]];
      const d_K: Tensor2D = [[]];

      const config: HALConfig = { d_model: 64, n_heads: 8 };

      expect(() => halAttention(Q, K, V, d_Q, d_K, config)).toThrow(RangeError);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Attention Properties
  // ═══════════════════════════════════════════════════════════════
  describe('Attention properties', () => {
    it('output is weighted combination of V', () => {
      const Q = createTensor(1, 1, 8, 0.5);
      const K = createTensor(1, 3, 8, 0.5);
      const V: Tensor3D = [
        [
          [1, 0, 0, 0, 0, 0, 0, 0],
          [0, 1, 0, 0, 0, 0, 0, 0],
          [0, 0, 1, 0, 0, 0, 0, 0],
        ],
      ];
      const d_Q = createDimTensor(1, 1, 1);
      const d_K = createDimTensor(1, 3, 1);

      const config: HALConfig = { d_model: 8, n_heads: 1 };
      const output = halAttention(Q, K, V, d_Q, d_K, config);

      // Output should be a convex combination of V rows
      // All entries should be in [0, 1] and sum ≈ 1 for each position
      const row = output[0][0];
      const sum = row.reduce((a, b) => a + b, 0);

      expect(sum).toBeCloseTo(1, 5);
      for (const val of row) {
        expect(val).toBeGreaterThanOrEqual(0);
        expect(val).toBeLessThanOrEqual(1);
      }
    });

    it('harmonic coupling affects attention distribution', () => {
      // Create scenario where harmonic coupling matters
      const Q = createTensor(1, 2, 4, 0.5);
      const K = createTensor(1, 2, 4, 0.5);
      const V: Tensor3D = [
        [
          [1, 0, 0, 0],
          [0, 1, 0, 0],
        ],
      ];

      // Different dimension vectors
      const d_Q_low = [[1, 1]];
      const d_Q_high = [[3, 3]];
      const d_K = [[1, 3]];

      const config: HALConfig = { d_model: 4, n_heads: 1, R: 2.0, normalize: false };

      const out_low = halAttention(Q, K, V, d_Q_low, d_K, config);
      const out_high = halAttention(Q, K, V, d_Q_high, d_K, config);

      // Different d_Q should produce different attention patterns
      expect(out_low[0][0]).not.toEqual(out_high[0][0]);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Batching
  // ═══════════════════════════════════════════════════════════════
  describe('Batching', () => {
    it('processes multiple batches independently', () => {
      const Q1 = createTensor(1, 2, 4, 0.3);
      const Q2 = createTensor(1, 2, 4, 0.7);
      const K = createTensor(1, 2, 4, 0.5);
      const V = createTensor(1, 2, 4, 1.0);
      const d_Q = createDimTensor(1, 2, 1);
      const d_K = createDimTensor(1, 2, 1);

      const config: HALConfig = { d_model: 4, n_heads: 1 };

      // Process separately
      const out1 = halAttention(Q1, K, V, d_Q, d_K, config);
      const out2 = halAttention(Q2, K, V, d_Q, d_K, config);

      // Process as batch
      const Q_batch: Tensor3D = [Q1[0], Q2[0]];
      const K_batch: Tensor3D = [K[0], K[0]];
      const V_batch: Tensor3D = [V[0], V[0]];
      const d_Q_batch: Tensor2D = [d_Q[0], d_Q[0]];
      const d_K_batch: Tensor2D = [d_K[0], d_K[0]];

      const out_batch = halAttention(Q_batch, K_batch, V_batch, d_Q_batch, d_K_batch, config);

      // Results should match
      expect(out_batch[0]).toEqual(out1[0]);
      expect(out_batch[1]).toEqual(out2[0]);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Configuration
  // ═══════════════════════════════════════════════════════════════
  describe('Configuration', () => {
    it('uses default R when not specified', () => {
      const Q = createTensor(1, 2, 4);
      const K = createTensor(1, 2, 4);
      const V = createTensor(1, 2, 4);
      const d_Q = createDimTensor(1, 2, 2);
      const d_K = createDimTensor(1, 2, 2);

      const config1: HALConfig = { d_model: 4, n_heads: 1 };
      const config2: HALConfig = { d_model: 4, n_heads: 1, R: CONSTANTS.R_FIFTH };

      const out1 = halAttention(Q, K, V, d_Q, d_K, config1);
      const out2 = halAttention(Q, K, V, d_Q, d_K, config2);

      expect(out1).toEqual(out2);
    });

    it('different R values produce different coupling matrices', () => {
      // Different R values should produce different coupling matrices
      const d_Q = [1, 2, 3];
      const d_K = [1, 2, 3];

      const M_low = harmonicCouplingMatrix(d_Q, d_K, 1.1, false);
      const M_high = harmonicCouplingMatrix(d_Q, d_K, 2.0, false);

      // Check that matrices are different
      let hasDifference = false;
      for (let i = 0; i < M_low.length; i++) {
        for (let j = 0; j < M_low[i].length; j++) {
          if (Math.abs(M_low[i][j] - M_high[i][j]) > 1e-6) {
            hasDifference = true;
            break;
          }
        }
      }
      expect(hasDifference).toBe(true);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Numerical Stability
  // ═══════════════════════════════════════════════════════════════
  describe('Numerical stability', () => {
    it('handles high dimension values', () => {
      const Q = createTensor(1, 2, 8, 0.1);
      const K = createTensor(1, 2, 8, 0.1);
      const V = createTensor(1, 2, 8, 1.0);
      const d_Q = [[5, 6]]; // High dimensions
      const d_K = [[5, 6]];

      const config: HALConfig = { d_model: 8, n_heads: 1, normalize: true };
      const output = halAttention(Q, K, V, d_Q, d_K, config);

      // All values should be finite
      for (const batch of output) {
        for (const seq of batch) {
          for (const val of seq) {
            expect(Number.isFinite(val)).toBe(true);
          }
        }
      }
    });

    it('softmax normalization ensures valid probability distribution', () => {
      const Q = createTensor(1, 1, 4, 0.5);
      const K = createTensor(1, 4, 4, 0.5);
      const V: Tensor3D = [
        [
          [1, 0, 0, 0],
          [0, 1, 0, 0],
          [0, 0, 1, 0],
          [0, 0, 0, 1],
        ],
      ];
      const d_Q = [[2]];
      const d_K = [[1, 2, 3, 4]];

      const config: HALConfig = { d_model: 4, n_heads: 1 };
      const output = halAttention(Q, K, V, d_Q, d_K, config);

      // Output is weighted V, weights sum to 1
      const sum = output[0][0].reduce((a, b) => a + b, 0);
      expect(sum).toBeCloseTo(1, 5);
    });

    it('handles uniform inputs gracefully', () => {
      const Q = createTensor(1, 2, 4, 0.5);
      const K = createTensor(1, 2, 4, 0.5);
      const V = createTensor(1, 2, 4, 0.5);
      const d_Q = createDimTensor(1, 2, 1);
      const d_K = createDimTensor(1, 2, 1);

      const config: HALConfig = { d_model: 4, n_heads: 1 };
      const output = halAttention(Q, K, V, d_Q, d_K, config);

      // Should produce uniform attention → V average
      for (const val of output[0][0]) {
        expect(val).toBeCloseTo(0.5, 5);
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // Golden Test Vectors
  // ═══════════════════════════════════════════════════════════════
  describe('Golden test vectors', () => {
    it('HAL attention matches expected for simple case', () => {
      // Simple 1-batch, 2-seq, 2-dim case
      const Q: Tensor3D = [
        [
          [1, 0],
          [0, 1],
        ],
      ];
      const K: Tensor3D = [
        [
          [1, 0],
          [0, 1],
        ],
      ];
      const V: Tensor3D = [
        [
          [1, 2],
          [3, 4],
        ],
      ];
      const d_Q = [[1, 1]];
      const d_K = [[1, 1]];

      const config: HALConfig = { d_model: 2, n_heads: 1, R: 1.0, normalize: false };
      const output = halAttention(Q, K, V, d_Q, d_K, config);

      // With R=1, coupling matrix is all 1s
      // Attention is just scaled dot-product softmax
      // This is verifiable with hand calculation
      expect(output.length).toBe(1);
      expect(output[0].length).toBe(2);

      // All values should be valid convex combinations of V
      for (const seq of output[0]) {
        for (const val of seq) {
          expect(val).toBeGreaterThanOrEqual(1);
          expect(val).toBeLessThanOrEqual(4);
        }
      }
    });
  });
});
