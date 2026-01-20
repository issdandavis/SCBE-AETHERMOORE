"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.hkdfSha256 = hkdfSha256;
const node_crypto_1 = __importDefault(require("node:crypto"));
function hkdfSha256(ikm, salt, info, len) {
    if (node_crypto_1.default.hkdfSync) {
        const result = node_crypto_1.default.hkdfSync('sha256', ikm, salt, info, len);
        // hkdfSync returns ArrayBuffer in newer Node versions, convert to Buffer
        return Buffer.from(result);
    }
    // Fallback implementation
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