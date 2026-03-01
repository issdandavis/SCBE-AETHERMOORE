param(
    [ValidateSet('start','verify','status','probe','env','all')]
    [string]$Mode = 'all'
)

$base = 'C:\Users\issda\SCBE-AETHERMOORE'
$bridge = Join-Path $base 'skills\clawhub\scbe-colab-n8n-bridge\scripts\colab_n8n_bridge.py'
$starter = Join-Path $base 'scripts\start_colab_bridge.ps1'
$profile = 'colab_local'

function Invoke-ColabBridge {
    param([string[]]$CommandArgs)
    & python $bridge --name $profile @CommandArgs
}

switch ($Mode.ToLowerInvariant()) {
    'start' {
        & pwsh -NoProfile -ExecutionPolicy Bypass -File $starter
    }
    'status' {
        Invoke-ColabBridge -CommandArgs @('--status', '--format', 'json')
    }
    'probe' {
        Invoke-ColabBridge -CommandArgs @('--probe')
    }
    'env' {
        Invoke-ColabBridge -CommandArgs @('--env', '--shell', 'pwsh')
    }
    'verify' {
        Invoke-ColabBridge -CommandArgs @('--status', '--format', 'json')
        Invoke-ColabBridge -CommandArgs @('--probe')
        Invoke-ColabBridge -CommandArgs @('--env', '--shell', 'pwsh')
    }
    default {
        & pwsh -NoProfile -ExecutionPolicy Bypass -File $starter
        Start-Sleep -Seconds 1
        Invoke-ColabBridge -CommandArgs @('--status', '--format', 'json')
        Invoke-ColabBridge -CommandArgs @('--probe')
        Invoke-ColabBridge -CommandArgs @('--env', '--shell', 'pwsh')
    }
}
