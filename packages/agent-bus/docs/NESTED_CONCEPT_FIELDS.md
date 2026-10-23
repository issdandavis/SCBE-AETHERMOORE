# Nested concept fields

Status: **implemented mechanism; no model-quality claim**

This layer indexes the existing public reasoning-artifact DAG into overlapping
concept bubbles and nested topic fields. It gives an agent a deterministic way
to find, follow, backtrack, and replay source-backed routes without presenting
generated prose as the model's private chain of thought.

## System map

```text
canonical bytes / source records
        |
        v
reasoning-artifact DAG
  - immutable public summaries
  - evidence and provenance hashes
  - six reversible tongue views
  - fork / merge / backtrack receipts
        |
        | exact artifact ids + verified DAG hash
        v
concept-field sidecar
  - overlapping concept bubbles (hyperedges)
  - nested topic fields (hierarchy)
  - typed directed relations
  - source / verified / hypothesis / rejected status
        |
        | goal + constraints
        v
deterministic bounded route planner
  - typed-edge or bubble hops
  - policy and evidence gates
  - stable tie breaking
        |
        v
public route receipt
  - parent, goal, source, evidence, alternatives boundary
  - hash chain per hop
  - replay verification
        |
        v
model prompt, deterministic solver, tool call, or evaluator
```

The sidecar does not alter model weights. A later learned binder may consume its
records before transformer block M0, but that is a separate controlled
experiment.

## Why this shape

- **Tree of Thoughts** supports explicit search, evaluation, and backtracking
  over coherent intermediate units.
- **Graph of Thoughts** permits dependencies, joins, and reuse that a single
  chain or tree cannot express.
- **GraphRAG** supports hierarchical communities for corpus-level navigation.
- **Relational GCNs** show why relation types should remain distinct instead of
  being reduced to one similarity score.
- **Concept bottleneck models** motivate human-readable concepts that can be
  inspected and intervened on.
- Faithfulness research shows that fluent chain-of-thought text need not be the
  cause of an answer. This implementation therefore records public state
  transitions and verifies a deterministic route; it does not call them private
  thoughts.

Primary sources are listed at the end of this document.

## Reused components

- `reasoning-artifact-graph.ts` remains the source of identity, provenance,
  branch history, policy, and reversible tongue checks.
- The six tongues remain exact transport/index views. Six encodings of one byte
  do not become six independent pieces of semantic evidence.
- Existing graph telemetry remains descriptive. Similar geometry cannot
  authorize a semantic merge.
- Existing deep-route experiments supply the local evidence boundary: receipts
  improved deep return; phi schedules and tokenizer-specific staircase routing
  did not separate from controls.

## New schema

### Concept bubble

A bubble is an overlapping hyperedge. It binds one named concept to one or more
artifact ids. Each membership has a weight, authority, evidence status, and
receipt hashes. One artifact may belong to several bubbles.

Membership authority and evidence status are separate. For example, a
deterministic keyword rule can be perfectly reproducible while remaining only a
heuristic interpretation.

### Topic field

A topic field groups bubbles and may be nested under another field. Fields are
acyclic. A bubble may appear in several fields, so the hierarchy narrows search
without asserting that concepts have only one home.

### Typed edge

Edges use one of these relations:

`supports`, `contradicts`, `requires`, `explains`, `enables`, `returns_to`,
`elaborates`, `transitions`, or `same_source`.

The route planner keeps relation identity. Goal-specific costs may prefer one
relation without deleting the others.

### Public route

A route starts from one or more explicit anchors and ends at an artifact, bubble,
or topic field. Every hop records its relation, source, evidence, cost, previous
receipt hash, and receipt hash. Replanning the same saved goal against the same
two graph hashes must reproduce the same route.

## Routing math

For explicit edge `e`, goal `g`, and relation `r(e)`, the traversal cost is

```text
c_g(e) = c(e) * m_g(r(e))
```

where `c(e) > 0` is the edge cost and `m_g(r) > 0` is an optional
goal-conditioned multiplier. Bubble traversal has its own declared positive
cost. Dijkstra search uses a lexical path signature to break equal-cost ties,
so replay does not depend on object insertion order.

The receipt chain is

```text
h_0 = H(goal || reasoning_graph_hash || concept_graph_hash)
h_i = H(h_(i-1) || hop_i)
```

The hash proves that a saved route changed. It does not prove the route's claims
are true. Truth authority remains on source or verifier receipts.

## Invariants and refusal rules

- Every artifact reference must exist in the bound reasoning-artifact DAG.
- Every bubble and field parent relation must be acyclic.
- A route cannot traverse a rejected relation.
- A source/verified-only route cannot traverse hypothesis memberships or edges.
- Denied, quarantined, or adversarial artifacts are excluded unless the goal
  explicitly admits their policy class.
- Similarity, common bubble membership, phi position, and reversible codec
  agreement cannot authorize a semantic merge.
- Search is bounded by hop and expansion limits.
- A failed search returns a stable `E_NO_ROUTE` result rather than inventing a
  bridge.

## Experiment gate

The mechanism tests prove schema validation, deterministic replay, overlap,
goal-conditioned route changes, hypothesis filtering, and tamper detection.
They do not prove improved reasoning.

A learned Clay claim requires:

1. independent source groups for train and holdout;
2. no-intervention and flat-retrieval baselines;
3. an equal-width untyped graph control;
4. a degree-preserving shuffled-relation control;
5. at least three seeds;
6. improvement over both baseline and matched controls by more than twice the
   pooled seed standard deviation;
7. causal deletion tests showing that removing a claimed supporting route
   changes the corresponding output or decision;
8. ordinary reading, coding, arithmetic, and conversation retention panels.

## Sources

- Besta et al., [Graph of Thoughts](https://arxiv.org/abs/2308.09687).
- Yao et al., [Tree of Thoughts](https://arxiv.org/abs/2305.10601).
- Edge et al., [From Local to Global: A Graph RAG Approach to Query-Focused Summarization](https://arxiv.org/abs/2404.16130).
- Schlichtkrull et al., [Modeling Relational Data with Graph Convolutional Networks](https://arxiv.org/abs/1703.06103).
- Koh et al., [Concept Bottleneck Models](https://proceedings.mlr.press/v119/koh20a.html).
- Lyu et al., [Faithful Chain-of-Thought Reasoning](https://aclanthology.org/2023.ijcnlp-main.20/).
- Paul et al., [Making Reasoning Matter](https://aclanthology.org/2024.findings-emnlp.882/).
