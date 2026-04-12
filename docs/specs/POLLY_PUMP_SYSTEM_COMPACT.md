# Polly Pump System Compact

Status: compact canonical working note  
Date: 2026-04-11  
Scope: tie the Polly Pump / pump packet / pump aquifer system back into the SCBE manifold, null-space, harmony, and escape-routing discussion.

## Purpose

The pump is not a separate magic subsystem. It is the orientation-and-routing front end for the rest of SCBE.

Its job is to:

1. sense an input before expression,
2. externalize routing state that a model would otherwise have to infer,
3. retrieve nearby semantic bundles from the aquifer,
4. stabilize the task before generation or dispatch,
5. verify outputs against the same orientation model after generation.

This is the practical bridge between:

- raw input,
- the 21D manifold / mixed geometry,
- null-space as structured absence,
- resonance / harmony,
- governance decisions,
- multi-model or multi-language routing.

## Minimal Pump Packet

From `docs/specs/BINARY_FIRST_TRAINING_STACK.md`:

```text
p(c) = [g(c), n(c), q(c), r(c)]
```

where:

- `g(c)` = six-tongue activation profile
- `n(c)` = null pattern / absence profile
- `q(c)` = governance posture
- `r(c)` = retrieval / routing hint

This is the smallest useful orientation pre-state.

## What The Pump Does In The Full System

The pump should be read as a control and routing surface, not just a classifier.

```text
input
  -> sense
  -> pump packet
  -> aquifer retrieval
  -> manifold placement
  -> route / stabilize / govern
  -> execute or generate
  -> re-sense output
  -> verify or quarantine
```

That makes the pump the first and last pass around any meaningful action.

## Tie-In To The Manifold

The manifold docs already define the mixed state space and product metric. The pump should not replace that. It should feed it.

Operationally:

- `g(c)` provides channel orientation.
- `n(c)` provides missing-support pressure.
- `q(c)` sets the governance lane.
- `r(c)` selects local retrieval and routing corridors.

These values should parameterize or condition the manifold placement step, not sit beside it as unrelated metadata.

Practical interpretation:

- tongue profile says which dimensions are hot,
- null profile says which dimensions are structurally absent,
- governance posture says how permissive the lane is,
- routing hint says where to look and which corridor to prefer.

## Tie-In To Null Space

Null space is not emptiness. It is structured absence.

In pump terms:

- high null pressure means the current input is under-supported in some channels,
- that absence is diagnostic,
- and it should affect both retrieval and risk.

The pump therefore turns absence into a usable signal before the main model reasons over the content.

This is why the null pattern belongs in the packet itself rather than being derived later as a side statistic.

## Tie-In To Harmony / Resonance

The resonance layer already separates geometry from wave alignment. The pump should be the upstream source of the semantic state that those alignment scores consume.

Working interpretation:

- geometry answers: where is this state?
- pump answers: what kind of state is this?
- resonance answers: does this state fit the surrounding field?

So the pump does not compute harmony by itself. It prepares the state needed to estimate relational harmony.

## Tie-In To Escape / Routing Pressure

The repo already has an escape model in the entropic layer. The pump is the right place to estimate whether a state is likely to move toward containment, corridor transfer, or escape pressure.

Working interpretation:

- `g(c)` influences which corridor or tongue lane is plausible,
- `n(c)` raises or lowers local support density,
- `q(c)` determines tolerance,
- `r(c)` selects retrieval neighbors and route candidates.

That means the pump can be used to estimate whether a state is:

- contained,
- near a corridor,
- thinly supported,
- or approaching escape conditions.

This is the practical place to connect pump state to manifold transfer ratio, effective escape bound, and corridor-angle alignment.

## Multi-Model And Multi-Language Use

The pump matters more when more than one model or language lane is active.

It provides:

- a shared orientation packet before dispatch,
- a way to route work to the best lane,
- a verification profile on the output,
- a way to detect cascade drift when the post-output packet no longer matches the expected route.

That is why the `FRONTIER_ORCHESTRATOR` note naturally extends the pump into a governance layer for model chains.

## Day-To-Day Role

In normal use, the pump should be the thing that keeps the system from having to rediscover its own context every time.

Daily effects:

- faster route selection,
- better bundle retrieval,
- less domain drift,
- stronger null-space diagnostics,
- more stable multi-model composition,
- cleaner fail-closed behavior.

## Current Repo State

Present in docs and handoff memory:

- pump packet contract,
- aquifer concept,
- multi-model orchestrator framing,
- handoff references to `src/polly_pump/`.

Not currently present in this working tree as live source:

- the referenced `src/polly_pump/packet.py`,
- `retriever.py`,
- `stabilizer.py`,
- `compiler.py`,
- `tests/test_polly_pump.py`.

So the compact conclusion is:

- the pump is a real architectural system,
- its role in the manifold stack is clear,
- but the current checkout preserves the contract more strongly than the direct implementation.

## Immediate Next Step

Use this note as the short source of truth when rebuilding or recovering the pump.

The first rebuild target should be:

1. `PumpPacket` schema,
2. bundle retriever contract,
3. stabilizer contract,
4. output re-sense / verification loop,
5. explicit hook into manifold placement and escape-risk estimation.
