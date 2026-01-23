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

/**
 * Sacred Tongue identifiers (6 domains)
 */
export type TongueID = 'ko' | 'av' | 'ru' | 'ca' | 'um' | 'dr';

/**
 * Policy levels for envelope verification
 */
export type PolicyLevel = 'standard' | 'strict' | 'secret' | 'critical';

/**
 * RWP v2.1 Multi-Signature Envelope
 * 
 * @template T - Payload type (must be JSON-serializable)
 */
export interface RWP2MultiEnvelope<T = any> {
  /** Protocol version (always "2.1") */
  ver: "2.1";
  
  /** Primary tongue indicating intent domain */
  primary_tongue: TongueID;
  
  /** Additional authenticated data (metadata) */
  aad: string;
  
  /** Timestamp in Unix milliseconds */
  ts: number;
  
  /** Nonce for replay protection (Base64URL) */
  nonce: string;
  
  /** Payload (Base64URL encoded JSON) */
  payload: string;
  
  /** Multi-signatures keyed by tongue */
  sigs: Partial<Record<TongueID, string>>;
  
  /** Optional key ID for key rotation */
  kid?: string;
}

/**
 * Keyring for Sacred Tongue HMAC keys
 */
export interface Keyring {
  /** HMAC keys indexed by tongue code */
  [tongueCode: string]: Buffer;
}

/**
 * Policy matrix configuration
 */
export interface PolicyMatrix {
  standard: TongueID[];   // Any valid signature
  strict: TongueID[];     // Requires RU (Policy)
  secret: TongueID[];     // Requires UM (Security)
  critical: TongueID[];   // Requires RU + UM + DR
}

/**
 * Verification result
 */
export interface VerificationResult {
  /** Whether verification passed */
  valid: boolean;
  
  /** List of valid tongues */
  validTongues: TongueID[];
  
  /** Error message if verification failed */
  error?: string;
  
  /** Decoded payload if verification passed */
  payload?: any;
}

/**
 * Envelope creation options
 */
export interface EnvelopeOptions {
  /** Key ID for key rotation */
  kid?: string;
  
  /** Custom timestamp (default: Date.now()) */
  timestamp?: number;
  
  /** Custom nonce (default: random 16 bytes) */
  nonce?: Buffer;
}

/**
 * Verification options
 */
export interface VerificationOptions {
  /** Replay window in milliseconds (default: 300000 = 5 minutes) */
  replayWindowMs?: number;
  
  /** Clock skew tolerance in milliseconds (default: 60000 = 1 minute) */
  clockSkewMs?: number;
  
  /** Policy level to enforce (default: 'standard') */
  policy?: PolicyLevel;
}

/**
 * Nonce cache entry
 */
export interface NonceCacheEntry {
  /** Nonce value */
  nonce: string;
  
  /** Timestamp when nonce was first seen */
  timestamp: number;
}

/**
 * Sacred Tongue specification
 */
export interface TongueSpec {
  /** 2-letter code */
  code: TongueID;
  
  /** Full name */
  name: string;
  
  /** Semantic domain */
  domain: string;
  
  /** 16 prefixes */
  prefixes: string[];
  
  /** 16 suffixes */
  suffixes: string[];
}

/**
 * Error types
 */
export class RWPError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'RWPError';
  }
}

export class SignatureError extends RWPError {
  constructor(message: string) {
    super(message);
    this.name = 'SignatureError';
  }
}

export class ReplayError extends RWPError {
  constructor(message: string) {
    super(message);
    this.name = 'ReplayError';
  }
}

export class PolicyError extends RWPError {
  constructor(message: string) {
    super(message);
    this.name = 'PolicyError';
  }
}
