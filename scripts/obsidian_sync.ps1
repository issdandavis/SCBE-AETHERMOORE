# obsidian_sync.ps1 — Auto-sync agent state to Obsidian cross-talk files
# Usage:
#   .\scripts\obsidian_sync.ps1 -Agent claude -Action "Built AetherNet dashboard" -Status "active"
#   .\scripts\obsidian_sync.ps1 -Agent codex -Action "Added auth middleware" -Status "active"
#   .\scripts\obsidian_sync.ps1 -PostTask -Title "Deploy to Cloud Run" -Priority high -Agent any -Context "FastAPI on 8300"
#   .\scripts\obsidian_sync.ps1 -Complete -TaskID "task-1772323500" -Agent claude

param(
    [string]$Agent = "",
    [string]$Action = "",
    [string]$Status = "active",
    [switch]$PostTask,
    [string]$Title = "",
    [string]$Priority = "medium",
    [string]$Context = "",
    [switch]$Complete,
    [string]$TaskID = "",
    [switch]$ShowStatus
)

$VaultPath = "C:\Users\issda\OneDrive\Dropbox\Izack Realmforge\AI Workspace"
$InboxPath = Join-Path $VaultPath "_inbox.md"
$CompletedPath = Join-Path $VaultPath "_completed.md"
$ActivePath = Join-Path $VaultPath "_active_tasks.md"
$Now = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
$NowShort = Get-Date -Format "yyyy-MM-dd HH:mm"

# --- Update agent profile ---
if ($Agent -and $Action -and -not $PostTask -and -not $Complete) {
    $AgentFile = Join-Path $VaultPath "agents\$Agent.md"
    if (Test-Path $AgentFile) {
        $content = Get-Content $AgentFile -Raw
        # Update last active timestamp
        $content = $content -replace '(?m)^- \*\*Last active\*\*:.*$', "- **Last active**: $Now"
        # Update status
        $content = $content -replace '(?m)^- \*\*Status\*\*:.*$', "- **Status**: $Status"
        # Update working on
        $content = $content -replace '(?m)^- \*\*Working on\*\*:.*$', "- **Working on**: $Action"
        Set-Content $AgentFile $content -NoNewline
        Write-Host "[OK] Updated $Agent profile: $Action" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Agent file not found: $AgentFile" -ForegroundColor Yellow
    }
}

# --- Post a new task to inbox ---
if ($PostTask -and $Title) {
    $TaskTimestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $TaskEntry = @"

---

## Task: $Title
- **ID**: task-$TaskTimestamp
- **Posted by**: $($Agent ? $Agent : "system")
- **Priority**: $Priority
- **Suggested agent**: $($Agent ? "any" : "any")
- **Posted at**: $Now
- **Context**: $Context
"@
    Add-Content $InboxPath $TaskEntry
    Write-Host "[OK] Posted task: $Title (task-$TaskTimestamp)" -ForegroundColor Green
}

# --- Mark task as completed ---
if ($Complete -and $TaskID) {
    # Move from inbox to completed
    $inbox = Get-Content $InboxPath -Raw
    if ($inbox -match "(?s)(## Task:.*?$TaskID.*?)(?=---|\z)") {
        $taskBlock = $Matches[1].Trim()
        $completedEntry = @"

---

$taskBlock
- **Completed by**: $($Agent ? $Agent : "unknown")
- **Completed at**: $Now
"@
        Add-Content $CompletedPath $completedEntry
        Write-Host "[OK] Moved task $TaskID to completed" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Task $TaskID not found in inbox" -ForegroundColor Yellow
    }
}

# --- Show current status ---
if ($ShowStatus) {
    Write-Host "`n=== Agent Status ===" -ForegroundColor Cyan
    Get-ChildItem (Join-Path $VaultPath "agents\*.md") | ForEach-Object {
        $name = $_.BaseName
        $content = Get-Content $_.FullName -Raw
        if ($content -match '(?m)^- \*\*Status\*\*:\s*(.+)$') { $st = $Matches[1] } else { $st = "?" }
        if ($content -match '(?m)^- \*\*Working on\*\*:\s*(.+)$') { $work = $Matches[1] } else { $work = "?" }
        if ($content -match '(?m)^- \*\*Last active\*\*:\s*(.+)$') { $la = $Matches[1] } else { $la = "?" }
        Write-Host "  $($name.PadRight(12)) [$st] $work (last: $la)" -ForegroundColor White
    }

    Write-Host "`n=== Inbox Tasks ===" -ForegroundColor Cyan
    $inbox = Get-Content $InboxPath -Raw
    $tasks = [regex]::Matches($inbox, '## Task:\s*(.+)')
    foreach ($t in $tasks) {
        Write-Host "  - $($t.Groups[1].Value)" -ForegroundColor White
    }

    Write-Host "`n=== Services ===" -ForegroundColor Cyan
    @(
        @{Name="AetherNet"; Port=8300},
        @{Name="PollyPad IDE"; Port=8200},
        @{Name="SCBE Bridge"; Port=8001},
        @{Name="n8n"; Port=5678}
    ) | ForEach-Object {
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:$($_.Port)/" -TimeoutSec 2 -ErrorAction Stop
            Write-Host "  $($_.Name.PadRight(20)) :$($_.Port)  UP" -ForegroundColor Green
        } catch {
            Write-Host "  $($_.Name.PadRight(20)) :$($_.Port)  DOWN" -ForegroundColor Red
        }
    }
}
