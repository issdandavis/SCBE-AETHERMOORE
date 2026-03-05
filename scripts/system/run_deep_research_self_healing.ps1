param(
    [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$Topic = "post-quantum ai governance",
    [string]$GatewayBaseUrl = "http://127.0.0.1:8000",
    [string]$ApiKey = "",
    [int]$Cycles = 3,
    [switch]$Continuous = $false,
    [int]$SleepSeconds = 60,
    [switch]$UsePlaywriter,
    [switch]$RunCiTriage,
    [switch]$EnableSelfHealing = $true,
    [switch]$EnableOnionRouting = $false
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = $env:SCBE_API_KEY
}
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = $env:N8N_API_KEY
}
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    # Fallback matches the default keys in src/api/main.py _load_api_keys()
    $ApiKey = "demo_key_12345"
}

if ($EnableOnionRouting) {
    throw "Onion/Tor automation is disabled in this workflow. Use manual, approved compliance procedures only."
}

$emitScript = Join-Path $RepoRoot "scripts\system\terminal_crosstalk_emit.ps1"
$watchdogScript = Join-Path $RepoRoot "scripts\system\watchdog_agent_stack_default.ps1"

function Emit-LoopPacket {
    param(
        [string]$TaskId,
        [string]$Summary,
        [string]$Status = "in_progress",
        [string]$NextAction = "",
        [string]$Why = "deep research loop"
    )
    if (Test-Path $emitScript) {
        & $emitScript `
            -TaskId $TaskId `
            -Summary $Summary `
            -Status $Status `
            -NextAction $NextAction `
            -Where "scripts/system/run_deep_research_self_healing.ps1" `
            -Why $Why `
            -How "sense-plan-execute-verify-recover"
    }
}

function Invoke-ArxivLane {
    python "$RepoRoot\scripts\system\browser_chain_dispatcher.py" --domain arxiv.org --task research --engine playwriter
}

function Invoke-PlaywriterEvidence {
    python "$RepoRoot\scripts\system\playwriter_lane_runner.py" --session 1 --task title
    python "$RepoRoot\scripts\system\playwriter_lane_runner.py" --session 1 --task snapshot
}

function Test-GatewayHealth {
    try {
        $resp = Invoke-RestMethod -Method Get -Uri "$GatewayBaseUrl/health" -TimeoutSec 5 -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Invoke-GatewayResearch {
    param([string]$Query)
    # Route: /hydra/research on the main gateway (src/api/main.py includes hydra_router)
    $payload = @{
        query = $Query
        max_subtasks = 5
        discovery_per_subtask = 3
        mode = "httpx"
    } | ConvertTo-Json
    $headers = @{
        "X-API-Key" = $ApiKey
    }
    Invoke-RestMethod -Method Post -Uri "$GatewayBaseUrl/hydra/research" -Headers $headers -ContentType "application/json" -Body $payload
}

function Invoke-CiTriage {
    $ciScript = "C:\Users\issda\.codex\skills\gh-fix-ci\scripts\inspect_pr_checks.py"
    if (Test-Path $ciScript) {
        python $ciScript --repo $RepoRoot
    }
}

if ((-not $Continuous) -and $Cycles -lt 1) {
    throw "Cycles must be >= 1"
}

Write-Host "=== Deep Research Self-Healing Loop ===" -ForegroundColor Cyan
Write-Host "Topic: $Topic"
if ($Continuous) {
    Write-Host "Mode: Continuous | Sleep: ${SleepSeconds}s"
} else {
    Write-Host "Cycles: $Cycles | Sleep: ${SleepSeconds}s"
}

$i = 0
while ($true) {
    $i++
    if ((-not $Continuous) -and ($i -gt $Cycles)) {
        break
    }

    $taskId = "DEEP-RESEARCH-CYCLE-$i"
    Emit-LoopPacket -TaskId $taskId -Summary "Cycle $i started for topic '$Topic'." -Status "in_progress" -NextAction "Run research stages."
    $errors = @()

    try {
        Write-Host "[Cycle $i] Routing arXiv lane..." -ForegroundColor Yellow
        Invoke-ArxivLane | Out-Null
    } catch {
        $errors += "arxiv_lane: $($_.Exception.Message)"
    }

    if (Test-GatewayHealth) {
        try {
            Write-Host "[Cycle $i] Running gateway web research..." -ForegroundColor Yellow
            $result = Invoke-GatewayResearch -Query $Topic
            $outDir = Join-Path $RepoRoot "artifacts\research"
            New-Item -ItemType Directory -Force -Path $outDir | Out-Null
            $outPath = Join-Path $outDir ("deep_research_cycle_{0:000}.json" -f $i)
            $result | ConvertTo-Json -Depth 12 | Set-Content -Path $outPath
        } catch {
            $errors += "gateway_research: $($_.Exception.Message)"
        }
    } else {
        Write-Warning "[Cycle $i] Gateway at $GatewayBaseUrl not reachable, skipping research step."
        $errors += "gateway_research: Gateway not reachable at $GatewayBaseUrl (start with: uvicorn src.api.main:app --port 8000)"
    }

    if ($UsePlaywriter) {
        try {
            Write-Host "[Cycle $i] Capturing Playwriter evidence..." -ForegroundColor Yellow
            Invoke-PlaywriterEvidence | Out-Null
        } catch {
            $errors += "playwriter: $($_.Exception.Message)"
        }
    }

    if ($RunCiTriage) {
        try {
            Write-Host "[Cycle $i] Running CI triage hook..." -ForegroundColor Yellow
            Invoke-CiTriage | Out-Null
        } catch {
            $errors += "ci_triage: $($_.Exception.Message)"
        }
    }

    if ($errors.Count -gt 0) {
        $errSummary = ($errors -join " | ")
        Write-Warning "[Cycle $i] Issues: $errSummary"
        $infraError = $false
        foreach ($err in $errors) {
            if ($err -match "^arxiv_lane|^playwriter|^ci_triage|^watchdog") {
                $infraError = $true
                break
            }
        }
        if ($EnableSelfHealing -and $infraError -and (Test-Path $watchdogScript)) {
            try {
                Write-Host "[Cycle $i] Running self-healing watchdog..." -ForegroundColor Magenta
                & $watchdogScript
            } catch {
                $errors += "watchdog: $($_.Exception.Message)"
            }
        }
        Emit-LoopPacket -TaskId $taskId -Summary "Cycle $i blocked: $($errors -join ' | ')" -Status "blocked" -NextAction "Check artifacts/research and watchdog logs."
    } else {
        Emit-LoopPacket -TaskId $taskId -Summary "Cycle $i completed." -Status "done" -NextAction "Proceed to next cycle."
    }

    if ((-not $Continuous) -and ($i -ge $Cycles)) {
        break
    }
    Start-Sleep -Seconds ([Math]::Max(5, $SleepSeconds))
}

Write-Host "Deep research loop complete." -ForegroundColor Green
