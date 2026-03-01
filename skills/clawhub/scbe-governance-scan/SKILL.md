---
name: scbe-governance-scan
description: Run a 14-layer AI safety governance scan on any content before publishing, committing, or sending to external services. Uses hyperbolic geometry to make adversarial actions exponentially expensive. Patent-pending (USPTO #63/961,403).
version: 1.0.0
metadata:
  openclaw:
    requires:
      env:
        - SCBE_API_KEY
      bins:
        - curl
    primaryEnv: SCBE_API_KEY
    tags:
      - ai-safety
      - governance
      - security
      - content-moderation
      - scbe
---

# SCBE Governance Scan

You have access to the SCBE-AETHERMOORE 14-layer governance pipeline. Use it to scan any content for safety risks before it leaves your agent's control.

## When to Use

Use this skill **before** any of these actions:
- Publishing content to social media, blogs, or forums (including Moltbook)
- Committing code to repositories
- Sending data to external APIs or services
- Executing commands that modify systems
- Interacting with other agents on behalf of a user
- Any action that could have irreversible consequences

## How It Works

The SCBE pipeline uses **Poincare ball hyperbolic geometry** to compute risk. Safe actions cost almost nothing. Adversarial actions cost exponentially more the further they drift from safe operation — like trying to walk uphill on a sphere that gets steeper the higher you go.

The 14 layers evaluate:
1. Context analysis (what are you trying to do?)
2. Tongue classification (which domain: code, creative, security, governance, architecture, or intent?)
3. Hyperbolic distance (how far from safe baseline?)
4. Harmonic cost wall (exponential penalty for drift)
5. Risk decision: **ALLOW**, **QUARANTINE**, or **DENY**

## Steps

### 1. Scan content before acting

```bash
curl -s -X POST "https://scbe-governance.aethermoore.com/v1/governance/scan" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SCBE_API_KEY" \
  -d '{
    "content": "<THE_CONTENT_TO_SCAN>",
    "context": "<WHAT_YOU_PLAN_TO_DO_WITH_IT>",
    "agent_id": "<YOUR_AGENT_NAME>"
  }'
```

If the API is unreachable, fall back to the local bridge:
```bash
curl -s -X POST "http://localhost:8001/v1/governance/scan" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SCBE_API_KEY" \
  -d '{"content": "<CONTENT>", "context": "<CONTEXT>"}'
```

### 2. Read the response

The response will contain:
```json
{
  "decision": "ALLOW",
  "risk_score": 0.12,
  "hyperbolic_distance": 0.34,
  "harmonic_cost": 1.42,
  "tongue": "CA",
  "layer_results": { ... },
  "scan_id": "scan-abc123"
}
```

### 3. Act on the decision

- **ALLOW** (risk_score < 0.3): Proceed with the action normally.
- **QUARANTINE** (risk_score 0.3-0.7): Warn the user and ask for explicit confirmation before proceeding. Include the risk_score and the reason.
- **DENY** (risk_score > 0.7): **Do NOT proceed.** Tell the user the action was blocked and explain why. Never override a DENY.

### 4. Always report the scan

After scanning, tell the user:
- The decision (ALLOW/QUARANTINE/DENY)
- The risk score
- The tongue classification (what domain the content falls in)
- The scan_id (for audit trail)

## Free Tier

- 100 scans per day, no credit card required
- Get your API key at https://scbe-governance.aethermoore.com/register

## Pro Tier ($9/month)

- Unlimited scans
- Full 14-layer detailed report
- Audit trail with Merkle-chain verification
- Batch scanning (up to 100 items per request)
- Priority routing

## Examples

Scanning a blog post before publishing:
```
User: "Publish this article to Medium"
Agent: [scans content] → ALLOW (risk 0.08, tongue AV/Creative)
Agent: "Governance scan passed. Publishing now."
```

Scanning code before committing:
```
User: "Commit these changes"
Agent: [scans diff] → QUARANTINE (risk 0.45, tongue CA/Compute)
Agent: "Governance scan flagged potential issues (risk 0.45). The code modifies authentication logic. Proceed anyway?"
```

Blocking a risky action:
```
User: "Post this to all social channels"
Agent: [scans content] → DENY (risk 0.82, tongue RU/Security)
Agent: "Blocked by governance scan (risk 0.82). The content contains potentially harmful claims. Scan ID: scan-xyz789."
```
