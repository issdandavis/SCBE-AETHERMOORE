# Governance PQC Proof Ladder

This note defines the runtime proof ladder used by SCBE governance-facing systems when post-quantum cryptography is available, partially available, or unavailable.

## Purpose

Governance code should not treat "PQC enabled" as a binary claim. The runtime has three distinct proof tiers with different security and audit meanings. The active tier must be reported explicitly anywhere an overseer or governance gate reasons about cryptographic trust.

## Proof Tiers

### Tier 1: Native Quantum-Resistant

- Backend: `liboqs`
- Algorithms: `ML-KEM-768` and `ML-DSA-65` via native bindings
- Quantum resistant: `true`
- Claim level: production-grade post-quantum cryptography

Use this tier when the native `oqs` module imports successfully and the shared library is available.

### Tier 2: Pure-Python Quantum-Resistant

- Backend: `kyber-py` / `dilithium-py`
- Algorithms: `ML-KEM-768` and `ML-DSA-65` in pure Python
- Quantum resistant: `true`
- Claim level: real post-quantum algorithms without native library dependency

Use this tier when native `liboqs` is unavailable but the pure-Python ML-KEM / ML-DSA packages are present.

### Tier 3: Deterministic Classical Fallback

- Backend: SHA-256 / HMAC simulation
- Algorithms: API-compatible simulation only
- Quantum resistant: `false`
- Claim level: deterministic development and air-gapped fallback only

Use this tier only when neither native nor pure-Python PQC is available.

## Governance Rules

1. Tier 1 and Tier 2 may be treated as quantum-resistant.
2. Tier 3 must never be described as quantum-resistant.
3. Governance telemetry should report:
   - active tier
   - backend string
   - quantum-resistant boolean
   - selected KEM and signature algorithm names
4. Any overseer or governance gate that requires real PQC should reject Tier 3.

## Runtime Source of Truth

The canonical runtime reporting surface is in:

- [src/crypto/pqc_liboqs.py](C:/Users/issda/SCBE-AETHERMOORE/src/crypto/pqc_liboqs.py:1)

Use:

- `get_pqc_proof_tier()`
- `get_pqc_backend()`
- `get_pqc_governance_status()`

These functions are the source of truth for governance-facing PQC state.
