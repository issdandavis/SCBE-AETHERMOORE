/**
 * Spiralverse Protocol - RWP v2.1 Multi-Signature Envelopes
 *
 * Provides multi-signature consensus (Roundtable) for AI governance.
 *
 * The Six Sacred Tongues:
 * - KO (Kor'aelin): Control & Orchestration
 * - AV (Avali): I/O & Messaging
 * - RU (Runethic): Policy & Constraints
 * - CA (Cassisivadan): Logic & Computation
 * - UM (Umbroth): Security & Privacy
 * - DR (Draumric): Types & Structures
 *
 * @module spiralverse
 */

import { createHmac, randomBytes } from 'crypto';

// ============================================================================
// Types
// ============================================================================

/** Sacred Tongue identifier */
export type TongueID = 'ko' | 'av' | 'ru' | 'ca' | 'um' | 'dr';

/** Policy enforcement level */
export type PolicyLevel = 'standard' | 'strict' | 'critical';

/** Keyring containing keys for all tongues */
export type Keyring = {
  [K in TongueID]?: Buffer;
};

/** Signature map by tongue */
export type SignatureMap = {
  [K in TongueID]?: string;
};

/** RWP v2.1 Envelope structure */
export interface RWPEnvelope {
  ver: '2.1';
  primary_tongue: TongueID;
  aad: string;
  payload: string; // base64url encoded
  sigs: SignatureMap;
  nonce: string; // base64url encoded
  ts: number; // milliseconds since epoch
  kid?: string; // optional key ID
}

/** Verification result */
export interface VerifyResult {
  valid: boolean;
  validTongues: TongueID[];
  payload?: unknown;
  error?: string;
}

/** Options for signing */
export interface SignOptions {
  kid?: string;
  timestamp?: number;
  nonce?: Buffer;
}

/** Options for verification */
export interface VerifyOptions {
  policy?: PolicyLevel;
  maxAge?: number; // max age in ms (default 300000 = 5 min)
  maxFutureSkew?: number; // max future skew in ms (default 60000 = 1 min)
}

// ============================================================================
// Constants
// ============================================================================

const VERSION = '2.1';
const DEFAULT_MAX_AGE = 300000; // 5 minutes
const DEFAULT_MAX_FUTURE_SKEW = 60000; // 1 minute

/** Policy requirements for each level */
const POLICY_REQUIREMENTS: Record<PolicyLevel, TongueID[]> = {
  standard: ['ko'],
  strict: ['ru'],
  critical: ['ru', 'um', 'dr'],
};

/** Action to policy mapping */
const ACTION_POLICIES: Record<string, PolicyLevel> = {
  read: 'standard',
  write: 'standard',
  deploy: 'strict',
  delete: 'strict',
  admin: 'critical',
  security: 'critical',
};

// ============================================================================
// Nonce Cache (Replay Protection)
// ============================================================================

const nonceCache = new Set<string>();
const nonceCacheTimestamps = new Map<string, number>();

/**
 * Clear the nonce cache (for testing)
 */
export function clearNonceCache(): void {
  nonceCache.clear();
  nonceCacheTimestamps.clear();
}

/**
 * Check if nonce has been used and add to cache
 */
function checkAndAddNonce(nonce: string, timestamp: number): boolean {
  // Clean up old nonces (older than 10 minutes)
  const now = Date.now();
  for (const [n, ts] of nonceCacheTimestamps) {
    if (now - ts > 600000) {
      nonceCache.delete(n);
      nonceCacheTimestamps.delete(n);
    }
  }

  if (nonceCache.has(nonce)) {
    return false; // Already used
  }

  nonceCache.add(nonce);
  nonceCacheTimestamps.set(nonce, timestamp);
  return true;
}

// ============================================================================
// Utility Functions
// ============================================================================

function toBase64Url(buf: Buffer): string {
  return buf.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function fromBase64Url(s: string): Buffer {
  let str = s.replace(/-/g, '+').replace(/_/g, '/');
  while (str.length % 4) str += '=';
  return Buffer.from(str, 'base64');
}

/**
 * Create HMAC-SHA256 signature
 */
function createSignature(key: Buffer, data: Buffer): string {
  const hmac = createHmac('sha256', key);
  hmac.update(data);
  return toBase64Url(hmac.digest());
}

/**
 * Verify HMAC-SHA256 signature
 */
function verifySignature(key: Buffer, data: Buffer, signature: string): boolean {
  const expected = createSignature(key, data);
  // Constant-time comparison
  if (expected.length !== signature.length) return false;
  let result = 0;
  for (let i = 0; i < expected.length; i++) {
    result |= expected.charCodeAt(i) ^ signature.charCodeAt(i);
  }
  return result === 0;
}

/**
 * Create signature data buffer
 */
function createSignatureData(
  version: string,
  primaryTongue: TongueID,
  aad: string,
  payload: string,
  nonce: string,
  ts: number,
  tongue: TongueID
): Buffer {
  const data = `${version}.${primaryTongue}.${tongue}.${aad}.${payload}.${nonce}.${ts}`;
  return Buffer.from(data, 'utf8');
}

// ============================================================================
// Core Functions
// ============================================================================

/**
 * Sign a payload with multiple Sacred Tongues (Roundtable consensus)
 *
 * @param payload - The payload to sign
 * @param primaryTongue - The initiating tongue
 * @param aad - Additional authenticated data
 * @param keyring - Keys for signing
 * @param signingTongues - Which tongues should sign
 * @param options - Optional signing options
 * @returns The signed RWP envelope
 */
export function signRoundtable(
  payload: unknown,
  primaryTongue: TongueID,
  aad: string,
  keyring: Keyring,
  signingTongues: TongueID[],
  options: SignOptions = {}
): RWPEnvelope {
  // Validate inputs
  if (payload === null || payload === undefined) {
    throw new Error('Payload is required');
  }

  if (!primaryTongue) {
    throw new Error('Primary tongue is required');
  }

  if (!signingTongues || signingTongues.length === 0) {
    throw new Error('At least one signing tongue is required');
  }

  // Check all required keys are present
  for (const tongue of signingTongues) {
    if (!keyring[tongue]) {
      throw new Error(`Missing key for tongue: ${tongue}`);
    }
  }

  // Encode payload
  const payloadJson = JSON.stringify(payload);
  const payloadEncoded = toBase64Url(Buffer.from(payloadJson, 'utf8'));

  // Generate nonce
  const nonce = options.nonce ?? randomBytes(16);
  const nonceEncoded = toBase64Url(nonce);

  // Timestamp
  const ts = options.timestamp ?? Date.now();

  // Create signatures for each tongue
  const sigs: SignatureMap = {};
  for (const tongue of signingTongues) {
    const key = keyring[tongue]!;
    const sigData = createSignatureData(
      VERSION,
      primaryTongue,
      aad,
      payloadEncoded,
      nonceEncoded,
      ts,
      tongue
    );
    sigs[tongue] = createSignature(key, sigData);
  }

  // Build envelope
  const envelope: RWPEnvelope = {
    ver: '2.1',
    primary_tongue: primaryTongue,
    aad,
    payload: payloadEncoded,
    sigs,
    nonce: nonceEncoded,
    ts,
  };

  if (options.kid) {
    envelope.kid = options.kid;
  }

  return envelope;
}

/**
 * Verify an RWP envelope
 *
 * @param envelope - The envelope to verify
 * @param keyring - Keys for verification
 * @param options - Verification options
 * @returns Verification result
 */
export function verifyRoundtable(
  envelope: RWPEnvelope,
  keyring: Keyring,
  options: VerifyOptions = {}
): VerifyResult {
  const maxAge = options.maxAge ?? DEFAULT_MAX_AGE;
  const maxFutureSkew = options.maxFutureSkew ?? DEFAULT_MAX_FUTURE_SKEW;

  // Check version
  if (envelope.ver !== '2.1') {
    return {
      valid: false,
      validTongues: [],
      error: `Unsupported version: ${envelope.ver}`,
    };
  }

  // Check timestamp
  const now = Date.now();
  const age = now - envelope.ts;

  if (age > maxAge) {
    return {
      valid: false,
      validTongues: [],
      error: 'Timestamp too old',
    };
  }

  if (age < -maxFutureSkew) {
    return {
      valid: false,
      validTongues: [],
      error: 'Timestamp is in the future',
    };
  }

  // Check nonce replay
  if (!checkAndAddNonce(envelope.nonce, envelope.ts)) {
    return {
      valid: false,
      validTongues: [],
      error: 'Nonce already used (replay detected)',
    };
  }

  // Verify signatures
  const validTongues: TongueID[] = [];
  const allTongues = Object.keys(envelope.sigs) as TongueID[];

  for (const tongue of allTongues) {
    const key = keyring[tongue];
    if (!key) continue; // Skip if key not in keyring

    const signature = envelope.sigs[tongue];
    if (!signature) continue;

    const sigData = createSignatureData(
      envelope.ver,
      envelope.primary_tongue,
      envelope.aad,
      envelope.payload,
      envelope.nonce,
      envelope.ts,
      tongue
    );

    if (verifySignature(key, sigData, signature)) {
      validTongues.push(tongue);
    }
  }

  if (validTongues.length === 0) {
    return {
      valid: false,
      validTongues: [],
      error: 'No valid signatures found',
    };
  }

  // Check policy if specified
  if (options.policy) {
    const required = POLICY_REQUIREMENTS[options.policy];
    const hasAllRequired = required.every(t => validTongues.includes(t));

    if (!hasAllRequired) {
      const missing = required.filter(t => !validTongues.includes(t));
      return {
        valid: false,
        validTongues,
        error: `Policy violation: missing required tongue(s): ${missing.join(', ')}`,
      };
    }
  }

  // Decode payload
  let payload: unknown;
  try {
    const payloadBuffer = fromBase64Url(envelope.payload);
    payload = JSON.parse(payloadBuffer.toString('utf8'));
  } catch {
    return {
      valid: false,
      validTongues,
      error: 'Failed to decode payload',
    };
  }

  return {
    valid: true,
    validTongues,
    payload,
  };
}

// ============================================================================
// Policy Helpers
// ============================================================================

/**
 * Check if a set of tongues satisfies a policy
 *
 * @param tongues - The tongues that have signed
 * @param policy - The policy level to check
 * @returns Whether the policy is satisfied
 */
export function checkPolicy(tongues: TongueID[], policy: PolicyLevel): boolean {
  const required = POLICY_REQUIREMENTS[policy];
  return required.every(t => tongues.includes(t));
}

/**
 * Get the required tongues for a policy level
 *
 * @param policy - The policy level
 * @returns Array of required tongue IDs
 */
export function getRequiredTongues(policy: PolicyLevel): TongueID[] {
  return [...POLICY_REQUIREMENTS[policy]];
}

/**
 * Suggest an appropriate policy level for an action
 *
 * @param action - The action being performed
 * @returns Suggested policy level
 */
export function suggestPolicy(action: string): PolicyLevel {
  const normalizedAction = action.toLowerCase();
  return ACTION_POLICIES[normalizedAction] ?? 'standard';
}
