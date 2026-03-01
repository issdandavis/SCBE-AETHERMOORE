param(
    [string]$Profile = "colab_local",
    [int]$Port = 8888,
    [string]$Token = "",
    [string]$NotebookDir = "C:\Users\issda",
    [string]$Python = "python",
    [switch]$NoRegister
)

$ErrorActionPreference = "Stop"

$bridgeScript = Join-Path $PSScriptRoot "colab_n8n_bridge.py"
if (-not (Test-Path $bridgeScript)) {
    throw "Bridge script not found: $bridgeScript"
}

if (-not $Token) {
    $Token = "scbe-" + ([guid]::NewGuid().ToString("N").Substring(0, 16))
}

function Stop-Existing-ColabPort {
    param([int]$Port)
    $listeners = Get-NetTCPConnection -State Listen -LocalAddress 127.0.0.1,:: -LocalPort $Port -ErrorAction SilentlyContinue
    if (-not $listeners) {
        return
    }
    $colabPids = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($colabPid in $colabPids) {
        try {
            Stop-Process -Id $colabPid -Force -ErrorAction SilentlyContinue
        } catch {
            # ignore
        }
    }
    Start-Sleep -Milliseconds 500
}

Stop-Existing-ColabPort -Port $Port

$args = @(
    "-m", "notebook",
    "--NotebookApp.allow_origin=https://colab.research.google.com",
    "--NotebookApp.allow_credentials=True",
    "--no-browser",
    "--port=$Port",
    "--NotebookApp.port_retries=0",
    "--NotebookApp.token=$Token",
    "--notebook-dir=$NotebookDir"
)

$proc = Start-Process -FilePath $Python -ArgumentList $args -WindowStyle Hidden -PassThru
$backendBase = "http://127.0.0.1:$Port"
$backendWithToken = "$backendBase/?token=$Token"

$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 250
    try {
        $conn = Get-NetTCPConnection -State Listen -LocalAddress 127.0.0.1 -LocalPort $Port -ErrorAction SilentlyContinue
        if ($conn) {
            $ready = $true
            break
        }
    } catch {
        # continue
    }
}
if (-not $ready) {
    throw "Jupyter did not bind port $Port in time."
}

Write-Host "COLAB_RUNTIME_PID=$($proc.Id)"
Write-Host "COLAB_BACKEND_URL=$backendBase"
Write-Host "COLAB_BACKEND_URL_WITH_TOKEN=$backendWithToken"

if (-not $NoRegister) {
    & $Python $bridgeScript --set --name $Profile --backend-url $backendWithToken --check | Out-Host
    Write-Host "BRIDGE_PROFILE=$Profile"
    & $Python $bridgeScript --env --name $Profile --shell pwsh | Out-Host
}

Write-Host "RUNNING"
