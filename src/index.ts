/**
 * SCBE-AETHERMOORE v3.0
 * Hyperbolic Geometry-Based Security with 14-Layer Architecture
 *
 * Patent Pending: USPTO #63/961,403
 * Author: Issac Daniel Davis
 *
 * @packageDocumentation
 */

// Namespace exports for convenient access (scbe.symphonic, scbe.crypto)
import * as symphonic from './symphonic/index.js';
import * as crypto from './crypto/index.js';
export { symphonic, crypto };

// Core Crypto Exports (also available at top level)
export * from './crypto/envelope.js';
export * from './crypto/hkdf.js';
export * from './crypto/jcs.js';
export * from './crypto/kms.js';
export * from './crypto/nonceManager.js';
export * from './crypto/replayGuard.js';
export * from './crypto/bloom.js';

// Metrics Exports
export * from './metrics/telemetry.js';

// Rollout Exports
export * from './rollout/canary.js';
export * from './rollout/circuitBreaker.js';

// Self-Healing Exports
export * from './selfHealing/coordinator.js';
export * from './selfHealing/deepHealing.js';
export * from './selfHealing/quickFixBot.js';

// Version and Metadata
export const VERSION = '3.0.0';
export const PATENT_NUMBER = 'USPTO #63/961,403';
export const ARCHITECTURE_LAYERS = 14;

/**
 * SCBE-AETHERMOORE Configuration
 */
export interface SCBEConfig {
  /** Enable 14-layer architecture */
  enableFullStack?: boolean;
  /** Harmonic scaling factor (default: 1.5) */
  harmonicScaling?: number;
  /** Poincaré ball radius constraint */
  poincareRadius?: number;
  /** Enable anti-fragile mode */
  antifragile?: boolean;
}

/**
 * Default SCBE configuration
 */
export const DEFAULT_CONFIG: SCBEConfig = {
  enableFullStack: true,
  harmonicScaling: 1.5,
  poincareRadius: 0.99,
  antifragile: true,
};
