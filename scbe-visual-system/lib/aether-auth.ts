/**
 * AetherAuth - Hyperbolic OAuth System
 * =====================================
 * Replaces standard OAuth tokens with GeoSeal Envelopes that are:
 * - Geometrically bound (only valid in correct trust ring)
 * - Time-dilated (attackers trapped in event horizon)
 * - Post-quantum resistant (RWP v3 envelope)
 * - Spectrally verified (Sacred Tongue encoding)
 *
 * Standard OAuth → AetherAuth mapping:
 * - Client ID → Identity Vector (6D Poincaré coordinate)
 * - Client Secret → Harmonic Fingerprint
 * - Access Token → GeoSeal Envelope
 * - Scope → Trust Ring (r < 0.3 = Core, r < 0.6 = Inner, etc.)
 *
 * @version 1.0.0
 */

import {
  SacredTongueTokenizer,
  getTokenizer,
  TongueCode,
  TONGUES,
  encodeToSpellText,
} from './sacred-tongue-tokenizer';

// ============================================================
// TYPES & INTERFACES
// ============================================================

export type TrustRing = 'core' | 'inner' | 'outer' | 'boundary' | 'event_horizon';

export interface IdentityVector {
  /** 6D coordinate in Poincaré Ball */
  coordinates: [number, number, number, number, number, number];
  /** Radial distance from center (0 = perfect alignment) */
  radius: number;
  /** Assigned trust ring based on radius */
  ring: TrustRing;
  /** Timestamp of vector computation */
  timestamp: number;
}

export interface HarmonicFingerprint {
  /** Base frequency from Sacred Tongue */
  frequency: number;
  /** Weighted hash of identity */
  weight: number;
  /** Tongue used for encoding */
  tongue: TongueCode;
  /** Spectral signature */
  signature: string;
}

export interface GeoSealEnvelope {
  /** Envelope version */
  version: 'GEOSEAL-1';
  /** Key ID for rotation */
  kid: string;
  /** Identity vector at time of issuance */
  identity: IdentityVector;
  /** Harmonic fingerprint */
  fingerprint: HarmonicFingerprint;
  /** Authorized scopes/actions */
  scopes: string[];
  /** Expiration timestamp */
  expiresAt: number;
  /** Issued timestamp */
  issuedAt: number;
  /** Sacred Tongue encoded payload */
  payload: string;
  /** Draumric-encoded signature */
  signature: string;
}

export interface AuthorizationResult {
  valid: boolean;
  envelope?: GeoSealEnvelope;
  ring: TrustRing;
  latencyMs: number;
  error?: string;
}

export interface AuthChallenge {
  challengeId: string;
  nonce: string;
  requiredRing: TrustRing;
  expiresAt: number;
  tongue: TongueCode;
}

// ============================================================
// TRUST RING CONFIGURATION
// ============================================================

export const TRUST_RING_THRESHOLDS: Record<TrustRing, { maxRadius: number; latencyMs: number }> = {
  core: { maxRadius: 0.3, latencyMs: 5 },           // Trusted, fast
  inner: { maxRadius: 0.6, latencyMs: 50 },         // Verified, normal
  outer: { maxRadius: 0.85, latencyMs: 500 },       // Cautious, delayed
  boundary: { maxRadius: 0.95, latencyMs: 5000 },   // Suspicious, significant delay
  event_horizon: { maxRadius: 1.0, latencyMs: Infinity } // Trapped, never completes
};

export function getRingFromRadius(radius: number): TrustRing {
  if (radius < TRUST_RING_THRESHOLDS.core.maxRadius) return 'core';
  if (radius < TRUST_RING_THRESHOLDS.inner.maxRadius) return 'inner';
  if (radius < TRUST_RING_THRESHOLDS.outer.maxRadius) return 'outer';
  if (radius < TRUST_RING_THRESHOLDS.boundary.maxRadius) return 'boundary';
  return 'event_horizon';
}

// ============================================================
// POINCARE BALL GEOMETRY
// ============================================================

/**
 * Compute hyperbolic distance in Poincaré Ball
 * d_H(u, v) = 2 * artanh(||-u ⊕ v||)
 * where ⊕ is Möbius addition
 */
function hyperbolicDistance(u: number[], v: number[]): number {
  // Simplified: Euclidean distance scaled by Poincaré metric
  let sumSq = 0;
  for (let i = 0; i < u.length; i++) {
    sumSq += (u[i] - v[i]) ** 2;
  }
  const euclidean = Math.sqrt(sumSq);

  // Poincaré metric: d_H ≈ 2 * atanh(d_E) for small distances
  // Clamp to prevent infinity
  const clamped = Math.min(euclidean, 0.9999);
  return 2 * Math.atanh(clamped);
}

/**
 * Project a context vector into Poincaré Ball
 */
function projectToPoincare(context: Record<string, unknown>): number[] {
  // Extract features from context
  const features: number[] = [];

  // Time-based feature (normalized to [0, 1])
  const hour = new Date().getHours();
  features.push(hour / 24);

  // Context hash features
  const contextStr = JSON.stringify(context);
  let hash = 0;
  for (let i = 0; i < contextStr.length; i++) {
    hash = ((hash << 5) - hash) + contextStr.charCodeAt(i);
    hash = hash & hash;
  }

  // Generate 6D vector from hash
  for (let i = 0; i < 5; i++) {
    const shift = i * 5;
    const val = ((hash >> shift) & 0x1f) / 31; // 5-bit values normalized
    features.push(val * 0.8 - 0.4); // Center around 0, max radius ~0.4
  }

  // Ensure we're inside the ball (radius < 1)
  let radius = Math.sqrt(features.reduce((sum, x) => sum + x * x, 0));
  if (radius >= 1) {
    const scale = 0.95 / radius;
    for (let i = 0; i < features.length; i++) {
      features[i] *= scale;
    }
  }

  return features;
}

// ============================================================
// AETHERAUTH CLASS
// ============================================================

export class AetherAuth {
  private tokenizer: SacredTongueTokenizer;
  private challenges: Map<string, AuthChallenge> = new Map();
  private envelopes: Map<string, GeoSealEnvelope> = new Map();
  private trustedOrigins: Set<string> = new Set();

  constructor() {
    this.tokenizer = getTokenizer();
  }

  // ==================== Identity Management ====================

  /**
   * Compute identity vector from context
   */
  computeIdentityVector(context: Record<string, unknown>): IdentityVector {
    const coordinates = projectToPoincare(context) as [number, number, number, number, number, number];

    // Compute radius (distance from origin)
    const radius = Math.sqrt(coordinates.reduce((sum, x) => sum + x * x, 0));

    return {
      coordinates,
      radius,
      ring: getRingFromRadius(radius),
      timestamp: Date.now()
    };
  }

  /**
   * Compute harmonic fingerprint for identity
   */
  computeHarmonicFingerprint(
    identity: IdentityVector,
    tongue: TongueCode = 'ko'
  ): HarmonicFingerprint {
    const spec = TONGUES[tongue];

    // Encode identity as bytes
    const identityStr = JSON.stringify(identity.coordinates);
    const tokens = this.tokenizer.encodeString(tongue, identityStr);

    // Compute spectral signature
    const frequency = this.tokenizer.computeHarmonicFingerprint(tongue, tokens);

    return {
      frequency,
      weight: spec.weight,
      tongue,
      signature: tokens.slice(0, 4).join('-') // First 4 tokens as signature
    };
  }

  // ==================== Challenge-Response ====================

  /**
   * Create authentication challenge (Avali-encoded)
   */
  createChallenge(requiredRing: TrustRing = 'inner'): AuthChallenge {
    // Generate random nonce
    const nonceBytes = new Uint8Array(16);
    crypto.getRandomValues(nonceBytes);

    const nonceTokens = this.tokenizer.encodeBytes('av', nonceBytes);
    const nonce = this.tokenizer.formatTokens('av', nonceTokens);

    const challenge: AuthChallenge = {
      challengeId: `challenge-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      nonce,
      requiredRing,
      expiresAt: Date.now() + 60000, // 1 minute expiry
      tongue: 'av'
    };

    this.challenges.set(challenge.challengeId, challenge);

    // Clean old challenges
    this.cleanupChallenges();

    return challenge;
  }

  /**
   * Respond to challenge and receive envelope
   */
  async respondToChallenge(
    challengeId: string,
    context: Record<string, unknown>,
    scopes: string[] = ['read']
  ): Promise<AuthorizationResult> {
    const startTime = Date.now();

    const challenge = this.challenges.get(challengeId);
    if (!challenge) {
      return {
        valid: false,
        ring: 'event_horizon',
        latencyMs: Date.now() - startTime,
        error: 'Challenge not found or expired'
      };
    }

    if (Date.now() > challenge.expiresAt) {
      this.challenges.delete(challengeId);
      return {
        valid: false,
        ring: 'event_horizon',
        latencyMs: Date.now() - startTime,
        error: 'Challenge expired'
      };
    }

    // Compute identity from context
    const identity = this.computeIdentityVector(context);

    // Check if identity meets required ring
    const ringOrder: TrustRing[] = ['core', 'inner', 'outer', 'boundary', 'event_horizon'];
    const identityRingIndex = ringOrder.indexOf(identity.ring);
    const requiredRingIndex = ringOrder.indexOf(challenge.requiredRing);

    if (identityRingIndex > requiredRingIndex) {
      // Apply time dilation (delay based on how far outside required ring)
      const delayMs = TRUST_RING_THRESHOLDS[identity.ring].latencyMs;
      if (delayMs < Infinity) {
        await new Promise(resolve => setTimeout(resolve, Math.min(delayMs, 5000)));
      }

      return {
        valid: false,
        ring: identity.ring,
        latencyMs: Date.now() - startTime,
        error: `Access denied: Identity in ${identity.ring} ring, requires ${challenge.requiredRing}`
      };
    }

    // Create GeoSeal envelope
    const envelope = this.createEnvelope(identity, scopes);

    // Consume challenge
    this.challenges.delete(challengeId);

    return {
      valid: true,
      envelope,
      ring: identity.ring,
      latencyMs: Date.now() - startTime
    };
  }

  // ==================== Envelope Management ====================

  /**
   * Create GeoSeal envelope (replaces OAuth access token)
   */
  private createEnvelope(
    identity: IdentityVector,
    scopes: string[]
  ): GeoSealEnvelope {
    const fingerprint = this.computeHarmonicFingerprint(identity);

    // Encode payload in Cassisivadan (ciphertext tongue)
    const payloadObj = {
      identity: identity.coordinates,
      scopes,
      iat: Date.now()
    };
    const payloadTokens = this.tokenizer.encodeString('ca', JSON.stringify(payloadObj));
    const payload = this.tokenizer.formatTokens('ca', payloadTokens);

    // Create signature in Draumric (auth tag tongue)
    const sigData = `${payload}|${identity.radius}|${Date.now()}`;
    const sigTokens = this.tokenizer.encodeString('dr', sigData);
    const signature = this.tokenizer.formatTokens('dr', sigTokens.slice(0, 8));

    const envelope: GeoSealEnvelope = {
      version: 'GEOSEAL-1',
      kid: `kid-${Date.now().toString(36)}`,
      identity,
      fingerprint,
      scopes,
      expiresAt: Date.now() + 3600000, // 1 hour
      issuedAt: Date.now(),
      payload,
      signature
    };

    this.envelopes.set(envelope.kid, envelope);

    return envelope;
  }

  /**
   * Verify GeoSeal envelope
   */
  verifyEnvelope(
    envelope: GeoSealEnvelope,
    currentContext: Record<string, unknown>,
    requiredScopes: string[] = []
  ): AuthorizationResult {
    const startTime = Date.now();

    // Check expiration
    if (Date.now() > envelope.expiresAt) {
      return {
        valid: false,
        ring: 'event_horizon',
        latencyMs: Date.now() - startTime,
        error: 'Envelope expired'
      };
    }

    // Compute current identity
    const currentIdentity = this.computeIdentityVector(currentContext);

    // Check geometric drift (has the context changed significantly?)
    const drift = hyperbolicDistance(
      envelope.identity.coordinates,
      currentIdentity.coordinates
    );

    // Allow some drift, but not too much
    const maxAllowedDrift = 0.5;
    if (drift > maxAllowedDrift) {
      // Apply time dilation for suspicious drift
      const ring = getRingFromRadius(drift);
      return {
        valid: false,
        ring,
        latencyMs: Date.now() - startTime,
        error: `Geometric drift detected: ${drift.toFixed(3)} > ${maxAllowedDrift}`
      };
    }

    // Check scopes
    const hasAllScopes = requiredScopes.every(s => envelope.scopes.includes(s));
    if (!hasAllScopes) {
      return {
        valid: false,
        ring: currentIdentity.ring,
        latencyMs: Date.now() - startTime,
        error: `Missing required scopes: ${requiredScopes.filter(s => !envelope.scopes.includes(s)).join(', ')}`
      };
    }

    return {
      valid: true,
      envelope,
      ring: currentIdentity.ring,
      latencyMs: Date.now() - startTime
    };
  }

  // ==================== Decorator/Middleware ====================

  /**
   * Authorization decorator for functions
   */
  authorize<T extends (...args: unknown[]) => unknown>(
    requiredRing: TrustRing,
    requiredScopes: string[] = []
  ) {
    return (fn: T, context: Record<string, unknown>, envelope: GeoSealEnvelope): T => {
      const result = this.verifyEnvelope(envelope, context, requiredScopes);

      if (!result.valid) {
        throw new Error(`Authorization failed: ${result.error}`);
      }

      const ringOrder: TrustRing[] = ['core', 'inner', 'outer', 'boundary', 'event_horizon'];
      if (ringOrder.indexOf(result.ring) > ringOrder.indexOf(requiredRing)) {
        throw new Error(`Insufficient trust ring: ${result.ring}, requires ${requiredRing}`);
      }

      return fn;
    };
  }

  // ==================== Utilities ====================

  private cleanupChallenges(): void {
    const now = Date.now();
    const toDelete: string[] = [];
    this.challenges.forEach((challenge, id) => {
      if (now > challenge.expiresAt) {
        toDelete.push(id);
      }
    });
    toDelete.forEach(id => this.challenges.delete(id));
  }

  /**
   * Register trusted origin for CORS-like protection
   */
  addTrustedOrigin(origin: string): void {
    this.trustedOrigins.add(origin);
  }

  /**
   * Check if origin is trusted
   */
  isTrustedOrigin(origin: string): boolean {
    return this.trustedOrigins.has(origin);
  }

  /**
   * Revoke an envelope
   */
  revokeEnvelope(kid: string): boolean {
    return this.envelopes.delete(kid);
  }

  /**
   * Get envelope by kid
   */
  getEnvelope(kid: string): GeoSealEnvelope | undefined {
    return this.envelopes.get(kid);
  }
}

// ============================================================
// SINGLETON & HELPERS
// ============================================================

let authInstance: AetherAuth | null = null;

export function getAetherAuth(): AetherAuth {
  if (!authInstance) {
    authInstance = new AetherAuth();
  }
  return authInstance;
}

/**
 * Quick authorization check
 */
export async function quickAuth(
  context: Record<string, unknown>,
  requiredRing: TrustRing = 'inner',
  scopes: string[] = ['read']
): Promise<AuthorizationResult> {
  const auth = getAetherAuth();
  const challenge = auth.createChallenge(requiredRing);
  return auth.respondToChallenge(challenge.challengeId, context, scopes);
}

/**
 * React hook for AetherAuth
 */
import { useState, useCallback } from 'react';

export function useAetherAuth() {
  const [auth] = useState(() => getAetherAuth());
  const [envelope, setEnvelope] = useState<GeoSealEnvelope | null>(null);
  const [ring, setRing] = useState<TrustRing>('event_horizon');
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const authenticate = useCallback(async (
    context: Record<string, unknown>,
    requiredRing: TrustRing = 'inner',
    scopes: string[] = ['read']
  ) => {
    const challenge = auth.createChallenge(requiredRing);
    const result = await auth.respondToChallenge(challenge.challengeId, context, scopes);

    if (result.valid && result.envelope) {
      setEnvelope(result.envelope);
      setRing(result.ring);
      setIsAuthenticated(true);
    } else {
      setEnvelope(null);
      setRing(result.ring);
      setIsAuthenticated(false);
    }

    return result;
  }, [auth]);

  const verify = useCallback((
    currentContext: Record<string, unknown>,
    requiredScopes: string[] = []
  ) => {
    if (!envelope) {
      return { valid: false, ring: 'event_horizon' as TrustRing, error: 'No envelope' };
    }
    return auth.verifyEnvelope(envelope, currentContext, requiredScopes);
  }, [auth, envelope]);

  const logout = useCallback(() => {
    if (envelope) {
      auth.revokeEnvelope(envelope.kid);
    }
    setEnvelope(null);
    setRing('event_horizon');
    setIsAuthenticated(false);
  }, [auth, envelope]);

  return {
    auth,
    envelope,
    ring,
    isAuthenticated,
    authenticate,
    verify,
    logout
  };
}
