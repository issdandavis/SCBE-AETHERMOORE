# Autonomous Agent Prediction Validation Harness

GeoSeal command:

```powershell
node C:\Users\issda\SCBE-AETHERMOORE\bin\geoseal.cjs aap-scaffold --zip --json
```

Aliases:

```powershell
geoseal aap-dashboard
geoseal agent-prediction-scaffold
geoseal agent-prediction-dashboard
geoseal aap-meta-eval --data-dir C:\path\to\autonomous-agent-prediction-beta --json
```

## Purpose

Use Kaggle Autonomous Agent Prediction (Beta) as an outside validation surface for SCBE training/tool-loop work.

This is not just a Kaggle package. It is a constrained benchmark for whether an agent can:

- inspect a fresh binary-classification dataset
- run deterministic tools under a budget
- generate candidate submissions
- track receipts and public feedback
- select the best two submissions before the session terminates

## Boundary

GeoSeal is the outer development cockpit. The Kaggle harness cannot call arbitrary local GeoSeal commands.

Anything needed inside the competition must be packaged under the submission root as:

- `agent.yaml`
- `prompts/*.md`
- `skills/*/SKILL.md`
- `skills/*/scripts/*.py`

The generated scaffold follows that boundary.

## Model pricing and selection

| Model ID | Display name | Input / 1M | Cached input / 1M | Output / 1M | Role |
| --- | --- | ---: | ---: | ---: | --- |
| `gemini-3.1-flash-lite` | Gemini 3.1 Flash Lite | `$0.25` | `$0.025` | `$1.50` | default main agent |
| `gemini-3.5-flash` | Gemini 3.5 Flash | `$1.50` | `$0.15` | `$9.00` | backup only |
| `gemini-3.1-pro-preview` | Gemini 3.1 Pro Preview | `$2.00` | `$0.20` | `$12.00` | rare fallback only |

The scaffold defaults to `gemini-3.1-flash-lite`.

Reason: under `max_budget_usd: $2.00`, the model should not perform long reasoning. The packaged scripts should do the data work, and the model should only route, call tools, read ledgers, submit candidates, and select the best two submissions.

## Generated artifacts

Default output:

```text
C:\dev\aap_validation\scbe_aap_agent\
C:\dev\aap_validation\scbe_aap_agent.zip
C:\dev\aap_validation\aap_validation_dashboard.html
```

Core files:

```text
agent.yaml
prompts/system.md
skills/tabular_binary_solver/SKILL.md
skills/tabular_binary_solver/scripts/solve_tabular_binary.py
validation_manifest.json
```

## Smallest-network lane

The generated solver includes micro neural-network candidates:

- `tiny_nn_k32_h4`: select up to 32 features, train one hidden layer of 4 units
- `tiny_nn_k64_h8`: select up to 64 features, train one hidden layer of 8 units

AAP scores AUC, not model size, so the correct policy is:

- submit the best ensemble first if leaderboard score matters
- keep the tiny NN candidates as proof of smallest-model capability
- promote the tiny NN only when its public score is close enough to the heavier model

## Inner agent loop

The system prompt instructs the competition agent to:

1. call `get_status`
2. run the packaged tabular solver with `run_command`
3. read `work/scbe_aap_outputs/aap_run_ledger.json`
4. submit ranked candidate CSV files with `submit_predictions`
5. record public scores
6. select the best two submissions
7. only then emit a plaintext final response

## Training value for SCBE

This lane produces practical receipts for:

- execution quality under budget
- tool-loop reliability
- validation-before-selection behavior
- whether small/local models can route and pre-filter effectively
- whether SCBE training data should reward repair, ledgering, and completion discipline

The useful score is not only leaderboard rank. The useful score is whether the agent produces better outputs with fewer wasted tool calls and clear receipts.

## Local meta-validation

The official data includes `data/train_01` through `data/train_16`, each with:

- `train.csv`
- `test.csv`
- `sample_submission.csv`
- `solution.csv`

Run:

```powershell
node C:\Users\issda\SCBE-AETHERMOORE\bin\geoseal.cjs aap-meta-eval --data-dir C:\path\to\autonomous-agent-prediction-beta --json
```

This outer runner:

- runs the generated solver once per `train_XX`
- scores every candidate CSV against `solution.csv`
- reports overall AUC plus `Usage` split AUC when available
- tracks whether tiny NN candidates are close to the heavier baselines
- writes a dashboard and CSV ledger under `C:\dev\aap_validation\local_meta_eval`

This is the pre-submit scoreboard. If the local meta-eval does not improve, the official hidden public/private sessions probably will not either.
