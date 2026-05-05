# Kaggle

Kaggle notebooks are a free GPU surface SCBE uses for short sweeps and pattern scoring.

## When Kaggle is worth it
- Small sweep (< 30 hours of T4 / P100).
- You can fit data + checkpoints into the 20 GB notebook scratch.
- The model fits in 16 GB GPU RAM (LoRA on 7B base, full fine-tune on 0.5-1.5B).

## Don't use Kaggle for
- Multi-day training runs (notebook idles out).
- Anything that needs > 2 GPUs.
- Datasets that contain secrets (notebooks are too easy to share publicly).

## SCBE Kaggle integration

| Script | Purpose |
|---|---|
| `scripts/system/consolidate_kaggle_kernels.py` | Pull current kernel state for review. |
| `scripts/eval/score_kaggle_round_patterns.py` | Score the patterns recovered from a Kaggle round vs SCBE's reference patterns. |
| `--copy-kaggle` flag on builders | Builders that include this flag copy the produced JSONL into a Kaggle dataset. |

## Push -> notebook -> verdict loop

1. Build dataset locally with `--copy-kaggle` flag.
2. The data lands in your Kaggle dataset (you set the dataset id once).
3. Notebook reads the dataset, trains, and writes a `verdict.json` to `/kaggle/working/`.
4. `consolidate_kaggle_kernels.py` pulls the verdict back into `training/runs/<run-name>/eval/`.
5. `training verdicts` shows it next to your HF runs.

## Free-tier hygiene

- Limit GPU hours per round (Kaggle gives ~30 hr/week of T4).
- If you exhaust them, the round queues; don't stack them.
- For longer-running specialists, prefer HF Jobs.
