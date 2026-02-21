# Decision Envelope v1

## Purpose
`DecisionEnvelopeV1` is the governance contract for autonomous action gating.

It is designed to be:
- protobuf-first for deterministic embedded encoding
- signed and replay-checkable
- auditable with deterministic MMR leaf hashing
- policy-authoritative (math does not invent policy)

## Canonical Files
- `proto/decision_envelope/v1/decision_envelope.proto`
- `src/governance/decision_envelope_v1.py`
- `schemas/decision_envelope_v1.schema.json`
- `schemas/examples/decision_envelope_v1.example.json`

## v1 Field Set

### Identity
- `identity.envelope_id`
- `identity.version` (`decision-envelope.v1`)
- `identity.mission_id`
- `identity.swarm_id`

### Authority
- `authority.issuer` (ground control authority)
- `authority.key_id`
- `authority.valid_from_ms`
- `authority.valid_until_ms`
- `authority.issued_at_ms`
- `authority.signature`
- `authority.signed_payload_hash`

### Scope
- `scope.agent_allowlist`
- `scope.capability_allowlist`
- `scope.target_allowlist`

### Constraints
- `constraints.mission_phase_allowlist`
- `constraints.resources.power_min`
- `constraints.resources.bandwidth_min`
- `constraints.resources.thermal_max`
- `constraints.max_risk_tier`

### Boundary Behavior
- `AUTO_ALLOW`
- `QUARANTINE`
- `DENY`

For `QUARANTINE` and `DENY`, recovery metadata is required:
- `recovery.path_id`
- `recovery.playbook_ref`
- `recovery.quorum_min`
- `recovery.human_ack_required`

### Audit Hooks
- `audit.mmr_fields`
- `audit.mmr_leaf_hash`

## Deterministic Signing Rules
1. Start from protobuf message.
2. Canonical signing bytes are deterministic protobuf serialization with:
   - `authority.signature = ""`
   - `authority.signed_payload_hash = ""`
   - `audit.mmr_leaf_hash = ""`
3. `signed_payload_hash = sha256(canonical_signing_bytes)`.
4. Sign `signed_payload_hash` (current runtime: HMAC-SHA256 placeholder; production can swap to ML-DSA).

## Deterministic MMR Rules
MMR leaf payload is canonical JSON with:
- sorted keys
- compact separators
- sorted/unique allowlists
- stable sort order for rules
- signature bytes excluded

`mmr_leaf_hash = sha256(canonical_mmr_payload)`.

Required MMR field list is `MMR_REQUIRED_FIELDS_V1` in `src/governance/decision_envelope_v1.py`.

## JSON / JSON-LD Projection
Use `envelope_to_json_projection(...)` for cockpit/policy tooling.

Projection includes `_canonical`:
- `proto_sha256` (required)
- `proto_b64` (optional, exact protobuf round-trip)

`json_projection_to_envelope(...)` reconstructs protobuf either:
- from `proto_b64`, or
- from JSON fields with canonical hash reference checks.

## Envelope-Only Evaluation Contract
`evaluate_action_inside_envelope(...)` only answers:
`given state, is action inside the signed envelope?`

It enforces:
- signed scope
- signed constraints
- signed boundary rules
- signed recovery metadata

It does not invent policy.

