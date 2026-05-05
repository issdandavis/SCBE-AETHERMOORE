# Model Merging

Combine multiple fine-tuned models or LoRAs into a single weight set without retraining.

## Use merging when
- You have N specialist models (coding, chemistry, governance) and want one daily-driver.
- You want to test "does the union of skills survive?" before committing to a multi-LoRA stack.
- You're chasing the cost-effective path: merge is free; further training is not.

## Common methods (pick by goal)

| Method | What it does | When |
|---|---|---|
| **Linear / weighted average** | Simple averaging of weights. | Same architecture, similar fine-tuning paths. |
| **TIES** | Trim to top-k magnitudes per param, sign-vote, then merge. | Combining 3+ specialists with overlapping skills. |
| **DARE** | Drop random params before merge. Lower interference. | Combining many adapters without explosion. |
| **SLERP** | Spherical linear interpolation; preserves activation norm. | Two strong models you want to *interpolate* between. |
| **Model Soups** | Average a few promising fine-tunes of the SAME base. | Bagging fine-tunes for stability. |

## SCBE dispatch

```
python scripts/system/dispatch_coding_model_merge_hf_job.py \
  --run-name my-merge \
  --base-model Qwen/Qwen2.5-Coder-0.5B-Instruct \
  --adapters issdandavis/adapter-a,issdandavis/adapter-b \
  --method ties
```

## Verify a merge

A merge is only useful if the resulting model passes all input specialists' must-pass markers AND doesn't regress its base. Run the regression eval after every merge before promoting:

```
python scripts/eval/build_training_evaluation_matrix.py
```

The matrix shows the merge's pass rate on each input specialist's gate side-by-side with the original specialists. Any cell that drops > 10% from input -> merge means the merge ate that specialist's signal; reduce its weight or pick a different method.
