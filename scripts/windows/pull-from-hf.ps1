# pull-from-hf.ps1
# Pull a trained model artifact from HuggingFace back to this PC.
# Usage:
#   .\pull-from-hf.ps1                                 # pulls default model
#   .\pull-from-hf.ps1 -Repo "issdandavis/my-model"    # custom repo
#   .\pull-from-hf.ps1 -Repo "issdandavis/my-model" -Dest "C:\models\my-model"

param(
    [string]$Repo = "issdandavis/scbe-aethermoore-coding-agent",
    [string]$Dest = "$env:USERPROFILE\dev\hf-models"
)

$token = $env:HF_TOKEN
if (-not $token) {
    Write-Host "HF_TOKEN not set. Run ~\setup-hf-token.ps1 first." -ForegroundColor Red
    exit 1
}

$venvPython = "$env:USERPROFILE\dev\SCBE-AETHERMOORE\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "venv python not found at $venvPython" -ForegroundColor Red
    exit 1
}

$repoLeaf = ($Repo -split "/")[-1]
$target = Join-Path $Dest $repoLeaf
New-Item -ItemType Directory -Path $target -Force | Out-Null

Write-Host "Pulling $Repo → $target" -ForegroundColor Cyan

& $venvPython -c @"
from huggingface_hub import snapshot_download
import os
path = snapshot_download(
    repo_id='$Repo',
    local_dir=r'$target',
    token=os.getenv('HF_TOKEN'),
)
print(f'pulled to {path}')
"@

if ($LASTEXITCODE -eq 0) {
    Write-Host "Done. Model at: $target" -ForegroundColor Green
    # Log to events.jsonl so the agent bus sees it
    $logDir = "$env:USERPROFILE\dev\SCBE-AETHERMOORE\artifacts\agent-bus"
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    $event = @{
        task_type = "hf_model_pull"
        query = $Repo
        success = $true
        timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
        sources_used = 1
        llm_provider = "huggingface"
        llm_model = $Repo
    } | ConvertTo-Json -Compress
    Add-Content -Path "$logDir\events.jsonl" -Value $event -Encoding utf8
    Write-Host "Logged to events.jsonl" -ForegroundColor Gray
} else {
    Write-Host "Pull failed (exit $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}
