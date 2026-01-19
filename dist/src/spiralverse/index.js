"use strict";
/**
 * Spiralverse - RWP v2.1 Multi-Signature Envelopes
 * =================================================
 *
 * Real World Protocol for secure AI-to-AI communication using
 * domain-separated authentication via Sacred Tongues.
 *
 * @module spiralverse
 * @version 2.1.0
 * @since 2026-01-18
 *
 * @example
 * ```typescript
 * import { signRoundtable, verifyRoundtable } from '@scbe/aethermoore/spiralverse';
 *
 * // Create keyring
 * const keyring = {
 *   ko: Buffer.from('...'),  // Kor'aelin (Control)
 *   av: Buffer.from('...'),  // Avali (I/O)
 *   ru: Buffer.from('...'),  // Runethic (Policy)
 *   ca: Buffer.from('...'),  // Cassisivadan (Compute)
 *   um: Buffer.from('...'),  // Umbroth (Security)
 *   dr: Buffer.from('...'),  // Draumric (Structure)
 * };
 *
 * // Sign envelope
 * const envelope = signRoundtable(
 *   { action: 'deploy', target: 'production' },
 *   'ko',                    // Primary tongue
 *   'agent-123',             // AAD
 *   keyring,
 *   ['ko', 'ru', 'um']       // Sign with Control, Policy, Security
 * );
 *
 * // Verify envelope
 * const result = verifyRoundtable(envelope, keyring, {
 *   policy: 'critical',      // Requires RU + UM + DR
 * });
 *
 * if (result.valid) {
 *   console.log('Valid tongues:', result.validTongues);
 *   console.log('Payload:', result.payload);
 * }
 * ```
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.SignatureError = exports.ReplayError = exports.RWPError = exports.PolicyError = exports.suggestPolicy = exports.getRequiredTongues = exports.getPolicyDescription = exports.enforcePolicy = exports.checkPolicy = exports.POLICY_MATRIX = exports.verifyRoundtable = exports.signRoundtable = exports.getNonceCacheSize = exports.destroyNonceCache = exports.clearNonceCache = void 0;
// Core RWP functions
var rwp_1 = require("./rwp");
Object.defineProperty(exports, "clearNonceCache", { enumerable: true, get: function () { return rwp_1.clearNonceCache; } });
Object.defineProperty(exports, "destroyNonceCache", { enumerable: true, get: function () { return rwp_1.destroyNonceCache; } });
Object.defineProperty(exports, "getNonceCacheSize", { enumerable: true, get: function () { return rwp_1.getNonceCacheSize; } });
Object.defineProperty(exports, "signRoundtable", { enumerable: true, get: function () { return rwp_1.signRoundtable; } });
Object.defineProperty(exports, "verifyRoundtable", { enumerable: true, get: function () { return rwp_1.verifyRoundtable; } });
// Policy enforcement
var policy_1 = require("./policy");
Object.defineProperty(exports, "POLICY_MATRIX", { enumerable: true, get: function () { return policy_1.POLICY_MATRIX; } });
Object.defineProperty(exports, "checkPolicy", { enumerable: true, get: function () { return policy_1.checkPolicy; } });
Object.defineProperty(exports, "enforcePolicy", { enumerable: true, get: function () { return policy_1.enforcePolicy; } });
Object.defineProperty(exports, "getPolicyDescription", { enumerable: true, get: function () { return policy_1.getPolicyDescription; } });
Object.defineProperty(exports, "getRequiredTongues", { enumerable: true, get: function () { return policy_1.getRequiredTongues; } });
Object.defineProperty(exports, "suggestPolicy", { enumerable: true, get: function () { return policy_1.suggestPolicy; } });
// Errors
var types_1 = require("./types");
Object.defineProperty(exports, "PolicyError", { enumerable: true, get: function () { return types_1.PolicyError; } });
Object.defineProperty(exports, "RWPError", { enumerable: true, get: function () { return types_1.RWPError; } });
Object.defineProperty(exports, "ReplayError", { enumerable: true, get: function () { return types_1.ReplayError; } });
Object.defineProperty(exports, "SignatureError", { enumerable: true, get: function () { return types_1.SignatureError; } });
//# sourceMappingURL=index.js.map