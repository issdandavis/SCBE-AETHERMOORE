---
name: aetherbrowse-ops
description: Operations guide for AetherBrowse — starting/stopping the stack, managing profiles, monitoring health, viewing governance logs, and troubleshooting. Use when launching AetherBrowse, checking stack health, viewing audit logs, managing browser profiles, or diagnosing connectivity issues between the runtime, worker, and governance services.
---

# AetherBrowse Operations

Use this skill when running, monitoring, or troubleshooting the AetherBrowse stack.

## Quick Start

### Launch the Runtime Server
```bash
# Default (CDP backend, port 8001)
python -m uvicorn agents.browser.main:app --host 0.0.0.0 --port 8001

# With auto-reload for development
python -m uvicorn agents.browser.main:app --reload --host 0.0.0.0 --port 8001
```

### CLI Single Actions
```bash
# Navigate
python agents/aetherbrowse_cli.py navigate https://example.com

# Click
python agents/aetherbrowse_cli.py --backend playwright click "#submit-btn"

# Type into field
python agents/aetherbrowse_cli.py type "#search-input" "query text"

# Screenshot
python agents/aetherbrowse_cli.py screenshot

# Full page screenshot
python agents/aetherbrowse_cli.py screenshot full_page

# Run action script
python agents/aetherbrowse_cli.py run-script actions.json

# Audit-only mode (validate without executing)
python agents/aetherbrowse_cli.py --audit-only navigate https://bank.example.com

# Generate training data
python agents/aetherbrowse_cli.py --training-log training.jsonl navigate https://example.com
```

### Backend Selection
```bash
--backend auto          # Auto-detect best available
--backend cdp           # Chrome DevTools Protocol (fastest, default)
--backend playwright    # Playwright (multi-browser, smart waits)
--backend selenium      # Selenium (legacy)
--backend chrome_mcp    # Model Context Protocol
--backend mock          # Offline testing (no real browser)
```

### Safety Tuning
```bash
--safe-radius 0.92       # Poincaré ball boundary (default 0.92)
--dim 16                 # PHDM embedding dimension (default 16)
--sensitivity-factor 1.0 # Risk sensitivity multiplier (higher = stricter)
```

## Health Check

### API Health Endpoint
```bash
curl http://localhost:8001/health
```

Expected response:
```json
{
  "status": "healthy",
  "components": {
    "phdm_brain": "initialized",
    "vision_embedder": "ready",
    "browser_backend": "connected"
  }
}
```

### Containment Statistics
```bash
curl http://localhost:8001/v1/containment-stats
```

Returns aggregate metrics: total checks, allow/deny/quarantine/escalate counts, average radius, boundary proximity stats.

### Safety Pre-Check (No Execution)
```bash
curl -X POST http://localhost:8001/v1/safety-check \
  -H "Content-Type: application/json" \
  -d '{"action": "navigate", "target": "https://bank.example.com"}'
```

## Governance Logs

### Audit Trail Location
AetherBrowse writes audit records to the session. Access via:
- **CLI**: Use `--training-log <path>` flag → JSONL output
- **API**: Response includes `audit_log` array in every `/v1/browse` response
- **Swarm Hub**: `artifacts/swarm_hub/primary.jsonl` for swarm operations

### Log Record Format
```json
{
  "session_id": "abc123",
  "agent_id": "aetherbrowse-agent",
  "action": "navigate",
  "target": "https://example.com",
  "decision": "ALLOW",
  "radius": 0.234,
  "risk_score": 0.15,
  "violations": [],
  "timestamp": "2026-03-04T12:00:00Z"
}
```

### Viewing Swarm Consensus Logs
```bash
# View recent roundtable decisions
cat artifacts/swarm_hub/primary.jsonl | python -m json.tool

# Filter by decision type
grep '"decision": "DENY"' artifacts/swarm_hub/primary.jsonl

# Count decisions by type
grep -c '"ALLOW"' artifacts/swarm_hub/primary.jsonl
grep -c '"DENY"' artifacts/swarm_hub/primary.jsonl
grep -c '"QUARANTINE"' artifacts/swarm_hub/primary.jsonl
```

## Profile Management

### AetherbrowseSession Configuration
```python
AetherbrowseSessionConfig(
    backend="cdp",          # Browser backend
    host="127.0.0.1",       # Backend host
    port=9222,              # Backend port (CDP default)
    agent_id="aetherbrowse-agent",
    auto_escalate=False,    # Auto-escalate quarantined actions
    safe_radius=0.92,       # Poincaré containment radius
    phdm_dim=16,            # Embedding dimensions
    sensitivity_factor=1.0, # Risk sensitivity
    headless=True,          # Headless browser mode
)
```

### Sensitivity Presets
| Profile       | safe_radius | sensitivity | Use Case                    |
|---------------|-------------|-------------|-----------------------------|
| Permissive    | 0.95        | 0.5         | Internal tools, trusted sites |
| Standard      | 0.92        | 1.0         | General browsing              |
| Strict        | 0.85        | 1.5         | Banking, healthcare           |
| Paranoid      | 0.75        | 2.0         | Government, classified        |

## Common Issues

### "Backend not connected"
1. Check browser is running: `curl http://localhost:9222/json/version` (CDP)
2. Start Chrome with remote debugging: `google-chrome --remote-debugging-port=9222`
3. Or use Playwright backend (manages its own browser): `--backend playwright`

### "PHDM DENY on safe site"
1. Check `--safe-radius` (try increasing to 0.95)
2. Check `--sensitivity-factor` (try decreasing to 0.5)
3. Use `--audit-only` to see the embedding without executing
4. The vision embedder may need recalibration for unfamiliar page layouts

### "Swarm consensus stalled"
1. Check `artifacts/swarm_hub/primary.jsonl` for voting records
2. Look for agents stuck in ESCALATE — may need human approval
3. Reduce quorum requirements if testing (4/6 → 3/6)

### "Mock backend returns empty results"
- Expected behavior: mock backend simulates actions without a real browser
- Use for: audit trail testing, governance policy validation, CI/CD pipelines
- Not for: actual page content, screenshots, DOM extraction

## Docker Deployment

```bash
# Build + run full stack
npm run docker:build && npm run docker:run

# Docker Compose (multi-container)
npm run docker:compose

# Expose ports: 8080 (API) + 3000 (UI) + 8001 (AetherBrowse)
```

## n8n Integration

```bash
# Send actions through n8n webhook bridge
curl -X POST http://localhost:8001/v1/integrations/n8n/browse \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "actions": [{"type": "screenshot"}]}'
```

## Reset Session
```bash
curl -X POST http://localhost:8001/v1/reset-session
```
Clears: browser state, audit trail, context embeddings, DOM snapshots.
