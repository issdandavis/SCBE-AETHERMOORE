# Zapier Integration Guide

Connect SCBE alerts to Slack, Email, Notion, and 5000+ other apps via Zapier.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCBE → ZAPIER → YOUR APPS                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   SCBE API                                                       │
│      │                                                          │
│      │ DENY or QUARANTINE decision                              │
│      │                                                          │
│      ▼                                                          │
│   /v1/alerts  ◀──── Zapier polls every 1-5 minutes              │
│      │                                                          │
│      │ New alert detected                                       │
│      │                                                          │
│      ▼                                                          │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                      ZAPIER                              │   │
│   │                                                          │   │
│   │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │   │
│   │   │  Slack  │  │  Email  │  │ Notion  │  │ PagerDuty│  │   │
│   │   └─────────┘  └─────────┘  └─────────┘  └─────────┘   │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Setup: SCBE → Slack

### Step 1: Create Zap

1. Go to [zapier.com](https://zapier.com) and log in
2. Click "Create Zap"

### Step 2: Set Trigger (SCBE Alerts)

1. Search for "Webhooks by Zapier"
2. Choose "Retrieve Poll" as trigger
3. Configure:
   - **URL**: `https://your-scbe-api.com/v1/alerts?pending_only=true`
   - **Headers**:
     ```
     X-API-Key: your-scbe-api-key
     ```

### Step 3: Set Action (Slack Message)

1. Search for "Slack"
2. Choose "Send Channel Message"
3. Connect your Slack workspace
4. Configure message:

```
🚨 SCBE Alert: {{severity}}

Agent: {{agent_id}}
Decision: {{alert_type}}
Message: {{message}}

Trust Score: {{data__trust_score}}
Audit ID: {{audit_id}}
Time: {{timestamp}}
```

### Step 4: Test & Enable

1. Click "Test trigger" to pull sample data
2. Review the Slack message preview
3. Click "Publish Zap"

---

## Quick Setup: SCBE → Email

### Trigger

Same as above - use "Webhooks by Zapier" → "Retrieve Poll"

### Action: Gmail/Email

1. Search for "Gmail" (or your email provider)
2. Choose "Send Email"
3. Configure:
   - **To**: security-team@yourcompany.com
   - **Subject**: `[SCBE {{severity}}] {{alert_type}} - {{agent_id}}`
   - **Body**:

```html
<h2>SCBE Security Alert</h2>

<table>
  <tr><td><b>Severity:</b></td><td>{{severity}}</td></tr>
  <tr><td><b>Agent:</b></td><td>{{agent_id}}</td></tr>
  <tr><td><b>Decision:</b></td><td>{{alert_type}}</td></tr>
  <tr><td><b>Trust Score:</b></td><td>{{data__trust_score}}</td></tr>
  <tr><td><b>Time:</b></td><td>{{timestamp}}</td></tr>
</table>

<p>{{message}}</p>

<p><a href="https://your-scbe-dashboard.com/audit/{{audit_id}}">View Full Audit</a></p>
```

---

## Quick Setup: SCBE → Notion

### Action: Create Database Item

1. Search for "Notion"
2. Choose "Create Database Item"
3. Select your alerts database
4. Map fields:
   - **Alert ID**: `{{alert_id}}`
   - **Severity**: `{{severity}}`
   - **Agent**: `{{agent_id}}`
   - **Message**: `{{message}}`
   - **Timestamp**: `{{timestamp}}`
   - **Status**: "New"

---

## Alert Data Structure

Each alert from `/v1/alerts` includes:

```json
{
  "alert_id": "alert-20260123-143052-a1b2c3",
  "timestamp": "2026-01-23T14:30:52.123456Z",
  "severity": "high",
  "alert_type": "decision_deny",
  "message": "Agent trading-bot-001 request was DENY: execute_trade",
  "agent_id": "trading-bot-001",
  "audit_id": "audit-20260123-143052-xyz789",
  "data": {
    "trust_score": 0.25,
    "risk_level": "HIGH"
  }
}
```

### Field Reference

| Field | Description | Example Values |
|-------|-------------|----------------|
| `severity` | Alert importance | `low`, `medium`, `high`, `critical` |
| `alert_type` | What triggered alert | `decision_deny`, `decision_quarantine`, `trust_decline` |
| `agent_id` | AI agent identifier | `trading-bot-001` |
| `audit_id` | Link to full audit | `audit-20260123-...` |
| `data.trust_score` | Agent's trust score | `0.0` - `1.0` |

---

## Advanced: Filtered Alerts

Only trigger on specific conditions:

### High Severity Only

Add a Filter step in Zapier:
- **Field**: `severity`
- **Condition**: `(Text) Exactly matches`
- **Value**: `high`

### Specific Agent

Add a Filter step:
- **Field**: `agent_id`
- **Condition**: `(Text) Contains`
- **Value**: `trading`

---

## Acknowledging Alerts

After processing, acknowledge alerts so they don't repeat:

### Option 1: Zapier Webhook Action

Add a second action after your notification:
1. "Webhooks by Zapier" → "POST"
2. URL: `https://your-scbe-api.com/v1/alerts/{{alert_id}}/ack`
3. Headers: `X-API-Key: your-key`

### Option 2: Let Them Auto-Expire

Alerts older than 24 hours are automatically marked as processed.

---

## Pre-Built Zap Templates

Copy these templates (replace URLs and keys):

### Slack Critical Alerts
```
Trigger: Webhooks by Zapier (Poll)
  URL: https://api.example.com/v1/alerts?pending_only=true
  Headers: X-API-Key: xxx

Filter: severity = high OR severity = critical

Action: Slack - Send Channel Message
  Channel: #security-alerts
  Message: 🚨 *{{severity}}* | {{message}}
```

### Daily Notion Summary
```
Trigger: Schedule by Zapier
  Every day at 9:00 AM

Action: Webhooks by Zapier (GET)
  URL: https://api.example.com/v1/metrics
  Headers: X-API-Key: xxx

Action: Notion - Create Database Item
  Title: SCBE Daily Report - {{zap_meta_human_now}}
  Allow Rate: {{allow_rate}}
  Deny Rate: {{deny_rate}}
  Total: {{total_decisions}}
```

---

## Troubleshooting

### "No new data" in trigger test

1. Generate a test alert:
```bash
curl -X POST https://your-api.com/v1/authorize \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"test","action":"test","target":"test","context":{"sensitivity":0.9}}'
```

2. Wait 30 seconds, test trigger again

### Duplicate alerts

Make sure to add the acknowledge step after your notification action.

### Rate limiting

Zapier polls every 1-15 minutes. For real-time alerts, consider:
- Upgrading to Zapier premium (instant triggers)
- Using SCBE webhooks directly (coming soon)

---

## See Also

- [Firebase Setup](firebase-setup.md) - Required for persistence
- [API Reference](../02-technical/api-reference.md) - Full endpoint docs
