# Terminal AI Router Quickstart

Cheap-first multi-provider routing from terminal with daily spend caps.

## 1) Run health + alias sync

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
powershell -ExecutionPolicy Bypass -File .\scripts\system\run_terminal_ai_router.ps1 -Mode health -SyncAliases
```

This syncs key aliases into canonical names when possible:
- `OPENAI_KEY -> OPENAI_API_KEY`
- `CLAUDE_API_KEY -> ANTHROPIC_API_KEY`
- `GROK_API_KEY -> XAI_API_KEY`
- `HUGGINGFACE_TOKEN -> HF_TOKEN`

Health report:
- `artifacts/ai_router/terminal_ai_health.json`

## 2) Route one prompt (cheap-first)

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
powershell -ExecutionPolicy Bypass -File .\scripts\system\run_terminal_ai_router.ps1 -Mode call -Prompt "Create a short launch checklist for today's AI wiki update." -Complexity auto -PrintResponse
```

Call report:
- `artifacts/ai_router/terminal_ai_router_last.json`

Daily spend ledger:
- `artifacts/ai_router/spend_ledger_YYYY-MM-DD.json`

## 3) Tune caps/models

Edit:
- `config/governance/terminal_ai_router_profiles.json`

Adjust:
- provider order
- model per tier (`cheap`, `standard`, `premium`)
- `daily_cap_usd`
- estimated cents per call

## 4) Strict health gate (for automation)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\system\run_terminal_ai_router.ps1 -Mode health -Strict -SyncAliases
```

Exit code is non-zero if any requested provider is not `ok`.
