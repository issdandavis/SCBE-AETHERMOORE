[CmdletBinding()]
param(
    [ValidateSet("doctor", "gateway", "tools", "servers", "tool-count", "tool-inspect", "tool-call", "server-enable", "server-disable")]
    [string]$Action = "doctor",

    [string]$Name = "",
    [string]$ArgsJson = "{}",
    [switch]$VerboseOutput
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Info([string]$Message) {
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "[OK]   $Message" -ForegroundColor Green
}

function Assert-DockerMcpReady {
    try {
        $null = docker version --format '{{.Server.Version}}' 2>$null
        $null = docker mcp --version
        Write-Ok "Docker + MCP CLI are available."
    }
    catch {
        throw "Docker MCP CLI not available. Install/update Docker Desktop MCP Toolkit."
    }
}

function Run-Doctor {
    Assert-DockerMcpReady
    Write-Info "MCP version"
    docker mcp version

    Write-Info "Enabled servers"
    docker mcp server ls

    Write-Info "Tool count"
    docker mcp tools count

    Write-Info "First tools"
    docker mcp tools ls | Select-Object -First 40
}

function Run-Gateway {
    Assert-DockerMcpReady
    Write-Info "Starting Docker MCP gateway (Ctrl+C to stop)"
    docker mcp gateway run
}

function Run-Tools {
    Assert-DockerMcpReady
    if ($VerboseOutput) {
        docker mcp tools ls --verbose
    }
    else {
        docker mcp tools ls
    }
}

function Run-Servers {
    Assert-DockerMcpReady
    docker mcp server ls
}

function Run-ToolCount {
    Assert-DockerMcpReady
    docker mcp tools count
}

function Run-ToolInspect {
    Assert-DockerMcpReady
    if ([string]::IsNullOrWhiteSpace($Name)) {
        throw "Provide -Name for tool inspection (example: browser_navigate)."
    }
    docker mcp tools inspect $Name
}

function Run-ToolCall {
    Assert-DockerMcpReady
    if ([string]::IsNullOrWhiteSpace($Name)) {
        throw "Provide -Name for tool call (example: browser_navigate)."
    }

    $payload = $null
    try {
        $payload = $ArgsJson | ConvertFrom-Json -AsHashtable
    }
    catch {
        throw "ArgsJson must be valid JSON. Received: $ArgsJson"
    }

    $compact = ($payload | ConvertTo-Json -Depth 16 -Compress)
    Write-Info "Calling tool '$Name' with payload: $compact"
    docker mcp tools call $Name $compact
}

function Run-ServerEnable {
    Assert-DockerMcpReady
    if ([string]::IsNullOrWhiteSpace($Name)) {
        throw "Provide -Name for server enable (example: github)."
    }
    docker mcp server enable $Name
}

function Run-ServerDisable {
    Assert-DockerMcpReady
    if ([string]::IsNullOrWhiteSpace($Name)) {
        throw "Provide -Name for server disable (example: github)."
    }
    docker mcp server disable $Name
}

switch ($Action) {
    "doctor"         { Run-Doctor; break }
    "gateway"        { Run-Gateway; break }
    "tools"          { Run-Tools; break }
    "servers"        { Run-Servers; break }
    "tool-count"     { Run-ToolCount; break }
    "tool-inspect"   { Run-ToolInspect; break }
    "tool-call"      { Run-ToolCall; break }
    "server-enable"  { Run-ServerEnable; break }
    "server-disable" { Run-ServerDisable; break }
    default           { throw "Unsupported action '$Action'." }
}
