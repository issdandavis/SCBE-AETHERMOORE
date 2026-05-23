# Semantic Atom Tokenizer

Status: implementation seed, not canonical replacement for SS1 transport.

The semantic atom tokenizer sits above SS1. SS1 remains byte-stable transport. This layer models meaning as explicit semantic atoms that can be embedded, related, refined, and ledgered.

## Core Rule

A semantic token is not just a string and not just a vector.

It is:

- a stable nucleus of invariants
- contextual orbitals by domain
- explicit bonds to other concepts
- domain isotopes
- code/workflow/physical relations
- a deterministic embedding vector
- lineage and refinement metadata

The vector is a projection. The relation tree remains explicit metadata so the system can audit why two meanings were placed near each other.

## Starter Atoms

The first implementation defines three atoms:

| Atom | Nucleus | Code Reading |
| --- | --- | --- |
| `FLOW` | directed movement through a medium, path, process, or system | control flow, data flow, event stream, pipeline |
| `WATER` | fluid material that flows, carries, dissolves, cools, erodes, and changes phase | stream, buffer, pipe, event bus |
| `BLOCK` | obstruction or constraint that prevents a flow from completing | exception, type error, failed test, policy denial |

These are intentionally small. They prove the structure before broad vocabulary expansion.

## Example

Input:

```text
Water can flow, but a failed test blocks deploy.
```

Semantic atom output:

```text
WATER -> FLOW -> BLOCK
```

Ledger output preserves:

- original input
- normalized input
- semantic ids
- bucket ids
- spans
- input hash

## Workflow Threads

Semantic atoms can also be rendered as modular workflow threads. This is the bridge from meaning tokens into board-play execution.

The first implementation emits:

- `nodes`: semantic atoms with bucket ids and domains
- `edges`: typed channels between atoms
- `braidedDomains`: all domains participating in the thread
- `stateRules`: rule text explaining how state may move across each edge
- `receipt`: input hash, token count, and edge count

Channel types:

| Channel | Meaning |
| --- | --- |
| `pipe` | bounded state movement that preserves payload identity |
| `funnel` | many inputs narrowing into one validation or dispatch point |
| `dot_to_dot` | explicit next-node progression |
| `websocket` | bidirectional session state across a handoff boundary |
| `agent_handoff` | authority transfer with source, target, task, and receipt |
| `bifurcation` | a flow splits under a rule; continuing, halted, and exiting lanes are ledgered |
| `merge` | split lanes realign only when state rules agree on shared invariants |

Example thread:

```text
Water enters the flow, then a type error blocks the pipeline.
```

Produces:

```text
WATER --pipe--> FLOW --bifurcation--> BLOCK --merge--> FLOW
```

This is the grounded version of braided long workflows, pipes/funnels, underpass/tunnel splits, websocket handoffs, and city-planning flow control. The metaphor is allowed only because the emitted object has explicit nodes, edges, state rules, and receipts.

## Atomic Analogy

The atom analogy is implemented as concrete fields:

| Analogy | Implementation |
| --- | --- |
| nucleus | `nucleus.meaning` and `nucleus.invariants` |
| electrons/orbitals | `orbitals[]` scoped by natural/code/workflow/physical/chemical/governance domains |
| bonds | `bonds[]` with relation kind, target, domain, and evidence |
| isotopes | `isotopes[]` for same core meaning in different domains |
| valence | `atomicProxy.valence` |
| reaction | future transformation rules between atoms |
| spectral line | deterministic embedding and bucket id |

## Boundary With SS1

Do not use this as transport encoding.

- SS1: reversible byte/tongue transport
- Semantic atom tokenizer: meaning object and relation graph
- Compiler/GeoBoard layer: legal moves, workflows, and execution receipts

The layers can connect, but they should not be collapsed.
