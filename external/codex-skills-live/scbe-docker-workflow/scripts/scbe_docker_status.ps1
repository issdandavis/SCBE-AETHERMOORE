param(
    [string]$RepoPath = "C:\Users\issda\SCBE-AETHERMOORE-working",
    [string[]]$ComposeFiles = @("docker-compose.yml", "docker-compose.api.yml", "docker-compose.unified.yml"),
    [string]$ContainerName = "",
    [int]$LogTail = 200,
    [switch]$InspectStacks,
    [switch]$ShowLogs,
    [switch]$CleanRestart,
    [switch]$NoPortCheck
)

$ErrorActionPreference = "Stop"

function Log-Section([string]$Title) {
    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

function Run-Safe([string]$Label, [scriptblock]$Action) {
    try {
        & $Action
        return $true
    } catch {
        Write-Host "[FAIL] $Label" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor DarkRed
        return $false
    }
}

function Get-ComposeCommand {
    try {
        & docker compose version | Out-Null
        if ($LASTEXITCODE -eq 0) {
            return "docker compose"
        }
    } catch {}

    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        return "docker-compose"
    }

    throw "Neither 'docker compose' nor 'docker-compose' is available."
}

function Invoke-Compose([string]$File, [string]$Command) {
    if ($script:ComposeCommand -eq "docker compose") {
        & docker compose -f $File $Command
    } else {
        & docker-compose -f $File $Command
    }
}

function Test-Http([string]$Name, [string]$Url) {
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -Method GET -TimeoutSec 6
        Write-Host "  $Name => $($resp.StatusCode) $Url" -ForegroundColor Green
    } catch {
        Write-Host "  $Name => FAILED $Url" -ForegroundColor Red
    }
}

$composeCmd = Get-ComposeCommand
$script:ComposeCommand = $composeCmd
Log-Section "Docker Runtime"
$null = Run-Safe "Docker command check" { docker version --format "{{json .}}" | Out-Null }
$null = Run-Safe "Image list (scbe-aethermoore*)" { docker images scbe-aethermoore* --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" }
$null = Run-Safe "Container snapshot" { docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" }

Log-Section "Port and Service Readiness (if enabled)"
if (-not $NoPortCheck) {
    try {
        $ports = @(8000, 8080, 3000)
        foreach ($p in $ports) {
            $listeners = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -eq $p }
            if ($listeners) {
                Write-Host "  :$p => LISTENING" -ForegroundColor Green
            } else {
                Write-Host "  :$p => not listening" -ForegroundColor Yellow
            }
        }
    } catch {
        Write-Host "  Could not read TCP port status in this environment." -ForegroundColor Yellow
    }
} else {
    Write-Host "  Skipped by -NoPortCheck."
}

Log-Section "Compose stack check"
foreach ($file in $ComposeFiles) {
    $filePath = Join-Path $RepoPath $file
    if (-not (Test-Path $filePath)) {
        Write-Host "$file missing in $RepoPath (skipping)." -ForegroundColor DarkYellow
        continue
    }
    Write-Host ""
    Write-Host "Stack file: $file" -ForegroundColor Gray
    if ($InspectStacks) {
        $null = Run-Safe "$file status" { Invoke-Compose $filePath "ps" }
        if ($ShowLogs) {
            $null = Run-Safe "$file logs (tail $LogTail)" {
                Invoke-Compose $filePath "logs --tail $LogTail"
            }
        }
    } else {
        Write-Host "  (use -InspectStacks to run status checks)"
    }
}

Log-Section "Container logs"
if ($ContainerName -ne "") {
    $null = Run-Safe "Logs for $ContainerName" { docker logs --tail $LogTail $ContainerName }
} else {
    Write-Host "  No -ContainerName provided (use -ContainerName '<name>' to inspect logs)."
}

Log-Section "Health probes"
Test-Http "Core API" "http://localhost:8000/v1/health"
Test-Http "Unified gateway" "http://localhost:8080/health"
Test-Http "Demo service" "http://localhost:8080/"

if ($CleanRestart) {
    Log-Section "Clean restart workflow"
    foreach ($file in $ComposeFiles) {
        $filePath = Join-Path $RepoPath $file
        if (-not (Test-Path $filePath)) { continue }
        Write-Host "Restarting compose file: $file" -ForegroundColor Yellow
        $null = Run-Safe "$file down" { Invoke-Compose $filePath "down --volumes --remove-orphans" }
        $null = Run-Safe "$file up (detached)" { Invoke-Compose $filePath "up -d" }
    }
}

Write-Host ""
Write-Host "Result: completed scbe_docker_status.ps1" -ForegroundColor Green
