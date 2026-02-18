param(
    [string]$ConfigPath = "",
    [string[]]$Servers = @("fetch", "power-cloud-architect-fetch"),
    [switch]$DryRun
)

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $env:USERPROFILE ".kiro/settings/mcp.json"
}

if (-not (Test-Path $ConfigPath)) {
    throw "MCP config not found: $ConfigPath"
}

$raw = Get-Content $ConfigPath -Raw
$config = $raw | ConvertFrom-Json

if ($null -eq $config) {
    throw "Unable to parse MCP config as JSON: $ConfigPath"
}

$changed = $false

function Set-Disabled($target, [string]$key, [bool]$value) {
    if ($null -eq $target.$key) {
        return $false
    }

    $current = [bool]$target.$key.disabled
    if ($current -ne $value) {
        $target.$key.disabled = $value
        return $true
    }
    return $false
}

foreach ($server in $Servers) {
    $top = Set-Disabled $config.mcpServers $server $false
    if ($top) {
        Write-Output "Enabled top-level MCP server: $server"
        $changed = $true
        continue
    }

    $nested = Set-Disabled $config.powers.mcpServers $server $false
    if ($nested) {
        Write-Output "Enabled power MCP server: $server"
        $changed = $true
    }
}

if ($changed -and -not $DryRun) {
    $config | ConvertTo-Json -Depth 20 | Set-Content $ConfigPath -NoNewline
    Write-Output "Updated: $ConfigPath"
}
elseif ($changed -and $DryRun) {
    Write-Output "Dry run only; no changes written."
} else {
    Write-Output "No changes required."
}
