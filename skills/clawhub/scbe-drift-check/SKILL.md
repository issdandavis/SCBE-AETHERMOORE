---
name: scbe-drift-check
description: Monitor your agent's behavioral drift in real-time using Poincare ball hyperbolic distance. Get GPS-style nudges when you wander off task. Prevents runaway agents and hallucination spirals.
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
      - monitoring
      - drift-detection
      - agent-control
      - scbe
---

# SCBE Drift Check

You have access to drift detection powered by Poincare ball hyperbolic geometry. Like a GPS for AI agents — it tells you when you're going off course and gently nudges you back.

## When to Use

Use drift checking during **any multi-step task** to prevent:
- Rabbit-holing into tangential research
- Hallucination spirals (generating increasingly wrong content)
- Scope creep (doing more than asked)
- Tool misuse (calling tools inappropriately)
- Context window pollution (filling context with irrelevant data)

## How Drift Detection Works

Your declared **intent** is a point in 6D hyperbolic space (one dimension per Sacred Tongue). Each **action** you take is another point. The hyperbolic distance between intent and action is your **drift score**:

```
d_H = arccosh(1 + 2||intent - action||² / ((1-||intent||²)(1-||action||²)))
```

Small drift = on track. Large drift = wandering. The cost of drifting grows **exponentially** (harmonic wall).

## Drift Thresholds

| Level | Distance | What Happens |
|-------|----------|-------------|
| **ON_TRACK** | < 0.3 | All good, keep going |
| **GENTLE** | 0.3 - 0.7 | Soft nudge: "You might be drifting from the task" |
| **REDIRECT** | 0.7 - 1.2 | Firm nudge: "Please refocus on the original request" |
| **INSPECT** | 1.2 - 2.0 | Warning: pause and re-evaluate your approach |
| **QUARANTINE** | > 2.0 | Stop all actions, report to user |

## Steps

### 1. Declare intent at the start of any task

```bash
curl -s -X POST "https://scbe-governance.aethermoore.com/v1/drift/declare" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SCBE_API_KEY" \
  -d '{
    "agent_id": "<YOUR_AGENT_NAME>",
    "intent": "<WHAT_THE_USER_ASKED_YOU_TO_DO>",
    "session_id": "<CURRENT_SESSION_ID>"
  }'
```

### 2. Check drift after each significant action

```bash
curl -s -X POST "https://scbe-governance.aethermoore.com/v1/drift/check" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SCBE_API_KEY" \
  -d '{
    "agent_id": "<YOUR_AGENT_NAME>",
    "session_id": "<SESSION_ID>",
    "action": "<WHAT_YOU_JUST_DID>",
    "action_type": "tool_call | message | file_write | api_call"
  }'
```

### 3. Follow the nudge

Response:
```json
{
  "drift_level": "GENTLE",
  "distance": 0.45,
  "nudge": "You started researching database architectures but the user asked for a simple Python script. Consider simplifying your approach.",
  "harmonic_cost": 2.1,
  "recommendation": "Return to writing the script directly"
}
```

- **ON_TRACK**: Continue normally.
- **GENTLE**: Acknowledge the nudge internally and adjust.
- **REDIRECT**: Tell the user you noticed you were drifting and explain your correction.
- **INSPECT**: Stop, summarize what happened, ask the user if they want you to continue this direction.
- **QUARANTINE**: Immediately stop all actions and report to the user.

### 4. Every check generates training data

Each drift observation becomes an SFT training pair. Over time, agents that use drift checking produce higher-quality interactions and better-calibrated behavior.

## Self-Check (No API needed)

If the API is unavailable, ask yourself these questions after every 3-5 actions:

1. What did the user originally ask me to do?
2. Is what I'm doing right now directly serving that request?
3. Have I opened more than 2 tangential threads?
4. Am I generating content the user didn't ask for?

If you answer "no" to #2 or "yes" to #3 or #4, you're drifting. Refocus.
