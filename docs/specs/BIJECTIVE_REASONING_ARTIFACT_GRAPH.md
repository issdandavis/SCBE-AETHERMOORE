# Bijective Reasoning Artifact Graph

**Status:** implemented and locally tested in `packages/agent-bus`; model-use and
training benefit remain unmeasured.

This specification connects existing SCBE components without treating every old
experiment as one finished system. It records inspectable reasoning artifacts:
public summaries, state transitions, syntax changes, evidence, policy, and
telemetry. It does not request, expose, or persist a model's private
chain-of-thought.

## Plain-language crosswalk

| Design phrase             | Executable meaning                                                              |
| ------------------------- | ------------------------------------------------------------------------------- |
| thinking lines            | typed public branch artifacts and state transitions                             |
| sung in different tongues | reversible views of one canonical byte sequence                                 |
| parallel paths            | immutable DAG forks with explicit parent IDs                                    |
| geometry interacting      | measured routing/coupling features; never truth authority                       |
| tubal tensor              | branch x feature x time array with a mode-3 Fourier view                        |
| convergence               | measured head distance and centroid residual                                    |
| backtracking              | a new hash-chained event that moves the active head to an ancestor              |
| syntax changed            | deterministic token delta against every parent                                  |
| global telemetry          | graph depth, policy holds, spectral energy, phase coherence, and rollback count |

## Claim-to-code map

| Need                         | Existing implementation                                        | Evidence state                                                | Missing part addressed here                                   |
| ---------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------- |
| Long workflows               | `packages/agent-bus/src/reaction-chain.ts`                     | implemented; existing tests pass                              | Artifact-level lineage and immutable rollback                 |
| Parallel search              | `packages/agent-bus/src/search-space-router.ts`                | implemented; title-normalized merge is routing convenience    | Canonical/equivalence merge gate                              |
| Reversible tongue transport  | `src/tokenizer/ss1.ts`                                         | all 256 bytes round-trip in KO/AV/RU/CA/UM/DR in the new test | Dependency-injected package adapter and per-node verification |
| Exact two-sided seam         | `src/agentic/meet_in_the_middle.py`                            | implemented; selected Python tests pass                       | General many-branch event graph                               |
| Governed execution           | Agent Bus pipeline and GeoSeal surfaces                        | implemented in several runtime profiles                       | External receipt hook for typed/executable equivalence        |
| Tube/relation representation | `C:\dev\loom\loom_multiplex.py`, ripple and tensor experiments | partial and experimental; not one canonical tensor API        | Small, explicit branch-feature-time telemetry calculation     |
| Backtracking and audit       | handoff receipts, task ledger, vector navigation receipts      | implemented in separate workflows                             | One artifact graph with replay-verifiable heads               |

The local inventory receipt for this build is
`artifacts/bijective_reasoning_graph_inventory_20260906.json`. It is generated
evidence and is not a package source file.

## Runtime boundary

```text
canonical public artifact bytes
        |
        +-- injected byte-exact tongue codec --> encoded KO/AV/RU/CA/UM/DR view
        |
        +-- public summary + state transition + syntax tokens
        |
        +-- evidence/provenance SHA-256 + policy disposition
        v
immutable artifact node --> append/fork/merge/backtrack event hash chain
        |
        +-- exact canonical equality -------------------------+
        |                                                     |
        +-- externally verified typed/executable receipt -----+--> allowed merge
        |
        +-- geometry or similarity alone --------------------------> blocked merge
        v
branch x feature x time telemetry for routing, diagnosis, and later experiments
```

Every derived tongue view must decode to the original canonical bytes. A view is
a representation of one value, not independent evidence. Evidence and
provenance enter through separate hash fields.

## Merge authority

An exact merge requires all parent nodes and the output node to have the same
canonical byte hash. This covers several tongue views of one artifact.

A non-exact merge requires a typed equivalence receipt bound to:

- every parent canonical hash;
- the output canonical hash;
- the verifier source hash;
- an external evidence hash; and
- a caller-supplied verifier that accepts the receipt.

The graph retains that receipt and its hash. This is the extension point for an
executed compiler equivalence check, GeoSeal policy decision, proof checker, or
another deterministic judge. Similar vectors, close geometry, high confidence,
or matching prose do not authorize a merge.

The event hash chain detects changes relative to a trusted retained head. It is
not a digital signature and does not authenticate an attacker who can replace
the entire graph and its trust anchor. Signed GeoSeal receipts belong outside
this module.

## Tube telemetry

For active heads, public feature trajectories form

`X in R^(B x F x T)`

where `B` is branch count, `F` is the declared feature schema, and `T` is the
longest primary-parent trajectory. A shorter branch holds its final state for
alignment. The implementation applies a unitary-scaled discrete Fourier
transform along the third mode:

`X_hat[b,f,k] = (1/sqrt(T)) * sum_t X[b,f,t] * exp(-i*2*pi*k*t/T)`

It reports:

- pairwise Euclidean distance between current branch heads;
- mean separation and mean residual from the head centroid;
- `convergence_degree = 1 / (1 + mean_separation)`;
- mode energy, non-DC energy, and high-frequency fraction;
- phase coherence across branch-feature tubes;
- branch depths, policy counts, unresolved heads, and backtrack count.

This is mode-3 spectral telemetry. No standard t-product, block-circulant
operator, tensor singular-value decomposition, or tubal-rank implementation was
found under those names in the scoped repositories. Calling this a t-SVD system
would overstate the implementation. An older implementation may exist under
another name or in an unavailable archive; its status is `UNKNOWN` until found
and tested.

## Policy states

The graph records `allow`, `deny`, `quarantine`, and `adversarial` as artifact
dispositions. Any non-allow parent blocks a merge. These are branch-level ledger
states and do not replace the canonical SCBE Layer 13 runtime profile, whose
exact labels and formulas must remain governed by the formula registry.

## Quantum-inspired counterfactual curriculum

Fiction can be useful as a constrained world-model exercise:

1. Convert a premise into typed assumptions, entities, units, and equations.
2. Separate established physical law, a declared fictional law, and an unknown.
3. Fork alternative worlds by changing one receipted assumption at a time.
4. Simulate or prove consequences where an executable judge exists.
5. Mark a branch unstable when it violates its declared invariants.
6. Produce a public explanation linked to the violated rule and evidence.

Complex amplitudes, interference, tensor networks, quantum walks, and
superposition-like branch mixtures can be simulated classically. That makes the
curriculum **quantum-inspired**, not a quantum computer or quantum security
primitive. Quantum mechanics itself is not vague or inherently unstable;
unitary evolution is precise and measurement outcomes are probabilistic.
Cryptographic authorization remains external and conventional unless a real,
identified post-quantum primitive is used.

## Evidence and limits from this audit

### Implementation guarantees

- Artifact and event bodies are deterministically SHA-256 hashed.
- Existing nodes are never deleted by backtracking.
- Appending to historical state requires an explicit fork or backtrack.
- Codec use is rejected if decoding changes any canonical byte.
- Policy-held branches cannot merge.
- Geometry-only non-exact merges are rejected.
- Typed equivalence requires an external verifier at merge time.
- Node, event, active-head, encoded-view, and mode-3 DFT work are explicitly
  bounded; longer histories must be sealed into linked segments.

### Measured locally

- New reasoning graph tests: 18 passed.
- Complete Agent Bus package suite: 719 passed across 27 files.
- Python tokenizer/meet-in-the-middle/GeoSeal selected suite: 29 passed.
- Canonical TypeScript SS1 check: 1,536 byte-token round trips
  (`256 bytes x 6 tongues`) passed.

The separate dirty `C:\dev\loom` worktree produced 13 passes and one stale
expectation failure: current experimental code reports 30 relation nodes while
`test_loom_multiplex.py` still expects 16. This branch was not changed here.

### Design hypotheses

- Feeding tube telemetry to a model may improve branch allocation,
  disagreement detection, or rollback decisions.
- Equation-constrained fiction may improve counterfactual transfer.
- Sacred Tongue views may help routing or error localization beyond their exact
  transport role.

None of those learning claims is proven by structural round trips.

## Required learning experiment

Any promotion into model training needs at least three seeds and all of these
comparisons:

1. no-intervention baseline;
2. equal-width ordinary feature baseline;
3. one-to-one shuffled binding between canonical items and tongue/tube views;
4. feature-family ablations;
5. held-out tasks requiring rollback and cross-branch reconciliation;
6. evaluator validation with deliberately wrong artifacts; and
7. an effect larger than twice pooled standard deviation.

The test must score task success, unsafe merge rate, provenance accuracy,
rollback recovery, compute cost, and latency. A successful byte round trip or a
lower geometric residual alone is not a reasoning gain.

## Known integration gaps

- The graph is a library surface; ReactionChain and the CLI do not yet emit its
  nodes automatically.
- Python and TypeScript Sacred Tongue profiles must carry an explicit mapping
  authority when mixed; passing tests within each profile do not establish that
  every historical vocabulary is byte-identical across implementations.
- The 18 code-language Loom map includes authored support faces. Runtime
  execution proof remains language-specific.
- Persisted equivalence receipts need a concrete signed GeoSeal or executable
  verifier adapter before non-exact production merges.
- Private model cognition is unavailable and unnecessary. The harness can audit
  only explicit artifacts, state transitions, tool outcomes, and receipts.
