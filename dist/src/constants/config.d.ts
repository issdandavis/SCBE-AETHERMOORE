/**
 * @file constants/config.ts
 * @module constants
 * @description Centralized configuration constants for SCBE-AETHERMOORE
 * @version 3.0.0
 */
/**
 * Harmonic pipeline configuration
 */
export declare const HARMONIC_CONFIG: {
    /** Hyperbolic scaling radius (R) for Poincare ball operations */
    readonly SCALING_RADIUS: 1.5;
    /** Maximum radius within Poincare ball boundary */
    readonly POINCARE_RADIUS: 0.99;
    /** Number of layers in the harmonic pipeline */
    readonly LAYER_COUNT: 14;
    /** Default beta value for exponential cost functions */
    readonly BETA_BASE: 1;
    /** Default omega value for phase oscillation */
    readonly OMEGA_BASE: 1;
};
/**
 * Risk assessment thresholds
 */
export declare const RISK_THRESHOLDS: {
    /** Below this value: low risk (ALLOW) */
    readonly LOW: 0.3;
    /** Above this value: high risk (DENY) */
    readonly HIGH: 0.7;
    /** Default Langues metric thresholds [low, high] */
    readonly LANGUES_DEFAULT: [number, number];
};
/**
 * Cryptographic configuration
 */
export declare const CRYPTO_CONFIG: {
    /** AES-256-GCM key length in bytes */
    readonly KEY_LENGTH: 32;
    /** GCM nonce/IV length in bytes */
    readonly NONCE_LENGTH: 12;
    /** Authentication tag length in bytes */
    readonly TAG_LENGTH: 16;
    /** HKDF salt length in bytes */
    readonly SALT_LENGTH: 32;
    /** Replay nonce length in bytes */
    readonly REPLAY_NONCE_LENGTH: 16;
};
/**
 * Envelope configuration
 */
export declare const ENVELOPE_CONFIG: {
    /** Current envelope version */
    readonly VERSION: "scbe-v1";
    /** Default TTL in milliseconds (10 minutes) */
    readonly DEFAULT_TTL_MS: 600000;
    /** Default clock skew allowance in milliseconds (2 minutes) */
    readonly DEFAULT_SKEW_MS: 120000;
    /** Replay guard default TTL in seconds */
    readonly REPLAY_TTL_SECONDS: 600;
    /** Replay guard bloom filter bits */
    readonly REPLAY_BLOOM_BITS: 2048;
    /** Replay guard bloom filter hash count */
    readonly REPLAY_BLOOM_HASHES: 4;
};
/**
 * Network/routing configuration
 */
export declare const NETWORK_CONFIG: {
    /** Default acknowledgment timeout in milliseconds */
    readonly ACK_TIMEOUT_MS: 30000;
    /** Maximum retry attempts for network operations */
    readonly MAX_RETRIES: 3;
    /** Minimum disjoint paths for combat mode */
    readonly MIN_DISJOINT_PATHS: 2;
    /** Health tracking window size */
    readonly HEALTH_TRACKING_WINDOW: 100;
    /** Minimum success rate for healthy paths */
    readonly MIN_SUCCESS_RATE: 0.7;
    /** Speed of light delay per AU in milliseconds */
    readonly LIGHT_DELAY_MS_PER_AU: 500000;
};
/**
 * Fleet/orchestration configuration
 */
export declare const FLEET_CONFIG: {
    /** Maximum concurrent agents */
    readonly MAX_AGENTS: 100;
    /** Task timeout in milliseconds */
    readonly TASK_TIMEOUT_MS: 300000;
    /** Heartbeat interval in milliseconds */
    readonly HEARTBEAT_INTERVAL_MS: 10000;
};
/**
 * Test configuration
 */
export declare const TEST_CONFIG: {
    /** Default test timeout in milliseconds */
    readonly TIMEOUT_MS: 30000;
    /** Property test iteration count */
    readonly PROPERTY_TEST_ITERATIONS: 100;
    /** Coverage thresholds */
    readonly COVERAGE: {
        readonly LINES: 80;
        readonly FUNCTIONS: 80;
        readonly BRANCHES: 70;
        readonly STATEMENTS: 80;
    };
};
/**
 * RWP (Real World Protocol) configuration
 */
export declare const RWP_CONFIG: {
    /** Current RWP version */
    readonly VERSION: "2.1";
    /** Default replay window in milliseconds (5 minutes) */
    readonly REPLAY_WINDOW_MS: 300000;
    /** Default clock skew tolerance in milliseconds (1 minute) */
    readonly CLOCK_SKEW_MS: 60000;
    /** Nonce cache max size */
    readonly NONCE_CACHE_SIZE: 10000;
    /** Nonce expiry time in milliseconds (5 minutes) */
    readonly NONCE_EXPIRY_MS: 300000;
};
/**
 * Golden ratio constant used in Langues metric
 */
export declare const PHI: number;
/**
 * Dimension flux state thresholds
 */
export declare const FLUX_THRESHOLDS: {
    /** Polly state threshold */
    readonly POLLY: 0.9;
    /** Quasi state threshold */
    readonly QUASI: 0.5;
    /** Demi state threshold */
    readonly DEMI: 0.1;
};
//# sourceMappingURL=config.d.ts.map