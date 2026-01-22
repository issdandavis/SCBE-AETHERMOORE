# RWP v2.1 Review Fixes - Summary

**Date**: January 18, 2026  
**Status**: ✅ All critical issues resolved

---

## What Was Fixed

This document summarizes the rigorous technical review fixes applied to RWP v2.1 requirements. All fixes follow the "examiner-grade teardown" template to ensure credibility and reproducibility.

---

## 1. Credibility Fixes

### Before (Overclaim):

```markdown
**Status**: Production Ready ✅
```

### After (Honest):

```markdown
**Status**: Requirements Complete - Ready for Implementation
```

**Why**: Requirements are complete, but implementation hasn't started yet. "Production ready" implies deployed and audited code.

---

## 2. PQC Contradiction Fixed

### Before (Contradictory):

```markdown
✅ Post-quantum cryptography (ML-KEM, ML-DSA)
...
FR-3.2.1: MUST use HMAC-SHA256 signatures
```

### After (Clear):

```markdown
### 1.2 What This Document Does NOT Cover

- ❌ Post-quantum cryptography (ML-KEM, ML-DSA) - **Future enhancement (v3.0+)**

### 1.3 Current Implementation Status

- ✅ **v2.1.0**: HMAC-SHA256 multi-signatures (this spec)
- ⚠️ **v3.0**: PQC upgrade with ML-DSA planned (Q2 2026)
```

**Why**: Can't claim PQC is complete when the spec requires HMAC-only. Clear version roadmap prevents confusion.

---

## 3. Canonicalization Specification (Critical for Interop)

### Before (Missing):

```markdown
Sign: ver|primary_tongue|aad|ts|nonce|payload
```

### After (Complete):

```markdown
### FR-2.1: AAD Canonicalization

- MUST use RFC 8785 JSON Canonicalization Scheme
- Keys sorted lexicographically
- No whitespace
- Numbers per RFC 8785 (minimal representation)
- **AAD canonicalization MUST apply recursively to all nested objects**
- If implementation cannot guarantee RFC 8785 number formatting, MUST reject floats or document deviation

### FR-2.2: Base64URL Encoding

- Alphabet: A-Za-z0-9-\_
- NO padding (= forbidden)
- Decoder MUST accept only canonical form (strict mode)
- Payload MUST be raw bytes, not JSON-encoded-by-mistake

### FR-2.3: Canonical Signing String Construction

**Option A** (Recommended): Canonical JSON of envelope-without-sigs
**Option B**: Explicit pipe-delimited concatenation
**Decision Required**: Choose one before implementation
```

**Why**: Without exact canonicalization rules, TypeScript and Python will produce different bytes → signature verification fails. This is the #1 cross-language interop failure cause.

---

## 4. Build Output Decision Point

### Before (Ambiguous):

```markdown
TypeScript MUST compile to CommonJS
```

### After (Explicit):

```markdown
### NFR-3.2: Build Outputs

**Option 1** (Recommended): Dual build

- dist/cjs/ - CommonJS
- dist/esm/ - ES Modules
- Requires Node.js 18+

**Option 2** (Simpler): CommonJS only

- Single dist/ output
- Compatible with Node.js 14+

**Decision Required**: Choose one before implementation. **Default: Option 1**
```

**Why**: "Compile to CommonJS" contradicts modern dual-build patterns. Explicit options with defaults prevent confusion.

---

## 5. Nonce Scope and Atomic Insertion

### Before (Vague):

```markdown
Nonce uniqueness enforced
```

### After (Precise):

```markdown
### FR-5.1: Nonce Uniqueness Scope

**Option A**: scope = (sender_id, primary_tongue)
**Option B**: scope = (primary_tongue)
**Decision Required**: Choose one. **Default: Option B**

### FR-5.4: Nonce Recording Atomicity

**Insertion Rule**: Record nonce if and only if:

1. ✅ Crypto verification passes
2. ✅ Timestamp within window
3. ✅ Nonce not seen before (atomic check-and-insert)

**CRITICAL**: Record nonce **even if policy fails** (QUARANTINE)
**Cache Insert Timing**: After crypto verifies, before policy evaluation
```

**Why**: Prevents replay/probing attacks. Attacker can't probe with same nonce repeatedly if it's recorded after crypto passes.

---

## 6. Timestamp Validation Parameters

### Before (Imprecise):

```markdown
|ts_now - envelope.ts| ≤ 60 seconds
```

### After (Explicit):

```markdown
### FR-5.3: Timestamp Validation

**Replay Window Parameters**:

- W = replay window = 60,000 ms (60 seconds)
- S = clock skew tolerance = 5,000 ms (5 seconds)

**Validation Rule**:
reject if ts > now + S (future timestamp beyond skew)
reject if ts < now - W (expired timestamp)
```

**Why**: Separate replay window (W) and clock skew (S) parameters enable proper distributed system clock handling.

---

## 7. Unknown Key Handling

### Before (Undefined):

```markdown
Verify signatures for all tongues
```

### After (Explicit):

```markdown
### FR-4.2: Valid Tongues List

**Handling Unknown Keys**:

- If tongue present in sigs but no key exists for kid[tongue], mark **INVALID**
- Verification continues for other tongues
- If primary_tongue has unknown key, entire envelope **DENIED**
```

**Why**: Defines exact behavior when key is missing. Prevents ambiguity in multi-signature scenarios.

---

## 8. Performance Requirements (Measurable)

### Before (Vague):

```markdown
High performance
```

### After (Measurable):

```markdown
### NFR-1.1: Envelope Creation

- **Throughput**: ≥10,000 envelopes/second (single core)
- **Latency**: p95 < 2ms, p99 < 5ms
- **Assumptions**:
  - Payload size ≤ 64KB
  - 1-3 signatures per envelope
  - Nonce cache size = 10,000
```

**Why**: Measurable requirements enable benchmarking and regression detection. Assumptions document test conditions.

---

## 9. Interop Test Vectors (Complete Schema)

### Before (Incomplete):

```markdown
10 interop test vectors required
```

### After (Complete):

```markdown
### NFR-4.2: Interop Test Vectors

**Test Vector Schema**:
{
"test_id": "vector_001_basic",
"description": "Single signature, no AAD",
"master_key": "hex(32 bytes)",
"envelope": { ... },
"expected_canonical_string": "...",
"expected_sigs": { "RU": "hex(64 chars)" },
"expected_result": "ALLOW"
}

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
```

**Why**: Complete schema enables automated interop testing. Both TypeScript and Python must pass all 10 vectors.

---

## 10. Decision Points Tracking

### New Section Added:

```markdown
## Summary of Decision Points

| Decision           | Options                                       | Default  | Priority |
| ------------------ | --------------------------------------------- | -------- | -------- |
| **Build Output**   | Option 1 (dual) or Option 2 (CJS only)        | Option 1 | HIGH     |
| **Signing String** | Option A (JSON) or Option B (pipe)            | Option A | HIGH     |
| **Nonce Scope**    | Option A (sender+tongue) or Option B (tongue) | Option B | MEDIUM   |

**Recommendation**: Accept all defaults for modern ecosystem compatibility
```

**Why**: Tracks all "Decision Required" items in one place. Prevents implementation from starting with unresolved choices.

---

## Files Updated

1. **requirements-v2.1-rigorous.md** - Complete requirements specification
2. **RIGOROUS_REVIEW_RESPONSE.md** - Issue-by-issue resolution tracking
3. **TEST_VECTORS.json** - 10 interop test vectors with schema
4. **REVIEW_FIXES_SUMMARY.md** - This document

---

## Implementation Checklist

Before starting implementation:

- [ ] Accept defaults for 3 decision points (or choose alternatives)
- [ ] Select RFC 8785 libraries:
  - TypeScript: `canonicalize` npm package
  - Python: `canonicaljson` or custom
- [ ] Generate test vector expected values (canonical strings + signatures)
- [ ] Verify constant-time comparison libraries:
  - TypeScript: `crypto.timingSafeEqual`
  - Python: `hmac.compare_digest`
- [ ] Define keyring format (key storage, rotation, expiration)
- [ ] Implement nonce cache (in-memory LRU for MVP)

---

## What Makes This "Rigorous"

1. **No Overclaims**: "Requirements Complete" not "Production Ready"
2. **Explicit Contradictions Resolved**: PQC vs HMAC clearly separated by version
3. **Byte-Level Specification**: Exact canonicalization rules prevent interop failures
4. **Decision Points Tracked**: All "choose one" items documented with defaults
5. **Measurable Requirements**: Performance with p95/p99, not "fast"
6. **Complete Test Vectors**: 10 vectors with schema, not "we'll test it"
7. **Security Timing**: Nonce insertion after crypto, before policy
8. **Edge Cases Defined**: Unknown keys, empty payloads, max nonce size

---

## Next Steps

1. **Review and Accept**: Review all 3 decision points, accept defaults or choose alternatives
2. **Generate Test Vectors**: Fill in `expected_canonical_string` and `expected_sigs` in TEST_VECTORS.json
3. **Design Document**: Create detailed design per Section 6 requirements
4. **Implementation**: Begin TypeScript and Python implementations
5. **Cross-Language Testing**: Validate all 10 test vectors pass both directions

---

**Version**: 2.1.0  
**Status**: Review Fixes Complete ✅  
**Last Updated**: January 18, 2026
