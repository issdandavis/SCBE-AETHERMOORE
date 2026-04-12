---
name: check-aetherbrowse
description: Health check the AetherBrowse stack — runtime, worker, Hydra Armor, and agent status
allowed-tools:
  - Bash
  - Read
---

Run a comprehensive health check on the AetherBrowse stack and report status.

## Instructions

1. Check runtime health:
   ```bash
   curl -s http://127.0.0.1:8400/health 2>/dev/null || echo '{"error": "runtime not reachable"}'
   ```

2. Check full system status:
   ```bash
   curl -s http://127.0.0.1:8400/api/status 2>/dev/null || echo '{"error": "api not reachable"}'
   ```

3. Check Hydra Armor:
   ```bash
   curl -s http://127.0.0.1:8400/v1/armor/health 2>/dev/null || echo '{"error": "armor not reachable"}'
   ```

4. Check recent runs:
   ```bash
   curl -s "http://127.0.0.1:8400/api/runs/latest?limit=3" 2>/dev/null || echo '{"error": "runs api not reachable"}'
   ```

5. Present a clear status summary:
   - Runtime: UP/DOWN
   - Electron connected: YES/NO
   - Playwright worker connected: YES/NO
   - Hydra Armor: OctoArmor available YES/NO, SCBE governance YES/NO
   - Agent statuses (Zara, Kael, Aria, Polly)
   - Recent run count and last run status

6. If anything is down, suggest the fix (e.g., "Run `/start-aetherbrowse` to launch the runtime").
