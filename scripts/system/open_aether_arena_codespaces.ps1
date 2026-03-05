param(
    [int]$Port = 4173,
    [switch]$OpenCodespaces,
    [switch]$Fullscreen,
    [switch]$KillOnPortInUse
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-ListeningPids {
    param([int]$TargetPort)
    $conns = Get-NetTCPConnection -State Listen -LocalPort $TargetPort -ErrorAction SilentlyContinue
    if (-not $conns) { return @() }
    return @($conns | Select-Object -ExpandProperty OwningProcess -Unique)
}

function Wait-UrlReady {
    param(
        [string]$Url,
        [int]$Retries = 20
    )
    for ($i = 0; $i -lt $Retries; $i++) {
        Start-Sleep -Milliseconds 300
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop | Out-Null
            return $true
        } catch {
        }
    }
    return $false
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
$publicDir = Join-Path $repoRoot "public"

if (-not (Test-Path $publicDir)) {
    throw "Public directory not found: $publicDir"
}

$existingPids = @(Get-ListeningPids -TargetPort $Port)
if ($existingPids.Count -gt 0 -and -not $KillOnPortInUse) {
    Write-Host "Using existing server on port $Port (PID(s): $($existingPids -join ', '))." -ForegroundColor Yellow
} elseif ($existingPids.Count -gt 0 -and $KillOnPortInUse) {
    foreach ($procId in $existingPids) {
        if ($procId -and (Get-Process -Id $procId -ErrorAction SilentlyContinue)) {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Milliseconds 500
}

$serverPid = $null
if (@(Get-ListeningPids -TargetPort $Port).Count -eq 0) {
    $serverProc = Start-Process -FilePath "python" `
        -ArgumentList @("-m", "http.server", "$Port", "--directory", $publicDir) `
        -WindowStyle Hidden `
        -PassThru
    $serverPid = $serverProc.Id
}

$arenaUrl = "http://127.0.0.1:$Port/arena.html"
if (-not (Wait-UrlReady -Url $arenaUrl)) {
    throw "Arena page failed to start at $arenaUrl"
}

$edgePath = Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe"
if (Test-Path $edgePath) {
    $edgeArgs = @("--new-window")
    if ($Fullscreen) {
        $edgeArgs += "--start-fullscreen"
    }
    $edgeArgs += $arenaUrl
    Start-Process -FilePath $edgePath -ArgumentList $edgeArgs | Out-Null
} else {
    Start-Process $arenaUrl | Out-Null
}

if ($OpenCodespaces) {
    Start-Process "https://github.com/codespaces" | Out-Null
}

Write-Host "Aether Arena is open: $arenaUrl" -ForegroundColor Green
if ($serverPid) {
    Write-Host "Started local server PID: $serverPid" -ForegroundColor DarkGray
}
if ($OpenCodespaces) {
    Write-Host "Opened GitHub Codespaces in browser." -ForegroundColor Cyan
}
