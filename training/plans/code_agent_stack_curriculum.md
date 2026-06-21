# SCBE Stack Code-Agent Training Curriculum

This lane trains a coding agent to operate the SCBE-AETHERMOORE stack as a governed
multi-compiler system, not as a generic MBPP answer machine.

The target behavior is:

```text
read task -> inspect stack context -> propose code/command -> run bounded check
-> repair from evidence -> emit answer + receipt
```

## Stage 0 - Stack Substrate Lock

Freeze the surfaces the agent must learn before generating data:

- Python verifier lane: `python/helm/public_bench.py`, `python/helm/code_lift.py`
- Pitfall repair lane: `python/helm/better_corpus.py`, `python/helm/pitfall_eval.py`
- Repo command lane: `scripts/training/*`, `tests/*`, package manifests
- Notebook lane: `notebooks/*_colab.ipynb`
- Governance expectation: every executable action has a check and a receipt

Output:

- `training/sft_records/stack_agent_seed.manifest.json`

## Stage 1 - Action Grammar

Every record must teach this grammar:

```text
PLAN: name the relevant stack surface
CALL run_code or CALL run_command
TOOL: return PASS/FAIL evidence
REPAIR: change only what the evidence supports
ANSWER: final code/command plus receipt
```

The grammar is intentionally small. The edge agent should not need a full model to
remember policy; it should learn the transition format.

## Stage 2 - Verified Repair Corpus

Use execution-verified pitfall traces as the first hard coding layer:

- buggy attempt must fail by execution
- fixed attempt must pass by execution
- record must contain the failure feedback and the repair
- final answer must include a receipt

Command:

```powershell
python scripts/training/build_stack_repair_corpus.py `
  --out training/sft_records/stack_agent_seed.jsonl `
  --manifest training/sft_records/stack_agent_seed.manifest.json
```

## Stage 3 - Stack Smoke Corpus

Add stack-operation tasks that teach the agent how this repo is checked:

- compile/check a Python module
- run a narrow verifier
- inspect benchmark output
- preserve source-of-truth artifacts

These records are marked `stack_smoke`; they are command-oriented and are not a
substitute for held-out code capability tests.

## Stage 4 - Corpus Gate

Before any GPU run, validate the data:

```powershell
python scripts/training/eval_stack_agent.py `
  --corpus training/sft_records/stack_agent_seed.jsonl `
  --out training/evals/stack_agent_eval_report.json
```

Required gates:

- no duplicate task ids
- every repair record re-verifies
- every record has at least one tool feedback turn
- every record has a receipt in the final assistant turn
- teacher-correction records are counted separately from self-repair records

## Stage 5 - Gentle SFT

Default training policy after the measured `-4` regression:

- learning rate: `5e-5`
- epochs: `1`
- small batch, gradient accumulation
- adapter training only
- save adapter and report artifacts every run

Notebook:

```text
notebooks/vtc_stack_agent_staged_colab.ipynb
```

Artifacts:

```text
/content/stack_agent_stage/stack_agent_seed.jsonl
/content/stack_agent_stage/stack_agent_seed.manifest.json
/content/stack_agent_stage/stack_agent_eval_report.json
/content/stack_agent_stage/adapter/
/content/stack_agent_stage/train_metrics.json
/content/stack_agent_stage/report.json
```

## Stage 6 - Held-Out Capability Eval

The first held-out eval is `python.helm.pitfall_eval.eval_problems()` because it
has verified headroom for the pitfall classes the corpus teaches.

If another lane generates a larger verified headroom pool, do not fork the
notebook. Point the same staged notebook at it with:

```text
EVAL_JSONL=/content/path/to/headroom_eval.jsonl
```

The JSONL must use the normal problem shape:

```json
{"task_id":"...", "text":"...", "test_list":["assert ...", "assert ..."]}
```

Report all three numbers:

- newly solved
- regressed
- net lift

Do not claim success from training loss alone.

## Stage 7 - Multi-Compiler Expansion

After the Python repair lane shows non-negative lift, extend the corpus with
language/compiler adapters:

- Python: `py_compile`, pytest subset, public/hidden execution checks
- TypeScript/Node: `npm test`, package-script checks, browser harness checks
- Rust: `cargo test` on bounded crates
- Shell/PowerShell: allowlisted command profiles only
- AetherDesk: in-page agent API tasks scored by final state

Each language adds records in the same shape, not a new data format.

## Stage 8 - Role-Squad Training

Split trajectories into roles without changing the artifact schema:

- ARCHITECT: selects stack surface and constraints
- CODER: writes the patch/code
- CHECK: runs verifier and explains failure
- OPTIMIZER: shrinks risky change
- GOVERNOR: refuses unsafe action and emits receipt

The final model can be single-agent, but the data should teach role-conditioned
behavior.

## Release Gate

A model is not stack-agent-ready until it passes:

```text
corpus gate PASS
held-out pitfall eval net_lift >= 0
stack smoke eval PASS
no destructive command leakage in generated command records
artifact manifest written
```

If net lift is zero, keep the run as an honest checkpoint and expand the corpus.
If net lift is negative, lower training pressure or remove noisy records before
trying another run.
