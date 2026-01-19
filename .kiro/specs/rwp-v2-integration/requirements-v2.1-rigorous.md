# RWP v2.1 Requirements - Rigorous Specification

**Feature**: RWP v2.1 Multi-Signature Envelope Protocol  
**Version**: 2.1.0  
**Status**: Requirements Complete - Ready for Implementation  
**Last Updated**: January 18, 2026

---

## 1. Context and Scope

### 1.1 What This Document Covers

RWP v2.1 is a **multi-signature envelope protocol** using HMAC-SHA256 for message authentication across multiple "Sacred Tongues" (trust domains). This document specifies:

- Envelope format and serialization
- HMAC-SHA256 signature generation and verification
- Multi-signature policy enforcement
- Replay protection with nonce management
- Cross-language interoperability (TypeScript ↔ Python)

### 1.2 What This Document Does NOT Cover

- ❌ Post-quantum cryptography (ML-KEM, ML-DSA) - **Future enhancement (v3.0+)**
- ❌ Dual-channel audio verification - **Separate system (see HARMONIC_VERIFICATION_SPEC.md)**
- ❌ Quantum key distribution - **Hardware-dependent future work**
- ❌ Dimensional flux ODE - **Layer 2 integration (separate spec)**

### 1.3 Current Implementation Status

- ✅ **v2.1.0**: HMAC-SHA256 multi-signatures (this spec)
- ⚠️ **v3.0**: PQC upgrade with ML-DSA planned (Q2 2026)
- ⚠️ **v3.1**: Hybrid classical+PQC planned (Q3 2026)

---

## 2. Functional Requirements

### FR-1: Envelope Structure

#### FR-1.1: Envelope Schema

The envelope MUST conform to this exact JSON schema:

```json
{
  "ver": "2.1",
  "primary_tongue": "RU",
  "kid": {
    "RU": "ru-2026-01",
    "UM": "um-2026-01",
    "DR": "dr-2026-01"
  },
  "ts": 1737161234567,
  "nonce": "base64url(16+ bytes, no padding)",
  "aad": {
    "action": "execute",
    "mode": "STRICT",
    "priority": 1
  },
  "payload": "base64url(bytes, no padding)",
  "sigs": {
    "RU": "hex(64 bytes)",
    "UM": "hex(64 bytes)",
    "DR": "hex(64 bytes)"
  }
}
```

**Rationale**: Fixed schema enables interop testing and prevents ambiguity.

#### FR-1.2: Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ver` | string | YES | Protocol version (exactly "2.1") |
| `primary_tongue` | string | YES | Primary Sacred Tongue (KO, AV, RU, CA, UM, DR) |
| `kid` | object | YES | Per-tongue key identifiers (map: tongue → key_id) |
| `ts` | integer | YES | Unix timestamp in milliseconds (UTC) |
| `nonce` | string | YES | Base64URL-encoded random bytes (≥16 bytes, no padding) |
| `aad` | object | NO | Additional authenticated data (canonicalized for signing) |
| `payload` | string | YES | Base64URL-encoded payload bytes (no padding) |
| `sigs` | object | YES | Per-tongue HMAC-SHA256 signatures (map: tongue → hex_sig) |

#### FR-1.3: Sacred Tongues

Valid tongue identifiers (case-sensitive):

- `KO` - Koraelin (base tongue, weight 1.0)
- `AV` - Avali (harmonic 1, weight 1.125)
- `RU` - Runethic (harmonic 2, weight 1.25)
- `CA` - Cassisivadan (harmonic 3, weight 1.333)
- `UM` - Umbroth (harmonic 4, weight 1.5)
- `DR` - Draumric (harmonic 5, weight 1.667)

**Constraint**: `primary_tongue` MUST be one of these six values.

---

### FR-2: Canonicalization (CRITICAL FOR INTEROP)

#### FR-2.1: AAD Canonicalization

**Problem**: TypeScript and Python produce different JSON bytes unless canonicalization is defined.

**Solution**: AAD MUST be serialized using **JSON Canonicalization Scheme (RFC 8785)** prior to signing.

**Requirements**:
- Keys MUST be sorted lexicographically (Unicode code point order)
- No whitespace between tokens
- Numbers MUST be serialized per RFC 8785 (minimal representation, no leading zeros, no trailing zeros after decimal)
- Strings MUST use minimal escaping (only `\"`, `\\`, control characters)
- No `NaN` or `Infinity` values allowed
- **AAD canonicalization MUST apply recursively to all nested objects and arrays per RFC 8785**
- If an implementation cannot guarantee RFC 8785 number formatting, it MUST reject floats or round to a fixed policy and document the deviation

**Example**:
```json
// Input (any order, whitespace):
{ "mode": "STRICT", "action": "execute", "priority": 1 }

// Canonical output (sorted, no whitespace):
{"action":"execute","mode":"STRICT","priority":1}
```

#### FR-2.2: Base64URL Encoding

**Requirements**:
- MUST use URL-safe alphabet: `A-Za-z0-9-_`
- MUST NOT include padding (`=` characters)
- MUST encode raw bytes (not hex strings)
- Decoder MUST accept only canonical form (strict mode - reject invalid characters)
- Payload MUST be raw bytes, not JSON-encoded-by-mistake

**Nonce Encoding**:
- Minimum 16 bytes, base64url encoded
- Uniqueness scope defined in FR-5.1

**Example**:
```
Input bytes:  [0x01, 0x02, 0x03, 0x04]
Base64URL:    "AQIDBA"  (no padding)
NOT:          "AQIDBA==" (padding forbidden)
```

#### FR-2.3: Canonical Signing String Construction

**What Bytes Are Signed**: The envelope object **excluding the `sigs` field**, canonicalized via RFC 8785, then serialized as a pipe-delimited string.

**Construction Algorithm**:

```
SignObject = {
  ver: envelope.ver,
  primary_tongue: envelope.primary_tongue,
  kid: envelope.kid,
  ts: envelope.ts,
  nonce: envelope.nonce,
  aad: envelope.aad,  // omit if not present
  payload: envelope.payload
}

canonical_json = RFC8785_Canonicalize(SignObject)
C = canonical_json
```

**Alternative** (explicit byte concatenation - simpler but more rigid):

```
C = ver || "|" || primary_tongue || "|" || canonical_aad || "|" || ts || "|" || nonce || "|" || payload
```

Where:
- `ver` = exactly "2.1"
- `primary_tongue` = tongue identifier (e.g., "RU")
- `canonical_aad` = RFC 8785 canonicalized JSON (or empty string if no AAD)
- `ts` = decimal integer (no leading zeros)
- `nonce` = base64url string (no padding)
- `payload` = base64url string (no padding)
- `||` = string concatenation (no separator bytes)
- `"|"` = literal pipe character (0x7C)

**Decision Required**: Choose **Option A** (recommended - canonical JSON of envelope-without-sigs) or **Option B** (explicit concatenation) before implementation.

**Example (Option B)**:
```
2.1|RU|{"action":"execute","mode":"STRICT"}|1737161234567|AQIDBA|SGVsbG8gV29ybGQ
```

---

### FR-3: Signature Generation

#### FR-3.1: Per-Tongue Key Derivation

Each tongue has an independent master key:

```
k_tongue = HMAC-SHA256(k_master, "tongue:" || tongue_id)
```

Where:
- `k_master` = 256-bit master secret (32 bytes)
- `tongue_id` = tongue identifier (e.g., "RU")
- Output = 256-bit derived key (32 bytes)

**Rationale**: Domain separation prevents key reuse attacks.

#### FR-3.2: HMAC-SHA256 Signature

For each tongue in the envelope:

```
sig_tongue = HMAC-SHA256(k_tongue, C)
```

Where:
- `k_tongue` = derived key from FR-3.1
- `C` = canonical signing string from FR-2.3
- Output = 256-bit HMAC tag (32 bytes)

**Encoding**: Signatures MUST be hex-encoded (64 hex characters, lowercase).

#### FR-3.3: Primary Tongue Signature

The `primary_tongue` signature MUST always be present in `sigs` object.

**Constraint**: If `primary_tongue = "RU"`, then `sigs.RU` MUST exist.

#### FR-3.4: Multi-Signature Policy

Envelopes MAY include signatures from multiple tongues (1-6 signatures).

**Minimum**: 1 signature (primary tongue)  
**Maximum**: 6 signatures (all tongues)

---

### FR-4: Signature Verification

#### FR-4.1: Verification Algorithm

For each signature in `sigs`:

1. **Key Derivation**: Derive `k_tongue` using FR-3.1
2. **Canonical String**: Reconstruct `C` using FR-2.3
3. **HMAC Computation**: Compute `expected_sig = HMAC-SHA256(k_tongue, C)`
4. **Constant-Time Comparison**: Compare `expected_sig` with `sigs[tongue]`
5. **Result**: Mark tongue as "valid" if signatures match exactly

**CRITICAL**: Signature comparison MUST be constant-time to prevent timing attacks.

#### FR-4.2: Valid Tongues List

After verification, the system MUST produce a list of "valid tongues":

```
valid_tongues = [tongue for tongue in sigs if verify(tongue) == PASS]
```

A tongue is "valid" if and only if:
- ✅ Key exists for that tongue
- ✅ HMAC tag matches exactly (constant-time comparison)
- ✅ Key ID (`kid[tongue]`) is not expired

**Handling Unknown Keys**:
- If a tongue is present in `sigs` but no key exists for `kid[tongue]`, that tongue is marked **INVALID** (not added to `valid_tongues`)
- Verification continues for other tongues
- If `primary_tongue` has unknown key, entire envelope is **DENIED** (see FR-4.3)

#### FR-4.3: Primary Tongue Requirement

The `primary_tongue` signature MUST verify successfully.

**Constraint**: If `primary_tongue` signature fails, the entire envelope MUST be rejected (DENY).

---

### FR-5: Replay Protection

#### FR-5.1: Nonce Uniqueness Scope

Nonce uniqueness MUST be enforced per:

**Option A** (Recommended if sender identity available):
```
scope = (sender_id, primary_tongue)
```

**Option B** (Simpler, if sender identity not available):
```
scope = (primary_tongue)
```

**Rationale**: Allows same nonce across different senders or tongues, but prevents replay within scope.

**Decision Required**: Choose one scope definition before implementation. **Default: Option B** (primary_tongue only).

#### FR-5.2: Nonce Storage

**Phase 2 MVP** (current):
- In-memory LRU cache with TTL
- Cache size: 10,000 nonces
- TTL: 120 seconds (2× replay window)
- Key format: `{scope}:{nonce_value}`

**Phase 3+** (future):
- Optional shared store (Redis/DynamoDB)
- Key format: `nonce:{scope}:{nonce_value}`
- TTL: Automatic expiration after replay window

#### FR-5.3: Timestamp Validation

**Replay Window Parameters**:
- `W` = replay window = 60,000 ms (60 seconds)
- `S` = clock skew tolerance = 5,000 ms (5 seconds)

**Validation Rule**:
```
reject if ts > now + S  (future timestamp beyond skew)
reject if ts < now - W  (expired timestamp)
```

Where:
- `ts` = envelope.ts (Unix milliseconds)
- `now` = current Unix timestamp (milliseconds)

**Constraint**: Reject if timestamp is outside window.

#### FR-5.4: Nonce Recording Atomicity

**Insertion Rule**: Nonce MUST be recorded if and only if:
1. ✅ Cryptographic verification passes (HMAC valid for primary_tongue)
2. ✅ Timestamp is within window (FR-5.3)
3. ✅ Nonce has not been seen before (atomic check-and-insert)

**CRITICAL**: Record nonce **even if policy enforcement fails** (QUARANTINE).

**Rationale**: Prevents attacker from probing with same nonce repeatedly.

**Cache Insert Timing**: Insert nonce **after crypto verifies** but **before policy evaluation** to prevent replay/probing loops.

---

### FR-6: Policy Enforcement

#### FR-6.1: Policy Modes

| Mode | Required Tongues | Description |
|------|------------------|-------------|
| `STANDARD` | primary_tongue | Single signature (default) |
| `STRICT` | primary_tongue + 1 other | Two signatures required |
| `SECRET` | primary_tongue + 2 others | Three signatures required |
| `CRITICAL` | All 6 tongues | Full consensus required |

#### FR-6.2: Policy Evaluation

```
policy_result = evaluate_policy(valid_tongues, policy_mode)
```

Where:
- `valid_tongues` = list from FR-4.2
- `policy_mode` = one of {STANDARD, STRICT, SECRET, CRITICAL}

**Returns**: `ALLOW` | `DENY` | `QUARANTINE`

#### FR-6.3: Decision Logic

**Primary Tongue Requirement**: Primary tongue signature MUST be valid (enforced in FR-4.3).

**Policy Evaluation**:
```
if primary_tongue not in valid_tongues:
    return DENY  // Already enforced in FR-4.3, but double-check here
    
required_count = {
    "STANDARD": 1,
    "STRICT": 2,
    "SECRET": 3,
    "CRITICAL": 6
}[policy_mode]

if len(valid_tongues) >= required_count:
    return ALLOW
else:
    return QUARANTINE
```

**Signature Order**: Signature order in `sigs` object is irrelevant (JSON object keys are unordered).

---

### FR-7: Error Handling

#### FR-7.1: External Error Response

External responses MUST be indistinguishable across failure modes:

```json
{
  "status": "DENY",
  "code": "AUTH_FAILED",
  "message": "Authentication failed"
}
```

**Constraint**: Same response for all failure types (timing, signature, replay, policy).

**Rationale**: Prevents information leakage to attackers.

#### FR-7.2: Internal Audit Log

Internal logs MAY include detailed failure reasons:

```json
{
  "timestamp": 1737161234567,
  "envelope_id": "nonce_value",
  "result": "DENY",
  "reason": "primary_tongue_signature_invalid",
  "details": {
    "primary_tongue": "RU",
    "valid_tongues": ["UM", "DR"],
    "policy_mode": "STRICT"
  }
}
```

**Constraint**: Audit logs MUST NOT be exposed to external callers.

---

## 3. Non-Functional Requirements

### NFR-1: Performance

#### NFR-1.1: Envelope Creation

- **Throughput**: ≥10,000 envelopes/second (single core)
- **Latency**: p95 < 2ms, p99 < 5ms
- **Assumptions**: 
  - Payload size ≤ 64KB
  - 1-3 signatures per envelope
  - Nonce cache size = 10,000

#### NFR-1.2: Envelope Verification

- **Throughput**: ≥50,000 verifications/second (single core)
- **Latency**: p95 < 1ms, p99 < 3ms
- **Assumptions**: Same as NFR-1.1

### NFR-2: Security

#### NFR-2.1: Cryptographic Primitives

- HMAC-SHA256 (FIPS 180-4, FIPS 198-1)
- 256-bit keys (32 bytes)
- Constant-time comparison for signatures

#### NFR-2.2: Timing Attack Resistance

All signature comparisons MUST use constant-time algorithms.

**Example** (Python):
```python
import hmac
result = hmac.compare_digest(expected_sig, received_sig)
```

**Example** (TypeScript):
```typescript
import { timingSafeEqual } from 'crypto';
result = timingSafeEqual(Buffer.from(expected), Buffer.from(received));
```

### NFR-3: Interoperability

#### NFR-3.1: Cross-Language Compatibility

TypeScript and Python implementations MUST produce identical:
- Canonical signing strings (byte-for-byte)
- HMAC signatures (hex-encoded, lowercase)
- Base64URL encodings (no padding)
- JSON canonicalization (RFC 8785)

**Verification**: 10 interop test vectors (see NFR-4.2) MUST pass in both directions.

#### NFR-3.2: Build Outputs

**Option 1** (Recommended): Dual build
- `dist/cjs/` - CommonJS (Node.js)
- `dist/esm/` - ES Modules (modern bundlers)
- `package.json` exports map with `import` and `require` conditions
- Requires Node.js 18+
- Enables tree-shaking and modern tooling

**Option 2** (Simpler): CommonJS only
- `"type": "commonjs"` in package.json
- Single `dist/` output
- Compatible with Node.js 14+
- Simpler build pipeline

**Decision Required**: Choose one option before implementation. **Default: Option 1** (dual build for modern ecosystem compatibility).

### NFR-4: Testing

#### NFR-4.1: Property-Based Testing

- Minimum 100 iterations per property
- Use `fast-check` (TypeScript) and `hypothesis` (Python)
- Test envelope round-trip (create → verify)
- Test cross-language interop (TS create → Python verify, vice versa)

#### NFR-4.2: Interop Test Vectors

Minimum 10 fixed test vectors with:
- Known master key (test-only, 32 bytes hex)
- Known envelope (JSON with all fields)
- Expected canonical signing string
- Expected signatures per tongue (hex, 64 chars)
- Both languages MUST produce identical results

**Test Vector Schema**:
```json
{
  "test_id": "vector_001_basic",
  "description": "Single signature, no AAD",
  "master_key": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "envelope": {
    "ver": "2.1",
    "primary_tongue": "RU",
    "kid": { "RU": "test-key-001" },
    "ts": 1737161234567,
    "nonce": "AQIDBAUG BwgJCgsMDQ4PEA",
    "payload": "SGVsbG8gV29ybGQ"
  },
  "expected_canonical_string": "2.1|RU||1737161234567|AQIDBAUGBwgJCgsMDQ4PEA|SGVsbG8gV29ybGQ",
  "expected_sigs": {
    "RU": "a1b2c3d4e5f6...hex(64 chars)"
  },
  "expected_result": "ALLOW"
}
```

**Required Test Cases**:
1. Single signature, no AAD
2. Single signature, with AAD (nested objects)
3. Multi-signature (3 tongues)
4. All 6 tongues (CRITICAL mode)
5. Empty payload (edge case)
6. Maximum nonce size (128 bytes)
7. AAD with special characters (escaping test)
8. AAD with numbers (canonicalization test)
9. Expired timestamp (should DENY)
10. Duplicate nonce (should DENY on second attempt)

**Validation**: Both TypeScript and Python MUST generate identical `expected_canonical_string` and `expected_sigs` for vectors 1-8.

---

## 4. Acceptance Criteria

### AC-1: Envelope Creation

- [ ] AC-1.1: Create envelope with 1 signature (primary tongue)
- [ ] AC-1.2: Create envelope with 3 signatures (multi-tongue)
- [ ] AC-1.3: Create envelope with AAD (canonicalized)
- [ ] AC-1.4: Create envelope without AAD (empty string)
- [ ] AC-1.5: Nonce is cryptographically random (≥16 bytes)
- [ ] AC-1.6: Timestamp is current Unix time (milliseconds)

### AC-2: Envelope Verification

- [ ] AC-2.1: Verify valid envelope (all signatures pass)
- [ ] AC-2.2: Reject envelope with invalid primary signature
- [ ] AC-2.3: Reject envelope with expired timestamp
- [ ] AC-2.4: Reject envelope with replayed nonce
- [ ] AC-2.5: Return list of valid tongues
- [ ] AC-2.6: Constant-time signature comparison

### AC-3: Replay Protection

- [ ] AC-3.1: Reject duplicate nonce within window
- [ ] AC-3.2: Accept same nonce after TTL expiration
- [ ] AC-3.3: Accept same nonce from different sender (if scoped)
- [ ] AC-3.4: Nonce cache evicts oldest entries (LRU)
- [ ] AC-3.5: Nonce recorded even on QUARANTINE

### AC-4: Policy Enforcement

- [ ] AC-4.1: STANDARD mode requires 1 signature
- [ ] AC-4.2: STRICT mode requires 2 signatures
- [ ] AC-4.3: SECRET mode requires 3 signatures
- [ ] AC-4.4: CRITICAL mode requires 6 signatures
- [ ] AC-4.5: Primary tongue signature always required

### AC-5: Interoperability

- [ ] AC-5.1: TypeScript creates, Python verifies (10 test vectors)
- [ ] AC-5.2: Python creates, TypeScript verifies (10 test vectors)
- [ ] AC-5.3: Identical canonical strings (both languages)
- [ ] AC-5.4: Identical HMAC signatures (both languages)
- [ ] AC-5.5: Identical Base64URL encoding (both languages)

### AC-6: Error Handling

- [ ] AC-6.1: External errors are indistinguishable
- [ ] AC-6.2: Internal audit logs include details
- [ ] AC-6.3: No information leakage on failure

---

## 5. Out of Scope (Future Work)

### OOS-1: Post-Quantum Cryptography

- ML-KEM-768 key encapsulation
- ML-DSA-65 digital signatures
- Hybrid classical+PQC construction

**Timeline**: v3.0 (Q2 2026)

### OOS-2: Dual-Channel Audio Verification

- Harmonic synthesis
- FFT-based verification
- Intent-modulated conlang

**Reference**: See `HARMONIC_VERIFICATION_SPEC.md`

### OOS-3: Quantum Key Distribution

- BB84 protocol
- E91 protocol
- Hardware integration

**Timeline**: Hardware-dependent (no ETA)

### OOS-4: Formal Verification

- Coq/Isabelle proofs
- Model checking (SPIN, TLA+)
- Symbolic execution

**Timeline**: Research project (Q4 2026+)

---

## 6. Design Document Requirements

The design document MUST specify:

1. **Canonicalization Implementation**
   - Exact RFC 8785 algorithm
   - Number encoding rules
   - String escaping rules

2. **Keyring Format**
   - Key storage structure
   - Key ID format
   - Key expiration handling
   - Key rotation procedure

3. **Nonce Cache Design**
   - LRU eviction algorithm
   - TTL management
   - Atomic insert operation
   - Scope key format

4. **Envelope Builder Algorithm**
   - TypeScript implementation
   - Python implementation
   - Step-by-step pseudocode

5. **Verifier Algorithm**
   - TypeScript implementation
   - Python implementation
   - Step-by-step pseudocode

6. **Policy Rules**
   - Exact logic for each mode
   - Edge case handling
   - Quarantine behavior

7. **Interop Test Vectors**
   - 10 fixed envelopes
   - Known keys and signatures
   - Both languages generate/verify

---

## 7. Example Envelope (Canonical)

```json
{
  "ver": "2.1",
  "primary_tongue": "RU",
  "kid": {
    "RU": "ru-2026-01",
    "UM": "um-2026-01"
  },
  "ts": 1737161234567,
  "nonce": "AQIDBAUG BwgJCgsMDQ4PEA",
  "aad": {
    "action": "execute",
    "mode": "STRICT",
    "priority": 1
  },
  "payload": "SGVsbG8gV29ybGQ",
  "sigs": {
    "RU": "a1b2c3d4e5f6...hex(64 chars)",
    "UM": "f6e5d4c3b2a1...hex(64 chars)"
  }
}
```

**Canonical Signing String**:
```
2.1|RU|{"action":"execute","mode":"STRICT","priority":1}|1737161234567|AQIDBAUGBwgJCgsMDQ4PEA|SGVsbG8gV29ybGQ
```

---

## 8. References

1. RFC 8785 - JSON Canonicalization Scheme (JCS)
2. FIPS 180-4 - Secure Hash Standard (SHA-256)
3. FIPS 198-1 - Keyed-Hash Message Authentication Code (HMAC)
4. RFC 4648 - Base64 Encoding (Base64URL variant)

---

**Version**: 2.1.0  
**Status**: Requirements Complete ✅  
**Next Step**: Design Document  
**Last Updated**: January 18, 2026
