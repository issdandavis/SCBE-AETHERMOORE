# Core Theorems — Sacred Eggs: Genesis / Bootstrap Authorization

> **Status:** Canonical theorem surface (authoritative when linked by `SPEC.md`).

## 0) Purpose and Threat Model

Genesis is a **type change** (`nonexistent → existent`), not a routine action. Therefore creation authorization requires explicit theorem-level controls, distinct from runtime action gating.

**Threats addressed**

- unauthorized spawning (Sybil births)
- key exfiltration during bootstrap
- failure-oracle leaks via distinct error signals
- cheap replayed hatch requests

**Security goal**

Creation requires consensus + context + linguistic gating, and failure reveals no discriminating cause (`NOISE` response class).

---

## 1) Formal Objects

- `Egg E`: sealed ritual container containing payload, policy, geometry anchor, and thresholds.
- `HatchRequest HR`: attempted hatch with context (`geo_ctx`, tongue weights, nonce, timestamp, witnesses).
- `HatchProof HP`: evidence bundle (votes/signatures/diversity checks/GeoSeal validation).
- `Outcome O`: either `HATCHED(entity)` or `NOISE(bytes)`.

Domain model:

- Runtime Control Kernel authorizes evolution of existing entities (`Field -> Token`).
- Genesis Control Surface authorizes birth of new entities/realms/pads (`Field -> CreationPermit`).

This closes kernel authority over both **evolution** and **birth**.

---

## 2) Hatch Condition Mathematics (φ-weight hierarchy)

Let `w_t >= 0` be per-tongue weights and `alpha_t >= 0` be policy coefficients.

- `Score(HR) = sum_t alpha_t * w_t`
- `TriadOK(HR) = [sum_{t in T3} w_t >= tau_tri] AND [forall t in T3: w_t >= tau_min]`

Tier ordering for creation classes:

`tau_agent < tau_pad < tau_realm < tau_rootkey`

Canonical hatch predicate:

`HatchOK(HR) = Score(HR) >= tau_total AND TriadOK(HR) AND GeoOK(HR) AND QuorumOK(HR) AND DiversityOK(HR) AND FreshNonce(HR)`

### Theorem T1 — Monotonicity

Holding context and all other variables constant, increasing any `w_t` cannot reduce hatch acceptability under `HatchOK`.

---

## 3) Geometric Validation (GeoSeal binding)

GeoSeal is binding, not decorative.

- containment invariant: `inside_poincare_ball(geo_ctx)`
- anchor constraint: `d_H(geo_ctx, egg_anchor) <= epsilon`

### Theorem T2 — Out-of-geometry indistinguishability

If geometric constraints fail, the externally observable outcome must be indistinguishable (shape-class) from other denied hatches (`NOISE` class).

---

## 4) Triadic Ritual Protocol (multi-tongue consensus)

Votes are signed statements over a canonical action hash.

`SignedVote(agent_id, decision, action_hash, nonce, timestamp, signature)`

Decision classes:

- `APPROVE`, `DENY`, `ABSTAIN`

Consensus requirements:

- quorum threshold by creation tier
- lineage diversity minimum
- tongue diversity minimum

Output on success:

- `CreationPermit` scoped to requested creation operation

---

## 5) Fail-to-noise Rules (oracle resistance)

All creation denials MUST obey:

1. single response class: `NOISE(fixed_len)`
2. no distinct failure codes over untrusted channel
3. bounded/constant-time behavior where practical
4. domain-separated noise derivation:

`noise = HKDF(K_fail, "egg_fail" || egg_id || nonce || context_digest)`

### Theorem T3 — Failure-channel non-disclosure

For external callers, failed hatch classes are non-separable beyond fixed public envelope metadata.

---

## 6) Layer Integration and Control Closure

- Layer 12/14 produce root/key/governance decisions and permit issuance authority.
- Sacred Eggs consume field conditions and emit `CreationPermit` or `NOISE`.
- On success, newborn entities inherit: seed/key material handle, policy profile, and initial tongue alignment vector.

---

## 7) Reference Interfaces (implementation hooks)

```python
create_egg(payload, policy, anchor_geo, thresholds) -> egg
propose_hatch(egg_id, geo_ctx, tongue_weights, witnesses, nonce, ts) -> hatch_request
verify_hatch(hatch_request) -> HATCHED(entity) | NOISE(bytes)
audit_log(event) -> None  # safe metadata only
```

Implementation requirements:

- canonical serialization for action hash and vote transcript
- replay defense via nonce freshness and bounded skew checks
- safe metadata logging (no key/seed disclosure)

---

## 8) Test Vectors and Negative Cases

Required negative tests:

- wrong geometry (`GeoOK = false`)
- insufficient triad weights (`TriadOK = false`)
- quorum met but diversity unmet (`DiversityOK = false`)
- replayed nonce (`FreshNonce = false`)
- unacceptable clock skew
- near-threshold misses returning same `NOISE` class as all denials

Required positive tests:

- tier-specific successful hatch (`agent/pad/realm/rootkey`) with expected quorum/diversity requirements

---

## 9) Canonical Definition

> **Sacred Eggs are the genesis-layer complement to GeoSeal and SCBE runtime governance.**
> GeoSeal answers whether an entity may act.
> Sacred Eggs answer whether an entity may come into existence at all.

A Sacred Egg is a sealed genesis authorization object that permits creation of a new agent, realm, or governed entity only after a ritualized validation process confirms quorum, intent, and geometric admissibility.

Sacred Eggs implement ritual-based genesis governance. They replace unilateral entity creation with a sealed, auditable authorization ceremony requiring quorum-weighted validation and geometric admissibility before a new agent or realm may be instantiated.

**Short form:** Sacred Eggs are consensus-bound genesis capsules for governed spawning.

### What makes Sacred Eggs distinct

Sacred Eggs are not config blobs or bootstrap files. They are a **creation-time governance primitive**.

They govern:
- **Whether** something may be created
- **Under what conditions** it may be created
- **What initial constraints** bind it at birth

Stack positioning:

| Layer | Primitive | Question |
|-------|-----------|----------|
| Genesis | Sacred Eggs | May this entity come into existence? |
| Access | GeoSeal | May this entity act? |
| Runtime | SCBE/HYDRA | How is this entity governed? |

### Canonical Lifecycle (G0–G4)

```
Stage G0 — Proposal
  Candidate egg assembled with: entity type, purpose, initial config,
  realm target, proposer identity, epoch data.

Stage G1 — Sealing
  Payload sealed cryptographically: content hash, signer set,
  provenance metadata, optional GeoSeal/context binding.

Stage G2 — Ritual Validation
  Egg evaluated against ritual constraints:
    - φ-weight tongue quorum (W = Σ w_i ≥ φ³)
    - Multi-party approval (ValidatorVotes)
    - Geometric proximity / admissibility (Poincaré ball)
    - Trust or coherence thresholds
    - Optional phase / epoch rules

Stage G3 — Hatching Decision
  System outputs: HATCH | QUARANTINE | DENY

Stage G4 — Spawn
  If approved, new entity instantiated with:
    - Bound initialization parameters
    - Inherited governance limits
    - Audit record / ledger entry (GenesisProof)
    - Genesis seal (SHA-256 of all proof fields)
```

### Formal Hatch Predicate

```
HATCH(E) = (Σ w_i ≥ φ_min)
          ∧ (GeomPass(E))
          ∧ (IntegrityPass(E))
          ∧ (GovPass(E))
          ∧ (RequiredValidatorsSigned(E))
```

Where:
- `Σ w_i` = phi-weighted tongue quorum sum
- `φ_min` = minimum ritual threshold (default: φ³ ≈ 4.236)
- `GeomPass` = geometric proximity / anchor validation in Poincaré ball
- `IntegrityPass` = payload hash verification
- `GovPass` = coherence, risk, or harmonic admissibility check

---

## 10) Canonical Implementation

**Python reference:** `src/symphonic_cipher/scbe_aethermoore/sacred_egg_genesis_lifecycle.py`

Core types:
- `SacredEgg` — sealed genesis payload with G0–G4 lifecycle fields
- `ValidatorVote` — tongue-weighted validator vote with signature
- `GenesisProof` — cryptographic birth certificate
- `SpawnedEntity` — newly instantiated entity with provenance
- `Decision = Literal["HATCH", "QUARANTINE", "DENY"]`

Core functions:
- `propose_egg()` — G0: Assemble candidate egg
- `seal_egg()` / `verify_seal()` — G1: Cryptographic sealing
- `cast_vote()` — G2: Collect validator votes
- `evaluate_ritual()` — G2/G3: Full hatch predicate evaluation
- `spawn_entity()` — G4: Instantiate entity with governance binding
- `genesis_noise()` — Fail-to-noise output generation
- `full_genesis_lifecycle()` — Convenience: G0 through G4 in one call

**TypeScript canonical:** `src/harmonic/sacredEggsGenesis.ts`

**Tests:** `tests/test_sacred_egg_genesis_lifecycle.py` (40 tests covering all lifecycle stages)

---

## 11) Crosslinks

- Canonical entrypoint: `SPEC.md`
- Concept definitions: `CONCEPTS.md`
- Python genesis lifecycle: `src/symphonic_cipher/scbe_aethermoore/sacred_egg_genesis_lifecycle.py`
- TypeScript genesis gate: `src/harmonic/sacredEggsGenesis.ts`
- Crypto containers: `src/crypto/sacred_eggs.py`
- Predicate-gated AEAD: `src/symphonic_cipher/scbe_aethermoore/sacred_eggs.py`
- GeoSeal integrator: `src/symphonic_cipher/scbe_aethermoore/sacred_egg_integrator.py`
- Registry: `src/symphonic_cipher/scbe_aethermoore/sacred_egg_registry.py`
- Patent-hardened reference: `src/symphonic_cipher/scbe_aethermoore/sacred_eggs_ref.py`
