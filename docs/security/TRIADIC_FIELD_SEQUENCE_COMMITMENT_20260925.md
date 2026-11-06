# Triadic Field Sequence Commitment

Date: 2026-09-25
Status: design proposal; not a new cryptographic primitive

## Purpose

This design turns the SCBE triadic braid and the proposed "field-hash sequence
injection" into a deterministic transcript commitment around standardized
cryptography. It can bind an agent's evidence, intent and resulting state into
one tamper-evident sequence without claiming that custom geometry replaces a
reviewed hash, KEM, signature or authenticated cipher.

The recommended engineering name is **Triadic Field Sequence Commitment
(TFSC)**. "Injective hash" should not be used as a security claim: a fixed-size
hash maps a larger input space into a smaller output space, so collisions must
exist. The useful property is instead:

1. an injective or unambiguous encoding over the allowed field domain;
2. a domain-separated, collision-resistant commitment to that encoding; and
3. a signature over the commitment and its sequence position.

## Three braid lanes

| Lane | Bound material | Existing SCBE sources | Security purpose |
|---|---|---|---|
| Evidence | Payload digest, tool arguments, tokenizer/tongue representation, source and artifact digests | STISTA, Six Tongues, Loom/Rubix, GeoSeal claims | Commits to what was observed or requested |
| Authority | Subject, audience, route, action, policy version, permissions, nonce and expiry | Signed-intent envelope, GeoSeal, HYDRA governance | Commits to who authorized exactly which operation |
| State | Previous root, sequence, braid state, bounded PHDM metrics, execution result and postcondition | T-braid, Hamiltonian braid, 14-layer gate, Mars relay | Commits to ordering, policy interpretation and what actually happened |

The braid is a structural relationship among these lanes. It does not become a
secret key and it does not increase the security strength of the underlying
hash or signature.

## Canonical field encoding

Each field must have exactly one byte representation:

```text
field = version || name_length || name || type || value_length || value
```

Rules:

- Lengths are unsigned big-endian integers of a fixed documented width.
- Text is UTF-8 in one required normalization form.
- Integers use one documented signed representation.
- Boolean, null and absent are distinct values.
- Maps reject duplicate keys and use deterministic key ordering.
- Floating-point governance values are converted to bounded fixed-point
  integers with an explicit scale. NaN, infinities and negative zero are
  rejected.
- Unknown critical fields are rejected. Unknown non-critical fields remain in
  the commitment even when an older verifier cannot interpret them.
- The schema and algorithm suite are committed fields, not ambient settings.

Deterministically encoded CBOR can provide the outer object format. NIST
TupleHash can hash each ordered tuple without ambiguity. These are established
building blocks rather than a new serialization or hash construction.

## Commitment construction

For event `i`, construct the three lane roots:

```text
E_i = TupleHash256(
        ["SCBE-TFSC-v1/evidence", schema_id, evidence_field_1, ...], 256)

A_i = TupleHash256(
        ["SCBE-TFSC-v1/authority", schema_id, authority_field_1, ...], 256)

S_i = TupleHash256(
        ["SCBE-TFSC-v1/state", schema_id, state_field_1, ...], 256)
```

Then braid the lanes into an append-only sequence root:

```text
B_i = TupleHash256([
        "SCBE-TFSC-v1/root",
        algorithm_suite,
        encode_u64(i),
        B_(i-1),
        E_i,
        A_i,
        S_i,
        braid_descriptor
      ], 256)
```

`B_0` uses a domain-separated genesis value containing the deployment ID and
initial policy root. The `braid_descriptor` records the lane arrangement or
crossing word if the application needs it. It is public, canonical and signed;
its secrecy is not a security assumption.

For internal symmetric authentication:

```text
tag_i = KMAC256(audit_key, B_i || deployment_id || epoch,
                "SCBE-TFSC-v1/audit", 256)
```

For transferable verification:

```text
signature_i = ML-DSA-65.Sign(agent_signing_key, B_i)
```

For confidentiality, establish the session with ML-KEM, derive protocol keys
with an approved KDF or KMAC construction, and use authenticated encryption.
Bind `B_i`, the algorithm suite and both endpoint identities as associated data.

## Safe meaning of field-sequence injection

"Injection" means adding a typed field at a defined schema position before the
lane commitment is calculated. It must never mean altering the internal state,
constants, matrices, nonce derivation or arithmetic of SHA-3, ML-KEM, ML-DSA or
the authenticated cipher.

Allowed examples:

- inject the six-tongue canonical digest into the evidence lane;
- inject the Hamiltonian braid state into the state lane;
- inject a PHDM distance as a bounded fixed-point policy observation;
- inject a GeoSeal target and postcondition into authority/state lanes;
- inject an offline Mars-relay checkpoint and parent root into the state lane.

Disallowed examples:

- derive a secret key directly from attacker-controlled PHDM scores;
- alter ML-KEM or ML-DSA coefficients using a braid value;
- use braid-word recovery hardness as the vault's cryptographic assumption;
- treat reversible double hashing as collision-resistant cryptographic hashing;
- truncate an authority root to 64 bits.

## Mapping to existing implementation

| Existing component | Reuse | Required change |
|---|---|---|
| `packages/kernel/src/tBraid.ts` | Temporal and governance observations for the state lane | Encode outputs as bounded fixed-point fields; do not use `H_braid` as key material or security bits |
| `src/ai_brain/hamiltonian-braid.ts` | Nine-state policy descriptor | Require signed authority before any `INSTANT_APPROVE`; include state plus policy version in the commitment |
| `python/scbe/elastic_bijective_hash.py` | Reversible indexing and lookup | Keep it outside the cryptographic trust root; verify retrieved objects against `B_i` |
| `spiral-word-app/braid_ledger.py` | Existing HMAC-backed receipt and PHDM path adapter | Commit full typed fields, previous root and sequence; add signed periodic checkpoints |
| `src/crypto/tri_bundle.py` | Canonical tri-braid representation source with order-dependent SHA3-256 identities | Retain its explicit order and version tag, but convert security-relevant floating-point fields to bounded fixed-point values and wrap every value with explicit type/length encoding |
| `src/crypto/braid_vault.py` | Research reference only | Do not use as a production vault: its comments and implementation disagree, both advertised hash lanes currently use PBKDF2-HMAC-SHA256, and braid conjugacy is not an approved key-hardness assumption |

## What this adds

- **Field substitution resistance:** names, types, values and positions are
  committed unambiguously.
- **Order and omission detection:** sequence and previous root expose deletion,
  insertion, reordering and rollback.
- **Cross-view binding:** the raw payload, tongue representation, policy and
  result can be proven to belong to the same event.
- **Protocol separation:** the same bytes cannot silently become a key request,
  policy update or tool command under another route.
- **Offline reconciliation:** independently stored Mars-relay branches can be
  compared at signed roots and resolved under explicit fork policy.
- **Selective proof:** a Merkle tree can replace a lane's flat field list when
  individual field inclusion proofs are needed.

It does not stop a compromised endpoint from signing a malicious request, hide
metadata, secure private keys, or make an unsafe policy correct. Those remain
separate identity, key-management, containment and governance problems.

## Verification plan

1. Publish fixed Python and TypeScript test vectors for every field type.
2. Require identical lane and braid roots across both implementations.
3. Mutate every field, type, length, lane, sequence and previous root; every
   mutation must either be rejected or change `B_i`.
4. Test omission, duplication, reordering, rollback, fork and replay attacks.
5. Test Unicode normalization and integer/fixed-point boundaries.
6. Verify ML-DSA tamper rejection and KMAC wrong-key rejection.
7. Benchmark flat TupleHash lanes against Merkle lanes at realistic fleet sizes.
8. Keep a reference parser small enough for independent review and fuzzing.

## Standards anchors

- [NIST SP 800-185](https://csrc.nist.gov/pubs/sp/800/185/final) defines cSHAKE,
  KMAC, TupleHash and ParallelHash. TupleHash is specifically designed to hash
  tuples of strings unambiguously.
- [FIPS 202](https://csrc.nist.gov/pubs/fips/202/final) defines SHA-3 and SHAKE.
- [NIST SP 800-108 Rev. 1](https://csrc.nist.gov/pubs/sp/800/108/r1/upd1/final)
  defines KDF constructions using HMAC, CMAC and KMAC.
- [RFC 8949](https://www.rfc-editor.org/rfc/rfc8949.html) specifies CBOR and
  deterministic-encoding requirements.
