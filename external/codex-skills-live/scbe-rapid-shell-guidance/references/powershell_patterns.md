# PowerShell Patterns (SCBE)

## Start browser service (Shell A)

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
$SCBE_KEY="0123456789abcdef0123456789abcdef"
$env:SCBE_API_KEY=$SCBE_KEY
$env:N8N_API_KEY=$SCBE_KEY
python -m uvicorn agents.browser.main:app --host 0.0.0.0 --port 8001
```

## Health check (Shell B)

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8001/health"
```

## Browse test call (Shell B)

```powershell
$SCBE_KEY="0123456789abcdef0123456789abcdef"
$headers=@{ "X-API-Key"=$SCBE_KEY; "Content-Type"="application/json" }
$body='{"actions":[{"action":"navigate","target":"https://example.com","timeout_ms":10000},{"action":"screenshot","target":"full_page","timeout_ms":12000}],"session_id":"test-session-1"}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8001/v1/integrations/n8n/browse" -Headers $headers -Body $body
```

## Clear busy port 8001

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8001 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
```

## Run one-click helper

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
.\scripts\start_aetherbrowse_oneclick.ps1 -SCBEKey "0123456789abcdef0123456789abcdef" -Port 8001 -KillOnPortInUse
```
