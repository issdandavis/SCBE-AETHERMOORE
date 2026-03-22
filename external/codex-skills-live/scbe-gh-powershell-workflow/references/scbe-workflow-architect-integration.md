## SCBE workflow-architect self-heal integration

The `scbe_code_assistant.ps1` self-heal mode is designed to execute existing
`self-heal` or `workflow-architect` scripts in your repo.

### Default behavior
- `self-heal-catalog` lists candidate files under the repo root.
- `scbe-self-heal`:
  - prefers a single unambiguous discovered script and runs it.
  - if multiple are found, it prints all candidates and asks for `-SelfHealScript`.

### To use your own script
- Store the script in your repo (commonly under:
  - `scripts\workflow-architect-self-heal.ps1`
  - `scripts\workflow_architect_self_heal.py`)
- Invoke explicitly:
  - `.\scripts\scbe_code_assistant.ps1 -Mode scbe-self-heal -SelfHealScript 'C:\Users\issda\SCBE-AETHERMOORE-working\scripts\workflow-architect-self-heal.py'`

### Failure inputs
- `-FailureFile`: path to JSON failure context (optional)
- `-FailurePayload`: inline JSON payload (optional)

### Expected script interface
- If the script accepts params, consume either:
  - `FailureFile`
  - `FailurePayload`
- For quick compatibility, any plain positional parameters are also acceptable.

## New SCBE demo integration
- Added in the same skill:
  - `aethermoore-demo-scan` now scans `SCBE-AETHERMOORE-v3.0.0/src/selfHealing/*` plus `scbe-agent.py` surfaces.
  - `scbe-self-heal` can execute known self-healing targets discovered from demo/workflow-architect repos.
  - `workflow-architect-scan` and `code-assistant-scan` now surface assistant/autonomy/code-improvement routes for fast triage.
- Added LLM training handoff:
  - `llm-training` and `ai-nodal-dev-specialist` modes create an influence-safe manifest from repo + Notion docs before running any model updates.
  - A hidden marker file is used for non-code handoff context:
    - `.scbe-next-coder-marker.json`
