# Dual-trit phase interference correction — 2026-09-07

Status: **geometric interference removed; toy-LWE objective advantage remains
UNDERPOWERED.** This is a bounded finite-field experiment, not an ML-KEM,
ML-DSA, Kyber or Dilithium attack claim.

## Existing components reused

The correction uses the repository's exact integer 30-degree cyclotomic action,
nine-state dual ternary table, trit torus built from existing hypercube support
edges, toy-LWE residual objective and safe interval bound. The earlier lossy
phase implementation and its evidence remain unchanged for comparison.

## Interference found and removed

The first wheel applied `sign()` to exact rotated integer coefficients. That
many-to-one projection collapsed different phase states. Taking only the early
prefix compounded the distortion.

`toy_lwe_phase_debias.py` instead reduces every exact rotated coefficient to its
balanced representative modulo three. This is a permutation of the finite trit
field. It then keeps complete 12-phase orbits and greedily selects the orbit
whose radius-one neighborhood covers the most still-uncovered states. The
selection reads no LWE matrix, public value, secret, residual or score.

| Exact whole-space measure | Legacy phase | Corrected phase | 100 random sets, mean |
| --- | ---: | ---: | ---: |
| Mean nearest Hamming distance | 1.5621 | **1.1975** | 1.3279 |
| States within distance 0 or 1 | 2,916 | **4,906** | not used for selection |
| Maximum coordinate-count deviation | 76 | **2** | 17.69 |
| Maximum pair-cell deviation | 66 | **4** | 17.00 |
| Members in complete phase orbits | 0/360 | **360/360** | n/a |

The corrected set beat every random control on all three preregistered coverage
effects by more than two population standard deviations. This confirms useful
locality in the finite **secret-coordinate geometry** and removes the original
phase construction's interference.

## Independent toy-LWE confirmation

The objective check used 300 fresh seeds numbered 10000 through 10299. Each
heuristic received exactly 360 residual evaluations. The exact interval solver
recovered the planted optimum in 300/300 cases; the first 12 were also checked
by exhaustive 6,561-candidate search.

| Method | Exact hits | Mean nearest Hamming | Mean selected Hamming | Mean score gap |
| --- | ---: | ---: | ---: | ---: |
| Legacy phase | 15/300 | 1.613 | 5.160 | 3,941.58 |
| Corrected complete-orbit cover | 15/300 | **1.210** | 5.060 | 3,909.13 |
| Uniform random | 21/300 | 1.280 | **4.987** | **3,828.33** |
| Corrected cover then torus walk | 6/300 | 1.747 | 5.340 | 4,092.13 |
| Random then torus walk | 19/300 | **1.627** | **4.990** | **3,891.58** |

The cover gets physically closer to the secret, as intended. The modular LWE
residual still has essentially zero correlation with raw Hamming distance, so
the score cannot identify that nearby foothold. No paired LWE objective effect
exceeded the required threshold.

## Geometry-to-algebra handoff

The proposed hybrid was tested directly. Sixty complete-orbit probes seeded the
incumbent for the unchanged safe interval lower bound. Every initial objective
call was charged.

| Exact method | Mean initial probes | Mean later evaluations | Mean total evaluations |
| --- | ---: | ---: | ---: |
| Algebraic bound alone | 0 | 526.61 | **526.61** |
| Corrected phase cover, then bound | 60 | 520.47 | 580.47 |
| Random probes, then bound | 60 | 519.13 | 579.13 |

The phase probes saved about 6.14 later evaluations but cost 60, adding about
53.86 total evaluations. They lost to the algebra-only solver on all 300
instances. Geometry therefore stays disabled as an LWE prepass.

The next mathematically relevant metric would live in the matrix-induced
measurement space, such as the centered modular displacement of `A(s-t)`,
rather than raw trit Hamming distance. Such a metric must still beat the exact
bound and matched random ordering before use.

Machine-readable evidence:
`../research/evidence/toy_lwe_phase_debias_20260907.json`. Chart:
`../research/evidence/toy_lwe_phase_debias_20260907.png`.
