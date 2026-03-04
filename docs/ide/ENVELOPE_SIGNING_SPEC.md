# SCBE Decision Envelope v1 -- Signing and Verification Specification

**Document version**: 1.0.0
**Date**: 2026-02-19
**Status**: NORMATIVE
**Classification**: Internal -- Engineering
**Patent reference**: USPTO Application #63/961,403
**Schema reference**: `proto/decision_envelope_v1.proto` (package `scbe.governance.v1`)

---

## Table of Contents

1. [Canonical Form for Signing](#1-canonical-form-for-signing)
2. [JSON-LD Projection Rules](#2-json-ld-projection-rules)
3. [MMR Audit Hook](#3-mmr-audit-hook)
4. [Quorum Signing Rules for QUARANTINE](#4-quorum-signing-rules-for-quarantine)
5. [Emergency Key Protocol](#5-emergency-key-protocol)
6. [Envelope Lifecycle](#6-envelope-lifecycle)
7. [Version Migration](#7-version-migration)

---

## 1. Canonical Form for Signing

### 1.1 Problem Statement

JSON encoding is non-deterministic: field ordering, whitespace, Unicode escaping, and number formatting vary across implementations. A signature over JSON bytes would break when re-serialized by a different library or platform. Protocol Buffers produce deterministic bytes for the same message content, making them suitable as the canonical signing format.

### 1.2 Signable Content Definition

The **signable content** of a `DecisionEnvelope` is the protobuf-encoded byte sequence produced when the following three fields are set to their zero-values:

| Field | Proto Type | Zero Value |
|---|---|---|
| `signature` | `bytes` | empty bytes (`b""`) |
| `counter_signature` | `bytes` | empty bytes (`b""`) |
| `canonical_hash` | `string` | empty string (`""`) |

All other fields retain their populated values. The resulting byte sequence is deterministic regardless of the language, library, or platform performing the serialization, because proto3 specifies a single canonical wire format for each field type.

### 1.3 Signing Procedure

```
Input:  DecisionEnvelope with all fields populated EXCEPT
        signature, counter_signature, and canonical_hash.

Step 1: Set signature = b""
        Set counter_signature = b""
        Set canonical_hash = ""

Step 2: signable_bytes = protobuf_serialize(envelope)
        // Deterministic: proto3 canonical encoding

Step 3: digest = sha256(signable_bytes)
        // 32-byte hash of the signable content

Step 4: signature = sign(digest, issuer_private_key, sig_algorithm)
        // ML-DSA-65: 3309-byte signature
        // SHA256_PLACEHOLDER: hmac_sha256(digest, shared_secret)

Step 5: Set envelope.signature = signature

Step 6: (Optional dual authorization)
        counter_signature = sign(digest, counter_authority_private_key, sig_algorithm)
        Set envelope.counter_signature = counter_signature

Step 7: full_bytes = protobuf_serialize(envelope)
        // Now includes signature and counter_signature

Step 8: canonical_hash = hex(sha256(full_bytes))
        // Lowercase hex encoding of the SHA-256 digest

Step 9: Set envelope.canonical_hash = canonical_hash
```

### 1.4 Verification Procedure

```
Input:  DecisionEnvelope received (all fields populated)

Step 1: saved_sig = envelope.signature
        saved_counter = envelope.counter_signature
        saved_hash = envelope.canonical_hash

Step 2: Set envelope.signature = b""
        Set envelope.counter_signature = b""
        Set envelope.canonical_hash = ""

Step 3: signable_bytes = protobuf_serialize(envelope)

Step 4: digest = sha256(signable_bytes)

Step 5: issuer_pubkey = key_registry.lookup(envelope.key_id)
        verify(saved_sig, digest, issuer_pubkey, envelope.sig_algorithm)
        // Reject if verification fails

Step 6: If saved_counter is non-empty:
          counter_pubkey = key_registry.lookup_counter(envelope.key_id)
          verify(saved_counter, digest, counter_pubkey, envelope.sig_algorithm)
          // Reject if verification fails

Step 7: Restore envelope.signature = saved_sig
        Restore envelope.counter_signature = saved_counter
        Restore envelope.canonical_hash = saved_hash

Step 8: (Optional integrity check)
        full_bytes = protobuf_serialize(envelope)
        expected_hash = hex(sha256(full_bytes_without_canonical_hash))
        // Note: canonical_hash is self-referential; verify by recomputing
        // from the envelope with canonical_hash zeroed
```

### 1.5 Determinism Guarantees

Proto3 canonical encoding guarantees:

- Fields are serialized in field number order.
- Default-valued fields (zero, empty, false) are omitted from the wire format.
- There is exactly one valid encoding for any given message content.
- Unknown fields are preserved in their received wire order (forward compatibility).

These guarantees mean that `signable_bytes` will be identical whether computed by a TypeScript implementation (using `protobufjs`), a Python implementation (using `protobuf`), a Rust implementation (using `prost`), or a Go implementation (using `protoc-gen-go`).

### 1.6 SHA256_PLACEHOLDER Algorithm (Development Only)

For development and testing without PQC library dependencies:

```
signature = hmac_sha256(key=shared_secret, message=digest)
```

The `shared_secret` is a 32-byte value configured in the development environment. The `key_id` field uses the format `"sha256-hmac:<key-name>"` to identify the shared secret.

**This algorithm MUST NOT be used in flight hardware or production deployments.** Validators in production mode reject envelopes with `sig_algorithm = SHA256_PLACEHOLDER`.

### 1.7 ML-DSA-65 Algorithm (Production)

For flight envelopes and production deployments:

- **Standard**: NIST FIPS 204 (Module-Lattice-Based Digital Signature Algorithm)
- **Security level**: 3 (128-bit quantum security)
- **Public key size**: 1952 bytes
- **Private key size**: 4032 bytes
- **Signature size**: 3309 bytes
- **Key ID format**: `"ml-dsa-65:<sha256-fingerprint-of-public-key>"`

The signing operation is:

```
signature = ml_dsa_65_sign(private_key, digest)
```

The verification operation is:

```
valid = ml_dsa_65_verify(public_key, digest, signature)
```

Key management follows the existing SCBE key management system (`src/crypto/kms.ts`, `src/crypto/pqc.ts`).

---

## 2. JSON-LD Projection Rules

### 2.1 Purpose

The Ground Cockpit and policy tooling operate in web environments where JSON is the native data format. The JSON-LD projection provides a human-readable, web-compatible representation of the signed protobuf envelope while maintaining cryptographic linkage to the canonical binary.

### 2.2 JSON-LD Context

The following `@context` maps protobuf field names to IRIs for semantic interoperability:

```json
{
  "@context": {
    "@version": 1.1,
    "scbe": "https://scbe-aethermoore.dev/ns/governance/v1#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",

    "envelopeId":          { "@id": "scbe:envelopeId",          "@type": "xsd:string" },
    "version":             { "@id": "scbe:version",             "@type": "xsd:unsignedInt" },
    "missionId":           { "@id": "scbe:missionId",           "@type": "xsd:string" },
    "swarmId":             { "@id": "scbe:swarmId",             "@type": "xsd:string" },
    "issuerId":            { "@id": "scbe:issuerId",            "@type": "xsd:string" },
    "keyId":               { "@id": "scbe:keyId",               "@type": "xsd:string" },
    "sigAlgorithm":        { "@id": "scbe:sigAlgorithm",        "@type": "xsd:string" },
    "signature":           { "@id": "scbe:signature",           "@type": "xsd:base64Binary" },
    "counterSignature":    { "@id": "scbe:counterSignature",    "@type": "xsd:base64Binary" },
    "signedAtMs":          { "@id": "scbe:signedAtMs",          "@type": "xsd:long" },
    "validFromMs":         { "@id": "scbe:validFromMs",         "@type": "xsd:long" },
    "validUntilMs":        { "@id": "scbe:validUntilMs",        "@type": "xsd:long" },
    "missionPhase":        { "@id": "scbe:missionPhase",        "@type": "xsd:string" },
    "allowedAgentIds":     { "@id": "scbe:allowedAgentIds",     "@container": "@set" },
    "allowedTargetIds":    { "@id": "scbe:allowedTargetIds",    "@container": "@set" },
    "allowedCapabilities": { "@id": "scbe:allowedCapabilities", "@container": "@set" },
    "resourceConstraints": { "@id": "scbe:resourceConstraints", "@type": "@id" },
    "maxRiskTier":         { "@id": "scbe:maxRiskTier",         "@type": "xsd:string" },
    "scbeThresholds":      { "@id": "scbe:scbeThresholds",      "@type": "@id" },
    "rules":               { "@id": "scbe:rules",               "@container": "@list" },
    "emergencyKeyHash":    { "@id": "scbe:emergencyKeyHash",    "@type": "xsd:base64Binary" },
    "canonicalHash":       { "@id": "scbe:canonicalHash",       "@type": "xsd:string" },
    "protobufHash":        { "@id": "scbe:protobufHash",        "@type": "xsd:string" },

    "minPower":            { "@id": "scbe:minPower",            "@type": "xsd:float" },
    "minBandwidth":        { "@id": "scbe:minBandwidth",        "@type": "xsd:float" },
    "minThermalMargin":    { "@id": "scbe:minThermalMargin",    "@type": "xsd:float" },
    "minPropellant":       { "@id": "scbe:minPropellant",       "@type": "xsd:float" },

    "allowMaxCost":            { "@id": "scbe:allowMaxCost",            "@type": "xsd:double" },
    "quarantineMaxCost":       { "@id": "scbe:quarantineMaxCost",       "@type": "xsd:double" },
    "allowMinCoherence":       { "@id": "scbe:allowMinCoherence",       "@type": "xsd:double" },
    "quarantineMinCoherence":  { "@id": "scbe:quarantineMinCoherence",  "@type": "xsd:double" },
    "allowMaxDrift":           { "@id": "scbe:allowMaxDrift",           "@type": "xsd:double" },
    "quarantineMaxDrift":      { "@id": "scbe:quarantineMaxDrift",      "@type": "xsd:double" },

    "pattern":             { "@id": "scbe:pattern",             "@type": "xsd:string" },
    "boundary":            { "@id": "scbe:boundary",            "@type": "xsd:string" },
    "maxExecutions":       { "@id": "scbe:maxExecutions",       "@type": "xsd:unsignedInt" },
    "resourceFloor":       { "@id": "scbe:resourceFloor",       "@type": "@id" },
    "recoveryPath":        { "@id": "scbe:recoveryPath",        "@type": "@id" },
    "resourceName":        { "@id": "scbe:resourceName",        "@type": "xsd:string" },
    "minimum":             { "@id": "scbe:minimum",             "@type": "xsd:float" },
    "type":                { "@id": "scbe:recoveryType",        "@type": "xsd:string" },
    "description":         { "@id": "scbe:description",         "@type": "xsd:string" },
    "requiredQuorumVotes": { "@id": "scbe:requiredQuorumVotes", "@type": "xsd:unsignedInt" }
  }
}
```

### 2.3 Field Name Mapping

The JSON projection uses **camelCase** field names to match the existing TypeScript type conventions in the SCBE codebase. The mapping from proto3 snake_case to JSON camelCase is:

| Proto3 Field | JSON Field |
|---|---|
| `envelope_id` | `envelopeId` |
| `mission_id` | `missionId` |
| `swarm_id` | `swarmId` |
| `issuer_id` | `issuerId` |
| `key_id` | `keyId` |
| `sig_algorithm` | `sigAlgorithm` |
| `counter_signature` | `counterSignature` |
| `signed_at_ms` | `signedAtMs` |
| `valid_from_ms` | `validFromMs` |
| `valid_until_ms` | `validUntilMs` |
| `mission_phase` | `missionPhase` |
| `allowed_agent_ids` | `allowedAgentIds` |
| `allowed_target_ids` | `allowedTargetIds` |
| `allowed_capabilities` | `allowedCapabilities` |
| `resource_constraints` | `resourceConstraints` |
| `max_risk_tier` | `maxRiskTier` |
| `scbe_thresholds` | `scbeThresholds` |
| `emergency_key_hash` | `emergencyKeyHash` |
| `canonical_hash` | `canonicalHash` |
| `min_power` | `minPower` |
| `min_bandwidth` | `minBandwidth` |
| `min_thermal_margin` | `minThermalMargin` |
| `min_propellant` | `minPropellant` |
| `allow_max_cost` | `allowMaxCost` |
| `quarantine_max_cost` | `quarantineMaxCost` |
| `allow_min_coherence` | `allowMinCoherence` |
| `quarantine_min_coherence` | `quarantineMinCoherence` |
| `allow_max_drift` | `allowMaxDrift` |
| `quarantine_max_drift` | `quarantineMaxDrift` |
| `max_executions` | `maxExecutions` |
| `resource_floor` | `resourceFloor` |
| `recovery_path` | `recoveryPath` |
| `resource_name` | `resourceName` |
| `required_quorum_votes` | `requiredQuorumVotes` |

### 2.4 The protobufHash Field

The JSON projection includes an additional field not present in the protobuf schema:

```json
{
  "protobufHash": "a3f2b1c4d5e6..."
}
```

This is the SHA-256 hex digest of the **canonical protobuf bytes** (the full serialized envelope including signatures, but with `canonical_hash` zeroed). It allows the Ground Cockpit to:

1. Display and work with the human-readable JSON form.
2. Reference the exact signed protobuf binary by hash.
3. Verify that a protobuf binary matches the JSON projection by comparing hashes.

The `protobufHash` value equals the `canonicalHash` field in the protobuf envelope.

### 2.5 Enum Encoding in JSON

Protobuf enum values are encoded as their **string names** (not numeric values) in the JSON projection:

```json
{
  "missionPhase": "SURFACE_OPS",
  "maxRiskTier": "MEDIUM",
  "sigAlgorithm": "ML_DSA_65",
  "rules": [
    {
      "pattern": "telemetry.*",
      "boundary": "AUTO_ALLOW"
    }
  ]
}
```

This matches proto3's canonical JSON mapping and is human-readable.

### 2.6 Binary Fields in JSON

Fields of type `bytes` (`signature`, `counter_signature`, `emergency_key_hash`) are encoded as **standard base64** (RFC 4648 section 4) in the JSON projection:

```json
{
  "signature": "TWFycyBpcyBhd2Vz...",
  "emergencyKeyHash": "x3Jv8k9p..."
}
```

### 2.7 Round-Trip Guarantee

The round-trip from JSON to protobuf and back preserves semantic equivalence:

```
JSON (source of truth: Ground Cockpit)
  -> Parse JSON to DecisionEnvelope message object
  -> Serialize to protobuf bytes
  -> Sign (produces signature)
  -> Serialize signed envelope to protobuf bytes
  -> Compute protobufHash = sha256(signed_protobuf_bytes)
  -> Project back to JSON, including protobufHash
  -> JSON + protobufHash (delivered to Ground Cockpit)
```

The JSON form itself is NOT signed. The protobuf bytes are signed. The JSON references the signed protobuf via `protobufHash`. This avoids all JSON canonicalization problems while giving the Ground Cockpit a usable working format.

### 2.8 Example JSON-LD Envelope

```json
{
  "@context": "https://scbe-aethermoore.dev/ns/governance/v1/context.jsonld",
  "@type": "DecisionEnvelope",
  "envelopeId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "version": 1,
  "missionId": "ARES-IV",
  "swarmId": "swarm-alpha",
  "issuerId": "gc://jpl-mission-control",
  "keyId": "ml-dsa-65:sha256:abcdef1234567890",
  "sigAlgorithm": "ML_DSA_65",
  "signature": "TWFycyBpcyBhd2Vzb21lLi...",
  "counterSignature": "",
  "signedAtMs": 1771459200000,
  "validFromMs": 1771459200000,
  "validUntilMs": 1771545600000,
  "missionPhase": "SURFACE_OPS",
  "allowedAgentIds": ["rover-alpha-01", "rover-alpha-02", "drone-scout-03"],
  "allowedTargetIds": [],
  "allowedCapabilities": ["NAVIGATE", "SAMPLE", "PHOTOGRAPH", "ANALYZE", "COMMUNICATE"],
  "resourceConstraints": {
    "minPower": 0.15,
    "minBandwidth": 0.05,
    "minThermalMargin": 0.10,
    "minPropellant": 0.0
  },
  "maxRiskTier": "HIGH",
  "scbeThresholds": {
    "allowMaxCost": 2.0,
    "quarantineMaxCost": 10.0,
    "allowMinCoherence": 0.85,
    "quarantineMinCoherence": 0.50,
    "allowMaxDrift": 0.10,
    "quarantineMaxDrift": 0.40
  },
  "rules": [
    {
      "pattern": "telemetry.*",
      "boundary": "AUTO_ALLOW",
      "maxExecutions": 0,
      "resourceFloor": null,
      "recoveryPath": null
    },
    {
      "pattern": "navigation.*",
      "boundary": "AUTO_ALLOW",
      "maxExecutions": 0,
      "resourceFloor": null,
      "recoveryPath": null
    },
    {
      "pattern": "drill.*",
      "boundary": "QUARANTINE",
      "maxExecutions": 0,
      "resourceFloor": {
        "resourceName": "power",
        "minimum": 0.40
      },
      "recoveryPath": {
        "type": "BFT_QUORUM",
        "description": "Retry with swarm quorum after drill safety review.",
        "requiredQuorumVotes": 4
      }
    },
    {
      "pattern": "habitat.atmosphere.*",
      "boundary": "DENY",
      "maxExecutions": 0,
      "resourceFloor": null,
      "recoveryPath": {
        "type": "EMERGENCY_KEY",
        "description": "Commander emergency override required for atmosphere changes.",
        "requiredQuorumVotes": 0
      }
    },
    {
      "pattern": "**",
      "boundary": "QUARANTINE",
      "maxExecutions": 0,
      "resourceFloor": null,
      "recoveryPath": {
        "type": "EARTH_SYNC",
        "description": "Wait for Ground Control decision in next comms window.",
        "requiredQuorumVotes": 0
      }
    }
  ],
  "emergencyKeyHash": "x3Jv8k9pQ2...",
  "canonicalHash": "a3f2b1c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2",
  "protobufHash": "a3f2b1c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2"
}
```

---

## 3. MMR Audit Hook

### 3.1 Overview

Every action evaluated against a `DecisionEnvelope` produces an `ActionReport`. These reports form the leaves of a Merkle Mountain Range (MMR), creating an append-only, tamper-evident audit chain that Ground Control can independently verify.

The MMR is chosen over a standard Merkle tree because:
- Append-only: new leaves can be added without recomputing the entire tree.
- Proof size: O(log n) inclusion proofs.
- No rebalancing: the structure grows monotonically, suitable for embedded systems with limited compute.

### 3.2 Leaf Hash Computation

When an action is evaluated against an envelope, the following procedure produces the MMR leaf:

```
Step 1: Populate all fields of the ActionReport message.
        - If the action triggered a QUARANTINE vote, populate
          quorum_summary BEFORE hashing.
        - If the action used an emergency override, set
          emergency_override = true.

Step 2: report_bytes = protobuf_serialize(action_report)
        // Deterministic proto3 encoding, same guarantees
        // as envelope signing (section 1.5).

Step 3: leaf_hash = sha256(report_bytes)
        // 32-byte digest becomes the MMR leaf.

Step 4: Append leaf_hash to the MMR.
        // The MMR implementation maintains peak hashes
        // and computes interior nodes on-the-fly.
```

### 3.3 Determinism Requirements

For Ground Control to independently reconstruct any leaf hash:

1. **All ActionReport fields must be populated before hashing.** Optional fields (like `quorum_summary`) use their proto3 default values (empty message) if not applicable. This means the hash of an AUTO_ALLOW action with no quorum will differ from the hash of the same action with an empty QuorumSummary explicitly set -- because proto3 omits default-valued fields from the wire format. Implementations MUST NOT explicitly set optional sub-messages to their default values unless the field is semantically meaningful.

2. **Timestamps must be the exact values recorded at decision time.** No rounding, no timezone adjustment. The `timestamp_ms` is the agent's local monotonic clock value.

3. **Hash fields (`state_hash`, `resource_hash`) must be computed before the ActionReport is serialized.** They are inputs, not outputs.

### 3.4 Ground Control Verification

Ground Control receives:
- The MMR peaks (periodic uplink during comms windows).
- Individual ActionReports (streamed or batched).

Verification procedure:
1. For each received ActionReport, compute `sha256(protobuf_serialize(report))`.
2. Verify the computed hash matches the corresponding MMR leaf.
3. Verify the MMR peaks by recomputing the MMR from all received leaves.
4. Any mismatch indicates tampering or data corruption.

### 3.5 MMR Compaction

The MMR grows monotonically. On memory-constrained Mars hardware, periodic compaction is permitted:

- Leaves older than the current envelope's `valid_from_ms` may be pruned after Ground Control acknowledges receipt.
- Pruned leaves are replaced with their subtree root hash, preserving the ability to verify the remaining leaves.
- The compaction event itself is logged as a special ActionReport with `domain = "system"` and `action_id = "mmr_compaction"`.

---

## 4. Quorum Signing Rules for QUARANTINE

### 4.1 When Quorum Applies

A BFT quorum vote is triggered when:
1. An action matches an envelope rule with `boundary = QUARANTINE`, AND
2. The SCBE pipeline's geometric assessment does not override the boundary to DENY (i.e., the action passes the quarantine thresholds), AND
3. The action's risk tier does not exceed `max_risk_tier`.

### 4.2 Vote Message Format

Each voting agent signs a deterministic vote message:

```
vote_payload = sha256(
  envelope_id              ||   // UTF-8 bytes of the envelope ID
  action_report_bytes      ||   // Protobuf-serialized ActionReport (with
                                // quorum_summary left at default/empty)
  vote_string                   // UTF-8 bytes: "APPROVE" or "REJECT"
)

vote_signature = sign(vote_payload, agent_private_key, sig_algorithm)
```

The `||` operator denotes byte concatenation. There are no delimiters between the components; the envelope_id and vote_string are variable-length but unambiguous because the ActionReport's protobuf encoding is self-delimiting.

### 4.3 Quorum Threshold

Quorum is met when the number of valid APPROVE signatures reaches the required threshold:

```
threshold = max(
  rule.recovery_path.required_quorum_votes,   // Envelope policy (typically 4)
  bft_engine.quorum_size                       // BFT minimum: 2f+1 (typically 3)
)
```

For the standard SCBE Mars configuration:
- **f = 1** (tolerate 1 Byzantine fault)
- **n >= 3f + 1 = 4** (minimum 4 agents in swarm)
- **BFT quorum = 2f + 1 = 3** (mathematical minimum)
- **Envelope policy = 4** (additional safety margin)
- **Effective threshold = max(4, 3) = 4** votes required

With a typical swarm of 6 agents, this means 4 out of 6 must APPROVE.

### 4.4 Vote Collection Procedure

```
Step 1: The requesting agent broadcasts the ActionReport (with
        quorum_summary empty) to all agents in the swarm.

Step 2: Each receiving agent independently:
        a. Verifies the requesting agent is in allowed_agent_ids.
        b. Verifies the action's capability is in allowed_capabilities.
        c. Runs the SCBE 14-layer pipeline on the action context.
        d. Decides APPROVE or REJECT based on its own assessment.
        e. Signs the vote_payload and sends the signature back.

Step 3: The requesting agent collects signatures for a bounded
        time window (default: 30 seconds, configurable per-rule).

Step 4: If APPROVE count >= threshold:
        - Populate quorum_summary with votes, threshold, total_agents,
          and voter_ids (APPROVE voters only).
        - Set final_decision = EXECUTE.
        - Create the complete ActionReport (now with quorum_summary).
        - Hash and append to MMR.

Step 5: If APPROVE count < threshold after timeout:
        - Populate quorum_summary with the final vote counts.
        - Set final_decision = DENIED.
        - Invoke the rule's recovery_path (if any).
        - Hash and append to MMR.
```

### 4.5 Byzantine Fault Handling

- **Non-responsive agents**: Count as abstentions (not votes). Do not count toward `total_agents` for quorum calculation. If too many agents are non-responsive such that `responsive_agents < threshold`, the vote fails and recovery_path is invoked.
- **Invalid signatures**: Discarded silently. The signing agent may be Byzantine.
- **Duplicate votes**: Only the first vote from each agent_id is counted. Subsequent votes from the same agent are discarded.
- **Conflicting votes**: An agent that sends both APPROVE and REJECT is treated as Byzantine. Both votes are discarded and the agent is flagged for diagnostic review.

### 4.6 Vote Privacy

Only APPROVE voter IDs are recorded in the QuorumSummary. This is a deliberate design choice:

- It prevents targeted retaliation against agents that voted REJECT.
- It provides accountability for agents that approved a potentially dangerous action.
- The count of non-approve voters can be inferred: `total_agents - len(voter_ids)`.

---

## 5. Emergency Key Protocol

### 5.1 Key Properties

| Property | Value |
|---|---|
| Key length | 32 bytes (256 bits) |
| Storage | Tamper-resistant hardware on habitat module |
| Knowledge | Mission commander only |
| Transmission | NEVER transmitted over any channel |
| Envelope field | `emergency_key_hash = sha256(key)` (32 bytes) |

The emergency key is a pre-shared secret established before launch and loaded into the habitat's tamper-resistant hardware module. It is NOT stored in the envelope, NOT transmitted during the mission, and NOT accessible to any software system. Only the SHA-256 hash of the key is stored in the envelope for verification.

### 5.2 Override Procedure

```
Precondition: An action has been DENIED by envelope policy, SCBE pipeline,
              or failed quorum vote. The mission commander determines that
              the action is operationally necessary despite the denial.

Step 1: Mission commander physically accesses the habitat command console.
        // No remote override is possible. Physical presence required.

Step 2: Commander enters the 32-byte emergency key via the console's
        secure input mechanism (hardware keypad or hardware token reader).

Step 3: System computes: presented_hash = sha256(presented_key)

Step 4: System compares: presented_hash == envelope.emergency_key_hash

Step 5: If match:
          a. Action is authorized.
          b. ActionReport is created with emergency_override = true.
          c. ActionReport is hashed and appended to MMR.
          d. A priority notification is queued for Ground Control
             (transmitted in the first available comms window).
          e. The emergency key is wiped from volatile memory immediately
             after hash comparison.

Step 6: If no match:
          a. Override attempt is rejected.
          b. A FAILED_EMERGENCY_OVERRIDE event is logged to the MMR.
          c. Three consecutive failed attempts trigger a 60-minute
             lockout of the emergency override mechanism.
          d. Ground Control is notified of failed attempts.
```

### 5.3 Ground Control Notification

All emergency overrides generate a priority notification with:

- The full ActionReport (including `emergency_override = true`).
- The timestamp of the override.
- The action that was originally DENIED and the reason for denial.
- The mission commander's agent_id.

This notification is transmitted in the first available comms window, ahead of regular telemetry. Ground Control reviews all emergency overrides and may choose to:

1. **Acknowledge**: The override was justified. No further action.
2. **Revoke**: Uplink a new envelope that explicitly addresses the situation.
3. **Investigate**: Request additional diagnostic data from the swarm.

### 5.4 Key Rotation

The emergency key cannot be rotated during the mission without a comms window. To rotate:

1. Ground Control generates a new 32-byte key.
2. The new key is securely transmitted to the habitat (encrypted with ML-KEM-768).
3. A new envelope is uplinked with `emergency_key_hash = sha256(new_key)`.
4. The commander loads the new key into the tamper-resistant hardware.
5. The old key is destroyed.

---

## 6. Envelope Lifecycle

### 6.1 State Diagram

```
                                 Phase transition
                                 matches phase
  +--------+    Ground     +--------+    Onboard     +----------+
  | CREATE |----Control--->| SIGN   |----uplink----->| VALIDATE |
  +--------+    signs      +--------+                +----------+
                                                          |
                                                     sig valid?
                                                     version ok?
                                                     phase ok?
                                                          |
                                              +-----------+-----------+
                                              |                       |
                                          valid                   invalid
                                              |                       |
                                              v                       v
                                        +-----------+           +-----------+
              +------------------------>| QUEUED    |           | REJECTED  |
              |   (not current phase    +-----------+           +-----------+
              |    or another envelope       |
              |    is already active)        | Current envelope expires
              |                              | OR phase transition matches
              |                              v
              |                        +----------+
              |                        | ACTIVATE |
              |                        +----------+
              |                              |
              |                              v
              |                        +----------+     Action
              |                        | EVALUATE |<----requests
              |                        +----------+     from agents
              |                              |
              |                    +---------+---------+
              |                    |                   |
              |              valid_until_ms        Replaced by
              |              reached               new envelope
              |                    |                   |
              |                    v                   v
              |               +----------+      +----------+
              +---------------| EXPIRED  |      | REPLACED |
                              +----------+      +----------+
                                   |
                          No replacement
                          envelope available
                                   |
                                   v
                          All actions QUEUED
                          until comms window
```

### 6.2 State Definitions

| State | Description |
|---|---|
| **CREATE** | Ground Control authors the envelope with all policy fields. Unsigned. |
| **SIGN** | Ground Control signs the envelope (and optionally counter-signs). The canonical protobuf bytes and canonical_hash are computed. |
| **VALIDATE** | The onboard system receives the signed envelope and verifies: (a) signature validity, (b) version compatibility, (c) mission_phase is known, (d) valid_from_ms is in the future or now, (e) issuer_id is in the trusted issuer registry. |
| **REJECTED** | Validation failed. The envelope is discarded. An error is logged and Ground Control is notified in the next comms window. |
| **QUEUED** | The envelope is valid but cannot activate yet. Either another envelope is currently active, or the envelope's mission_phase does not match the current phase. Multiple envelopes can be queued simultaneously (for different upcoming phases). |
| **ACTIVATE** | The envelope becomes the active governance contract for its swarm. All agent actions are now evaluated against this envelope's rules, thresholds, and constraints. Only one envelope can be ACTIVE per swarm. |
| **EVALUATE** | The steady-state: every agent action is evaluated against the active envelope. ActionReports are generated and appended to the MMR. |
| **EXPIRED** | `valid_until_ms` has been reached. The envelope can no longer authorize actions. If a queued envelope exists for the current phase, it activates. If not, all actions become QUEUED. |
| **REPLACED** | A new envelope has been activated for the same swarm. The old envelope is archived (retained in storage for audit purposes but no longer authoritative). |

### 6.3 Concurrency Rule

**Only one envelope can be ACTIVE per swarm at any given time.**

This is a hard invariant enforced by the onboard governance engine. If two envelopes somehow reach ACTIVATE state simultaneously (e.g., due to a race condition in comms processing), the envelope with the later `signed_at_ms` wins and the earlier one transitions to REPLACED.

### 6.4 Phase Transition Behavior

When the mission transitions to a new phase (e.g., TRANSIT to ORBIT_INSERT):

1. The active envelope's `mission_phase` is compared to the new phase.
2. If they do not match, the active envelope transitions to EXPIRED (regardless of `valid_until_ms`).
3. The queued envelopes are scanned for one whose `mission_phase` matches the new phase AND whose `valid_from_ms <= now`.
4. If found, that envelope transitions to ACTIVATE.
5. If not found, all actions become QUEUED and the system waits for a new envelope from Ground Control.

### 6.5 Comms Loss Scenario

If the current envelope expires and no replacement is available (comms blackout):

1. All agent actions transition to QUEUED status.
2. Agents continue life-support and passive telemetry (hardcoded safety-critical actions that do not require envelope authorization).
3. Queued actions are held in a FIFO buffer (max 1024 entries; oldest entries are dropped if the buffer fills).
4. When a comms window opens, Ground Control is notified of the expired envelope and the queued action backlog.
5. Ground Control uplinks a new envelope, which activates and begins processing the queued actions (if the new envelope's rules permit them).

---

## 7. Version Migration

### 7.1 Version Identification

Every `DecisionEnvelope` carries a `version` field (uint32):

| Version | Status | Schema File |
|---|---|---|
| 1 | Current (this document) | `proto/decision_envelope_v1.proto` |
| 2+ | Future (not yet defined) | TBD |

### 7.2 Compatibility Rules

Proto3 provides built-in forward compatibility through unknown field preservation:

1. **Adding new fields**: A v2 envelope received by a v1 system will have the new fields preserved as unknown fields in the wire format. The v1 system can still verify the signature (because the signable content bytes include the unknown fields) and evaluate the envelope using the fields it understands.

2. **Removing fields**: Fields must never be removed in future versions. They can be deprecated (marked with a comment) but their field numbers must not be reused.

3. **Changing field types**: Field types must not change. If a field needs a different type, add a new field with a new number and deprecate the old one.

4. **Adding enum values**: New enum values can be added freely. A v1 system receiving an unknown enum value will see it as the numeric value. Validators should treat unknown enum values as UNSPECIFIED (triggering fail-closed behavior for safety-critical enums like BoundaryType).

### 7.3 Minimum Supported Version

Both Ground Control and onboard systems maintain a `minimum_supported_version` configuration:

```
IF envelope.version < minimum_supported_version:
    REJECT envelope (version too old, may lack required security features)

IF envelope.version > maximum_understood_version:
    ACCEPT envelope but log a warning
    // Unknown fields are preserved; known fields are evaluated normally
    // This allows a v1 system to accept a v2 envelope (degraded but functional)
```

### 7.4 Version Negotiation

During comms windows, Ground Control and the onboard system exchange version capabilities:

```json
{
  "minSupportedVersion": 1,
  "maxUnderstoodVersion": 1,
  "preferredVersion": 1
}
```

Ground Control always uplinks envelopes at the version that both sides support. If the onboard system has been updated to support v2 but Ground Control has not, Ground Control continues sending v1 envelopes (which the v2 system fully supports).

### 7.5 Migration Procedure for v2

When v2 is defined:

1. The new schema is published as `proto/decision_envelope_v2.proto` (or as additions to the v1 file with new field numbers).
2. Ground Control software is updated first (it must understand v2 to create v2 envelopes).
3. Onboard software is updated during a maintenance window (OTA update during comms window).
4. Ground Control begins sending v2 envelopes only after confirming the onboard system reports `maxUnderstoodVersion >= 2`.
5. A transition period allows both v1 and v2 envelopes to coexist in the queue.
6. After the transition period, `minimum_supported_version` is raised to 2 on both sides.

---

## References

### Internal

| Document | Location |
|---|---|
| Decision Envelope v1 Protobuf Schema | `proto/decision_envelope_v1.proto` |
| BFT Consensus Implementation | `src/ai_brain/bft-consensus.ts` |
| SHA-256 Hash-Chained Audit Logger | `src/ai_brain/audit.ts` |
| 21D Brain State Types | `src/ai_brain/types.ts` |
| Post-Quantum Cryptography | `src/crypto/pqc.ts` |
| Sealed Envelope Encryption | `src/crypto/envelope.ts` |
| Key Management | `src/crypto/kms.ts` |
| Replay Guard | `src/crypto/replayGuard.ts` |
| 14-Layer Pipeline | `src/harmonic/pipeline14.ts` |
| Harmonic Wall (L12) | `src/harmonic/harmonicScaling.ts` |
| Hyperbolic Operations (L5-L7) | `src/harmonic/hyperbolic.ts` |
| IDE Threat Model | `docs/ide/THREAT_MODEL.md` |
| IDE Architecture Options | `docs/ide/ARCH_OPTIONS.md` |
| IDE MVP Specification | `docs/ide/MVP_SPEC.md` |
| Existing Decision Record Schema | `schemas/decision_record.schema.json` |

### External Standards

| Standard | Reference |
|---|---|
| NIST FIPS 204 (ML-DSA) | Module-Lattice-Based Digital Signature Algorithm |
| NIST FIPS 203 (ML-KEM) | Module-Lattice-Based Key-Encapsulation Mechanism |
| Proto3 Language Specification | https://protobuf.dev/programming-guides/proto3/ |
| Proto3 Canonical Encoding | https://protobuf.dev/programming-guides/encoding/ |
| JSON-LD 1.1 | https://www.w3.org/TR/json-ld11/ |
| RFC 4648 (Base64) | https://datatracker.ietf.org/doc/html/rfc4648 |
| Merkle Mountain Range | https://github.com/opentimestamps/opentimestamps-server/blob/master/doc/merkle-mountain-range.md |
| BFT Consensus (n >= 3f+1) | Lamport, Shostak, Pease. "The Byzantine Generals Problem" (1982) |

---

*This specification is normative for all SCBE-AETHERMOORE implementations that create, sign, verify, or evaluate Decision Envelopes. Any deviation from the procedures defined here constitutes a protocol violation and must be reported as a security incident.*
