# From expansion wake to verified lattice search

Date: 2026-09-07
Status: **defensive research map; no deployed-key attack claim**

## Decision

The particle-after-expansion analogy is useful if it is stated as an inverse
problem. A compact private state is expanded and transformed into a much larger
public object. The public object still obeys exact algebraic relations, but a
cryptographic hash or XOF deliberately destroys useful *locality*: nearby seeds
should not produce nearby public values. A search method therefore needs a
measurable invariant, side channel, bias, or algebraic bound. Geometry cannot
recover information that is absent from its observations.

The strongest research direction for the existing dual-trit and oriented-zero
work is an **audited scheduler for established lattice solvers**. The topology
can encode bounded choices, regions, restarts, and receipts. The score and
pruning authority must come from the LWE equations, basis-reduction state, and
verified implementation measurements.

## The “particle” model in ML-KEM

At a simplified level, ML-KEM key generation performs this deterministic
expansion:

```text
(rho, sigma) = SHA3-512(d || parameter)
A            = SampleNTT(rho)
s, e         = SampleCBD(PRF(sigma, counters))
t            = A*s + e  (in the specified polynomial module)
public key   = Encode(t) || rho
```

The private origin is not a particle in physical space. It is the seed and the
small secret/error polynomials. The public key exposes `rho`, the matrix derived
from it, and `t`. Recovering the private state is constrained by `t = A*s + e`,
which is why primal, dual, decoding, hybrid, and distinguishing attacks work in
lattice space rather than walking adjacent seed integers.

The expansion does not create entropy. It deterministically diffuses the seed
through SHA3/SHAKE and module arithmetic. In principle, exhaustive preimage
search could reproduce an origin. In practice, the 256-bit seed domain and the
intended one-way behavior remove a useful smooth route back to it.

This also corrects two claims in the earlier AI-generated discussion:

- ML-KEM and ML-DSA use related families of module-lattice mathematics, but
  they have different keys and security purposes. A protocol does not normally
  require an adversary to break both at the same instant.
- An implementation can couple them through reused randomness, cache state,
  power, faults, or control flow. That is a real system-level concern, but it is
  not an innate shared key space in the standards.

[FIPS 203](https://doi.org/10.6028/NIST.FIPS.203) specifies the ML-KEM expansion
and describes its security as related to Module-LWE. [FIPS
204](https://doi.org/10.6028/NIST.FIPS.204) specifies the separate ML-DSA
signature role and says key pairs must not be reused for other purposes.

## Where a “wake” can survive

| Candidate wake | Observable evidence | Research status |
| --- | --- | --- |
| Adjacent seed locality | Distance between expanded outputs | The local 4,096-pair SHA3-512 probe found no effect above two pooled standard deviations. |
| Raw trit-coordinate locality | Candidate Hamming distance versus modular residual | Near-zero correlation in the local 100- and 300-seed toy experiments. |
| Algebraic interval structure | A proved lower bound on all candidates in a box | Useful on tiny LWE: 12.70x fewer complete candidates than exhaustive search, with exact recovery. |
| Reduced-basis structure | Gram-Schmidt profile, column variance, projected residuals | Established attacks use it; this is the best place to test an adaptive scheduler. |
| Atypical secret distribution | Sparse binary/ternary or unusually small secrets | Learned attacks have recovered such challenge instances, but this does not establish a break of normal ML-KEM secrets. |
| Timing, power, EM, or faults | Measurements correlated with secret-dependent operations | Demonstrated against particular implementations; this attacks implementation leakage rather than Module-LWE directly. |
| Related or reused randomness | Cross-session or cross-primitive statistical relation | Potentially serious if present; prevent it with domain separation, independent keys, and health-tested randomness. |

The learned-cryptanalysis record is narrower than the earlier AI response
implied. [SALSA](https://arxiv.org/abs/2207.04785),
[PICANTE](https://arxiv.org/abs/2303.04178), and [SALSA
VERDE](https://arxiv.org/abs/2306.11641) show that models can assist recovery
for selected small, sparse-secret LWE regimes. They rely on algebraic samples
and, in PICANTE, lattice preprocessing. They do not show that a neural model can
intuit a generic route through an ML-KEM key space.

The more recent [Benchmarking Attacks on
LWE](https://arxiv.org/abs/2408.00882) compares neural and conventional attacks
under common accounting. It reports recovery of very sparse secrets at
Kyber-like dimensions, not ordinary full ML-KEM keys. Its accompanying code is
noncommercially licensed, so it can inform a research benchmark but must not be
copied into a commercial product without license review.

The “wake” analogy fits implementation leakage more directly.
[KyberSlash](https://eprint.iacr.org/2024/1049) demonstrated timing leakage from
secret-dependent division in affected Kyber implementations. Separate studies
have demonstrated [fault attacks against Keccak-based PQC
implementations](https://eprint.iacr.org/2024/1522) and [power leakage after
timing fixes](https://eprint.iacr.org/2024/2051). Those results support external
verification, constant-time review, entropy separation, and fault detection.
They do not weaken every conforming implementation or the underlying standard
by themselves.

## What the local experiments already established

1. An exact modular interval bound recovered all planted secrets in 100 tiny
   instances and reduced complete-candidate evaluations from 6,561 to 516.61 on
   average. This is a real bounded-search result for that toy distribution.
2. Four-anchor box ordering did not improve the bound. It lost on 87 of 100
   seeds and remains **UNDERPOWERED**.
3. A corrected 360-state dual-trit phase cover improved geometric coverage, but
   random candidates still obtained better LWE objectives. Better coordinate
   coverage did not create measurement-space locality.
4. Adding the phase probes before the exact solver cost more total work than the
   algebra-only solver on all 300 instances.
5. The exact oriented-zero controller is useful for hysteresis, bounded chart
   changes, quarantine, and receipts. On toy LWE it reproduced a direct route
   schedule and added no independent search gain.

These are useful negative and positive results. They prevent the project from
spending compute on a visually appealing geometry that lacks an observable
signal, while retaining the exact control machinery that did work.

Detailed local results:

- [`MULTISCALE_LWE_BOX_FIELD_RESEARCH.md`](MULTISCALE_LWE_BOX_FIELD_RESEARCH.md)
- [`DUAL_TRIT_TORUS_LWE_RESULT.md`](DUAL_TRIT_TORUS_LWE_RESULT.md)
- [`DUAL_TRIT_PHASE_DEBIAS_RESULT.md`](DUAL_TRIT_PHASE_DEBIAS_RESULT.md)
- [`ORIENTED_ZERO_HYBRID_RESULT.md`](ORIENTED_ZERO_HYBRID_RESULT.md)

## Preregistered next experiment

The machine-readable protocol is
[`lattice_scheduler_preregistration_20260907.json`](../research/evidence/lattice_scheduler_preregistration_20260907.json).
Its purpose is to test one falsifiable claim:

> Given the same solver operations, samples, wall time, CPU/GPU time, and memory,
> an exact dual-trit controller using algebraic reduction telemetry lowers total
> secret-recovery cost on held-out public LWE challenge distributions.

### Solver layer

Use established public implementations or compatible reimplementations of:

- primal/uSVP and primal drop-and-solve;
- dual distinguishers and dual-hybrid meet-in-the-middle;
- BKZ-based preprocessing;
- the maintained [LWE Estimator](https://github.com/malb/lattice-estimator) for
  cost estimates, never as proof of a measured recovery.

The 2025 analysis [Cool and Cruel is
Dual](https://eprint.iacr.org/2025/1002) is important here: apparent geometric
features can be alternate descriptions of known dual behavior, and a primal
drop-and-solve control can outperform them. Both families belong in the
baseline set.

### Controller layer

At each bounded decision point, the controller observes only declared solver
telemetry:

```text
GSO slope and profile shape
column and projected-residual variance
current BKZ block size and tours
dropped coordinates and retained samples
estimated remaining work
measured CPU/GPU seconds and peak memory
restart and collision counts
```

Dual trits encode `decrease / hold / increase` for one permitted parameter at a
time. Oriented zero is a quarantine state when the evidence is absent,
conflicting, nonfinite, or inside a hysteresis band. Every proposed action must
pass a deterministic legality and budget checker before the solver executes it.
The model never supplies a secret, cryptographic proof, or authorization.

### Mandatory controls

1. The solver's default schedule with no intervention.
2. A fixed expert schedule.
3. A uniformly random legal scheduler with the same decision budget.
4. A size- and compute-matched learned policy without trit/topological
   coordinates.
5. The best applicable established primal or dual attack.

Training and tuning instances must be separate from held-out dimensions,
moduli, secret distributions, and random seeds. Preprocessing, feature
extraction, failed restarts, duplicate proposals, model training, and memory are
all charged. A low final residual without exact secret recovery is not a hit.

### Decision rule

Call the controller useful only when it:

- recovers the exact planted secret or wins the declared decision game;
- beats both the no-intervention baseline and its matched random/learned
  control;
- shows an effect larger than two pooled standard deviations over at least
  three independent seeds per condition;
- retains the effect on out-of-distribution dimensions and secret families;
- reports the complete scaling curve and all compute/memory costs.

Anything weaker is **UNDERPOWERED** or **NO ADVANTAGE**, not a cryptographic
break. Normal ML-KEM parameters remain out of scope until a public challenge
result and independent reproduction justify that claim.

## Security boundary in the current SCBE code

The repository correctly refuses its historical nonsecure Kyber-like embedding
unless an explicit insecure test opt-in is present. The real wrapper prefers
ML-KEM-768 and ML-DSA-65 backends and fails closed when only the simulation is
available. That boundary must remain intact.

One integration label needs later hardening:
`authorize_pqc_level()` checks configured integer levels, then returns the text
`PQC authorized`. It does not verify a signature, KEM transcript, backend tier,
key provenance, entropy health, or implementation attestation. The lower
constructor currently fails closed, which limits immediate risk, but the layer
should be described as a **configuration policy check** or require an attested
real backend before claiming PQC authorization.

FIPS 204 already requires integer arithmetic rather than floating-point
rounding for conforming ML-DSA implementations. The project's exact fractions,
trits, and signed approach states are compatible with deterministic control and
audit. They should remain outside the cryptographic primitive unless analyzed
and standardized separately.

## Publication threshold

This can become publishable research if the adaptive scheduler beats the
mandatory controls on recognized public challenge instances, scales beyond the
training regime, includes full cost accounting, releases reproducible code and
seeds, and survives independent reproduction. A carefully controlled negative
result can still be a useful technical report because it identifies which
geometric intuitions fail and which algebraic signals survive.

The current evidence supports a research program, not a new attack on ML-KEM or
ML-DSA. It also supports the larger security design: standardized cryptography
and non-agentic controls form the root; neural/topological components propose,
prioritize, quarantine, and explain actions under independently verified rules.

The primary-source claim ledger is
[`lattice_inverse_sources_20260907.json`](../research/evidence/lattice_inverse_sources_20260907.json).
Focused validation evidence is
[`lattice_inverse_validation_20260907.json`](../research/evidence/lattice_inverse_validation_20260907.json).
