# colab-status.ps1
# One-screen status for your AI training pipeline:
#   - Recent HF uploads (datasets + model repos under issdandavis)
#   - Last few agent-bus events
#   - Local dev environment health
#
# Usage:  .\colab-status.ps1

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "===== SCBE TRAINING STATUS =====" -ForegroundColor Cyan
Write-Host ""

# --- HF account state ---
Write-Host "[HuggingFace]" -ForegroundColor Yellow
$token = $env:HF_TOKEN
if (-not $token) {
    Write-Host "  HF_TOKEN: not set" -ForegroundColor Red
} else {
    Write-Host "  HF_TOKEN: set ($($token.Substring(0,6))...)" -ForegroundColor Green
    $venvPython = "$env:USERPROFILE\dev\SCBE-AETHERMOORE\.venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        $py = @'
from huggingface_hub import HfApi
import os
api = HfApi(token=os.getenv("HF_TOKEN"))
me = api.whoami()
print("  account: " + me.get("name", "?"))
models = list(api.list_models(author=me["name"], limit=5, sort="lastModified"))
print("  recent models (" + str(len(models)) + " of latest):")
for m in models[:5]:
    last = getattr(m, "last_modified", None) or getattr(m, "lastModified", "?")
    mid = getattr(m, "modelId", None) or getattr(m, "id", "?")
    print("    " + str(mid) + " (updated " + str(last) + ")")
datasets = list(api.list_datasets(author=me["name"], limit=5, sort="lastModified"))
print("  recent datasets (" + str(len(datasets)) + " of latest):")
for d in datasets[:5]:
    last = getattr(d, "last_modified", None) or getattr(d, "lastModified", "?")
    print("    " + str(d.id) + " (updated " + str(last) + ")")
'@
        $tmp = [System.IO.Path]::GetTempFileName() + ".py"
        $py | Set-Content -Path $tmp -Encoding utf8
        & $venvPython $tmp 2>&1
        Remove-Item $tmp -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "[Agent Bus events.jsonl - last 5]" -ForegroundColor Yellow
$events = "$env:USERPROFILE\dev\SCBE-AETHERMOORE\artifacts\agent-bus\events.jsonl"
if (Test-Path $events) {
    Get-Content $events -Tail 5 | ForEach-Object {
        try {
            $e = $_ | ConvertFrom-Json
            $when = if ($e.timestamp) { $e.timestamp.Substring(0, 19) } else { "?" }
            $tt   = if ($e.task_type)  { $e.task_type } else { "?" }
            $ok   = if ($e.success)    { "OK"  } else { "FAIL" }
            Write-Host ("  {0}  {1,-20} {2}" -f $when, $tt, $ok)
        } catch {
            Write-Host "  (unparseable line)" -ForegroundColor DarkGray
        }
    }
} else {
    Write-Host "  no events.jsonl yet" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "[Local dev env]" -ForegroundColor Yellow
$venv = "$env:USERPROFILE\dev\SCBE-AETHERMOORE\.venv\Scripts\python.exe"
if (Test-Path $venv) {
    $pyver = & $venv --version 2>&1
    Write-Host "  venv python: $pyver" -ForegroundColor Green
    $count = (& $venv -m pip list 2>&1 | Measure-Object -Line).Lines
    Write-Host "  venv packages: $count"
} else {
    Write-Host "  venv: NOT FOUND" -ForegroundColor Red
}

$ollamaUp = $false
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
    $ollamaUp = $r.StatusCode -eq 200
} catch {}
if ($ollamaUp) {
    Write-Host "  ollama: running" -ForegroundColor Green
} else {
    Write-Host "  ollama: not running" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Done." -ForegroundColor Cyan
