param(
    [int]$Port = 8500,
    [string]$Host = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

Write-Host "Starting AetherCode from: $repoRoot"
Write-Host "URL: http://$Host`:$Port"

python -m uvicorn --app-dir $repoRoot src.aethercode.gateway:app --host $Host --port $Port
