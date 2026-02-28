# SCBE Multi-Provider Tool Calling (HF + Claude + Grok + OpenAI)

## What this gives you
One SCBE endpoint for all model providers, so Telegram/n8n/Zapier can call:
- Hugging Face (`huggingface`)
- Claude (`anthropic`)
- Grok (`xai`)
- OpenAI/Codex (`openai`)

Endpoint:
- `POST /v1/llm/dispatch`
- `GET /v1/llm/providers`

Bridge file:
- `workflows/n8n/scbe_n8n_bridge.py`

## Required environment variables
Set only the providers you want to use:

```powershell
$env:SCBE_API_KEYS="scbe-dev-key,test-key"
$env:HF_TOKEN="hf_xxx"
$env:ANTHROPIC_API_KEY="sk-ant-xxx"
$env:XAI_API_KEY="xai-xxx"
$env:OPENAI_API_KEY="sk-xxx"
$env:SCBE_ZAPIER_HOOK_URL="https://hooks.zapier.com/hooks/catch/..."
```

Optional model defaults:
```powershell
$env:SCBE_HF_MODEL="Qwen/Qwen2.5-7B-Instruct"
$env:SCBE_ANTHROPIC_MODEL="claude-3-5-sonnet-latest"
$env:SCBE_XAI_MODEL="grok-beta"
$env:SCBE_OPENAI_MODEL="gpt-4o-mini"
```

## Check provider status
```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8001/v1/llm/providers" -Headers @{ "X-API-Key" = "scbe-dev-key" }
```

## Dispatch example (Grok + Zapier callback)
```powershell
$body = @{
  provider = "xai"
  model = "grok-beta"
  messages = @(
    @{ role = "system"; content = "You are SCBE operator AI." },
    @{ role = "user"; content = "Summarize bridge health and suggest next action." }
  )
  route_to_zapier = $true
  metadata = @{ source = "telegram"; workflow = "ops-status" }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8001/v1/llm/dispatch" `
  -Headers @{ "X-API-Key" = "scbe-dev-key" } `
  -ContentType "application/json" `
  -Body $body
```

## Dispatch example (Claude with tool definitions)
```powershell
$body = @{
  provider = "anthropic"
  tools = @(
    @{ name = "get_health"; description = "Read service health"; input_schema = @{ type = "object"; properties = @{} } }
  )
  messages = @(
    @{ role = "user"; content = "Use get_health and report failures." }
  )
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8001/v1/llm/dispatch" `
  -Headers @{ "X-API-Key" = "scbe-dev-key" } `
  -ContentType "application/json" `
  -Body $body
```

## n8n pattern
1. Telegram Trigger node receives command.
2. Set/Code node maps command -> `provider`, `messages`, `tools`.
3. HTTP Request node calls `/v1/llm/dispatch`.
4. IF node handles `tool_calls` branch.
5. Optional HTTP node sends callback to Zapier.
6. Telegram node sends final response.

