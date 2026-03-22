# Flow Surface Map

Use this reference when mapping a goal onto concrete repo surfaces.

## Core surfaces

### Browser surface

Use when:

- page state matters
- sign-in matters
- visual verification matters

Main files:

- `scripts/system/browser_chain_dispatcher.py`
- `scripts/system/playwriter_lane_runner.py`
- `agents/aetherbrowse_cli.py`

### Relay surface

Use when:

- one agent needs to hand work to another
- a machine-readable packet should survive context loss

Main files:

- `scripts/system/crosstalk_relay.py`
- `scripts/system/terminal_crosstalk_emit.ps1`
- `docs/system/CROSSTALK_RELIABILITY_RUNBOOK.md`

### Scoreboard surface

Use when:

- the work needs lanes, legs, and checkpoints

Main file:

- `scripts/system/goal_race_loop.py`

### Vector surface

Use when:

- a workflow can be represented as an enabled/disabled or weighted action set

Main file:

- `scripts/system/workflow_vector.py`

### Cadence / modulation surface

Use when:

- you need periodic versus aperiodic rhythm decisions
- you want a scheduling hint rather than one fixed loop

Main docs/files:

- `docs/research/2026-03-16-phase-control-modulation-matrices.md`
- `artifacts/experiments/phase_control_modulation_report.json`

### Automation surface

Use when:

- a webhook or scheduled workflow should carry or wake work

Main docs/files:

- `docs/AETHERBROWSE_CLOUD_RUN.md`
- `docs/WEB_RESEARCH_TRAINING_PIPELINE.md`
- `workflows/n8n/*`
- `scripts/system/start_hydra_terminal_tunnel.ps1`

## Decision rule

Start from:

1. source of truth
2. handoff path
3. verification point

Only then add:

4. automation trigger
5. cadence tuning
6. additional agents
