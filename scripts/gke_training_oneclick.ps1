param(
    [switch]$DryRun,
    [switch]$Suspend,
    [switch]$Resume,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$manifest = Join-Path $repoRoot "k8s/training/node-fleet-gke-automation.yaml"
$namespace = "scbe-training"

if (-not (Test-Path $manifest)) {
    throw "Manifest missing: $manifest"
}

function Invoke-Step {
    param([string]$Command)
    if ($DryRun) {
        Write-Host "[dry-run] $Command"
    } else {
        Invoke-Expression $Command
    }
}

function Set-Suspend {
    param([bool]$Value)
    $payload = "{""spec"":{""suspend"":$($Value.ToString().ToLower())}}"
    Invoke-Step "kubectl -n $namespace patch cronjob codex-ingest-daily -p '$payload'"
    Invoke-Step "kubectl -n $namespace patch cronjob node-fleet-train-6h -p '$payload'"
}

if ($Suspend) {
    Set-Suspend -Value $true
    exit 0
}

if ($Resume) {
    Set-Suspend -Value $false
    exit 0
}

if ($Uninstall) {
    Invoke-Step "kubectl delete -f `"$manifest`""
    exit 0
}

if (-not $env:HF_TOKEN -or -not $env:NOTION_TOKEN) {
    throw "HF_TOKEN and NOTION_TOKEN must be set for deploy mode."
}

Invoke-Step "kubectl create namespace $namespace --dry-run=client -o yaml | kubectl apply -f -"
Invoke-Step "kubectl -n $namespace create secret generic hf-secrets --from-literal=token=`"$($env:HF_TOKEN)`" --dry-run=client -o yaml | kubectl apply -f -"
Invoke-Step "kubectl -n $namespace create secret generic notion-secrets --from-literal=token=`"$($env:NOTION_TOKEN)`" --dry-run=client -o yaml | kubectl apply -f -"
Invoke-Step "kubectl apply -f `"$manifest`""
Invoke-Step "kubectl -n $namespace get cronjobs"

Write-Host "GKE training automation deploy complete."

