# Functional Coding Agent Benchmark

Date: 2026-04-26

## Purpose

This lane tests coding agents like a user would experience them: prompt in, TypeScript function out, execute it, compare the returned value and final game state.

Perplexity and frozen eval are useful training signals, but they do not prove the model can perform the task. Promotion into a merge profile requires executable behavior.

## Commands

Run a local model or LoRA adapter:

```powershell
npm run benchmark:coding-agents -- --models BASE <adapter-or-model> --max-new-tokens 260
```

Run pasted outputs from another agent/provider:

```powershell
npm run benchmark:coding-agents -- --candidate-file artifacts\coding_agent_benchmarks\external_candidate_template.json
```

Gate a report:

```powershell
npm run benchmark:coding-agents:gate -- artifacts\coding_agent_benchmarks\latest\report.json --min-pass-rate 0.85 --beat-base
```

## Current Task Set

- `score_add`: mutate `state.score` and return the new score.
- `heal_clamp`: heal, clamp to max HP, append `healed`.
- `inventory_unique`: append missing inventory item once.
- `cooldown_gate`: decrement active cooldown or fire action and reset cooldown.
- `quest_flags`: require all flags, add reward once, preserve rewards on failure.
- `weighted_choice`: return the first option crossing cumulative weight without mutating state.

## College Choice Matrix

The college-style lane adds SAT-prep-like coding drills: lesson, multiple-choice boundary, gold solution, repair from near-miss, binary/hex prompt surface, and hidden executable checks.

Build it:

```powershell
python scripts\build_college_coding_choice_matrix.py
```

Run only the college hidden checks:

```powershell
npm run benchmark:coding-agents -- --models BASE --task-file config\training\coding_agent_benchmarks\college_choice_eval_tasks_v1.json --replace-default-tasks --max-new-tokens 260
```

Run the gold candidate template:

```powershell
npm run benchmark:coding-agents:college:gold
```

Current college hidden baseline:

- `BASE`: 2/5, 40.00%.
- `college-choice-gold-template`: 5/5, 100.00%.

Current generated training payload:

- 35 SFT records.
- 5 hidden executable eval tasks.
- Record families: lesson, multiple-choice boundary, gold generation, repair from near miss, binary/hex prompt map, and trick rejection.

Convenience commands:

```powershell
npm run benchmark:coding-agents:college -- --models BASE --max-new-tokens 260
npm run benchmark:coding-agents:compare -- artifacts\coding_agent_benchmarks\20260426T142831Z artifacts\coding_agent_benchmarks\20260426T143616Z --label college-base --label college-gold
```

## Kaggle Approval Metrics v2

The `coding-approval-metrics-v2` Kaggle round now includes `college_coding_choice_matrix_v1.sft.jsonl`. It should only launch when a GPU slot is free.

Preflight:

```powershell
npm run training:kaggle:approval-v2:ready
```

Launch when ready:

```powershell
npm run training:kaggle:approval-v2:launch
```

Blocking wait mode if we want the terminal to hold until a slot opens:

```powershell
python scripts\kaggle_auto\launch.py --round coding-approval-metrics-v2 --gpu t4 --wait-ready --poll --poll-interval 300
```

## Promotion Rule

An adapter is not eligible for merge unless it passes the functional gate.

Default gate:

- Pass rate at least 85%.
- If BASE is present in the same report, adapter pass rate must be greater than BASE when `--beat-base` is used.
- The report must include task-level failures so repair data can be generated from exact runtime evidence.

## Current Evidence

Latest expanded benchmark before repair training:

- `BASE`: 4/6, 66.67%.
- `issdandavis/scbe-coding-agent-qwen-stage6-repair-v7-hfjobs`: 3/6, 50.00%.
- External candidate template: 6/6, 100.00%.

The current adapter is blocked from merge. The repaired TypeScript debug SFT set now includes gold examples for the three hard patterns: cooldown gate, quest flags, and weighted choice.
