param(
    [switch]$CleanStale
)

$ErrorActionPreference = "Stop"

function Get-CommandLine {
    param([Parameter(Mandatory = $true)]$Process)
    if ($null -eq $Process.CommandLine) {
        return ""
    }
    return ($Process.CommandLine -replace 'Authorization:\s*Bearer\s+[^"\s]+', 'Authorization: Bearer <redacted>')
}

function New-GhostRecord {
    param(
        [Parameter(Mandatory = $true)]$Process,
        [Parameter(Mandatory = $true)][string]$Category,
        [Parameter(Mandatory = $true)][string]$Action
    )
    [pscustomobject]@{
        Pid = $Process.ProcessId
        ParentPid = $Process.ParentProcessId
        Name = $Process.Name
        Category = $Category
        RecommendedAction = $Action
        CommandLine = Get-CommandLine $Process
    }
}

$processes = Get-CimInstance Win32_Process
$records = New-Object System.Collections.Generic.List[object]
$stalePids = New-Object System.Collections.Generic.List[int]

foreach ($p in $processes) {
    $cmd = Get-CommandLine $p

    if ($cmd -match 'gh auth refresh' -and $cmd -match 'codespace' -and $cmd -match 'NoExit') {
        $records.Add((New-GhostRecord $p "stale-codespaces-auth" "Safe to close after browser/device auth is done."))
        $stalePids.Add([int]$p.ProcessId)
        continue
    }

    if ($cmd -match 'python(\.exe)? -m http\.server 8765') {
        $records.Add((New-GhostRecord $p "stale-local-smoke-server" "Usually safe to stop if no UI smoke test is active."))
        $stalePids.Add([int]$p.ProcessId)
        continue
    }

    if ($cmd -match '@modelcontextprotocol|@playwright/mcp|mcp-remote|@stripe/mcp|context7-mcp') {
        $records.Add((New-GhostRecord $p "agent-mcp-helper" "Leave running while Claude/Codex needs connectors."))
        continue
    }

    if ($cmd -match 'Long-lived PowerShell AST parser|@openai/codex|codex\.exe') {
        $records.Add((New-GhostRecord $p "codex-runtime-helper" "Leave running while Codex is active."))
        continue
    }

    if ($cmd -match 'claude\.exe|ChromeNativeHost|chrome-native-host') {
        $records.Add((New-GhostRecord $p "claude-runtime-helper" "Leave running while Claude/browser integration is active."))
        continue
    }

    if ($cmd -match 'ollama app|ollama\.exe serve') {
        $records.Add((New-GhostRecord $p "ollama-local-model-server" "Leave running if local no-key AI is in use."))
        continue
    }

    if ($cmd -match 'serve_geoseal_harness|uvicorn') {
        $records.Add((New-GhostRecord $p "local-dev-server" "Check whether a demo or harness is using it before stopping."))
        continue
    }
}

if ($CleanStale) {
    foreach ($pid in ($stalePids | Sort-Object -Unique)) {
        try {
            Stop-Process -Id $pid -Force -ErrorAction Stop
            Write-Host "Stopped stale helper PID=$pid"
        } catch {
            Write-Warning "Could not stop PID=${pid}: $($_.Exception.Message)"
        }
    }
}

$records |
    Sort-Object Category, Pid |
    Format-Table -AutoSize Pid, ParentPid, Name, Category, RecommendedAction

Write-Host ""
Write-Host "Tip: rerun with -CleanStale to stop only stale Codespaces auth windows and port-8765 smoke servers."
