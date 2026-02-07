"use strict";
/**
 * Dual-Channel Consensus: Bin Selection
 *
 * Deterministically selects frequency bins and phases from challenge
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
exports.selectBinsAndPhases = selectBinsAndPhases;
const crypto = __importStar(require("crypto"));
/**
 * Select bins and phases deterministically from challenge
 *
 * @param seed - HMAC-derived seed from (K, τ, n, c)
 * @param b - Number of bits (bins to select)
 * @param k_min - Minimum bin index
 * @param k_max - Maximum bin index
 * @param delta_k_min - Minimum bin spacing
 * @returns Selected bins and phases
 */
function selectBinsAndPhases(seed, b, k_min, k_max, delta_k_min) {
    const bins = [];
    const phases = [];
    const used = new Set();
    let attempts = 0;
    const maxAttempts = b * 100;
    while (bins.length < b && attempts < maxAttempts) {
        // Generate candidate bin
        const hash = crypto
            .createHash('sha256')
            .update(seed)
            .update(Buffer.from([attempts]))
            .digest();
        const candidate = k_min + (hash.readUInt32BE(0) % (k_max - k_min + 1));
        // Check spacing constraint
        let valid = true;
        for (const existing of bins) {
            if (Math.abs(candidate - existing) < delta_k_min) {
                valid = false;
                break;
            }
            // Avoid harmonic collisions (2x, 3x)
            if (Math.abs(candidate - 2 * existing) < delta_k_min ||
                Math.abs(candidate - 3 * existing) < delta_k_min) {
                valid = false;
                break;
            }
        }
        if (valid && !used.has(candidate)) {
            bins.push(candidate);
            used.add(candidate);
            // Derive phase from same seed
            const phaseHash = crypto
                .createHash('sha256')
                .update(seed)
                .update(Buffer.from('phase'))
                .update(Buffer.from([bins.length]))
                .digest();
            phases.push(2 * Math.PI * (phaseHash.readUInt32BE(0) / 0xffffffff));
        }
        attempts++;
    }
    if (bins.length < b) {
        throw new Error(`Could not select ${b} bins with spacing ${delta_k_min}`);
    }
    return { bins, phases };
}
//# sourceMappingURL=bin-selector.js.map