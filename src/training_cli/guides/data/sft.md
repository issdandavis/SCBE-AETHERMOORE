# Supervised Fine-Tuning (SFT)

Train a base model to imitate target outputs given prompts.

## Use SFT when
- You have prompt -> ideal-completion pairs and want the model to reproduce that style.
- You're teaching a new vocabulary, format, or canonical phrasing.
- You're bootstrapping a base model toward a domain (code, chemistry, governance).

## Don't use SFT when
- You only have *preferences* (A is better than B) -> use DPO.
- You have a tested base model and want to combine specialists -> use model merging.

## Data shape (canonical for SCBE)

JSONL, one example per line:

```json
{"prompt": "...", "completion": "..."}
```

Or chat-style:

```json
{"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
```

Existing SCBE builders that produce SFT-ready JSONL:
- `scripts/training_data/build_coding_approval_metrics_v3.py`
- `scripts/training_data/build_geoseal_industry_commands_sft.py`
- `scripts/training_data/build_chemistry_adapter_sft.py`
- `scripts/training_data/build_sacred_tongue_syntax_alignment_sft.py`

## Dispatch (HF Jobs)

```
python scripts/system/dispatch_coding_agent_hf_job.py \
  --run-name my-sft-run \
  --base-model Qwen/Qwen2.5-Coder-0.5B-Instruct \
  --data training-data/sft/my_data.jsonl \
  --flavor default
```

## Verify before pushing
- Run `training quickstart` to see the dispatch command before executing.
- Run `training status` after dispatch to monitor.
- Verdict file lands at `training/runs/<run-name>/eval/<job-id>_verdict.json`.
- A run is considered ready to ship only when `must_pass_all_ok: true` AND the gate passes without `constrained_gate_scaffold` (see scbe-stack guide).
