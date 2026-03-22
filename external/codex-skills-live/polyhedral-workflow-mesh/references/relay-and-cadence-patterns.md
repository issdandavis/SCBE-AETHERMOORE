# Relay And Cadence Patterns

Use this reference when the mesh needs more than one simple handoff.

## Pattern 1: Baton relay

Best for:

- Codex -> Claude
- agent -> automation
- browser lane -> repo lane

Shape:

- one packet
- one recipient
- one verify step
- one ack step

Use:

- `scripts/system/crosstalk_relay.py`

## Pattern 2: Goal race

Best for:

- multi-leg work that still has one clear finish line
- parallel lanes with checkpoints

Shape:

- lane owner per leg
- dependency chain
- visible scoreboard

Use:

- `scripts/system/goal_race_loop.py`

## Pattern 3: Trigger mesh

Best for:

- webhook wakeups
- n8n or connector automation
- event-driven follow-up

Shape:

- ledger or packet stays canonical
- automation reads or reacts to that state
- automation writes proof back

Use:

- `docs/AETHERBROWSE_CLOUD_RUN.md`
- `docs/WEB_RESEARCH_TRAINING_PIPELINE.md`

## Pattern 4: Periodic + aperiodic rendezvous

Best for:

- scheduled review or batch jobs
- irregular arrivals from other agents or users

Shape:

- periodic lane owns heartbeat
- aperiodic lane owns arrivals
- both write into one shared checkpoint or drop zone

Use:

- `docs/research/2026-03-16-phase-control-modulation-matrices.md`

## Pattern 5: Polyhedral face routing

Best for:

- one project touching browser, terminal, repo, automation, and review

Shape:

- each face has local rules
- edges define allowed handoffs
- one owner face decides the final state

## Anti-patterns

Avoid:

- freeform AI chatter without packets
- multiple sources of truth
- automation that mutates state without logging
- periodic loops forcing event-driven work to wait blindly
- event floods without a rendezvous buffer
