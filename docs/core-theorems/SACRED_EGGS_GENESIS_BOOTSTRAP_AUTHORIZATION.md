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

## 9) Crosslinks

- Canonical entrypoint: `SPEC.md`
- Concept definitions: `CONCEPTS.md`
- Experimental reference implementation: `experimental/scbe_21d_max_fixed.py` (non-authoritative)
