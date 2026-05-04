# AI Context Vault And Channels

The AI context vault gives Codex, Claude, Kimi, local Ollama lanes, and future agents a small rolling memory surface for active tasks.

It is local-first:

- full trail: `artifacts/agent_context_vault/agents/<agent>/rolling.jsonl`
- compact handoff: `artifacts/agent_context_vault/agents/<agent>/state.json`
- live team channel: `artifacts/agent_context_vault/channels/<channel>.jsonl`
- task scoreboard: `artifacts/agent_context_vault/scoreboards/<task>.json`

The compact state is the pre-compaction funnel. Agents write bounded events while they work, then call `digest` before context gets compressed or handed off.

## Smoke Test

```powershell
python scripts/system/agent_context_vault.py --json simulate --task-id ai-context-vault-smoke --agents agent.codex,agent.claude,agent.kimi
```

Read the shared channel:

```powershell
python scripts/system/agent_context_vault.py --json channel --channel ai-context-vault-smoke --tail 20
```

Read one agent's compact state:

```powershell
python scripts/system/agent_context_vault.py --json read --agent agent.kimi --tail 5
```

## Write Pattern

Each agent appends a small event:

```powershell
python scripts/system/agent_context_vault.py --json append `
  --agent agent.codex `
  --channel release-team `
  --task-id release-clean `
  --summary "Codex checked npm package status and found three publish surfaces." `
  --proof "npm view scbe-aethermoore version" `
  --next-action "Claude should review package metadata before publish."
```

Then compact before handoff:

```powershell
python scripts/system/agent_context_vault.py --json digest --agent agent.codex --max-items 12 --max-chars 1600
```

## Scaling Rule

Use this vault for task-local state, not secret storage.

- Store summaries, proof paths, hashes, open actions, risk labels, and channel IDs.
- Do not store API keys, tokens, passwords, raw private prompts, or customer data.
- Mirror to cloud only after the local trail is proven and scrubbed.

For durable delivery across the older AI-to-AI lanes, keep using:

```powershell
python scripts/system/crosstalk_relay.py emit --sender agent.codex --recipient agent.claude --task-id TASK --summary "Bounded handoff."
python scripts/system/crosstalk_relay.py health
```

The vault is the rolling task memory. `crosstalk_relay.py` is the delivery bus. `context_librarian.py` remains the pairwise compact merger when two agent states need one shared packet.

## Formation Matrix Tuning

Use the deterministic tuner to sweep formation ratios and interaction factors:

```powershell
python scripts/system/tune_formation_matrix.py --grid 7 --top 12
```

The latest tuning report is written to:

`artifacts/agent_context_vault/formation_matrix_tuning.json`

Current local sweep result:

- best formation: `quad`
- roles: `scout`, `coder`, `verifier`, `firefighter`
- base ratio: `1.909280`
- target ratio from `1.5 * phi`: `2.427051`
- interaction: `0.680000`
- expansion: `1.440000`
- gate pressure: `1.340000`
- externality factor: `0.360000`
- score: `0.537044`

Interpretation:

- Use `pair` for narrow private work or one-model verification.
- Use `triad` for the stable default: builder, verifier, context roller.
- Use `quad` when you want maximum variable mapping without full mesh chatter.
- Use `hex` when broad research, release, packaging, and verification lanes all need to run at once.

## HYDRA Compound Matrix Council

The compound matrix council combines Kaggle Grandmaster-style strategy with the SCBE formation matrix:

```powershell
python scripts/system/multi_model_compound_matrix.py --top 10
```

Outputs:

- `artifacts/agent_context_vault/compound_matrix/compound_matrix_packet.json`
- `artifacts/agent_context_vault/compound_matrix/full_system_review.md`

Deep-research findings encoded into the council:

- Winning systems start with the evaluation metric and a validation split that mirrors hidden test behavior.
- Large feature factories work when they are followed by leakage checks and pruning.
- Out-of-fold predictions are the safe substrate for stacking because the upper layer sees held-out predictions, not in-fold leakage.
- Ensembling works best when model errors are diverse; similar models add chatter more than signal.
- Pseudo-labeling is useful only when fold-safe and confidence-gated.
- Post-processing belongs at the end, after the core validation spine is stable.

Current council ranking:

1. `op_rag_source_ingest` — source manifest, provenance, and leakage-check ingest.
2. `op_training_eval_loop` — compare local, Kaggle, and Hugging Face runs with one evaluation contract.
3. `op_coding_patch_gate` — bounded patch plus focused regression proof.
4. `op_doc_finding_research` — find source docs and convert them into routeable evidence.
5. `op_pathfinding_repo` — shortest tested route from goal to script, test, and artifact.

Reusable skill:

`.agents/skills/hydra-compound-matrix/SKILL.md`

## HYDRA Challenge Reloop

Use the challenge loop to test the council against a real local challenge, evaluate completion, and create a new isolated loop plan:

```powershell
python scripts/system/hydra_challenge_loop.py --challenge repo_ladder_validate --max-attempts 1
```

Pipeline:

1. `hydra_challenge_loop.py` runs the challenge verifier and records attempts.
2. `hydra_challenge_eval.py` converts the run into a completion factor.
3. `hydra_challenge_reloop.py` creates a temp run branch directory and compacted next-loop plan.

The temp run branch is not a real Git branch. It is an isolated artifact directory so the dirty worktree is not mutated.

Current smoke challenges:

- `repo_ladder_validate`: validates repo-native agentic benchmark task manifests.
- `repo_ladder_level1`: runs the repo-native agentic benchmark ladder through level 1.
- `external_eval_validate`: validates the external agentic eval adapter manifest.

Artifacts:

- `artifacts/agent_context_vault/challenge_loop/*_latest.json`
- `artifacts/agent_context_vault/challenge_loop/*_latest.md`
- `artifacts/agent_context_vault/challenge_loop/eval/*_eval_latest.json`
- `artifacts/agent_context_vault/challenge_loop/loops/*/next_loop_plan.json`

Completion rule:

`c = 1.0` when the verifier passes. Failed runs carry residual `1 - c` into the next loop so the next attempt starts from compacted evidence, not the full raw trail.

## Kaggle Strategy Replay With SCBE Substrate

Run the dry replay against known Kaggle-style solution patterns:

```powershell
python scripts/system/replay_kaggle_solution_strategy.py
```

Outputs:

- `artifacts/agent_context_vault/kaggle_replay/kaggle_solution_strategy_replay_latest.json`
- `artifacts/agent_context_vault/kaggle_replay/kaggle_solution_strategy_replay_latest.md`

Current local result:

- templates checked: `5`
- average top-5 coverage: `0.77`
- aligned templates: `4/5`
- claim boundary: dry strategy replay only; no Kaggle data downloaded and no leaderboard score claimed.

The replay now distinguishes raw council rank from SCBE substrate-adjusted rank. The adjusted rank means the operation can be routed through the actual harness:

- GeoSeal CLI receipts through `explain-route`, `code-packet`, and `atomic`.
- Sacred Tongues full-name routes: `Kor'aelin`, `Avali`, `Runethic`, `Cassisivadan`, `Umbroth`, `Draumric`.
- Atomic tokenizer features for atoms, bonds, molecules, reactions, catalysts, and residues.
- Self-reflective builder knobs, where agents may improve the harness they are using only when a route receipt, round-trip hash, and eval gain exist.
- Bureaucratic machine flow, where the harness supplies intake, desk-pair review, phase-lead timing, context-secretary compression, and audit-printer receipts.

Office role mapping:

- `intake_clerk`: source and document finding lanes move papers fast without changing the world.
- `desk_pair`: coding and council lanes think twice, check each other, and only then produce a candidate.
- `phase_lead`: evaluation lane sets the clock and decides whether the phase advances or holds.
- `context_secretary`: release and digest lanes compress the useful residue into the context vault.
- `audit_printer`: benchmark packet lanes print the receipt trail for public claims.

Use this as the pre-data gate. If the dry replay stays above `0.60`, the next step is a small real dataset replay through Kaggle or a local public benchmark adapter.
