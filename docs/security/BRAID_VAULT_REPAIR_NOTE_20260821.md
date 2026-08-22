# Braid Vault repair note

**Status:** security repair plan; implementation deliberately unchanged

**Date:** 2026-08-21

**Source audited:** `src/crypto/braid_vault.py`

**Source SHA-256:** `1b6cd9962913e14bee2ebac6b853a121cffb1e5404913235cd0d25ea5b5592b6`

**Test SHA-256:** `4685990f1428ce2190ccc7144a9a44c123b1f53957747253199bcfffa3ce9d17`

**Repository HEAD during audit:** `7da3d3d5093d7bb792eda05597648e9b2cfab344`

This note turns the 2026-08-21 audit into a bounded repair task. It does not
authorize use of the current module for production secrets and does not claim
that a custom construction becomes secure by increasing its braid length.

## Outcome

The module contains a useful, deterministic, order-sensitive mixer and a clear
three-strand domain model. It is **not currently an authenticated vault**, an
implementation of braid-group cryptography, or a dual-primitive construction in
the sense claimed by its documentation.

The standard cryptographic boundary should be a versioned AEAD envelope. The
braid/tongue machinery may remain as domain separation, routing metadata, audit
fingerprints, or an additional non-secret context input. It must not be the
confidentiality or authenticity claim.

## Findings, in repair order

### BV-01 — critical — stored ciphertext is malleable and unauthenticated

`store()` XORs a length-prefixed payload with an expanded key. `retrieve()`
repeats the XOR, trusts the recovered four-byte length, and returns the slice.
There is no authentication tag, nonce, or associated-data check.

A focused local probe flipped one ciphertext bit. Retrieval did not reject the
entry and returned changed plaintext of the original length:

```text
tamper_rejected False
returned_changed_plaintext True length 6
```

**Repair:** replace the XOR envelope with one standard AEAD implementation:

- AES-GCM as specified by NIST SP 800-38D; or
- ChaCha20-Poly1305 as specified by RFC 8439.

Use a fresh nonce according to the chosen construction's requirements and bind
canonical, versioned associated data including at least the entry identifier,
envelope version, algorithm identifier, tongue affinity, and expiry policy.
Authentication failure must return a generic failure and must never release
plaintext.

### BV-02 — high — the documented primitives do not match the code

The module and tests call the channels SHA3-256 and BLAKE2b-256. `_h_a()` and
`_h_b()` both call `pbkdf2_hmac("sha256", ...)`; only the fixed salt and
iteration count differ. Different output is not evidence of independent
primitive families.

**Repair:** remove the SHA3/BLAKE2 and “compromise of either is insufficient”
claims. Prefer a single standard KDF and a single standard AEAD boundary. If two
hashes are retained for non-security fingerprints, implement the named hashes,
domain-separate them, and describe them only as redundant audit channels unless
a real composition argument is supplied.

### BV-03 — high — the transform is not a representation of `B_3`

The comments correctly state the abstract braid relation
`sigma_1 sigma_2 sigma_1 = sigma_2 sigma_1 sigma_2`, but the implemented
hash/XOR/rotate transform does not satisfy it. A deterministic probe over the
same initial strands produced:

```text
braid_relation_holds False
declared_inverse_restores False
```

The named inverse crossings cannot invert prior one-way hash operations. The
tests currently establish order sensitivity (`s1;s2 != s2;s1`), which is real,
but do not establish a group action, the braid relation, invertibility, or a
reduction to a conjugacy problem.

**Repair:** remove “inverse”, “topological security”, and “conjugacy hardness”
security claims from the executable module. Rename the operations as directional
mix steps. If an actual braid-group representation is later implemented, first
add executable identity, composition, braid-relation, and inverse laws; then
obtain specialist review before assigning any security property to it.

### BV-04 — high when the braid word is treated as a secret — default path entropy is 24 bits

`BraidWord.generate(length=12)` chooses one of four values per step. Because
four divides 256, byte reduction is uniform, but the nominal path space is only
`4^12 = 2^24`. The passphrase also influences the current vault key, so this is
not a claim that every deployment has only 24 total bits. It is a direct
contradiction of the documentation's statement that the braid word itself is
the key.

Sixty-four independent four-way choices would provide 128 nominal raw bits, but
that arithmetic is not a security proof and transform collisions can only lower
the effective space.

**Repair:** generate a 256-bit random vault key from the operating-system CSPRNG
and protect it with the project's existing secret-store/root-of-trust path. Use
the braid word as public context or routing metadata. Do not count it as an
independent security factor.

### BV-05 — high — password derivation has no per-vault random salt or envelope parameters

`create_vault()` feeds the passphrase into `_h_a()` with the module-wide fixed
salt `braid-vault-h-a`. Equal passphrases therefore derive equal master seeds
before the random braid is applied, and no versioned KDF parameters are stored
with the vault.

**Repair:** use a standard password-based derivation with a fresh random
per-vault salt and persist the KDF name, salt, and cost parameters in the
versioned header. NIST SP 800-132 is the baseline reference for PBKDF2 storage
applications. If the platform root of trust supplies a high-entropy master key,
prefer that over a human passphrase.

## Versioned replacement envelope

The next format should be explicit and migration-friendly:

```text
VaultEnvelopeV2
  version          = 2
  algorithm        = AES-256-GCM | ChaCha20-Poly1305
  kdf              = versioned KDF identifier and parameters
  salt             = random per-vault salt when password-derived
  nonce            = fresh per-entry nonce
  ciphertext_tag   = AEAD output
  associated_data  = canonical(entry_id, version, affinity, expiry policy)
```

The master key, raw passphrase, and plaintext never enter logs or metadata. AAD
must use a canonical byte encoding rather than locale-sensitive strings or raw
floating-point serialization.

## Migration plan

1. Add `VaultEntryV2` beside the current entry type; do not mutate existing
   records in place.
2. Implement AEAD seal/open through an established cryptography library. No
   custom stream cipher, tag truncation, or silent fallback.
3. Add dual-read/single-write behavior: read legacy entries only for migration,
   immediately write V2 after a successful authenticated re-seal, and create all
   new entries as V2.
4. Back up and inventory legacy entries before migration. Re-seal to temporary
   storage, verify every plaintext digest in memory, then atomically switch the
   registry. Keep rollback material until the migration receipt is complete.
5. Make rotation transactional across the full entry set. One authentication
   failure aborts the rotation without a partial swap.
6. After the migration window, disable legacy reads and retain only a count and
   digest receipt—never secret material—in the audit log.

## Required tests before security use

- deterministic round-trip vector for the selected AEAD;
- ciphertext, nonce, tag, AAD, entry-ID, and length tampering each fail closed;
- nonce uniqueness over a large generated sample and explicit duplicate-nonce
  rejection where the library permits it;
- wrong key, wrong passphrase, expired entry, truncated entry, oversized length,
  empty value, binary value, and maximum supported value;
- KDF parameter/version round-trip and migration from a frozen legacy fixture;
- interrupted migration and interrupted rotation leave the old vault readable;
- logs contain identifiers/digests only and never plaintext, keys, passphrases,
  nonces plus keys, or decrypted payload fragments;
- tests and comments name the primitives actually executed;
- if braid terminology remains, algebraic tests distinguish order sensitivity
  from group identities and no conjugacy-hardness claim appears without a
  reviewed reduction.

## Acceptance boundary

Until BV-01 through BV-05 are resolved and the invalid-input tests pass, call
this component an **experimental braided mixer with reversible storage API**, not
a secure, post-quantum, topological, or dual-primitive vault.

The multi-hash and tongue structure can still help as complementary annotation
and routing. It is not discarded; it is moved outside the security boundary so
standard cryptography protects it and the documentation says exactly what the
code does.

## Primary references

- NIST, [SP 800-38D: Galois/Counter Mode (GCM) and
  GMAC](https://csrc.nist.gov/pubs/sp/800/38/d/final) — authenticated encryption
  with associated data.
- IETF, [RFC 8439: ChaCha20 and Poly1305 for IETF
  Protocols](https://www.rfc-editor.org/rfc/rfc8439.html) — includes the
  ChaCha20-Poly1305 AEAD construction and complete-tag requirement.
- NIST, [SP 800-132: Password-Based Key Derivation for Storage
  Applications](https://csrc.nist.gov/pubs/sp/800/132/final) — password-derived
  master keys, salts, and iteration parameters.
