param(
    [string]$SCBEKey = "0123456789abcdef0123456789abcdef",
    [string]$TrainingRunDir = "",
    [string]$JobsFile = "examples/aetherbrowse_tasks.sample.json",
    [int]$Port = 8001
)

$ErrorActionPreference = "Stop"

$env:SCBE_API_KEY = $SCBEKey
$env:N8N_API_KEY = $SCBEKey
$env:SCBE_BROWSER_WEBHOOK_URL = "http://127.0.0.1:$Port/v1/integrations/n8n/browse"

$proc = Start-Process -FilePath python -ArgumentList "-m uvicorn agents.browser.main:app --host 127.0.0.1 --port $Port" -PassThru

try {
    $healthy = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 600
        try {
            $h = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3
            if ($h.status -eq "healthy") {
                $healthy = $true
                break
            }
        } catch {}
    }
    if (-not $healthy) {
        throw "AetherBrowse service did not become healthy."
    }

    $argsList = @(
        "scripts/build_evidence_pack.py",
        "--api-key", $SCBEKey,
        "--jobs-file", $JobsFile
    )
    if (-not [string]::IsNullOrWhiteSpace($TrainingRunDir)) {
        $argsList += @("--training-run-dir", $TrainingRunDir)
    }
    python @argsList
    if ($LASTEXITCODE -ne 0) {
        throw "Evidence pack build failed."
    }
    Write-Host ""
    Write-Host "DONE: evidence pack created under artifacts/evidence_packs/" -ForegroundColor Green
}
finally {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
}

