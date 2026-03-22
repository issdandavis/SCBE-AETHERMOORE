# SCBE Security Evidence Pack

Status: Internal working document — NOT for public release without review
Updated: 2026-03-22
Author: Issac Davis (@issdandavis)

---

## What This Document Is

A claim-by-claim evidence matrix for SCBE-AETHERMOORE's security properties.
Each claim has: an ID, a precise statement, supporting test files, sample
output, and known limitations.

This is engineering documentation, not marketing material.

---

## Definition

SCBE is a pre-execution control system that evaluates agent actions in a
multi-dimensional state space and enforces constraints before execution.

It is not a prompt filter, not a classifier, and not just encryption.

---

## A. Claims

### C1: Continuous Geometric Scoring

**Statement:** SCBE evaluates actions using a continuous cost function in
hyperbolic space, rather than binary allow/deny classification.

**Precise formula:** `H(d*) = pi^(phi * d*)` where phi = (1+sqrt(5))/2.

**What this means:** As an agent's state drifts further from safe operation
(d* increases), the cost grows super-exponentially. At d*=0: cost=1.
At d*=1: cost~5. At d*=2: cost~25. At d*=3: cost~128.

**Evidence:**
- `tests/test_qr_cube_kdf_hardened.py` — 42 tests verifying scalar properties,
  monotonicity, overflow behavior, HKDF structural properties
- `tests/test_qr_cube_pi_phi_kdf.py` — 20 tests verifying KDF contract
  (determinism, input sensitivity, domain separation, numeric hygiene)
- `src/symphonic_cipher/scbe_aethermoore/qr_cube_kdf.py` — canonical implementation

**Sample output:**
```
d*=0.0 → cost=1.000
d*=0.5 → cost=2.246
d*=1.0 → cost=5.047
d*=2.0 → cost=25.47
d*=3.0 → cost=128.5
```

**Limitation:** This function is unbounded — at large d* it overflows float64.
The bounded safety score `H_score = 1/(1+d+2*pd)` is used for governance
decisions. The relationship between the two is documented in
`docs/L12_HARMONIC_SCALING_CANON.md` but not yet validated by external review.

---

### C2: Multi-Dimensional Semantic Dispersal

**Statement:** SCBE encodes content across 6 linguistic dimensions (Sacred
Tongues: KO, AV, RU, CA, UM, DR) weighted by golden ratio powers
(1.00, 1.62, 2.62, 4.24, 6.85, 11.09). This creates a multi-dimensional
semantic fingerprint where changes in any dimension are detectable.

**Evidence:**
- `tests/test_langues_dispersal.py` — 24 tests covering spin quantization,
  dispersal rate, routing decisions, and integration with real corpus data
- `src/storage/langues_dispersal.py` — dispersal computation with metric tensor

**Key empirical result (1713 real records from 15 sources):**
```
Dispersal rate:      5.006
Spin entropy:        0.784
Effective dimension: 5.20 out of 6
Unique spin codes:   161 out of 729 possible
Dominant tongue:     DR (phi^5 = 11.09 weight)
```

**Triple encoding validation (50 real records, KO/CA/DR perspectives):**
```
Correlation KO-CA: 0.14  (nearly independent)
Correlation KO-DR: 0.10  (nearly independent)
Correlation CA-DR: 0.60  (moderate overlap)
Anisotropy ratio:  0.62
Verdict: Triple encoding carries independent signal.
```

**Limitation:** The 6D tongue coordinate derivation from text metrics is
simplistic (word count, digit ratio, etc.). The dispersal properties are
real but the quality of the underlying encoding depends on the tokenizer.
Not yet tested with adversarial inputs designed to manipulate specific
tongue dimensions.

---

### C3: Tamper Detection Sensitivity

**Statement:** SCBE detects data tampering through geometric consistency
rather than signature verification alone. Multiple detection mechanisms
operate simultaneously.

**Evidence:**
- `tests/test_tamper_detection.py` — 17 tests across 7 attack vectors

**Results by attack vector:**

| Attack | Detection Method | Result | Test |
|---|---|---|---|
| Coordinate drift (+0.5) | Chladni mode change → noise | Detected | `test_single_bit_flip_in_vector_produces_noise` |
| Gradual drift (0.01/step) | Spin code transition | Detected | `test_gradual_drift_detection` |
| Content swap | SHA-256 hash mismatch | Detected | `test_content_swap_detected_by_hash` |
| Replay old coords | Chladni mode mismatch | Detected | `test_replay_old_coords_on_rekeyed_content_fails` |
| Bulk injection (10/100) | Dispersal rate + dim shift | Detected | `test_dispersal_rate_shifts_on_injection` |
| Cross-surface tamper | Hash comparison across stores | Detected | `test_hash_mismatch_across_surfaces` |
| Prompt injection payload | Tongue coordinate shift | Detected | `test_injection_changes_tongue_coords` |

**Limitation:** These tests use internally generated attack payloads, not
standardized adversarial datasets. The Chladni access control depends on
the (n,m) mode derivation from tongue coordinates — if an attacker knows
the derivation function, they can compute the correct mode. The security
rests on the secrecy of the tongue coordinates, not the algorithm.
This is analogous to Kerckhoffs's principle — the system should be secure
even if the algorithm is known. Currently it is NOT: knowing the tongue
coords reveals the Chladni mode.

---

### C4: Cross-Language Dispersal

**Statement:** Because SCBE processes content across 6 weighted dimensions
simultaneously, attacks that exploit a single linguistic dimension (e.g.,
low-resource language bypass) produce anomalous dispersal patterns
detectable through spin vector changes.

**Evidence:**
- Dispersal analysis on 1713 real records shows 5.2 of 6 dimensions active
- Spin entropy of 0.784 indicates non-degenerate distribution across codes

**Limitation:** Not yet tested against actual cross-language adversarial
attacks. The "6 tongues" are not real languages — they are phi-weighted
mathematical dimensions. The mapping from natural language to tongue
coordinates is the weakest link.

---

### C5: Trust-Cost Amplification

**Statement:** The golden ratio weighting creates a natural hierarchy where
security-critical dimensions (DR=integrity, UM=redaction) are automatically
more expensive to tamper with than operational dimensions (KO=intent,
AV=transport).

**Evidence:**
- `test_metric_weighted_tamper_costs_more_in_dr`: DR tamper costs 11.09x
  more than KO tamper for the same magnitude shift

**Sample calculation:**
```
KO shift of 0.3: cost = phi^0 * 0.3 = 0.30
DR shift of 0.3: cost = phi^5 * 0.3 = 3.33
Ratio: 11.09x
```

**Limitation:** The 11x cost ratio is a property of the metric, not an
empirically validated security guarantee. An attacker who understands
the weighting can focus attacks on low-weight dimensions. The question
is whether meaningful attacks are possible by only manipulating low-weight
dimensions — this has not been tested.

---

## B. Threat Model

### In scope (tested)
- Content tampering (bit flips, swaps, gradual drift)
- Coordinate manipulation (tongue vector shifting)
- Bulk data injection (poisoning)
- Cross-surface consistency violations
- Replay attacks (old coordinates after rekey)

### Out of scope (not tested)
- Adaptive adversarial attacks (iterative optimization against the cost function)
- Model extraction (inferring the tongue coordinate derivation)
- Side-channel attacks (timing, power analysis)
- Direct prompt injection through the 14-layer pipeline
- Attacks at the Poincare ball boundary (known vulnerability per Dec 2024 paper)

### Known vulnerabilities
1. **Poincare boundary**: Position-adaptive attacks achieve high success rates
   near the ball boundary where hyperbolic distance computations lose precision.
   Partial mitigation: AUDIT_EPSILON boundary clamping.
   Recommended hardening: Lorentz model dual representation for boundary operations.

2. **Chladni mode predictability**: If attacker knows tongue coordinates, they
   can compute the correct Chladni (n,m) mode and bypass access control.
   The security depends on coordinate secrecy, not algorithmic secrecy.

3. **Tongue coordinate derivation**: The mapping from text → 6D coordinates
   uses simple text metrics. A sophisticated attacker could craft content
   that produces specific tongue coordinates.

---

## C. Comparisons

**Wording note:** Comparisons use "classifier-based," "rule-based,"
"signature-based," "monitoring-based" categories. We avoid asserting
total uniqueness. Instead: "appears uncommon" or "we have not found
deployed systems that document this combination."

### Category placement

| Category | Examples | SCBE difference |
|---|---|---|
| Classifier-based | Azure Prompt Shields, Anthropic Constitutional Classifiers, Meta PromptGuard | SCBE uses continuous scoring, not binary classification |
| Rule-based | AWS Bedrock Guardrails, NVIDIA NeMo | SCBE constraints are geometric, not rule-defined |
| Signature-based | NIST/CISA recommended approach | SCBE adds geometric consistency on top of signatures |
| Monitoring-based | DARPA GARD/SABER, enterprise red teaming | SCBE is preventive (pre-execution), not detective |
| State-space control | **SCBE** | Evaluates actions in bounded hyperbolic state space |

### Defensible positioning statement

> SCBE-AETHERMOORE is an experimental AI governance architecture that
> evaluates agent actions within a constrained hyperbolic state space,
> where deviations increase security cost and trigger additional validation
> before execution.
>
> Unlike classifier-only or rule-only approaches, SCBE treats security
> as movement through a bounded geometric space. Early internal tests
> suggest this approach detects several classes of data tampering through
> geometric consistency rather than pattern matching.
>
> The system is under active development. Internal benchmarks are
> encouraging but have not yet been validated against standardized
> adversarial datasets or external red teams.

---

## D. Test Summary

```
 42  hardened KDF tests (pi^phi scalar, HKDF, edge cases, ternary trits)
 20  KDF contract tests (determinism, sensitivity, domain separation)
  9  scalar formula tests
  7  flux parameters (quorum consensus)
 24  langues dispersal (spin, routing, integration)
 17  tamper detection (7 attack vectors)
 13  fusion surfaces (CymaticCone, SemiSphereCone, TongueRouter)
 17  lightning query (routing, feedback, adaptation)
 10  tri-lattice membrane (three-lattice experiment)
---
159  security-relevant tests (this session)
326  total tests green (including storage benchmarks)
```

---

## E. Next Steps (ordered by impact)

1. **Adversarial benchmark**: Run 100+ prompt injection examples through
   SCBE scoring. Measure baseline vs SCBE-gated success rate.

2. **Boundary hardening**: Implement Lorentz model dual representation
   for operations near the Poincare ball boundary.

3. **External red team**: Invite security researchers to attack the
   Chladni access control and tongue coordinate derivation.

4. **Standardized dataset**: Test tamper detection against NIST/MITRE
   adversarial ML datasets (not just internally generated attacks).

5. **Paper draft**: "Geometric State-Space Control for AI Agent Security"
   — submit to arXiv as experimental/position paper, not as solved-problem.
