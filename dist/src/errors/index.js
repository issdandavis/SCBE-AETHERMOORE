"use strict";
/**
 * @file errors/index.ts
 * @module errors
 * @description Custom error hierarchy for SCBE-AETHERMOORE
 * @version 3.0.0
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ConfigError = exports.AuthError = exports.NetworkError = exports.ReplayError = exports.HarmonicLayerError = exports.ValidationError = exports.EnvelopeError = exports.CryptoError = exports.SCBEError = void 0;
exports.isSCBEError = isSCBEError;
exports.wrapError = wrapError;
/**
 * Base error class for all SCBE errors
 * Provides structured error context for debugging and monitoring
 */
class SCBEError extends Error {
    code;
    context;
    timestamp;
    constructor(message, code, context) {
        super(message);
        this.name = 'SCBEError';
        this.code = code;
        this.context = context;
        this.timestamp = Date.now();
        // Maintains proper stack trace for where error was thrown
        if (Error.captureStackTrace) {
            Error.captureStackTrace(this, this.constructor);
        }
    }
    /**
     * Convert error to JSON for logging/serialization
     */
    toJSON() {
        return {
            name: this.name,
            code: this.code,
            message: this.message,
            context: this.context,
            timestamp: this.timestamp,
            stack: this.stack,
        };
    }
}
exports.SCBEError = SCBEError;
/**
 * Cryptographic operation errors
 */
class CryptoError extends SCBEError {
    constructor(message, context) {
        super(message, 'CRYPTO_ERROR', context);
        this.name = 'CryptoError';
    }
}
exports.CryptoError = CryptoError;
/**
 * Envelope encryption/decryption errors
 */
class EnvelopeError extends SCBEError {
    constructor(message, context) {
        super(message, 'ENVELOPE_ERROR', context);
        this.name = 'EnvelopeError';
    }
}
exports.EnvelopeError = EnvelopeError;
/**
 * Input validation errors
 */
class ValidationError extends SCBEError {
    constructor(message, context) {
        super(message, 'VALIDATION_ERROR', context);
        this.name = 'ValidationError';
    }
}
exports.ValidationError = ValidationError;
/**
 * Harmonic layer processing errors
 */
class HarmonicLayerError extends SCBEError {
    layer;
    constructor(layer, message, context) {
        super(message, `HARMONIC_L${layer}_ERROR`, { layer, ...context });
        this.name = 'HarmonicLayerError';
        this.layer = layer;
    }
}
exports.HarmonicLayerError = HarmonicLayerError;
/**
 * Replay attack detection errors
 */
class ReplayError extends SCBEError {
    constructor(message, context) {
        super(message, 'REPLAY_ERROR', context);
        this.name = 'ReplayError';
    }
}
exports.ReplayError = ReplayError;
/**
 * Network/routing errors
 */
class NetworkError extends SCBEError {
    constructor(message, context) {
        super(message, 'NETWORK_ERROR', context);
        this.name = 'NetworkError';
    }
}
exports.NetworkError = NetworkError;
/**
 * Authentication/authorization errors
 */
class AuthError extends SCBEError {
    constructor(message, context) {
        super(message, 'AUTH_ERROR', context);
        this.name = 'AuthError';
    }
}
exports.AuthError = AuthError;
/**
 * Configuration errors
 */
class ConfigError extends SCBEError {
    constructor(message, context) {
        super(message, 'CONFIG_ERROR', context);
        this.name = 'ConfigError';
    }
}
exports.ConfigError = ConfigError;
/**
 * Type guard to check if an error is an SCBEError
 */
function isSCBEError(error) {
    return error instanceof SCBEError;
}
/**
 * Wrap unknown errors into SCBEError
 */
function wrapError(error, defaultCode = 'UNKNOWN_ERROR') {
    if (error instanceof SCBEError) {
        return error;
    }
    if (error instanceof Error) {
        return new SCBEError(error.message, defaultCode, {
            originalName: error.name,
            originalStack: error.stack,
        });
    }
    return new SCBEError(String(error), defaultCode);
}
//# sourceMappingURL=index.js.map