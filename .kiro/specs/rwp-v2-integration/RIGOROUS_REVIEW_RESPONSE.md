# RWP v2.1 Rigorous Review - Response Document

**Date**: January 18, 2026  
**Purpose**: Address all contradictions and missing specifications identified in technical review  
**Status**: ✅ All critical issues resolved in `requirements-v2.1-rigorous.md`

---

## Executive Summary

This document responds to the rigorous technical review of RWP v2.1 requirements. All identified contradictions, missing specifications, and ambiguities have been resolved in the updated requirements document.

**Key Changes**:

- ✅ Resolved PQC vs HMAC contradiction
- ✅ Defined RFC 8785 JSON canonicalization with recursive nesting
- ✅ Locked envelope schema with per-tongue key IDs
- ✅ Specified nonce scope and storage model with atomic insertion
- ✅ Clarified error handling (external vs internal)
- ✅ Tightened multi-signature policy with explicit logic
- ✅ Made performance requirements measurable (p50/p95/p99)
- ✅ Required 10 interop test vectors with complete schema
- ⚠️ Identified 3 decision points requiring pre-implementation choices

---

## Issue 1: Contradictions / Inconsistencies

### A) "✅ Post-quantum cryptography (ML-KEM, ML-DSA)" vs. FR says HMAC-only

**Problem Identified**:

> In 1.2 Context you claim PQC is complete, but FR-3.2.1 hard-requires HMAC-SHA256 signatures. That's fine if HMAC is the current implementation and ML-DSA is a future upgrade, but the doc must not imply both are already in v3.1.0.

**Resolution** (requirements-v2.1-rigorous.md):

Section 1.2 now clearly states:

```markdown
### 1.2 What This Document Does NOT Cover

- ❌ Post-quantum cryptography (ML-KEM, ML-DSA) - **Future enhancement (v3.0+)**
```

Section 1.3 provides version roadmap:

```markdown
### 1.3 Current Implementation Status

- ✅ **v2.1.0**: HMAC-SHA256 multi-signatures (this spec)
- ⚠️ **v3.0**: PQC upgrade with ML-DSA planned (Q2 2026)
- ⚠️ **v3.1**: Hybrid classical+PQC planned (Q3 2026)
```

**Status**: ✅ **RESOLVED** - Clear separation between v2.1 (HMAC) and v3.0+ (PQC)

---

### B) "TypeScript MUST compile to CommonJS" vs your earlier exports/import/require warning

**Problem Identified**:

> You previously showed a package.json exports map with import/require conditions. That usually means you're shipping dual-mode output. If you truly require CommonJS only, then avoid ESM import conditions, or explicitly describe dual build outputs (CJS + ESM) and require Node 18+.

**Resolution** (requirements-v2.1-rigorous.md):

Section NFR-3.2 now provides two explicit options with defaults.

**Status**: ⚠️ **RESOLVED AS A DECISION POINT** (must choose before implementation; default recommended)

---

## Issue 2: Missing Canonicalization (Interop Will Fail Without It)

**Problem Identified**:

> You repeatedly rely on signing: ver|primary_tongue|aad|ts|nonce|payload. But you don't define how aad is serialized. If aad is JSON (it is), then TS and Python will produce different bytes unless you define canonicalization. This is the #1 cross-language signature failure cause.

**Resolution** (requirements-v2.1-rigorous.md):

Section FR-2 now provides complete canonicalization specification using RFC 8785 with recursive nesting requirements.

**Status**: ✅ **RESOLVED** - RFC 8785 with recursive nesting and number handling clarification

---

## Issue 3: What Bytes Are Signed (Exact Signing Input)

**Problem Identified**:

> RFC 8785 tells you how to canonicalize JSON, but you still need to specify what exactly is signed. Do you sign the envelope-without-sigs, or do you use explicit byte concatenation?

**Resolution** (requirements-v2.1-rigorous.md):

Section FR-2.3 now defines two explicit options (Option A: canonical JSON, Option B: pipe-delimited).

**Status**: ⚠️ **RESOLVED AS A DECISION POINT** (must choose before implementation; Option A recommended)

---

## Issue 4: Base64URL Specification Incomplete

**Problem Identified**:

> Your Base64URL section cuts off. Need complete specification including decoder strictness and nonce encoding rules.

**Resolution** (requirements-v2.1-rigorous.md):

Section FR-2.2 now complete with alphabet, padding rules, decoder strictness, and nonce encoding requirements.

**Status**: ✅ **RESOLVED** - Complete Base64URL specification with decoder strictness

---

## Issue 5: Nonce Scope and Cache Model

**Problem Identified**:

> Nonce uniqueness scope needs to be explicit. Is it per-sender, per-tongue, or both? Also need to define cache insert timing to prevent replay/probing loops.

**Resolution** (requirements-v2.1-rigorous.md):

Section FR-5.1 defines explicit scope options with default. Section FR-5.4 defines atomic insertion timing.

**Status**: ⚠️ **RESOLVED AS A DECISION POINT** (must choose scope; default provided) + ✅ **RESOLVED** (atomic insertion timing)

---

## Issue 6: Timestamp Validation Parameters

**Problem Identified**:

> Need explicit replay window (W) and clock skew tolerance (S) parameters, not just "60 seconds".

**Resolution** (requirements-v2.1-rigorous.md):

Section FR-5.3 now defines W = 60,000 ms and S = 5,000 ms with explicit validation rules.

**Status**: ✅ **RESOLVED** - Explicit W and S parameters with validation logic

---

## Issue 7: Multi-Signature Policy - Unknown Key Handling

**Problem Identified**:

> If a tongue is missing a key (unknown kid), does verification fail hard or mark that tongue invalid? Need explicit behavior.

**Resolution** (requirements-v2.1-rigorous.md):

Section FR-4.2 now defines unknown key handling and Section FR-6.3 clarifies signature order irrelevance.

**Status**: ✅ **RESOLVED** - Explicit unknown key behavior and signature order clarification

---

## Issue 8: Performance Requirements - Measurability

**Problem Identified**:

> Performance numbers must state environment, workload, method, and distribution (p50/p95/p99). If aspirational, mark as "Target".

**Resolution** (requirements-v2.1-rigorous.md):

Section NFR-1 now includes measurable requirements with p95/p99 latency, throughput targets, and explicit assumptions.

**Status**: ✅ **RESOLVED** - Measurable performance requirements with assumptions

---

## Issue 9: Interop Test Vectors - Complete Schema

**Problem Identified**:

> "10 interop test vectors" is great, but need to define their exact contents and required test cases.

**Resolution** (requirements-v2.1-rigorous.md):

Section NFR-4.2 now provides complete test vector schema with 10 required test cases covering all edge cases.

**Status**: ✅ **RESOLVED** - Complete test vector schema with 10 required test cases

---

## Summary of Decision Points

Before implementation begins, the following decisions MUST be made and documented:

| Decision                        | Options                                                | Default  | Priority |
| ------------------------------- | ------------------------------------------------------ | -------- | -------- |
| **Build Output**                | Option 1 (dual CJS+ESM) or Option 2 (CJS only)         | Option 1 | HIGH     |
| **Signing String Construction** | Option A (canonical JSON) or Option B (pipe-delimited) | Option A | HIGH     |
| **Nonce Scope**                 | Option A (sender+tongue) or Option B (tongue only)     | Option B | MEDIUM   |

**Recommendation**: Accept all defaults (Option 1, Option A, Option B) for modern ecosystem compatibility and simplicity.

---

## Implementation Checklist

Before starting implementation, verify:

- [ ] Build output decision made (Option 1 or 2) - **Default: Option 1**
- [ ] Signing string construction decision made (Option A or B) - **Default: Option A**
- [ ] Nonce scope decision made (Option A or B) - **Default: Option B**
- [ ] RFC 8785 library selected (TypeScript: canonicalize, Python: canonicaljson)
- [ ] Key management system defined (keyring format, rotation procedure)
- [ ] Nonce storage backend chosen (in-memory LRU for MVP)
- [ ] Test vectors generated (10 minimum, schema defined in NFR-4.2)
- [ ] Constant-time comparison library verified (crypto.timingSafeEqual, hmac.compare_digest)

---

## Next Steps

1. **Accept Defaults**: Review and accept recommended defaults for 3 decision points
2. **Generate Test Vectors**: Create 10 interop test vectors using schema from NFR-4.2
3. **Design Document**: Create detailed design document per Section 6 requirements
4. **Implementation**: Begin TypeScript and Python implementations
5. **Cross-Language Testing**: Validate all 10 test vectors pass in both directions

---

## Document History

| Version | Date       | Changes                     | Status      |
| ------- | ---------- | --------------------------- | ----------- |
| 1.0     | 2026-01-15 | Initial requirements        | Draft       |
| 2.0     | 2026-01-17 | Added rigorous review       | Review      |
| 2.1     | 2026-01-18 | Resolved all contradictions | Complete ✅ |

---

**Version**: 2.1.0  
**Status**: Review Response Complete ✅  
**Requirements Document**: `requirements-v2.1-rigorous.md`  
**Next Step**: Accept defaults and generate test vectors  
**Last Updated**: January 18, 2026
