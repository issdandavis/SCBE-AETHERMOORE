# Command Patterns

## MCP setup (project)

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
Remove-Item .mcp.json -Force
$repo = "C:\Users\issda\SCBE-AETHERMOORE"
claude mcp add fs --scope project -- cmd /c npx -y @modelcontextprotocol/server-filesystem "$repo"
claude mcp add fetch --scope project -- cmd /c npx -y @modelcontextprotocol/server-fetch
Get-Content .mcp.json
```

## AetherBrowse local service

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
.\scripts\run_aetherbrowse_service.ps1 -SCBEKey "0123456789abcdef0123456789abcdef" -Port 8001 -KillOnPortInUse
```

## Health and browse test (separate shell)

```powershell
$headers = @{ "X-API-Key" = "0123456789abcdef0123456789abcdef"; "Content-Type" = "application/json" }
$body = '{"actions":[{"action":"navigate","target":"https://example.com","timeout_ms":10000},{"action":"screenshot","target":"full_page","timeout_ms":12000}],"session_id":"test-session-1"}'
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8001/health"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8001/v1/integrations/n8n/browse" -Headers $headers -Body $body
```

## PR merge flow when dirty

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
git status --short
git fetch origin main
git merge origin/main
git push origin feat/aetherbrowse-v0.1
gh pr merge 210 --merge --repo issdandavis/SCBE-AETHERMOORE
```
