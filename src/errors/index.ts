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
export class SCBEError extends Error {
  public readonly code: string;
  public readonly context?: Record<string, unknown>;
  public readonly timestamp: number;

  constructor(message: string, code: string, context?: Record<string, unknown>) {
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
  toJSON(): Record<string, unknown> {
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

/**
 * Cryptographic operation errors
 */
export class CryptoError extends SCBEError {
  constructor(message: string, context?: Record<string, unknown>) {
    super(message, 'CRYPTO_ERROR', context);
    this.name = 'CryptoError';
  }
}

/**
 * Envelope encryption/decryption errors
 */
export class EnvelopeError extends SCBEError {
  constructor(message: string, context?: Record<string, unknown>) {
    super(message, 'ENVELOPE_ERROR', context);
    this.name = 'EnvelopeError';
  }
}

/**
 * Input validation errors
 */
export class ValidationError extends SCBEError {
  constructor(message: string, context?: Record<string, unknown>) {
    super(message, 'VALIDATION_ERROR', context);
    this.name = 'ValidationError';
  }
}

/**
 * Harmonic layer processing errors
 */
export class HarmonicLayerError extends SCBEError {
  public readonly layer: number;

  constructor(layer: number, message: string, context?: Record<string, unknown>) {
    super(message, `HARMONIC_L${layer}_ERROR`, { layer, ...context });
    this.name = 'HarmonicLayerError';
    this.layer = layer;
  }
}

/**
 * Replay attack detection errors
 */
export class ReplayError extends SCBEError {
  constructor(message: string, context?: Record<string, unknown>) {
    super(message, 'REPLAY_ERROR', context);
    this.name = 'ReplayError';
  }
}

/**
 * Network/routing errors
 */
export class NetworkError extends SCBEError {
  constructor(message: string, context?: Record<string, unknown>) {
    super(message, 'NETWORK_ERROR', context);
    this.name = 'NetworkError';
  }
}

/**
 * Authentication/authorization errors
 */
export class AuthError extends SCBEError {
  constructor(message: string, context?: Record<string, unknown>) {
    super(message, 'AUTH_ERROR', context);
    this.name = 'AuthError';
  }
}

/**
 * Configuration errors
 */
export class ConfigError extends SCBEError {
  constructor(message: string, context?: Record<string, unknown>) {
    super(message, 'CONFIG_ERROR', context);
    this.name = 'ConfigError';
  }
}

/**
 * Type guard to check if an error is an SCBEError
 */
export function isSCBEError(error: unknown): error is SCBEError {
  return error instanceof SCBEError;
}

/**
 * Wrap unknown errors into SCBEError
 */
export function wrapError(error: unknown, defaultCode = 'UNKNOWN_ERROR'): SCBEError {
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
