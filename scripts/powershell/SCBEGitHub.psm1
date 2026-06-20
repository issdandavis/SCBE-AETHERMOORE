# SCBEGitHub.psm1
# GitHub "Copilot-style" commands for the SCBE PowerShell shell.
#
# Turns plain English into the right `gh`/`git` command and (optionally) runs it,
# the way `gh copilot suggest` does -- but it works OFFLINE via a rule-based
# resolver, and transparently upgrades to `gh copilot` or the SCBE AI when either
# is available. Also ships convenience verbs for the common GitHub ops.
#
# Load it (works in Windows PowerShell 5.1 and PowerShell 7+):
#   Import-Module C:\Users\issda\scbe-main-check\scripts\powershell\SCBEGitHub.psm1
#
# Use it:
#   scbe-gh open a PR for my branch
#   ghc why did CI fail
#   scbe-gh merge PR 2310            # prints the command; add -Run to execute
#   Get-SCBECIStatus -Limit 5
#   Submit-SCBEChange "fix: thing" -Pr
#
# Make it permanent (add to your $PROFILE):
#   Import-Module C:\Users\issda\scbe-main-check\scripts\powershell\SCBEGitHub.psm1

$script:SCBEDefaultRepo = 'issdandavis/SCBE-AETHERMOORE'

function Get-SCBERepo {
    <#.SYNOPSIS Resolve the current GitHub repo slug (owner/name), falling back to the SCBE default.#>
    [CmdletBinding()]
    param()
    try {
        $slug = (gh repo view --json nameWithOwner -q .nameWithOwner 2>$null)
        if ($LASTEXITCODE -eq 0 -and $slug) { return $slug.Trim() }
    } catch { }
    return $script:SCBEDefaultRepo
}

function Test-SCBEHasGhCopilot {
    <#.SYNOPSIS True if the official `gh copilot` extension is installed.#>
    [CmdletBinding()]
    param()
    try { $null = gh copilot --version 2>$null; return ($LASTEXITCODE -eq 0) } catch { return $false }
}

function Resolve-SCBEGitHubCommand {
    <#.SYNOPSIS Offline rule-based intent -> gh/git command. Returns $null if nothing matches.#>
    [CmdletBinding()]
    param([Parameter(Mandatory, ValueFromRemainingArguments)][string[]]$Request)
    $low = (($Request -join ' ').Trim()).ToLowerInvariant()
    switch -Regex ($low) {
        'why.*(ci|build|check|run|test).*(fail|red|brok)|what.*(fail|brok)|see.*(fail).*log' { return 'gh run view --log-failed' }
        '(merge).*(pr|pull request).*?#?\s*(\d+)'        { return "gh pr merge $($Matches[3]) --squash --delete-branch" }
        '(checkout|switch to|check out).*(pr|pull request).*?#?\s*(\d+)' { return "gh pr checkout $($Matches[3])" }
        '(view|show|open|look at).*(pr|pull request).*?#?\s*(\d+)' { return "gh pr view $($Matches[3]) --web" }
        '(check|show|view|are).*(pr|pull|my).*(check|ci|green|pass)' { return 'gh pr checks' }
        '(create|open|make|start|raise|draft).*(pr|pull request)' { return 'gh pr create --fill' }
        '(list|show|see|open).*(pr|pull request)'        { return 'gh pr list' }
        '(ci|build|workflow|action|run|test).*(status|state|list|recent|latest|pass|green|red)' { return "gh run list --limit 10" }
        '(show|list|see|recent).*(run|ci|build|action|workflow)' { return "gh run list --limit 10" }
        '(create|open|file|make|raise).*(issue|bug|ticket)' { return 'gh issue create' }
        '(list|show|see).*(issue|bug|ticket)'            { return 'gh issue list' }
        '(release).*(list|show|recent)|list.*release'    { return 'gh release list' }
        '(clone)\s+(\S+)'                                { return "gh repo clone $($Matches[2])" }
        '(commit).*(push)|push.*(commit)|save.*(push)|commit and push|ship .*(change)' { return 'git add -A; git commit -m "<message>"; git push' }
        '(push)\b'                                       { return 'git push' }
        '(repo|repository|github).*(status|state|overview)|^\s*status' { return 'gh status' }
        '(am i|are we).*(log|auth)|auth.*(status)|logged in|who am i' { return 'gh auth status' }
        '(diff|what changed|my changes)'                 { return 'git diff --stat' }
        default { return $null }
    }
}

function Get-SCBEAISuggestion {
    <#.SYNOPSIS Ask the SCBE CLI's AI verb for a one-line command (only if a model backend is configured).#>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Request)
    $repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
    $scbe = Join-Path $repoRoot 'scbe.py'
    if (-not (Test-Path $scbe)) { return $null }
    try {
        $out = python $scbe ask "Reply with ONLY the single gh or git command (no backticks, no prose) to: $Request" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $out) { return $null }
        $line = ($out | Where-Object { $_ -match '^\s*(gh|git)\s' } | Select-Object -First 1)
        if ($line) { return $line.Trim() }
    } catch { }
    return $null
}

function Invoke-SCBEGitHubCopilot {
    <#
    .SYNOPSIS  Plain English -> the right gh/git command, copilot-style.
    .EXAMPLE   scbe-gh open a PR for my branch
    .EXAMPLE   scbe-gh merge PR 2310 -Run
    #>
    [CmdletBinding()]
    param(
        [Parameter(ValueFromRemainingArguments)][string[]]$Request,
        [switch]$Run,     # execute the suggested command (confirm first unless -Force)
        [switch]$Force    # run without confirming
    )
    $req = ($Request -join ' ').Trim()
    if (-not $req) {
        Write-Host 'Usage: scbe-gh <what you want to do on GitHub>   e.g.  scbe-gh why did CI fail' -ForegroundColor Yellow
        return
    }

    $cmd = $null; $source = 'rules'
    if (Test-SCBEHasGhCopilot) {
        $sugg = (gh copilot suggest -t shell "$req" 2>$null | Where-Object { $_ -match '^(gh|git)\s' } | Select-Object -Last 1)
        if ($sugg) { $cmd = $sugg.Trim(); $source = 'gh-copilot' }
    }
    if (-not $cmd) { $cmd = Resolve-SCBEGitHubCommand $req }
    if (-not $cmd) {
        $ai = Get-SCBEAISuggestion -Request $req
        if ($ai) { $cmd = $ai; $source = 'scbe-ai' }
    }
    if (-not $cmd) {
        Write-Host "No GitHub command matched `"$req`"." -ForegroundColor Yellow
        Write-Host "Tip: install copilot for free-form NL -> gh extension install github/gh-copilot" -ForegroundColor DarkGray
        return
    }

    Write-Host ''
    Write-Host "  # suggested ($source)" -ForegroundColor DarkGray
    Write-Host "  $cmd" -ForegroundColor Cyan
    Write-Host ''
    if ($cmd -match '<[^>]+>') {
        Write-Host '  (fill in the <...> placeholder, then run it)' -ForegroundColor Yellow
        return
    }
    if (-not ($Run -or $Force)) {
        Write-Host '  (add -Run to execute, or -Run -Force to skip this hint)' -ForegroundColor DarkGray
        return
    }
    $go = $Force
    if (-not $go) {
        $ans = Read-Host "  Run it? [y/N]"
        $go = ($ans -match '^(y|yes)$')
    }
    if ($go) {
        Write-Host "  > $cmd" -ForegroundColor Green
        Invoke-Expression $cmd
    }
}

function Get-SCBEGitHubExplanation {
    <#.SYNOPSIS Explain a gh/git command (uses `gh copilot explain` if present, else a built-in cheatsheet).#>
    [CmdletBinding()]
    param([Parameter(ValueFromRemainingArguments)][string[]]$Command)
    $c = ($Command -join ' ').Trim()
    if (-not $c) { Write-Host 'Usage: scbe-ghx <command to explain>' -ForegroundColor Yellow; return }
    if (Test-SCBEHasGhCopilot) { gh copilot explain "$c"; return }
    $map = @{
        'gh pr create'  = 'Open a pull request from the current branch.'
        'gh pr checks'  = 'Show CI check status for the PR of the current branch.'
        'gh pr merge'   = 'Merge a pull request (use --squash to squash, --delete-branch to clean up).'
        'gh run list'   = 'List recent GitHub Actions workflow runs.'
        'gh run view'   = 'Show one run; --log-failed prints only the failed steps logs.'
        'gh issue create' = 'Open a new issue.'
        'gh status'     = 'Overview of your assigned issues/PRs and review requests.'
        'gh auth status'= 'Show your gh authentication state.'
    }
    $hit = $false
    foreach ($k in $map.Keys) { if ($c -like "$k*") { Write-Host "  $c" -ForegroundColor Cyan; Write-Host "  -> $($map[$k])"; $hit = $true; break } }
    if (-not $hit) { Write-Host "No built-in explanation. Install: gh extension install github/gh-copilot for full explain." -ForegroundColor DarkGray }
}

# ---- convenience verbs (thin, repo-aware gh/git wrappers) --------------------

function Get-SCBECIStatus {
    <#.SYNOPSIS Recent CI runs for the SCBE repo.#>
    [CmdletBinding()] param([int]$Limit = 10)
    gh run list --repo (Get-SCBERepo) --limit $Limit
}

function Get-SCBEPRStatus {
    <#.SYNOPSIS List open PRs, or view one by number.#>
    [CmdletBinding()] param([int]$Number)
    if ($Number) { gh pr view $Number --repo (Get-SCBERepo) } else { gh pr list --repo (Get-SCBERepo) }
}

function New-SCBEPullRequest {
    <#.SYNOPSIS Open a PR from the current branch (autofills from commits if no title given).#>
    [CmdletBinding()] param([string]$Title, [string]$Body, [switch]$Draft)
    $args = @('pr', 'create')
    if ($Title) { $args += @('--title', $Title) } else { $args += '--fill' }
    if ($Body)  { $args += @('--body', $Body) }
    if ($Draft) { $args += '--draft' }
    gh @args
}

function Submit-SCBEChange {
    <#.SYNOPSIS Stage all, commit with a message, push; with -Pr also open a pull request.#>
    [CmdletBinding()] param([Parameter(Mandatory)][string]$Message, [switch]$Pr)
    git add -A
    git commit -m $Message
    if ($LASTEXITCODE -ne 0) { Write-Host 'Nothing to commit (or commit failed).' -ForegroundColor Yellow; return }
    git push
    if ($Pr) { gh pr create --fill }
}

New-Alias -Name scbe-gh  -Value Invoke-SCBEGitHubCopilot -Force
New-Alias -Name ghc      -Value Invoke-SCBEGitHubCopilot -Force
New-Alias -Name scbe-ghx -Value Get-SCBEGitHubExplanation -Force

Export-ModuleMember -Function Get-SCBERepo, Test-SCBEHasGhCopilot, Resolve-SCBEGitHubCommand, `
    Get-SCBEAISuggestion, Invoke-SCBEGitHubCopilot, Get-SCBEGitHubExplanation, `
    Get-SCBECIStatus, Get-SCBEPRStatus, New-SCBEPullRequest, Submit-SCBEChange `
    -Alias scbe-gh, ghc, scbe-ghx
