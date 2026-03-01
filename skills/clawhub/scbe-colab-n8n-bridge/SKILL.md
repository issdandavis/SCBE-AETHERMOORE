---
name: scbe-colab-n8n-bridge
description: Bridge Colab local notebook connections to SCBE n8n and agent flows with tokenized local secret storage.
version: 1.0.0
metadata:
  openclaw:
    requires:
      env:
        - SCBE_SECRET_STORE_PATH
      bins:
        - python
    primaryEnv: SCBE_SECRET_STORE_PATH
    tags:
      - local-connection
      - n8n
      - obsidian
      - scbe
      - workflow
---

# SCBE Colab Local Connection + n8n Bridge Skill

Use this skill when you need a Colab local connection URL to drive local n8n / governance workflows without exposing API tokens in plain text.

## Inputs

- `--set` stores/refreshes a profile from Colab local connection settings.
- `--status` prints a masked profile summary.
- `--env` prints shell-safe environment exports.
- `--probe` checks `/api` with the stored token.
- `--workflow` emits a JSON payload for downstream n8n webhook posting.

### Colab Local Connection format

Use the backend URL shown by Colab local connection, for example:

```text
http://127.0.0.1:8888/?token=YOUR_TOKEN
```

Trust the notebook author before running local-connection cells. Keep output local.

## Script usage

```powershell
# 1) Save profile from local URL
python skills/clawhub/scbe-colab-n8n-bridge/scripts/colab_n8n_bridge.py `
  --set `
  --name pivot `
  --backend-url "http://127.0.0.1:8888/?token=..."

# 2) Save with explicit token and route to an n8n webhook
python skills/clawhub/scbe-colab-n8n-bridge/scripts/colab_n8n_bridge.py `
  --set `
  --name pivot `
  --backend-url "http://127.0.0.1:8888/" `
  --token "YOUR_TOKEN" `
  --n8n-webhook "http://127.0.0.1:5678/webhook/scbe-pivot" `
  --check

# 3) Export env vars for current shell
python skills/clawhub/scbe-colab-n8n-bridge/scripts/colab_n8n_bridge.py --env --name pivot

# 4) Probe Colab API for the stored profile
python skills/clawhub/scbe-colab-n8n-bridge/scripts/colab_n8n_bridge.py --probe --name pivot

# 5) Build workflow payload for n8n
python skills/clawhub/scbe-colab-n8n-bridge/scripts/colab_n8n_bridge.py `
  --workflow --name pivot --format json
```

### Activate runtime from terminal (recommended workflow)

Run this single command to start local runtime + auto-register it:

```powershell
pwsh -File "skills/clawhub/scbe-colab-n8n-bridge/scripts/activate_colab_runtime.ps1" `
  -Profile colab_local `
  -Port 8888 `
  -Token scbe-local-bridge `
  -NotebookDir "C:\Users\issda"
```

Output includes:
- `COLAB_BACKEND_URL_WITH_TOKEN=http://127.0.0.1:8888/?token=...`
- `COLAB_RUNTIME_PID=...`
- `RUNNING` when fully ready

To run the same setup from a remote script/host, keep the command in a startup task and
connect Colab UI to:

```text
http://127.0.0.1:8888/?token=<printed_token>
```

## Storage behavior

- The script stores profile metadata in `%USERPROFILE%\\.scbe\\colab_n8n_bridge.json`.
- Raw tokens are saved in `src/security/secret_store` using Sacred Tongue encoding (not plain text).
- `status` and `env` show masked token previews only.

## Data contract

Profile metadata keys:

- `backend_url`
- `n8n_webhook`
- `backend_secret_name`
- `token_secret_name`
- `updated_at`

Workflow payload keys:

- `profile`
- `backend_url`
- `n8n_webhook`
- `token` (only with `--reveal-token`)
- `timestamp`

## Notes for Claude/Codex cross-talk

- Keep this file as a handoff artifact and update Obsidian notes when profile names rotate.
- Use a stable profile name (`pivot`, `polly`, `agent_ops`) so other agents can discover it.

### Auto-start setup

#### Install Windows Scheduled Task (recommended)

```powershell
pwsh -ExecutionPolicy Bypass -File "skills/clawhub/scbe-colab-n8n-bridge/scripts/install_colab_bridge_startup_task.ps1"
```

#### Install startup batch only

```powershell
Copy-Item "skills/clawhub/scbe-colab-n8n-bridge/scripts/start_colab_bridge.bat" `
  "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\start_colab_bridge.bat" -Force
```

#### Startup installer options

```powershell
pwsh -ExecutionPolicy Bypass -File "skills/clawhub/scbe-colab-n8n-bridge/scripts/install_colab_bridge_startup_task.ps1" `
  -TaskName "SCBE-Colab-Bridge" `
  -Profile colab_local `
  -Port 8888 `
  -Token "scbe-local-bridge" `
  -NotebookDir "C:\Users\issda"

pwsh -ExecutionPolicy Bypass -File "skills/clawhub/scbe-colab-n8n-bridge/scripts/install_colab_bridge_startup_task.ps1" -UseStartupFolder -NoScheduledTask
```

### Remove auto-start

```powershell
pwsh -ExecutionPolicy Bypass -File "skills/clawhub/scbe-colab-n8n-bridge/scripts/remove_colab_bridge_startup_task.ps1" -TaskName "SCBE-Colab-Bridge" -RemoveStartupBatch
```
