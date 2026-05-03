# Agentic Layer Runner Roadmap

Generated: 2026-05-02

Purpose: define the best near-term path for turning SCBE-AETHERMOORE into a layer-by-layer agentic coding and training system without adding unnecessary framework weight.

## Core Decision

Build **layer runners**, not permanent layer agents.

A runner is a small executable contract for one layer or lane. It may call an AI model, a local tool, a test, a tokenizer, a benchmark, or a handoff packet. The system should activate runners only when the packet requires them.

This keeps token use low and makes every handoff auditable.

## Why This Fits The Current Repo

The repo already has the load-bearing pieces:

| Existing piece | Use in layer-runner system |
|---|---|
| Bijective tokenizer and code packets | Exact input/output transport and round-trip proof. |
| GeoSeal CLI | User-facing route surface for packets, harnesses, history, replay, and tests. |
| `src/agent_comms/` | Packet, pair, provider, graph-runner, secure handoff, and ledger primitives. |
| Harness terminal | Provider matrix, lane switching, analog actions, and research benchmark families. |
| Stage 5 and Stage 6 gates | Training promotion and constrained generation gates. |
| Post-gate digestion | Compact residue chains after training/eval runs. |
| Research roadmap index | Converts research captures into testable implementation lanes. |

## External Research Signal

Useful patterns to absorb:

- Claude Code subagents: specialized workers with isolated context, tool restrictions, permissions, hooks, and optional memory.
- Claude Code hooks: lifecycle gates around prompts, tools, subagents, compaction, file changes, and session boundaries.
- LangGraph supervisor: handoff tools and supervisor routing are useful, but state and handoff messages must stay explicit.
- AlphaEvolve: the real gain is not "many agents"; it is candidate generation plus automated evaluators and iterative improvement.

What to reject:

- Roleplay-heavy agent teams without strict packet contracts.
- A 14-agent always-on fleet.
- Blind framework adoption that duplicates GeoSeal, packet graph runner, or existing harness providers.
- Research captures that never become tests.

## Target Architecture

```text
User goal
  -> intent packet
  -> bijective tokenizer/code-packet
  -> layer runner registry
  -> selected layer runners
  -> handoff receipts
  -> tests/evals
  -> integration gate
  -> deploy test
  -> release/promotion
```

Each runner has:

- `runner_id`
- `layer_id`
- `lane`
- `purpose`
- `input_schema`
- `output_schema`
- `allowed_tools`
- `required_signal`
- `required_tests`
- `promotion_gate`
- `receipt_fields`

## Layer Runner Contract

Minimal JSON shape:

```json
{
  "schema_version": "scbe_layer_runner_spec_v1",
  "runner_id": "layer06-stage6-gate",
  "layer_id": "L06",
  "lane": "coding_generation_gate",
  "purpose": "Validate generated code output before commit or training promotion.",
  "input_schema": "scbe_code_packet_v1",
  "output_schema": "scbe_layer_receipt_v1",
  "allowed_tools": ["read", "execute_tests"],
  "required_signal": "layer-hop:L05->L06:gate",
  "required_tests": [
    "python -m pytest tests/test_stage6_constrained_decoding.py -q"
  ],
  "promotion_gate": {
    "must_pass": true,
    "requires_receipt": true
  },
  "receipt_fields": [
    "packet_sha256",
    "source_sha256",
    "runner_id",
    "layer_id",
    "gate_passed",
    "evidence_path"
  ]
}
```

## First Build Slice

Build this in the smallest useful order.

### 1. Registry

Add:

```text
config/layer_runners/layer_runner_registry.json
```

Start with 5 runners, not 14:

| Runner | Why first |
|---|---|
| `L01-intent-packet` | Turns ambiguous user commands into an actionable packet. |
| `L03-bijective-code-packet` | Proves exact source/token round-trip. |
| `L06-stage6-gate` | Uses the existing constrained generation work. |
| `L10-geoseal-handoff` | Seals handoff packets and provider-pair signals. |
| `L14-eval-digest` | Converts run logs into residue and next-lane decisions. |

### 2. CLI Surface

Add GeoSeal commands:

```text
geoseal layer-run --runner L06-stage6-gate --packet packet.json --json
geoseal layer-chain --from L01 --to L14 --packet packet.json --json
geoseal layer-registry --json
```

Do this by extending `src/geoseal_cli.py`, not by creating a separate CLI.

### 3. Receipts

Every runner writes a receipt:

```text
artifacts/layer_runs/<run_id>/<runner_id>.receipt.json
```

Receipt must include:

- input packet hash
- output packet hash
- layer id
- runner id
- tool class used
- tests run
- pass/fail
- next recommended runner

### 4. Tests

Add:

```text
tests/agent_comms/test_layer_runner_registry.py
tests/terminal/test_geoseal_layer_runner_cli.py
```

Required cases:

- registry loads
- duplicate runner id fails
- invalid layer hop signal fails
- runner receipt is deterministic
- failed test blocks promotion
- chain can run a two-runner path

## Training Path

After the runner system exists, train on runner behavior:

1. Generate synthetic user goals.
2. Convert each into an intent packet.
3. Route to the smallest runner chain.
4. Execute or simulate the chain.
5. Store only compact traces:

```json
{
  "goal": "...",
  "packet": "...",
  "runner_chain": ["L01-intent-packet", "L03-bijective-code-packet", "L06-stage6-gate"],
  "receipts": ["..."],
  "final_verdict": "pass"
}
```

This becomes SFT data for "choose the correct runner chain", not bloated prose.

## Benchmark Path

Use three benchmark levels:

| Level | Benchmark | Meaning |
|---|---|---|
| Local unit | Registry and receipt tests | The runner system is structurally valid. |
| Harness eval | GeoSeal harness terminal and provider matrix | Provider-pair signaling and tool boundaries work. |
| Task eval | SWE-Bench-style or repo task suite | The agentic system improves real code tasks. |

Do not claim agentic improvement from training loss alone.

## Best Path For This Weekend

1. Keep the current research JSONs as roadmap seeds, but move them out of root after digestion.
2. Harden `scripts/system/parallelism_system.py` with a command allowlist before committing it as a real harness tool.
3. Add the layer runner registry with 5 runners only.
4. Add `geoseal layer-registry` and `geoseal layer-run` for dry-run receipts.
5. Wire Stage 6 and post-gate digestion as the first real runner pair.
6. Run focused tests.
7. Then train small SFT traces on runner-chain selection.

## Success Criteria

The system is ready for the next gear when:

- a user goal becomes a packet without prose bloat,
- the packet chooses a runner chain,
- each runner emits a receipt,
- failed gates stop the chain,
- passed gates produce a replayable artifact,
- the trace can become training data,
- release readiness can inspect the receipts.

