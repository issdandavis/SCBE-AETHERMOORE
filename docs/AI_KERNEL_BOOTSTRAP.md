# SCBE AI Kernel Bootstrap (User-Space)

This repo now includes a user-space AI kernel scaffold for governed multi-agent browsing and dataset generation.

## What "AI kernel" means here

Not an operating-system kernel.

It is a deterministic governance core that:

1. Accepts intent + policy.
2. Gates each task through defensive checks.
3. Enforces allowed domains/fields/PII rules.
4. Emits auditable decisions + training traces.

## Added components

1. `python/scbe/defensive_mesh.py`
- `DefensiveMeshKernel`
- `GovernedJob`, `GovernedTask`, `TaskGateResult`
- Integrates:
  - `agents/antivirus_membrane.py`
  - `agents/kernel_antivirus_gate.py`

2. `scripts/scbe_ai_kernel_wrapper.py`
- Reads YAML/JSON job specs.
- Gates tasks with SCBE defensive mesh.
- Optionally calls a browser worker endpoint.
- Writes run artifacts + optional HF JSONL rows.

3. `workflows/scbe_ai_kernel/starter_town_job.yaml`
- Starter-town vertical slice task spec.

4. `workflows/scbe_ai_kernel/manager_agent_prompt.md`
- Manager-planner prompt template with hard policy contract.

## Run

```powershell
python scripts/scbe_ai_kernel_wrapper.py `
  --job workflows/scbe_ai_kernel/starter_town_job.yaml `
  --skip-hf
```

With browser worker:

```powershell
python scripts/scbe_ai_kernel_wrapper.py `
  --job workflows/scbe_ai_kernel/starter_town_job.yaml `
  --browser-endpoint http://127.0.0.1:8000/scrape
```

Default HF output path:

- `training-data/hf-digimon-egg/defensive_mesh_sft.jsonl`

## Core artifacts produced per run

- `training/runs/scbe_ai_kernel/<timestamp>/job.json`
- `training/runs/scbe_ai_kernel/<timestamp>/governed_tasks.json`
- `training/runs/scbe_ai_kernel/<timestamp>/blocked_tasks.json`
- `training/runs/scbe_ai_kernel/<timestamp>/browser_results.json`
- `training/runs/scbe_ai_kernel/<timestamp>/output_items.json`
- `training/runs/scbe_ai_kernel/<timestamp>/review.json`

