"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.resetSessionCounter = exports.nextNonce = exports.deriveNoncePrefix = void 0;
const hkdf_js_1 = require("./hkdf.js");
const node_crypto_1 = __importDefault(require("node:crypto"));
const counters = new Map();
function deriveNoncePrefix(kNonce, sessionId) {
    // 64-bit prefix: HKDF(k_nonce, session_id)
    const info = Buffer.from(`scbe:nonce:prefix:v1`);
    const salt = node_crypto_1.default.createHash('sha256').update(sessionId).digest();
    return (0, hkdf_js_1.hkdfSha256)(kNonce, salt, info, 8);
}
exports.deriveNoncePrefix = deriveNoncePrefix;
function nextNonce(prefix, sessionId) {
    const key = sessionId;
    const cur = counters.get(key) ?? -1;
    const next = (cur + 1) >>> 0; // 32-bit counter
    counters.set(key, next);
    // Rotate before wrap
    if (next === 0xFFFFFFFF) {
        throw new Error('nonce counter exhausted; rotate key/session');
    }
    const counterBuf = Buffer.alloc(4);
    counterBuf.writeUInt32BE(next, 0);
    return { nonce: Buffer.concat([prefix, counterBuf]), counter: next };
}
exports.nextNonce = nextNonce;
function resetSessionCounter(sessionId) {
    counters.delete(sessionId);
}
exports.resetSessionCounter = resetSessionCounter;
//# sourceMappingURL=nonceManager.js.map