# Security validation: oriented-zero hybrid control

Scope: the new isolated research module
`src/crypto/oriented_zero_hybrid.py` and its benchmark interface. This is a
standalone validation of five concrete failure hypotheses, not a repository-
wide security scan.

## Validation rubric

- [x] Exact input semantics: reject floating values, oversized integers,
  invalid trits, and a side that conflicts with a nonzero coordinate.
- [x] Transition authority: reject duplicate, missing, undeclared, and unsafe
  region edges before they can authorize a jump.
- [x] Runtime boundedness: cap arithmetic, graph and trace size; prevent
  threshold chatter; and bound every cycle with hysteresis, reset, dwell, and
  a finite jump count.
- [x] Evidence integrity: detect changed/reordered receipts and reproduce the
  complete trace through the package API.
- [x] Claim discipline: compare the graph schedule with direct, no-intervention,
  and equal-objective-budget controls before claiming search value.

Validation used focused package-API tests, exhaustive finite-state traces, a
real benchmark CLI invocation, adjacent regressions, source tracing, and exact
symbolic checks. No network service or production cryptographic primitive was
needed or exercised.

## Closure table

| Candidate | Root control | Source | Sink/control | Disposition | Confidence |
| --- | --- | --- | --- | --- | --- |
| OZ-HYB-001: ambiguous zero side selects an unauthorized region | `oriented_zero_hybrid.py:261-274` | caller-supplied observation | `advance()` jump lookup | suppressed | high |
| OZ-HYB-002: malformed or ambiguous graph authorizes an unintended edge | `oriented_zero_hybrid.py:186-221` | caller-supplied graph policy | `RegionGraph.edge()` | suppressed | high |
| OZ-HYB-003: crafted size or near-zero oscillation causes unbounded work | `oriented_zero_hybrid.py:34-54`, `186-224`, `448-553` | oversized policy/value or repeated observations | exact arithmetic and transition loop | suppressed | high |
| OZ-HYB-004: receipt hashes are mistaken for hostile-writer authentication | `oriented_zero_hybrid.py:13-18`, `563-624` | graph/receipt writer | audit-chain trust boundary | deferred | high |
| OZ-HYB-005: graph structure is claimed to locate a hidden toy-LWE target | `oriented_zero_hybrid_benchmark.py:320-449` | public toy objective | search result/claim | not_applicable | high |

## OZ-HYB-001 — suppressed

Attacker input: an observation containing a coordinate, side trit, and routing
context. The security-relevant sink is the regional `JUMP` in `advance()`.

The constructor rejects every nonzero coordinate whose side differs from its
sign (`oriented_zero_hybrid.py:274`). At exact zero, side `0` reaches
`QUARANTINE`; it does not fall through to either directional edge
(`oriented_zero_hybrid.py:478-483`). Missing contexts reach `DENY`
(`oriented_zero_hybrid.py:493-497`). Dynamic tests cover both sides, neutral
zero, conflicting sides, invalid trits, and missing context. The candidate does
not survive for the tested package boundary.

Remaining uncertainty: a future caller could label an exact zero with a false
remembered side before constructing the typed observation. Side provenance is
an integration responsibility and must be independently receipted.

## OZ-HYB-002 — suppressed

Attacker input: a malformed graph configuration. The sink is edge selection for
an authorized state jump.

Graph construction requires immutable typed tuples, unique region IDs and edge
keys, declared endpoints, positive budgets, ordered guards, and a reset at or
beyond the destination exit radius (`oriented_zero_hybrid.py:178-206`). Dynamic
tests exercise duplicate edges, unknown endpoints, negative and inside-guard
resets, wrong member types, and post-construction duplicate-edge tampering. All
fail closed before a jump.

Remaining uncertainty: trusted graph provenance is outside this module and is
tracked under OZ-HYB-004.

## OZ-HYB-003 — suppressed

Attacker input: oversized exact values, graphs, traces, or arbitrarily repeated
values on or around the enter threshold. The impact hypothesis is excessive
arithmetic/iteration work or policy chatter.

Exact numerator/denominator components are capped at 4,096 bits, graphs at
1,024 regions and 4,096 edges, and a trace at 1,000,000 observations. Tests
prove oversized values and collections fail before arithmetic or iteration.
The graph also requires `enter < exit`; every jump disarms the guard; only a
later sample at or beyond the exit radius rearms it; minimum dwell and a finite
jump budget add independent bounds. One hundred repeated exact-zero samples
caused one jump. Across 100 paired traces, threshold-only control emitted 132
events per trace while the hybrid emitted the intended 12. Exhaustive
enumeration of 15,625 length-six traces and 93,750 steps found zero invariant
failures and no consecutive jumps. This candidate does not survive in the
bounded package API.

Remaining uncertainty: wall-clock resource bounds for a host that submits an
unbounded number of observations still belong at the outer process/service
boundary.

## OZ-HYB-004 — deferred production requirement

Attacker input: a writer able to replace both graph/receipt content and all
untrusted hashes. The affected boundary is any future authorization system that
treats the receipt head as proof of authorship.

The chain binds graph digest, prior digest, state, exact observation, outcome,
and accounting. Tests prove that changed fields, reordering, route
discontinuities, and changed graph policies fail verification, and full replay
reconstructs all receipts. This is strong evidence of deterministic tamper
detection when the expected graph/head comes from a trusted source.

Counterevidence to an authentication claim: SHA-256 linkage alone has no secret
or signer. A hostile writer who controls the trust anchor can regenerate the
entire chain. The module and report state this explicitly, and production
GeoSeal integration remains disabled. Before integration, sign or externally
anchor the graph digest and receipt head, then validate key ownership and
rollback handling through the actual ingress.

## OZ-HYB-005 — not applicable as a security finding; research claim refuted

The benchmark compiled the same coarse-to-fine toy-LWE schedule through the
graph and directly. Candidate, score, objective-evaluation count, and route
matched on all 100 seeds. The graph reached the exact optimum score 5/100 times;
the equal-budget random control reached it 3/100 times. The graph's mean score
lead over random did not exceed two population standard deviations, and it did
not pass that gate against the unit-step control.

The implementation therefore makes no target-finding or production
cryptanalytic claim. The graph is useful for controlling and linearizing a
route after an observable condition is met.

## Evidence

- Focused tests: 134 passed; 100% statement and branch coverage.
- Adjacent regressions: 277 passed across prior toy-LWE, FSGS, hybrid mesh, and
  topological-CFI surfaces.
- SymPy: exact limit `C`, zero residual for gap and inverse identities, and
  derivative `-C*h/(h+r)^2`.
- Loom signed-zero cross-check: 1,000/1,000 class/sign/order and 330/330
  equal-order L'Hopital cases; neutral `|0|` refused.
- Machine receipt:
  `docs/research/evidence/oriented_zero_hybrid_20260907_VALIDATION.json`.

No reportable vulnerability was found in the isolated module under its stated
trust boundary. OZ-HYB-004 remains an explicit blocker for production
authorization use.
