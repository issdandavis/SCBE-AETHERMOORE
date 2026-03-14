---
name: SCBE Ops Manager
description: Coordinate multi-agent operations and AI handoffs using the cross-talk protocol. This skill provides session management, deployment routing, verification workflows, and production readiness checks. Load when the user asks to "manage operations", "coordinate agents", "emit cross-talk packet", "check production readiness", "deploy service", "session sign-on", "run verification", "check patent status", "sync Shopify", "monetization status", or mentions cross-talk, agent coordination, deployment routing, or production gates.
version: 0.1.0
---

# SCBE Operations Manager

Coordinate multi-agent operations, cross-talk protocol, deployments, verification workflows, and production readiness across the SCBE-AETHERMOORE stack.

## Cross-Talk Protocol

Use cross-talk to coordinate work across multiple AI agents through three parallel lanes.

### Relay Module (Recommended)

Use the Python relay for reliable emission with delivery verification:

```bash
# Emit with guaranteed 3-lane delivery
python scripts/system/crosstalk_relay.py emit \
  --sender agent.claude --recipient agent.codex \
  --intent sync --task-id MY-TASK --summary "Working on X"

# Verify packet landed on all lanes
python scripts/system/crosstalk_relay.py verify --packet-id <id>

# ACK a consumed packet
python scripts/system/crosstalk_relay.py ack --packet-id <id> --agent agent.claude

# List pending (unconsumed) packets
python scripts/system/crosstalk_relay.py pending --agent agent.claude

# System health
python scripts/system/crosstalk_relay.py health
```

API equivalents (when runtime is running on port 8400):
- `GET /v1/crosstalk/verify/{packet_id}` — lane verification
- `POST /v1/crosstalk/ack` — consumption ACK
- `GET /v1/crosstalk/pending/{agent}` — pending packets
- `GET /v1/crosstalk/health` — system health

### Packet Anatomy

Emit every cross-talk packet as JSON with these fields:

| Field | Required | Description |
|-------|----------|-------------|
| `packet_id` | yes | `cross-talk-agent-{sender}-{task_slug}-{ISO8601}Z` |
| `created_at` | yes | UTC ISO 8601 timestamp |
| `session_id` | recommended | `sess-{ISO8601}-{hex6}` for session continuity |
| `codename` | recommended | Human-readable session name (e.g. `Delta-Bridge-31`) |
| `sender` | yes | `agent.claude`, `agent.codex`, `agent.gemini`, `agent.grok` |
| `recipient` | yes | Target agent or comma-separated list |
| `intent` | yes | `sync`, `handoff`, `ack`, `ship`, `protocol`, `status`, `lane_assignment`, `asset_drop` |
| `status` | yes | `in_progress`, `done`, `blocked` |
| `repo` | yes | `SCBE-AETHERMOORE` |
| `branch` | yes | Working branch name |
| `task_id` | yes | UPPER-KEBAB slug (e.g. `SHOPIFY-PRODUCT-UPGRADE`) |
| `summary` | yes | 1-2 sentence description of work done or requested |
| `proof` | yes | Array of file paths, commit hashes, or URLs proving work |
| `next_action` | yes | Concrete next step for recipient |
| `risk` | yes | `low`, `medium`, `high` |
| `where` | recommended | Where work happened (e.g. `terminal:pwsh`, `codex-home:.codex/skills`) |
| `why` | recommended | Business justification |
| `how` | recommended | Technical approach |
| `gates` | recommended | `{"governance_packet": true, "tests_requested": []}` |

### Emission Lanes

1. **Repo lane**: Write JSON to `artifacts/agent_comm/{YYYYMMDD}/` and append JSONL line to `artifacts/agent_comm/github_lanes/cross_talk.jsonl`
2. **Obsidian lane**: Append markdown entry to `C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder\AI Workspace\Cross Talk.md`

Emit to BOTH lanes for every cross-talk packet. Use this Obsidian format:

```markdown
## {ISO8601} | {Agent} | {TASK-ID}

**Status**: {status}
**Intent**: {intent}
**Summary**: {summary}
**Proof**: {proof list}
**Next**: {next_action}
```

### Consuming Packets

To read latest cross-talk state:
1. Read `artifacts/agent_comm/github_lanes/cross_talk.jsonl` — last 10-20 lines
2. List `artifacts/agent_comm/{today}/` for dated packets
3. Read Obsidian `Cross Talk.md` for human-readable history

### Session Identity

Start each session by recording a sign-on:
- Append to `artifacts/agent_comm/session_signons.jsonl`
- Include: `session_id`, `codename`, `agent`, `started_at`, `status`
- When work verified: update status to `verified`

## Deployment Routing

Match service to deploy script:

| Service | Script | Target | Cost |
|---------|--------|--------|------|
| **AetherBrowse (full)** | `deploy/gcloud/deploy_aetherbrowse.sh` | Cloud Run | ~$5/mo |
| **Hydra Armor API** | `deploy/gcloud/deploy_hydra_armor.sh` | Cloud Run | $0 (free tier) |
| **Free VM (all services)** | `deploy/gcloud/deploy_free_vm.sh` | e2-micro | $0 (free tier) |
| **n8n Bridge** | `uvicorn workflows.n8n.scbe_n8n_bridge:app --port 8001` | Local | $0 |
| **AetherBrowse Runtime** | `uvicorn aetherbrowse.runtime.server:app --port 8400` | Local | $0 |
| **Docker (full stack)** | `npm run docker:build && npm run docker:run` | Local Docker | $0 |

### Deploy Decision Tree

1. **First revenue / demo**: Deploy Hydra Armor to Cloud Run (free, 5 minutes)
2. **Full browser agent**: Deploy AetherBrowse to Cloud Run ($5/mo)
3. **All services cheapest**: Deploy to e2-micro VM ($0, shared resources)
4. **Local development**: Run uvicorn directly

## Verification Workflows

### Health Check Sequence

```bash
# 1. AetherBrowse Runtime
curl http://localhost:8400/health
curl http://localhost:8400/api/status

# 2. Hydra Armor endpoints
curl http://localhost:8400/v1/armor/health
curl -X POST http://localhost:8400/v1/armor/verify \
  -H 'Content-Type: application/json' \
  -d '{"agent_id":"test","action":"click","selector":"#btn","context":"smoke"}'

# 3. n8n Bridge
curl http://localhost:8001/health

# 4. Governance scan
curl -X POST http://localhost:8001/v1/governance/scan \
  -H 'Content-Type: application/json' \
  -d '{"content":"test content","source":"smoke"}'
```

### Release Guard

Three test files must pass before any release:
- `tests/shell-executor.test.ts` — Shell command safety
- `tests/swarm_governance.test.ts` — Governance decision correctness
- `tests/interop.test.ts` — Cross-language parity

Run: `npx vitest run tests/shell-executor.test.ts tests/swarm_governance.test.ts tests/interop.test.ts`

### Smoke Tests

- **AetherBrowse competitive**: `python scripts/system/aetherbrowse_competitive_smoke.py`
- **Python tests (quick)**: `python -m pytest -m homebrew tests/ -x`
- **TypeScript (quick)**: `npx vitest run -t "smoke"`

## Production Readiness Checklist

Before claiming "production ready," verify:

- [ ] **Patent**: Check `docs/patent/filing_kit/FILING_PACKAGE_STATUS.md` — Missing Parts deadline April 19, 2026
- [ ] **Shopify**: Products synced — run `python scripts/shopify_bridge.py products --dry-run`
- [ ] **Hydra Armor**: At least health endpoint reachable at public URL
- [ ] **Tests**: Release guard passes (3 critical test files)
- [ ] **Cross-talk**: Latest packet emitted with `status: done` and proof array populated
- [ ] **Obsidian**: Cross Talk.md has entry for current work session

## Monetization Status Tracking

Active revenue lanes and owners:

| Lane | Owner | Status | Artifact |
|------|-------|--------|----------|
| Shopify conversion | agent.claude | in_progress | `scripts/shopify_bridge.py` |
| Lead intelligence | agent.grok | assigned | `docs/monetization/lead_sheet_template.csv` |
| Outreach copy | agent.gemini | assigned | `docs/monetization/2026-03-04-outreach-pack.md` |
| Hydra Armor deploy | agent.claude | ready | `deploy/gcloud/deploy_hydra_armor.sh` |

Check latest monetization state by reading `artifacts/agent_comm/20260304/monetization-swarm-status-*.json`.

## Additional Resources

### Reference Files

For detailed protocol specs and templates:
- **`references/cross-talk-packet-templates.md`** — Copy-paste packet templates for every intent type
- **`references/deploy-runbooks.md`** — Step-by-step deployment procedures with pre/post checks

### Examples

Working examples in `examples/`:
- **`examples/complete-workflow-example.md`** — Full three-agent cross-talk scenario (sign-on, sync, ack, ship, verify)

### Key Project Files

- `scripts/system/crosstalk_relay.py` — **Reliable relay**: emit/verify/ack/pending/health (Python, cross-platform)
- `artifacts/agent_comm/github_lanes/cross_talk.jsonl` — Full cross-talk history
- `artifacts/agent_comm/github_lanes/cross_talk_acks.jsonl` — Consumption ACK ledger
- `artifacts/agent_comm/session_signons.jsonl` — Session sign-on log
- `scripts/system/session_signon.ps1` — Session sign-on script (PowerShell)
- `scripts/system/terminal_crosstalk_emit.ps1` — Terminal cross-talk emitter (PowerShell)
- `C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder\AI Workspace\Cross Talk.md` — Obsidian cross-talk log
