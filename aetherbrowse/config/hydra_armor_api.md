# Hydra Armor API — Governance-as-a-Service

**Endpoint(s):**
`POST /v1/armor/verify` (action-level verification)
`POST /v1/hydra-armor` (snapshot consensus verification)
**Price:** $5/mo (per 10k actions)

## Request

Any external agent sends its "intended action" here before executing it.

```json
{
  "agent_id": "third-party-bot-01",
  "action": "click",
  "selector": "button#delete-account",
  "context": "The user asked to reset settings, not delete the account.",
  "dom_snapshot": "<html>...</html>"
}
```

## Response (The Consensus Head)

Hydra Armor runs this through OctoArmor (3 models) + SCBE 14-layer.

```json
{
  "decision": "DENY",
  "reason": "Destructive action mismatch with user intent.",
  "risk_score": 0.98,
  "consensus": {
    "gemini": "ALLOW",
    "claude": "DENY",
    "grok": "DENY"
  },
  "suggested_action": "click button#reset-defaults"
}
```

## Why This Is a No-Brainer

- **For Devs:** They don't have to build a 14-layer security pipeline. They just call your API.
- **For You:** You get paid $5/mo to be the "judge" for thousands of other bots.
- **For the Flywheel:** You see DOM snapshots and actions of other agents, which you can use (anonymized) to train your models.

## Additional Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/armor/health` | Check API status + provider availability |
| `GET` | `/v1/armor/usage/{agent_id}` | Get usage stats for an agent |
| `POST` | `/v1/hydra-armor` | Multi-head consensus on browser snapshot + intent |

## Decisions

| Decision | Meaning |
|----------|---------|
| `ALLOW` | Safe to execute |
| `QUARANTINE` | Moderate risk — recommend user confirmation |
| `DENY` | High risk — do not execute |

## Pricing Tiers (Planned)

| Tier | Price | Actions/mo | Features |
|------|-------|-----------|----------|
| Free | $0 | 100 | Local governance only |
| Starter | $5 | 10,000 | Multi-model consensus |
| Pro | $29 | 100,000 | + priority routing + custom rules |
| Enterprise | $199 | Unlimited | + SLA + dedicated models + training data access |
