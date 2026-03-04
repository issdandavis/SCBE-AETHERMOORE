# Polly Pads: Dual-Zone Workspaces for AI Agent Safety

**By the SCBE-AETHERMOORE Team | February 2026**

## The Code Safety Problem

When multiple AI agents write code simultaneously, how do you prevent one from overwriting another's work? How do you ensure experimental code doesn't accidentally reach production? How do you gate which tools an agent can use based on its current trust level?

Polly Pads solve this with **dual-zone workspaces** -- each AI agent operates in either a HOT (exploratory) zone or a SAFE (execution) zone, with governance-gated promotion between them.

## HOT Zone vs SAFE Zone

### HOT Zone (Exploratory)
- Agents can plan, hypothesize, and draft
- Limited toolset: `plan_only` plus mode-specific read tools
- No deployment, no execution, no destructive operations
- Any agent starts here by default

### SAFE Zone (Execution)
- Full toolset available: build, deploy, config, experiment
- Requires SCBE governance approval to enter
- Coherence must be >= 0.55
- Harmonic cost (h_eff) must be <= 1,000
- Drift (d_star) must be <= 1.2

The promotion from HOT to SAFE isn't automatic -- it requires the governance gate to return ALLOW. An agent with low coherence (meaning recent failures or anomalous behavior) physically cannot access execution tools.

## Six Pad Modes

Each Polly Pad operates in one of six modes, mapped to the Sacred Tongues:

| Mode | Tongue | SAFE Tools | Use Case |
|------|--------|-----------|----------|
| ENGINEERING | CA (Cascade) | build, deploy, config | Software development |
| NAVIGATION | AV (Avatara) | map, proximity | Spatial/network operations |
| SYSTEMS | DR (Draconic) | telemetry, config, policy | Infrastructure management |
| SCIENCE | UM (Umbra) | hypothesis, experiment | Research and analysis |
| COMMS | KO (Knowledge) | radio, encrypt | Communications |
| MISSION | RU (Runes) | goals, constraints, policy | Strategic planning |

The mode determines which tools are available in each zone. An agent in ENGINEERING mode with SAFE zone access can build and deploy. The same agent in SCIENCE mode can only hypothesize and experiment. Mode + zone = precise capability gating.

## The SQLite Lifecycle

Every Polly Pad has a lifecycle managed by SQLite:

```sql
CREATE TABLE pads (
  pad_id TEXT PRIMARY KEY,
  mode TEXT NOT NULL DEFAULT 'ENGINEERING',
  zone TEXT NOT NULL DEFAULT 'HOT',
  metadata_json TEXT,
  created_at INTEGER,
  updated_at INTEGER
);

CREATE TABLE pad_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pad_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at INTEGER
);
```

Every flock action -- agent spawn, task assignment, governance vote, task completion -- is logged as a pad event. This creates a complete audit trail:

```json
{"event_type": "flock_summon", "payload": {"agent": "sheep-f48e", "msg": "Alpha summoned as leader"}}
{"event_type": "flock_embark", "payload": {"agent": "sheep-7fd8", "msg": "Scribe-Rune embarks on quest-44d9"}}
{"event_type": "flock_complete", "payload": {"agent": "quest-44d9", "msg": "Quest conquered"}}
```

## Squad Space: Multi-Agent Proximity

When multiple agents work in the same pad, the Squad Space tracks their positions in 6D Poincare hyperbolic space. Agents that are "close" (low hyperbolic distance) can share context. Agents that drift apart lose shared memory access.

The proximity graph enables:
- **Neighbor discovery** -- Which agents are working on related tasks?
- **Quorum computation** -- Do enough nearby agents agree on an action?
- **Leader election** -- The agent with lowest harmonic cost and highest coherence becomes the leader

## Cousin Takeover

When a pad fails (agent crashes, coherence drops to zero), the system spawns a **cousin pad** that inherits the compact state of the failed pad. The cousin picks up where the original left off, but in a fresh HOT zone -- it must re-earn SAFE access.

This is the self-healing mechanism: no work is lost, but the replacement agent doesn't inherit the trust level of its predecessor. It must prove itself.

## Real Integration

Polly Pads are live in the Claude IDE. The status bar shows:
- Current zone (HOT/SAFE) with colored indicator
- Current mode (ENGINEERING/NAVIGATION/etc.)
- Sacred Tongue affinity (CA/AV/DR/etc.)

Click the zone indicator to attempt promotion. Click the mode badge to cycle through modes. Every change is logged to SQLite and visible in the flock's Chronicles.

## Why Dual Zones Matter

Single-zone AI agent workspaces are a liability. An agent that can simultaneously plan *and* execute has no safety margin. Dual zones enforce a simple but powerful principle: **think before you act, and prove you're trustworthy before you act.**

The code is open source: [github.com/issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE)

---

*SCBE-AETHERMOORE is developed by ISSDANDavis. Patent pending: USPTO #63/961,403.*
