# Remote Training Runs - 2026-05-01

## Purpose

Start guarded remote training work on Hugging Face and Kaggle without filling the local machine or deleting daily-use files.

## Local Preflight

Command:

```powershell
npm run training:preflight:zero-cost
```

Result:

- OK
- Profile: `scbe-zero-cost-local-0.5b`
- Files checked: 4
- Missing: 0
- Empty: 0

## Hugging Face

Command:

```powershell
python scripts/system/dispatch_coding_agent_hf_job.py dispatch --profile-path config/model_training/coding-agent-qwen-geoshell-pair-agent-v1.json --smoke --backend api-inline --json
```

Result:

- Dispatched: true
- Job ID: `69f4374dd2c8bd8662bd4406`
- Job URL: https://huggingface.co/jobs/issdandavis/69f4374dd2c8bd8662bd4406
- Flavor: `t4-small`
- Timeout: `30m`
- Profile: `coding-agent-qwen-geoshell-pair-agent-v1-smoke`
- Base model: `Qwen/Qwen2.5-Coder-0.5B-Instruct`
- Adapter repo target: `issdandavis/scbe-coding-agent-qwen-geoshell-pair-agent-v1`
- Dataset repo: `issdandavis/scbe-coding-agent-sft-geoshell-pair-agent-v1`

Uploaded dataset files:

- `geoshell_pair_agent_v1_train.sft.jsonl`
- `geoshell_pair_agent_v1_holdout.sft.jsonl`

Monitor:

```powershell
hf jobs ps
hf jobs inspect 69f4374dd2c8bd8662bd4406
hf jobs logs 69f4374dd2c8bd8662bd4406
```

Notes:

- This is a smoke run with `push_adapter=false`.
- Do not dispatch the full run until the smoke job passes or its failure mode is understood.

## Kaggle

Command:

```powershell
npm run training:kaggle:approval-v2:launch
```

Result:

- Kernel pushed successfully
- Kernel version: 4
- Kernel URL: https://www.kaggle.com/code/issacizrealdavis/polly-auto-coding-approval-metrics-v1
- Exact ref: `issacizrealdavis/polly-auto-coding-approval-metrics-v1`
- Status after launch: `KernelWorkerStatus.RUNNING`
- Round: `coding-approval-metrics-v2`
- GPU: `t4`
- HF target repo: `issdandavis/scbe-coding-approval-metrics-qwen-kaggle-v2`
- HF dataset repo: `issdandavis/scbe-coding-agent-sft-stage6-repair-v7`

Monitor:

```powershell
python scripts/kaggle_auto/launch.py --status
kaggle kernels status issacizrealdavis/polly-auto-coding-approval-metrics-v1
```

Pull output when done:

```powershell
python scripts/kaggle_auto/launch.py --pull --round coding-approval-metrics-v2
```

## Next Gate

1. Check HF job logs and Kaggle status.
2. If HF smoke succeeds, dispatch the non-smoke GeoShell pair-agent training profile.
3. If Kaggle completes, pull output and run the paired eval / training review before promoting any adapter.
4. Do not merge adapters until `review_training_runs.py` marks the lane as promotion-ready with an explicit frozen gate pass.

## Later Update - Confirmed Adapter and Merge

Confirmed completed remote run:

- Kaggle kernel: `issacizrealdavis/polly-auto-coding-approval-metrics-v1`
- Round: `coding-approval-metrics-v2`
- DONE artifact: `artifacts/kaggle_outputs/polly-auto-coding-approval-metrics-v1/DONE.json`
- Status: `complete`
- Global step: `30`
- Train records: `175`
- Eval records: `107`
- Best eval metric: `2.9622254371643066`

Published adapter:

- Repo: `issdandavis/scbe-coding-approval-metrics-qwen-kaggle-v2`
- Upload commit: `0abc4f86bd8f07d077b1189fae4e1587a520ce78`
- Source folder: `artifacts/kaggle_outputs/polly-auto-coding-approval-metrics-v1/polly-coding-approval-metrics-v2`

Merged model:

- Local merged folder: `artifacts/merged_models/scbe-coding-approval-metrics-qwen-merged-v1-local`
- HF repo: `issdandavis/scbe-coding-approval-metrics-qwen-merged-v1`
- Verified remote files: `model.safetensors`, `config.json`, `tokenizer.json`, `tokenizer_config.json`, `generation_config.json`, `chat_template.jinja`, `scbe_merge_summary.json`
- Local smoke result: merged model loaded and generated a valid `def add(a, b): return a + b` function prefix.

Cleanup:

- Cancelled stale HF smoke job `69f4374dd2c8bd8662bd4406`.
- Cancelled redundant HF merge job `69f46801d70108f37ace2089` after local merge and HF upload were confirmed.

Open blocker:

- `dsl-synthesis-v3-fast` still fails on Kaggle at `loading_tokenizer`.
- Patch added to `scripts/kaggle_auto/kernel_template.py`:
  - `STATUS.json` phase telemetry for tokenizer/model/trainer/train/save/push.
  - `ERROR.json` failure payload on caught exceptions.
  - `TOKENIZERS_PARALLELISM=false`.
  - slow tokenizer path with `use_fast=False`.
- The failure still appears to be a hard worker failure before Python can write `ERROR.json`; do not relaunch this notebook blindly. Next repair should use a tiny tokenizer-only Kaggle probe or a packaged local model/tokenizer input before another full training push.
