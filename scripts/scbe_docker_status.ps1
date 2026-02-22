[CmdletBinding()]
param(
    [ValidateSet("doctor", "up", "down", "restart", "status", "logs", "health", "build", "clean")]
    [string]$Action = "doctor",

    [ValidateSet("default", "api", "unified", "research", "hydra-remote")]
    [string]$Stack = "api",

    [string]$ContainerName = "",
    [int]$LogTail = 120,
    [switch]$Follow,
    [switch]$NoBuild,
    [switch]$CleanVolumes,
    [switch]$InspectStacks,
    [switch]$ShowLogs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:ProjectRoot = Split-Path -Parent $PSScriptRoot

$stackFiles = @{
    "default"      = "docker-compose.yml"
    "api"          = "docker-compose.api.yml"
    "unified"      = "docker-compose.unified.yml"
    "research"     = "docker-compose.research.yml"
    "hydra-remote" = "docker-compose.hydra-remote.yml"
}

$stackProjects = @{
    "default"      = "scbe-default"
    "api"          = "scbe-api"
    "unified"      = "scbe-unified"
    "research"     = "scbe-research"
    "hydra-remote" = "scbe-hydra-remote"
}

$stackPorts = @{
    "default"      = @(8000, 8080)
    "api"          = @(8080)
    "unified"      = @(8000, 8080, 8081, 9090, 3000, 6379)
    "research"     = @(8000)
    "hydra-remote" = @()
}

$stackHealth = @{
    "default"      = @("http://localhost:8000/health")
    "api"          = @("http://localhost:8080/v1/health")
    "unified"      = @(
        "http://localhost:8000/v1/health",
        "http://localhost:8080/health",
        "http://localhost:9090/-/healthy",
        "http://localhost:8081/health"
    )
    "research"     = @("http://localhost:8000/v1/health")
    "hydra-remote" = @()
}

function Write-Info([string]$Message) {
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "[OK]   $Message" -ForegroundColor Green
}

function Write-WarnMsg([string]$Message) {
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Err([string]$Message) {
    Write-Host "[ERR]  $Message" -ForegroundColor Red
}

function Assert-DockerReady {
    try {
        $null = docker version --format '{{.Server.Version}}' 2>$null
        $null = docker info --format '{{.ServerVersion}}' 2>$null
        Write-Ok "Docker daemon reachable."
    }
    catch {
        throw "Docker daemon is not reachable. Start Docker Desktop/Engine first."
    }
}

function Assert-ComposeReady {
    try {
        $null = docker compose version 2>$null
        Write-Ok "Docker Compose plugin available."
    }
    catch {
        throw "Docker Compose plugin is unavailable."
    }
}

function Get-ComposeFilePath([string]$TargetStack) {
    $file = $stackFiles[$TargetStack]
    if ([string]::IsNullOrWhiteSpace($file)) {
        throw "Unknown stack '$TargetStack'."
    }
    $path = Join-Path $script:ProjectRoot $file
    if (-not (Test-Path $path)) {
        throw "Compose file not found: $path"
    }
    return $path
}

function Get-ProjectName([string]$TargetStack) {
    $name = $stackProjects[$TargetStack]
    if ([string]::IsNullOrWhiteSpace($name)) {
        throw "Project name missing for stack '$TargetStack'."
    }
    return $name
}

function Invoke-Compose([string]$TargetStack, [string[]]$ComposeArgs) {
    $composeFile = Get-ComposeFilePath $TargetStack
    $projectName = Get-ProjectName $TargetStack
    Push-Location $script:ProjectRoot
    try {
        & docker compose -p $projectName -f $composeFile @ComposeArgs
    }
    finally {
        Pop-Location
    }
}

function Test-Ports([string]$TargetStack) {
    $ports = $stackPorts[$TargetStack]
    if ($null -eq $ports -or $ports.Count -eq 0) {
        Write-Info "No host port checks defined for stack '$TargetStack'."
        return
    }

    foreach ($port in $ports) {
        $inUse = (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0
        if ($inUse) {
            Write-WarnMsg "Port $port is already in use."
        }
        else {
            Write-Ok "Port $port is free."
        }
    }
}

function Test-Health([string]$TargetStack) {
    $urls = $stackHealth[$TargetStack]
    if ($null -eq $urls -or $urls.Count -eq 0) {
        Write-Info "No HTTP health endpoints configured for stack '$TargetStack'."
        return
    }

    foreach ($url in $urls) {
        try {
            $resp = Invoke-WebRequest -Uri $url -TimeoutSec 4 -UseBasicParsing
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300) {
                Write-Ok "$url -> $($resp.StatusCode)"
            }
            else {
                Write-WarnMsg "$url -> $($resp.StatusCode)"
            }
        }
        catch {
            Write-WarnMsg "$url -> unreachable"
        }
    }
}

function Run-Doctor([string]$TargetStack) {
    Write-Info "Running Docker doctor for stack '$TargetStack'"
    Assert-DockerReady
    Assert-ComposeReady

    $composePath = Get-ComposeFilePath $TargetStack
    Write-Ok "Compose file found: $composePath"

    Push-Location $script:ProjectRoot
    try {
        $null = docker compose -f $composePath config
        Write-Ok "Compose config is valid."
    }
    finally {
        Pop-Location
    }

    if (Test-Path (Join-Path $script:ProjectRoot ".env")) {
        Write-Ok ".env file present."
    }
    else {
        Write-WarnMsg ".env file missing. Copy from .env.example for predictable runtime settings."
    }

    Test-Ports $TargetStack
    Invoke-Compose $TargetStack @("ps")
    Test-Health $TargetStack

    if ($ShowLogs) {
        Invoke-Compose $TargetStack @("logs", "--tail", [string]$LogTail)
    }
}

function Run-Status([string]$TargetStack) {
    Assert-DockerReady
    Assert-ComposeReady
    Write-Info "Status for stack '$TargetStack'"
    Invoke-Compose $TargetStack @("ps")
    Test-Health $TargetStack
}

function Run-Up([string]$TargetStack) {
    Assert-DockerReady
    Assert-ComposeReady
    Test-Ports $TargetStack
    Write-Info "Starting stack '$TargetStack'"
    $args = @("up", "-d")
    if (-not $NoBuild) {
        $args += "--build"
    }
    Invoke-Compose $TargetStack $args
    Run-Status $TargetStack
}

function Run-Down([string]$TargetStack) {
    Assert-DockerReady
    Assert-ComposeReady
    Write-Info "Stopping stack '$TargetStack'"
    $args = @("down")
    if ($CleanVolumes) {
        $args += "--volumes"
    }
    Invoke-Compose $TargetStack $args
}

function Run-Restart([string]$TargetStack) {
    Run-Down $TargetStack
    Run-Up $TargetStack
}

function Run-Logs([string]$TargetStack) {
    Assert-DockerReady
    if (-not [string]::IsNullOrWhiteSpace($ContainerName)) {
        $args = @("logs", "--tail", [string]$LogTail)
        if ($Follow) {
            $args += "-f"
        }
        $args += $ContainerName
        & docker @args
        return
    }

    Assert-ComposeReady
    $composeArgs = @("logs", "--tail", [string]$LogTail)
    if ($Follow) {
        $composeArgs += "-f"
    }
    Invoke-Compose $TargetStack $composeArgs
}

function Run-Build([string]$TargetStack) {
    Assert-DockerReady
    Assert-ComposeReady
    Write-Info "Building stack '$TargetStack'"
    Invoke-Compose $TargetStack @("build")
}

function Run-Clean() {
    Assert-DockerReady
    Write-WarnMsg "Pruning stopped containers and dangling images..."
    & docker system prune -f
}

if ($InspectStacks) {
    Assert-DockerReady
    Assert-ComposeReady
    foreach ($s in $stackFiles.Keys) {
        Write-Host ""
        Write-Host "==== STACK: $s ====" -ForegroundColor Magenta
        try {
            Run-Status $s
        }
        catch {
            Write-WarnMsg "Failed to inspect stack '$s': $($_.Exception.Message)"
        }
    }
    exit 0
}

switch ($Action) {
    "doctor"  { Run-Doctor $Stack; break }
    "up"      { Run-Up $Stack; break }
    "down"    { Run-Down $Stack; break }
    "restart" { Run-Restart $Stack; break }
    "status"  { Run-Status $Stack; break }
    "logs"    { Run-Logs $Stack; break }
    "health"  { Test-Health $Stack; break }
    "build"   { Run-Build $Stack; break }
    "clean"   { Run-Clean; break }
    default   { throw "Unsupported action '$Action'." }
}
