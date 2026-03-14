param(
    [string]$ProjectRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [int]$IntervalHours = 4,
    [int]$LoopMinutes = 240,
    [switch]$EnableMoney = $true,
    [switch]$EnableSmoke,
    [switch]$ConfigureGrokFromEnv = $true,
    [switch]$StartNow = $true,
    [switch]$PreferBackgroundLoop
)

$ErrorActionPreference = "Stop"

function Write-Info {
    param([string]$Message)
    Write-Host "[SCBE setup] $Message"
}

function Get-DotEnvValue {
    param(
        [string]$EnvPath,
        [string]$Name
    )

    if (-not (Test-Path $EnvPath)) {
        return ""
    }

    $pattern = "^" + [regex]::Escape($Name) + "=(.*)$"
    foreach ($line in Get-Content -Path $EnvPath) {
        if ($line -match '^\s*#') {
            continue
        }
        if ($line -match $pattern) {
            $value = $Matches[1].Trim()
            $value = $value.Trim('"')
            $value = $value.Trim("'")
            return $value
        }
    }

    return ""
}

function Configure-GrokKey {
    param([string]$RepoRoot)

    $envPath = Join-Path $RepoRoot ".env"
    $grokKey = Get-DotEnvValue -EnvPath $envPath -Name "GROK_API_KEY"
    if ([string]::IsNullOrWhiteSpace($grokKey)) {
        $grokKey = Get-DotEnvValue -EnvPath $envPath -Name "XAI_API_KEY"
    }
    if ([string]::IsNullOrWhiteSpace($grokKey)) {
        Write-Info "No GROK_API_KEY or XAI_API_KEY found in .env; skipping grok key wiring."
        return
    }

    $grokDir = Join-Path $HOME ".grok"
    $settingsPath = Join-Path $grokDir "user-settings.json"
    New-Item -ItemType Directory -Force -Path $grokDir | Out-Null

    if (Test-Path $settingsPath) {
        $settings = Get-Content -Path $settingsPath -Raw | ConvertFrom-Json
    }
    else {
        $settings = [pscustomobject]@{}
    }

    $settings | Add-Member -NotePropertyName apiKey -NotePropertyValue $grokKey -Force
    if (-not ($settings.PSObject.Properties.Name -contains "settingsVersion")) {
        $settings | Add-Member -NotePropertyName settingsVersion -NotePropertyValue 1 -Force
    }

    ($settings | ConvertTo-Json -Depth 100) | Set-Content -Path $settingsPath -Encoding UTF8
    Write-Info "Updated ~/.grok/user-settings.json with API key from .env (value hidden)."
}

function Get-PythonPath {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $cmd = Get-Command python3 -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    throw "Python was not found in PATH."
}

function Register-OpsAutopilotTask {
    param(
        [string]$RepoRoot,
        [int]$Hours,
        [switch]$Money,
        [switch]$Smoke
    )

    $registerScript = Join-Path $RepoRoot "scripts\system\register_autopilot_task.ps1"
    if (-not (Test-Path $registerScript)) {
        throw "Missing register script: $registerScript"
    }

    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $registerScript,
        "-Interval", "$Hours"
    )
    if ($Money) {
        $args += "-WithMoney"
    }
    if ($Smoke) {
        $args += "-WithSmoke"
    }

    & powershell @args
    if ($LASTEXITCODE -ne 0) {
        throw "register_autopilot_task.ps1 failed."
    }

    Write-Info "Scheduled task SCBE-OpsAutopilot registered."
}

function Start-OpsAutopilotTaskNow {
    try {
        Start-ScheduledTask -TaskName "SCBE-OpsAutopilot"
        Write-Info "Scheduled task triggered immediately."
        return $true
    }
    catch {
        Write-Info "Start-ScheduledTask failed: $($_.Exception.Message)"
        return $false
    }
}

function Start-BackgroundLoop {
    param(
        [string]$RepoRoot,
        [int]$Minutes,
        [switch]$Money,
        [switch]$Smoke
    )

    $existing = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='python3.exe'" |
        Where-Object { $_.CommandLine -match "ops_24x7_autopilot\.py" } |
        Select-Object -First 1
    if ($existing) {
        Write-Info "Background loop already running (PID=$($existing.ProcessId))."
        return
    }

    $pythonPath = Get-PythonPath
    $args = @(
        "scripts\ops_24x7_autopilot.py",
        "--scan-name", "scheduled",
        "--repeat-every-minutes", "$Minutes",
        "--iterations", "999999"
    )

    if ($Money) {
        $args += "--run-money"
        $args += "--money-probe"
    }
    else {
        $args += "--no-run-money"
    }

    if ($Smoke) {
        $args += "--run-smoke"
    }
    else {
        $args += "--no-run-smoke"
    }

    $proc = Start-Process -FilePath $pythonPath -ArgumentList $args -WorkingDirectory $RepoRoot -WindowStyle Hidden -PassThru
    Write-Info "Fallback background loop started (PID=$($proc.Id)) every $Minutes minute(s)."
}

if (-not (Test-Path $ProjectRoot)) {
    throw "Project root not found: $ProjectRoot"
}

Set-Location $ProjectRoot

if ($ConfigureGrokFromEnv) {
    Configure-GrokKey -RepoRoot $ProjectRoot
}

$taskReady = $false
if (-not $PreferBackgroundLoop) {
    try {
        Register-OpsAutopilotTask -RepoRoot $ProjectRoot -Hours $IntervalHours -Money:$EnableMoney -Smoke:$EnableSmoke
        $taskReady = $true
    }
    catch {
        Write-Info "Task scheduler registration failed: $($_.Exception.Message)"
    }
}

if ($StartNow) {
    if ($taskReady) {
        $started = Start-OpsAutopilotTaskNow
        if (-not $started) {
            Start-BackgroundLoop -RepoRoot $ProjectRoot -Minutes $LoopMinutes -Money:$EnableMoney -Smoke:$EnableSmoke
        }
    }
    else {
        Start-BackgroundLoop -RepoRoot $ProjectRoot -Minutes $LoopMinutes -Money:$EnableMoney -Smoke:$EnableSmoke
    }
}

$latest = Join-Path $ProjectRoot "artifacts\ops-autopilot\latest.json"
if (Test-Path $latest) {
    try {
        $payload = Get-Content -Path $latest -Raw | ConvertFrom-Json
        Write-Info "Latest autopilot status: $($payload.status)"
        Write-Info "Latest run id: $($payload.run_id)"
    }
    catch {
        Write-Info "Autopilot latest report exists but could not be parsed."
    }
}
else {
    Write-Info "No latest autopilot report yet. Wait 1-3 minutes and check artifacts/ops-autopilot/latest.json"
}

Write-Info "Setup complete."
