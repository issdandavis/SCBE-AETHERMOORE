param(
    [switch]$CleanStale,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

function Get-CommandLine {
    param([Parameter(Mandatory = $true)]$Process)
    if ($null -eq $Process.CommandLine) {
        return ""
    }
    $line = $Process.CommandLine
    $line = $line -replace 'Authorization:\s*Bearer\s+[^"\s^]+', 'Authorization: Bearer <redacted>'
    $line = $line -replace 'KGAT_[A-Za-z0-9_]+', 'KGAT_<redacted>'
    $line = $line -replace 'github_pat_[A-Za-z0-9_]+', 'github_pat_<redacted>'
    $line = $line -replace 'hf_[A-Za-z0-9_]+', 'hf_<redacted>'
    return $line
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

    if ($p.Name -eq "OpenConsole.exe" -and $cmd -match '\s-Embedding\b') {
        $records.Add((New-GhostRecord $p "windows-terminal-embedding" "Usually spawned by a hidden scheduled/background console task. Check matching run time in scheduled tasks."))
        continue
    }

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

try {
    $tasks = Get-ScheduledTask | Where-Object {
        $_.Actions.Execute -match 'powershell|pwsh|cmd|python|pythonw' -or
        $_.TaskName -match 'SCBE|Aether|Codex|Claude|Agent'
    }
    foreach ($task in $tasks) {
        foreach ($action in $task.Actions) {
            $target = $null
            if ($action.Arguments -match '-File\s+"([^"]+)"') {
                $target = $Matches[1]
            } elseif ($action.Arguments -match '-File\s+([^\s]+)') {
                $target = $Matches[1]
            } elseif ($action.Execute -match 'pythonw?(\.exe)?$' -and $action.Arguments -match '^"([^"]+)"') {
                $target = $Matches[1]
            }

            if ($target -and -not (Test-Path -LiteralPath $target)) {
                $category = "broken-scheduled-task"
                $recommendedAction = "Disable or repoint this task; missing script can flash blank terminal windows."
                if ($task.State -eq "Disabled") {
                    $category = "broken-disabled-scheduled-task"
                    $recommendedAction = "Already disabled; repoint or delete later if this task is no longer needed."
                }
                $records.Add([pscustomobject]@{
                    Pid = "-"
                    ParentPid = "-"
                    Name = $task.TaskName
                    Category = $category
                    RecommendedAction = $recommendedAction
                    State = [string]$task.State
                    CommandLine = "$($action.Execute) $($action.Arguments)"
                })
            }
        }
    }
} catch {
    Write-Warning "Scheduled-task audit skipped: $($_.Exception.Message)"
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

if ($Json) {
    $rows = @($records | Sort-Object Category, Pid)
    [pscustomobject]@{
        schema_version = "scbe_ghost_terminal_audit_v1"
        generated_at = (Get-Date).ToString("o")
        clean_stale_requested = [bool]$CleanStale
        total_records = $rows.Count
        categories = @($rows | Group-Object Category | ForEach-Object {
            [pscustomobject]@{
                category = $_.Name
                count = $_.Count
            }
        })
        records = $rows
    } | ConvertTo-Json -Depth 6
    return
}

$records |
    Sort-Object Category, Pid |
    Format-Table -AutoSize Pid, ParentPid, Name, Category, RecommendedAction

Write-Host ""
Write-Host "Tip: rerun with -CleanStale to stop only stale Codespaces auth windows and port-8765 smoke servers."
