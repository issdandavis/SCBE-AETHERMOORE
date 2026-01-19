# RWP v2.1 Multi-Signature Envelopes - Requirements

**Feature**: rwp-v2-integration  
**Version**: 3.1.0  
**Phase**: 2 (Protocol Layer)  
**Status**: Planning  
**Timeline**: Q2 2026 (3 months)  
**Dependencies**: Sacred Tongues (✅ Complete)

---

## 1. Overview

### 1.1 Purpose

Implement the Real World Protocol (RWP) v2.1 for secure AI-to-AI communication using multi-signature envelopes with domain-separated authentication via Sacred Tongues.

### 1.2 Context

This is Phase 2 of the SCBE-AETHERMOORE unified platform. The foundation (v3.0.0) is complete with:
- ✅ Sacred Tongues (6 domains: KO, AV, RU, CA, UM, DR)
- ✅ Post-quantum cryptography (ML-KEM, ML-DSA)
- ✅ 14-layer SCBE architecture
- ✅ Hyperbolic geometry security

RWP v2.1 builds on Sacred Tongues to enable secure, policy-enforced communication between AI agents.

### 1.3 Goals

**Primary Goals**:
1. Enable secure AI-to-AI communication with multi-signature consensus
2. Implement policy-based authorization (standard, strict, secret, critical)
3. Prevent replay attacks with timestamp + nonce validation
4. Provide domain-separated authentication via Sacred Tongues
5. Support both TypeScript and Python implementations

**Success Criteria**:
- Agents can send/receive RWP envelopes
- Policy enforcement works correctly
- Replay attacks are prevented
- 95% test coverage
- <10ms envelope creation time
- <5ms envelope verification time

---

## 2. User Stories

### 2.1 Agent Communication

**As an** AI agent  
**I want to** send secure messages to other agents  
**So that** my communications are authenticated and tamper-proof

**Acceptance Criteria**:
- AC-2.1.1: Agent can create RWP envelope with payload
- AC-2.1.2: Agent can sign envelope with multiple tongues
- AC-2.1.3: Agent can send envelope to another agent
- AC-2.1.4: Receiving agent can verify signatures
- AC-2.1.5: Receiving agent can decrypt payload
- AC-2.1.6: Invalid signatures are rejected

### 2.2 Policy Enforcement

**As a** system administrator  
**I want to** enforce different security policies for different message types  
**So that** critical operations require stronger authentication

**Acceptance Criteria**:
- AC-2.2.1: Standard policy accepts any valid signature
- AC-2.2.2: Strict policy requires RU (Policy) tongue signature
- AC-2.2.3: Secret policy requires UM (Security) tongue signature
- AC-2.2.4: Critical policy requires RU + UM + DR tongue signatures
- AC-2.2.5: Policy violations are rejected with clear error messages
- AC-2.2.6: Policy can be configured per message type

### 2.3 Replay Attack Prevention

**As a** security engineer  
**I want to** prevent replay attacks on agent communications  
**So that** old messages cannot be reused maliciously

**Acceptance Criteria**:
- AC-2.3.1: Each envelope has unique nonce
- AC-2.3.2: Each envelope has timestamp
- AC-2.3.3: Envelopes outside replay window are rejected
- AC-2.3.4: Duplicate nonces are rejected
- AC-2.3.5: Replay window is configurable (default 5 minutes)
- AC-2.3.6: Nonce cache is memory-efficient

### 2.4 Multi-Signature Consensus

**As an** AI orchestrator  
**I want to** require multiple agents to sign critical decisions  
**So that** no single agent can authorize dangerous operations

**Acceptance Criteria**:
- AC-2.4.1: Envelope can have multiple signatures (1-6 tongues)
- AC-2.4.2: Each signature is domain-separated by tongue
- AC-2.4.3: Verification returns list of valid tongues
- AC-2.4.4: Policy enforcement checks required tongues
- AC-2.4.5: Partial signatures are rejected for critical policy
- AC-2.4.6: Signature order doesn't matter

### 2.5 Key Management

**As a** developer  
**I want to** manage cryptographic keys for each Sacred Tongue  
**So that** I can rotate keys and maintain security

**Acceptance Criteria**:
- AC-2.5.1: Keyring stores keys for all 6 tongues
- AC-2.5.2: Keys can be loaded from secure storage
- AC-2.5.3: Keys can be rotated without breaking existing envelopes
- AC-2.5.4: Key ID (kid) is included in envelope
- AC-2.5.5: Multiple key versions can coexist
- AC-2.5.6: Expired keys are rejected

### 2.6 Interoperability

**As a** platform integrator  
**I want to** use RWP v2.1 from both TypeScript and Python  
**So that** I can integrate with different parts of the system

**Acceptance Criteria**:
- AC-2.6.1: TypeScript SDK creates valid envelopes
- AC-2.6.2: Python SDK creates valid envelopes
- AC-2.6.3: TypeScript can verify Python-created envelopes
- AC-2.6.4: Python can verify TypeScript-created envelopes
- AC-2.6.5: Envelope format is identical across languages
- AC-2.6.6: Error messages are consistent across languages

---

## 3. Functional Requirements

### 3.1 Envelope Structure

**FR-3.1.1**: RWP envelope MUST have version field set to "2.1"

**FR-3.1.2**: RWP envelope MUST have primary_tongue field indicating intent domain

**FR-3.1.3**: RWP envelope MUST have aad (additional authenticated data) field

**FR-3.1.4**: RWP envelope MUST have ts (timestamp) field in Unix milliseconds

**FR-3.1.5**: RWP envelope MUST have nonce field for replay protection

**FR-3.1.6**: RWP envelope MUST have payload field (Base64URL encoded)

**FR-3.1.7**: RWP envelope MUST have sigs field with tongue-keyed signatures

**FR-3.1.8**: Envelope MUST be JSON-serializable

### 3.2 Signature Generation

**FR-3.2.1**: Signatures MUST use HMAC-SHA256 algorithm

**FR-3.2.2**: Each tongue MUST have independent HMAC key

**FR-3.2.3**: Signature input MUST include: ver|primary_tongue|aad|ts|nonce|payload

**FR-3.2.4**: Signature MUST be Base64URL encoded

**FR-3.2.5**: Multiple tongues can sign same envelope

**FR-3.2.6**: Signature order MUST NOT affect verification

### 3.3 Signature Verification

**FR-3.3.1**: Verification MUST check all provided signatures

**FR-3.3.2**: Verification MUST return list of valid tongues

**FR-3.3.3**: Invalid signatures MUST be rejected

**FR-3.3.4**: Missing keys MUST cause verification failure

**FR-3.3.5**: Timestamp MUST be within replay window

**FR-3.3.6**: Nonce MUST NOT be reused within replay window

### 3.4 Policy Enforcement

**FR-3.4.1**: Standard policy MUST accept any valid signature

**FR-3.4.2**: Strict policy MUST require RU (Policy) tongue

**FR-3.4.3**: Secret policy MUST require UM (Security) tongue

**FR-3.4.4**: Critical policy MUST require RU + UM + DR tongues

**FR-3.4.5**: Policy check MUST happen after signature verification

**FR-3.4.6**: Policy violations MUST return clear error messages

### 3.5 Replay Protection

**FR-3.5.1**: Replay window MUST default to 300,000ms (5 minutes)

**FR-3.5.2**: Replay window MUST be configurable

**FR-3.5.3**: Nonce cache MUST store recent nonces

**FR-3.5.4**: Nonce cache MUST expire old entries

**FR-3.5.5**: Duplicate nonces MUST be rejected

**FR-3.5.6**: Future timestamps MUST be rejected (clock skew tolerance: 60s)

### 3.6 Key Management

**FR-3.6.1**: Keyring MUST store keys indexed by tongue code

**FR-3.6.2**: Keys MUST be 32-byte buffers (256-bit)

**FR-3.6.3**: Key ID (kid) MUST be included in envelope

**FR-3.6.4**: Multiple key versions MUST be supported

**FR-3.6.5**: Key rotation MUST NOT break existing envelopes

**FR-3.6.6**: Expired keys MUST be rejected

---

## 4. Non-Functional Requirements

### 4.1 Performance

**NFR-4.1.1**: Envelope creation MUST complete in <10ms

**NFR-4.1.2**: Envelope verification MUST complete in <5ms

**NFR-4.1.3**: Nonce cache lookup MUST complete in <1ms

**NFR-4.1.4**: System MUST handle 1000+ envelopes/second

**NFR-4.1.5**: Memory usage MUST be <100MB for 10K cached nonces

### 4.2 Security

**NFR-4.2.1**: HMAC keys MUST be 256-bit (32 bytes)

**NFR-4.2.2**: Nonces MUST be cryptographically random (16 bytes minimum)

**NFR-4.2.3**: Timestamps MUST use Unix milliseconds (64-bit)

**NFR-4.2.4**: Replay window MUST be configurable (default 5 minutes)

**NFR-4.2.5**: Signature algorithm MUST be HMAC-SHA256

**NFR-4.2.6**: Keys MUST be stored securely (not in plaintext)

### 4.3 Reliability

**NFR-4.3.1**: System MUST handle malformed envelopes gracefully

**NFR-4.3.2**: System MUST handle missing keys gracefully

**NFR-4.3.3**: System MUST handle clock skew (±60s tolerance)

**NFR-4.3.4**: System MUST log all verification failures

**NFR-4.3.5**: System MUST NOT leak information on failure

### 4.4 Maintainability

**NFR-4.4.1**: Code MUST have 95%+ test coverage (lines, functions, branches, statements)

**NFR-4.4.2**: All functions MUST have JSDoc/docstring comments

**NFR-4.4.3**: API MUST be consistent across TypeScript and Python

**NFR-4.4.4**: Error messages MUST be clear and actionable

**NFR-4.4.5**: Code MUST follow project style guide

### 4.5 Testing

**NFR-4.5.1**: MUST include unit tests for all core functions

**NFR-4.5.2**: MUST include property-based tests using fast-check (TypeScript) and hypothesis (Python)

**NFR-4.5.3**: Property-based tests MUST run minimum 100 iterations

**NFR-4.5.4**: MUST include interoperability tests (TypeScript ↔ Python)

**NFR-4.5.5**: MUST include requirement traceability comments in all tests

**NFR-4.5.6**: MUST test all acceptance criteria with automated tests

### 4.5 Testing

**NFR-4.5.1**: MUST include unit tests for all core functions

**NFR-4.5.2**: MUST include property-based tests using fast-check (TypeScript) and hypothesis (Python)

**NFR-4.5.3**: Property-based tests MUST run minimum 100 iterations

**NFR-4.5.4**: MUST include interoperability tests (TypeScript ↔ Python)

**NFR-4.5.5**: MUST include requirement traceability comments in all tests

**NFR-4.5.6**: MUST test all acceptance criteria with automated tests

### 4.6 Compatibility

**NFR-4.6.1**: TypeScript implementation MUST work with Node.js 18+

**NFR-4.6.2**: Python implementation MUST work with Python 3.9+

**NFR-4.6.3**: Envelope format MUST be language-agnostic (JSON)

**NFR-4.6.4**: Envelopes MUST be interoperable across languages

**NFR-4.6.5**: API MUST be backward compatible within v2.x

---

## 5. Technical Constraints

### 5.1 Dependencies

**TC-5.1.1**: MUST use existing Sacred Tongues implementation

**TC-5.1.2**: MUST integrate with existing SCBE architecture

**TC-5.1.3**: MUST use Node.js crypto module (TypeScript)

**TC-5.1.4**: MUST use Python hashlib and hmac modules

**TC-5.1.5**: MUST NOT introduce new external dependencies

### 5.2 Integration Points

**TC-5.2.1**: MUST integrate with Sacred Tongues tokenizer

**TC-5.2.2**: MUST integrate with existing key management

**TC-5.2.3**: MUST integrate with Fleet Engine (Phase 3)

**TC-5.2.4**: MUST integrate with Roundtable Service (Phase 4)

**TC-5.2.5**: MUST support future PQC upgrade (ML-DSA signatures)

### 5.3 Platform Requirements

**TC-5.3.1**: TypeScript MUST compile to CommonJS (package.json type: "commonjs")

**TC-5.3.2**: TypeScript MUST target ES2020

**TC-5.3.3**: Python MUST support type hints

**TC-5.3.4**: Python MUST pass mypy type checking

**TC-5.3.5**: Both implementations MUST pass linting

---

## 6. Out of Scope

### 6.1 Not Included in v3.1.0

**OOS-6.1.1**: Fleet Engine integration (Phase 3 - v3.2.0)

**OOS-6.1.2**: Roundtable Service integration (Phase 4 - v3.3.0)

**OOS-6.1.3**: Autonomy Engine integration (Phase 5 - v3.4.0)

**OOS-6.1.4**: Vector Memory integration (Phase 6 - v3.5.0)

**OOS-6.1.5**: Workflow integrations (Phase 7 - v4.0.0)

### 6.2 Future Enhancements

**OOS-6.2.1**: Hybrid PQC signatures (ML-DSA + HMAC)

**OOS-6.2.2**: Encrypted payloads (SpiralSeal SS1 integration)

**OOS-6.2.3**: Distributed key management

**OOS-6.2.4**: Hardware security module (HSM) support

**OOS-6.2.5**: Audit logging and compliance reporting

---

## 7. Assumptions

### 7.1 Environment

**A-7.1.1**: Agents have synchronized clocks (±60s tolerance)

**A-7.1.2**: Agents have secure key storage

**A-7.1.3**: Network is reliable (no message loss)

**A-7.1.4**: Agents are trusted (Byzantine fault tolerance in Phase 4)

### 7.2 Usage

**A-7.2.1**: Envelopes are used for agent-to-agent communication

**A-7.2.2**: Payloads are JSON-serializable objects

**A-7.2.3**: Keys are rotated periodically (monthly recommended)

**A-7.2.4**: Replay window is sufficient for network latency

---

## 8. Risks and Mitigations

### 8.1 Security Risks

**R-8.1.1**: **Risk**: HMAC key compromise  
**Mitigation**: Key rotation, secure storage, audit logging

**R-8.1.2**: **Risk**: Replay attacks  
**Mitigation**: Nonce cache, timestamp validation, configurable window

**R-8.1.3**: **Risk**: Clock skew attacks  
**Mitigation**: ±60s tolerance, NTP synchronization

**R-8.1.4**: **Risk**: Policy bypass  
**Mitigation**: Strict policy enforcement, comprehensive tests

### 8.2 Performance Risks

**R-8.2.1**: **Risk**: Nonce cache memory growth  
**Mitigation**: LRU eviction, configurable cache size

**R-8.2.2**: **Risk**: Signature verification bottleneck  
**Mitigation**: Parallel verification, caching, profiling

**R-8.2.3**: **Risk**: JSON serialization overhead  
**Mitigation**: Efficient encoding, payload size limits

### 8.3 Integration Risks

**R-8.3.1**: **Risk**: TypeScript/Python incompatibility  
**Mitigation**: Comprehensive interop tests, shared test vectors

**R-8.3.2**: **Risk**: Breaking changes to Sacred Tongues  
**Mitigation**: Version pinning, integration tests

**R-8.3.3**: **Risk**: Fleet Engine API mismatch  
**Mitigation**: Design for future integration, clear interfaces

---

## 9. Success Metrics

### 9.1 Functional Metrics

**M-9.1.1**: 100% of acceptance criteria met

**M-9.1.2**: 95%+ test coverage (lines, functions, branches)

**M-9.1.3**: 0 critical security vulnerabilities

**M-9.1.4**: 100% interoperability (TypeScript ↔ Python)

### 9.2 Performance Metrics

**M-9.2.1**: <10ms envelope creation time (p95)

**M-9.2.2**: <5ms envelope verification time (p95)

**M-9.2.3**: 1000+ envelopes/second throughput

**M-9.2.4**: <100MB memory usage for 10K cached nonces

### 9.3 Quality Metrics

**M-9.3.1**: 0 failing tests

**M-9.3.2**: 0 linting errors

**M-9.3.3**: 0 type checking errors

**M-9.3.4**: 100% API documentation coverage

---

## 10. Glossary

**RWP**: Real World Protocol - Secure communication protocol for AI agents

**Envelope**: Signed message container with metadata and payload

**Sacred Tongue**: Domain-separated cryptographic identity (KO, AV, RU, CA, UM, DR)

**HMAC**: Hash-based Message Authentication Code

**Nonce**: Number used once - prevents replay attacks

**AAD**: Additional Authenticated Data - metadata included in signature

**Policy Level**: Security requirement (standard, strict, secret, critical)

**Replay Window**: Time period during which nonces are cached

**Keyring**: Collection of cryptographic keys indexed by tongue

**Kid**: Key ID - identifies which key version was used

---

## 11. References

### 11.1 Internal Documents

- `UNIFIED_VISION.md` - Complete platform vision
- `INTEGRATION_ROADMAP.md` - 18-month roadmap
- `src/symphonic_cipher/scbe_aethermoore/spiral_seal/sacred_tongues.py` - Sacred Tongues implementation
- `ARCHITECTURE_5_LAYERS.md` - SCBE architecture

### 11.2 Standards

- RFC 2104 - HMAC: Keyed-Hashing for Message Authentication
- RFC 4648 - Base64URL encoding
- NIST FIPS 180-4 - SHA-256 specification

### 11.3 Related Work

- USPTO Patent #63/961,403 - SCBE-AETHERMOORE system
- Sacred Tongues Protocol v1.0
- SpiralSeal SS1 Cipher specification

---

**Last Updated**: January 18, 2026  
**Version**: 1.0.0  
**Status**: Requirements Complete  
**Next Step**: Design Document

---

**Approval**:
- [ ] Product Owner
- [ ] Technical Lead
- [ ] Security Engineer
- [ ] QA Lead

---

*"From 'Do you have the key?' to 'Are you the right entity, in the right context, at the right time, doing the right thing, for the right reason?'"*

🛡️ **Secure. Semantic. Scalable.**
