param(
    [string]$LanIp = "",
    [int]$GatewayPort = 8400,
    [int]$WebPort = 8088,
    [switch]$UseRemoteApi,
    [string]$RemoteApiBase = "https://34.134.99.90:8001",
    [bool]$AllowGatewayFallback = $true,
    [switch]$KillOnPortInUse
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-PreferredLanIp {
    $route = Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue |
        Sort-Object RouteMetric |
        Select-Object -First 1

    if ($route) {
        $ip = Get-NetIPAddress -InterfaceIndex $route.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object {
                $_.IPAddress -notlike "127.*" -and
                $_.IPAddress -notlike "169.254.*"
            } |
            Select-Object -ExpandProperty IPAddress -First 1
        if ($ip) { return $ip }
    }

    $fallback = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike "127.*" -and
            $_.IPAddress -notlike "169.254.*"
        } |
        Select-Object -ExpandProperty IPAddress -First 1
    if ($fallback) { return $fallback }

    throw "Unable to determine LAN IP. Pass -LanIp manually."
}

function Get-ListeningPids {
    param([int]$Port)
    $conns = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if (-not $conns) { return @() }
    return @($conns | Select-Object -ExpandProperty OwningProcess -Unique)
}

function Ensure-PortFree {
    param(
        [int]$Port,
        [string]$Label
    )
    $pids = @(Get-ListeningPids -Port $Port)
    if ($pids.Count -gt 0 -and -not $KillOnPortInUse) {
        throw "$Label port $Port is busy (PID(s): $($pids -join ', ')). Re-run with -KillOnPortInUse."
    }
    foreach ($procId in $pids) {
        if (Get-Process -Id $procId -ErrorAction SilentlyContinue) {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
    if ($pids.Count -gt 0) { Start-Sleep -Milliseconds 600 }
}

function Wait-HttpOk {
    param(
        [string]$Url,
        [string]$Name,
        [int]$Retries = 60
    )
    for ($i = 0; $i -lt $Retries; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 3 -ErrorAction Stop | Out-Null
            return
        } catch {
        }
    }
    throw "$Name not ready at $Url"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
$pidDir = Join-Path $repoRoot "artifacts\system"
New-Item -ItemType Directory -Path $pidDir -Force | Out-Null
$pidFile = Join-Path $pidDir "aether_phone_mode_pids.json"

Set-Location $repoRoot

if (-not $LanIp) {
    $LanIp = Get-PreferredLanIp
}

Ensure-PortFree -Port $WebPort -Label "Web"
if (-not $UseRemoteApi) {
    Ensure-PortFree -Port $GatewayPort -Label "Gateway"
}

$started = @()
try {
    if ($UseRemoteApi) {
        $apiBase = $RemoteApiBase
    } else {
        $gatewayProc = Start-Process -FilePath "python" `
            -ArgumentList @("-m", "uvicorn", "src.aethercode.gateway:app", "--host", "0.0.0.0", "--port", "$GatewayPort") `
            -WorkingDirectory $repoRoot `
            -WindowStyle Hidden `
            -PassThru

        $started += [ordered]@{
            name = "gateway"
            pid = $gatewayProc.Id
            url = "http://$LanIp`:$GatewayPort"
        }

        try {
            Wait-HttpOk -Url "http://127.0.0.1:$GatewayPort/health" -Name "Gateway"
            $apiBase = "http://$LanIp`:$GatewayPort"
        } catch {
            if (-not $AllowGatewayFallback) {
                throw
            }
            if ($gatewayProc -and (Get-Process -Id $gatewayProc.Id -ErrorAction SilentlyContinue)) {
                Stop-Process -Id $gatewayProc.Id -Force -ErrorAction SilentlyContinue
            }
            $started = @($started | Where-Object { $_.name -ne "gateway" })
            Write-Warning "Gateway failed to start; falling back to remote API base: $RemoteApiBase"
            $apiBase = $RemoteApiBase
        }
    }

    $env:AETHERCODE_API_BASE = $apiBase
    & node "kindle-app/scripts/copy-pwa-assets.js" | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Asset copy/patch failed."
    }
    Remove-Item Env:AETHERCODE_API_BASE -ErrorAction SilentlyContinue

    $webRoot = Join-Path $repoRoot "kindle-app\www"
    $webServerScript = Join-Path $repoRoot "scripts\system\serve_kindle_www.mjs"
    $webProc = Start-Process -FilePath "node" `
        -ArgumentList @($webServerScript, "--root", $webRoot, "--host", "0.0.0.0", "--port", "$WebPort") `
        -WorkingDirectory $repoRoot `
        -PassThru
    Write-Host "Started web server process PID $($webProc.Id)" -ForegroundColor DarkGray
    Start-Sleep -Milliseconds 800
    if ($webProc.HasExited) {
        throw "Web server process exited immediately (code $($webProc.ExitCode))."
    }

    $started += [ordered]@{
        name = "web"
        pid = $webProc.Id
        url = "http://$LanIp`:$WebPort"
    }
    Wait-HttpOk -Url "http://127.0.0.1:$WebPort/index.html" -Name "Web UI"

    $snapshot = [ordered]@{
        ok = $true
        started_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        repo_root = $repoRoot
        lan_ip = $LanIp
        web_url = "http://$LanIp`:$WebPort/index.html"
        local_url = "http://127.0.0.1:$WebPort/index.html"
        api_base = $apiBase
        use_remote_api = [bool]$UseRemoteApi
        processes = $started
    }
    $snapshot | ConvertTo-Json -Depth 8 | Set-Content -Path $pidFile -Encoding UTF8

    Write-Host "Aether phone mode is live." -ForegroundColor Green
    Write-Host "Open on Kindle/phone: http://$LanIp`:$WebPort/index.html" -ForegroundColor Cyan
    Write-Host "PID snapshot: $pidFile" -ForegroundColor Gray
} catch {
    foreach ($entry in $started) {
        if ($entry.pid -and (Get-Process -Id $entry.pid -ErrorAction SilentlyContinue)) {
            Stop-Process -Id $entry.pid -Force -ErrorAction SilentlyContinue
        }
    }
    throw
}
