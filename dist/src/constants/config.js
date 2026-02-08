"use strict";
/**
 * @file constants/config.ts
 * @module constants
 * @description Centralized configuration constants for SCBE-AETHERMOORE
 * @version 3.0.0
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.FLUX_THRESHOLDS = exports.PHI = exports.RWP_CONFIG = exports.TEST_CONFIG = exports.FLEET_CONFIG = exports.NETWORK_CONFIG = exports.ENVELOPE_CONFIG = exports.CRYPTO_CONFIG = exports.RISK_THRESHOLDS = exports.HARMONIC_CONFIG = void 0;
/**
 * Harmonic pipeline configuration
 */
exports.HARMONIC_CONFIG = {
    /** Hyperbolic scaling radius (R) for Poincare ball operations */
    SCALING_RADIUS: 1.5,
    /** Maximum radius within Poincare ball boundary */
    POINCARE_RADIUS: 0.99,
    /** Number of layers in the harmonic pipeline */
    LAYER_COUNT: 14,
    /** Default beta value for exponential cost functions */
    BETA_BASE: 1.0,
    /** Default omega value for phase oscillation */
    OMEGA_BASE: 1.0,
};
/**
 * Risk assessment thresholds
 */
exports.RISK_THRESHOLDS = {
    /** Below this value: low risk (ALLOW) */
    LOW: 0.3,
    /** Above this value: high risk (DENY) */
    HIGH: 0.7,
    /** Default Langues metric thresholds [low, high] */
    LANGUES_DEFAULT: [1.0, 10.0],
};
/**
 * Cryptographic configuration
 */
exports.CRYPTO_CONFIG = {
    /** AES-256-GCM key length in bytes */
    KEY_LENGTH: 32,
    /** GCM nonce/IV length in bytes */
    NONCE_LENGTH: 12,
    /** Authentication tag length in bytes */
    TAG_LENGTH: 16,
    /** HKDF salt length in bytes */
    SALT_LENGTH: 32,
    /** Replay nonce length in bytes */
    REPLAY_NONCE_LENGTH: 16,
};
/**
 * Envelope configuration
 */
exports.ENVELOPE_CONFIG = {
    /** Current envelope version */
    VERSION: 'scbe-v1',
    /** Default TTL in milliseconds (10 minutes) */
    DEFAULT_TTL_MS: 600_000,
    /** Default clock skew allowance in milliseconds (2 minutes) */
    DEFAULT_SKEW_MS: 120_000,
    /** Replay guard default TTL in seconds */
    REPLAY_TTL_SECONDS: 600,
    /** Replay guard bloom filter bits */
    REPLAY_BLOOM_BITS: 2048,
    /** Replay guard bloom filter hash count */
    REPLAY_BLOOM_HASHES: 4,
};
/**
 * Network/routing configuration
 */
exports.NETWORK_CONFIG = {
    /** Default acknowledgment timeout in milliseconds */
    ACK_TIMEOUT_MS: 30_000,
    /** Maximum retry attempts for network operations */
    MAX_RETRIES: 3,
    /** Minimum disjoint paths for combat mode */
    MIN_DISJOINT_PATHS: 2,
    /** Health tracking window size */
    HEALTH_TRACKING_WINDOW: 100,
    /** Minimum success rate for healthy paths */
    MIN_SUCCESS_RATE: 0.7,
    /** Speed of light delay per AU in milliseconds */
    LIGHT_DELAY_MS_PER_AU: 500_000,
};
/**
 * Fleet/orchestration configuration
 */
exports.FLEET_CONFIG = {
    /** Maximum concurrent agents */
    MAX_AGENTS: 100,
    /** Task timeout in milliseconds */
    TASK_TIMEOUT_MS: 300_000,
    /** Heartbeat interval in milliseconds */
    HEARTBEAT_INTERVAL_MS: 10_000,
};
/**
 * Test configuration
 */
exports.TEST_CONFIG = {
    /** Default test timeout in milliseconds */
    TIMEOUT_MS: 30_000,
    /** Property test iteration count */
    PROPERTY_TEST_ITERATIONS: 100,
    /** Coverage thresholds */
    COVERAGE: {
        LINES: 80,
        FUNCTIONS: 80,
        BRANCHES: 70,
        STATEMENTS: 80,
    },
};
/**
 * RWP (Real World Protocol) configuration
 */
exports.RWP_CONFIG = {
    /** Current RWP version */
    VERSION: '2.1',
    /** Default replay window in milliseconds (5 minutes) */
    REPLAY_WINDOW_MS: 300_000,
    /** Default clock skew tolerance in milliseconds (1 minute) */
    CLOCK_SKEW_MS: 60_000,
    /** Nonce cache max size */
    NONCE_CACHE_SIZE: 10_000,
    /** Nonce expiry time in milliseconds (5 minutes) */
    NONCE_EXPIRY_MS: 300_000,
};
/**
 * Golden ratio constant used in Langues metric
 */
exports.PHI = (1 + Math.sqrt(5)) / 2;
/**
 * Dimension flux state thresholds
 */
exports.FLUX_THRESHOLDS = {
    /** Polly state threshold */
    POLLY: 0.9,
    /** Quasi state threshold */
    QUASI: 0.5,
    /** Demi state threshold */
    DEMI: 0.1,
};
//# sourceMappingURL=config.js.map