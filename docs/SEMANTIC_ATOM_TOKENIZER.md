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

| Atom        | Nucleus                                                                            | Code Reading                                                    |
| ----------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `FLOW`      | directed movement through a medium, path, process, or system                       | control flow, data flow, event stream, pipeline                 |
| `WATER`     | fluid material that flows, carries, dissolves, cools, erodes, and changes phase    | stream, buffer, pipe, event bus                                 |
| `BLOCK`     | obstruction or constraint that prevents a flow from completing                     | exception, type error, failed test, policy denial               |
| `TRANSFORM` | bounded operation that changes representation or state while preserving invariants | function, arithmetic operation, compiler pass, verified rewrite |

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

| Channel         | Meaning                                                                        |
| --------------- | ------------------------------------------------------------------------------ |
| `pipe`          | bounded state movement that preserves payload identity                         |
| `funnel`        | many inputs narrowing into one validation or dispatch point                    |
| `dot_to_dot`    | explicit next-node progression                                                 |
| `websocket`     | bidirectional session state across a handoff boundary                          |
| `agent_handoff` | authority transfer with source, target, task, and receipt                      |
| `bifurcation`   | a flow splits under a rule; continuing, halted, and exiting lanes are ledgered |
| `merge`         | split lanes realign only when state rules agree on shared invariants           |

Example thread:

```text
Water enters the flow, then a type error blocks the pipeline.
```

Produces:

```text
WATER --pipe--> FLOW --bifurcation--> BLOCK --merge--> FLOW
```

This is the grounded version of braided long workflows, pipes/funnels, underpass/tunnel splits, websocket handoffs, and city-planning flow control. The metaphor is allowed only because the emitted object has explicit nodes, edges, state rules, and receipts.

## Cross-Language Code Bridge

`src/tokenizer/semantic_code_bridge.py` connects the semantic atom layer to the existing code-weight packet system.

Current proof:

- Python, TypeScript, Rust, and C implementations of the same `add(a, b)` function produce the same `interchange_key`.
- Each language still keeps its own source hash, lexical tokens, transport tongue, and transport token hash.
- The shared operation path maps into semantic atoms:

```text
function_definition/2 -> return_flow -> arithmetic:add/2
FLOW -> FLOW -> TRANSFORM
```

This proves semantic realignment across language-specific syntax while preserving source-specific packets.

## Aperiodic Token Realignment

Aperiodic token realignment is a governance pass over token boundaries and semantic weights. It lets the substrate move without becoming noise.

Definition:

```text
T_n = Align(BaseTokenize(x), phase_n, drift_n, pressure_n)
```

Where:

- `BaseTokenize(x)` is SS1, byte/subword, or another tokenizer surface.
- `phase_n` is a deterministic phase offset derived from logged context, not an unrecorded random value.
- `drift_n` is the detected semantic or structural deviation.
- `pressure_n` is the governance pressure from the harmonic wall, route checks, or quarantine rules.
- `T_n` is the realigned token stream with receipts.

The point is not to make the tokenizer unpredictable to the verifier. The point is to make it non-locking to an attacker while remaining reproducible to the ledger.

Checks before re-alignment:

| Check                  | Meaning                                                           | Possible action                                |
| ---------------------- | ----------------------------------------------------------------- | ---------------------------------------------- |
| boundary instability   | suspicious or lossy token splits                                  | split, merge, or route through byte transport  |
| semantic drift         | meaning diverges from prior context or declared task              | re-weight atoms, add review edge, quarantine   |
| attack rhythm          | repeated prompt-injection cadence or exploitable phrase structure | rotate tongue mapping or isolate span          |
| entropy anomaly        | stream is too structured or too chaotic for the claimed surface   | lower trust, preserve raw bytes, add receipt   |
| tongue mismatch        | token stream routes to the wrong symbolic chamber                 | remap chamber or force source-language packet  |
| binary/hexa loss check | encoded view cannot reconstruct the source bytes or operation     | deny transform, keep source packet, quarantine |

Data-loss rule: every realignment must carry the original bytes, source token spans, semantic atoms, emitted form, hashes, and a loss classification. Binary and hexadecimal compiler lanes are useful only as proof surfaces if they preserve this receipt chain.

Current boundary:

- This is not yet a full source-code compiler.
- It does not yet generate target-language code.
- It does not yet prove arbitrary Turing-complete equivalence.
- It proves the bridge layer: language-specific packets can bifurcate, align on a shared semantic operation signature, and preserve enough source evidence for verification.

## Atomic Analogy

The atom analogy is implemented as concrete fields:

| Analogy            | Implementation                                                                    |
| ------------------ | --------------------------------------------------------------------------------- |
| nucleus            | `nucleus.meaning` and `nucleus.invariants`                                        |
| electrons/orbitals | `orbitals[]` scoped by natural/code/workflow/physical/chemical/governance domains |
| bonds              | `bonds[]` with relation kind, target, domain, and evidence                        |
| isotopes           | `isotopes[]` for same core meaning in different domains                           |
| valence            | `atomicProxy.valence`                                                             |
| reaction           | future transformation rules between atoms                                         |
| spectral line      | deterministic embedding and bucket id                                             |

## Boundary With SS1

Do not use this as transport encoding.

- SS1: reversible byte/tongue transport
- Semantic atom tokenizer: meaning object and relation graph
- Compiler/GeoBoard layer: legal moves, workflows, and execution receipts

The layers can connect, but they should not be collapsed.
