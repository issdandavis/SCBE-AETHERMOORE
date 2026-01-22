"use strict";
/**
 * SCBE HAL - Harmonic Attention Layer
 *
 * Implements attention mechanism with harmonic coupling matrix:
 * - Λ(d)[i,j] = R^(d_i · d_j) harmonic weighting
 * - Softmax attention with harmonic modulation
 * - Batched tensor operations
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.harmonicCouplingMatrix = harmonicCouplingMatrix;
exports.halAttention = halAttention;
const constants_js_1 = require("./constants.js");
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
function harmonicCouplingMatrix(d_Q, d_K, R = constants_js_1.CONSTANTS.R_FIFTH, normalize = true) {
    if (!(R > 0))
        throw new RangeError('R must be > 0');
    const n = d_Q.length, m = d_K.length;
    const M = Array.from({ length: n }, () => Array(m).fill(0));
    let dmax = 0;
    if (normalize) {
        const maxQ = Math.max(...d_Q), maxK = Math.max(...d_K);
        dmax = maxQ * maxK;
    }
    const lnR = Math.log(R);
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < m; j++) {
            const expo = d_Q[i] * d_K[j] - (normalize ? dmax : 0);
            M[i][j] = Math.exp(expo * lnR);
        }
    }
    return M;
}
/**
 * Row-wise softmax normalization
 */
function softmaxRowWise(M) {
    return M.map((row) => {
        const maxVal = Math.max(...row);
        const a = row.map((x) => x - maxVal);
        const e = a.map(Math.exp);
        const Z = e.reduce((p, c) => p + c, 0) || 1;
        return e.map((x) => x / Z);
    });
}
/**
 * Matrix multiplication C = A × B
 */
function matMul(A, B) {
    const n = A.length, k = A[0]?.length ?? 0, m = B[0]?.length ?? 0;
    if (k !== B.length)
        throw new RangeError('matMul shape mismatch');
    const C = Array.from({ length: n }, () => Array(m).fill(0));
    for (let i = 0; i < n; i++) {
        for (let t = 0; t < k; t++) {
            const a = A[i][t];
            const Bt = B[t];
            for (let j = 0; j < m; j++)
                C[i][j] += a * Bt[j];
        }
    }
    return C;
}
/**
 * Matrix transpose
 */
function transpose(A) {
    const n = A.length, m = A[0]?.length ?? 0;
    const T = Array.from({ length: m }, () => Array(n).fill(0));
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < m; j++)
            T[j][i] = A[i][j];
    }
    return T;
}
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
function halAttention(Q, K, V, d_Q, d_K, config) {
    const B = Q.length;
    const d_model = config.d_model;
    const R = config.R ?? constants_js_1.CONSTANTS.R_FIFTH;
    const normalize = config.normalize ?? true;
    const out = [];
    for (let b = 0; b < B; b++) {
        const Qb = Q[b], Kb = K[b], Vb = V[b];
        const n = Qb.length, m = Kb.length;
        if (!n || !m)
            throw new RangeError('Empty Q/K sequences');
        if ((Qb[0]?.length ?? 0) !== d_model ||
            (Kb[0]?.length ?? 0) !== d_model ||
            (Vb[0]?.length ?? 0) !== d_model) {
            throw new RangeError('d_model mismatch');
        }
        // Scaled dot-product: S = (Q × K^T) / √d_model
        const S = matMul(Qb, transpose(Kb)).map((row) => row.map((x) => x / Math.sqrt(d_model)));
        // Harmonic coupling: S = S ⊙ Λ
        const Lambda = harmonicCouplingMatrix(d_Q[b], d_K[b], R, normalize);
        for (let i = 0; i < n; i++) {
            for (let j = 0; j < m; j++) {
                S[i][j] *= Lambda[i][j];
            }
        }
        // Softmax and value projection
        const W = softmaxRowWise(S);
        const Y = matMul(W, Vb);
        out.push(Y);
    }
    return out;
}
//# sourceMappingURL=halAttention.js.map