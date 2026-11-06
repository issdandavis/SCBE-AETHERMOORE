# Patent engineering repairs — 2026-09-09

The current RuntimeGate and both 14-layer decision modules now reject invalid
coordinates/decision inputs, use an explicit bounded safety-to-risk contract,
and admit reference observations only after a final ALLOW. The runtime distance
is now Poincare distance after a declared weighted embedding. These are local
engineering repairs to the September 9 review, not changes to preserved patent
documents or proof of complete system security.

## Changes and meaning

| Finding | Implemented repair | Evidence |
|---|---|---|
| NaN or out-of-range layer inputs could ALLOW | Both public L13 functions return finite DENY assessments; L12 rejects invalid distances/phase deviation; runtime rejects malformed six-coordinate vectors | Boundary regressions include NaN, infinity, negative distances, score bounds, threshold order and invalid realm IDs |
| Bounded safety score was compared with an unreachable H > 100 condition | H = 1/(1+d+2p); raw risk = 1-H; evidence risk = max(raw risk, 1-coherence); realm scaling cannot lower it | Fixed realm distance/coherence, increasing triadic distance now produces ALLOW, REVIEW, DENY, SNAP |
| Rejected requests moved the trusted reference | Evaluate first, then admit final ALLOW to raw/embedded means; late vetoes do not earn positive trust or update the trichromatic baseline | Direct-denial and calibration/full-path quarantine regressions; prior completed trust sets this request's headroom |
| Runtime called a Euclidean norm hyperbolic | Reuse the existing Poincare-distance implementation on explicitly embedded coordinates | Independent distance oracle away from origin; exact radial equivalence at origin; restart checks |
| Primary pipeline changed reference after its first evaluation | Generated realm centers no longer silently become calibrated reference points; explicit calibration sets the reference | Existing identical-input regression now passes; calibrated-profile suite passes |

For normalized coordinates x, use W = diag(phi^0,...,phi^5),
z = sqrt(W)x and E(x) = tanh(||z||/2) z/||z||, with E(0)=0. The stored reference
is the arithmetic mean of allowed E(x) values inside the convex unit ball,
not an intrinsic Frechet mean. Runtime cost is
pi ** (phi * min(d_Poincare(E(x), reference), 5)). At the origin the distance
equals ||sqrt(W)x||. Away from it this is a different metric and can produce
higher costs. Existing production thresholds were not loosened to hide changes.

L13 uses max(1-H, 1-coherence), multiplied by a realm weight only when that
increases risk, then clipped to [0,1]. Score thresholds theta/(1+theta) correspond
to the declared distance thresholds; risk >= 0.99 takes the SNAP branch. These
are explicit policy choices, not cryptographic security parameters or proved
optimal thresholds. A valid zero/neutral trit is not a malformed measurement.

## State and compatibility

Runtime snapshots are now `runtime-gate-state/v2`, with metric identifier
`weighted-poincare-tanh-half/allowed-reference-v2`. The new embedded reference
is persisted beside the raw mean used by spin checks. Candidate state is
validated before live state changes. Legacy v1 reference means and trust
history are discarded with a warning because they may contain rejected
observations. Query counts, cumulative cost and deny memory remain. Coordinate
backend/metric changes similarly discard incompatible references. Reflexes are
cleared on reset/reload and when the recorded threshold/backend fingerprint
changes; this is not a complete capability-cache authorization proof.

The first five RuntimeGate observations still use the existing calibration
policy. Final ALLOW is necessary for admission, but that does not prove the
observation is benign. Clean bootstrap and slow contamination resistance need
a stronger enrollment and adversarial evaluation protocol.

The old `full_system.py` demonstration aggregators retain their separate
cold-start/softening policy. They can override an L13 decision. Their existing
tests are compatibility tests, not evidence of mandatory DENY enforcement.
Use the repaired runtime gate's actual decision boundary when evaluating these
fixes; do not call the entire legacy system fail-closed on this evidence.

## Validation

All validation was offline, on CPU with two numerical threads, without new
dependencies or model downloads. Logs, original source bytes, before/after
hashes and a task-only patch are under `artifacts/patent_repairs_20260909/`.

| Run | Result |
|---|---|
| Original 48 new boundary/reference regressions against pre-edit code | 44 failed, 4 passed |
| Original runtime compatibility suite | 90 passed |
| Original primary 14-layer suite, verified preserved-source import | 4 failed, 47 passed |
| Repaired focused boundary/math/runtime/persistence/API/encoding/calibrated-profile suite | 162 passed |
| Repaired primary and legacy layer suites, separate interpreters/import paths | 51 + 51 passed |
| Existing primary and legacy full-system consumer suites | 20 + 20 passed |
| Same-pole repulsor and existing product-metric tests | 23 passed |

Total: 327 passing test executions in the final listed suites. The new test
file now has 52 cases, including four additional trust/council regressions.
Two old council fixtures needed a higher *test-only* direct-denial threshold
so the council could be exercised; separate tests require direct DENY under
the ordinary configured threshold. Stale primary tests for exponential H were
replaced with the bounded safety contract; assertions were not removed.
Existing pytest plugin-option and FastAPI lifespan deprecation warnings remain.
The repulsor's near-gate unauthorized fixtures now reach SNAP; their assertions
accept DENY or SNAP and still require ALLOW for the authenticated owner.

## Remaining review work

The original review's whole guarded-tool-call proof, legacy aggregator policy,
container recovery, cache/principal/resource binding, real instrumented CFI,
matched security/performance comparisons, PHDM import-path audit and actual
filed-document authentication remain open. No stronger cipher, complete
containment, learned generalization or patent coverage is claimed here.

Clay training continues under its unchanged external contract. The observed
contract contains no SCBE source pins. At 15:15 UTC, nine of twelve arms had
completed and a tenth had initialized; neither model weights nor its training
controller were changed by these repairs.
