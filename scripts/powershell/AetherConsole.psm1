# AetherConsole.psm1
# A discoverable terminal UI for SCBE -- no "UI shock", no blank prompt.
#
# You never have to know what to type. You open it, you SEE your options, you
# pick a number. tmux-style status bar on top; numbered menus you navigate.
#
#   aether            # open the console
#   menu              # same thing
#
# Works in Windows PowerShell 5.1 and PowerShell 7+. No dependencies.
# Catalog of actions lives next to this file in AetherMenu.catalog.json, so the
# menu can be regenerated without touching the engine.

$script:AetherCatalogPath = Join-Path $PSScriptRoot 'AetherMenu.catalog.json'
$script:AetherQuit = $false

function Get-AetherCatalog {
    if (Test-Path $script:AetherCatalogPath) {
        try { return (Get-Content $script:AetherCatalogPath -Raw -Encoding UTF8 | ConvertFrom-Json) } catch { }
    }
    return $null
}

function Get-AetherStatus {
    $repo = ''; $branch = ''
    try { $branch = (git rev-parse --abbrev-ref HEAD 2>$null) } catch { }
    try { $repo = (gh repo view --json nameWithOwner -q .nameWithOwner 2>$null) } catch { }
    if (-not $repo) { $repo = Split-Path -Leaf (Get-Location).Path }
    if (-not $branch) { $branch = '-' }
    return [pscustomobject]@{ Repo = "$repo".Trim(); Branch = "$branch".Trim(); Time = (Get-Date -Format 'HH:mm') }
}

function Write-AetherHeader {
    param([string]$Title = 'AETHER CONSOLE')
    $w = 66
    $s = Get-AetherStatus
    $bar = '=' * $w
    Write-Host ''
    Write-Host "  $bar" -ForegroundColor DarkCyan
    Write-Host ("   {0}" -f $Title) -ForegroundColor Cyan
    $status = "   repo: {0}   branch: {1}   {2}" -f $s.Repo, $s.Branch, $s.Time
    if ($status.Length -gt $w) { $status = $status.Substring(0, $w) }
    Write-Host $status -ForegroundColor DarkGray
    Write-Host "  $bar" -ForegroundColor DarkCyan
}

function Invoke-AetherAction {
    param([Parameter(Mandatory)]$Action)
    $cmd = [string]$Action.command
    if ($Action.needs_input) {
        $q = if ($Action.input_prompt) { $Action.input_prompt } else { 'Value' }
        $val = Read-Host ("  $q")
        if ($null -eq $val) { $val = '' }
        $quoted = '"' + ($val -replace '"', '`"') + '"'
        $cmd = $cmd -replace '\{input\}', $quoted
    }
    if ($Action.run_mode -eq 'confirm') {
        Write-Host ''
        Write-Host "  This will run:" -ForegroundColor Yellow
        Write-Host "    $cmd" -ForegroundColor White
        $ans = Read-Host "  Run it? [y/N]"
        if ($ans -notmatch '^(y|yes)$') { Write-Host '  (cancelled)' -ForegroundColor DarkGray; return }
    }
    Write-Host ''
    Write-Host "  > $cmd" -ForegroundColor Green
    Write-Host ('  ' + ('-' * 60)) -ForegroundColor DarkGray
    try { Invoke-Expression $cmd } catch { Write-Host "  (error: $($_.Exception.Message))" -ForegroundColor Red }
    Write-Host ('  ' + ('-' * 60)) -ForegroundColor DarkGray
}

function Show-AetherCategory {
    param([Parameter(Mandatory)]$Category, [switch]$RenderOnly)
    $actions = @($Category.actions)
    while (-not $script:AetherQuit) {
        if (-not $RenderOnly) { Clear-Host }
        Write-AetherHeader -Title (("{0}  {1}" -f $Category.icon, $Category.category).Trim())
        Write-Host ''
        for ($i = 0; $i -lt $actions.Count; $i++) {
            Write-Host ("   {0,2})  {1}" -f ($i + 1), $actions[$i].label) -ForegroundColor Cyan
            if ($actions[$i].desc) { Write-Host ("        {0}" -f $actions[$i].desc) -ForegroundColor DarkGray }
        }
        Write-Host ''
        Write-Host "    B)  Back        Q)  Quit" -ForegroundColor DarkGray
        if ($RenderOnly) { return }
        $sel = Read-Host "`n  Pick a number"
        if ($sel -match '^(q|quit)$') { $script:AetherQuit = $true; return }
        if ($sel -match '^(b|back|)$') { return }
        $idx = 0
        if ([int]::TryParse($sel, [ref]$idx) -and $idx -ge 1 -and $idx -le $actions.Count) {
            Invoke-AetherAction -Action $actions[$idx - 1]
            Read-Host "`n  (press Enter to go back)" | Out-Null
        }
    }
}

function Show-AetherConsole {
    <#
    .SYNOPSIS  The SCBE terminal menu. Open it, see your options, pick a number.
    .EXAMPLE   aether
    #>
    [CmdletBinding()]
    param([switch]$RenderOnly)
    $cat = Get-AetherCatalog
    if (-not $cat -or -not $cat.categories) {
        Write-Host "Aether menu catalog not found ($script:AetherCatalogPath)." -ForegroundColor Red
        return
    }
    $cats = @($cat.categories)
    $script:AetherQuit = $false
    while (-not $script:AetherQuit) {
        if (-not $RenderOnly) { Clear-Host }
        Write-AetherHeader -Title 'AETHER CONSOLE  --  what do you want to do?'
        Write-Host ''
        for ($i = 0; $i -lt $cats.Count; $i++) {
            Write-Host ("   {0,2})  {1}  {2}" -f ($i + 1), $cats[$i].icon, $cats[$i].category) -ForegroundColor Cyan
        }
        Write-Host ''
        Write-Host "    A)  Ask the AI anything (plain English)" -ForegroundColor Green
        Write-Host "    G)  GitHub helper (scbe-gh ...)" -ForegroundColor Green
        Write-Host "    Q)  Quit" -ForegroundColor DarkGray
        if ($RenderOnly) { return }
        $sel = Read-Host "`n  Pick a number"
        if ($sel -match '^(q|quit)$') { break }
        if ($sel -match '^(a|ask)$') {
            $q = Read-Host "  Ask"
            if ($q) { if (Get-Command scbe-gh -EA SilentlyContinue) { scbe-gh $q } else { python scbe.py ask "$q" } ; Read-Host "`n  (Enter to go back)" | Out-Null }
            continue
        }
        if ($sel -match '^(g|github)$') {
            $q = Read-Host "  GitHub, in English"
            if ($q -and (Get-Command scbe-gh -EA SilentlyContinue)) { scbe-gh $q; Read-Host "`n  (Enter to go back)" | Out-Null }
            continue
        }
        $idx = 0
        if ([int]::TryParse($sel, [ref]$idx) -and $idx -ge 1 -and $idx -le $cats.Count) {
            Show-AetherCategory -Category $cats[$idx - 1]
        }
    }
    Write-Host "`n  bye." -ForegroundColor DarkGray
}

New-Alias -Name aether -Value Show-AetherConsole -Force
New-Alias -Name menu   -Value Show-AetherConsole -Force

Export-ModuleMember -Function Show-AetherConsole, Show-AetherCategory, Invoke-AetherAction, `
    Get-AetherCatalog, Get-AetherStatus, Write-AetherHeader -Alias aether, menu
