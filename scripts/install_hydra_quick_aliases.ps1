param(
    [string]$ProfilePath = $PROFILE
)

$ErrorActionPreference = "Stop"

$startMarker = "# >>> HYDRA QUICK ALIASES >>>"
$endMarker = "# <<< HYDRA QUICK ALIASES <<<"

$resolvedProfilePath = $ProfilePath
if ([string]::IsNullOrWhiteSpace($resolvedProfilePath)) {
    $resolvedProfilePath = $PROFILE.CurrentUserCurrentHost
}
if ([string]::IsNullOrWhiteSpace($resolvedProfilePath)) {
    $resolvedProfilePath = Join-Path $HOME "Documents\PowerShell\Microsoft.PowerShell_profile.ps1"
}

$block = @"
$startMarker
function hstatus { hydra status --json }
function hresearch {
    param([Parameter(ValueFromRemainingArguments = `$true)][string[]]`$Args)
    if (-not `$Args -or `$Args.Count -eq 0) {
        Write-Host "Usage: hresearch <topic>"
        return
    }
    hydra research `$Args[0] --mode httpx --max-subtasks 2 --discovery 3
}
function harxiv {
    param([Parameter(ValueFromRemainingArguments = `$true)][string[]]`$Args)
    if (-not `$Args -or `$Args.Count -eq 0) {
        Write-Host "Usage: harxiv <topic>"
        return
    }
    hydra arxiv search `$Args[0] --cat cs.AI --max 5
}
function hqueue { hydra switchboard stats }
$endMarker
"@

if (-not (Test-Path $resolvedProfilePath)) {
    $parent = Split-Path -Parent $resolvedProfilePath
    if ($parent -and -not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    New-Item -ItemType File -Path $resolvedProfilePath -Force | Out-Null
}

$current = Get-Content -Raw -Path $resolvedProfilePath
if ($null -eq $current) {
    $current = ""
}
$pattern = [regex]::Escape($startMarker) + "[\s\S]*?" + [regex]::Escape($endMarker)
if ([regex]::IsMatch($current, $pattern)) {
    $updated = [regex]::Replace($current, $pattern, $block)
}
else {
    $sep = if ($current.EndsWith("`n") -or [string]::IsNullOrEmpty($current)) { "" } else { "`r`n" }
    $updated = $current + $sep + $block + "`r`n"
}

Set-Content -Path $resolvedProfilePath -Value $updated -Encoding UTF8
Write-Host "HYDRA quick aliases installed to $resolvedProfilePath"
Write-Host "Open a new PowerShell session (or run: . `"$resolvedProfilePath`")"
