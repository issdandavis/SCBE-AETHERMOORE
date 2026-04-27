# TriAttention KV Cache Lane

**Date:** 2026-04-27
**Status:** Research-tracking specification. No runtime behavior is enabled by this document.
**Primary sources:**
- Paper: https://arxiv.org/abs/2604.04921
- Code: https://github.com/WeianMao/triattention

## Purpose

TriAttention is relevant to SCBE because it attacks the right bottleneck for long agentic sessions: KV cache memory during inference. It is not a training recipe, not a LoRA merge method, and not quantization. It is a runtime compression strategy for serving long-context models while preserving reasoning quality.

The useful fit for this repository is narrow:

- Long agent-bus transcripts where early instructions, recent turns, and late discoveries all matter.
- Long code-review or repair sessions where definitions appear near the beginning and the actionable bug appears near the end.
- Proposal and research sessions where citations, constraints, and final reviewer notes must survive the full context.
- Remote/free compute serving paths where KV cache pressure is the limiting factor before raw model quality.

## Source Finding

The TriAttention paper identifies a KV-cache bottleneck in extended reasoning. Instead of ranking keys only from recent post-RoPE queries, it works from pre-RoPE Q/K structure and estimates key importance with trigonometric distance preferences plus Q/K norm signals. The public repository reports vLLM and SGLang integration paths, which makes it more directly testable than a paper-only idea.

The important engineering point for SCBE: this can reduce serving memory without flattening or quantizing the model weights. That matches the current model-development rule: keep weights unquantized until the model is actually good, then optimize serving separately.

## SCBE Integration Rule

TriAttention is allowed only as an inference backend candidate until it passes SCBE gates. It must not change training data, adapter weights, tokenizer contracts, or model-promotion decisions.

Default behavior remains full-context, no-compression inference.

## Candidate Runtime Shape

The SCBE runtime should treat TriAttention as a backend capability flag:

1. A model server advertises `kv_cache_strategy=triattention_reference_v1`.
2. The agent bus records the prompt class, context length, model id, KV budget, decode speed, and downstream task result.
3. The evaluator compares the same task under full-cache inference and compressed-cache inference.
4. The router uses TriAttention only for lanes that pass task-specific gates.

This avoids mixing up three different concerns:

- Training quality: whether the model learned the coding/binary/tongue task.
- Weight composition: whether adapters can be routed or merged without forgetting.
- Runtime efficiency: whether KV cache compression preserves enough evidence while improving throughput.

## Test Gates

TriAttention must pass these before any default use:

- Accuracy floor: compressed-cache output keeps at least 99 percent of full-cache task performance on the same model and prompt set.
- End-of-text recall: facts introduced late in the prompt remain available with at least 98 percent recall.
- Executable coding delta: executable benchmark pass rate drops by no more than 1 percentage point versus full-cache.
- Citation recall delta: proposal/research citation recall drops by no more than 1 percentage point.
- Agent-bus replay: long bus transcripts replay to the same final decision class.
- Security holdout: hidden or late safety constraints cannot be dropped.

## First SCBE Benchmark Set

The first benchmark should be small and deterministic:

- `agent_bus_replay`: replay long AI-to-AI-to-human bus traces with late corrections.
- `long_context_code_review`: put API contracts at the beginning, implementation in the middle, and the bug report at the end.
- `proposal_citation_preservation`: require citations and constraints from early and late sections of a proposal packet.
- `binary_hex_tongue_coding`: require conversion among English, Python, binary, hexadecimal, and Sacred Tongues records across a long prompt.

## Blocked Lanes Until Measured

Do not enable compressed KV cache by default for:

- Final contract or proposal submission review.
- Security-sensitive decisions.
- Model-promotion gates.
- Adapter merge/routing acceptance decisions.

Reason: cache compression can silently discard evidence. Governance must treat this as a measurable runtime risk, not a free speedup.

## Implementation Phases

### Phase 0: Metadata Only

Add a config entry that names TriAttention as a candidate strategy and records gates. No behavior change.

### Phase 1: Trace Collection

Update long-context eval outputs to store:

- Context length.
- Prompt bucket tags: beginning, middle, recent, end-of-text.
- Required fact locations.
- Full-cache result.
- Candidate compressed-cache result, when available.

### Phase 2: Remote Backend Experiment

Use a remote or already-paid compute lane. Do not require local Docker or local GPU space.

Preferred order:

1. Hugging Face paid credit if the backend can run the required server.
2. Colab if an interactive browser/runtime is needed.
3. Kaggle if a notebook can run deterministic benchmark batches.
4. Local only if disk and GPU state are explicitly healthy.

### Phase 3: Router Hook

Expose `kv_cache_strategy` as a provider capability in the agent bus. Route only measured-safe lanes to the compressed backend.

## Acceptance Decision

TriAttention becomes useful to SCBE only if it improves runtime capacity without reducing governed task quality. The win condition is not "paper says faster"; the win condition is:

- Longer agent sessions fit in available compute.
- Coding and citation outputs stay correct.
- Late constraints remain visible.
- The bus records enough evidence to prove the optimization did not hide a failure.

