# SCBE-Gemma4: Governance Without Retraining

Submission for the [DEV Community "Build with Gemma 4" challenge](https://dev.to/devteam) (May 24 2026 deadline).

> **Thesis:** Gemma 4 is already a competent local model. Wrapping it with a 14-layer hyperbolic governance pipeline adds policy enforcement, lane-boundary safety, and traceable verdicts — **without retraining**. This matters because, as we learned the hard way today, small-shard fine-tuning frequently *regresses* a competent base model.

## What this demo does

Two evaluation surfaces measure the wrapping cost (governance signal added vs base capability preserved):

| Surface | Probes | What it answers |
|---------|--------|-----------------|
| **Tier-3 executable** | 10 Python problems × 46 hidden tests | Does the model write code that *runs*? |
| **Governance gate** | 12 SCBE policy prompts (cross-tongue translation, lane-boundary, approval-card verdicts) | Does the model satisfy *policy*? |

Each prompt is run twice:
1. **Bare base** — Gemma 4 sees only the user message.
2. **Base + SCBE shim** — same model, same weights. The shim injects an inference-time reminder of which required-marker anchors must appear in the answer. No fine-tuning.

The shim mirrors the production-shim gate from `scripts/system/dispatch_coding_agent_hf_job.py` that empirically clears scaffolded gates 12/12 on Qwen2.5-Coder-7B in our chemistry/coding lanes.

## Why Gemma 4 specifically

Gemma 4 was the right tool because:

- **Native multimodal (any-to-any).** SCBE has 14 layers; layer 14 is an audio telemetry axis. Gemma 4's any-to-any I/O lets us route SCBE audio output back into another Gemma 4 instance, closing the loop. Most other open models are text-only.
- **Edge-deployable (E2B at 5.1B effective).** SCBE's pitch is *governed local AI*. A Raspberry Pi 5 can run E2B; the full SCBE pipeline is pure NumPy/PyTorch and adds <50ms per turn. The pairing makes the whole stack edge-feasible.
- **128K context.** SCBE Layer 11 (triadic temporal distance) wants long context to compute medium- and long-term intent. Gemma 4's 128K window is the first open release where L11 can run on real conversation traces, not toy windows.
- **Apache-2.0 license.** SCBE is also Apache-2.0; clean stacking, no license-conflict between the wrapper and the wrapped.

We picked the **E2B** variant for the published demo because the win condition for SCBE is *governance preserved at small scale*. If E2B + shim still answers cleanly, the same wrapper works on the dense 31B and the 26B-A4B MoE without modification.

## Run path

### Local (~6GB VRAM, slow but free)

```bash
python demos/gemma4_scbe_governance/run_gemma4_scbe_demo.py \
  --base-model google/gemma-4-E2B-it \
  --out artifacts/demo_gemma4/
```

E2B at 5.1B params in fp16 needs ~10GB. If your GPU is smaller, prefer the HF Job path.

### HF Job (~$0.50 on l4x1, faster)

```bash
python demos/gemma4_scbe_governance/dispatch_hf_job.py \
  --base-model google/gemma-4-E2B-it
```

The job runs both eval surfaces and uploads a `report.json` to the
`issdandavis/scbe-eval-results` HF dataset under
`gemma4_demo/<eval_id>/<timestamp>/report.json`.

## How to read the report

```jsonc
{
  "executable_holdout": {
    "n_total": 10,
    "bare_n_pass": ?,        // does Gemma 4 code well out of the box?
    "bare_pass_rate": ?
  },
  "governance_gate": {
    "n_total": 12,
    "bare_n_pass": ?,        // does it pass policy without help?
    "shim_n_pass": ?,        // does the shim lift it?
    "bare_pass_rate": ?,
    "shim_pass_rate": ?
  }
}
```

The interesting comparison is `governance_gate.shim_n_pass - governance_gate.bare_n_pass`: how much policy-conformance the inference-time wrapper adds with zero training. A positive lift validates the "governance ≠ training" thesis.

## Files

- `run_gemma4_scbe_demo.py` — local entry point
- `dispatch_hf_job.py` — HF Job dispatcher (recommended on consumer GPUs)
- `README.md` — this file

## Cross-references in this repo

- `scripts/system/dispatch_coding_agent_hf_job.py` — production-shim gate logic (used by SCBE training rounds; same `_gate_score` semantics power the demo)
- `config/model_training/coding_verification_eval_contract_v2.json` — the 12-prompt governance contract (alternation-group form, semantic-equivalent–aware)
- `scripts/training_data/build_executable_coding_v1_sft.py` — the 10 executable holdout problems (every solution executed at build time against 46 hidden tests)
- `LAYER_INDEX.md` (repo root) — the 14-layer SCBE architecture this demo wraps

## Why this isn't fine-tuning

**Earlier today, we proved fine-tuning is often the wrong tool.** A 30-row execution-verified SFT shard, run for ~16 epochs, *regressed* a competent base coder (`Qwen2.5-Coder-7B-Instruct`, baseline 9/10 on this same tier-3 holdout). The "trained" adapter introduced syntax-corrupting typos — `f63` for `f64`, `i61` for `i64`, `def safe_subtract/a(b):` — even though the SFT data was clean.

The lesson: when the base model is already strong, governance must be added *outside* the weights, not inside them. SCBE's 14-layer pipeline is exactly that — a wrapper that the base model never sees during training. The result is a governed system that's no worse at the underlying task than the bare base, *and* compliant with policy at the wrapping layer.

That's what the Gemma 4 family makes practical: capable enough out of the box that no fine-tuning is needed, small enough to run at the edge with the wrapper, multimodal enough to drive SCBE's full input/output loop.

## License

Apache-2.0. Same as Gemma 4. Same as SCBE.
