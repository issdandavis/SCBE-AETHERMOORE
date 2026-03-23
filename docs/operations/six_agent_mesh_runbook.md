# Six-Agent Mesh Runbook

This runbook defines how a six-worker SCBE mesh operates in one repo while using the repaired Obsidian vault and the repo-local cross-talk relay. It is designed for parallel work where each worker owns a narrow mutable surface and returns evidence to a coordinating agent, typically `agent.codex`.

## Purpose

- Launch a six-worker mesh without file collisions.
- Keep machine-readable handoff packets in the repo.
- Mirror human-readable status into the repaired Obsidian vault.
- Track relay state with goal-race artifacts and ACKs.
- Recover quickly when the Obsidian lane or CDP browser lane drifts.

## Control Surfaces

- Dated packet lane: `artifacts/agent_comm/<YYYYMMDD>/cross-talk-*.json`
- JSONL bus: `artifacts/agent_comm/github_lanes/cross_talk.jsonl`
- ACK lane: `artifacts/agent_comm/github_lanes/cross_talk_acks.jsonl`
- Obsidian mirror: `<resolved workspace>/Cross Talk.md`
- Goal-race artifacts: `artifacts/goal_races/<run_id>/packets.json`, `scoreboard.json`, `README.md`

The relay script writes to all three communication lanes on emit:

```powershell
python scripts/system/crosstalk_relay.py emit --sender agent.codex --recipient agent.mesh --intent orchestrate --task-id SIX-AGENT-MESH-KICKOFF --summary "Launch mesh." --proof artifacts/goal_races/<run_id>/packets.json artifacts/goal_races/<run_id>/scoreboard.json --next-action "Workers claim ownership and begin."
```

## Kickoff

1. Generate or identify the active goal-race run under `artifacts/goal_races/<run_id>/`.
2. Treat `packets.json` as the immutable routing and dependency contract for the run.
3. Treat `scoreboard.json` as the live readiness and completion snapshot for the run.
4. Emit one kickoff packet that points at `packets.json` and `scoreboard.json` in `--proof`.
5. Publish a worker ownership matrix before any worker edits a file.
6. Require each worker to operate only on explicitly assigned mutable paths.
7. Require each worker to return one summary, one proof list, and one next action.

## Goal-Race Artifact Use

The goal-race artifact is the coordination backbone for the mesh.

- `packets.json` answers: who owns what phase, what depends on what, and what the done criteria are.
- `scoreboard.json` answers: which lanes are still pending, which checkpoint tasks exist, and whether the run is still in `ready`, `in_progress`, or `blocked` state.
- `README.md` is the human summary and should not be treated as the canonical machine state.

For the current six-agent kickoff pattern, the kickoff packet should reference the goal-race artifact directly in `proof`, not paraphrase it. This keeps all workers and the coordinator aligned on the same run ID.

## Worker Ownership

The mesh should use one owner per mutable file set. The coordinator is outside the worker count and is responsible for launch, integration, and final verification.

| Worker | Scope | Ownership rule |
|---|---|---|
| 1 | Browser capability lane | Edit only kickoff-assigned browser capability files. |
| 2 | Browser ops docs lane | Edit only kickoff-assigned browser ops documentation files. |
| 3 | Workflow mesh lane | Edit only kickoff-assigned workflow mesh files. |
| 4 | HF training lane | Edit only kickoff-assigned HF training files. |
| 5 | System research lane | Edit only kickoff-assigned system research files. |
| 6 | Mesh runbook lane | Edit only `docs/operations/six_agent_mesh_runbook.md`. |

Ownership rules:

- Do not edit another worker's file, even for a small fix.
- If a worker discovers a needed change outside its owned path, emit a packet to the coordinator instead of patching it.
- If ownership must change mid-run, the coordinator emits a new packet that reassigns the file or creates a repair packet.
- Goal-race lane roles such as `navigator`, `operator`, and `verifier` are phase roles, not permission to cross-edit another worker's file.

## Relay Packet Contract

Every worker packet should include:

- `sender`
- `recipient`
- `intent`
- `task_id`
- `summary`
- `status`
- `proof`
- `next_action`

Recommended worker completion template:

```powershell
python scripts/system/crosstalk_relay.py emit `
  --sender agent.worker-name `
  --recipient agent.codex `
  --intent sync `
  --task-id <TASK-ID> `
  --summary "<one-line completion or blocker summary>" `
  --status in_progress `
  --proof <primary-artifact> <secondary-proof-if-any> `
  --next-action "<what coordinator should do next>"
```

Use `status=blocked` if the worker cannot proceed without reassignment, missing context, or a repaired dependency.

## Proof Expectations

Workers should return evidence, not just claims.

- Minimum proof for a docs lane: changed file path plus a readback-verification note.
- Minimum proof for a code lane: changed file path plus one test, smoke, or artifact path.
- Minimum proof for a browser lane: output artifact plus one verification signal such as screenshot, DOM snapshot, health check, or smoke result.
- If the worker changed no file, the proof must still include the decision artifact or command output path that justifies the status.

Proof quality bar:

- Use repo-relative paths in `proof`.
- Prefer immutable artifacts such as `packets.json`, `scoreboard.json`, screenshots, smoke JSON, or generated notes.
- Do not place secrets, tokens, or raw `.env` contents in a packet.
- Keep the `summary` short and put detail into the proof path or next action.

## ACK Flow

The ACK lane marks consumption, not agreement.

1. Sender emits the packet.
2. Sender or coordinator verifies that the packet landed on dated JSON, JSONL bus, and Obsidian.
3. Recipient checks pending packets:

```powershell
python scripts/system/crosstalk_relay.py pending --agent agent.codex
```

4. Recipient reads the packet and claims responsibility for the next action.
5. Recipient ACKs only after consuming the packet:

```powershell
python scripts/system/crosstalk_relay.py ack --packet-id <packet-id> --agent agent.codex --notes "Consumed and queued for integration."
```

6. Coordinator checks health if ACKs stop moving:

```powershell
python scripts/system/crosstalk_relay.py health
```

Operational rules:

- Do not ACK before reading the proof and next action.
- A sender can verify delivery, but only the recipient should ACK consumption.
- If a packet is delivered but not ACKed, it remains actionable work.
- If a packet is ACKed but the follow-up fails, emit a new packet with the new status instead of rewriting history.

## Obsidian Drift Checklist

The relay resolves the Obsidian workspace in this order:

1. `OBSIDIAN_WORKSPACE` environment variable, if set and the path exists.
2. Any existing vault in `%APPDATA%\Obsidian\obsidian.json`.
3. Fallback legacy workspace: `C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder\AI Workspace`

If the Obsidian lane drifts:

1. Run `python scripts/system/crosstalk_relay.py health` and inspect the reported `lanes.obsidian.workspace`, `path`, and `exists` fields.
2. If the wrong vault is selected, inspect `%APPDATA%\Obsidian\obsidian.json` and confirm the repaired vault is present.
3. If vault discovery is unclear, run:

```powershell
python scripts/system/list_obsidian_vaults.py --json
```

4. If needed, set `OBSIDIAN_WORKSPACE` to the repaired vault path for the current shell and rerun `health`.
5. Confirm that the parent directory for `Cross Talk.md` exists before re-emitting a packet.
6. Do not patch `crosstalk_relay.py` during an active mesh unless that file is explicitly assigned to a worker.

## CDP Browser Drift Checklist

The repo's browser lane is CDP-first. The AetherBrowse blueprint expects CDP backend support, and the tunnel stack checks browser health at `http://127.0.0.1:<BrowserPort>/health`.

If browser availability drifts:

1. Decide whether the issue is service health, browser backend, or local binary/runtime.
2. Check the browser service health endpoint used by the stack:

```powershell
Invoke-WebRequest http://127.0.0.1:<BrowserPort>/health
```

3. If the service is down, restart or reuse the local stack through the normal launcher rather than improvising a new browser surface.
4. If the service is up but actions fail, verify the CDP-backed path still matches the expected backend in the local browser tooling.
5. If Playwright or Chromium is the broken dependency rather than the HTTP service, repair the local runtime with the approved Playwright setup path before blaming the mesh.
6. Emit a `blocked` packet with the failing endpoint or artifact path if the lane cannot recover inside its ownership boundary.

Useful recovery signals already present in the repo:

- `docs/AETHERBROWSE_BLUEPRINT.md` documents the CDP-first execution path.
- `scripts/system/start_hydra_terminal_tunnel.ps1` checks browser readiness via the `/health` endpoint and writes smoke artifacts.
- `artifacts/system_smoke/` and `artifacts/page_evidence/` are the preferred proof locations for browser service recovery.

## Minimal Operating Loop

1. Kickoff packet establishes the run ID and points to the goal-race artifact.
2. Workers edit only their owned files.
3. Workers emit completion or blocker packets with proof.
4. Recipients ACK consumed packets.
5. Coordinator integrates only after proof is present and ownership rules were respected.
6. If Obsidian or browser health drifts, repair the lane first or emit a blocker packet; do not silently continue on a broken channel.
