/**
 * @file errors/index.ts
 * @module errors
 * @description Custom error hierarchy for SCBE-AETHERMOORE
 * @version 3.0.0
 */
/**
 * Base error class for all SCBE errors
 * Provides structured error context for debugging and monitoring
 */
export declare class SCBEError extends Error {
    readonly code: string;
    readonly context?: Record<string, unknown>;
    readonly timestamp: number;
    constructor(message: string, code: string, context?: Record<string, unknown>);
    /**
     * Convert error to JSON for logging/serialization
     */
    toJSON(): Record<string, unknown>;
}
/**
 * Cryptographic operation errors
 */
export declare class CryptoError extends SCBEError {
    constructor(message: string, context?: Record<string, unknown>);
}
/**
 * Envelope encryption/decryption errors
 */
export declare class EnvelopeError extends SCBEError {
    constructor(message: string, context?: Record<string, unknown>);
}
/**
 * Input validation errors
 */
export declare class ValidationError extends SCBEError {
    constructor(message: string, context?: Record<string, unknown>);
}
/**
 * Harmonic layer processing errors
 */
export declare class HarmonicLayerError extends SCBEError {
    readonly layer: number;
    constructor(layer: number, message: string, context?: Record<string, unknown>);
}
/**
 * Replay attack detection errors
 */
export declare class ReplayError extends SCBEError {
    constructor(message: string, context?: Record<string, unknown>);
}
/**
 * Network/routing errors
 */
export declare class NetworkError extends SCBEError {
    constructor(message: string, context?: Record<string, unknown>);
}
/**
 * Authentication/authorization errors
 */
export declare class AuthError extends SCBEError {
    constructor(message: string, context?: Record<string, unknown>);
}
/**
 * Configuration errors
 */
export declare class ConfigError extends SCBEError {
    constructor(message: string, context?: Record<string, unknown>);
}
/**
 * Type guard to check if an error is an SCBEError
 */
export declare function isSCBEError(error: unknown): error is SCBEError;
/**
 * Wrap unknown errors into SCBEError
 */
export declare function wrapError(error: unknown, defaultCode?: string): SCBEError;
//# sourceMappingURL=index.d.ts.map