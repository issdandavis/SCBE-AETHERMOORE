# LoRA / PEFT

Low-Rank Adaptation: train a small set of adapter weights instead of the full model.

## Use LoRA when
- You're fine-tuning anything > 1B parameters.
- You want multiple specialized variants from one base (chemistry adapter, governance adapter).
- You're cost-bounded; LoRA training is 10-50x cheaper than full fine-tuning.

## Don't use LoRA when
- The base model is already small (< 500M params); full fine-tune is fine.
- You need to change the model's tokenizer or vocabulary -> requires full fine-tune.

## Key knobs

- `r` (rank): higher r = more capacity, more memory. Start at 16 for code/chemistry, 8 for style.
- `alpha`: scaling factor; common rule alpha = 2 * r.
- `target_modules`: which projection matrices get the adapter. For Qwen/LLaMA: `["q_proj","k_proj","v_proj","o_proj"]`. For coverage: add `["gate_proj","up_proj","down_proj"]` (slower, often higher quality).

## Existing adapter registry

```
python scripts/model_training/build_adapter_registry.py
```

That writes a manifest of every adapter in `training/runs/*` with its base, rank, and last verdict. Use the registry to pick a starting adapter for further training rather than retraining from scratch.

## LoRA stack composition

You can chain adapters at inference time. To plan a stack against your goal (coding + chemistry + governance), use:

```
python scripts/eval/plan_adapter_stack.py
```

Loaded adapters multiply, so order matters. Plan output suggests an order that minimizes cross-adapter drift.

## Drift analysis

After training a new LoRA, check it didn't regress its base capabilities:

```
python scripts/eval/analyze_lora_drift.py --use-registry
```

Flagged adapters need a smaller `r`, lower learning rate, or fewer steps.
