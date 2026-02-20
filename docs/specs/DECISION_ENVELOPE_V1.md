# Decision Envelope v1 (Protobuf-First)

This document defines the SCBE Decision Envelope contract used by quorum, harmonic wall evaluation, and MMR audit anchoring.

## Canonical Source

- Canonical wire contract: `proto/decision_envelope/v1/decision_envelope.proto`
- JSON projection schema: `schemas/decision_envelope_v1.schema.json`
- Example projection: `schemas/examples/decision_envelope_v1.example.json`

## Design Goal

Policy is encoded in a signed envelope. Runtime math only answers:

- "Given action/state, is this inside the envelope constraints?"

No implicit policy is invented by evaluators.

## v1 Required Blocks

1. Identity
- `envelope_id`, `schema_version`, `mission_id`, `swarm_id`

2. Authority
- `issuer`, `key_id`, validity window, signature metadata

3. Scope
- explicit allowlists for `agents`, `capabilities`, `targets`

4. Constraints
- `mission_phase_allowlist`
- `resource_floors`: `power_mw_min`, `bandwidth_kbps_min`, `thermal_headroom_c_min`
- `max_risk_tier`
- harmonic wall params: `scarcity_limit`, `base`, `alpha`

5. Boundary behavior
- `AUTO_ALLOW | QUARANTINE | DENY`
- Recovery metadata required for `QUARANTINE` and `DENY`

6. Audit hooks
- deterministic canonicalization marker
- `signed_protobuf_sha256`
- `mmr_leaf_sha256`, `mmr_prev_root_sha256`, `mmr_leaf_index`
- explicit `hash_fields`

## Deterministic Signing and Hashing Rules

1. Serialize `DecisionEnvelopeV1` using deterministic protobuf encoding.
2. Compute `signed_protobuf_sha256 = SHA256(deterministic_protobuf_bytes)`.
3. Sign the deterministic bytes (or the SHA256 digest, depending on signer API).
4. Store signature in `SignatureBlock`.
5. Build MMR leaf hash from deterministic, ordered fields listed in `audit.hash_fields`.
6. Record `mmr_leaf_sha256` and append to MMR chain.

## JSON Projection Rule

JSON exists for cockpit/policy tooling. It must either:

- round-trip exactly to the same deterministic protobuf bytes, or
- carry `authority.signature.signed_protobuf_sha256` / `audit.signed_protobuf_sha256`
  that matches the signed protobuf artifact.

v1 enforces the second path as minimum interop requirement.

## Predicate Evaluator

Reference evaluator:

- `src/security/decision_envelope_predicate.py`

It returns inside/outside with telemetry (`scarcity_score`, `harmonic_cost`, violations),
and does not assign side effects or policy outcomes.

