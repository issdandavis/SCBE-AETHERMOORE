# SCBE mathematical contracts in Lean

This project formalizes selected SCBE formulas and the contracts between encoding,
geometric scoring, directed routing, decisions and reference-state admission.
It extends the repository's existing system map; it does not replace the runtime.

The September 19, 2026 proof pass contains **85 Lean theorems** (38 added to the
previous 47). The build and axiom
audit are reproducible with `verify.py`. Formal results apply to the definitions
and hypotheses written in these files. Python correspondence is a separate,
bounded executable audit. No theorem establishes complete system security,
post-quantum hardness, patent scope, or correctness of every runtime profile.

The latest saved check is [evidence/proof-extension-20260919.json](evidence/proof-extension-20260919.json).
The [September 19 proof guide](PROOF_GUIDE_20260919.md) maps the new statements,
assumptions, runtime correspondence and remaining obligations.
The earlier 47-theorem check is [evidence/proof-portable-20260918.json](evidence/proof-portable-20260918.json).
The earlier receipt preserves the proof before cross-platform vocabulary-hash
normalization; the theorem statements are unchanged.

## What is proved

| File | Checked properties | Required assumptions |
|---|---|---|
| `SCBE/Geometry.lean` | Positive phi weights; positive weighted quadratic energy away from zero; bounded positive safety score; decreasing safety with increasing distance/phase; increasing evidence risk; positive Poincare denominator and acosh argument at least one; symmetry and diagonal argument | Exact real arithmetic; nonnegative distance/phase; positive weights; coordinates strictly inside the unit ball where required |
| `SCBE/Harmonic.lean` | `R^(d^2) >= 1`; monotonicity and strict monotonicity in nonnegative distance; cost and safety have opposite orders | `R >= 1`, or `R > 1` for strictness |
| `SCBE/Routing.lean` | Accepted transitions use directed policy edges and known endpoints; every executed edge is legal; executed transition count is bounded by fuel; a symmetric gate cannot distinguish a one-way edge from its reverse | A supplied, immutable policy; the policy's accuracy is outside this proof |
| `SCBE/Composition.lean` | Decision composition preserves both restrictions; associativity and commutativity; an aggregate allows only when every check allows; a fourteen-result specialization; rejected candidates do not update the reference; an authorized step requires a legal edge and all checks allowing | All mandatory checks reach the aggregator and all execution uses the guarded step |
| `SCBE/Codecs.lean` | Byte-sequence round trip; cross-tongue translation composition and reversal; symbol-count preservation | Each valid tongue vocabulary is equivalent to `Fin 256` |
| `SCBE/Vocabulary.lean` | The exported fixture has six tables, each with 256 entries | Fixture matches the named Python source; checked separately by the exporter |
| `SCBE/NestedRegions.lean` | Exact refinement containment; strictly decreasing width; half-open seams; coordinate inversion/rebasing; normalized weighted embedding with squared norm at most 9/16 | Positive rational width; valid subdivision; normalized nonnegative weights; bounded local coordinates |
| `SCBE/RestrictedExecution.lean` | Restricted quarantine progress; unscoped refusal; control identity; directed-route and host-check requirements | DCP inspection profile; trusted evidence and scope classification; pure total handler model |
| `SCBE/InterfaceConnections.lean` | Policy, path, execution and dispatch preserved across bijections; six-tongue specialization; chunk composition and no sequence alias | Full policy transported with the same equivalence; valid vocabulary lists |

`Codecs.lean` supports a different token type for each tongue. Its equivalences
apply to valid vocabulary members, not arbitrary text. The concrete Python table
uniqueness and decoder agreement are checked exhaustively for all 256 bytes in
each tongue by `audit_implementation.py`; they are not smuggled into Lean as axioms.
The general sequence proof is in Lean, while the Python-table connection is tested.

The Poincare theorems cover the algebraic argument passed to `acosh`. They do not
prove the full metric's triangle inequality, boundary clamping, or floating-point
error bounds. Likewise, the fourteen-result theorem is a composition law: the
actual fourteen layers do not each emit a `Decision`. Adapters must turn required
evidence into check results before that theorem can apply.

## Reproduce

Install the pinned Lean toolchain using the [official Lean installation guide](https://lean-lang.org/install/manual/).
From `formal/lean`, with `lean` and `lake` available:

```sh
lake update
lake exe cache get Mathlib.Data.Real.Sqrt Mathlib.Algebra.BigOperators.Group.Finset.Basic Mathlib.Tactic.Linarith Mathlib.Tactic.Positivity Mathlib.Tactic.Ring Mathlib.Tactic.FieldSimp Mathlib.Data.List.Basic Mathlib.Logic.Equiv.List Mathlib.Analysis.SpecialFunctions.Pow.Real
python -X utf8 verify.py --output validation.json
```

The toolchain is Lean 4.19.0. `lake-manifest.json` pins Mathlib to
`c44e0c8ee63ca166450922a373c7409c5d26b00b` and pins its transitive dependencies.
No runtime Python/TypeScript dependency is added by this project. For a first
setup that should avoid fetching the entire Mathlib cache, set
`MATHLIB_NO_CACHE_ON_UPDATE=1` before `lake update`, then use the selective command
above. Limit `LEAN_NUM_THREADS=2` on a machine running training.

`verify.py` performs a build, enumerates every named theorem in this project,
audits its transitive axiom dependencies, hashes the sources and dependency pins,
and requires seven false fixtures to be rejected. It first proves the negation
of each fixture. They cover reversed edges, weakened refusals, the valid origin
score, overlapping seams, admission by rebasing and quarantine scope/promotion.
It refuses unfinished proofs, native decision shortcuts and custom axioms. Only
the standard `propext`, `Classical.choice` and `Quot.sound` dependencies are allowed.
This trust boundary follows [Lean's axiom documentation](https://lean-lang.org/doc/reference/latest/Axioms/).

Receipts are immutable: choose a new output filename for another validation.
The included GitHub workflow runs the formal check only. It does not claim that
Python correspondence passes merely because Lean builds.

For the implementation audit, use the repository's existing Python environment
with NumPy:

```sh
python -X utf8 export_vocabulary.py --check
python -X utf8 audit_implementation.py --repo ../.. --output /path/to/new-audit.json
```

The audit imports exact files from the supplied repository and records their
SHA-256 hashes. It exits nonzero on a failed contract or claim probe. Geometry
samples remain away from clamping, so they do not conceal the exact-real versus
floating-point boundary. The CFI audit enumerates all 64 loop-free directed graphs
on three vertices and checks 25 endpoint pairs in each, plus four state/type/path
checks. The full-system audit uses explicit L13 fixtures to isolate the wrapper;
it is not an end-to-end detector-accuracy experiment.

The vocabulary export uses a normalized-LF source hash so Windows and Linux
checkouts produce the same Lean fixture. The implementation receipts retain raw
file hashes for the deployed files. Scoped Git attributes keep proof sources and
their dependency pins at LF line endings.

## September 18 source review (before repair)

GitHub `main` was inspected at `91987c938c566bd6ced718a07c70fa7a62da6663`.
Its newest main-branch maintenance runs passed; dependency PR #2855 was mergeable
with passing checks. Clay had no open PRs. The recent repository-health and
Hugging Face sync issues were automated reports, not reproduced runtime failures.

A separate local SCBE worktree had uncommitted September repairs. Its HEAD alone
does not identify those repairs; the audit receipt's file hashes do. Results:

| Audit group | Published main | Local repaired sources |
|---|---|---|
| Six vocabularies: 10,758 byte/translation/empty-sequence cases | PASS | PASS |
| L12 formula: 35 finite samples | PASS | PASS |
| L12 invalid-domain rejection | FAIL: accepts NaN | PASS: 5 cases |
| L5 interior geometry: 192 checks | PASS | PASS |
| Frozen directed CFI | FAIL: accepts a nonedge even in an edgeless graph | PASS: 1,604 checks |
| Full-system refusal precedence | FAIL: REVIEW becomes ALLOW | PASS: 32 checks |
| L6 header's general isometry claim | FALSE | FALSE |

The L6 counterexample uses `u=(0,0)`, `v=(0.25,0)` and `t=15` with default
parameters. Distance changes from `0.510825623766` to `1.27706405941`.
The same implementation later acknowledges that breathing is a deformation.
The isometry statement in its header therefore must not be used as a theorem.
The initial oscillation could cross zero and lose invertibility. That was an
observed defect, not a valid theorem. The subsequent repair in this branch uses
positive bounded breathing, an inverse and explicit derivative/domain tests;
the historical counterexample above is retained for traceability.

The reviewed CFI, decision and reference-admission fixes are now included in this
branch. `audit_implementation.py` now tests the declared positive-deformation
contract, rather than demanding the false general-isometry claim. See
[the security assessment](../../docs/security/NIST_READINESS.md) for runtime tests,
crypto boundaries and unresolved deployment obligations. The current audit
receipt is separate from the pre-repair source review.

## Patent connection and next proof obligations

The local patent work package and its September 15 Lean plan distinguish exact
directed-edge enforcement from geometric approximations. This formalization
follows that boundary. The public draft's quadratic-exponential cost and the
current formula registry's bounded safety score are proved separately. They have
opposite monotonic directions and incompatible ranges; the bounded score cannot
ever exceed the legacy `100` threshold.

No authenticated submitted Claims document was available in the inspected
sources. This is an engineering-property map, not a numbered-claim coverage
analysis. The owner's private patent records and review receipts remain outside
this repository. See [SYSTEM_MAP.md](SYSTEM_MAP.md) for every layer and its boundary.

Next obligations, in dependency order:

1. Establish the directed-policy extraction and deployment chain; enforce the
   actual edge gate on every action and instrumented control-flow transition.
2. Bind capabilities to principal, resource, action, context, expiry and replay
   state. A legal CFG edge alone does not establish authorization for a tool.
3. Formalize the radial embedding and permitted phase transformations. Specify
   how breathing deforms distances and restrict its singular parameter cases.
4. Prove numeric refinement with explicit tolerances, finite-value handling and
   dimension checks, then connect each named TS/Python profile independently.
5. Prove concrete table decoding from the exported vocabulary, eliminating the
   current tested correspondence boundary for the six codec equivalences.
6. Model reference averaging, cache invalidation, state recovery and concurrency;
   the current admission theorem covers only the final decision gate.

Training gains, attack detection rates, latency, Lyapunov stability and
cryptographic indistinguishability require their own evidence and are not
consequences of these 85 theorems.
