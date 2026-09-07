# Integer phase shards — research specification

Status: experimental composition scaffold. This is not a new cipher, entropy
source, post-quantum primitive, or production key ceremony.

## User concept translated into exact operations

Four 256-bit source samples are treated as full integers. The proposed scale
`2.75` is the exact rational `11/4`. For each input `x_i`, the transform runs:

```text
n_i = 11*x_i + c_i
(y_i, c_(i+1)) = divmod(n_i, 4)
```

The terminal remainder is retained. Decoding walks backward:

```text
n_i = 4*y_i + c_(i+1)
c_i = n_i mod 11
x_i = (n_i - c_i) / 11
```

Valid streams have `c_i` in `{0,1,2,3}`. This realizes “move the fraction to
the end and keep going” without floating point or rounding.

Thirty-degree phase is represented by a formal twelfth root of unity `zeta`:

```text
zeta^4 - zeta^2 + 1 = 0
zeta^12 = 1
```

Multiplication by `zeta` maps integer coefficients as follows:

```text
(a0, a1, a2, a3) -> (-a3, a0, a1+a3, a2)
```

Twelve applications return exactly to the original tuple. A Z coordinate is
derived from all source material and included in the conditioned transcript.
It is not counted as independent entropy.

## Two meanings of “prime”

The primed-anchor witness uses **prime as a selected reference**, not as a
claim of mathematical primality. Any integer can be the local origin. Given
signed correction terms and an observation, it records the residual:

```text
predicted = anchor + sum(corrections)
residual  = observed - predicted
```

The residual magnitude passes through the exact `11/4` carry transform and its
sign remains explicit. A keyed HMAC binds the anchor, every correction, the
carried residual, scale, and context. This behaves like a spotter's calibrated
record: changing the target, range/wind-like correction, measurement, or
context breaks verification. It is an authenticated coordinate witness, not a
randomness source and not a proof that the anchor is a prime number.

The separate prime-factor yardstick uses actual mathematical primes to encode
an exponent vector. Unique factorization makes that representation exact and
reversible at arbitrary integer depth, but the scalar can become much larger
than the vector. Distances must be computed after decoding the exponent vector;
scalar magnitude or logarithmic distance is not a substitute for that metric.

## Cryptographic boundary

The transforms are bijections, so they preserve the source information. They
do not increase min-entropy. The raw framed samples and transformed state are
both passed through HKDF-SHA256. Source commitments use SHA3-256. Branch and Z
material use separate HKDF labels.

The public receipt contains source identifiers and commitments, canonical
context hash, ceremony nonce, transform commitment, integer scale, and phase
step. It never contains the raw samples, root key, transformed coordinates, or
Z secret. These hashes can still confirm guesses about weak source values.
Do not publish a receipt when a source is a password, counter, decimal seed,
human-chosen number, or any other value without a defensible min-entropy bound.

The 5W/How authorization transcript belongs in the canonical `context` input:

- Who: principal, delegation, and key identifiers.
- What: exact action and expected effects.
- When: nonce, counter, issue time, and expiry.
- Where: device, workspace identity, network, and trust ring.
- Why: declared purpose plus evidence references.
- How: tool, arguments, isolation, budget, and rollback.

The caller must sign and verify that complete transcript. A context hash alone
does not authenticate it.

## Broken-glass split and tree

The initial experiment implements a two-of-two split:

```text
owner_share   = independent random 256-bit value
service_share = root_key XOR owner_share
root_key      = owner_share XOR service_share
```

Uniform owner randomness makes either share alone independent of the root.
Production multi-device recovery should use a reviewed threshold scheme and,
where possible, perform threshold operations without reconstructing the key.

Tree nodes bind path, epoch, phase, and context. A deterministic child does not
provide post-compromise recovery: parent compromise reveals that child.
Supplying fresh independent entropy to a node and securely erasing the old key
creates the intended ratchet boundary.

## Assumptions and tests required before integration

1. Identify the physical origin of each source. Four wrappers around the same
   operating-system generator are one source.
2. Estimate and document source min-entropy and source-specific health tests.
3. Use commit/reveal if mutually distrustful participants contribute samples,
   preventing a final participant from adapting its input after seeing others.
4. Store the owner share in a passkey, hardware token, or separately encrypted
   recovery medium. Do not place both shares in the same account or backup.
5. Bind ceremony version, algorithms, source IDs, 5W/How context, commitments,
   and owner acknowledgement into the signed GeoSeal transcript.
6. Keep ML-KEM, ML-DSA, SLH-DSA, AEAD, and the Agent Bus enforcement boundary
   unchanged. This transform may organize their keys; it does not replace them.
7. Obtain independent cryptographic review before protecting valuable data.

The focused test suite checks exhaustive small-domain injectivity, randomized
256-bit reversal, twelve-step phase identity, absence of floating-point
constants, keyed primed-anchor reconstruction and tamper rejection,
source/context binding, RFC 5869 HKDF vectors, tree separation, and two-of-two
reconstruction.
