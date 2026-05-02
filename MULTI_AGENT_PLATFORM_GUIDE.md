# SCBE Multi-Agent Coding Platform — Setup Guide

## Overview

This platform allows **multiple AI models** (Claude, Gemini, OpenAI, local models, etc.) to collaborate on code development through:

- **HYDRA Orchestration** — 6 specialist agents (Spine + Heads + Ledger)
- **MCP Servers** — Standard protocol for AI-to-AI communication
- **Sacred Tongues Protocol** — 6-language governance framework
- **L13 Risk Gate** — All code changes gated by hyperbolic safety scaling

## Quick Start

### 1. Launch the Platform

```bash
cd c:\Users\ddavi\dev\SCBE-AETHERMOORE
python platform_launcher.py
```

**Output:**

- HYDRA Spine + 6 Specialist Heads start on ports 9000-9005
- MCP servers listen on ports 8000-8003
- Ledger initialized at `artifacts/swarm_ledger.jsonl`
- Config saved to `.scbe_platform_config.json`

### 2. Configure Your AI Models

Update **`.mcp.json`** to route each AI instance to the platform:

```json
{
  "mcpServers": {
    "scbe-governance": {
      "type": "stdio",
      "command": "python",
      "args": ["mcp/scbe_server.py", "--port", "8000"],
      "env": {
        "SCBE_LEDGER": "artifacts/swarm_ledger.jsonl",
        "GOVERNANCE_MODE": "L13"
      }
    },
    "swarm-orchestrator": {
      "type": "stdio",
      "command": "python",
      "args": ["hydra/spine.py", "--mode", "api"]
    },
    "specialist-koscout": {
      "type": "stdio",
      "command": "python",
      "args": ["hydra/head.py", "--tongue", "KO", "--role", "scout"]
    }
  }
}
```

### 3. Multi-Agent Workflow

Each AI gets a **specialized role** (Sacred Tongue):

| Tongue | AI Role | Example Tool  | Task                                         |
| ------ | ------- | ------------- | -------------------------------------------- |
| **KO** | Scout   | Claude Opus   | Understand requirements, plan code structure |
| **AV** | Vision  | Claude Sonnet | Analyze code patterns, find bugs             |
| **RU** | Reader  | Gemini Ultra  | Fetch docs, research libraries               |
| **CA** | Clicker | Local LLM     | Execute tests, run commands                  |
| **UM** | Typer   | OpenAI o1     | Write code, implement features               |
| **DR** | Judge   | Claude Haiku  | Review code, enforce standards               |

### 4. Governance & Safety

**All code changes go through the L13 Risk Gate:**

```
Human Request
    ↓
    KO (Scout) — Plan work
    ↓
    AV (Vision) — Analyze existing code
    ↓
    RU (Reader) — Check documentation
    ↓
    UM (Typer) — Write code
    ↓
    CA (Clicker) — Test changes
    ↓
    DR (Judge) — Review & quality gate
    ↓
    [L13 RISK GATE]
    ↓
    Harmonic Scaling H(d,R) = R^(d²)
    ↓
    ✅ ALLOW (safe) or 🚫 DENY (dangerous)
```

**The L13 gate uses:**

- Hyperbolic distance (Poincaré ball) to measure intent drift
- Sacred Tongues to detect injection attacks in 6 languages
- Byzantine Fault Tolerant consensus (3+ heads must agree)
- Exponential cost scaling for adversarial patterns

## Example: Multi-Agent Code Review

### Scenario: Three Claude instances collaboratively code a feature

```python
# 1. Scout (Claude Opus) reads the request
"Build a user authentication module with rate limiting"

# 2. Vision (Claude Sonnet) analyzes existing auth code
"Current implementation uses bcrypt + JWT. Rate limit = 100/min."

# 3. Reader (Claude + Gemini) fetches relevant docs
"bcrypt best practices, OWASP rate limit guidelines, etc."

# 4. Typer (Claude + OpenAI) writes the feature
"""
async def rate_limited_login(email, password):
    # Check rate limit for email
    # Hash password with bcrypt
    # Generate JWT token
    # Log to ledger
"""

# 5. Clicker executes tests
"Test runs: 47 pass, 0 fail. Coverage: 98%"

# 6. Judge reviews the code
"✓ Follows security patterns
 ✓ Rate limiting implemented
 ✓ No SQL injection vectors
 ✓ Good test coverage"

# 7. L13 Gate evaluates all changes
"Harmonic distance = 0.2 (safe)
 All 6 tongues agree
 ALLOW → Code committed to main"
```

## MCP Server Reference

### `/scbe_core` — Governance Gate

```
Query L13 decision for intent
Evaluate hyperbolic distance H(d,R)
Get risk tier (ALLOW/QUARANTINE/DENY)
```

### `/swarm` — Agent Coordination

```
Get specialist head status
Check ledger records
Submit task to head
Get task result
```

### `/orchestrator` — Task Routing

```
Plan work across 6 heads
Distribute sub-tasks
Coordinate BFT consensus
Route to ledger
```

## Ledger Format

Each action is recorded in `artifacts/swarm_ledger.jsonl`:

```json
{
  "timestamp": "2026-04-30T15:32:10.123Z",
  "type": "code_review",
  "tongue": "UM",
  "role": "Typer",
  "action": "write_code",
  "file": "src/auth.py",
  "lines_changed": 42,
  "intent_hash": "0x7a2c...",
  "hyperbolic_distance": 0.15,
  "decision": "ALLOW",
  "reason": "Safe pattern within bounds",
  "consensus": ["KO", "AV", "RU", "CA", "UM", "DR"]
}
```

## Troubleshooting

**MCP servers not connecting?**

- Ensure `.mcp.json` has correct paths and env vars
- Check that ledger file is writable
- Run `platform_launcher.py` first to start Spine/Heads

**Ledger not recording?**

- Verify `artifacts/` directory exists
- Check file permissions on `artifacts/swarm_ledger.jsonl`
- Look at Spine logs for errors

**A specialist head is slow?**

- That tongue specialist is under load
- Route non-urgent tasks to another tongue
- Check `juggling_scheduler.py` for task conflicts

## Advanced: Custom Specialist Roles

You can add custom agents by extending `hydra/head.py`:

```python
class CustomHead(BaseHead):
    """My custom specialist"""

    async def execute_task(self, task):
        # Custom logic here
        result = await my_custom_logic(task)
        return result
```

Then register in `platform_launcher.py`:

```python
CUSTOM_TONGUES = {
    "XX": {"name": "MyTongue", "role": "custom", "freq": "xyz Hz"}
}
```

## Security Notes

1. **All AI-to-AI communication is gated by L13**
   - Prevents adversarial prompt injection
   - Detects deceptive task routing

2. **Ledger is immutable**
   - Every action is recorded
   - BFT consensus prevents tampering
   - Audit trail for governance review

3. **Hyperbolic geometry scaling**
   - Exponential cost for suspicious patterns
   - Makes attacks computationally infeasible
   - Safety amplification: 2,184,164x at d=6

## For More Info

- **SPEC.md** — Canonical system specification
- **LAYER_INDEX.md** — 14-layer architecture
- **CLAUDE.md** — Development workflow
- **AGENTS.md** — Repository guidelines

---

**Platform Version:** 1.0.0  
**Last Updated:** April 30, 2026  
**Status:** Production Ready
