# Dice Input Coding Systems

Generated: 2026-05-31

## Thesis

The idea is worth researching if it is framed precisely:

> A die is a typed finite-domain choice operator.

In this frame, "throwing dice into a coding system" is not vague randomness. It is a bounded input event:

```text
Die(name, sides, value, role, seed, constraints)
```

A normal die is `1d6`. A code die can be `1dN`, where `N` is exactly the number of legal choices at that point in the system.

Examples:

- `1d2`: choose boolean branch.
- `1d6`: choose one Sacred Tongue column.
- `1dK`: choose one legal compiler rewrite.
- `1dM`: choose one allowed tool call.
- `0`: no throw, null action, pass, or choose a different die family.

That makes the metaphor operational: dice become a reproducible choice trace for code generation, testing, routing, and agent workflows.

## Why This Is Real

This overlaps with established work:

- property-based testing generates many random inputs and shrinks failing cases;
- probabilistic programming represents random variables and finite distributions;
- discrete probabilistic programming systems such as Dice/noDice model finite choices and inference;
- program synthesis systems search over legal programs or grammar choices;
- LLM tool systems expose bounded tool choices and structured schemas.

The SCBE-specific angle is to make the random choice **auditable** and **typed**.

## Core Model

```json
{
  "schema_version": "scbe_dice_choice_v1",
  "die_id": "tool-route-001",
  "dimension": 1,
  "sides": 17,
  "value": 5,
  "side_label": "geoseal-compile",
  "role": "tool_choice",
  "seed": "sha256:...",
  "constraints": ["allowed_tool", "read_only"],
  "zero_policy": "no_throw|pass|reroll|different_die",
  "receipt_hash": "sha256:..."
}
```

Important distinction:

- `sides` is the legal option count.
- `value` is the selected side.
- `side_label` binds the side to a real operation.
- `seed` makes the throw reproducible.
- `constraints` prevent invalid moves.

## The 0 Question

The user's intuition is useful:

> 0 is not thrown or a different die is thrown.

There are four valid interpretations:

| Zero Meaning | Use |
| --- | --- |
| `no_throw` | No choice was made; deterministic path continued. |
| `pass` | Explicit skip action, like a board-game pass. |
| `reroll` | Invalid sampled value, try again under same domain. |
| `different_die` | Current domain is wrong; switch to a different option set. |

For SCBE, this should be explicit in the packet. Do not let `0` silently mean failure.

## How This Maps To Coding

### 1. Property-Based Testing

Dice generate input values.

```text
function under test + die stream -> generated cases -> failing case -> shrunk minimal case
```

This maps cleanly to Hypothesis and fast-check:

- finite domains: `sampled_from(...)` / constants;
- integer ranges: `integers(...)`;
- compound objects: strategy/composite generation;
- replay: seed and minimized counterexample.

SCBE value: store the die stream and shrink path as a receipt.

### 2. Cross-Language Compilation

Dice choose among legal translation moves.

```text
source AST node -> legal target rewrites -> throw 1dK -> apply selected rewrite -> run tests
```

If tests fail, the system can replay the choice stream and identify the bad throw.

This fits the reaction-state packet:

```text
source language -> transform dice -> target language -> recalculation -> classification
```

### 3. Tool Routing

Dice select tools only from allowed sides.

```text
intent -> allowed tool set -> 1dN -> selected tool -> execution receipt
```

This is useful for:

- randomized exploration;
- ensemble model routing;
- testing policy guards;
- avoiding deterministic local minima.

### 4. Agent Pathfinding

Dice select legal moves in a constructed space.

```text
state -> legal moves -> weighted die -> chosen move -> new state
```

Weights can come from:

- cost;
- risk;
- security clearance;
- confidence;
- route pressure;
- semantic gravity;
- novelty budget.

This ties directly to SCBE pathfinding, Rubix browser, and sparse search-space router lanes.

## Weighted Dice

Plain dice are uniform. Coding systems often need weighted dice:

```text
side 1: 50% choose safe direct rewrite
side 2: 25% choose alternative rewrite
side 3: 15% ask tool
side 4: 10% escalate
```

This is where dice become more like probability distributions. It overlaps with probabilistic programming, but the SCBE difference is that each throw is a receipt, not just a hidden sample.

## Relationship To OpenAI Tooling

OpenAI's Responses API supports stateful interactions, structured outputs, tool calls, file/web/computer tools, function calling, and MCP tools. That matters because a dice-choice system can be represented as structured output or a tool call:

```text
model proposes candidate choices
runtime validates legal sides
runtime rolls/selects side
tool executes selected side
receipt records the throw
```

This keeps the model from inventing invalid sides.

## Relationship To Research

Relevant research anchors:

- `TerpreT` treats program induction as random variables plus an interpreter connecting programs to observations.
- `Dice` and `noDice` focus on discrete probabilistic programs.
- `RefineStat` explores probabilistic program synthesis with syntactic and semantic validity checks.
- property-based testing research treats generation as controlled choice sequences and uses shrinking to reduce failures.

These all support the idea that finite choices are a serious computational object.

## SCBE Product Shape

Add a new lane:

```bash
scbe dice roll --sides 6 --seed demo --json
scbe dice route --choices tools.json --intent "compile this" --json
scbe dice replay --receipt dice-run.json --json
scbe dice bench --json
```

The benchmark should test:

1. deterministic replay from seed;
2. invalid side rejection;
3. zero-policy behavior;
4. weighted side distribution sanity;
5. route quality versus random baseline;
6. shrink/reduce failing path to minimal bad throw;
7. integration with reaction-state packets.

## Claim Boundary

Do not claim "dice make code intelligent."

Claim:

> SCBE can represent bounded code, tool, and agent choices as reproducible finite-domain dice packets with replayable receipts.

That is real, testable, and useful.

## Sources

- OpenAI Responses overview: https://developers.openai.com/api/reference/responses/overview
- OpenAI tools guide: https://developers.openai.com/api/docs/guides/tools
- fast-check docs: https://fast-check.dev/
- Hypothesis docs: https://hypothesis.readthedocs.io/
- noDice: https://arxiv.org/abs/2602.20049
- TerpreT: https://arxiv.org/abs/1608.04428
- RefineStat: https://arxiv.org/abs/2509.01082
- Test-case reduction via generation: https://drmaciver.github.io/papers/reduction-via-generation-preview.pdf
