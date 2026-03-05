# SCBE-AETHERMOORE — Offline Functionality Specification (OFS)

Version: `1.0.0`  
Date: `2026-02-18`  
Status: `Normative`  
Patent: `US Provisional #63/961,403`

## 0. Normative Language

`MUST` / `MUST NOT` / `SHOULD` / `MAY` follow RFC 2119 semantics.

Offline means node operation with no network dependency for correctness or safety enforcement.

## 1. Offline Modes

- `O0` Online: network available, full feature set.
- `O1` Disconnected: network unavailable, safe operation with reduced features.
- `O2` Air-gapped: network prohibited, safe + auditable operation.
- `O3` Intermittent: unreliable network, local-first + eventual sync.

## 2. Core Offline Invariants

1. Enforcement MUST be deterministic from local inputs and local state.
2. Enforcement MUST NOT require remote services.
3. Remote data MAY be advisory; never enforcement-critical.
4. Core MUST function identically if periphery is unavailable.
5. Time logic MUST tolerate clock issues and use monotonic time.
6. Crypto verification/signing for enforcement MUST work offline.
7. Revocation/OCSP checks MUST be optional, non-blocking.

## 3. Required Offline Core Components

1. Immutable Laws module (hash-locked)
2. Flux Manifest module (signed, versioned)
3. Governance Engine (pure decision function)
4. MMX (deterministic multimodal scalars)
5. Sacred Tongues tokenizer (deterministic)
6. Voxel store (content-addressed, idempotent, sharded)
7. PQ crypto suite (ML-KEM-768, ML-DSA-65)
8. Audit ledger (append-only, hash-chained, signed)

## 4. Decision Capsule Requirement

Every decision MUST emit a signed capsule containing:

- `inputs_hash`
- `laws_hash`
- `manifest_hash`
- `state_root`
- `decision`
- `reason_codes`
- `timestamp_monotonic`
- `signature` (ML-DSA-65)

## 5. Trust States

- `T0` Trusted
- `T1` Time-Untrusted
- `T2` Manifest-Stale
- `T3` Key-Rollover Required
- `T4` Integrity-Degraded

Fail-closed conditions MUST force `DENY` or `QUARANTINE` for high-trust actions.

## 6. O3 Sync Rules

On reconnect, node MAY upload:

- decision capsules
- audit deltas
- voxel deltas
- manifest pull requests

Sync MUST be resumable + idempotent.

Manifest conflict resolution priority:
1. valid signature
2. higher `epoch_id`
3. higher quorum weight (if configured)

## 7. File Layout (Implemented)

- `docs/OFFLINE_MODE_SPEC.md`
- `src/governance/offline_mode.ts`
- `src/governance/index.ts`
- `src/governance/immutable_laws.ts`
- `src/governance/flux_manifest.ts`
- `src/governance/governance_engine.ts`
- `src/governance/mmx.ts`
- `src/governance/audit_ledger.ts`
- `src/governance/voxel_store.ts`
- `src/governance/pq_crypto.ts`
- `src/governance/sync_client.ts`

## 8. Notes

This document is the normative reference for offline-mode behavior.  
Implementation details are defined in `src/governance/offline_mode.ts`.
