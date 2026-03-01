param(
    [string]$Profile = "colab_local",
    [int]$Port = 8888,
    [string]$Token = "scbe-local-bridge",
    [string]$NotebookDir = "C:\Users\issda",
    [string]$Python = "python"
)

$base = "C:\Users\issda\SCBE-AETHERMOORE"
$bridgeScript = Join-Path $base 'skills\clawhub\scbe-colab-n8n-bridge\scripts\activate_colab_runtime.ps1'

if (-not (Test-Path $bridgeScript)) {
    throw "activate_colab_runtime.ps1 not found: $bridgeScript"
}

pwsh -NoProfile -ExecutionPolicy Bypass -File $bridgeScript `
    -Profile $Profile `
    -Port $Port `
    -Token $Token `
    -NotebookDir $NotebookDir `
    -Python $Python
