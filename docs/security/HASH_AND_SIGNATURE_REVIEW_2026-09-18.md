# Hashing, signing and braid composition review

This is a source review with executable regressions, not a cryptographic proof,
penetration-test certificate, FIPS module validation or NIST certification.

## Plain-language map

A hash is a fixed-size fingerprint of input bytes. Matching a trusted fingerprint
helps detect changes. A hash alone cannot identify the sender: anyone can hash
replacement data. HMAC authenticates using a shared secret; a digital signature
uses a private signing key and a public verification key. Encryption hides data;
authenticated encryption also detects tampering. Reversible tokenization is an
encoding, not a cryptographic hash.

The custom work here mostly composes established primitives or organizes data
around them. That can be useful without claiming a new secure hash primitive.

| Component | Actual implementation | Role and limit |
| --- | --- | --- |
| `src/crypto/braid_vault.py` | Two domain-separated PBKDF2-HMAC-SHA256 channels, three strands, ordered mixing, final XOR | Experimental key derivation. Neither SHA3+BLAKE2 nor three independent secrets. The word's inverse labels do not invert the rehashed state; no braid-group hardness reduction is established. |
| `src/crypto/tri_bundle.py` | SHA3-256 of ordered packed numeric data, then SHA3-256 of the three bundle hashes and cluster context | Structured identity fingerprints. Each cluster has 27 numeric components and six views have 162. The phi scaling factor is about 207; it is not an entropy or dimension count. |
| `src/crypto/sacred_eggs.py` | SHA-256 shells, HMAC/HKDF-SHA256 and a sorted three-shell binding | Commitments, derivation and contextual binding. Three shells do not imply triple security. Showing a secret to a verifier is not a zero-knowledge proof. |
| `packages/kernel/src/tBraid.ts` | Derived temporal variants, weighted hyperbolic distances and an exponential score | A routing/geometry measure, not a cryptographic hash or signature. |
| `python/scbe/elastic_bijective_hash.py` | Reversible SplitMix64-based mapping with a double-hashed lookup table | Indexing and memory lookup. Not a collision-resistant security primitive. |
| `src/spiralverse/rwp2_envelope.py` | Per-tongue, domain-separated HMAC-SHA256 with explicit keys and a canonical envelope | Shared-secret authentication, not public-key signatures. Freshness state is process-local. |
| Both `spiral_seal/signatures.py` copies | Native liboqs ML-DSA-65 when available, or legacy Dilithium3; explicitly enabled Ed25519 for development | Actual signing. Ed25519 development mode is classical, not PQ-secure. A standard algorithm alone does not establish FIPS module validation. |

## Confirmed signing and vault defects repaired

1. **Format-only authentication:** the legacy fallback accepted any
   `FALLBACK_SIG:` prefix followed by 32 bytes, without checking the message or
   key. Default key generation/signing now refuses when the native backend is
   unavailable. Isolated development mode requires both `SCBE_ALLOW_MOCK_PQC=1`
   and `SCBE_ENV=test` or `development`, and uses real Ed25519 verification.
   Removing opt-in immediately disables verification of development signatures.
2. **Ignored backend verdict:** the legacy pqcrypto adapter ignored a boolean
   false verdict and returned true unless an exception was raised. It now
   requires an explicit true result for its legacy CFFI API contract. Unknown
   return conventions fail closed and require a separately tested adapter.
3. **Ignored signature request:** the old `seal.py` SS1 wire format omitted KEM
   and signature fields; `verify_sig=True` did not verify anything. These
   unsupported envelope requests now reject. Unsigned symmetric round trips and
   AAD checks remain supported. This class is distinct from the package export
   in `spiral_seal.py`; the entire latter protocol is not certified by this review.
4. **Unauthenticated vault entries:** custom XOR encryption could return altered
   plaintext. Version 2 uses AES-256-GCM with a fresh 96-bit nonce, a per-entry
   derived key and authenticated entry identity, salt, timestamps, tongue and
   JSON metadata. Rotation validates all records and stages all new ciphertext
   before replacing vault state. TTL zero expires rather than becoming immortal.

### Compatibility

Legacy unauthenticated vault entries and format-only signatures are deliberately
rejected. There is no silent downgrade or automatic migration. This in-memory
vault has no documented persistence/export interface; any external retained
legacy ciphertext needs a separate, explicitly reviewed recovery procedure from
a trusted copy. Do not discard old storage on the basis of this change.

Metadata must be JSON-compatible and finite. Rotation preserves original
creation and expiry timestamps. Replay of a whole valid old entry, concurrent
transactions, secure memory erasure and durable storage are outside this vault's
guarantees. The custom master derivation remains experimental; authenticated
encryption does not prove that derivation secure or repair low-entropy secrets.

## Remaining blockers and limits

- Custom derivation and braid constructions still need independent
  cryptanalysis. Passing functional/tamper tests cannot establish hardness.
- RWP2 replay state is per process and does not survive restarts. Deployments
  with multiple workers need a shared atomic freshness store. Key provisioning,
  rotation, custody and policy selection remain operator responsibilities.
  Possessing multiple tongue keys does not establish multiple independent actors.
- Aethercode's authenticated receipt only authenticates the supplied trace.
  It does not prove execution or truth. Its `PROOF` command still builds a
  descriptive trace summary, not a formal or cryptographic computation proof.
- `create_session_egg` derives its yolk from the session ID. If that ID is public,
  the yolk is public too. It is suitable as a deterministic identifier, not an
  independently secret authentication credential.
- Tri-bundle hashes fingerprint packed binary floating-point values. They do
  not establish semantic equality across alternate float representations;
  field shape, finite-value and canonicalization rules need a separate contract
  before using arbitrary external bundles as security commitments.
- Rehashing, additional tongues, nested decimal coordinates and longer encodings
  do not create fresh secret entropy. Geometry may route a decision but cannot
  authorize a missing or invalid signature.

## Connected RWP2 and Aethercode repair

Follow-up inspection reproduced eight concrete bad outcomes on the pre-repair
commit: authentication with public demo keys; accepted changes to key ID, tier
and version; accepted delimiter redistribution; accepted empty required signer
sets; replay after eviction of a live cache record; and `LEDGER VERIFY nonsense`
returning true. The corrected contract is:

- `SignatureEngine(keys=...)` and `EnvelopeFactory(keys=...)` require explicitly
  supplied, nonempty keys. Source-visible historical demo keys are rejected.
  Keys are copied so later caller dictionary changes cannot switch the verifier.
- MAC revision 2 encodes typed fields as canonical JSON, binary payload as
  Base64URL, and authenticates every field including `kid`, `tier` and `version`.
  Each tongue has its own domain label. Old delimiter-based tags are rejected.
- Every tier's minimum signers must verify. An explicit required set may add
  requirements, but cannot remove the tier minimum or be empty. Missing signing
  keys raise instead of silently creating a partial result.
- The factory verifies the MAC before consuming a nonce. A lock makes check and
  record atomic within one process. A full replay cache rejects new work instead
  of evicting unexpired receipts and allowing replays.
- Aethercode accepts `signing_keys=...` for authenticated operations. Without
  keys ordinary interpretation works, but signing/receipt export rejects and
  verification returns false. `LEDGER SIGN` uses HMAC-SHA256 with a ledger domain.
  `LEDGER VERIFY {"message":"hello","mac":"<64 hex characters>"}` checks that
  exact message. Demonstrations explicitly create ephemeral random keys.

These are deliberate compatibility breaks for insecure defaults and tags.
Provision keys from a secret store, update all communicating peers, and issue
fresh envelopes; do not add an acceptance fallback for the old format. The
`TONGUE_KEYS` symbol remains importable only as historical public demo data and
must not be used as a secret. No existing secret store is modified by this patch.

`tests/security/test_rwp2_authentication_contract.py` covers both failures and
ordinary operation, all four tiers, Unicode, binary payloads, wrong keys,
tampered headers, malformed tags and concurrent replay. Together with the
canonical-registry and full-system checks, the focused follow-up had 39 passing
tests. The full-system test's broad title is not a certification claim.

## Reproduction and validation

`tests/security/test_braid_signature_integrity.py` exercises both shipped Python
copies, default/production rejection, explicit development signing, wrong keys,
modified messages, truncated signatures, legacy serializer refusal, vault
header/ciphertext mutation, failed rotation and lifetime preservation. The
initial 16 tests failed on the old implementation. Expanded caller checks also
reproduced ignored verification and ignored backend verdicts before repair.

`tests/test_braid_vault.py` supplies ordinary vault operation controls. Existing
signing suites now opt in to development mode explicitly and require wrong
message/key rejection instead of merely checking that a boolean was returned.

Run locally without triggering native library bootstrap:

```powershell
$env:SCBE_FORCE_SKIP_LIBOQS = '1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest -p pytest_asyncio.plugin -o addopts='' tests/security/test_braid_signature_integrity.py tests/test_braid_vault.py -q
```

The native liboqs CI smoke separately exercises both real ML-DSA-65 legacy
signing adapters, requiring a valid round trip and rejection of wrong keys,
changed messages, truncation and the old fake prefix. Contract-test doubles are
not evidence of native cryptographic operation. Current results belong in PR
checks and test receipts, rather than being inferred from this document.

## Primary references

- [NIST FIPS 202: SHA-3](https://csrc.nist.gov/pubs/fips/202/final).
- [NIST FIPS 204: ML-DSA](https://csrc.nist.gov/pubs/fips/204/final).
- [Cryptography AEAD API and nonce/authentication requirements](https://cryptography.io/en/latest/hazmat/primitives/aead/).
- [Legacy pqcrypto CFFI API](https://github.com/kpdemetriou/pqcrypto), whose
  documented verification result is boolean; different generations of this
  package require explicit compatibility testing.

See also [NIST readiness](NIST_READINESS.md) for the broader, partial
SSDF self-assessment and outstanding assurance work. The follow-up
[dual-trit polarity research](DUAL_TRIT_POLARITY_COMMITMENT_RESEARCH_20260919.md)
formalizes the centered multi-sign field while keeping SHAKE256 as its
cryptographic boundary. The [ML-KEM and ML-DSA hardening review](ML_KEM_ML_DSA_HARDENING_RESEARCH_20260919.md)
maps that field onto standards-compatible transcript receipts and fault checks.
The [whole-system agent review](WHOLE_SYSTEM_AGENT_SECURITY_20260919.md) maps
the same rule through the tool-execution boundary.
