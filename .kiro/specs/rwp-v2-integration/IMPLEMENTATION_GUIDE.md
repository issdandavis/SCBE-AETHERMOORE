# RWP v2.1 Implementation Guide

**Date**: January 18, 2026  
**Purpose**: Step-by-step guide for implementing RWP v2.1 from rigorous requirements  
**Prerequisites**: Read `requirements-v2.1-rigorous.md` and `RIGOROUS_REVIEW_RESPONSE.md`

---

## Phase 1: Pre-Implementation Decisions

### Step 1.1: Accept or Choose Defaults

Review the 3 decision points and document your choices:

| Decision | Default | Your Choice | Rationale |
|----------|---------|-------------|-----------|
| Build Output | Option 1 (dual CJS+ESM) | _________ | _________ |
| Signing String | Option A (canonical JSON) | _________ | _________ |
| Nonce Scope | Option B (tongue only) | _________ | _________ |

**Recommendation**: Accept all defaults unless you have specific constraints.

### Step 1.2: Select Libraries

#### TypeScript Libraries
```json
{
  "dependencies": {
    "canonicalize": "^2.0.0",  // RFC 8785 JSON canonicalization
    // OR implement custom per RFC 8785
  }
}
```

#### Python Libraries
```python
# requirements.txt
canonicaljson==2.0.0  # RFC 8785 JSON canonicalization
# OR implement custom per RFC 8785
```

### Step 1.3: Document Decisions

Create `IMPLEMENTATION_DECISIONS.md`:
```markdown
# RWP v2.1 Implementation Decisions

**Date**: YYYY-MM-DD
**Team**: [Your Team]

## Decision 1: Build Output
**Choice**: Option 1 (dual CJS+ESM)
**Rationale**: Modern ecosystem compatibility, tree-shaking support

## Decision 2: Signing String Construction
**Choice**: Option A (canonical JSON of envelope-without-sigs)
**Rationale**: Consistent with JSON-first design, easier to maintain

## Decision 3: Nonce Scope
**Choice**: Option B (primary_tongue only)
**Rationale**: Simpler implementation, sender identity not available in MVP

## RFC 8785 Library
**TypeScript**: canonicalize npm package
**Python**: canonicaljson pip package
```

---

## Phase 2: Generate Test Vectors

### Step 2.1: Implement Key Derivation

```typescript
// TypeScript
import { createHmac } from 'crypto';

function deriveTongueKey(masterKey: Buffer, tongueId: string): Buffer {
  return createHmac('sha256', masterKey)
    .update(`tongue:${tongueId}`)
    .digest();
}
```

```python
# Python
import hmac
import hashlib

def derive_tongue_key(master_key: bytes, tongue_id: str) -> bytes:
    return hmac.new(
        master_key,
        f"tongue:{tongue_id}".encode('utf-8'),
        hashlib.sha256
    ).digest()
```

### Step 2.2: Implement Canonical Signing String

**If you chose Option A** (canonical JSON):
```typescript
// TypeScript
import canonicalize from 'canonicalize';

function buildSigningString(envelope: Envelope): string {
  const signObject = {
    ver: envelope.ver,
    primary_tongue: envelope.primary_tongue,
    kid: envelope.kid,
    ts: envelope.ts,
    nonce: envelope.nonce,
    ...(envelope.aad && { aad: envelope.aad }),
    payload: envelope.payload
  };
  return canonicalize(signObject) || '';
}
```

```python
# Python
import canonicaljson

def build_signing_string(envelope: dict) -> bytes:
    sign_object = {
        'ver': envelope['ver'],
        'primary_tongue': envelope['primary_tongue'],
        'kid': envelope['kid'],
        'ts': envelope['ts'],
        'nonce': envelope['nonce'],
        'payload': envelope['payload']
    }
    if 'aad' in envelope:
        sign_object['aad'] = envelope['aad']
    return canonicaljson.encode_canonical_json(sign_object)
```

**If you chose Option B** (pipe-delimited):
```typescript
// TypeScript
import canonicalize from 'canonicalize';

function buildSigningString(envelope: Envelope): string {
  const canonicalAad = envelope.aad ? canonicalize(envelope.aad) : '';
  return [
    envelope.ver,
    envelope.primary_tongue,
    canonicalAad,
    envelope.ts.toString(),
    envelope.nonce,
    envelope.payload
  ].join('|');
}
```

### Step 2.3: Generate Signatures for Test Vectors

```typescript
// TypeScript
import { createHmac } from 'crypto';

function generateSignature(tongueKey: Buffer, canonicalString: string): string {
  return createHmac('sha256', tongueKey)
    .update(canonicalString, 'utf-8')
    .digest('hex');
}
```

```python
# Python
import hmac
import hashlib

def generate_signature(tongue_key: bytes, canonical_string: bytes) -> str:
    return hmac.new(
        tongue_key,
        canonical_string,
        hashlib.sha256
    ).hexdigest()
```

### Step 2.4: Fill in TEST_VECTORS.json

Run your key derivation and signature generation for each test vector:

```typescript
// generate-test-vectors.ts
import fs from 'fs';

const masterKey = Buffer.from('0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef', 'hex');
const vectors = JSON.parse(fs.readFileSync('TEST_VECTORS.json', 'utf-8'));

for (const vector of vectors.vectors) {
  const canonicalString = buildSigningString(vector.envelope);
  vector.expected_canonical_string = canonicalString;
  
  vector.expected_sigs = {};
  for (const tongue of Object.keys(vector.envelope.kid)) {
    const tongueKey = deriveTongueKey(masterKey, tongue);
    vector.expected_sigs[tongue] = generateSignature(tongueKey, canonicalString);
  }
}

fs.writeFileSync('TEST_VECTORS_COMPLETE.json', JSON.stringify(vectors, null, 2));
```

### Step 2.5: Verify Cross-Language Consistency

```bash
# Generate from TypeScript
npm run generate-test-vectors

# Generate from Python
python generate_test_vectors.py

# Compare outputs
diff TEST_VECTORS_TS.json TEST_VECTORS_PY.json
# Should be identical!
```

---

## Phase 3: Implement Core Components

### Step 3.1: Envelope Builder

```typescript
// TypeScript: envelope-builder.ts
import { randomBytes } from 'crypto';

export interface Envelope {
  ver: string;
  primary_tongue: string;
  kid: Record<string, string>;
  ts: number;
  nonce: string;
  aad?: Record<string, any>;
  payload: string;
  sigs: Record<string, string>;
}

export class EnvelopeBuilder {
  private masterKey: Buffer;
  
  constructor(masterKey: Buffer) {
    this.masterKey = masterKey;
  }
  
  build(
    primaryTongue: string,
    tongues: string[],
    payload: Buffer,
    aad?: Record<string, any>
  ): Envelope {
    // Generate nonce (16 bytes minimum)
    const nonce = randomBytes(16).toString('base64url');
    
    // Build kid map
    const kid: Record<string, string> = {};
    for (const tongue of tongues) {
      kid[tongue] = `key-${Date.now()}`; // Replace with actual key ID lookup
    }
    
    // Build envelope without sigs
    const envelope: Partial<Envelope> = {
      ver: '2.1',
      primary_tongue: primaryTongue,
      kid,
      ts: Date.now(),
      nonce,
      ...(aad && { aad }),
      payload: payload.toString('base64url')
    };
    
    // Generate canonical signing string
    const canonicalString = buildSigningString(envelope as Envelope);
    
    // Generate signatures
    const sigs: Record<string, string> = {};
    for (const tongue of tongues) {
      const tongueKey = deriveTongueKey(this.masterKey, tongue);
      sigs[tongue] = generateSignature(tongueKey, canonicalString);
    }
    
    return { ...envelope, sigs } as Envelope;
  }
}
```

### Step 3.2: Envelope Verifier

```typescript
// TypeScript: envelope-verifier.ts
import { timingSafeEqual } from 'crypto';

export enum VerificationResult {
  ALLOW = 'ALLOW',
  DENY = 'DENY',
  QUARANTINE = 'QUARANTINE'
}

export class EnvelopeVerifier {
  private masterKey: Buffer;
  private nonceCache: Set<string>;
  private replayWindow: number = 60_000; // 60 seconds
  private clockSkew: number = 5_000; // 5 seconds
  
  constructor(masterKey: Buffer) {
    this.masterKey = masterKey;
    this.nonceCache = new Set();
  }
  
  verify(envelope: Envelope, policyMode: string): VerificationResult {
    // Step 1: Validate timestamp
    const now = Date.now();
    if (envelope.ts > now + this.clockSkew) {
      return VerificationResult.DENY; // Future timestamp
    }
    if (envelope.ts < now - this.replayWindow) {
      return VerificationResult.DENY; // Expired timestamp
    }
    
    // Step 2: Build canonical signing string
    const canonicalString = buildSigningString(envelope);
    
    // Step 3: Verify signatures (constant-time)
    const validTongues: string[] = [];
    for (const [tongue, receivedSig] of Object.entries(envelope.sigs)) {
      const tongueKey = deriveTongueKey(this.masterKey, tongue);
      const expectedSig = generateSignature(tongueKey, canonicalString);
      
      // Constant-time comparison
      const receivedBuf = Buffer.from(receivedSig, 'hex');
      const expectedBuf = Buffer.from(expectedSig, 'hex');
      
      if (receivedBuf.length === expectedBuf.length && 
          timingSafeEqual(receivedBuf, expectedBuf)) {
        validTongues.push(tongue);
      }
    }
    
    // Step 4: Check primary tongue
    if (!validTongues.includes(envelope.primary_tongue)) {
      return VerificationResult.DENY;
    }
    
    // Step 5: Check nonce replay (atomic check-and-insert)
    const nonceKey = `${envelope.primary_tongue}:${envelope.nonce}`;
    if (this.nonceCache.has(nonceKey)) {
      return VerificationResult.DENY; // Replay detected
    }
    this.nonceCache.add(nonceKey); // Record nonce BEFORE policy check
    
    // Step 6: Evaluate policy
    const requiredCount = {
      'STANDARD': 1,
      'STRICT': 2,
      'SECRET': 3,
      'CRITICAL': 6
    }[policyMode] || 1;
    
    if (validTongues.length >= requiredCount) {
      return VerificationResult.ALLOW;
    } else {
      return VerificationResult.QUARANTINE;
    }
  }
}
```

### Step 3.3: Python Implementation

```python
# Python: envelope_verifier.py
import hmac
import hashlib
import time
from enum import Enum
from typing import Dict, List, Optional

class VerificationResult(Enum):
    ALLOW = 'ALLOW'
    DENY = 'DENY'
    QUARANTINE = 'QUARANTINE'

class EnvelopeVerifier:
    def __init__(self, master_key: bytes):
        self.master_key = master_key
        self.nonce_cache: set = set()
        self.replay_window = 60_000  # 60 seconds
        self.clock_skew = 5_000  # 5 seconds
    
    def verify(self, envelope: dict, policy_mode: str) -> VerificationResult:
        # Step 1: Validate timestamp
        now = int(time.time() * 1000)
        if envelope['ts'] > now + self.clock_skew:
            return VerificationResult.DENY
        if envelope['ts'] < now - self.replay_window:
            return VerificationResult.DENY
        
        # Step 2: Build canonical signing string
        canonical_string = build_signing_string(envelope)
        
        # Step 3: Verify signatures (constant-time)
        valid_tongues = []
        for tongue, received_sig in envelope['sigs'].items():
            tongue_key = derive_tongue_key(self.master_key, tongue)
            expected_sig = generate_signature(tongue_key, canonical_string)
            
            # Constant-time comparison
            if hmac.compare_digest(received_sig, expected_sig):
                valid_tongues.append(tongue)
        
        # Step 4: Check primary tongue
        if envelope['primary_tongue'] not in valid_tongues:
            return VerificationResult.DENY
        
        # Step 5: Check nonce replay
        nonce_key = f"{envelope['primary_tongue']}:{envelope['nonce']}"
        if nonce_key in self.nonce_cache:
            return VerificationResult.DENY
        self.nonce_cache.add(nonce_key)
        
        # Step 6: Evaluate policy
        required_count = {
            'STANDARD': 1,
            'STRICT': 2,
            'SECRET': 3,
            'CRITICAL': 6
        }.get(policy_mode, 1)
        
        if len(valid_tongues) >= required_count:
            return VerificationResult.ALLOW
        else:
            return VerificationResult.QUARANTINE
```

---

## Phase 4: Testing

### Step 4.1: Unit Tests

```typescript
// TypeScript: envelope.test.ts
import { describe, it, expect } from 'vitest';
import { EnvelopeBuilder, EnvelopeVerifier, VerificationResult } from './envelope';

describe('RWP v2.1 Envelope', () => {
  const masterKey = Buffer.from('0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef', 'hex');
  
  it('should create and verify valid envelope', () => {
    const builder = new EnvelopeBuilder(masterKey);
    const verifier = new EnvelopeVerifier(masterKey);
    
    const envelope = builder.build('RU', ['RU'], Buffer.from('Hello World'));
    const result = verifier.verify(envelope, 'STANDARD');
    
    expect(result).toBe(VerificationResult.ALLOW);
  });
  
  it('should reject replayed nonce', () => {
    const builder = new EnvelopeBuilder(masterKey);
    const verifier = new EnvelopeVerifier(masterKey);
    
    const envelope = builder.build('RU', ['RU'], Buffer.from('Hello World'));
    
    const result1 = verifier.verify(envelope, 'STANDARD');
    expect(result1).toBe(VerificationResult.ALLOW);
    
    const result2 = verifier.verify(envelope, 'STANDARD');
    expect(result2).toBe(VerificationResult.DENY); // Replay detected
  });
});
```

### Step 4.2: Interop Tests

```typescript
// TypeScript: interop.test.ts
import { describe, it, expect } from 'vitest';
import fs from 'fs';

describe('RWP v2.1 Interop Test Vectors', () => {
  const vectors = JSON.parse(fs.readFileSync('TEST_VECTORS_COMPLETE.json', 'utf-8'));
  
  for (const vector of vectors.vectors) {
    it(`should pass ${vector.test_id}: ${vector.description}`, () => {
      const masterKey = Buffer.from(vector.master_key, 'hex');
      const verifier = new EnvelopeVerifier(masterKey);
      
      const result = verifier.verify(vector.envelope, 'STANDARD');
      expect(result).toBe(vector.expected_result);
    });
  }
});
```

### Step 4.3: Cross-Language Interop

```bash
# Test TypeScript creates, Python verifies
npm run test:interop:ts-to-py

# Test Python creates, TypeScript verifies
npm run test:interop:py-to-ts
```

---

## Phase 5: Documentation

### Step 5.1: API Documentation

Generate API docs from code:
```bash
# TypeScript
npm run docs  # Uses TypeDoc

# Python
pdoc --html envelope_verifier.py
```

### Step 5.2: Usage Examples

Create `examples/` directory with:
- `basic-usage.ts` / `basic_usage.py`
- `multi-signature.ts` / `multi_signature.py`
- `policy-modes.ts` / `policy_modes.py`

### Step 5.3: Migration Guide

If upgrading from v2.0, create `MIGRATION_v2.0_to_v2.1.md`

---

## Phase 6: Deployment Checklist

Before deploying to production:

- [ ] All 10 interop test vectors pass (both directions)
- [ ] Property-based tests run (100+ iterations)
- [ ] Performance benchmarks meet NFR-1 requirements
- [ ] Constant-time comparison verified (no timing leaks)
- [ ] Nonce cache eviction tested (LRU behavior)
- [ ] Error responses are indistinguishable (no info leakage)
- [ ] Audit logging implemented (internal only)
- [ ] Key rotation procedure documented
- [ ] Monitoring and alerting configured

---

## Troubleshooting

### Issue: Signatures don't match across languages

**Cause**: Canonicalization differences

**Fix**:
1. Print canonical signing string from both implementations
2. Compare byte-for-byte (use hex dump)
3. Check RFC 8785 number formatting
4. Verify nested object handling

### Issue: Nonce replay not detected

**Cause**: Cache not persisting or scope incorrect

**Fix**:
1. Verify nonce is recorded after crypto passes
2. Check scope key format matches FR-5.1
3. Ensure atomic check-and-insert

### Issue: Performance below NFR-1 targets

**Cause**: Inefficient canonicalization or crypto

**Fix**:
1. Profile with `perf` (Linux) or `Instruments` (macOS)
2. Cache derived tongue keys if master key doesn't change
3. Use native crypto libraries (not pure JS/Python)

---

## Next Steps

1. Complete Phase 1 (decisions)
2. Generate test vectors (Phase 2)
3. Implement core components (Phase 3)
4. Run all tests (Phase 4)
5. Deploy to staging (Phase 6)

---

**Version**: 2.1.0  
**Status**: Implementation Guide Complete ✅  
**Last Updated**: January 18, 2026
