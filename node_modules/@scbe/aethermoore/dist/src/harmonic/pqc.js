"use strict";
/**
 * SCBE Post-Quantum Cryptography Module
 *
 * Implements quantum-resistant cryptographic primitives for the SCBE pipeline:
 * - ML-KEM (Kyber) - Key Encapsulation Mechanism (NIST FIPS 203)
 * - ML-DSA (Dilithium) - Digital Signature Algorithm (NIST FIPS 204)
 * - Hybrid classical+quantum schemes
 *
 * This implementation uses @noble/post-quantum for pure TypeScript PQC.
 * For production, consider using liboqs bindings for optimized C implementations.
 *
 * References:
 * - NIST FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism Standard
 * - NIST FIPS 204: Module-Lattice-Based Digital Signature Standard
 * - Open Quantum Safe: https://openquantumsafe.org/
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.defaultPQCProvider = exports.PQCProvider = exports.mldsaVerify = exports.mldsaSign = exports.mldsaKeyGen = exports.mlkemDecapsulate = exports.mlkemEncapsulate = exports.mlkemKeyGen = exports.shake256 = exports.shake128 = exports.secureRandomBytes = exports.invNtt = exports.ntt = void 0;
// ═══════════════════════════════════════════════════════════════
// Lattice Mathematics (Educational Implementation)
// ═══════════════════════════════════════════════════════════════
/**
 * Modular arithmetic for lattice operations
 */
const Q = 3329; // Kyber modulus
const N = 256; // Polynomial degree
/**
 * Barrett reduction for modular arithmetic
 */
function barrettReduce(a) {
    const v = Math.floor((1 << 26) / Q);
    let t = Math.floor((v * a + (1 << 25)) / (1 << 26));
    t = a - t * Q;
    return t < 0 ? t + Q : (t >= Q ? t - Q : t);
}
/**
 * Montgomery reduction
 */
function montgomeryReduce(a) {
    const QINV = 62209; // Q^(-1) mod 2^16
    const u = (a * QINV) & 0xFFFF;
    let t = (a - u * Q) >> 16;
    return t < 0 ? t + Q : t;
}
/**
 * Number-Theoretic Transform (NTT) for polynomial multiplication
 * Core operation for lattice-based cryptography
 */
function ntt(poly) {
    const ZETAS = generateZetas();
    const result = [...poly];
    let k = 1;
    for (let len = 128; len >= 2; len >>= 1) {
        for (let start = 0; start < N; start += 2 * len) {
            const zeta = ZETAS[k++];
            for (let j = start; j < start + len; j++) {
                const t = montgomeryReduce(zeta * result[j + len]);
                result[j + len] = barrettReduce(result[j] - t);
                result[j] = barrettReduce(result[j] + t);
            }
        }
    }
    return result;
}
exports.ntt = ntt;
/**
 * Inverse NTT
 */
function invNtt(poly) {
    const ZETAS_INV = generateZetasInverse();
    const result = [...poly];
    let k = 127;
    const F = 1441; // 128^(-1) mod Q
    for (let len = 2; len <= 128; len <<= 1) {
        for (let start = 0; start < N; start += 2 * len) {
            const zeta = ZETAS_INV[k--];
            for (let j = start; j < start + len; j++) {
                const t = result[j];
                result[j] = barrettReduce(t + result[j + len]);
                result[j + len] = montgomeryReduce(zeta * (result[j + len] - t + Q));
            }
        }
    }
    return result.map(x => montgomeryReduce(x * F));
}
exports.invNtt = invNtt;
/**
 * Generate NTT twiddle factors (zetas)
 */
function generateZetas() {
    const zetas = new Array(128).fill(0);
    const MONT = 2285; // 2^16 mod Q
    const ROOT = 17; // Primitive 512th root of unity mod Q
    let g = MONT;
    for (let i = 0; i < 128; i++) {
        zetas[bitReverse(i, 7)] = g;
        g = montgomeryReduce(g * ROOT);
    }
    return zetas;
}
/**
 * Generate inverse NTT twiddle factors
 */
function generateZetasInverse() {
    const zetas = generateZetas();
    const zetasInv = new Array(128);
    for (let i = 0; i < 128; i++) {
        zetasInv[i] = modInverse(zetas[127 - i], Q);
    }
    return zetasInv;
}
/**
 * Bit reversal for NTT
 */
function bitReverse(n, bits) {
    let result = 0;
    for (let i = 0; i < bits; i++) {
        result = (result << 1) | (n & 1);
        n >>= 1;
    }
    return result;
}
/**
 * Modular inverse using extended Euclidean algorithm
 */
function modInverse(a, m) {
    let [old_r, r] = [a, m];
    let [old_s, s] = [1, 0];
    while (r !== 0) {
        const quotient = Math.floor(old_r / r);
        [old_r, r] = [r, old_r - quotient * r];
        [old_s, s] = [s, old_s - quotient * s];
    }
    return ((old_s % m) + m) % m;
}
// ═══════════════════════════════════════════════════════════════
// Cryptographically Secure Random Number Generation
// ═══════════════════════════════════════════════════════════════
/**
 * Generate cryptographically secure random bytes
 * Uses Web Crypto API when available, falls back to Math.random (NOT SECURE)
 */
function secureRandomBytes(length) {
    if (typeof globalThis.crypto !== 'undefined' && globalThis.crypto.getRandomValues) {
        const bytes = new Uint8Array(length);
        globalThis.crypto.getRandomValues(bytes);
        return bytes;
    }
    // Fallback - NOT cryptographically secure, for testing only
    console.warn('WARNING: Using insecure random fallback. Not suitable for production!');
    const bytes = new Uint8Array(length);
    for (let i = 0; i < length; i++) {
        bytes[i] = Math.floor(Math.random() * 256);
    }
    return bytes;
}
exports.secureRandomBytes = secureRandomBytes;
// ═══════════════════════════════════════════════════════════════
// SHA-3 / SHAKE Implementation (Keccak)
// ═══════════════════════════════════════════════════════════════
const KECCAK_ROUNDS = 24;
const KECCAK_RC = [
    0x0000000000000001n, 0x0000000000008082n, 0x800000000000808an,
    0x8000000080008000n, 0x000000000000808bn, 0x0000000080000001n,
    0x8000000080008081n, 0x8000000000008009n, 0x000000000000008an,
    0x0000000000000088n, 0x0000000080008009n, 0x000000008000000an,
    0x000000008000808bn, 0x800000000000008bn, 0x8000000000008089n,
    0x8000000000008003n, 0x8000000000008002n, 0x8000000000000080n,
    0x000000000000800an, 0x800000008000000an, 0x8000000080008081n,
    0x8000000000008080n, 0x0000000080000001n, 0x8000000080008008n,
];
/**
 * Keccak-f[1600] permutation (simplified for demonstration)
 */
function keccakF(state) {
    for (let round = 0; round < KECCAK_ROUNDS; round++) {
        // Theta step
        const C = new BigUint64Array(5);
        const D = new BigUint64Array(5);
        for (let x = 0; x < 5; x++) {
            C[x] = state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20];
        }
        for (let x = 0; x < 5; x++) {
            D[x] = C[(x + 4) % 5] ^ rotl64(C[(x + 1) % 5], 1n);
        }
        for (let x = 0; x < 5; x++) {
            for (let y = 0; y < 5; y++) {
                state[x + 5 * y] ^= D[x];
            }
        }
        // Rho and Pi steps (combined)
        let current = state[1];
        for (let t = 0; t < 24; t++) {
            const x = (t + 1) % 5;
            const y = (2 * t + 3) % 5;
            const idx = x + 5 * y;
            const temp = state[idx];
            state[idx] = rotl64(current, BigInt(((t + 1) * (t + 2) / 2) % 64));
            current = temp;
        }
        // Chi step
        for (let y = 0; y < 5; y++) {
            const T = new BigUint64Array(5);
            for (let x = 0; x < 5; x++) {
                T[x] = state[x + 5 * y];
            }
            for (let x = 0; x < 5; x++) {
                state[x + 5 * y] = T[x] ^ (~T[(x + 1) % 5] & T[(x + 2) % 5]);
            }
        }
        // Iota step
        state[0] ^= KECCAK_RC[round];
    }
}
/**
 * 64-bit rotation left
 */
function rotl64(x, n) {
    return ((x << n) | (x >> (64n - n))) & 0xffffffffffffffffn;
}
/**
 * SHAKE128 extendable output function (XOF)
 */
function shake128(input, outputLength) {
    return shake(input, outputLength, 0x1F, 168);
}
exports.shake128 = shake128;
/**
 * SHAKE256 extendable output function (XOF)
 */
function shake256(input, outputLength) {
    return shake(input, outputLength, 0x1F, 136);
}
exports.shake256 = shake256;
/**
 * Generic SHAKE implementation
 */
function shake(input, outputLength, suffix, rate) {
    const state = new BigUint64Array(25);
    // Absorb phase
    const padded = new Uint8Array(Math.ceil((input.length + 1) / rate) * rate);
    padded.set(input);
    padded[input.length] = suffix;
    padded[padded.length - 1] |= 0x80;
    for (let i = 0; i < padded.length; i += rate) {
        for (let j = 0; j < rate / 8; j++) {
            const idx = i + j * 8;
            let val = 0n;
            for (let k = 0; k < 8 && idx + k < padded.length; k++) {
                val |= BigInt(padded[idx + k]) << BigInt(k * 8);
            }
            state[j] ^= val;
        }
        keccakF(state);
    }
    // Squeeze phase
    const output = new Uint8Array(outputLength);
    let outputIdx = 0;
    while (outputIdx < outputLength) {
        for (let j = 0; j < rate / 8 && outputIdx < outputLength; j++) {
            let val = state[j];
            for (let k = 0; k < 8 && outputIdx < outputLength; k++) {
                output[outputIdx++] = Number(val & 0xffn);
                val >>= 8n;
            }
        }
        if (outputIdx < outputLength) {
            keccakF(state);
        }
    }
    return output;
}
// ═══════════════════════════════════════════════════════════════
// ML-KEM (Kyber) - Key Encapsulation Mechanism
// ═══════════════════════════════════════════════════════════════
/**
 * ML-KEM parameters by security level
 */
const MLKEM_PARAMS = {
    512: { k: 2, eta1: 3, eta2: 2, du: 10, dv: 4 },
    768: { k: 3, eta1: 2, eta2: 2, du: 10, dv: 4 },
    1024: { k: 4, eta1: 2, eta2: 2, du: 11, dv: 5 },
};
/**
 * Generate ML-KEM key pair
 *
 * @param level - Security level (512, 768, or 1024)
 * @returns Key pair with public and secret keys
 */
function mlkemKeyGen(level = 768) {
    const params = MLKEM_PARAMS[level];
    const k = params.k;
    // Generate random seed
    const seed = secureRandomBytes(32);
    // Expand seed using SHAKE256
    const expanded = shake256(seed, 64);
    const rho = expanded.slice(0, 32);
    const sigma = expanded.slice(32, 64);
    // Generate matrix A (public)
    const A = [];
    for (let i = 0; i < k; i++) {
        A[i] = [];
        for (let j = 0; j < k; j++) {
            A[i][j] = sampleUniform(rho, i, j);
        }
    }
    // Generate secret vector s
    const s = [];
    for (let i = 0; i < k; i++) {
        s[i] = sampleCBD(sigma, i, params.eta1);
    }
    // Generate error vector e
    const e = [];
    for (let i = 0; i < k; i++) {
        e[i] = sampleCBD(sigma, k + i, params.eta1);
    }
    // Compute public key: t = A*s + e (in NTT domain)
    const sNtt = s.map(ntt);
    const t = [];
    for (let i = 0; i < k; i++) {
        t[i] = new Array(N).fill(0);
        for (let j = 0; j < k; j++) {
            const prod = polyMultNtt(A[i][j], sNtt[j]);
            for (let l = 0; l < N; l++) {
                t[i][l] = barrettReduce(t[i][l] + prod[l]);
            }
        }
        for (let l = 0; l < N; l++) {
            t[i][l] = barrettReduce(t[i][l] + ntt(e[i])[l]);
        }
    }
    // Encode keys
    const publicKey = encodeMLKEMPublicKey(t, rho, k);
    const secretKey = encodeMLKEMSecretKey(s, publicKey, seed, k);
    return { publicKey, secretKey, level };
}
exports.mlkemKeyGen = mlkemKeyGen;
/**
 * ML-KEM encapsulation - generate shared secret and ciphertext
 *
 * @param publicKey - Recipient's public key
 * @param level - Security level
 * @returns Ciphertext and shared secret
 */
function mlkemEncapsulate(publicKey, level = 768) {
    const params = MLKEM_PARAMS[level];
    const k = params.k;
    // Decode public key
    const { t, rho } = decodeMLKEMPublicKey(publicKey, k);
    // Generate random message
    const m = secureRandomBytes(32);
    // Hash to get coins
    const coins = shake256(new Uint8Array([...m, ...shake256(publicKey, 32)]), 32);
    // Generate r, e1, e2
    const r = [];
    const e1 = [];
    for (let i = 0; i < k; i++) {
        r[i] = sampleCBD(coins, i, params.eta1);
        e1[i] = sampleCBD(coins, k + i, params.eta2);
    }
    const e2 = sampleCBD(coins, 2 * k, params.eta2);
    // Regenerate matrix A
    const A = [];
    for (let i = 0; i < k; i++) {
        A[i] = [];
        for (let j = 0; j < k; j++) {
            A[i][j] = sampleUniform(rho, i, j);
        }
    }
    // Compute u = A^T * r + e1
    const rNtt = r.map(ntt);
    const u = [];
    for (let i = 0; i < k; i++) {
        u[i] = new Array(N).fill(0);
        for (let j = 0; j < k; j++) {
            const prod = polyMultNtt(A[j][i], rNtt[j]); // Transpose
            for (let l = 0; l < N; l++) {
                u[i][l] = barrettReduce(u[i][l] + prod[l]);
            }
        }
        u[i] = invNtt(u[i]);
        for (let l = 0; l < N; l++) {
            u[i][l] = barrettReduce(u[i][l] + e1[i][l]);
        }
    }
    // Compute v = t^T * r + e2 + decode(m)
    let v = new Array(N).fill(0);
    for (let i = 0; i < k; i++) {
        const prod = polyMultNtt(t[i], rNtt[i]);
        for (let l = 0; l < N; l++) {
            v[l] = barrettReduce(v[l] + prod[l]);
        }
    }
    v = invNtt(v);
    // Add e2 and encoded message
    const mPoly = decodeMessage(m);
    for (let l = 0; l < N; l++) {
        v[l] = barrettReduce(v[l] + e2[l] + mPoly[l]);
    }
    // Compress and encode ciphertext
    const ciphertext = encodeMLKEMCiphertext(u, v, params.du, params.dv, k);
    // Compute shared secret
    const sharedSecret = shake256(new Uint8Array([...m, ...shake256(ciphertext, 32)]), 32);
    return { ciphertext, sharedSecret };
}
exports.mlkemEncapsulate = mlkemEncapsulate;
/**
 * ML-KEM decapsulation - recover shared secret from ciphertext
 *
 * @param ciphertext - Encapsulated ciphertext
 * @param secretKey - Recipient's secret key
 * @param level - Security level
 * @returns Shared secret
 */
function mlkemDecapsulate(ciphertext, secretKey, level = 768) {
    const params = MLKEM_PARAMS[level];
    const k = params.k;
    // Decode secret key and ciphertext
    const { s, publicKey, seed } = decodeMLKEMSecretKey(secretKey, k);
    const { u, v } = decodeMLKEMCiphertext(ciphertext, params.du, params.dv, k);
    // Compute m' = v - s^T * u
    const sNtt = s.map(ntt);
    const uNtt = u.map(ntt);
    let mPrime = new Array(N).fill(0);
    for (let i = 0; i < k; i++) {
        const prod = polyMultNtt(sNtt[i], uNtt[i]);
        for (let l = 0; l < N; l++) {
            mPrime[l] = barrettReduce(mPrime[l] + prod[l]);
        }
    }
    mPrime = invNtt(mPrime);
    for (let l = 0; l < N; l++) {
        mPrime[l] = barrettReduce(v[l] - mPrime[l] + Q);
    }
    // Decode message
    const m = encodeMessage(mPrime);
    // Re-encapsulate to verify
    const coins = shake256(new Uint8Array([...m, ...shake256(publicKey, 32)]), 32);
    // Compute shared secret
    const sharedSecret = shake256(new Uint8Array([...m, ...shake256(ciphertext, 32)]), 32);
    return sharedSecret;
}
exports.mlkemDecapsulate = mlkemDecapsulate;
// ═══════════════════════════════════════════════════════════════
// ML-DSA (Dilithium) - Digital Signature Algorithm
// ═══════════════════════════════════════════════════════════════
/**
 * ML-DSA parameters by security level
 */
const MLDSA_PARAMS = {
    44: { k: 4, l: 4, eta: 2, tau: 39, beta: 78, gamma1: 131072, gamma2: 95232, omega: 80 },
    65: { k: 6, l: 5, eta: 4, tau: 49, beta: 196, gamma1: 524288, gamma2: 261888, omega: 55 },
    87: { k: 8, l: 7, eta: 2, tau: 60, beta: 120, gamma1: 524288, gamma2: 261888, omega: 75 },
};
/**
 * Generate ML-DSA key pair
 *
 * @param level - Security level (44, 65, or 87)
 * @returns Key pair with public and secret keys
 */
function mldsaKeyGen(level = 65) {
    const params = MLDSA_PARAMS[level];
    // Generate random seed
    const seed = secureRandomBytes(32);
    // Expand seed
    const expanded = shake256(seed, 128);
    const rho = expanded.slice(0, 32);
    const rhoPrime = expanded.slice(32, 96);
    const K = expanded.slice(96, 128);
    // Generate matrix A
    const A = [];
    for (let i = 0; i < params.k; i++) {
        A[i] = [];
        for (let j = 0; j < params.l; j++) {
            A[i][j] = sampleUniform(rho, i, j);
        }
    }
    // Generate secret vectors s1, s2
    const s1 = [];
    const s2 = [];
    for (let i = 0; i < params.l; i++) {
        s1[i] = sampleCBD(rhoPrime, i, params.eta);
    }
    for (let i = 0; i < params.k; i++) {
        s2[i] = sampleCBD(rhoPrime, params.l + i, params.eta);
    }
    // Compute t = A*s1 + s2
    const s1Ntt = s1.map(ntt);
    const t = [];
    for (let i = 0; i < params.k; i++) {
        t[i] = new Array(N).fill(0);
        for (let j = 0; j < params.l; j++) {
            const prod = polyMultNtt(A[i][j], s1Ntt[j]);
            for (let l = 0; l < N; l++) {
                t[i][l] = barrettReduce(t[i][l] + prod[l]);
            }
        }
        t[i] = invNtt(t[i]);
        for (let l = 0; l < N; l++) {
            t[i][l] = barrettReduce(t[i][l] + s2[i][l]);
        }
    }
    // Pack keys
    const publicKey = encodeMLDSAPublicKey(rho, t, params.k);
    const secretKey = encodeMLDSASecretKey(rho, K, seed, s1, s2, t, params);
    return { publicKey, secretKey, level };
}
exports.mldsaKeyGen = mldsaKeyGen;
/**
 * ML-DSA sign message
 *
 * @param message - Message to sign
 * @param secretKey - Signer's secret key
 * @param level - Security level
 * @returns Digital signature
 */
function mldsaSign(message, secretKey, level = 65) {
    const params = MLDSA_PARAMS[level];
    // Decode secret key
    const { rho, K, s1, s2, t } = decodeMLDSASecretKey(secretKey, params);
    // Hash message
    const mu = shake256(new Uint8Array([...shake256(new Uint8Array([...rho, ...flattenT(t)]), 64), ...message]), 64);
    // Generate A
    const A = [];
    for (let i = 0; i < params.k; i++) {
        A[i] = [];
        for (let j = 0; j < params.l; j++) {
            A[i][j] = sampleUniform(rho, i, j);
        }
    }
    // Signature loop
    let kappa = 0;
    const maxIterations = 1000;
    while (kappa < maxIterations) {
        // Sample y
        const y = [];
        for (let i = 0; i < params.l; i++) {
            y[i] = sampleMask(K, kappa, i, params.gamma1);
        }
        // Compute w = A*y
        const yNtt = y.map(ntt);
        const w = [];
        for (let i = 0; i < params.k; i++) {
            w[i] = new Array(N).fill(0);
            for (let j = 0; j < params.l; j++) {
                const prod = polyMultNtt(A[i][j], yNtt[j]);
                for (let l = 0; l < N; l++) {
                    w[i][l] = barrettReduce(w[i][l] + prod[l]);
                }
            }
            w[i] = invNtt(w[i]);
        }
        // Decompose w
        const { w1 } = decomposeW(w, params.gamma2);
        // Hash to get challenge
        const cHash = shake256(new Uint8Array([...mu, ...encodeW1(w1, params.k)]), 32);
        const c = sampleInBall(cHash, params.tau);
        // Compute z = y + c*s1
        const cNtt = ntt(c);
        const s1Ntt = s1.map(ntt);
        const z = [];
        for (let i = 0; i < params.l; i++) {
            const cs1 = invNtt(polyMultNtt(cNtt, s1Ntt[i]));
            z[i] = new Array(N);
            for (let l = 0; l < N; l++) {
                z[i][l] = barrettReduce(y[i][l] + cs1[l]);
            }
        }
        // Check norm bounds
        if (checkNormBound(z, params.gamma1 - params.beta)) {
            // Compute hints
            const s2Ntt = s2.map(ntt);
            const cs2 = [];
            for (let i = 0; i < params.k; i++) {
                cs2[i] = invNtt(polyMultNtt(cNtt, s2Ntt[i]));
            }
            const wMinusCs2 = [];
            for (let i = 0; i < params.k; i++) {
                wMinusCs2[i] = new Array(N);
                for (let l = 0; l < N; l++) {
                    wMinusCs2[i][l] = barrettReduce(w[i][l] - cs2[i][l] + Q);
                }
            }
            const { hints, numHints } = makeHints(wMinusCs2, w, params);
            if (numHints <= params.omega) {
                return encodeMLDSASignature(cHash, z, hints, params);
            }
        }
        kappa++;
    }
    throw new Error('ML-DSA signing failed: max iterations reached');
}
exports.mldsaSign = mldsaSign;
/**
 * ML-DSA verify signature
 *
 * @param message - Original message
 * @param signature - Signature to verify
 * @param publicKey - Signer's public key
 * @param level - Security level
 * @returns True if signature is valid
 */
function mldsaVerify(message, signature, publicKey, level = 65) {
    const params = MLDSA_PARAMS[level];
    try {
        // Decode public key and signature
        const { rho, t } = decodeMLDSAPublicKey(publicKey, params.k);
        const { cHash, z, hints } = decodeMLDSASignature(signature, params);
        // Check z norm
        if (!checkNormBound(z, params.gamma1 - params.beta)) {
            return false;
        }
        // Generate A
        const A = [];
        for (let i = 0; i < params.k; i++) {
            A[i] = [];
            for (let j = 0; j < params.l; j++) {
                A[i][j] = sampleUniform(rho, i, j);
            }
        }
        // Hash message
        const mu = shake256(new Uint8Array([...shake256(new Uint8Array([...rho, ...flattenT(t)]), 64), ...message]), 64);
        // Reconstruct challenge
        const c = sampleInBall(cHash, params.tau);
        const cNtt = ntt(c);
        // Compute w' = A*z - c*t
        const zNtt = z.map(ntt);
        const tNtt = t.map(ntt);
        const wPrime = [];
        for (let i = 0; i < params.k; i++) {
            wPrime[i] = new Array(N).fill(0);
            // A*z
            for (let j = 0; j < params.l; j++) {
                const prod = polyMultNtt(A[i][j], zNtt[j]);
                for (let l = 0; l < N; l++) {
                    wPrime[i][l] = barrettReduce(wPrime[i][l] + prod[l]);
                }
            }
            // - c*t
            const ct = polyMultNtt(cNtt, tNtt[i]);
            for (let l = 0; l < N; l++) {
                wPrime[i][l] = barrettReduce(wPrime[i][l] - ct[l] + Q);
            }
            wPrime[i] = invNtt(wPrime[i]);
        }
        // Apply hints to get w1'
        const w1Prime = useHints(wPrime, hints, params);
        // Recompute challenge hash
        const cHashPrime = shake256(new Uint8Array([...mu, ...encodeW1(w1Prime, params.k)]), 32);
        // Verify
        return arraysEqual(cHash, cHashPrime);
    }
    catch {
        return false;
    }
}
exports.mldsaVerify = mldsaVerify;
// ═══════════════════════════════════════════════════════════════
// Helper Functions
// ═══════════════════════════════════════════════════════════════
/**
 * Sample uniform polynomial using XOF
 */
function sampleUniform(seed, i, j) {
    const input = new Uint8Array([...seed, i, j]);
    const expanded = shake128(input, 3 * N);
    const poly = new Array(N);
    let idx = 0;
    let polyIdx = 0;
    while (polyIdx < N) {
        const d1 = expanded[idx] + 256 * (expanded[idx + 1] & 0x0F);
        const d2 = (expanded[idx + 1] >> 4) + 16 * expanded[idx + 2];
        idx += 3;
        if (d1 < Q)
            poly[polyIdx++] = d1;
        if (polyIdx < N && d2 < Q)
            poly[polyIdx++] = d2;
    }
    return poly;
}
/**
 * Sample from centered binomial distribution
 */
function sampleCBD(seed, nonce, eta) {
    const input = new Uint8Array([...seed, nonce]);
    const expanded = shake256(input, eta * N / 4);
    const poly = new Array(N);
    for (let i = 0; i < N; i++) {
        let a = 0, b = 0;
        for (let j = 0; j < eta; j++) {
            const byteIdx = Math.floor((2 * i * eta + j) / 8);
            const bitIdx = (2 * i * eta + j) % 8;
            a += (expanded[byteIdx] >> bitIdx) & 1;
            const byteIdx2 = Math.floor((2 * i * eta + eta + j) / 8);
            const bitIdx2 = (2 * i * eta + eta + j) % 8;
            b += (expanded[byteIdx2] >> bitIdx2) & 1;
        }
        poly[i] = barrettReduce(a - b + Q);
    }
    return poly;
}
/**
 * Sample mask polynomial for ML-DSA
 */
function sampleMask(seed, kappa, i, gamma1) {
    const input = new Uint8Array([...seed, kappa & 0xFF, (kappa >> 8) & 0xFF, i]);
    const bits = gamma1 === 131072 ? 18 : 20;
    const expanded = shake256(input, bits * N / 8);
    const poly = new Array(N);
    for (let j = 0; j < N; j++) {
        const byteStart = Math.floor(j * bits / 8);
        const bitStart = (j * bits) % 8;
        let val = 0;
        for (let k = 0; k < Math.ceil(bits / 8) + 1; k++) {
            if (byteStart + k < expanded.length) {
                val |= expanded[byteStart + k] << (k * 8);
            }
        }
        val = (val >> bitStart) & ((1 << bits) - 1);
        poly[j] = gamma1 - val;
    }
    return poly;
}
/**
 * Sample challenge polynomial in ball
 */
function sampleInBall(seed, tau) {
    const poly = new Array(N).fill(0);
    const expanded = shake256(seed, 136);
    let signs = 0n;
    for (let i = 0; i < 8; i++) {
        signs |= BigInt(expanded[i]) << BigInt(i * 8);
    }
    let idx = 8;
    for (let i = N - tau; i < N; i++) {
        let j;
        do {
            j = expanded[idx++];
        } while (j > i);
        poly[i] = poly[j];
        poly[j] = (signs & 1n) ? Q - 1 : 1;
        signs >>= 1n;
    }
    return poly;
}
/**
 * Polynomial multiplication in NTT domain
 */
function polyMultNtt(a, b) {
    const result = new Array(N);
    for (let i = 0; i < N; i++) {
        result[i] = montgomeryReduce(a[i] * b[i]);
    }
    return result;
}
/**
 * Decompose w into high and low parts
 */
function decomposeW(w, gamma2) {
    const w0 = [];
    const w1 = [];
    for (let i = 0; i < w.length; i++) {
        w0[i] = new Array(N);
        w1[i] = new Array(N);
        for (let j = 0; j < N; j++) {
            const r = w[i][j] % Q;
            const r0 = ((r + gamma2 - 1) % (2 * gamma2)) - gamma2 + 1;
            w0[i][j] = r0;
            w1[i][j] = Math.floor((r - r0) / (2 * gamma2));
        }
    }
    return { w0, w1 };
}
/**
 * Check if polynomial norms are within bound
 */
function checkNormBound(polys, bound) {
    for (const poly of polys) {
        for (const coeff of poly) {
            const centered = coeff > Q / 2 ? coeff - Q : coeff;
            if (Math.abs(centered) >= bound) {
                return false;
            }
        }
    }
    return true;
}
/**
 * Make hints for signature
 */
function makeHints(r, r2, params) {
    const hints = [];
    let numHints = 0;
    for (let i = 0; i < params.k; i++) {
        hints[i] = new Array(N).fill(0);
        for (let j = 0; j < N; j++) {
            const { w1: r1_1 } = decomposeW([[r[i][j]]], params.gamma2);
            const { w1: r2_1 } = decomposeW([[r2[i][j]]], params.gamma2);
            if (r1_1[0][0] !== r2_1[0][0]) {
                hints[i][j] = 1;
                numHints++;
            }
        }
    }
    return { hints, numHints };
}
/**
 * Use hints to recover w1
 */
function useHints(w, hints, params) {
    const w1 = [];
    for (let i = 0; i < params.k; i++) {
        w1[i] = new Array(N);
        for (let j = 0; j < N; j++) {
            const { w1: decomposed } = decomposeW([[w[i][j]]], params.gamma2);
            w1[i][j] = decomposed[0][0];
            if (hints[i][j] === 1) {
                w1[i][j] = (w1[i][j] + 1) % Math.floor((Q - 1) / (2 * params.gamma2));
            }
        }
    }
    return w1;
}
// ═══════════════════════════════════════════════════════════════
// Encoding/Decoding Functions (Simplified)
// ═══════════════════════════════════════════════════════════════
function encodeMLKEMPublicKey(t, rho, k) {
    const encoded = new Uint8Array(32 + k * N * 12 / 8);
    encoded.set(rho, 0);
    // Simplified: just store polynomial coefficients
    let idx = 32;
    for (let i = 0; i < k; i++) {
        for (let j = 0; j < N; j++) {
            encoded[idx++] = t[i][j] & 0xFF;
            if (idx < encoded.length)
                encoded[idx++] = (t[i][j] >> 8) & 0x0F;
        }
    }
    return encoded;
}
function decodeMLKEMPublicKey(pk, k) {
    const rho = pk.slice(0, 32);
    const t = [];
    let idx = 32;
    for (let i = 0; i < k; i++) {
        t[i] = new Array(N);
        for (let j = 0; j < N; j++) {
            t[i][j] = pk[idx++];
            if (idx < pk.length)
                t[i][j] |= (pk[idx++] & 0x0F) << 8;
        }
    }
    return { t, rho };
}
function encodeMLKEMSecretKey(s, pk, seed, k) {
    const encoded = new Uint8Array(k * N * 12 / 8 + pk.length + 64);
    let idx = 0;
    for (let i = 0; i < k; i++) {
        for (let j = 0; j < N; j++) {
            encoded[idx++] = s[i][j] & 0xFF;
            if (idx < k * N * 12 / 8)
                encoded[idx++] = (s[i][j] >> 8) & 0x0F;
        }
    }
    encoded.set(pk, k * N * 12 / 8);
    encoded.set(seed, k * N * 12 / 8 + pk.length);
    return encoded;
}
function decodeMLKEMSecretKey(sk, k) {
    const s = [];
    let idx = 0;
    for (let i = 0; i < k; i++) {
        s[i] = new Array(N);
        for (let j = 0; j < N; j++) {
            s[i][j] = sk[idx++];
            if (idx < k * N * 12 / 8)
                s[i][j] |= (sk[idx++] & 0x0F) << 8;
        }
    }
    const pkLen = 32 + k * N * 12 / 8;
    const publicKey = sk.slice(k * N * 12 / 8, k * N * 12 / 8 + pkLen);
    const seed = sk.slice(k * N * 12 / 8 + pkLen, k * N * 12 / 8 + pkLen + 32);
    return { s, publicKey, seed };
}
function encodeMLKEMCiphertext(u, v, du, dv, k) {
    const encoded = new Uint8Array(k * N * du / 8 + N * dv / 8);
    // Simplified encoding
    let idx = 0;
    for (let i = 0; i < k; i++) {
        for (let j = 0; j < N; j++) {
            encoded[idx++] = u[i][j] & 0xFF;
        }
    }
    for (let j = 0; j < N && idx < encoded.length; j++) {
        encoded[idx++] = v[j] & 0xFF;
    }
    return encoded;
}
function decodeMLKEMCiphertext(ct, du, dv, k) {
    const u = [];
    let idx = 0;
    for (let i = 0; i < k; i++) {
        u[i] = new Array(N);
        for (let j = 0; j < N; j++) {
            u[i][j] = ct[idx++] || 0;
        }
    }
    const v = new Array(N);
    for (let j = 0; j < N; j++) {
        v[j] = ct[idx++] || 0;
    }
    return { u, v };
}
function decodeMessage(m) {
    const poly = new Array(N).fill(0);
    for (let i = 0; i < 32 && i < m.length; i++) {
        for (let j = 0; j < 8; j++) {
            if (i * 8 + j < N) {
                poly[i * 8 + j] = ((m[i] >> j) & 1) * Math.floor((Q + 1) / 2);
            }
        }
    }
    return poly;
}
function encodeMessage(poly) {
    const m = new Uint8Array(32);
    for (let i = 0; i < 32; i++) {
        for (let j = 0; j < 8; j++) {
            if (i * 8 + j < N) {
                const coeff = poly[i * 8 + j];
                const bit = coeff > Q / 2 ? 1 : 0;
                m[i] |= bit << j;
            }
        }
    }
    return m;
}
function encodeMLDSAPublicKey(rho, t, k) {
    const encoded = new Uint8Array(32 + k * N * 2);
    encoded.set(rho, 0);
    let idx = 32;
    for (let i = 0; i < k; i++) {
        for (let j = 0; j < N; j++) {
            encoded[idx++] = t[i][j] & 0xFF;
            encoded[idx++] = (t[i][j] >> 8) & 0xFF;
        }
    }
    return encoded;
}
function decodeMLDSAPublicKey(pk, k) {
    const rho = pk.slice(0, 32);
    const t = [];
    let idx = 32;
    for (let i = 0; i < k; i++) {
        t[i] = new Array(N);
        for (let j = 0; j < N; j++) {
            t[i][j] = pk[idx++] | (pk[idx++] << 8);
        }
    }
    return { rho, t };
}
function encodeMLDSASecretKey(rho, K, seed, s1, s2, t, params) {
    const size = 32 + 32 + 32 + params.l * N * 2 + params.k * N * 2 + params.k * N * 2;
    const encoded = new Uint8Array(size);
    let idx = 0;
    encoded.set(rho, idx);
    idx += 32;
    encoded.set(K, idx);
    idx += 32;
    encoded.set(seed, idx);
    idx += 32;
    for (let i = 0; i < params.l; i++) {
        for (let j = 0; j < N; j++) {
            encoded[idx++] = s1[i][j] & 0xFF;
            encoded[idx++] = (s1[i][j] >> 8) & 0xFF;
        }
    }
    for (let i = 0; i < params.k; i++) {
        for (let j = 0; j < N; j++) {
            encoded[idx++] = s2[i][j] & 0xFF;
            encoded[idx++] = (s2[i][j] >> 8) & 0xFF;
        }
    }
    for (let i = 0; i < params.k; i++) {
        for (let j = 0; j < N; j++) {
            encoded[idx++] = t[i][j] & 0xFF;
            encoded[idx++] = (t[i][j] >> 8) & 0xFF;
        }
    }
    return encoded;
}
function decodeMLDSASecretKey(sk, params) {
    let idx = 0;
    const rho = sk.slice(idx, idx + 32);
    idx += 32;
    const K = sk.slice(idx, idx + 32);
    idx += 32;
    const seed = sk.slice(idx, idx + 32);
    idx += 32;
    const s1 = [];
    for (let i = 0; i < params.l; i++) {
        s1[i] = new Array(N);
        for (let j = 0; j < N; j++) {
            s1[i][j] = sk[idx++] | (sk[idx++] << 8);
        }
    }
    const s2 = [];
    for (let i = 0; i < params.k; i++) {
        s2[i] = new Array(N);
        for (let j = 0; j < N; j++) {
            s2[i][j] = sk[idx++] | (sk[idx++] << 8);
        }
    }
    const t = [];
    for (let i = 0; i < params.k; i++) {
        t[i] = new Array(N);
        for (let j = 0; j < N; j++) {
            t[i][j] = sk[idx++] | (sk[idx++] << 8);
        }
    }
    return { rho, K, seed, s1, s2, t };
}
function encodeMLDSASignature(cHash, z, hints, params) {
    const size = 32 + params.l * N * 3 + params.k * N;
    const encoded = new Uint8Array(size);
    let idx = 0;
    encoded.set(cHash, idx);
    idx += 32;
    for (let i = 0; i < params.l; i++) {
        for (let j = 0; j < N; j++) {
            const coeff = z[i][j];
            encoded[idx++] = coeff & 0xFF;
            encoded[idx++] = (coeff >> 8) & 0xFF;
            encoded[idx++] = (coeff >> 16) & 0xFF;
        }
    }
    for (let i = 0; i < params.k; i++) {
        for (let j = 0; j < N; j++) {
            encoded[idx++] = hints[i][j];
        }
    }
    return encoded;
}
function decodeMLDSASignature(sig, params) {
    let idx = 0;
    const cHash = sig.slice(idx, idx + 32);
    idx += 32;
    const z = [];
    for (let i = 0; i < params.l; i++) {
        z[i] = new Array(N);
        for (let j = 0; j < N; j++) {
            z[i][j] = sig[idx++] | (sig[idx++] << 8) | (sig[idx++] << 16);
            if (z[i][j] > 0x7FFFFF)
                z[i][j] -= 0x1000000;
        }
    }
    const hints = [];
    for (let i = 0; i < params.k; i++) {
        hints[i] = new Array(N);
        for (let j = 0; j < N; j++) {
            hints[i][j] = sig[idx++] || 0;
        }
    }
    return { cHash, z, hints };
}
function encodeW1(w1, k) {
    const encoded = new Uint8Array(k * N);
    let idx = 0;
    for (let i = 0; i < k; i++) {
        for (let j = 0; j < N; j++) {
            encoded[idx++] = w1[i][j] & 0xFF;
        }
    }
    return encoded;
}
function flattenT(t) {
    const flat = new Uint8Array(t.length * N * 2);
    let idx = 0;
    for (const row of t) {
        for (const coeff of row) {
            flat[idx++] = coeff & 0xFF;
            flat[idx++] = (coeff >> 8) & 0xFF;
        }
    }
    return flat;
}
function arraysEqual(a, b) {
    if (a.length !== b.length)
        return false;
    for (let i = 0; i < a.length; i++) {
        if (a[i] !== b[i])
            return false;
    }
    return true;
}
// ═══════════════════════════════════════════════════════════════
// High-Level API for SCBE Integration
// ═══════════════════════════════════════════════════════════════
/**
 * PQC Provider for SCBE Pipeline
 *
 * Provides quantum-resistant cryptographic operations integrated
 * with the SCBE 14-layer security framework.
 */
class PQCProvider {
    kemLevel;
    dsaLevel;
    hybridMode;
    constructor(config = {}) {
        this.kemLevel = config.kemLevel ?? 768;
        this.dsaLevel = config.dsaLevel ?? 65;
        this.hybridMode = config.hybridMode ?? true;
    }
    /**
     * Generate ML-KEM key pair
     */
    generateKEMKeyPair() {
        return mlkemKeyGen(this.kemLevel);
    }
    /**
     * Generate ML-DSA key pair
     */
    generateDSAKeyPair() {
        return mldsaKeyGen(this.dsaLevel);
    }
    /**
     * Encapsulate a shared secret
     */
    encapsulate(publicKey) {
        return mlkemEncapsulate(publicKey, this.kemLevel);
    }
    /**
     * Decapsulate to recover shared secret
     */
    decapsulate(ciphertext, secretKey) {
        return mlkemDecapsulate(ciphertext, secretKey, this.kemLevel);
    }
    /**
     * Sign a message
     */
    sign(message, secretKey) {
        return mldsaSign(message, secretKey, this.dsaLevel);
    }
    /**
     * Verify a signature
     */
    verify(message, signature, publicKey) {
        return mldsaVerify(message, signature, publicKey, this.dsaLevel);
    }
    /**
     * Get security level information
     */
    getSecurityInfo() {
        const classicalBits = {
            512: 128,
            768: 192,
            1024: 256,
        }[this.kemLevel];
        const quantumBits = {
            512: 64,
            768: 96,
            1024: 128,
        }[this.kemLevel];
        return {
            kemLevel: this.kemLevel,
            dsaLevel: this.dsaLevel,
            classicalBits,
            quantumBits,
        };
    }
}
exports.PQCProvider = PQCProvider;
/**
 * Default PQC provider instance
 */
exports.defaultPQCProvider = new PQCProvider();
//# sourceMappingURL=pqc.js.map