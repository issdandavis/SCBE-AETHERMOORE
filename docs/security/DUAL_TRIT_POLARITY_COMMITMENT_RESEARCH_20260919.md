# Dual-trit polarity commitment research

**Review date:** 2026-09-19
**Status:** executable experimental encoding over a standardized hash
**Implementation:** `src/crypto/dual_trit_polarity_commitment.py`

## Result

The “zero cell expanding toward a full one cell in every direction” idea can be
made precise as a symmetric, reversible coordinate field. That field is useful
for byte routing, visual shells, inverse checks, multi-view receipts, and
tamper-evident audit structure.

It is not, by itself, a secure new hash. The implemented commitment derives its
cryptographic security from SHAKE256. The geometry is injective preprocessing
and receipt organization; it contributes no secret entropy and no independent
collision or preimage hardness.

## Field construction

For a byte `b` in `{0,...,255}`, define its centered coordinate:

```text
c(b) = 2b - 255
```

The coordinates are the 256 nonzero odd integers from -255 through +255. The
neutral value zero is reserved as an explicit center cell rather than assigned
to either polarity.

```text
shell(b)    = (|c(b)| + 1) / 2     in {1,...,128}
polarity(b) = sign(c(b))           in {-1,+1}
c(255-b)    = -c(b)
```

Every coordinate has a fixed six-trit balanced-ternary representation:

```text
c(b) = sum(t_i * 3^(5-i)) for i=0..5, where t_i in {-1,0,+1}
```

Six trits cover `[-364,364]`, so all centered bytes fit. The dual rail is:

```text
positive_rail(b) = (t_0,...,t_5)
negative_rail(b) = (-t_0,...,-t_5)
```

Thus every cell has two exactly related polarity views, and byte complementation
swaps the rails. These views are deliberately correlated; they are not two
independent hashes or two independent witnesses.

## Canonical byte field

The encoded transcript contains:

1. a versioned magic value;
2. an eight-byte payload length;
3. the explicit neutral center cell;
4. six fixed trit symbols and their six exact inverse symbols for every byte.

The decoder rejects unknown symbols, wrong lengths, a changed neutral cell,
non-inverse rails, even/zero/out-of-range centered coordinates, and
noncanonical trit representations. Exhaustive tests cover all 256 byte cells.

## Two commitment modes

### Fast root

```text
E(M) = canonical dual-trit encoding of M
R_fast = SHAKE256(
    domain || label_center || len(context) || context || len(E(M)) || E(M),
    512 bits
)
```

`dual_trit_root` is intended for integrity checkpoints where the radial views
do not need separate receipts.

### Full radial receipt

For each of six trit axes, the implementation extracts both polarity symbols
from every payload cell and hashes that directional stream:

```text
D_j = SHAKE256(domain || label_j || context || length || axis_stream_j, 512 bits)
C   = R_fast
R_full = SHAKE256(domain || label_root || context || length || C || D_0 || ... || D_5, 512 bits)
```

The six directional digests make the separate views auditable. `R_full` is
not claimed to be stronger than the 512-bit SHAKE256 boundary.

## Quantum interpretation

For an ideal `n`-bit hash output, generic quantum preimage search has
`O(2^(n/2))` query scaling through Grover search. Generic collision finding
has `O(2^(n/3))` query scaling in the Brassard-Hoyer-Tapp black-box model.
For a 512-bit output, those idealized exponents are approximately:

| Goal | Generic idealized query exponent |
|---|---:|
| Preimage | 256 bits |
| Collision | 170.7 bits |

These are asymptotic query models, not implementation security ratings. Circuit
depth, memory, parallelism, oracle cost, cryptanalytic structure, and future
algorithms matter. NIST's practical PQC categories compare multiple resource
metrics rather than assigning security from output length alone.

NIST currently recommends SHAKE256 as an XOF option for PQC submissions and
also identifies TupleHash256 and KMAC256 for structured hashing and MAC use.
Where tuple semantics or keyed authentication are required, use those
standardized constructions rather than inventing an ambiguous concatenation.

## Standard quantum-resistant structures to compose with

| Need | Standard structure | Place for the dual-trit field |
|---|---|---|
| Variable-length digest | SHAKE256 sponge/XOF | Canonical field is the message input |
| Named protocol/domain separation | cSHAKE | Put the protocol and schema in the customization string |
| Secret authentication | KMAC256 or HMAC-SHA-256 | Authenticate the field/root; polarity is not a key |
| Ordered structured records | TupleHash256 | Each field/view is a separate tuple member |
| Large parallel objects | ParallelHash | Hash canonical chunks, then combine through the specified tree |
| Public post-quantum signatures | FIPS 205 SLH-DSA or another approved release signature | Sign a domain-separated root; do not replace its internal hash structure |

FIPS 205 standardizes SLH-DSA, a stateless hash-based post-quantum signature
derived from SPHINCS+. Its tree and one-time-signature structure solves a
different problem from this reversible polarity encoding. If many dual-trit
objects need one signed checkpoint, their roots can be leaves in a conventional
domain-separated Merkle tree, with the resulting root signed by a reviewed
signature backend. Tree position, leaf/node labels, arity, length, and schema
must all be committed to prevent structural ambiguity.

## Why the trits remain outside the security boundary

Balanced ternary does not automatically resist classical or quantum attacks.
Curl-P is a cautionary balanced-ternary hash with published differential
cryptanalysis. Later work on Troika emphasizes that analysis tools for
non-binary designs are specialized and incomplete. This project therefore
keeps SHAKE256 as the security boundary and uses trits as an injective semantic
field.

The design rule is:

> Geometry may organize what is committed. A reviewed cryptographic primitive
> provides the commitment.

## Measured behavior

The benchmark used three fixed seeds, 512 random 64-byte inputs per seed, one
random flipped input bit per case, and 512-bit outputs.

| Mode | Mean changed output bits | Mean time/input | Relative to direct SHAKE256 | Observed collisions |
|---|---:|---:|---:|---:|
| Direct domain-separated SHAKE256 control | 49.9746% | 4.82 us | 1.00x | 0 / 1,536 |
| Fast dual-trit root | 50.0830% | 18.00 us | 4.14x | 0 / 1,536 |
| Full six-direction radial root | 49.9029% | 132.48 us | 30.57x | 0 / 1,536 |

Both avalanche deltas were inside two pooled seed standard deviations of the
direct control. That means this small test did not resolve a difference; it
does not prove randomness or collision resistance. No observed collision in
1,536 samples is only a smoke test.

The canonical field expands a 64-byte sample to 783 bytes. The fast root is
reasonable for selected object or action boundaries. The full radial mode
should be reserved for audit checkpoints, diagnostics, visualization, or
research measurements rather than token-level hashing.

Evidence:

- `reports/security/dual_trit_hash_benchmark_20260919.json`
- `tests/security/test_dual_trit_polarity_commitment.py`

## Safe SCBE integration

1. Use `dual_trit_root` as a domain-separated content commitment only where
   the reversible field is useful.
2. Use KMAC256 or HMAC-SHA-256 when a secret authenticates the commitment.
3. Sign the resulting protocol transcript with the selected release signature
   backend when public verification is required.
4. Carry the field's shell, polarity, and axes into Layers 1-12 as telemetry.
5. Let Layer 13 attenuate or reject a capability; never let geometry mint one.
6. Emit the chosen mode, schema version, context, algorithm, output length, and
   backend identity in Layer 14 receipts.
7. Keep canonical decoding strict and fuzz both the encoder and decoder.

## Primary sources

- [NIST FIPS 202, SHA-3 and SHAKE](https://csrc.nist.gov/pubs/fips/202/final)
- [NIST SP 800-185, cSHAKE/KMAC/TupleHash/ParallelHash](https://csrc.nist.gov/pubs/sp/800/185/final)
- [NIST FIPS 205, Stateless Hash-Based Digital Signature Standard](https://csrc.nist.gov/pubs/fips/205/final)
- [NIST PQC FAQ and symmetric primitive guidance](https://csrc.nist.gov/Projects/Post-Quantum-Cryptography/faqs)
- [NIST PQC security evaluation criteria](https://csrc.nist.gov/Projects/Post-Quantum-Cryptography/Post-Quantum-Cryptography-Standardization/Evaluation-Criteria/Security-%28Evaluation-Criteria%29)
- [Grover, A fast quantum mechanical algorithm for database search](https://arxiv.org/abs/quant-ph/9605043)
- [Brassard, Hoyer and Tapp, Quantum Algorithm for the Collision Problem](https://arxiv.org/abs/quant-ph/9705002)
- [Cryptanalysis of Curl-P](https://madars.org/papers/2020-curl-p.pdf)
- [Differential analysis of the ternary hash function Troika](https://eprint.iacr.org/2023/036.pdf)
