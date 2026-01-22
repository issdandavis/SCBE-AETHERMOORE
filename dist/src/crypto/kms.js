"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getMasterKey = getMasterKey;
/**
 * Replace with your real KMS/HSM integration.
 * Contract: getMasterKey(kid) returns a 32-byte key (Buffer) with export disabled in production.
 */
const node_crypto_1 = __importDefault(require("node:crypto"));
const cache = new Map();
async function getMasterKey(kid) {
    if (cache.has(kid))
        return cache.get(kid);
    const uri = process.env.SCBE_KMS_URI || 'mem://dev';
    // DEMO ONLY: derive a process-unique pseudo-key from kid+uri (DO NOT USE IN PROD)
    const key = node_crypto_1.default.createHash('sha256').update(`${uri}:${kid}`).digest(); // 32 bytes
    cache.set(kid, key);
    return key;
}
//# sourceMappingURL=kms.js.map