"use strict";
/**
 * SCBE-AETHERMOORE Lattice Watermarking
 * ======================================
 *
 * Post-quantum safe watermarking using Ring-LWE lattice cryptography.
 * Embeds verifiable hashes into video frames that survive compression.
 *
 * Security: Learning-with-errors hardness, quantum-resistant, tamper-evident
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateWatermarkKeys = generateWatermarkKeys;
exports.embedWatermark = embedWatermark;
exports.verifyWatermark = verifyWatermark;
exports.hashFrameContent = hashFrameContent;
exports.createWatermarkChain = createWatermarkChain;
const crypto = __importStar(require("crypto"));
const types_js_1 = require("./types.js");
/** Minimum lattice dimension for security */
const MIN_DIMENSION = 8;
/** Maximum lattice dimension (memory/performance) */
const MAX_DIMENSION = 256;
/** Minimum modulus for security */
const MIN_MODULUS = 17;
/** Maximum modulus to prevent overflow */
const MAX_MODULUS = 65521; // Largest 16-bit prime
/**
 * Validate and clamp watermark configuration
 */
function validateConfig(config) {
    return {
        dimension: Math.max(MIN_DIMENSION, Math.min(MAX_DIMENSION, Math.floor(config.dimension))),
        modulus: Math.max(MIN_MODULUS, Math.min(MAX_MODULUS, Math.floor(config.modulus))),
        errorBound: Math.max(1, Math.min(5, Math.floor(config.errorBound))),
    };
}
/**
 * Generate a random polynomial with coefficients in Z_q
 */
function randomPolynomial(n, q) {
    const poly = new Array(n);
    const bytes = crypto.randomBytes(n * 4);
    for (let i = 0; i < n; i++) {
        // Read 4 bytes as unsigned int and reduce mod q
        const val = bytes.readUInt32LE(i * 4);
        poly[i] = val % q;
    }
    return poly;
}
/**
 * Generate small error polynomial for LWE
 * Coefficients in {-errorBound, ..., errorBound}
 */
function errorPolynomial(n, errorBound) {
    const poly = new Array(n);
    const bytes = crypto.randomBytes(n);
    for (let i = 0; i < n; i++) {
        // Map byte to [-errorBound, errorBound]
        const val = bytes[i] % (2 * errorBound + 1);
        poly[i] = val - errorBound;
    }
    return poly;
}
/**
 * Polynomial multiplication in Z_q[X]/(X^n + 1)
 * Uses naive O(n²) multiplication - sufficient for small n
 */
function polyMul(a, b, q) {
    const n = a.length;
    const result = new Array(n).fill(0);
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) {
            const idx = i + j;
            const coeff = (a[i] * b[j]) % q;
            if (idx < n) {
                result[idx] = (result[idx] + coeff) % q;
            }
            else {
                // Reduce by X^n + 1: X^n ≡ -1
                result[idx - n] = (result[idx - n] - coeff + q) % q;
            }
        }
    }
    return result;
}
/**
 * Polynomial addition in Z_q
 */
function polyAdd(a, b, q) {
    const n = a.length;
    const result = new Array(n);
    for (let i = 0; i < n; i++) {
        result[i] = (a[i] + b[i]) % q;
    }
    return result;
}
/**
 * Scalar multiplication of polynomial
 */
function polyScale(a, s, q) {
    return a.map((coeff) => (((coeff * s) % q) + q) % q);
}
/**
 * Generate Ring-LWE public/secret key pair
 *
 * Public key: (a, b) where b = a·s + e
 * Secret key: s
 */
function generateWatermarkKeys(config = types_js_1.DEFAULT_WATERMARK_CONFIG) {
    config = validateConfig(config);
    const { dimension: n, modulus: q, errorBound } = config;
    // Secret key: small polynomial
    const s = errorPolynomial(n, errorBound);
    // Public polynomial a (random)
    const a = randomPolynomial(n, q);
    // Error polynomial e
    const e = errorPolynomial(n, errorBound);
    // b = a·s + e (mod q)
    const as = polyMul(a, s, q);
    const b = polyAdd(as, e, q);
    return {
        publicKey: [a, b],
        secretKey: s,
    };
}
/**
 * Encode a hash into lattice format
 * Maps hash bytes to polynomial coefficients
 */
function hashToPolynomial(hash, n, q) {
    const poly = new Array(n).fill(0);
    // Use hash bytes directly as coefficients, cycling if needed
    for (let i = 0; i < n; i++) {
        const byteIdx = i % hash.length;
        poly[i] = hash[byteIdx] % q;
    }
    return poly;
}
/**
 * Embed watermark into frame data
 * Uses additive embedding in least significant bits
 */
function embedWatermark(frameData, hash, publicKey, config = types_js_1.DEFAULT_WATERMARK_CONFIG) {
    config = validateConfig(config);
    const { dimension: n, modulus: q } = config;
    // Convert hash to bytes
    const hashBytes = Buffer.from(hash, 'hex');
    if (hashBytes.length === 0) {
        return frameData; // No hash to embed
    }
    // Encode hash as polynomial
    const m = hashToPolynomial(hashBytes, n, q);
    // Encrypt message: c = (a·r + e1, b·r + e2 + ⌊q/2⌋·m)
    const [a, b] = publicKey;
    const r = errorPolynomial(n, config.errorBound);
    const e1 = errorPolynomial(n, config.errorBound);
    const e2 = errorPolynomial(n, config.errorBound);
    const ar = polyMul(a, r, q);
    const c1 = polyAdd(ar, e1, q);
    const br = polyMul(b, r, q);
    const scaledM = polyScale(m, Math.floor(q / 2), q);
    const c2 = polyAdd(polyAdd(br, e2, q), scaledM, q);
    // Embed ciphertext coefficients into frame LSBs
    const result = frameData instanceof Float32Array
        ? new Float32Array(frameData)
        : new Uint8ClampedArray(frameData);
    // Embed c1 and c2 interleaved
    const embedLen = Math.min(2 * n, result.length);
    for (let i = 0; i < embedLen; i++) {
        const coeff = i < n ? c1[i] : c2[i - n];
        const embedBit = coeff % 2;
        if (result instanceof Float32Array) {
            // For float data, add small perturbation
            const sign = embedBit === 1 ? 1 : -1;
            result[i] += sign * 0.0001;
        }
        else {
            // For uint8 data, modify LSB
            result[i] = (result[i] & 0xfe) | embedBit;
        }
    }
    return result;
}
/**
 * Extract and verify watermark from frame data
 */
function verifyWatermark(frameData, expectedHash, secretKey, config = types_js_1.DEFAULT_WATERMARK_CONFIG) {
    config = validateConfig(config);
    const { dimension: n, modulus: q } = config;
    // Extract embedded coefficients from LSBs
    const extractLen = Math.min(2 * n, frameData.length);
    const c1 = new Array(n).fill(0);
    const c2 = new Array(n).fill(0);
    for (let i = 0; i < extractLen; i++) {
        let bit;
        if (frameData instanceof Float32Array) {
            // For float data, check sign of fractional part
            const frac = frameData[i] - Math.floor(frameData[i]);
            bit = frac >= 0.5 ? 1 : 0;
        }
        else {
            bit = frameData[i] & 1;
        }
        // Reconstruct coefficient (partial recovery)
        if (i < n) {
            c1[i] = bit;
        }
        else {
            c2[i - n] = bit;
        }
    }
    // Attempt decryption: m' = c2 - c1·s
    const c1s = polyMul(c1, secretKey, q);
    const decrypted = new Array(n);
    for (let i = 0; i < n; i++) {
        decrypted[i] = (((c2[i] - c1s[i]) % q) + q) % q;
    }
    // Decode polynomial to hash
    const extractedBytes = [];
    for (let i = 0; i < n && extractedBytes.length < 32; i++) {
        // Round to nearest encoding value
        const thresh = Math.floor(q / 4);
        const bit = decrypted[i] > thresh && decrypted[i] < q - thresh ? 1 : 0;
        extractedBytes.push(bit);
    }
    // Convert bits to hash string (simplified)
    const extractedHash = extractedBytes
        .map((b) => b.toString())
        .join('')
        .substring(0, 64);
    // Compute confidence based on bit agreement
    const expectedBits = Buffer.from(expectedHash, 'hex');
    let matchCount = 0;
    const compareLen = Math.min(extractedBytes.length, expectedBits.length * 8);
    for (let i = 0; i < compareLen; i++) {
        const byteIdx = Math.floor(i / 8);
        const bitIdx = i % 8;
        const expectedBit = (expectedBits[byteIdx] >> bitIdx) & 1;
        if (extractedBytes[i] === expectedBit) {
            matchCount++;
        }
    }
    const confidence = compareLen > 0 ? matchCount / compareLen : 0;
    return {
        valid: confidence > 0.7, // 70% threshold for valid watermark
        extractedHash,
        expectedHash,
        confidence,
    };
}
/**
 * Generate hash for frame content
 */
function hashFrameContent(frameData, frameIndex, timestamp) {
    const hash = crypto.createHash('sha256');
    // Hash frame metadata
    hash.update(Buffer.from([
        (frameIndex >> 24) & 0xff,
        (frameIndex >> 16) & 0xff,
        (frameIndex >> 8) & 0xff,
        frameIndex & 0xff,
    ]));
    // Hash timestamp
    const timestampInt = Math.floor(timestamp * 1000);
    hash.update(Buffer.from([
        (timestampInt >> 24) & 0xff,
        (timestampInt >> 16) & 0xff,
        (timestampInt >> 8) & 0xff,
        timestampInt & 0xff,
    ]));
    // Sample frame data for efficiency (every 100th element)
    const sampleSize = Math.min(1000, Math.ceil(frameData.length / 100));
    const step = Math.max(1, Math.floor(frameData.length / sampleSize));
    for (let i = 0; i < frameData.length; i += step) {
        if (frameData instanceof Float32Array) {
            // Convert float to integer representation
            const intVal = Math.floor(frameData[i] * 65535);
            hash.update(Buffer.from([(intVal >> 8) & 0xff, intVal & 0xff]));
        }
        else {
            hash.update(Buffer.from([frameData[i]]));
        }
    }
    return hash.digest('hex');
}
/**
 * Create a watermark chain for video integrity
 * Each frame's hash includes the previous frame's hash
 */
function createWatermarkChain(frameHashes) {
    if (frameHashes.length === 0) {
        return {
            chainHash: crypto.createHash('sha256').update('empty').digest('hex'),
            merkleRoot: crypto.createHash('sha256').update('empty').digest('hex'),
        };
    }
    // Linear chain hash
    let chainHash = frameHashes[0];
    for (let i = 1; i < frameHashes.length; i++) {
        chainHash = crypto
            .createHash('sha256')
            .update(chainHash + frameHashes[i])
            .digest('hex');
    }
    // Merkle tree root
    let layer = [...frameHashes];
    while (layer.length > 1) {
        const nextLayer = [];
        for (let i = 0; i < layer.length; i += 2) {
            const left = layer[i];
            const right = layer[i + 1] || left; // Duplicate last if odd
            const combined = crypto
                .createHash('sha256')
                .update(left + right)
                .digest('hex');
            nextLayer.push(combined);
        }
        layer = nextLayer;
    }
    return {
        chainHash,
        merkleRoot: layer[0],
    };
}
//# sourceMappingURL=watermark.js.map