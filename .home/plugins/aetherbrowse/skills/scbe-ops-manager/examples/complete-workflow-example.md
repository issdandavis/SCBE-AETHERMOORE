# Complete Cross-Talk Workflow Example

A real three-agent scenario: Shopify product catalog upgrade.

## 1. Session Sign-On

Claude signs on at session start. Append to `artifacts/agent_comm/session_signons.jsonl`:

```json
{"session_id": "sess-20260304T021500Z-a3f1c2", "codename": "Polaris-Forge-07", "agent": "agent.claude", "started_at": "2026-03-04T02:15:00Z", "status": "active", "goals": ["Upgrade Shopify products", "Deploy Hydra Armor", "Emit cross-talk ACK"]}
```

## 2. Claude Emits Sync Packet (Starting Work)

Write to `artifacts/agent_comm/20260304/cross-talk-agent-claude-shopify-upgrade-20260304T021500Z.json`:

```json
{
  "packet_id": "cross-talk-agent-claude-shopify-upgrade-20260304T021500Z",
  "created_at": "2026-03-04T02:15:00Z",
  "session_id": "sess-20260304T021500Z-a3f1c2",
  "codename": "Polaris-Forge-07",
  "sender": "agent.claude",
  "recipient": "agent.codex",
  "intent": "sync",
  "status": "in_progress",
  "repo": "SCBE-AETHERMOORE",
  "branch": "clean-sync",
  "task_id": "SHOPIFY-PRODUCT-UPGRADE",
  "summary": "Upgrading all 7 Shopify products with improved descriptions and adding Hydra Armor API as new product.",
  "proof": ["scripts/shopify_bridge.py"],
  "next_action": "Will emit ship packet when product catalog is committed.",
  "risk": "low",
  "gates": {"governance_packet": true, "tests_requested": []}
}
```

Append same as JSONL line to `artifacts/agent_comm/github_lanes/cross_talk.jsonl`.

Append to Obsidian `Cross Talk.md`:

```markdown
## 2026-03-04T02:15:00Z | Claude | SHOPIFY-PRODUCT-UPGRADE

**Status**: in_progress
**Intent**: sync
**Summary**: Upgrading all 7 Shopify products with improved descriptions and adding Hydra Armor API as new product.
**Proof**: scripts/shopify_bridge.py
**Next**: Will emit ship packet when product catalog is committed.
```

## 3. Codex Receives and Emits ACK

Codex reads the sync packet from either lane and replies:

```json
{
  "packet_id": "cross-talk-agent-codex-shopify-upgrade-ack-20260304T021600Z",
  "created_at": "2026-03-04T02:16:00Z",
  "sender": "agent.codex",
  "recipient": "agent.claude",
  "intent": "ack",
  "status": "in_progress",
  "repo": "SCBE-AETHERMOORE",
  "branch": "clean-sync",
  "task_id": "SHOPIFY-PRODUCT-UPGRADE-ACK",
  "summary": "ACK on Shopify product upgrade. Will handle Shopify conversion optimization after Claude ships catalog.",
  "proof": [],
  "next_action": "Await ship packet from Claude before running conversion copy pass.",
  "risk": "low",
  "gates": {"governance_packet": true, "tests_requested": []}
}
```

## 4. Claude Completes and Emits Ship Packet

After committing the upgraded `shopify_bridge.py`:

```json
{
  "packet_id": "cross-talk-agent-claude-shopify-upgrade-ship-20260304T022000Z",
  "created_at": "2026-03-04T02:20:00Z",
  "session_id": "sess-20260304T021500Z-a3f1c2",
  "codename": "Polaris-Forge-07",
  "sender": "agent.claude",
  "recipient": "agent.codex,agent.gemini",
  "intent": "ship",
  "status": "done",
  "repo": "SCBE-AETHERMOORE",
  "branch": "clean-sync",
  "task_id": "SHOPIFY-PRODUCT-UPGRADE",
  "summary": "Shipped upgraded Shopify catalog: 7 products with rich descriptions, Hydra Armor API added with 3 pricing tiers.",
  "proof": ["scripts/shopify_bridge.py", "commit abc1234"],
  "next_action": "Run `python scripts/shopify_bridge.py products --publish-live` to push to Shopify.",
  "risk": "low",
  "where": "terminal:claude-code",
  "why": "Improve conversion rate on existing Shopify traffic",
  "how": "Rewrote product descriptions, added tiered Hydra Armor pricing",
  "gates": {"governance_packet": true, "tests_requested": []}
}
```

## 5. Session Verified

After confirming products sync successfully, update sign-on:

```json
{"session_id": "sess-20260304T021500Z-a3f1c2", "codename": "Polaris-Forge-07", "agent": "agent.claude", "started_at": "2026-03-04T02:15:00Z", "status": "verified", "goals": ["Upgrade Shopify products", "Deploy Hydra Armor", "Emit cross-talk ACK"]}
```

## Key Takeaways

- Every packet goes to BOTH lanes (repo JSON + Obsidian markdown)
- Use `sync` when starting, `ship` when done, `ack` when receiving
- Include `proof` array with concrete evidence (file paths, commit hashes, URLs)
- Session identity (`session_id` + `codename`) threads packets together
- Mark session `verified` only after deliverables confirmed
