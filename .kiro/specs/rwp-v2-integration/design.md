# RWP v2.1 Multi-Signature Envelopes - Design Document

**Feature**: rwp-v2-integration  
**Version**: 3.1.0  
**Phase**: 2 (Protocol Layer)  
**Status**: Design  
**Last Updated**: January 18, 2026

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Module Structure](#2-module-structure)
3. [Data Structures](#3-data-structures)
4. [Core Algorithms](#4-core-algorithms)
5. [API Specifications](#5-api-specifications)
6. [Security Design](#6-security-design)
7. [Performance Design](#7-performance-design)
8. [Error Handling](#8-error-handling)
9. [Testing Strategy](#9-testing-strategy)
10. [Integration Points](#10-integration-points)
11. [Implementation Plan](#11-implementation-plan)
12. [Appendices](#12-appendices)

---

## 1. Architecture Overview

### 1.1 System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCBE-AETHERMOORE v3.1.0                      │
│                  (RWP v2.1 Integration Layer)                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      RWP v2.1 LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Envelope   │  │    Policy    │  │   Keyring    │         │
│  │   Manager    │  │   Enforcer   │  │   Manager    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────┐          │
│  │          Signature Engine (HMAC-SHA256)          │          │
│  └──────────────────────────────────────────────────┘          │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────┐          │
│  │         Replay Protection (Nonce Cache)          │          │
│  └──────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              SACRED TONGUES FRAMEWORK (v3.0.0)                  │
│  KO │ AV │ RU │ CA │ UM │ DR                                   │
│  (Domain Separation + Semantic Routing)                         │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Design Principles

**DP-1.2.1**: **Domain Separation** - Each Sacred Tongue has independent cryptographic identity

**DP-1.2.2**: **Fail-to-Noise** - Invalid operations return noise, not error details

**DP-1.2.3**: **Zero Trust** - Verify everything, trust nothing

**DP-1.2.4**: **Semantic Security** - Intent determines authentication requirements

**DP-1.2.5**: **Composability** - Components work independently and together

**DP-1.2.6**: **Language Agnostic** - TypeScript and Python implementations are identical

### 1.3 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT CODE                             │
│  (Fleet Engine, Roundtable, User Applications)                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      PUBLIC API LAYER                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  signRoundtable()    verifyRoundtable()                  │  │
│  │  enforceRoundtablePolicy()    createKeyring()            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    ENVELOPE MANAGER                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • Create envelope structure                             │  │
│  │  • Serialize/deserialize                                 │  │
│  │  • Validate envelope format                              │  │
│  │  • Generate nonces                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    SIGNATURE ENGINE                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • HMAC-SHA256 computation                               │  │
│  │  • Multi-tongue signing                                  │  │
│  │  • Signature verification                                │  │
│  │  • Base64URL encoding/decoding                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    POLICY ENFORCER                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • Policy matrix lookup                                  │  │
│  │  • Required tongue validation                            │  │
│  │  • Policy violation detection                            │  │
│  │  • Custom policy support                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    REPLAY PROTECTOR                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • Nonce cache (LRU)                                     │  │
│  │  • Timestamp validation                                  │  │
│  │  • Clock skew tolerance                                  │  │
│  │  • Duplicate detection                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    KEYRING MANAGER                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • Key storage (per tongue)                              │  │
│  │  • Key rotation support                                  │  │
│  │  • Key versioning (kid)                                  │  │
│  │  • Secure key loading                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    CRYPTO PRIMITIVES                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Node.js crypto (TypeScript)                             │  │
│  │  Python hashlib + hmac (Python)                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.4 Data Flow

#### 1.4.1 Envelope Creation Flow

```
1. Client creates envelope request
   ↓
2. Envelope Manager generates structure
   - Assigns version: "2.1"
   - Sets primary_tongue from request
   - Copies aad from request
   - Generates timestamp (Date.now())
   - Generates random nonce (16 bytes)
   - Encodes payload to Base64URL
   ↓
3. Signature Engine signs envelope
   - For each tongue in signingTongues:
     - Construct canonical string
     - Compute HMAC-SHA256
     - Encode signature to Base64URL
     - Store in sigs[tongue]
   ↓
4. Return signed envelope
```

#### 1.4.2 Envelope Verification Flow

```
1. Client submits envelope for verification
   ↓
2. Replay Protector validates freshness
   - Check timestamp within window
   - Check nonce not in cache
   - Add nonce to cache
   ↓
3. Signature Engine verifies signatures
   - For each tongue in envelope.sigs:
     - Lookup key in keyring
     - Reconstruct canonical string
     - Compute expected HMAC-SHA256
     - Compare with envelope signature
     - Add to validTongues if match
   ↓
4. Policy Enforcer checks requirements
   - Lookup policy level
   - Check validTongues contains required tongues
   - Return success/failure
   ↓
5. Return verification result
```

---

## 2. Module Structure

### 2.1 TypeScript Module Organization

```
src/spiralverse/
├── index.ts                 # Public API exports
├── rwp.ts                   # Core envelope logic
├── policy.ts                # Policy enforcement
├── keyring.ts               # Key management
├── replay.ts                # Replay protection
├── signature.ts             # Signature engine
├── types.ts                 # TypeScript interfaces
├── constants.ts             # Constants and enums
└── utils.ts                 # Utility functions

tests/spiralverse/
├── rwp.test.ts              # Core tests
├── policy.test.ts           # Policy tests
├── keyring.test.ts          # Keyring tests
├── replay.test.ts           # Replay tests
├── signature.test.ts        # Signature tests
├── interop.test.ts          # TypeScript ↔ Python interop
└── property.test.ts         # Property-based tests (fast-check)
```

### 2.2 Python Module Organization

```
src/symphonic_cipher/spiralverse/
├── __init__.py              # Public API exports
├── rwp.py                   # Core envelope logic
├── policy.py                # Policy enforcement
├── keyring.py               # Key management
├── replay.py                # Replay protection
├── signature.py             # Signature engine
├── types.py                 # Type definitions
├── constants.py             # Constants and enums
└── utils.py                 # Utility functions

tests/spiralverse/
├── test_rwp.py              # Core tests
├── test_policy.py           # Policy tests
├── test_keyring.py          # Keyring tests
├── test_replay.py           # Replay tests
├── test_signature.py        # Signature tests
├── test_interop.py          # Python ↔ TypeScript interop
└── test_property.py         # Property-based tests (hypothesis)
```

### 2.3 Module Dependencies

```
┌─────────────┐
│   index.ts  │  (Public API)
└─────────────┘
       ↓
┌─────────────┐
│    rwp.ts   │  (Core Logic)
└─────────────┘
       ↓
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ signature.ts│  policy.ts  │  replay.ts  │ keyring.ts  │
└─────────────┴─────────────┴─────────────┴─────────────┘
       ↓             ↓             ↓             ↓
┌─────────────┬─────────────┬─────────────┬─────────────┐
│   types.ts  │constants.ts │  utils.ts   │   crypto    │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

**Dependency Rules**:

- No circular dependencies
- Core modules depend only on primitives
- Public API depends on core modules
- Tests depend on all modules

---

## 3. Data Structures

### 3.1 Core Types (TypeScript)

```typescript
/**
 * Sacred Tongue identifier
 * KO: Kor'aelin (Control & Orchestration)
 * AV: Avali (I/O & Messaging)
 * RU: Runethic (Policy & Constraints)
 * CA: Cassisivadan (Logic & Computation)
 * UM: Umbroth (Security & Privacy)
 * DR: Draumric (Types & Structures)
 */
export type TongueID = 'ko' | 'av' | 'ru' | 'ca' | 'um' | 'dr';

/**
 * Policy security level
 * standard: Any valid signature
 * strict: Requires RU (Policy)
 * secret: Requires UM (Security)
 * critical: Requires RU + UM + DR (full consensus)
 */
export type PolicyLevel = 'standard' | 'strict' | 'secret' | 'critical';

/**
 * RWP v2.1 Multi-Signature Envelope
 *
 * @template T - Payload type (must be JSON-serializable)
 */
export interface RWP2MultiEnvelope<T = any> {
  /** Protocol version (always "2.1") */
  ver: '2.1';

  /** Primary intent domain (determines semantic routing) */
  primary_tongue: TongueID;

  /** Additional authenticated data (metadata, context) */
  aad: string;

  /** Unix timestamp in milliseconds */
  ts: number;

  /** Cryptographic nonce for replay protection (Base64URL) */
  nonce: string;

  /** Base64URL-encoded JSON payload */
  payload: string;

  /** Multi-signature map: tongue → Base64URL HMAC-SHA256 */
  sigs: Partial<Record<TongueID, string>>;

  /** Optional key ID for key rotation */
  kid?: string;
}

/**
 * Keyring for multi-tongue authentication
 * Maps tongue ID to 32-byte HMAC key
 */
export interface Keyring {
  /** Keyring identifier */
  id: string;

  /** Key map: tongue → 32-byte Buffer */
  keys: Partial<Record<TongueID, Buffer>>;

  /** Optional key version */
  version?: string;

  /** Optional expiration timestamp */
  expiresAt?: number;
}

/**
 * Verification result
 */
export interface VerificationResult {
  /** Whether verification succeeded */
  success: boolean;

  /** List of tongues with valid signatures */
  validTongues: TongueID[];

  /** Error message if verification failed */
  error?: string;

  /** Decoded payload (if verification succeeded) */
  payload?: any;
}

/**
 * Policy enforcement result
 */
export interface PolicyResult {
  /** Whether policy is satisfied */
  satisfied: boolean;

  /** Policy level that was checked */
  level: PolicyLevel;

  /** Required tongues for this policy */
  required: TongueID[];

  /** Tongues that were present */
  present: TongueID[];

  /** Missing tongues (if policy not satisfied) */
  missing?: TongueID[];
}

/**
 * Replay protection configuration
 */
export interface ReplayConfig {
  /** Replay window in milliseconds (default: 300000 = 5 minutes) */
  windowMs: number;

  /** Clock skew tolerance in milliseconds (default: 60000 = 1 minute) */
  skewMs: number;

  /** Maximum nonce cache size (default: 10000) */
  maxCacheSize: number;
}

/**
 * Envelope creation options
 */
export interface EnvelopeOptions {
  /** Key ID for key rotation */
  kid?: string;

  /** Custom timestamp (for testing) */
  timestamp?: number;

  /** Custom nonce (for testing) */
  nonce?: string;
}
```

### 3.2 Core Types (Python)

```python
from typing import TypedDict, Literal, Optional, Dict, List, Any
from dataclasses import dataclass

# Sacred Tongue identifier
TongueID = Literal['ko', 'av', 'ru', 'ca', 'um', 'dr']

# Policy security level
PolicyLevel = Literal['standard', 'strict', 'secret', 'critical']

class RWP2MultiEnvelope(TypedDict, total=False):
    """RWP v2.1 Multi-Signature Envelope"""
    ver: Literal["2.1"]
    primary_tongue: TongueID
    aad: str
    ts: int
    nonce: str
    payload: str
    sigs: Dict[TongueID, str]
    kid: Optional[str]

@dataclass
class Keyring:
    """Keyring for multi-tongue authentication"""
    id: str
    keys: Dict[TongueID, bytes]
    version: Optional[str] = None
    expires_at: Optional[int] = None

@dataclass
class VerificationResult:
    """Verification result"""
    success: bool
    valid_tongues: List[TongueID]
    error: Optional[str] = None
    payload: Optional[Any] = None

@dataclass
class PolicyResult:
    """Policy enforcement result"""
    satisfied: bool
    level: PolicyLevel
    required: List[TongueID]
    present: List[TongueID]
    missing: Optional[List[TongueID]] = None

@dataclass
class ReplayConfig:
    """Replay protection configuration"""
    window_ms: int = 300000  # 5 minutes
    skew_ms: int = 60000     # 1 minute
    max_cache_size: int = 10000

@dataclass
class EnvelopeOptions:
    """Envelope creation options"""
    kid: Optional[str] = None
    timestamp: Optional[int] = None
    nonce: Optional[str] = None
```

### 3.3 Constants

```typescript
/**
 * Sacred Tongues metadata
 */
export const TONGUES = {
  ko: { name: "Kor'aelin", domain: 'control' },
  av: { name: 'Avali', domain: 'io' },
  ru: { name: 'Runethic', domain: 'policy' },
  ca: { name: 'Cassisivadan', domain: 'compute' },
  um: { name: 'Umbroth', domain: 'security' },
  dr: { name: 'Draumric', domain: 'structure' },
} as const;

/**
 * Policy matrix: level → required tongues
 */
export const POLICY_MATRIX: Record<PolicyLevel, TongueID[]> = {
  standard: [], // Any valid signature
  strict: ['ru'], // Requires Policy tongue
  secret: ['um'], // Requires Security tongue
  critical: ['ru', 'um', 'dr'], // Requires Policy + Security + Structure
};

/**
 * Default replay protection configuration
 */
export const DEFAULT_REPLAY_CONFIG: ReplayConfig = {
  windowMs: 300000, // 5 minutes
  skewMs: 60000, // 1 minute
  maxCacheSize: 10000, // 10K nonces
};

/**
 * Cryptographic constants
 */
export const CRYPTO_CONSTANTS = {
  HMAC_ALGORITHM: 'sha256',
  KEY_SIZE: 32, // 256 bits
  NONCE_SIZE: 16, // 128 bits
  SIGNATURE_SIZE: 32, // 256 bits (SHA-256 output)
} as const;

/**
 * Protocol version
 */
export const RWP_VERSION = '2.1' as const;
```

---

## 4. Core Algorithms

### 4.1 Signature Generation Algorithm

```typescript
/**
 * Generate HMAC-SHA256 signature for an envelope
 *
 * Algorithm:
 * 1. Construct canonical string from envelope fields
 * 2. Compute HMAC-SHA256 using tongue-specific key
 * 3. Encode signature to Base64URL
 *
 * Canonical String Format:
 *   ver|primary_tongue|aad|ts|nonce|payload
 *
 * Security Properties:
 * - Domain separation: Each tongue uses independent key
 * - Replay protection: Includes timestamp and nonce
 * - Context binding: Includes aad (additional authenticated data)
 * - Integrity: Any modification invalidates signature
 *
 * @param envelope - Envelope to sign (without sigs field)
 * @param key - 32-byte HMAC key for specific tongue
 * @param tongue - Tongue identifier
 * @returns Base64URL-encoded signature
 */
function generateSignature(
  envelope: Omit<RWP2MultiEnvelope, 'sigs'>,
  key: Buffer,
  tongue: TongueID
): string {
  // Step 1: Construct canonical string
  const canonical = [
    envelope.ver,
    envelope.primary_tongue,
    envelope.aad,
    envelope.ts.toString(),
    envelope.nonce,
    envelope.payload,
  ].join('|');

  // Step 2: Compute HMAC-SHA256
  const hmac = crypto.createHmac('sha256', key);
  hmac.update(canonical, 'utf8');
  const signature = hmac.digest();

  // Step 3: Encode to Base64URL
  return base64url.encode(signature);
}
```

**Pseudocode**:

```
FUNCTION generateSignature(envelope, key, tongue):
  canonical ← ver || "|" || primary_tongue || "|" || aad || "|" ||
              ts || "|" || nonce || "|" || payload

  signature ← HMAC-SHA256(key, canonical)

  RETURN Base64URL(signature)
END FUNCTION
```

**Complexity**: O(n) where n = length of canonical string  
**Time**: <1ms for typical envelope (< 10KB)

### 4.2 Multi-Signature Generation Algorithm

```typescript
/**
 * Sign envelope with multiple tongues
 *
 * Algorithm:
 * 1. For each tongue in signingTongues:
 *    a. Lookup key in keyring
 *    b. Generate signature using generateSignature()
 *    c. Store signature in envelope.sigs[tongue]
 * 2. Return envelope with all signatures
 *
 * Security Properties:
 * - Independent signatures: Each tongue signs independently
 * - Partial signatures: Some tongues can be missing
 * - Order independence: Signature order doesn't matter
 *
 * @param envelope - Envelope to sign
 * @param keyring - Keyring with keys for each tongue
 * @param signingTongues - List of tongues to sign with
 * @returns Envelope with signatures
 */
function signRoundtable<T>(
  envelope: Omit<RWP2MultiEnvelope<T>, 'sigs'>,
  keyring: Keyring,
  signingTongues: TongueID[]
): RWP2MultiEnvelope<T> {
  const sigs: Partial<Record<TongueID, string>> = {};

  for (const tongue of signingTongues) {
    // Lookup key
    const key = keyring.keys[tongue];
    if (!key) {
      throw new Error(`Missing key for tongue: ${tongue}`);
    }

    // Generate signature
    sigs[tongue] = generateSignature(envelope, key, tongue);
  }

  return { ...envelope, sigs };
}
```

**Pseudocode**:

```
FUNCTION signRoundtable(envelope, keyring, signingTongues):
  sigs ← empty map

  FOR EACH tongue IN signingTongues:
    key ← keyring.keys[tongue]
    IF key is NULL:
      THROW "Missing key for tongue"
    END IF

    signature ← generateSignature(envelope, key, tongue)
    sigs[tongue] ← signature
  END FOR

  envelope.sigs ← sigs
  RETURN envelope
END FUNCTION
```

**Complexity**: O(k × n) where k = number of tongues, n = envelope size  
**Time**: <10ms for 6 tongues signing 10KB envelope

### 4.3 Signature Verification Algorithm

```typescript
/**
 * Verify all signatures in an envelope
 *
 * Algorithm:
 * 1. For each signature in envelope.sigs:
 *    a. Lookup key in keyring
 *    b. Reconstruct canonical string
 *    c. Compute expected HMAC-SHA256
 *    d. Compare with envelope signature (constant-time)
 *    e. Add tongue to validTongues if match
 * 2. Return list of valid tongues
 *
 * Security Properties:
 * - Constant-time comparison: Prevents timing attacks
 * - Independent verification: Each signature verified independently
 * - Fail-safe: Invalid signatures don't affect valid ones
 *
 * @param envelope - Envelope to verify
 * @param keyring - Keyring with keys for verification
 * @returns List of tongues with valid signatures
 */
function verifySignatures(envelope: RWP2MultiEnvelope, keyring: Keyring): TongueID[] {
  const validTongues: TongueID[] = [];

  for (const [tongue, signature] of Object.entries(envelope.sigs)) {
    // Lookup key
    const key = keyring.keys[tongue as TongueID];
    if (!key) {
      continue; // Skip if key not available
    }

    // Reconstruct canonical string
    const canonical = [
      envelope.ver,
      envelope.primary_tongue,
      envelope.aad,
      envelope.ts.toString(),
      envelope.nonce,
      envelope.payload,
    ].join('|');

    // Compute expected signature
    const hmac = crypto.createHmac('sha256', key);
    hmac.update(canonical, 'utf8');
    const expected = hmac.digest();

    // Constant-time comparison
    const actual = base64url.toBuffer(signature);
    if (crypto.timingSafeEqual(expected, actual)) {
      validTongues.push(tongue as TongueID);
    }
  }

  return validTongues;
}
```

**Pseudocode**:

```
FUNCTION verifySignatures(envelope, keyring):
  validTongues ← empty list

  FOR EACH (tongue, signature) IN envelope.sigs:
    key ← keyring.keys[tongue]
    IF key is NULL:
      CONTINUE  // Skip missing keys
    END IF

    canonical ← constructCanonicalString(envelope)
    expected ← HMAC-SHA256(key, canonical)
    actual ← Base64URL.decode(signature)

    IF timingSafeEqual(expected, actual):
      validTongues.append(tongue)
    END IF
  END FOR

  RETURN validTongues
END FUNCTION
```

**Complexity**: O(k × n) where k = number of signatures, n = envelope size  
**Time**: <5ms for 6 signatures on 10KB envelope

### 4.4 Policy Enforcement Algorithm

```typescript
/**
 * Enforce policy requirements on verified tongues
 *
 * Algorithm:
 * 1. Lookup required tongues for policy level
 * 2. Check if all required tongues are in validTongues
 * 3. Return satisfaction result
 *
 * Policy Matrix:
 * - standard: [] (any valid signature)
 * - strict: ['ru'] (requires Policy tongue)
 * - secret: ['um'] (requires Security tongue)
 * - critical: ['ru', 'um', 'dr'] (requires Policy + Security + Structure)
 *
 * @param validTongues - List of tongues with valid signatures
 * @param policy - Policy level to enforce
 * @returns Policy enforcement result
 */
function enforceRoundtablePolicy(validTongues: TongueID[], policy: PolicyLevel): PolicyResult {
  const required = POLICY_MATRIX[policy];
  const present = validTongues;

  // Check if all required tongues are present
  const missing = required.filter((t) => !present.includes(t));
  const satisfied = missing.length === 0;

  return {
    satisfied,
    level: policy,
    required,
    present,
    missing: satisfied ? undefined : missing,
  };
}
```

**Pseudocode**:

```
FUNCTION enforceRoundtablePolicy(validTongues, policy):
  required ← POLICY_MATRIX[policy]
  present ← validTongues

  missing ← []
  FOR EACH tongue IN required:
    IF tongue NOT IN present:
      missing.append(tongue)
    END IF
  END FOR

  satisfied ← (missing is empty)

  RETURN PolicyResult(satisfied, policy, required, present, missing)
END FUNCTION
```

**Complexity**: O(r × p) where r = required tongues, p = present tongues  
**Time**: <1ms (typically r ≤ 3, p ≤ 6)

### 4.5 Replay Protection Algorithm

```typescript
/**
 * Validate envelope freshness and prevent replay attacks
 *
 * Algorithm:
 * 1. Check timestamp is within replay window
 * 2. Check timestamp is not in future (with clock skew tolerance)
 * 3. Check nonce is not in cache (duplicate detection)
 * 4. Add nonce to cache with expiration
 *
 * Security Properties:
 * - Time-bound: Old envelopes are rejected
 * - Uniqueness: Duplicate nonces are rejected
 * - Clock skew tolerance: Allows ±60s clock difference
 * - Memory efficient: LRU cache with automatic eviction
 *
 * @param envelope - Envelope to validate
 * @param config - Replay protection configuration
 * @param cache - Nonce cache
 * @returns true if envelope is fresh, false otherwise
 */
function validateFreshness(
  envelope: RWP2MultiEnvelope,
  config: ReplayConfig,
  cache: NonceCache
): boolean {
  const now = Date.now();
  const ts = envelope.ts;
  const nonce = envelope.nonce;

  // Check timestamp is not too old
  if (now - ts > config.windowMs) {
    return false; // Too old
  }

  // Check timestamp is not in future (with clock skew tolerance)
  if (ts - now > config.skewMs) {
    return false; // Too far in future
  }

  // Check nonce is not duplicate
  if (cache.has(nonce)) {
    return false; // Replay attack detected
  }

  // Add nonce to cache with expiration
  const expiresAt = ts + config.windowMs;
  cache.set(nonce, expiresAt);

  return true;
}
```

**Pseudocode**:

```
FUNCTION validateFreshness(envelope, config, cache):
  now ← currentTimestamp()
  ts ← envelope.ts
  nonce ← envelope.nonce

  // Check age
  IF (now - ts) > config.windowMs:
    RETURN false  // Too old
  END IF

  // Check future timestamp
  IF (ts - now) > config.skewMs:
    RETURN false  // Too far in future
  END IF

  // Check duplicate
  IF cache.has(nonce):
    RETURN false  // Replay attack
  END IF

  // Add to cache
  expiresAt ← ts + config.windowMs
  cache.set(nonce, expiresAt)

  RETURN true
END FUNCTION
```

**Complexity**: O(1) with hash-based cache  
**Time**: <1ms

### 4.6 Nonce Cache Management Algorithm

```typescript
/**
 * LRU cache for nonce storage with automatic expiration
 *
 * Data Structure:
 * - Map: nonce → expiresAt
 * - Doubly-linked list for LRU ordering
 *
 * Operations:
 * - set(nonce, expiresAt): O(1)
 * - has(nonce): O(1)
 * - evict(): O(1) per eviction
 * - cleanup(): O(n) where n = expired entries
 *
 * Eviction Policy:
 * 1. Automatic: When cache exceeds maxCacheSize
 * 2. Expiration: When nonce timestamp exceeds expiresAt
 * 3. LRU: Least recently used nonces evicted first
 */
class NonceCache {
  private cache: Map<string, number>;
  private maxSize: number;

  constructor(maxSize: number = 10000) {
    this.cache = new Map();
    this.maxSize = maxSize;
  }

  /**
   * Add nonce to cache with expiration
   * O(1) time complexity
   */
  set(nonce: string, expiresAt: number): void {
    // Evict if cache is full
    if (this.cache.size >= this.maxSize) {
      this.evictOldest();
    }

    this.cache.set(nonce, expiresAt);
  }

  /**
   * Check if nonce exists in cache
   * O(1) time complexity
   */
  has(nonce: string): boolean {
    const expiresAt = this.cache.get(nonce);
    if (expiresAt === undefined) {
      return false;
    }

    // Check if expired
    if (Date.now() > expiresAt) {
      this.cache.delete(nonce);
      return false;
    }

    return true;
  }

  /**
   * Evict oldest nonce (LRU)
   * O(1) time complexity
   */
  private evictOldest(): void {
    const firstKey = this.cache.keys().next().value;
    if (firstKey) {
      this.cache.delete(firstKey);
    }
  }

  /**
   * Clean up expired nonces
   * O(n) time complexity where n = cache size
   */
  cleanup(): void {
    const now = Date.now();
    for (const [nonce, expiresAt] of this.cache.entries()) {
      if (now > expiresAt) {
        this.cache.delete(nonce);
      }
    }
  }
}
```

**Pseudocode**:

```
CLASS NonceCache:
  cache: Map<string, number>
  maxSize: number

  FUNCTION set(nonce, expiresAt):
    IF cache.size >= maxSize:
      evictOldest()
    END IF
    cache[nonce] ← expiresAt
  END FUNCTION

  FUNCTION has(nonce):
    expiresAt ← cache[nonce]
    IF expiresAt is NULL:
      RETURN false
    END IF

    IF currentTime() > expiresAt:
      cache.delete(nonce)
      RETURN false
    END IF

    RETURN true
  END FUNCTION

  FUNCTION evictOldest():
    firstKey ← cache.keys().first()
    cache.delete(firstKey)
  END FUNCTION

  FUNCTION cleanup():
    now ← currentTime()
    FOR EACH (nonce, expiresAt) IN cache:
      IF now > expiresAt:
        cache.delete(nonce)
      END IF
    END FOR
  END FUNCTION
END CLASS
```

**Memory**: O(n) where n = maxCacheSize  
**Typical**: 10K nonces × 50 bytes = 500KB

---

## 5. API Specifications

### 5.1 TypeScript Public API

#### 5.1.1 signRoundtable()

````typescript
/**
 * Create and sign an RWP v2.1 multi-signature envelope
 *
 * This is the primary function for creating secure agent-to-agent messages.
 * It generates a complete envelope with timestamp, nonce, and multi-tongue
 * signatures.
 *
 * @template T - Payload type (must be JSON-serializable)
 *
 * @param envelope - Envelope structure without signatures
 * @param envelope.primary_tongue - Primary intent domain
 * @param envelope.aad - Additional authenticated data (metadata)
 * @param envelope.payload - Payload object (will be JSON-encoded)
 *
 * @param keyring - Keyring with HMAC keys for each tongue
 * @param signingTongues - List of tongues to sign with (1-6)
 * @param options - Optional configuration
 * @param options.kid - Key ID for key rotation
 * @param options.timestamp - Custom timestamp (for testing)
 * @param options.nonce - Custom nonce (for testing)
 *
 * @returns Complete signed envelope
 *
 * @throws {Error} If keyring is missing required keys
 * @throws {Error} If payload is not JSON-serializable
 * @throws {Error} If signingTongues is empty
 *
 * @example
 * ```typescript
 * const keyring = createKeyring({
 *   ko: Buffer.from('...'),
 *   ru: Buffer.from('...'),
 * });
 *
 * const envelope = signRoundtable(
 *   {
 *     ver: "2.1",
 *     primary_tongue: 'ko',
 *     aad: 'task-assignment',
 *     ts: Date.now(),
 *     nonce: generateNonce(),
 *     payload: base64url.encode(JSON.stringify({ task: 'analyze' })),
 *   },
 *   keyring,
 *   ['ko', 'ru'],
 *   { kid: 'v1' }
 * );
 * ```
 *
 * Time Complexity: O(k × n) where k = tongues, n = envelope size
 * Space Complexity: O(n)
 * Performance: <10ms for typical envelope
 */
export function signRoundtable<T = any>(
  envelope: Omit<RWP2MultiEnvelope<T>, 'sigs'>,
  keyring: Keyring,
  signingTongues: TongueID[],
  options?: EnvelopeOptions
): RWP2MultiEnvelope<T>;
````

#### 5.1.2 verifyRoundtable()

````typescript
/**
 * Verify an RWP v2.1 multi-signature envelope
 *
 * This function performs complete verification including:
 * 1. Replay protection (timestamp + nonce validation)
 * 2. Signature verification (HMAC-SHA256)
 * 3. Returns list of valid tongues
 *
 * @param envelope - Envelope to verify
 * @param keyring - Keyring with HMAC keys for verification
 * @param config - Optional replay protection configuration
 *
 * @returns Verification result with valid tongues and decoded payload
 *
 * @throws {Error} If envelope format is invalid
 * @throws {Error} If replay attack detected
 *
 * @example
 * ```typescript
 * const result = verifyRoundtable(envelope, keyring, {
 *   windowMs: 300000,  // 5 minutes
 *   skewMs: 60000,     // 1 minute
 * });
 *
 * if (result.success) {
 *   console.log('Valid tongues:', result.validTongues);
 *   console.log('Payload:', result.payload);
 * } else {
 *   console.error('Verification failed:', result.error);
 * }
 * ```
 *
 * Time Complexity: O(k × n) where k = signatures, n = envelope size
 * Space Complexity: O(n)
 * Performance: <5ms for typical envelope
 */
export function verifyRoundtable(
  envelope: RWP2MultiEnvelope,
  keyring: Keyring,
  config?: Partial<ReplayConfig>
): VerificationResult;
````

#### 5.1.3 enforceRoundtablePolicy()

````typescript
/**
 * Enforce policy requirements on verified tongues
 *
 * Checks if the verified tongues satisfy the required policy level.
 *
 * Policy Levels:
 * - standard: Any valid signature (no specific requirements)
 * - strict: Requires RU (Policy) tongue
 * - secret: Requires UM (Security) tongue
 * - critical: Requires RU + UM + DR (Policy + Security + Structure)
 *
 * @param validTongues - List of tongues with valid signatures
 * @param policy - Policy level to enforce
 *
 * @returns Policy enforcement result
 *
 * @example
 * ```typescript
 * const result = verifyRoundtable(envelope, keyring);
 * const policyResult = enforceRoundtablePolicy(
 *   result.validTongues,
 *   'critical'
 * );
 *
 * if (!policyResult.satisfied) {
 *   console.error('Missing tongues:', policyResult.missing);
 * }
 * ```
 *
 * Time Complexity: O(r × p) where r = required, p = present
 * Space Complexity: O(1)
 * Performance: <1ms
 */
export function enforceRoundtablePolicy(
  validTongues: TongueID[],
  policy: PolicyLevel
): PolicyResult;
````

#### 5.1.4 createKeyring()

````typescript
/**
 * Create a keyring for multi-tongue authentication
 *
 * Generates or loads HMAC keys for each Sacred Tongue.
 * Keys must be 32 bytes (256 bits) for HMAC-SHA256.
 *
 * @param keys - Map of tongue → 32-byte key
 * @param options - Optional keyring configuration
 * @param options.id - Keyring identifier
 * @param options.version - Key version for rotation
 * @param options.expiresAt - Expiration timestamp
 *
 * @returns Keyring object
 *
 * @throws {Error} If any key is not 32 bytes
 *
 * @example
 * ```typescript
 * // Generate random keys
 * const keyring = createKeyring({
 *   ko: crypto.randomBytes(32),
 *   av: crypto.randomBytes(32),
 *   ru: crypto.randomBytes(32),
 *   ca: crypto.randomBytes(32),
 *   um: crypto.randomBytes(32),
 *   dr: crypto.randomBytes(32),
 * }, {
 *   id: 'production-v1',
 *   version: 'v1',
 *   expiresAt: Date.now() + 30 * 24 * 60 * 60 * 1000, // 30 days
 * });
 *
 * // Load from secure storage
 * const keyring = createKeyring({
 *   ko: Buffer.from(process.env.KO_KEY, 'hex'),
 *   ru: Buffer.from(process.env.RU_KEY, 'hex'),
 *   um: Buffer.from(process.env.UM_KEY, 'hex'),
 * });
 * ```
 *
 * Time Complexity: O(k) where k = number of keys
 * Space Complexity: O(k)
 * Performance: <1ms
 */
export function createKeyring(
  keys: Partial<Record<TongueID, Buffer>>,
  options?: {
    id?: string;
    version?: string;
    expiresAt?: number;
  }
): Keyring;
````

#### 5.1.5 generateNonce()

````typescript
/**
 * Generate cryptographically random nonce
 *
 * Uses crypto.randomBytes() for secure random generation.
 * Nonce is 16 bytes (128 bits) encoded as Base64URL.
 *
 * @returns Base64URL-encoded nonce
 *
 * @example
 * ```typescript
 * const nonce = generateNonce();
 * // Example: "xK7j9mP2qR8vL4nT6wY1zA"
 * ```
 *
 * Time Complexity: O(1)
 * Space Complexity: O(1)
 * Performance: <1ms
 */
export function generateNonce(): string;
````

#### 5.1.6 encodePayload()

````typescript
/**
 * Encode payload to Base64URL JSON
 *
 * Serializes payload to JSON and encodes to Base64URL.
 *
 * @template T - Payload type
 * @param payload - Payload object (must be JSON-serializable)
 *
 * @returns Base64URL-encoded JSON string
 *
 * @throws {Error} If payload is not JSON-serializable
 *
 * @example
 * ```typescript
 * const encoded = encodePayload({ task: 'analyze', priority: 'high' });
 * // Example: "eyJ0YXNrIjoiYW5hbHl6ZSIsInByaW9yaXR5IjoiaGlnaCJ9"
 * ```
 *
 * Time Complexity: O(n) where n = payload size
 * Space Complexity: O(n)
 * Performance: <1ms for typical payload
 */
export function encodePayload<T>(payload: T): string;
````

#### 5.1.7 decodePayload()

````typescript
/**
 * Decode Base64URL JSON payload
 *
 * Decodes Base64URL string and parses JSON.
 *
 * @template T - Expected payload type
 * @param encoded - Base64URL-encoded JSON string
 *
 * @returns Decoded payload object
 *
 * @throws {Error} If decoding or parsing fails
 *
 * @example
 * ```typescript
 * const payload = decodePayload<{ task: string }>(encoded);
 * console.log(payload.task); // "analyze"
 * ```
 *
 * Time Complexity: O(n) where n = encoded size
 * Space Complexity: O(n)
 * Performance: <1ms for typical payload
 */
export function decodePayload<T>(encoded: string): T;
````

### 5.2 Python Public API

#### 5.2.1 sign_roundtable()

```python
def sign_roundtable(
    envelope: Dict[str, Any],
    keyring: Keyring,
    signing_tongues: List[TongueID],
    options: Optional[EnvelopeOptions] = None
) -> RWP2MultiEnvelope:
    """
    Create and sign an RWP v2.1 multi-signature envelope

    This is the primary function for creating secure agent-to-agent messages.
    It generates a complete envelope with timestamp, nonce, and multi-tongue
    signatures.

    Args:
        envelope: Envelope structure without signatures
            - primary_tongue: Primary intent domain
            - aad: Additional authenticated data (metadata)
            - payload: Payload object (will be JSON-encoded)
        keyring: Keyring with HMAC keys for each tongue
        signing_tongues: List of tongues to sign with (1-6)
        options: Optional configuration
            - kid: Key ID for key rotation
            - timestamp: Custom timestamp (for testing)
            - nonce: Custom nonce (for testing)

    Returns:
        Complete signed envelope

    Raises:
        ValueError: If keyring is missing required keys
        ValueError: If payload is not JSON-serializable
        ValueError: If signing_tongues is empty

    Example:
        >>> keyring = create_keyring({
        ...     'ko': os.urandom(32),
        ...     'ru': os.urandom(32),
        ... })
        >>>
        >>> envelope = sign_roundtable(
        ...     {
        ...         'ver': '2.1',
        ...         'primary_tongue': 'ko',
        ...         'aad': 'task-assignment',
        ...         'ts': int(time.time() * 1000),
        ...         'nonce': generate_nonce(),
        ...         'payload': encode_payload({'task': 'analyze'}),
        ...     },
        ...     keyring,
        ...     ['ko', 'ru'],
        ...     EnvelopeOptions(kid='v1')
        ... )

    Time Complexity: O(k × n) where k = tongues, n = envelope size
    Space Complexity: O(n)
    Performance: <10ms for typical envelope
    """
```

#### 5.2.2 verify_roundtable()

```python
def verify_roundtable(
    envelope: RWP2MultiEnvelope,
    keyring: Keyring,
    config: Optional[ReplayConfig] = None
) -> VerificationResult:
    """
    Verify an RWP v2.1 multi-signature envelope

    This function performs complete verification including:
    1. Replay protection (timestamp + nonce validation)
    2. Signature verification (HMAC-SHA256)
    3. Returns list of valid tongues

    Args:
        envelope: Envelope to verify
        keyring: Keyring with HMAC keys for verification
        config: Optional replay protection configuration

    Returns:
        Verification result with valid tongues and decoded payload

    Raises:
        ValueError: If envelope format is invalid
        ValueError: If replay attack detected

    Example:
        >>> result = verify_roundtable(envelope, keyring, ReplayConfig(
        ...     window_ms=300000,  # 5 minutes
        ...     skew_ms=60000,     # 1 minute
        ... ))
        >>>
        >>> if result.success:
        ...     print('Valid tongues:', result.valid_tongues)
        ...     print('Payload:', result.payload)
        ... else:
        ...     print('Verification failed:', result.error)

    Time Complexity: O(k × n) where k = signatures, n = envelope size
    Space Complexity: O(n)
    Performance: <5ms for typical envelope
    """
```

#### 5.2.3 enforce_roundtable_policy()

```python
def enforce_roundtable_policy(
    valid_tongues: List[TongueID],
    policy: PolicyLevel
) -> PolicyResult:
    """
    Enforce policy requirements on verified tongues

    Checks if the verified tongues satisfy the required policy level.

    Policy Levels:
        - standard: Any valid signature (no specific requirements)
        - strict: Requires RU (Policy) tongue
        - secret: Requires UM (Security) tongue
        - critical: Requires RU + UM + DR (Policy + Security + Structure)

    Args:
        valid_tongues: List of tongues with valid signatures
        policy: Policy level to enforce

    Returns:
        Policy enforcement result

    Example:
        >>> result = verify_roundtable(envelope, keyring)
        >>> policy_result = enforce_roundtable_policy(
        ...     result.valid_tongues,
        ...     'critical'
        ... )
        >>>
        >>> if not policy_result.satisfied:
        ...     print('Missing tongues:', policy_result.missing)

    Time Complexity: O(r × p) where r = required, p = present
    Space Complexity: O(1)
    Performance: <1ms
    """
```

### 5.3 Error Handling

#### 5.3.1 Error Types

```typescript
/**
 * Base error class for RWP v2.1
 */
export class RWPError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'RWPError';
  }
}

/**
 * Signature verification failed
 */
export class SignatureError extends RWPError {
  constructor(message: string) {
    super(message);
    this.name = 'SignatureError';
  }
}

/**
 * Policy enforcement failed
 */
export class PolicyError extends RWPError {
  constructor(
    message: string,
    public readonly required: TongueID[],
    public readonly present: TongueID[]
  ) {
    super(message);
    this.name = 'PolicyError';
  }
}

/**
 * Replay attack detected
 */
export class ReplayError extends RWPError {
  constructor(message: string) {
    super(message);
    this.name = 'ReplayError';
  }
}

/**
 * Keyring error (missing or invalid keys)
 */
export class KeyringError extends RWPError {
  constructor(message: string) {
    super(message);
    this.name = 'KeyringError';
  }
}

/**
 * Envelope format error
 */
export class EnvelopeError extends RWPError {
  constructor(message: string) {
    super(message);
    this.name = 'EnvelopeError';
  }
}
```

#### 5.3.2 Error Messages

```typescript
/**
 * Standard error messages
 */
export const ERROR_MESSAGES = {
  // Signature errors
  SIGNATURE_INVALID: 'Signature verification failed',
  SIGNATURE_MISSING: 'Required signature missing',

  // Policy errors
  POLICY_NOT_SATISFIED: 'Policy requirements not satisfied',
  POLICY_MISSING_TONGUES: 'Missing required tongues: {tongues}',

  // Replay errors
  REPLAY_TIMESTAMP_OLD: 'Envelope timestamp too old',
  REPLAY_TIMESTAMP_FUTURE: 'Envelope timestamp too far in future',
  REPLAY_NONCE_DUPLICATE: 'Duplicate nonce detected (replay attack)',

  // Keyring errors
  KEYRING_KEY_MISSING: 'Missing key for tongue: {tongue}',
  KEYRING_KEY_INVALID: 'Invalid key size (expected 32 bytes)',
  KEYRING_EXPIRED: 'Keyring has expired',

  // Envelope errors
  ENVELOPE_INVALID_FORMAT: 'Invalid envelope format',
  ENVELOPE_MISSING_FIELD: 'Missing required field: {field}',
  ENVELOPE_INVALID_VERSION: 'Invalid protocol version (expected 2.1)',
  ENVELOPE_PAYLOAD_INVALID: 'Invalid payload encoding',
} as const;
```

---

## 6. Security Design

### 6.1 Threat Model

#### 6.1.1 Adversary Capabilities

**A1: Network Adversary**

- Can intercept messages
- Can replay messages
- Can modify messages in transit
- Cannot break HMAC-SHA256
- Cannot guess 256-bit keys

**A2: Compromised Agent**

- Has valid keys for some tongues
- Can create valid signatures for owned tongues
- Cannot forge signatures for other tongues
- Cannot bypass policy enforcement

**A3: Timing Adversary**

- Can measure signature verification time
- Cannot extract keys from timing information (constant-time comparison)

**A4: Memory Adversary**

- Can read process memory
- Cannot extract keys from secure storage
- Cannot bypass key rotation

#### 6.1.2 Security Goals

**G1: Authentication** - Only agents with valid keys can create signatures

**G2: Integrity** - Any modification to envelope invalidates signatures

**G3: Replay Protection** - Old messages cannot be reused

**G4: Domain Separation** - Each tongue has independent cryptographic identity

**G5: Policy Enforcement** - Critical operations require multi-tongue consensus

**G6: Fail-to-Noise** - Invalid operations don't leak information

### 6.2 Security Properties

#### 6.2.1 Cryptographic Properties

**P1: HMAC-SHA256 Security**

```
Theorem: HMAC-SHA256 is existentially unforgeable under chosen-message attack
Proof: Follows from SHA-256 collision resistance and HMAC construction
Security Level: 256 bits (2^256 operations to forge)
```

**P2: Domain Separation**

```
Theorem: Signatures from different tongues are cryptographically independent
Proof: Each tongue uses independent 256-bit key
       Pr[forge tongue A | know key B] = 2^-256
```

**P3: Replay Protection**

```
Theorem: Probability of successful replay attack is negligible
Proof: Nonce space = 2^128 (16 bytes)
       Collision probability after n nonces: n^2 / 2^129
       For n = 10^9: Pr[collision] ≈ 2^-69 (negligible)
```

**P4: Timing Safety**

```
Theorem: Signature verification is constant-time
Proof: Uses crypto.timingSafeEqual() for comparison
       Time complexity independent of signature content
```

#### 6.2.2 Protocol Properties

**P5: Multi-Signature Security**

```
Theorem: k-of-n multi-signature requires k valid keys
Proof: Each signature verified independently
       Pr[forge k signatures] = (2^-256)^k = 2^(-256k)
       For k=3: Pr[forge] = 2^-768 (infeasible)
```

**P6: Policy Enforcement**

```
Theorem: Critical policy requires RU + UM + DR signatures
Proof: Policy matrix enforced after verification
       Missing any required tongue → policy violation
       Attacker must compromise all 3 keys
```

**P7: Freshness Guarantee**

```
Theorem: Accepted envelopes are at most W milliseconds old
Proof: Timestamp validation: now - ts ≤ W
       Where W = replay window (default 300,000ms = 5 minutes)
```

### 6.3 Attack Resistance

#### 6.3.1 Replay Attack Resistance

**Attack**: Adversary captures valid envelope and resends it

**Defense**:

1. Timestamp validation (envelope must be fresh)
2. Nonce cache (duplicate nonces rejected)
3. Configurable replay window (default 5 minutes)

**Security Analysis**:

```
Pr[successful replay] = Pr[nonce collision] + Pr[timestamp valid]
                      ≈ 2^-128 + 0 (after window expires)
                      ≈ 2^-128 (negligible)
```

#### 6.3.2 Forgery Attack Resistance

**Attack**: Adversary attempts to forge signature without key

**Defense**:

1. HMAC-SHA256 with 256-bit keys
2. Constant-time comparison
3. Independent keys per tongue

**Security Analysis**:

```
Pr[forge single signature] = 2^-256 (brute force)
Pr[forge k signatures] = 2^(-256k)
For critical policy (k=3): 2^-768 operations (infeasible)
```

#### 6.3.3 Modification Attack Resistance

**Attack**: Adversary modifies envelope fields

**Defense**:

1. All fields included in canonical string
2. HMAC covers entire envelope
3. Any modification invalidates signature

**Security Analysis**:

```
Modified envelope → different canonical string
                  → different HMAC output
                  → signature verification fails
Pr[valid signature after modification] = 2^-256
```

#### 6.3.4 Timing Attack Resistance

**Attack**: Adversary measures verification time to extract key bits

**Defense**:

1. Constant-time comparison (crypto.timingSafeEqual)
2. Fixed-time HMAC computation
3. No early exit on mismatch

**Security Analysis**:

```
Verification time = T_hmac + T_compare
T_compare = constant (independent of signature)
Information leaked = 0 bits
```

#### 6.3.5 Key Compromise Resistance

**Attack**: Adversary compromises one tongue's key

**Defense**:

1. Domain separation (independent keys)
2. Policy enforcement (requires multiple tongues)
3. Key rotation support

**Security Analysis**:

```
Compromised keys: 1 of 6
Critical policy requires: 3 of 6 (RU + UM + DR)
Attacker must compromise: 2 additional keys
Pr[compromise 3 keys] = (Pr[compromise 1])^3
```

### 6.4 Key Management Security

#### 6.4.1 Key Generation

```typescript
/**
 * Generate cryptographically secure key
 *
 * Requirements:
 * - 256 bits (32 bytes) of entropy
 * - Cryptographically secure random source
 * - Unique per tongue
 */
function generateKey(): Buffer {
  return crypto.randomBytes(32);
}
```

**Security**: Uses OS-provided CSPRNG (cryptographically secure pseudo-random number generator)

#### 6.4.2 Key Storage

```typescript
/**
 * Secure key storage recommendations
 *
 * Production:
 * - AWS Secrets Manager
 * - HashiCorp Vault
 * - Azure Key Vault
 * - Google Cloud KMS
 *
 * Development:
 * - Environment variables (encrypted)
 * - .env files (gitignored)
 * - Local keychain
 *
 * Never:
 * - Hardcoded in source
 * - Committed to git
 * - Stored in plaintext
 */
```

#### 6.4.3 Key Rotation

```typescript
/**
 * Key rotation strategy
 *
 * 1. Generate new key with new kid (key ID)
 * 2. Deploy new key to all agents
 * 3. Start signing with new key
 * 4. Keep old key for verification (grace period)
 * 5. After grace period, remove old key
 *
 * Recommended rotation frequency: Monthly
 * Grace period: 2× replay window (10 minutes)
 */
interface KeyRotationPlan {
  currentKid: string;
  newKid: string;
  rotationDate: number;
  gracePeriodMs: number;
}
```

### 6.5 Fail-to-Noise Design

#### 6.5.1 Principle

**Goal**: Invalid operations return noise, not error details

**Rationale**: Prevents information leakage to attackers

**Implementation**:

```typescript
/**
 * Fail-to-noise verification
 *
 * Invalid signature → returns empty validTongues list
 * Does NOT reveal:
 * - Which signature failed
 * - Why signature failed
 * - Which key was used
 * - Timing information
 */
function verifySignatures(envelope: RWP2MultiEnvelope, keyring: Keyring): TongueID[] {
  const validTongues: TongueID[] = [];

  for (const [tongue, signature] of Object.entries(envelope.sigs)) {
    const key = keyring.keys[tongue as TongueID];
    if (!key) {
      continue; // Silent failure
    }

    const valid = verifySignature(envelope, key, tongue as TongueID);
    if (valid) {
      validTongues.push(tongue as TongueID);
    }
    // No error on invalid signature
  }

  return validTongues; // May be empty
}
```

#### 6.5.2 Error Handling

```typescript
/**
 * Public API error handling
 *
 * Internal errors (for debugging):
 * - Logged to secure audit log
 * - Include full details
 * - Never exposed to caller
 *
 * External errors (for caller):
 * - Generic error messages
 * - No sensitive information
 * - Actionable guidance
 */

// Internal logging (secure)
logger.error('Signature verification failed', {
  tongue: 'ko',
  reason: 'HMAC mismatch',
  envelope_id: envelope.nonce,
  timestamp: Date.now(),
});

// External error (generic)
throw new SignatureError('Signature verification failed');
// Does NOT reveal which tongue or why
```

### 6.6 Compliance and Standards

#### 6.6.1 Cryptographic Standards

**NIST FIPS 180-4**: SHA-256 specification  
**RFC 2104**: HMAC specification  
**RFC 4648**: Base64URL encoding

#### 6.6.2 Security Best Practices

**OWASP Top 10**: Addressed

- A02:2021 – Cryptographic Failures: ✅ HMAC-SHA256, 256-bit keys
- A04:2021 – Insecure Design: ✅ Threat model, security properties
- A07:2021 – Identification and Authentication Failures: ✅ Multi-signature

**NIST Cybersecurity Framework**: Aligned

- Identify: ✅ Threat model documented
- Protect: ✅ HMAC-SHA256, domain separation
- Detect: ✅ Replay detection, audit logging
- Respond: ✅ Key rotation, incident response
- Recover: ✅ Key rotation, grace periods

---

## 7. Performance Design

### 7.1 Performance Requirements

**PR-7.1.1**: Envelope creation: <10ms (p95)  
**PR-7.1.2**: Envelope verification: <5ms (p95)  
**PR-7.1.3**: Policy enforcement: <1ms (p95)  
**PR-7.1.4**: Nonce cache lookup: <1ms (p95)  
**PR-7.1.5**: Throughput: 1000+ envelopes/second  
**PR-7.1.6**: Memory: <100MB for 10K cached nonces

### 7.2 Performance Analysis

#### 7.2.1 Envelope Creation

```
Operation Breakdown:
1. Generate nonce: 0.1ms (crypto.randomBytes)
2. Get timestamp: 0.01ms (Date.now)
3. Encode payload: 0.5ms (JSON + Base64URL)
4. Sign with k tongues: k × 1ms (HMAC-SHA256)
5. Serialize envelope: 0.2ms (JSON.stringify)

Total: 0.81ms + k × 1ms
For k=6: 6.81ms ✅ (< 10ms requirement)
```

**Optimization Opportunities**:

- Parallel signing (reduce to max(1ms) instead of sum)
- Payload caching (skip re-encoding)
- Nonce pre-generation (amortize cost)

#### 7.2.2 Envelope Verification

```
Operation Breakdown:
1. Parse envelope: 0.2ms (JSON.parse)
2. Validate timestamp: 0.01ms (comparison)
3. Check nonce cache: 0.5ms (Map lookup)
4. Verify k signatures: k × 0.8ms (HMAC + compare)
5. Decode payload: 0.3ms (Base64URL + JSON)

Total: 1.01ms + k × 0.8ms
For k=6: 5.81ms ✅ (< 5ms requirement with optimization)
```

**Optimization Opportunities**:

- Parallel verification (reduce to max(0.8ms))
- Early exit on policy check (skip unnecessary verifications)
- Signature caching (for repeated verification)

#### 7.2.3 Throughput Analysis

```
Single-threaded:
- Creation: 6.81ms → 147 envelopes/second
- Verification: 5.81ms → 172 envelopes/second

Multi-threaded (8 cores):
- Creation: 147 × 8 = 1,176 envelopes/second ✅
- Verification: 172 × 8 = 1,376 envelopes/second ✅

With parallel signing/verification:
- Creation: 2ms → 500 × 8 = 4,000 envelopes/second
- Verification: 1.5ms → 667 × 8 = 5,336 envelopes/second
```

### 7.3 Memory Analysis

#### 7.3.1 Envelope Size

```
Envelope Structure:
- ver: 4 bytes ("2.1")
- primary_tongue: 2 bytes ("ko")
- aad: variable (typically 50 bytes)
- ts: 13 bytes (Unix milliseconds)
- nonce: 24 bytes (Base64URL of 16 bytes)
- payload: variable (typically 1KB)
- sigs: 6 × 44 bytes = 264 bytes (Base64URL of 32 bytes)
- kid: 10 bytes (optional)

Total: ~1.4KB per envelope (typical)
```

#### 7.3.2 Nonce Cache Memory

```
Cache Entry:
- nonce: 24 bytes (string)
- expiresAt: 8 bytes (number)
- Map overhead: ~20 bytes

Total: ~52 bytes per entry

For 10K entries: 52 × 10,000 = 520KB ✅ (< 100MB requirement)
```

#### 7.3.3 Keyring Memory

```
Keyring:
- id: 20 bytes (string)
- keys: 6 × 32 bytes = 192 bytes
- version: 10 bytes (string)
- expiresAt: 8 bytes (number)

Total: ~230 bytes per keyring

For 100 keyrings: 230 × 100 = 23KB (negligible)
```

### 7.4 Optimization Strategies

#### 7.4.1 Parallel Signing

```typescript
/**
 * Sign envelope with multiple tongues in parallel
 *
 * Reduces time from O(k) to O(1) where k = number of tongues
 */
async function signRoundtableParallel<T>(
  envelope: Omit<RWP2MultiEnvelope<T>, 'sigs'>,
  keyring: Keyring,
  signingTongues: TongueID[]
): Promise<RWP2MultiEnvelope<T>> {
  const signaturePromises = signingTongues.map(async (tongue) => {
    const key = keyring.keys[tongue];
    if (!key) {
      throw new Error(`Missing key for tongue: ${tongue}`);
    }
    const signature = await generateSignatureAsync(envelope, key, tongue);
    return [tongue, signature] as const;
  });

  const signatures = await Promise.all(signaturePromises);
  const sigs = Object.fromEntries(signatures);

  return { ...envelope, sigs };
}
```

**Performance Gain**: 6.81ms → 2ms (3.4× faster)

#### 7.4.2 Signature Caching

```typescript
/**
 * Cache verified signatures to avoid re-verification
 *
 * Use case: Same envelope verified multiple times
 * Cache key: envelope.nonce (unique per envelope)
 */
class SignatureCache {
  private cache: Map<string, TongueID[]>;

  get(nonce: string): TongueID[] | undefined {
    return this.cache.get(nonce);
  }

  set(nonce: string, validTongues: TongueID[]): void {
    this.cache.set(nonce, validTongues);
  }
}
```

**Performance Gain**: 5.81ms → 0.5ms (11.6× faster for cached)

#### 7.4.3 Nonce Pre-generation

```typescript
/**
 * Pre-generate nonces in background
 *
 * Amortizes crypto.randomBytes cost across multiple envelopes
 */
class NoncePool {
  private pool: string[] = [];
  private readonly poolSize = 100;

  constructor() {
    this.refill();
  }

  get(): string {
    if (this.pool.length < 10) {
      this.refill();
    }
    return this.pool.pop()!;
  }

  private refill(): void {
    for (let i = 0; i < this.poolSize; i++) {
      this.pool.push(generateNonce());
    }
  }
}
```

**Performance Gain**: Amortizes 0.1ms cost across 100 envelopes

---

## 8. Error Handling

### 8.1 Error Hierarchy

```
RWPError (base)
├── SignatureError
│   ├── SignatureInvalidError
│   ├── SignatureMissingError
│   └── SignatureFormatError
├── PolicyError
│   ├── PolicyNotSatisfiedError
│   ├── PolicyMissingTonguesError
│   └── PolicyUnknownLevelError
├── ReplayError
│   ├── ReplayTimestampOldError
│   ├── ReplayTimestampFutureError
│   └── ReplayNonceDuplicateError
├── KeyringError
│   ├── KeyringKeyMissingError
│   ├── KeyringKeyInvalidError
│   └── KeyringExpiredError
└── EnvelopeError
    ├── EnvelopeInvalidFormatError
    ├── EnvelopeMissingFieldError
    ├── EnvelopeInvalidVersionError
    └── EnvelopePayloadInvalidError
```

### 8.2 Error Handling Strategies

#### 8.2.1 Fail-Fast vs. Fail-Safe

**Fail-Fast** (for development/debugging):

```typescript
// Throw immediately on error
function signRoundtable(...) {
  if (!keyring.keys[tongue]) {
    throw new KeyringKeyMissingError(`Missing key for tongue: ${tongue}`);
  }
  // ...
}
```

**Fail-Safe** (for production):

```typescript
// Return error result instead of throwing
function signRoundtable(...): Result<RWP2MultiEnvelope, RWPError> {
  if (!keyring.keys[tongue]) {
    return Err(new KeyringKeyMissingError(`Missing key for tongue: ${tongue}`));
  }
  // ...
  return Ok(envelope);
}
```

#### 8.2.2 Error Recovery

```typescript
/**
 * Retry strategy for transient errors
 */
async function signRoundtableWithRetry(
  envelope: Omit<RWP2MultiEnvelope, 'sigs'>,
  keyring: Keyring,
  signingTongues: TongueID[],
  options?: { maxRetries?: number; retryDelayMs?: number }
): Promise<RWP2MultiEnvelope> {
  const maxRetries = options?.maxRetries ?? 3;
  const retryDelayMs = options?.retryDelayMs ?? 100;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await signRoundtable(envelope, keyring, signingTongues);
    } catch (error) {
      if (attempt === maxRetries) {
        throw error; // Final attempt failed
      }

      // Only retry transient errors
      if (error instanceof KeyringError || error instanceof EnvelopeError) {
        await sleep(retryDelayMs * Math.pow(2, attempt)); // Exponential backoff
      } else {
        throw error; // Don't retry non-transient errors
      }
    }
  }
}
```

#### 8.2.3 Error Logging

```typescript
/**
 * Structured error logging
 */
interface ErrorLog {
  timestamp: number;
  level: 'error' | 'warn' | 'info';
  errorType: string;
  message: string;
  context: Record<string, any>;
  stackTrace?: string;
}

function logError(error: RWPError, context: Record<string, any>): void {
  const log: ErrorLog = {
    timestamp: Date.now(),
    level: 'error',
    errorType: error.name,
    message: error.message,
    context: {
      ...context,
      // Redact sensitive information
      keyring: context.keyring ? '[REDACTED]' : undefined,
      envelope: context.envelope
        ? {
            ver: context.envelope.ver,
            primary_tongue: context.envelope.primary_tongue,
            ts: context.envelope.ts,
            // Redact payload and signatures
          }
        : undefined,
    },
    stackTrace: error.stack,
  };

  // Send to secure logging service
  secureLogger.log(log);
}
```

### 8.3 Validation and Sanitization

#### 8.3.1 Input Validation

```typescript
/**
 * Validate envelope structure
 */
function validateEnvelope(envelope: any): envelope is RWP2MultiEnvelope {
  // Check required fields
  if (typeof envelope !== 'object' || envelope === null) {
    throw new EnvelopeInvalidFormatError('Envelope must be an object');
  }

  if (envelope.ver !== '2.1') {
    throw new EnvelopeInvalidVersionError('Invalid protocol version');
  }

  if (!isValidTongueID(envelope.primary_tongue)) {
    throw new EnvelopeMissingFieldError('Invalid primary_tongue');
  }

  if (typeof envelope.aad !== 'string') {
    throw new EnvelopeMissingFieldError('Missing or invalid aad');
  }

  if (typeof envelope.ts !== 'number' || envelope.ts <= 0) {
    throw new EnvelopeMissingFieldError('Missing or invalid timestamp');
  }

  if (typeof envelope.nonce !== 'string' || envelope.nonce.length === 0) {
    throw new EnvelopeMissingFieldError('Missing or invalid nonce');
  }

  if (typeof envelope.payload !== 'string') {
    throw new EnvelopeMissingFieldError('Missing or invalid payload');
  }

  if (typeof envelope.sigs !== 'object' || envelope.sigs === null) {
    throw new EnvelopeMissingFieldError('Missing or invalid sigs');
  }

  return true;
}
```

#### 8.3.2 Key Validation

```typescript
/**
 * Validate keyring keys
 */
function validateKeyring(keyring: Keyring): void {
  if (!keyring.id || typeof keyring.id !== 'string') {
    throw new KeyringError('Invalid keyring ID');
  }

  if (!keyring.keys || typeof keyring.keys !== 'object') {
    throw new KeyringError('Invalid keyring keys');
  }

  for (const [tongue, key] of Object.entries(keyring.keys)) {
    if (!isValidTongueID(tongue)) {
      throw new KeyringError(`Invalid tongue ID: ${tongue}`);
    }

    if (!Buffer.isBuffer(key) || key.length !== 32) {
      throw new KeyringKeyInvalidError(`Invalid key size for ${tongue} (expected 32 bytes)`);
    }
  }

  // Check expiration
  if (keyring.expiresAt && Date.now() > keyring.expiresAt) {
    throw new KeyringExpiredError('Keyring has expired');
  }
}
```

#### 8.3.3 Sanitization

```typescript
/**
 * Sanitize envelope for logging
 */
function sanitizeEnvelope(envelope: RWP2MultiEnvelope): any {
  return {
    ver: envelope.ver,
    primary_tongue: envelope.primary_tongue,
    aad: envelope.aad,
    ts: envelope.ts,
    nonce: envelope.nonce.substring(0, 8) + '...', // Truncate nonce
    payload: '[REDACTED]', // Never log payload
    sigs: Object.keys(envelope.sigs), // Only log which tongues signed
    kid: envelope.kid,
  };
}
```

---

## 9. Testing Strategy

### 9.1 Test Pyramid

```
                    ┌─────────────┐
                    │   E2E Tests │  (10%)
                    │   5 tests   │
                    └─────────────┘
                  ┌───────────────────┐
                  │ Integration Tests │  (20%)
                  │    20 tests       │
                  └───────────────────┘
              ┌─────────────────────────────┐
              │      Unit Tests             │  (70%)
              │      100+ tests             │
              └─────────────────────────────┘
```

### 9.2 Unit Tests

#### 9.2.1 Signature Generation Tests

```typescript
describe('generateSignature', () => {
  it('should generate valid HMAC-SHA256 signature', () => {
    const envelope = createTestEnvelope();
    const key = Buffer.from('a'.repeat(64), 'hex');
    const signature = generateSignature(envelope, key, 'ko');

    expect(signature).toMatch(/^[A-Za-z0-9_-]{43}$/); // Base64URL, 32 bytes
  });

  it('should be deterministic for same inputs', () => {
    const envelope = createTestEnvelope();
    const key = Buffer.from('a'.repeat(64), 'hex');

    const sig1 = generateSignature(envelope, key, 'ko');
    const sig2 = generateSignature(envelope, key, 'ko');

    expect(sig1).toBe(sig2);
  });

  it('should differ for different keys', () => {
    const envelope = createTestEnvelope();
    const key1 = Buffer.from('a'.repeat(64), 'hex');
    const key2 = Buffer.from('b'.repeat(64), 'hex');

    const sig1 = generateSignature(envelope, key1, 'ko');
    const sig2 = generateSignature(envelope, key2, 'ko');

    expect(sig1).not.toBe(sig2);
  });

  it('should differ for different envelope fields', () => {
    const envelope1 = createTestEnvelope({ aad: 'test1' });
    const envelope2 = createTestEnvelope({ aad: 'test2' });
    const key = Buffer.from('a'.repeat(64), 'hex');

    const sig1 = generateSignature(envelope1, key, 'ko');
    const sig2 = generateSignature(envelope2, key, 'ko');

    expect(sig1).not.toBe(sig2);
  });
});
```

#### 9.2.2 Verification Tests

```typescript
describe('verifySignatures', () => {
  it('should verify valid signatures', () => {
    const keyring = createTestKeyring();
    const envelope = signRoundtable(createTestEnvelope(), keyring, ['ko', 'ru']);

    const validTongues = verifySignatures(envelope, keyring);

    expect(validTongues).toEqual(['ko', 'ru']);
  });

  it('should reject invalid signatures', () => {
    const keyring = createTestKeyring();
    const envelope = signRoundtable(createTestEnvelope(), keyring, ['ko']);

    // Tamper with signature
    envelope.sigs.ko = 'invalid-signature';

    const validTongues = verifySignatures(envelope, keyring);

    expect(validTongues).toEqual([]);
  });

  it('should reject modified envelope', () => {
    const keyring = createTestKeyring();
    const envelope = signRoundtable(createTestEnvelope(), keyring, ['ko']);

    // Modify envelope
    envelope.aad = 'modified';

    const validTongues = verifySignatures(envelope, keyring);

    expect(validTongues).toEqual([]);
  });
});
```

#### 9.2.3 Policy Enforcement Tests

```typescript
describe('enforceRoundtablePolicy', () => {
  it('should satisfy standard policy with any signature', () => {
    const result = enforceRoundtablePolicy(['ko'], 'standard');
    expect(result.satisfied).toBe(true);
  });

  it('should satisfy strict policy with RU', () => {
    const result = enforceRoundtablePolicy(['ko', 'ru'], 'strict');
    expect(result.satisfied).toBe(true);
  });

  it('should not satisfy strict policy without RU', () => {
    const result = enforceRoundtablePolicy(['ko'], 'strict');
    expect(result.satisfied).toBe(false);
    expect(result.missing).toEqual(['ru']);
  });

  it('should satisfy critical policy with RU+UM+DR', () => {
    const result = enforceRoundtablePolicy(['ru', 'um', 'dr'], 'critical');
    expect(result.satisfied).toBe(true);
  });

  it('should not satisfy critical policy with partial signatures', () => {
    const result = enforceRoundtablePolicy(['ru', 'um'], 'critical');
    expect(result.satisfied).toBe(false);
    expect(result.missing).toEqual(['dr']);
  });
});
```

#### 9.2.4 Replay Protection Tests

```typescript
describe('validateFreshness', () => {
  let cache: NonceCache;

  beforeEach(() => {
    cache = new NonceCache();
  });

  it('should accept fresh envelope', () => {
    const envelope = createTestEnvelope({ ts: Date.now() });
    const config = DEFAULT_REPLAY_CONFIG;

    const result = validateFreshness(envelope, config, cache);

    expect(result).toBe(true);
  });

  it('should reject old envelope', () => {
    const envelope = createTestEnvelope({
      ts: Date.now() - 400000, // 6.67 minutes ago
    });
    const config = DEFAULT_REPLAY_CONFIG; // 5 minute window

    const result = validateFreshness(envelope, config, cache);

    expect(result).toBe(false);
  });

  it('should reject future envelope', () => {
    const envelope = createTestEnvelope({
      ts: Date.now() + 120000, // 2 minutes in future
    });
    const config = DEFAULT_REPLAY_CONFIG; // 1 minute skew tolerance

    const result = validateFreshness(envelope, config, cache);

    expect(result).toBe(false);
  });

  it('should reject duplicate nonce', () => {
    const envelope = createTestEnvelope();
    const config = DEFAULT_REPLAY_CONFIG;

    // First attempt should succeed
    expect(validateFreshness(envelope, config, cache)).toBe(true);

    // Second attempt should fail (replay attack)
    expect(validateFreshness(envelope, config, cache)).toBe(false);
  });
});
```

### 9.3 Property-Based Tests

#### 9.3.1 Signature Properties

```typescript
import fc from 'fast-check';

describe('Signature Properties', () => {
  // Property 1: Signature is deterministic
  it('Property 1: Same inputs produce same signature', () => {
    fc.assert(
      fc.property(
        fc.record({
          aad: fc.string(),
          ts: fc.integer({ min: 0 }),
          nonce: fc.string({ minLength: 16, maxLength: 32 }),
          payload: fc.string(),
        }),
        fc.hexaString({ minLength: 64, maxLength: 64 }),
        (envelopeData, keyHex) => {
          const envelope = createEnvelope(envelopeData);
          const key = Buffer.from(keyHex, 'hex');

          const sig1 = generateSignature(envelope, key, 'ko');
          const sig2 = generateSignature(envelope, key, 'ko');

          return sig1 === sig2;
        }
      ),
      { numRuns: 100 }
    );
  });

  // Property 2: Different keys produce different signatures
  it('Property 2: Different keys produce different signatures', () => {
    fc.assert(
      fc.property(
        fc.record({
          aad: fc.string(),
          ts: fc.integer({ min: 0 }),
          nonce: fc.string({ minLength: 16, maxLength: 32 }),
          payload: fc.string(),
        }),
        fc.hexaString({ minLength: 64, maxLength: 64 }),
        fc.hexaString({ minLength: 64, maxLength: 64 }),
        (envelopeData, keyHex1, keyHex2) => {
          fc.pre(keyHex1 !== keyHex2); // Precondition: keys are different

          const envelope = createEnvelope(envelopeData);
          const key1 = Buffer.from(keyHex1, 'hex');
          const key2 = Buffer.from(keyHex2, 'hex');

          const sig1 = generateSignature(envelope, key1, 'ko');
          const sig2 = generateSignature(envelope, key2, 'ko');

          return sig1 !== sig2;
        }
      ),
      { numRuns: 100 }
    );
  });

  // Property 3: Signature verification is inverse of signing
  it('Property 3: Verify(Sign(envelope, key), key) = true', () => {
    fc.assert(
      fc.property(
        fc.record({
          aad: fc.string(),
          ts: fc.integer({ min: 0 }),
          nonce: fc.string({ minLength: 16, maxLength: 32 }),
          payload: fc.string(),
        }),
        fc.hexaString({ minLength: 64, maxLength: 64 }),
        (envelopeData, keyHex) => {
          const envelope = createEnvelope(envelopeData);
          const key = Buffer.from(keyHex, 'hex');
          const keyring = createKeyring({ ko: key });

          const signed = signRoundtable(envelope, keyring, ['ko']);
          const validTongues = verifySignatures(signed, keyring);

          return validTongues.includes('ko');
        }
      ),
      { numRuns: 100 }
    );
  });

  // Property 4: Modified envelope fails verification
  it('Property 4: Verify(Modify(Sign(envelope)), key) = false', () => {
    fc.assert(
      fc.property(
        fc.record({
          aad: fc.string(),
          ts: fc.integer({ min: 0 }),
          nonce: fc.string({ minLength: 16, maxLength: 32 }),
          payload: fc.string(),
        }),
        fc.hexaString({ minLength: 64, maxLength: 64 }),
        fc.string(),
        (envelopeData, keyHex, newAad) => {
          fc.pre(envelopeData.aad !== newAad); // Precondition: modification

          const envelope = createEnvelope(envelopeData);
          const key = Buffer.from(keyHex, 'hex');
          const keyring = createKeyring({ ko: key });

          const signed = signRoundtable(envelope, keyring, ['ko']);
          signed.aad = newAad; // Modify envelope

          const validTongues = verifySignatures(signed, keyring);

          return !validTongues.includes('ko');
        }
      ),
      { numRuns: 100 }
    );
  });
});
```

#### 9.3.2 Policy Properties

```typescript
describe('Policy Properties', () => {
  // Property 5: Standard policy always satisfied with any signature
  it('Property 5: Standard policy accepts any valid signature', () => {
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom('ko', 'av', 'ru', 'ca', 'um', 'dr'), {
          minLength: 1,
          maxLength: 6,
        }),
        (tongues) => {
          const result = enforceRoundtablePolicy(tongues as TongueID[], 'standard');
          return result.satisfied;
        }
      ),
      { numRuns: 100 }
    );
  });

  // Property 6: Critical policy requires RU+UM+DR
  it('Property 6: Critical policy requires RU+UM+DR', () => {
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom('ko', 'av', 'ru', 'ca', 'um', 'dr'), {
          minLength: 0,
          maxLength: 6,
        }),
        (tongues) => {
          const result = enforceRoundtablePolicy(tongues as TongueID[], 'critical');
          const hasRequired =
            tongues.includes('ru') && tongues.includes('um') && tongues.includes('dr');
          return result.satisfied === hasRequired;
        }
      ),
      { numRuns: 100 }
    );
  });
});
```

### 9.4 Integration Tests

#### 9.4.1 End-to-End Flow

```typescript
describe('End-to-End Flow', () => {
  it('should create, sign, verify, and enforce policy', () => {
    // Setup
    const keyring = createKeyring({
      ko: crypto.randomBytes(32),
      ru: crypto.randomBytes(32),
      um: crypto.randomBytes(32),
      dr: crypto.randomBytes(32),
    });

    // Create envelope
    const envelope = {
      ver: '2.1' as const,
      primary_tongue: 'ko' as const,
      aad: 'test-message',
      ts: Date.now(),
      nonce: generateNonce(),
      payload: encodePayload({ message: 'Hello, World!' }),
    };

    // Sign with multiple tongues
    const signed = signRoundtable(envelope, keyring, ['ko', 'ru', 'um', 'dr']);

    // Verify signatures
    const result = verifyRoundtable(signed, keyring);
    expect(result.success).toBe(true);
    expect(result.validTongues).toEqual(['ko', 'ru', 'um', 'dr']);

    // Enforce critical policy
    const policyResult = enforceRoundtablePolicy(result.validTongues, 'critical');
    expect(policyResult.satisfied).toBe(true);

    // Decode payload
    expect(result.payload).toEqual({ message: 'Hello, World!' });
  });
});
```

#### 9.4.2 TypeScript ↔ Python Interop

```typescript
describe('TypeScript ↔ Python Interoperability', () => {
  it('should verify Python-created envelope in TypeScript', async () => {
    // Python creates and signs envelope
    const pythonEnvelope = await execPython(`
from spiralverse import sign_roundtable, create_keyring
import json

keyring = create_keyring({'ko': b'a' * 32})
envelope = sign_roundtable({
    'ver': '2.1',
    'primary_tongue': 'ko',
    'aad': 'test',
    'ts': 1234567890,
    'nonce': 'test-nonce',
    'payload': 'eyJ0ZXN0IjoidmFsdWUifQ',
}, keyring, ['ko'])

print(json.dumps(envelope))
    `);

    // TypeScript verifies
    const keyring = createKeyring({ ko: Buffer.from('a'.repeat(32)) });
    const result = verifyRoundtable(JSON.parse(pythonEnvelope), keyring);

    expect(result.success).toBe(true);
    expect(result.validTongues).toEqual(['ko']);
  });

  it('should verify TypeScript-created envelope in Python', async () => {
    // TypeScript creates and signs envelope
    const keyring = createKeyring({ ko: Buffer.from('a'.repeat(32)) });
    const envelope = signRoundtable(
      {
        ver: '2.1',
        primary_tongue: 'ko',
        aad: 'test',
        ts: 1234567890,
        nonce: 'test-nonce',
        payload: 'eyJ0ZXN0IjoidmFsdWUifQ',
      },
      keyring,
      ['ko']
    );

    // Python verifies
    const pythonResult = await execPython(`
from spiralverse import verify_roundtable, create_keyring
import json

envelope = json.loads('${JSON.stringify(envelope)}')
keyring = create_keyring({'ko': b'a' * 32})
result = verify_roundtable(envelope, keyring)

print(json.dumps({'success': result.success, 'valid_tongues': result.valid_tongues}))
    `);

    const result = JSON.parse(pythonResult);
    expect(result.success).toBe(true);
    expect(result.valid_tongues).toEqual(['ko']);
  });
});
```

### 9.5 Performance Tests

```typescript
describe('Performance Tests', () => {
  it('should create envelope in <10ms', () => {
    const keyring = createTestKeyring();
    const envelope = createTestEnvelope();

    const start = performance.now();
    signRoundtable(envelope, keyring, ['ko', 'av', 'ru', 'ca', 'um', 'dr']);
    const duration = performance.now() - start;

    expect(duration).toBeLessThan(10);
  });

  it('should verify envelope in <5ms', () => {
    const keyring = createTestKeyring();
    const envelope = signRoundtable(createTestEnvelope(), keyring, [
      'ko',
      'av',
      'ru',
      'ca',
      'um',
      'dr',
    ]);

    const start = performance.now();
    verifyRoundtable(envelope, keyring);
    const duration = performance.now() - start;

    expect(duration).toBeLessThan(5);
  });

  it('should handle 1000 envelopes/second', async () => {
    const keyring = createTestKeyring();
    const count = 1000;

    const start = performance.now();
    for (let i = 0; i < count; i++) {
      const envelope = signRoundtable(createTestEnvelope(), keyring, ['ko']);
      verifyRoundtable(envelope, keyring);
    }
    const duration = performance.now() - start;

    const throughput = (count / duration) * 1000; // envelopes/second
    expect(throughput).toBeGreaterThan(1000);
  });
});
```

### 9.6 Security Tests

```typescript
describe('Security Tests', () => {
  it('should prevent replay attacks', () => {
    const keyring = createTestKeyring();
    const envelope = signRoundtable(createTestEnvelope(), keyring, ['ko']);

    // First verification should succeed
    const result1 = verifyRoundtable(envelope, keyring);
    expect(result1.success).toBe(true);

    // Second verification should fail (replay attack)
    expect(() => verifyRoundtable(envelope, keyring)).toThrow(ReplayError);
  });

  it('should reject tampered envelopes', () => {
    const keyring = createTestKeyring();
    const envelope = signRoundtable(createTestEnvelope(), keyring, ['ko']);

    // Tamper with payload
    envelope.payload = encodePayload({ malicious: 'data' });

    const result = verifyRoundtable(envelope, keyring);
    expect(result.success).toBe(false);
  });

  it('should use constant-time comparison', () => {
    const keyring = createTestKeyring();
    const envelope = signRoundtable(createTestEnvelope(), keyring, ['ko']);

    // Measure verification time for valid signature
    const times1: number[] = [];
    for (let i = 0; i < 100; i++) {
      const start = performance.now();
      verifySignatures(envelope, keyring);
      times1.push(performance.now() - start);
    }

    // Tamper and measure verification time for invalid signature
    envelope.sigs.ko = 'invalid-signature';
    const times2: number[] = [];
    for (let i = 0; i < 100; i++) {
      const start = performance.now();
      verifySignatures(envelope, keyring);
      times2.push(performance.now() - start);
    }

    // Times should be similar (constant-time)
    const avg1 = times1.reduce((a, b) => a + b) / times1.length;
    const avg2 = times2.reduce((a, b) => a + b) / times2.length;
    const diff = Math.abs(avg1 - avg2);

    expect(diff).toBeLessThan(0.1); // <0.1ms difference
  });
});
```
