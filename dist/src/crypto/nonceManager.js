"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.nextNonce = nextNonce;
exports.deriveNoncePrefix = deriveNoncePrefix;
exports.resetSessionCounter = resetSessionCounter;
const node_crypto_1 = __importDefault(require("node:crypto"));
/**
 * Generate a cryptographically secure random 96-bit (12-byte) nonce.
 *
 * FIX for HIGH-001: Previously used an in-memory counter that reset on process
 * restart, risking nonce reuse with the same session_id. Random nonces eliminate
 * this vulnerability entirely.
 *
 * Birthday bound: ~2^48 messages before 50% collision probability, which is
 * acceptable for typical authorization workloads.
 */
function nextNonce() {
    return { nonce: node_crypto_1.default.randomBytes(12) };
}
/**
 * @deprecated No longer used for nonce generation. Session binding is enforced
 * via AAD (env, provider_id, intent_id) rather than nonce prefix.
 * Kept for backward compatibility with any external callers.
 */
function deriveNoncePrefix(_kNonce, _sessionId) {
    // Return 8 zero bytes - prefix matching is disabled in verifyEnvelope
    return Buffer.alloc(8);
}
/**
 * @deprecated Counter-based nonce tracking removed (HIGH-001 fix).
 * This function is now a no-op kept for API compatibility.
 */
function resetSessionCounter(_sessionId) {
    // No-op: random nonces don't require session tracking
}
//# sourceMappingURL=nonceManager.js.map