/**
 * @file pqc-strategies.ts
 * @module crypto/pqc-strategies
 * @layer Layer 4, Layer 5, Layer 13
 * @component PQC Strategy Profiles + TriStitch + Geometric Key Binding
 * @version 1.0.0
 *
 * Three capabilities in one module:
 *
 * 1. **Strategy Profiles** — named algorithm combos (balanced-v1, paranoid-v1,
 *    iot-v1, conservative-v1) so governance can pick by risk level, not by
 *    algorithm name. Swappable in one place when NIST updates guidance.
 *
 * 2. **TriStitch Combiner** — run 3 KEMs from different PQC families and XOR
 *    all shared secrets. Attacker must break all three math problems at once.
 *    PQC + PQC + PQC, not just classical + PQC.
 *
 * 3. **Geometric Key Binding** — fuse the PQC shared secret with the 21D brain
 *    state via HKDF. The resulting session key is only valid when both crypto
 *    AND geometry agree. "Valid math but wrong intent" gets rejected.
 *
 * Usage:
 *   const strategy = getStrategy('balanced-v1');
 *   const session = await executeStrategy(strategy, brainState);
 *   // session.boundKey is HKDF(pqcSecret, SHA256(21D state))
 */

import { createHash, createHmac } from 'crypto';
import {
  type QuantumSafeKEM,
  type QuantumSafeSignature,
  type QSKeyPair,
  type QSEncapsulation,
  type PQCFamily,
  type NISTLevel,
  getKEM,
  getSignature,
} from './quantum-safe.js';

// ============================================================
// STRATEGY PROFILE DEFINITIONS
// ============================================================

/** A named PQC strategy profile */
export interface PQCStrategy {
  /** Strategy identifier (e.g., 'balanced-v1') */
  name: string;
  /** Human description */
  description: string;
  /** KEM algorithm(s) — single for standard, multiple for TriStitch */
  kemAlgorithms: string[];
  /** Signature algorithm */
  sigAlgorithm: string;
  /** Include classical ECDH XOR component */
  classicalHybrid: boolean;
  /** Minimum NIST security level */
  minNistLevel: NISTLevel;
  /** Recommended use case */
  useCase: string;
  /** PQC families involved (for audit logging) */
  families: PQCFamily[];
}

/** Built-in strategy catalog */
export const STRATEGY_CATALOG: Record<string, PQCStrategy> = {
  'balanced-v1': {
    name: 'balanced-v1',
    description: 'Lattice KEM + lattice sig + classical hybrid. Standard SCBE default.',
    kemAlgorithms: ['ML-KEM-768'],
    sigAlgorithm: 'ML-DSA-65',
    classicalHybrid: true,
    minNistLevel: 3,
    useCase: 'General-purpose governance, API requests, fleet coordination',
    families: ['lattice'],
  },
  'paranoid-v1': {
    name: 'paranoid-v1',
    description: 'TriStitch: 3-family KEM (lattice + code + lattice-L5) + hash-based sig.',
    kemAlgorithms: ['ML-KEM-768', 'Classic-McEliece-348864', 'ML-KEM-1024'],
    sigAlgorithm: 'SLH-DSA-256s',
    classicalHybrid: true,
    minNistLevel: 5,
    useCase: 'High-value governance decisions, key ceremony, sentinel escalation',
    families: ['lattice', 'code-based', 'hash-based'],
  },
  'conservative-v1': {
    name: 'conservative-v1',
    description: 'Lattice KEM + hash-based sig. Two different math problems.',
    kemAlgorithms: ['ML-KEM-768'],
    sigAlgorithm: 'SLH-DSA-128s',
    classicalHybrid: true,
    minNistLevel: 3,
    useCase: 'Long-term audit records, provenance tracking, compliance',
    families: ['lattice', 'hash-based'],
  },
  'iot-v1': {
    name: 'iot-v1',
    description: 'Lightweight lattice KEM + sig. Minimizes bandwidth and compute.',
    kemAlgorithms: ['ML-KEM-512'],
    sigAlgorithm: 'ML-DSA-44',
    classicalHybrid: false,
    minNistLevel: 1,
    useCase: 'Edge devices, IoT agents, bandwidth-constrained environments',
    families: ['lattice'],
  },
};

// User-defined strategies
const customStrategies = new Map<string, PQCStrategy>();

/** Get a strategy by name. Checks custom, then built-in catalog. */
export function getStrategy(name: string): PQCStrategy {
  const custom = customStrategies.get(name);
  if (custom) return custom;
  const builtin = STRATEGY_CATALOG[name];
  if (builtin) return builtin;
  throw new Error(`Unknown PQC strategy: ${name}. Available: ${listStrategyNames().join(', ')}`);
}

/** Register a custom strategy profile */
export function registerStrategy(strategy: PQCStrategy): void {
  customStrategies.set(strategy.name, strategy);
}

/** List all available strategy names */
export function listStrategyNames(): string[] {
  return [...Object.keys(STRATEGY_CATALOG), ...customStrategies.keys()];
}

/** Clear custom strategies (for testing) */
export function clearCustomStrategies(): void {
  customStrategies.clear();
}

// ============================================================
// TRISTITCH COMBINER
// ============================================================

/** Result of a TriStitch multi-KEM combination */
export interface TriStitchResult {
  /** Combined shared secret (XOR of all KEM secrets + optional classical) */
  combinedSecret: Uint8Array;
  /** Per-KEM results for audit trail */
  kemResults: Array<{
    algorithm: string;
    family: PQCFamily;
    ciphertext: Uint8Array;
    secretSize: number;
  }>;
  /** Number of independent PQC families stitched */
  familyCount: number;
  /** Whether classical component was included */
  classicalComponent: boolean;
}

/**
 * TriStitch: run multiple KEMs from different families and XOR-combine
 * all shared secrets. The combined secret is compromised only if ALL
 * constituent families are broken simultaneously.
 *
 * @param kemNames - Array of KEM algorithm names (1-4)
 * @param classicalHybrid - XOR in 32 random bytes (classical ECDH placeholder)
 * @returns Combined secret + per-KEM audit data
 */
export async function triStitch(
  kemNames: string[],
  classicalHybrid: boolean = true
): Promise<{
  result: TriStitchResult;
  keyPairs: QSKeyPair[];
}> {
  if (kemNames.length === 0) {
    throw new Error('TriStitch requires at least one KEM algorithm');
  }
  if (kemNames.length > 4) {
    throw new Error('TriStitch supports at most 4 KEM algorithms');
  }

  const kems: QuantumSafeKEM[] = kemNames.map((n) => getKEM(n));
  const keyPairs: QSKeyPair[] = [];
  const encapsulations: QSEncapsulation[] = [];

  // Step 1: Generate key pairs and encapsulate for each KEM
  for (const kem of kems) {
    const kp = await kem.generateKeyPair();
    keyPairs.push(kp);
    const enc = await kem.encapsulate(kp.publicKey);
    encapsulations.push(enc);
  }

  // Step 2: XOR all shared secrets together
  const combined = new Uint8Array(32);
  for (const enc of encapsulations) {
    for (let i = 0; i < 32; i++) {
      combined[i] ^= enc.sharedSecret[i];
    }
  }

  // Step 3: Optionally XOR in classical randomness
  let classicalUsed = false;
  if (classicalHybrid) {
    const classicalBytes = new Uint8Array(
      createHash('sha256').update(Buffer.from(crypto.getRandomValues(new Uint8Array(32)))).digest()
    );
    for (let i = 0; i < 32; i++) {
      combined[i] ^= classicalBytes[i];
    }
    classicalUsed = true;
  }

  // Step 4: Build audit trail
  const families = new Set<PQCFamily>();
  const kemResults = kems.map((kem, i) => {
    families.add(kem.descriptor.family);
    return {
      algorithm: kem.descriptor.name,
      family: kem.descriptor.family,
      ciphertext: encapsulations[i].ciphertext,
      secretSize: encapsulations[i].sharedSecret.length,
    };
  });

  return {
    result: {
      combinedSecret: combined,
      kemResults,
      familyCount: families.size,
      classicalComponent: classicalUsed,
    },
    keyPairs,
  };
}

// ============================================================
// GEOMETRIC KEY BINDING (21D → Session Key)
// ============================================================

/**
 * HKDF-SHA256: extract-then-expand.
 * Inline to avoid import cycle with hkdf.ts (which imports node:crypto directly).
 */
function hkdf256(ikm: Uint8Array, salt: Uint8Array, info: Uint8Array, len: number): Uint8Array {
  // Extract
  const prk = createHmac('sha256', Buffer.from(salt)).update(Buffer.from(ikm)).digest();
  // Expand
  const n = Math.ceil(len / 32);
  let t = Buffer.alloc(0);
  let okm = Buffer.alloc(0);
  for (let i = 0; i < n; i++) {
    t = createHmac('sha256', prk)
      .update(Buffer.concat([t, Buffer.from(info), Buffer.from([i + 1])]))
      .digest();
    okm = Buffer.concat([okm, t]);
  }
  return new Uint8Array(okm.subarray(0, len));
}

/**
 * Compute the geometric fingerprint of a 21D brain state.
 *
 * SHA-256 over the IEEE 754 double representation of all 21 components,
 * preserving full precision including decimal drift artifacts.
 *
 * @param state - 21D brain state vector
 * @returns 32-byte fingerprint
 */
export function geometricFingerprint(state: number[]): Uint8Array {
  const buf = Buffer.alloc(state.length * 8);
  for (let i = 0; i < state.length; i++) {
    buf.writeDoubleBE(state[i], i * 8);
  }
  return new Uint8Array(createHash('sha256').update(buf).digest());
}

/** Geometric binding configuration */
export interface GeoBindConfig {
  /** Domain separation label (default: 'scbe:geo-bind:v1') */
  domain?: string;
  /** Include Poincaré norm in info string (default: true) */
  includeNorm?: boolean;
  /** Include phase index in info string (default: true) */
  includePhase?: boolean;
}

/** Result of geometric key binding */
export interface GeoBoundKey {
  /** The bound session key: HKDF(pqcSecret, geoFingerprint, domainInfo) */
  boundKey: Uint8Array;
  /** Geometric fingerprint used as salt */
  geoFingerprint: Uint8Array;
  /** SHA-256 hex of the bound key (for audit logs) */
  keyId: string;
  /** Poincaré norm of the 21D state at binding time */
  stateNorm: number;
}

/**
 * Bind a PQC shared secret to a 21D brain state.
 *
 * boundKey = HKDF-SHA256(
 *   ikm  = pqcSharedSecret,
 *   salt = SHA256(21D state as IEEE 754 doubles),
 *   info = "scbe:geo-bind:v1|norm=X.XXX|phase=N"
 * )
 *
 * The resulting session key is valid only when:
 * 1. The PQC crypto decrypts correctly, AND
 * 2. The geometric state matches what was bound at key creation.
 *
 * "Valid math but wrong intent" → wrong geometric fingerprint → wrong key.
 *
 * @param sharedSecret - PQC shared secret (32 bytes from KEM/TriStitch)
 * @param brainState - 21D state vector [SCBE(6) + nav(6) + cog(3) + sem(3) + swarm(3)]
 * @param config - Optional binding configuration
 * @returns Bound session key + metadata
 */
export function bindKeyToGeometry(
  sharedSecret: Uint8Array,
  brainState: number[],
  config: GeoBindConfig = {}
): GeoBoundKey {
  const domain = config.domain ?? 'scbe:geo-bind:v1';
  const includeNorm = config.includeNorm ?? true;
  const includePhase = config.includePhase ?? true;

  // Step 1: Compute geometric fingerprint (salt)
  const geoFingerprint = geometricFingerprint(brainState);

  // Step 2: Compute Poincaré norm of the state
  let normSq = 0;
  for (const x of brainState) normSq += x * x;
  const stateNorm = Math.sqrt(normSq);

  // Step 3: Build domain-separated info string
  let info = domain;
  if (includeNorm) {
    info += `|norm=${stateNorm.toFixed(6)}`;
  }
  if (includePhase) {
    // Phase index: which Sacred Tongue has maximum weight (first 6 components)
    let maxIdx = 0;
    let maxVal = -Infinity;
    const phaseLen = Math.min(6, brainState.length);
    for (let i = 0; i < phaseLen; i++) {
      if (Math.abs(brainState[i]) > maxVal) {
        maxVal = Math.abs(brainState[i]);
        maxIdx = i;
      }
    }
    info += `|phase=${maxIdx}`;
  }

  const infoBytes = new TextEncoder().encode(info);

  // Step 4: HKDF derive the bound key
  const boundKey = hkdf256(sharedSecret, geoFingerprint, infoBytes, 32);

  // Step 5: Compute key ID for audit trail
  const keyId = createHash('sha256').update(Buffer.from(boundKey)).digest('hex').slice(0, 16);

  return { boundKey, geoFingerprint, keyId, stateNorm };
}

/**
 * Verify that a key binding matches an expected geometric state.
 *
 * Re-derives the bound key from the same inputs and compares.
 * Uses constant-time comparison to prevent timing attacks.
 *
 * @param boundKey - Previously derived bound key
 * @param sharedSecret - Original PQC shared secret
 * @param brainState - Current 21D state to verify against
 * @param config - Same config used during binding
 * @returns true if geometric state matches
 */
export function verifyGeometricBinding(
  boundKey: Uint8Array,
  sharedSecret: Uint8Array,
  brainState: number[],
  config: GeoBindConfig = {}
): boolean {
  const rederived = bindKeyToGeometry(sharedSecret, brainState, config);

  // Constant-time comparison
  if (boundKey.length !== rederived.boundKey.length) return false;
  let diff = 0;
  for (let i = 0; i < boundKey.length; i++) {
    diff |= boundKey[i] ^ rederived.boundKey[i];
  }
  return diff === 0;
}

// ============================================================
// STRATEGY EXECUTOR
// ============================================================

/** Full result of executing a PQC strategy with geometric binding */
export interface StrategyExecutionResult {
  /** Strategy that was executed */
  strategyName: string;
  /** Geometrically-bound session key */
  boundKey: GeoBoundKey;
  /** TriStitch result (if multi-KEM) or single KEM result */
  triStitch: TriStitchResult;
  /** Signature key pair for signing governance decisions */
  sigKeyPair: QSKeyPair;
  /** Signature algorithm instance */
  sigAlgorithm: string;
  /** Families involved (for Layer 13 audit) */
  families: PQCFamily[];
  /** Timestamp of execution */
  timestamp: number;
}

/**
 * Execute a complete PQC strategy with geometric binding.
 *
 * This is the top-level API for governance:
 *   1. Resolve strategy → algorithm combos
 *   2. TriStitch KEMs → combined shared secret
 *   3. Bind to 21D geometric state → session key
 *   4. Generate signature key pair for decision signing
 *
 * @param strategyName - Strategy profile name (e.g., 'balanced-v1')
 * @param brainState - Current 21D brain state for geometric binding
 * @param geoConfig - Optional geometric binding config
 * @returns Complete execution result with bound key + signing capability
 */
export async function executeStrategy(
  strategyName: string,
  brainState: number[],
  geoConfig?: GeoBindConfig
): Promise<StrategyExecutionResult> {
  const strategy = getStrategy(strategyName);

  // Step 1: TriStitch KEMs
  const { result: triStitchResult } = await triStitch(
    strategy.kemAlgorithms,
    strategy.classicalHybrid
  );

  // Step 2: Geometric binding
  const boundKey = bindKeyToGeometry(triStitchResult.combinedSecret, brainState, geoConfig);

  // Step 3: Signature key pair
  const sig = getSignature(strategy.sigAlgorithm);
  const sigKeyPair = await sig.generateKeyPair();

  return {
    strategyName: strategy.name,
    boundKey,
    triStitch: triStitchResult,
    sigKeyPair,
    sigAlgorithm: strategy.sigAlgorithm,
    families: strategy.families,
    timestamp: Date.now(),
  };
}

/**
 * Sign a governance decision using a strategy execution result.
 *
 * @param message - The governance decision payload
 * @param execution - Result from executeStrategy()
 * @returns Signature bytes
 */
export async function signWithStrategy(
  message: Uint8Array,
  execution: StrategyExecutionResult
): Promise<Uint8Array> {
  const sig = getSignature(execution.sigAlgorithm);
  return sig.sign(message, execution.sigKeyPair.secretKey);
}
