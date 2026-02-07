"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.hkdfSha256 = hkdfSha256;
const node_crypto_1 = __importDefault(require("node:crypto"));
/**
 * Check if hkdfSync is available (Node.js 18+)
 */
function hasHkdfSync() {
    return typeof node_crypto_1.default.hkdfSync === 'function';
}
/**
 * Get hkdfSync function if available
 */
function getHkdfSync() {
    return node_crypto_1.default.hkdfSync;
}
/**
 * Derive key material using HKDF-SHA256
 * Uses native crypto.hkdfSync when available (Node.js 18+),
 * falls back to manual implementation for older versions.
 *
 * @param ikm - Input keying material
 * @param salt - Salt value
 * @param info - Context/application-specific info
 * @param len - Desired output length in bytes
 * @returns Derived key material
 */
function hkdfSha256(ikm, salt, info, len) {
    const hkdfSync = getHkdfSync();
    if (hasHkdfSync() && hkdfSync) {
        const result = hkdfSync('sha256', ikm, salt, info, len);
        // hkdfSync returns ArrayBuffer in newer Node versions, convert to Buffer
        return Buffer.from(result);
    }
    // Fallback implementation for older Node.js versions
    const prk = node_crypto_1.default.createHmac('sha256', salt).update(ikm).digest();
    const n = Math.ceil(len / 32);
    let t = Buffer.alloc(0);
    let okm = Buffer.alloc(0);
    for (let i = 0; i < n; i++) {
        t = node_crypto_1.default
            .createHmac('sha256', prk)
            .update(Buffer.concat([t, info, Buffer.from([i + 1])]))
            .digest();
        okm = Buffer.concat([okm, t]);
    }
    return okm.subarray(0, len);
}
//# sourceMappingURL=hkdf.js.map