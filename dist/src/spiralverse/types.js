"use strict";
/**
 * RWP v2.1 Multi-Signature Envelopes - Type Definitions
 * =====================================================
 *
 * Real World Protocol for secure AI-to-AI communication using
 * domain-separated authentication via Sacred Tongues.
 *
 * @module spiralverse/types
 * @version 2.1.0
 * @since 2026-01-18
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.PolicyError = exports.ReplayError = exports.SignatureError = exports.RWPError = void 0;
/**
 * Error types
 */
class RWPError extends Error {
    constructor(message) {
        super(message);
        this.name = 'RWPError';
    }
}
exports.RWPError = RWPError;
class SignatureError extends RWPError {
    constructor(message) {
        super(message);
        this.name = 'SignatureError';
    }
}
exports.SignatureError = SignatureError;
class ReplayError extends RWPError {
    constructor(message) {
        super(message);
        this.name = 'ReplayError';
    }
}
exports.ReplayError = ReplayError;
class PolicyError extends RWPError {
    constructor(message) {
        super(message);
        this.name = 'PolicyError';
    }
}
exports.PolicyError = PolicyError;
//# sourceMappingURL=types.js.map