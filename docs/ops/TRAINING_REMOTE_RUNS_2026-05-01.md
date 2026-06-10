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

DSL synthesis repair:

- `polly-tokenizer-probe-qwen-coder` completed on Kaggle in about 30 seconds, proving Qwen tokenizer download/load/encode works on Kaggle.
- The apparent `loading_tokenizer` failure was misleading. Added `checking_device` / `device_checked` telemetry and confirmed the real blocker was Kaggle assigning a Tesla P100 (`sm_60`) while the round required sm70+ behavior.
- Patched `scripts/kaggle_auto/kernel_template.py` so:
  - T4/A100 assignments keep the real 4-bit NF4 GPU training path.
  - P100 assignments enter a bounded CPU smoke fallback instead of hard-failing during P100 model load.
  - CPU/P100 smoke defaults are capped with `cpu_smoke_max_records` and `cpu_smoke_max_steps`.
- `dsl-synthesis-v3-fast` version 8 completed:
  - DONE artifact: `artifacts/kaggle_output/polly-auto-dsl-syn-v3-fast/DONE.json`
  - Status: `complete`
  - Global step: `3`
  - Train records: `32`
  - Eval records: `6`
  - Train loss: `67.37401326497395`
  - Adapter: `artifacts/kaggle_output/polly-auto-dsl-syn-v3-fast/polly-dsl-synthesis-v3-fast/adapter_model.safetensors`
- Published smoke adapter and evidence:
  - Repo: `issdandavis/scbe-coding-agent-qwen-dsl-synthesis-v3-fast-kaggle`
  - Adapter upload commit: `ee1f2ac18a9089d860b909b9c3505a9d7f16d61e`
  - DONE commit: `dc15ad00fd6f80eb8aec3b6205c8f38dac1c4332`
  - Training history commit: `15af2b5bf08203f253a40b0a29873f14c73e2a37`

Promotion note:

- The DSL v3-fast adapter is a completed smoke artifact, not a promotion-quality adapter. Loss is high and the run used the bounded fallback path. Use it as proof that the Kaggle lane no longer fails silently; wait for a real T4/A100 run before adding this adapter to a production merge.
