---
name: start-aetherbrowse
description: Launch the AetherBrowse runtime server and optionally the Playwright worker
argument-hint: "[--full] [--worker-only]"
allowed-tools:
  - Bash
  - Read
---

Launch the AetherBrowse governed browser stack. By default, start only the agent runtime server. Use `--full` to also start the Playwright worker, or `--worker-only` to start just the worker.

## Instructions

1. Read the current working directory and confirm we are in the SCBE-AETHERMOORE repo.

2. Check if the runtime is already running:
   ```bash
   curl -s http://127.0.0.1:8400/health 2>/dev/null
   ```

3. If the user passed `--worker-only`, skip to step 5.

4. Start the agent runtime in background:
   ```bash
   cd C:\Users\issda\SCBE-AETHERMOORE && python -m uvicorn aetherbrowse.runtime.server:app --host 127.0.0.1 --port 8400 &
   ```
   Wait 3 seconds, then verify with the health endpoint.

5. If the user passed `--full` or `--worker-only`, start the Playwright worker:
   ```bash
   cd C:\Users\issda\SCBE-AETHERMOORE && python aetherbrowse/worker/browser_worker.py &
   ```

6. Report the stack status by hitting `http://127.0.0.1:8400/health` and `http://127.0.0.1:8400/api/status`.

7. Show the user the available endpoints:
   - Landing: http://127.0.0.1:8400/landing
   - Search: http://127.0.0.1:8400/search
   - Dashboard: http://127.0.0.1:8400/home
   - Health: http://127.0.0.1:8400/health
   - Hydra Armor: http://127.0.0.1:8400/v1/armor/health
