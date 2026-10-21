# Traceable spiral-staircase reasoning result

Date: 2026-10-21

## Verdict

The measured improvement is real for reversible token routing. A learned move,
a discrete lattice snap, and an exact inverse receipt completed every tested
out-and-back route through unseen depth 12 on all three seeds. The deep route
floor rose from 0.321 in the decoupled continuous model to 1.000 after lattice
snap. The earlier coupled model scored 0.172.

This result establishes a reusable execution mechanism for finite token states.
It does not establish open-domain reasoning quality. Language, code, and factual
reasoning need separate tasks that use the same mechanism and compare against
ordinary exact encodings.

## What was tested

- 64 exact states and eight reversible operations: add/subtract 1, add/subtract
  3, XOR 1, XOR 3, and six-bit rotate left/right.
- An OPEN sequence applies operations. CLOSE must apply their inverses in LIFO
  order and return to the starting state.
- Training depths were 1-4. Evaluation depths were 1-12, so depths 5-12 test
  extrapolation.
- Every arm used 60,020 parameters, 600 updates, and three seeds (11, 23, 37).
- A claim had to beat its paired control on every seed by more than two pooled
  standard deviations. Deep support also required an absolute score of at least
  0.90.

## The three repairs

| architecture | one-step accuracy | short route floor | deep route floor | deep full-route exact |
|---|---:|---:|---:|---:|
| coupled state and stack | n/a | 0.572 | 0.172 | 0.000 |
| decoupled state and stack | 1.000 | 0.861 | 0.321 | 0.027 |
| decoupled + lattice snap | 1.000 | 1.000 | **1.000** | **1.000** |

The first repair separated current-state motion from return-stack memory. That
made every one-step operation correct but left each result as a continuous
vector. Tiny off-codebook errors accumulated during repeated composition.

The second repair projected every learned proposal onto one of the 64 learned
token prototypes. If `z` is the current prototype, `a` is an operation, and
`f_theta` is the learned move, the model computes

`u = normalize(z + f_theta(z, a))`

and selects

`j* = argmax_j <u, p_j>`.

The forward state becomes exactly `p_j*`. Training uses a straight-through soft
projection so gradients still reach `f_theta`. One correct operation can
therefore be composed repeatedly without numerical state drift.

The receipt carries the exact inverse operation for each OPEN. CLOSE reads that
receipt in reverse order. This is the return address that gets the token stream
home after a long route.

## Controls and limits

| arm | one-step | short floor | deep floor | deep full route |
|---|---:|---:|---:|---:|
| aligned six-lane + receipt + phi | 1.000 | 1.000 | **1.000** | **1.000** |
| aligned six-lane, no receipt + phi | 0.999 | 0.995 | 0.061 | 0.021 |
| aligned six-lane, no receipt + uniform | 0.999 | 0.997 | 0.101 | 0.068 |
| aligned six-lane, no receipt + zero schedule | 1.000 | 0.987 | 0.097 | 0.054 |
| ordinary exact encoding + receipt + phi | 1.000 | 1.000 | **1.000** | **1.000** |
| shuffled lane identity + receipt + phi | 0.829 | 0.781 | 0.491 | 0.201 |

The exact receipt is essential to depth extrapolation. The no-receipt model can
look nearly perfect at seen depths while failing beyond them. This is the most
important control in the experiment.

The phi schedule did not improve neural stack memory. Uniform and zero schedules
were better on the no-receipt deep control, so phi remains a useful coordinate,
ledger, and rendering convention rather than a measured memory advantage here.

Ordinary exact bytes tied the aligned six-lane encoding on route accuracy. The
six tongues provide named, reversible evidence surfaces and provenance; this
task did not show an accuracy advantage over another exact encoding. Destroying
cross-lane identity with a shuffled codec cut the deep floor to 0.491, showing
that consistent identity matters even though the particular exact code did not.

The learned bit head averaged 0.807 byte exact on the aligned receipt arm while
prototype identity and route execution were perfect. Exact byte and tongue
faces should remain on the detached evidence rail; the route head should select
their conserved identity instead of reconstructing every bit from memory.

## Elastic rendered paths

The Venom/Flubber-style motion belongs between stable nodes. For an edge
`e=(i,j)`, use a bounded curve `q_e(s,t)` with fixed endpoints

`q_e(0,t)=p_i` and `q_e(1,t)=p_j`.

Its bend and stretch can carry the discarded proposal residual
`r = u - p_j*`, uncertainty, or correction energy. The edge may deform and
recoil; it may not rename either endpoint or erase the receipt. This keeps the
animation useful as an activation trace without allowing presentation geometry
to corrupt token identity. The current benchmark did not feed this residual
back into routing because the discrete route is already exact; feedback needs a
new controlled test.

## Fit with existing components

- `python/scbe/tangent_parallel.py` already reprojects continuous drift to a
  bounded line. Lattice snap is its finite token-state counterpart.
- `src/training/topological_loss.py` supplies Laplacian and torsion smoothness
  for an elastic path, but those terms should shape only the proposal or edge.
- `src/tokenizer/topology_view.py` can render the selected route and costs.
- `python/scbe/phdm_router.py` can propose a realm sequence. Its current
  no-repeat rule means the receipt controller, not PHDM, must execute nested
  returns.
- `src/tokenizer/topological_operator_tree.py` supplies deterministic operation
  signatures. They are routing evidence, not cryptographic authorization.
- `src/knowledge/tokenizer_graph/memory_chain.py` can retain receipt lineage.

## Integration rule

Use this first as a typed controller around Clay's model:

1. tokenize into exact byte/tongue identities;
2. let a learned head propose the next operation or tool;
3. snap the proposal to an allowed operation node;
4. execute it only through a typed, verified tool;
5. push its inverse receipt before entering another realm;
6. retain proposal residuals as an auditable sidecar;
7. pop receipts to return, then decode through the same bijection.

This gives Clay a traceable action path without asking a language-model weight
vector to preserve an exact call stack. After that controller is working, test a
language task where the model must open subproblems, use verified tools, close
them in order, and explain the route from the receipt chain.

## Evidence

- `artifacts/spiral_staircase_reasoning_20261021/RESULTS.json`
- `artifacts/spiral_staircase_sidecar_20261021/RESULTS.json`
- `artifacts/spiral_staircase_lattice_snap_20261021/RESULTS.json`
- `artifacts/spiral_staircase_lattice_snap_20261021/checkpoints/CHECKPOINT_MANIFEST.json`
- `artifacts/reasoning_staircase_20261021.xlsx`

The three winning checkpoints are stored as `safetensors`. Each was recreated
from the original seed and schedule, matched to the previously recorded model
state hash, loaded into a fresh model, and matched again.
