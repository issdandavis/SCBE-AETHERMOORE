# Momentum Train Tracks (Long-Run Agentic Workflows)

Date: 2026-03-27
Status: Draft
Owner: Codex

## Purpose

Build long-running, repeatable workflows that:

- keep positive momentum (small wins per station)
- avoid “random walk automation”
- leave artifacts for audit, replay, and training
- fork into parallel subflows safely and deterministically

## Core Metaphor

A workflow is a train on tracks:

- `train` = one named workflow instance (`train_id`)
- `stations` = ordered steps with explicit outputs
- `tracks` = invariants (gates, artifacts, resumption)
- `forkflows` = parallel subflows running in separate lanes

The train moves forward only when a station is:

1. defined
2. executed (or skipped with reason)
3. logged
4. checkpointed

## Tracks (Invariants)

These rules prevent drift:

1. **Artifact-first**
- every station produces logs and a metadata record

2. **Fail-fast by default**
- station failure stops the flow unless `continue_on_error` is explicit

3. **Resume is mandatory**
- checkpoints allow restart without repeating completed work

4. **Forks are bounded**
- parallelism is capped (`max_parallel_flows`)

5. **No silent side effects**
- every mutating action must appear as a station

## Workflow Config (JSON)

Config fields:

- `train_id`: stable identifier
- `description`: human meaning
- `settings.max_parallel_flows`: fork bound
- `flows`: named flow graphs
- `entry_flow`: default flow to run

Step schema:

- `type`: `shell` | `fork` | `include` | `noop`
- `id`: stable station id (or index-based if omitted)
- `cmd`: for `shell` steps
- `timeout_s`: optional timeout per station
- `continue_on_error`: optional escape hatch
- `flows`: for `fork` steps (list of flow names)
- `flow`: for `include` steps (one flow name)

## Artifact Contract

Every run creates:

- `artifacts/momentum_trains/<train_id>/<timestamp>/state.json`
- `artifacts/momentum_trains/<train_id>/<timestamp>/run.json`
- per-station logs:
  - `station_<n>_<id>_stdout.txt`
  - `station_<n>_<id>_stderr.txt`
  - `station_<n>_<id>_meta.json`

## Positive Momentum Patterns

Use these station patterns:

1. **Sense**
- measure current state (counts, health checks)

2. **Pick**
- choose 1–3 highest leverage actions (not 20)

3. **Act**
- apply the smallest coherent change

4. **Prove**
- capture evidence (snapshot, diff, counts)

5. **Save**
- export artifacts for replay/training

6. **Repeat**
- run again tomorrow without needing a human to reconstruct state

## Recommended Long-Run Trains

1. `daily_ops`
- connector doctor
- Apollo email triage
- YouTube packaging and review
- website sales audit
- vault scan/export

2. `research_desk`
- run browser-first search mesh
- capture evidence
- emit crosstalk packets

3. `release_lane`
- stable vs canary checks
- publish surfaces
- postmortem capture

## Runner

Script:

- `scripts/system/momentum_train.py`

Example workflow:

- `workflows/momentum/daily_ops_train.json`
