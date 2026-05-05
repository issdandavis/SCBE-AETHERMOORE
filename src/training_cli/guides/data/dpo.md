# Direct Preference Optimization (DPO)

Train a model from preference pairs (chosen vs rejected) without a separate reward model.

## Use DPO when
- You have an SFT-trained model and want to *steer* its behavior on contested choices.
- You can rank pairs of outputs (which is better) but cannot write the canonical answer.
- You're closing the gap on a small set of failing-must-pass markers (the SCBE Stage 6 case).

## Don't use DPO when
- The base model has never seen the domain -> SFT first.
- You have only one good example per case -> use SFT.

## Data shape

JSONL, one preference triple per line:

```json
{"prompt": "...", "chosen": "...", "rejected": "..."}
```

Existing SCBE builders that produce DPO-ready JSONL:
- `scripts/training_data/build_agentic_preference_math_dpo.py`
- `scripts/training_data/build_geoshell_pair_agent_preference_dpo.py`

## Dispatch (HF Jobs)

```
python scripts/system/dispatch_coding_agent_dpo_hf_job.py \
  --run-name my-dpo-run \
  --base-model issdandavis/scbe-coding-agent-qwen-stage6-repair-v8 \
  --data training-data/dpo/my_pairs.jsonl
```

## SCBE-specific: scaffold dependence

When you DPO an SFT-trained model and the post-DPO regression eval passes only with `constrained_gate_scaffold: true`, the model has learned to **cooperate with the harness**, not to emit canonical vocabulary on its own. Verify with a no-scaffold run:

```
# rerun the regression eval with --no-scaffold and confirm the result
```

If scaffolded passes 5/5 and no-scaffold fails 0/5, you have two paths:
1. Ship the harness+adapter together as the deployed agent.
2. Train another iteration to fix raw vocabulary fidelity (more SFT echo data, or a v10 raw-quality DPO).
