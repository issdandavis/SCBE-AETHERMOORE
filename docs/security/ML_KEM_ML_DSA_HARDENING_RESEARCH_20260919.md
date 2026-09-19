# ML-KEM and ML-DSA hardening research

**Review date:** 2026-09-19
**Status:** standards-backed design guidance; no modified cryptographic core
**Related experiment:** `src/crypto/dual_trit_polarity_commitment.py`

## Decision

Kyber and Dilithium became the bases of NIST's ML-KEM and ML-DSA standards.
The standardized versions are the production target; legacy Kyber and
Dilithium encodings are not assumed to be interchangeable with them.

SCBE can harden their use at four boundaries:

1. exact input, encoding, context, and algorithm checks;
2. constant-time, side-channel-aware and fault-aware implementations;
3. standardized protocol composition, key confirmation, and hybrid migration;
4. an independently computed dual-trit receipt over public transcript data.

The fourth item can improve observability, domain separation, corruption
localization, and independent fault detection. It does not increase the
lattice problem's hardness, add entropy, or replace SHAKE, ML-KEM, ML-DSA, an
approved key combiner, or authenticated encryption.

## Cryptography in one map

Cryptography combines narrowly defined tools:

| Tool | Secret held | Main job |
|---|---|---|
| Cryptographic hash | None | Fixed-size commitment to bytes |
| MAC | Shared key | Authenticate bytes between key holders |
| AEAD | Shared key | Encrypt and authenticate a message and its context |
| KEM | Recipient private key | Establish a shared secret over a public channel |
| Digital signature | Signer's private key | Publicly authenticate a message |

Algorithms may be public. Security depends on protected keys and randomness,
hard mathematical problems, exact protocol composition, and an implementation
that does not leak secrets through timing, memory, power, faults, or errors.

ML-KEM supplies key establishment; it does not authenticate identity. ML-DSA
supplies authentication; it does not encrypt. A protocol normally uses both
with a KDF and an AEAD, or relies on a reviewed protocol such as TLS to compose
those jobs.

## Simplified ML-KEM mechanics

ML-KEM works with vectors of polynomials in a finite ring. Suppressing the
compression and number-theoretic-transform details, key generation resembles:

```text
A = public pseudorandom matrix
s = small secret vector
e = small error vector
t = A*s + e mod q
public key  = (A seed, t)
private key = s plus data needed for checked decapsulation
```

Encapsulation samples another small vector and errors:

```text
u = A^T*r + e1 mod q
v = t^T*r + e2 + Encode(m) mod q
```

The recipient approximately cancels the shared linear term:

```text
v - s^T*u = Encode(m) + small combined error
```

Careful parameter bounds permit recovery of `m`, while recovering `s` from the
public noisy equations is believed hard. ML-KEM then applies a
Fujisaki-Okamoto-style transform: it derives the shared key and encryption
coins from `m` and the public key hash, re-encrypts after decapsulation, and
compares the reconstructed ciphertext. A mismatch selects a pseudorandom
fallback derived from the private rejection value and ciphertext. This
implicit rejection is part of the active-attack defense and must not become a
distinguishable error oracle.

## Simplified ML-DSA mechanics

ML-DSA uses a related module-lattice setting with two small secret vectors:

```text
t = A*s1 + s2 mod q
```

For a message representative `mu`, signing repeatedly does roughly this:

```text
y  = fresh masked commitment vector
w1 = HighBits(A*y)
c  = H(mu || w1)
z  = y + c*s1
```

The signer emits a challenge, `z`, and a reconstruction hint only if norm and
hint bounds pass. Otherwise it rejects that attempt and samples again. The
verifier reconstructs the commitment from `A*z - c*t` and checks the challenge.
The rejection process prevents the signature from exposing the small secret,
but it also creates an implementation surface that must be protected.

## Hardening that has evidence behind it

| Boundary | Required or preferred control | Reason |
|---|---|---|
| Version | Identify FIPS 203 ML-KEM and FIPS 204 ML-DSA exactly | Avoid legacy-format and algorithm confusion |
| Parameters | Negotiate an approved parameter set and bind its identifier into the transcript | Prevent downgrade and cross-parameter parsing |
| ML-KEM public input | Enforce exact length and canonical modulus encoding before encapsulation | FIPS 203 requires these checks |
| ML-KEM private input | Check ciphertext/key lengths and the embedded public-key hash | FIPS 203 decapsulation checks depend on them |
| ML-KEM rejection | Preserve the complete re-encryption comparison and indistinguishable fallback path | Prevent chosen-ciphertext and reaction oracles |
| ML-DSA verification | Reject every wrong public-key or signature length and noncanonical encoding | FIPS 204 ties these checks to strong unforgeability |
| ML-DSA signing | Prefer hedged signing with fresh `rnd`; protect every rejected attempt | Fresh randomness helps against faults and leakage but is not sufficient alone |
| Context | Use a nonempty, stable ML-DSA context and distinct keys for distinct signing profiles where practical | Bind purpose and stop cross-protocol reuse |
| Timing | Remove secret-dependent branches, division, memory access, and early exits | KyberSlash recovered keys from secret-dependent division timing |
| Physical leakage | Apply reviewed masking/hiding for the actual target and test power/EM behavior | Masking can itself introduce exploitable gadgets |
| Faults | Protect the FO comparison; self-verify signatures; use redundant checks on separate paths where the threat warrants it | Faults can bypass or expose decisive internal checks |
| Memory | Zeroize secret seeds, small vectors, commitment values, rejected attempts, and shared secrets | Intermediate state can reveal the private key |
| Randomness | Use an approved DRBG/RBG with health checks and independent domain-separated draws | Reuse or biased randomness can collapse security |
| Protocol | Use a standardized combiner and authenticate the whole handshake transcript | Ad hoc concatenation does not prove hybrid security |
| Validation | Run official known-answer tests, malformed-input tests, differential tests, fuzzing, and cross-library interoperability | Correct happy-path output is insufficient evidence |

The selected parameter set changes the cost margin but does not repair a
timing leak, reused random value, parser bug, faulted comparison, or exposed
secret. Implementation and protocol hardening therefore comes before merely
choosing the largest set.

## Hybrid deployment

A post-quantum/traditional hybrid can preserve confidentiality when one
component remains secure, but only if the combiner and transcript have a proof
for the surrounding protocol. NIST SP 800-227 specifies approved approaches.
RFC 10024 defines TLS 1.3 groups including X25519MLKEM768 and
SecP384r1MLKEM1024. Its analysis relies on the TLS 1.3 transcript and cannot be
copied into an unrelated protocol by concatenating two shared secrets.

For an SCBE transport, either use such a reviewed protocol directly or define
a separate composition specification and obtain independent cryptographic
review. ML-KEM decapsulation output should feed an approved KDF/AEAD path; it
should never be used as an authorization decision or exposed to geometry.

## Safe role for the dual-trit polarity field

The zero-centered field can wrap **public transcript bytes**:

```text
T = TLV(
    protocol_version,
    role,
    ML-KEM algorithm and parameter IDs,
    hash(public key),
    hash(ciphertext),
    ML-DSA algorithm and parameter IDs,
    signature context,
    hash(message transcript),
    nonce and policy receipt
)

F = CanonicalDualTritEncode(T)
R = cSHAKE256(F, function_name="SCBE-DTP-PQC", customization=profile)
```

Then bind `R` into the authenticated protocol transcript or sign it with
ML-DSA under a dedicated context such as `SCBE-PQC-RECEIPT-v1`. If `R` is sent
without a MAC, signature, or authenticated transcript, an attacker can replace
both `T` and `R`; it adds no integrity by itself.

Useful properties of this layer are:

- exact inversion and canonical-decoding checks before cryptographic use;
- six directional receipts that can localize corruption for diagnostics;
- an independent implementation path for detecting storage or transport
  faults in public artifacts;
- deterministic visualization and policy telemetry;
- explicit schema and purpose separation across SCBE layers.

The field must not encode or log `s`, `e`, `y`, rejected ML-DSA commitments,
private seeds, decapsulation keys, shared secrets, or KDF output. It must not
modify coefficient distributions, replace ML-KEM's ciphertext comparison, or
supply ML-DSA randomness. Those changes would leave the standardized security
argument.

## Test program for SCBE

1. **Conformance:** run FIPS known-answer and negative tests for every enabled
   parameter set and verify output against an independent implementation.
2. **Parsing:** mutate every length, bit field, coefficient encoding, algorithm
   ID, context, ciphertext, signature, and receipt field.
3. **Timing:** apply `dudect`-style statistics and secret-flow tooling to each
   target build; explicitly scan for division and variable-latency operations.
4. **Faults:** inject skipped comparisons, flipped branches, corrupted hashes,
   truncated buffers, stale randomness, and altered public transcript fields.
5. **Physical targets:** measure power and EM leakage on the actual embedded or
   accelerator target; software-only reasoning cannot validate masking.
6. **Protocol:** test downgrade, replay, role reflection, cross-context
   signatures, key substitution, algorithm confusion, and invalid-ciphertext
   response equivalence.
7. **Ablation:** compare the standards-only baseline with the dual-trit receipt
   enabled. Measure fault localization, false alarms, latency, bytes, and memory
   over at least three seeds or independent runs.

Success means the receipt leaves all standardized cryptographic outputs
unchanged, catches a stated fault class better than controls, and stays inside
its overhead budget. It does not justify claiming more post-quantum security
bits.

## Primary sources

- [NIST FIPS 203: ML-KEM](https://csrc.nist.gov/pubs/fips/203/final)
- [NIST FIPS 204: ML-DSA](https://csrc.nist.gov/pubs/fips/204/final)
- [NIST SP 800-227: Recommendations for KEMs](https://csrc.nist.gov/pubs/sp/800/227/final)
- [RFC 10024: PQ/T hybrid ML-KEM key agreement for TLS 1.3](https://www.rfc-editor.org/rfc/rfc10024.html)
- [RFC 9958: Post-Quantum Cryptography for Engineers](https://www.rfc-editor.org/rfc/rfc9958.html)
- [KyberSlash: secret-dependent division timings](https://kyberslash.cr.yp.to/papers.html)
- [Carry Your Fault: faults against masked LWE KEMs](https://arxiv.org/abs/2401.14098)
- [Finding and Protecting the Weakest Link: masked ML-DSA](https://eprint.iacr.org/2025/276)
