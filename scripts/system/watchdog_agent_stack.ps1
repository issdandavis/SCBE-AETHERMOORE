param(
    [string]$ProjectRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$N8nUserFolder = "C:\Users\issda\SCBE-AETHERMOORE\.n8n_local_iso",
    [int]$BridgePort = 8002,
    [int]$BrowserPort = 8012,
    [int]$N8nPort = 5680,
    [int]$N8nTaskBrokerPort = 5681,
    [string]$LogFile = "C:\Users\issda\SCBE-AETHERMOORE\artifacts\ops\watchdog_agent_stack.log",
    [string]$TelegramBotToken = "",
    [string]$TelegramChatId = "",
    [switch]$TelegramSilent,
    [switch]$ImportWorkflows,
    [switch]$PublishWorkflows
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message)
    $stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$stamp] $Message"
    Write-Host $line
    $dir = Split-Path -Parent $LogFile
    if ($dir) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    Add-Content -Path $LogFile -Value $line
}

if (-not $TelegramBotToken) {
    $TelegramBotToken = $env:SCBE_TELEGRAM_BOT_TOKEN
}
if (-not $TelegramBotToken) {
    $TelegramBotToken = $env:TELEGRAM_BOT_TOKEN
}
if (-not $TelegramChatId) {
    $TelegramChatId = $env:SCBE_TELEGRAM_CHAT_ID
}
if (-not $TelegramChatId) {
    $TelegramChatId = $env:TELEGRAM_CHAT_ID
}
if ($TelegramChatId -and ($TelegramChatId -notmatch '^-?\d+$')) {
    Write-Log "WARN: Telegram chat id must be numeric. Alerts disabled for chat id '$TelegramChatId'."
    $TelegramChatId = ""
}

function Send-TelegramAlert {
    param(
        [string]$Text,
        [string]$Level = "INFO"
    )

    if (-not $TelegramBotToken -or -not $TelegramChatId) {
        return
    }

    $icon = switch ($Level.ToUpperInvariant()) {
        "ERROR" { "[ERROR]" }
        "WARN" { "[WARN]" }
        default { "[INFO]" }
    }
    $hostName = if ($env:COMPUTERNAME) { $env:COMPUTERNAME } else { "unknown-host" }
    $message = "$icon [SCBE][$Level][$hostName] $Text"

    $payload = @{
        chat_id = $TelegramChatId
        text = $message
        disable_notification = [bool]$TelegramSilent
    }

    try {
        Invoke-RestMethod `
            -Method Post `
            -Uri ("https://api.telegram.org/bot{0}/sendMessage" -f $TelegramBotToken) `
            -ContentType "application/json" `
            -Body ($payload | ConvertTo-Json -Compress) | Out-Null
        Write-Log "Telegram alert sent (level=$Level)."
    } catch {
        Write-Log "WARN: failed to send Telegram alert: $($_.Exception.Message)"
    }
}

function Test-Http {
    param([string]$Url, [int]$TimeoutSec = 5)
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec $TimeoutSec
        return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500)
    } catch {
        return $false
    }
}

function Stop-Ports {
    param([int[]]$Ports)
    $pids = @()
    try {
        $pids = Get-NetTCPConnection -State Listen -ErrorAction Stop |
            Where-Object { $_.LocalPort -in $Ports } |
            Select-Object -ExpandProperty OwningProcess -Unique
    } catch {
        Write-Log "WARN: unable to enumerate listening ports: $($_.Exception.Message)"
        return
    }

    foreach ($procId in $pids) {
        try {
            Stop-Process -Id $procId -Force -ErrorAction Stop
            Write-Log "Stopped process $procId on target ports."
        } catch {
            Write-Log "WARN: failed to stop process $($procId): $($_.Exception.Message)"
        }
    }
}

$bridgeHealthy = Test-Http -Url "http://127.0.0.1:$BridgePort/health"
$browserHealthy = Test-Http -Url "http://127.0.0.1:$BrowserPort/health"
$n8nHealthy = Test-Http -Url "http://127.0.0.1:$N8nPort/healthz"
if (-not $n8nHealthy) {
    $n8nHealthy = Test-Http -Url "http://127.0.0.1:$N8nPort"
}

if ($bridgeHealthy -and $browserHealthy -and $n8nHealthy) {
    Write-Log "Healthy: bridge=$BridgePort browser=$BrowserPort n8n=$N8nPort"
    exit 0
}

Write-Log "Unhealthy: bridge=$bridgeHealthy browser=$browserHealthy n8n=$n8nHealthy. Restarting stack."
Send-TelegramAlert -Level "WARN" -Text "Watchdog detected unhealthy stack. bridge=$bridgeHealthy browser=$browserHealthy n8n=$n8nHealthy. Restarting."
Stop-Ports -Ports @($BridgePort, $BrowserPort, $N8nPort, $N8nTaskBrokerPort)

$startScript = Join-Path $ProjectRoot "workflows\n8n\start_n8n_local.ps1"
if (-not (Test-Path $startScript)) {
    throw "Start script not found: $startScript"
}

$argsList = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $startScript,
    "-ProjectRoot", $ProjectRoot,
    "-N8nUserFolder", $N8nUserFolder,
    "-BridgePort", "$BridgePort",
    "-BrowserPort", "$BrowserPort",
    "-N8nPort", "$N8nPort",
    "-N8nTaskBrokerPort", "$N8nTaskBrokerPort",
    "-StartBrowserAgent"
)
if ($ImportWorkflows) { $argsList += "-ImportWorkflows" }
if ($PublishWorkflows) { $argsList += "-PublishWorkflows" }

[void](Start-Process -FilePath "powershell.exe" -ArgumentList $argsList -WindowStyle Hidden -PassThru)
Start-Sleep -Seconds 10

$bridgeHealthy = Test-Http -Url "http://127.0.0.1:$BridgePort/health"
$browserHealthy = Test-Http -Url "http://127.0.0.1:$BrowserPort/health"
$n8nHealthy = Test-Http -Url "http://127.0.0.1:$N8nPort/healthz"
if (-not $n8nHealthy) {
    $n8nHealthy = Test-Http -Url "http://127.0.0.1:$N8nPort"
}

if ($bridgeHealthy -and $browserHealthy -and $n8nHealthy) {
    Write-Log "Recovery succeeded: bridge=$BridgePort browser=$BrowserPort n8n=$N8nPort"
    Send-TelegramAlert -Level "INFO" -Text "Recovery succeeded. bridge=$BridgePort browser=$BrowserPort n8n=$N8nPort"
    exit 0
}

Write-Log "Recovery failed: bridge=$bridgeHealthy browser=$browserHealthy n8n=$n8nHealthy"
Send-TelegramAlert -Level "ERROR" -Text "Recovery failed. bridge=$bridgeHealthy browser=$browserHealthy n8n=$n8nHealthy"
exit 1
