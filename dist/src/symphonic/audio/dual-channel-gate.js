"use strict";
/**
 * Dual-Channel Consensus Gate
 *
 * Combines cryptographic transcript verification with
 * challenge-bound acoustic watermark verification.
 *
 * Part of SCBE-AETHERMOORE v3.0.0
 * Patent: USPTO #63/961,403
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
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.DualChannelGate = void 0;
const crypto = __importStar(require("crypto"));
const bin_selector_1 = require("./bin-selector");
const matched_filter_1 = require("./matched-filter");
/**
 * Dual-Channel Consensus Gate
 *
 * Combines cryptographic transcript verification with
 * challenge-bound acoustic watermark verification.
 */
class DualChannelGate {
    profile;
    K; // Master key
    N_seen; // Nonce set
    W; // Time window (seconds)
    constructor(profile, K, W = 60) {
        this.profile = profile;
        this.K = K;
        this.N_seen = new Set();
        this.W = W;
    }
    /**
     * Verify request with dual-channel consensus
     */
    verify(request) {
        const { AAD, payload, timestamp, nonce, tag, audio, challenge } = request;
        // --- Crypto Channel ---
        const C = Buffer.concat([
            Buffer.from('scbe.v1'),
            AAD,
            Buffer.from(timestamp.toString()),
            Buffer.from(nonce),
            payload
        ]);
        const expectedTag = crypto.createHmac('sha256', this.K).update(C).digest();
        const V_mac = crypto.timingSafeEqual(tag, expectedTag);
        const tau_recv = Date.now() / 1000;
        const V_time = Math.abs(tau_recv - timestamp) <= this.W;
        const V_nonce = !this.N_seen.has(nonce);
        const S_crypto = V_mac && V_time && V_nonce;
        if (!S_crypto) {
            return 'DENY';
        }
        // --- Audio Channel ---
        // Derive bins/phases from challenge
        const seed = crypto.createHmac('sha256', this.K)
            .update(Buffer.from('bins'))
            .update(Buffer.from(timestamp.toString()))
            .update(Buffer.from(nonce))
            .update(Buffer.from(challenge))
            .digest();
        const { bins, phases } = (0, bin_selector_1.selectBinsAndPhases)(seed, this.profile.b, this.profile.k_min, this.profile.k_max, this.profile.delta_k_min);
        // Verify watermark
        const result = (0, matched_filter_1.verifyWatermark)(audio, challenge, bins, phases, this.profile);
        const S_audio = result.passed;
        // Update nonce set (prevent replay)
        this.N_seen.add(nonce);
        // Decision logic
        if (S_audio) {
            return 'ALLOW';
        }
        else {
            return 'QUARANTINE';
        }
    }
    /**
     * Generate challenge for client
     */
    generateChallenge() {
        const challenge = new Uint8Array(this.profile.b);
        crypto.randomFillSync(challenge);
        // Convert to 0/1
        for (let i = 0; i < challenge.length; i++) {
            challenge[i] = challenge[i] % 2;
        }
        return challenge;
    }
    /**
     * Clear old nonces (TTL cleanup)
     */
    clearOldNonces() {
        // In production, implement TTL-based cleanup
        // For now, simple clear
        this.N_seen.clear();
    }
    /**
     * Get current nonce count
     */
    getNonceCount() {
        return this.N_seen.size;
    }
}
exports.DualChannelGate = DualChannelGate;
//# sourceMappingURL=dual-channel-gate.js.map