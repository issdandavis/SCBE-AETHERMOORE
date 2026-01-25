# RWP v2.1 Specification - Complete Package

**Version**: 2.1.0  
**Date**: January 18, 2026  
**Status**: ✅ Requirements Complete, Ready for Implementation

---

## What is RWP v2.1?

RWP (Runethic Weighting Protocol) v2.1 is a **multi-signature envelope protocol** using HMAC-SHA256 for message authentication across multiple "Sacred Tongues" (trust domains). It provides:

- Multi-signature authentication (1-6 signatures)
- Replay protection with nonce management
- Policy-based access control (STANDARD, STRICT, SECRET, CRITICAL)
- Cross-language interoperability (TypeScript ↔ Python)
- Constant-time signature verification

---

## Document Structure

This specification package contains 6 documents:

### 1. **requirements-v2.1-rigorous.md** ⭐ START HERE

**Purpose**: Complete functional and non-functional requirements  
**Audience**: Implementers, reviewers, auditors  
**Status**: ✅ Complete and rigorous

**Contents**:

- Envelope structure and field definitions
- RFC 8785 JSON canonicalization specification
- HMAC-SHA256 signature generation and verification
- Replay protection with nonce management
- Policy enforcement logic
- Performance requirements (measurable)
- 41 acceptance criteria

**Read this first** to understand what needs to be built.

---

### 2. **RIGOROUS_REVIEW_RESPONSE.md**

**Purpose**: Issue-by-issue resolution of technical review  
**Audience**: Reviewers, technical leads  
**Status**: ✅ All 9 issues resolved

**Contents**:

- Resolution of PQC vs HMAC contradiction
- Canonicalization specification (RFC 8785)
- Build output decision point
- Nonce scope and atomic insertion
- Unknown key handling
- Performance measurability
- Test vector schema
- 3 decision points requiring pre-implementation choices

**Read this** to understand what was fixed and why.

---

### 3. **REVIEW_FIXES_SUMMARY.md**

**Purpose**: Before/after comparison of all fixes  
**Audience**: Quick reference for reviewers  
**Status**: ✅ Complete

**Contents**:

- 10 major fixes with before/after examples
- Credibility fixes (no overclaims)
- Canonicalization specification (critical for interop)
- Decision points tracking
- Implementation checklist

**Read this** for a quick overview of what changed.

---

### 4. **TEST_VECTORS.json**

**Purpose**: 10 interop test vectors for cross-language validation  
**Audience**: Implementers, QA engineers  
**Status**: ⚠️ Schema complete, values need generation

**Contents**:

- 10 test cases covering:
  - Single signature, no AAD
  - Single signature, with AAD (nested objects)
  - Multi-signature (3 tongues)
  - All 6 tongues (CRITICAL mode)
  - Empty payload
  - Maximum nonce size
  - Special characters (escaping)
  - Numbers (canonicalization)
  - Expired timestamp (DENY)
  - Duplicate nonce (DENY)

**Use this** to validate TypeScript and Python implementations produce identical results.

---

### 5. **IMPLEMENTATION_GUIDE.md** ⭐ IMPLEMENTERS START HERE

**Purpose**: Step-by-step implementation guide  
**Audience**: Developers implementing RWP v2.1  
**Status**: ✅ Complete with code examples

**Contents**:

- Phase 1: Pre-implementation decisions
- Phase 2: Generate test vectors
- Phase 3: Implement core components (with code)
- Phase 4: Testing (unit, interop, cross-language)
- Phase 5: Documentation
- Phase 6: Deployment checklist
- Troubleshooting guide

**Follow this** to implement RWP v2.1 correctly.

---

### 6. **README.md** (this file)

**Purpose**: Navigation and quick reference  
**Audience**: Everyone  
**Status**: ✅ Complete

---

## Quick Start

### For Reviewers

1. Read **requirements-v2.1-rigorous.md** (complete spec)
2. Read **RIGOROUS_REVIEW_RESPONSE.md** (what was fixed)
3. Verify all 9 issues are resolved

### For Implementers

1. Read **requirements-v2.1-rigorous.md** (understand requirements)
2. Read **IMPLEMENTATION_GUIDE.md** (follow step-by-step)
3. Make 3 pre-implementation decisions (or accept defaults)
4. Generate test vectors using **TEST_VECTORS.json** schema
5. Implement core components (envelope builder, verifier)
6. Run all tests (unit, interop, cross-language)

### For QA Engineers

1. Read **requirements-v2.1-rigorous.md** Section 4 (Acceptance Criteria)
2. Use **TEST_VECTORS.json** for interop testing
3. Verify all 41 acceptance criteria pass

---

## Decision Points (Must Choose Before Implementation)

| Decision           | Options                                                | Default  | Priority |
| ------------------ | ------------------------------------------------------ | -------- | -------- |
| **Build Output**   | Option 1 (dual CJS+ESM) or Option 2 (CJS only)         | Option 1 | HIGH     |
| **Signing String** | Option A (canonical JSON) or Option B (pipe-delimited) | Option A | HIGH     |
| **Nonce Scope**    | Option A (sender+tongue) or Option B (tongue only)     | Option B | MEDIUM   |

**Recommendation**: Accept all defaults for modern ecosystem compatibility.

---

## Key Features

### ✅ Rigorous Specification

- No overclaims ("Requirements Complete" not "Production Ready")
- Byte-level canonicalization rules (RFC 8785)
- Measurable performance requirements (p95/p99)
- Complete test vector schema

### ✅ Cross-Language Interop

- TypeScript and Python implementations
- 10 interop test vectors (both directions)
- Identical canonical strings and signatures

### ✅ Security

- HMAC-SHA256 (FIPS 180-4, FIPS 198-1)
- Constant-time signature comparison
- Replay protection with nonce management
- Atomic nonce insertion (prevents probing)

### ✅ Policy-Based Access Control

- STANDARD: 1 signature (primary tongue)
- STRICT: 2 signatures
- SECRET: 3 signatures
- CRITICAL: 6 signatures (full consensus)

---

## Implementation Status

| Component                 | Status         | Evidence                      |
| ------------------------- | -------------- | ----------------------------- |
| Requirements              | ✅ Complete    | requirements-v2.1-rigorous.md |
| Review Response           | ✅ Complete    | RIGOROUS_REVIEW_RESPONSE.md   |
| Test Vector Schema        | ✅ Complete    | TEST_VECTORS.json             |
| Implementation Guide      | ✅ Complete    | IMPLEMENTATION_GUIDE.md       |
| TypeScript Implementation | ❌ Not started | -                             |
| Python Implementation     | ❌ Not started | -                             |
| Test Vector Values        | ⚠️ Schema only | Need to generate              |
| Cross-Language Tests      | ❌ Not started | -                             |

---

## Performance Targets (NFR-1)

### Envelope Creation

- **Throughput**: ≥10,000 envelopes/second (single core)
- **Latency**: p95 < 2ms, p99 < 5ms
- **Assumptions**: Payload ≤ 64KB, 1-3 signatures, nonce cache = 10,000

### Envelope Verification

- **Throughput**: ≥50,000 verifications/second (single core)
- **Latency**: p95 < 1ms, p99 < 3ms
- **Assumptions**: Same as above

---

## Acceptance Criteria Summary

**Total**: 41 acceptance criteria across 6 categories

- ✅ AC-1: Envelope Creation (6 criteria)
- ✅ AC-2: Envelope Verification (6 criteria)
- ✅ AC-3: Replay Protection (5 criteria)
- ✅ AC-4: Policy Enforcement (5 criteria)
- ✅ AC-5: Interoperability (5 criteria)
- ✅ AC-6: Error Handling (3 criteria)

See **requirements-v2.1-rigorous.md** Section 4 for complete list.

---

## Out of Scope (Future Work)

### v3.0 (Q2 2026)

- Post-quantum cryptography (ML-KEM, ML-DSA)
- Hybrid classical+PQC construction

### v3.1+ (Q3 2026+)

- Dual-channel audio verification
- Quantum key distribution (hardware-dependent)
- Formal verification (Coq/Isabelle)

---

## References

1. **RFC 8785** - JSON Canonicalization Scheme (JCS)
2. **FIPS 180-4** - Secure Hash Standard (SHA-256)
3. **FIPS 198-1** - Keyed-Hash Message Authentication Code (HMAC)
4. **RFC 4648** - Base64 Encoding (Base64URL variant)

---

## Support

### Questions?

- Read **requirements-v2.1-rigorous.md** for complete specification
- Read **IMPLEMENTATION_GUIDE.md** for step-by-step instructions
- Check **RIGOROUS_REVIEW_RESPONSE.md** for resolved issues

### Found an Issue?

- Check if it's a known decision point (3 tracked)
- Verify against acceptance criteria (41 total)
- Review test vectors for edge cases

---

## Version History

| Version | Date       | Changes                     | Status      |
| ------- | ---------- | --------------------------- | ----------- |
| 1.0     | 2026-01-15 | Initial requirements        | Draft       |
| 2.0     | 2026-01-17 | Added rigorous review       | Review      |
| 2.1     | 2026-01-18 | Resolved all contradictions | Complete ✅ |

---

## Next Steps

1. **Review**: Accept or choose alternatives for 3 decision points
2. **Generate**: Fill in test vector expected values
3. **Implement**: Follow IMPLEMENTATION_GUIDE.md
4. **Test**: Validate all 41 acceptance criteria
5. **Deploy**: Follow Phase 6 deployment checklist

---

**Version**: 2.1.0  
**Status**: Specification Complete ✅  
**Ready for**: Implementation  
**Last Updated**: January 18, 2026
