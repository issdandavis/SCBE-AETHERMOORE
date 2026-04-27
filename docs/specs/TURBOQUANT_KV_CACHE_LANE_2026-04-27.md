# TurboQuant KV Cache Lane

**Date:** 2026-04-27
**Status:** research-tracking note; no runtime behavior enabled
**Primary paper:** https://arxiv.org/abs/2504.19874
**Implementation references:**
- https://huggingface.co/vivekvar/turboquant
- https://github.com/0xSero/turboquant

## Summary

TurboQuant is a vector/KV-cache quantization method aimed at inference-time memory pressure. It is not a reason to quantize SCBE model weights yet. It is a candidate runtime optimization for long-context serving after our models and adapters pass functional gates.

The key distinction:

- **Weight quantization:** compresses model parameters and can change model behavior permanently for that artifact.
- **KV-cache quantization:** compresses the temporary attention cache created during inference. It can reduce memory for long sessions without flattening the trained model weights.

For SCBE, TurboQuant belongs beside TriAttention as a measured serving experiment, not inside the training or adapter-merge path.

## What The Paper Claims

The TurboQuant paper frames vector quantization as a geometric distortion problem. Its method rotates high-dimensional vectors so coordinate values follow a more quantizer-friendly distribution, then applies optimal scalar quantizers. For inner-product preservation, it adds a residual one-bit Quantized Johnson-Lindenstrauss transform.

The paper reports quality-neutral KV-cache quantization around 3.5 bits per channel and only marginal degradation around 2.5 bits per channel. It also reports strong nearest-neighbor recall without dataset-specific codebook training.

## Implementation Notes From Public Builds

The Hugging Face implementation presents TurboQuant as a drop-in cache for Hugging Face Transformers, with no training or calibration data required. It reports cache savings across several model families and highlights exact prefill-logit fidelity in its tests.

The Triton/vLLM-oriented GitHub implementation is more relevant for production serving, but it is also more experimental. Its own README calls out limits that matter to us:

- fused kernels matter; naive hybrid paths may decompress history back to float32 during compute;
- 2-bit values can degrade quality more than 4-bit values;
- MoE or linear-attention models may benefit less;
- deep serving integration is needed for the full memory/speed win.

## SCBE Fit

TurboQuant is most useful for:

- long agent-bus transcripts;
- browser/operator sessions with long trace history;
- proposal/research review where many citations stay in context;
- local/Ollama-style workflows once upstream runtimes support it;
- paid Hugging Face or Colab experiments where context length is the bottleneck.

TurboQuant is not currently useful for:

- improving bad training data;
- fixing adapter forgetting;
- proving a coding model can execute;
- merging LoRA weights;
- final proposal/security review without a measured full-cache comparison.

## Comparison With TriAttention

TriAttention decides **which cache regions to keep**: initial tokens, recent tokens, and end-of-text tokens.

TurboQuant decides **how to compress cached vectors** once they are kept.

They are complementary in theory:

- TriAttention is a cache-selection policy.
- TurboQuant is a cache-compression encoding.

The safe SCBE path is to test them separately first, then test a combined policy only if both independently pass.

## Proposed Eval Gate

Before enabling TurboQuant anywhere in SCBE routing, compare full-cache inference against TurboQuant-cache inference on the same model and prompts:

- `agent_bus_replay`: final decision class must match full-cache result.
- `long_context_code_review`: executable-pass delta must be no worse than 1 percentage point.
- `proposal_citation_preservation`: citation recall delta must be no worse than 1 percentage point.
- `end_of_text_constraint_recall`: late safety or task constraints must retain at least 98 percent recall.
- `binary_hex_tongue_coding`: cross-representation transformations must remain byte-round-trip correct.

Promotion target:

- full-cache quality parity first;
- memory reduction second;
- decode speed third.

## Implementation Plan

1. Keep SCBE weights unquantized.
2. Add TurboQuant only as a provider/runtime capability flag.
3. Run a remote experiment first; avoid local Docker/GPU pressure.
4. Record cache budget, context length, decode speed, executable result, citation recall, and late-fact recall.
5. Use routing only after measured parity on SCBE tasks.

## Recommended Near-Term Action

Do not install TurboQuant into the main runtime yet. The next useful action is to add it to the serving-strategy backlog and create an experiment harness that can compare:

- full cache;
- TurboQuant cache;
- TriAttention-style cache selection;
- combined selection plus compression.

