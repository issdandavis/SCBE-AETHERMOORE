param(
    [string]$Root = 'C:\Users\issda',
    [string]$ReportPath = 'C:\Users\issda\SCBE-AETHERMOORE\docs\github_organization_health_2026-02-28.md'
)

$ErrorActionPreference = 'Stop'

$locals = @()
foreach ($dir in Get-ChildItem -Path $Root -Directory -ErrorAction SilentlyContinue) {
    $git = Join-Path $dir.FullName '.git'
    if (-not (Test-Path $git)) {
        continue
    }

    $remote = git -C $dir.FullName remote get-url origin 2>$null
    if ([string]::IsNullOrWhiteSpace($remote)) { $remote = '(none)' }

    $branch = git -C $dir.FullName rev-parse --abbrev-ref HEAD 2>$null
    if ([string]::IsNullOrWhiteSpace($branch)) { $branch = '(detached)' }

    $dirty = (git -C $dir.FullName status --short 2>$null | Measure-Object).Count
    $untracked = (git -C $dir.FullName status --short --untracked-files=all 2>$null | Select-String '^\?\?' | Measure-Object).Count

    $ahead = 'n/a'
    $behind = 'n/a'
    if ($remote -ne '(none)' -and $branch -notmatch 'HEAD|\(detached\)') {
        $counts = git -C $dir.FullName rev-list --left-right --count "origin/$branch...$branch" 2>$null
        if ($LASTEXITCODE -eq 0 -and $counts -match '^(\d+)\s+(\d+)$') {
            $behind = [int]$matches[1]
            $ahead = [int]$matches[2]
        }
    }

    $locals += [pscustomobject]@{
        Repo=$dir.Name
        Path=$dir.FullName
        Branch=$branch
        Remote=$remote
        Dirty=$dirty
        Untracked=$untracked
        Ahead=$ahead
        Behind=$behind
    }
}

$localReport = @()
$localReport += '# Local Repo Snapshot'
$localReport += ''
$localReport += '| Repo | Branch | Remote | Dirty | Untracked | Ahead | Behind |'
$localReport += '| --- | --- | --- | --- | --- | --- | --- |'
foreach ($r in $locals | Sort-Object Repo) {
    $localReport += "| $($r.Repo) | $($r.Branch) | $($r.Remote) | $($r.Dirty) | $($r.Untracked) | $($r.Ahead) | $($r.Behind) |"
}

$query = @'
query {
  user(login: "issdandavis") {
    repositories(first: 100, ownerAffiliations: [OWNER]) {
      nodes {
        nameWithOwner
        isPrivate
        isFork
        isArchived
        defaultBranchRef { name }
        updatedAt
        openPullRequests: pullRequests(states: OPEN) { totalCount }
      }
    }
  }
}
'@

$remoteJson = gh api graphql -f query=$query
$remoteData = $remoteJson | ConvertFrom-Json

$remoteReport = @()
$remoteReport += '# Remote Repo Snapshot (issdandavis)'
$remoteReport += ''
$remoteReport += '| Repo | Private | Fork | Archived | Default Branch | Open PRs | Updated |'
$remoteReport += '| --- | --- | --- | --- | --- | --- | --- |'
foreach ($repo in ($remoteData.data.user.repositories.nodes | Sort-Object { [datetime]$_.updatedAt } -Descending)) {
    $branch = if ($repo.defaultBranchRef) { $repo.defaultBranchRef.name } else { '(none)' }
    $updated = [datetime]$repo.updatedAt | Get-Date -Format yyyy-MM-dd
    $remoteReport += "| $($repo.nameWithOwner) | $($repo.isPrivate) | $($repo.isFork) | $($repo.isArchived) | $branch | $($repo.openPullRequests.totalCount) | $updated |"
}

$openPrList = $remoteData.data.user.repositories.nodes | Where-Object { $_.isArchived -eq $false -and $_.openPullRequests.totalCount -gt 0 }
$highPr = ($openPrList | Sort-Object { [int]$_.openPullRequests.totalCount } -Descending | ForEach-Object { "$($_.nameWithOwner)($($_.openPullRequests.totalCount))" }) -join ', '

$report = @()
$report += "# GitHub Organization Health Audit"
$report += "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$report += ''
$report += $localReport
$report += ''
$report += $remoteReport
$report += ''
$report += '## Actions to organize'
if ($openPrList.Count -gt 0) {
    $report += "- Active PR-heavy repos: $highPr"
} else {
    $report += '- No active remote PR backlog reported in first 100 repos.'
}

$dupes = $locals | Where-Object { $_.Remote -ne '(none)' } | Group-Object Remote | Where-Object Count -gt 1
if ($dupes.Count -gt 0) {
    $report += ''
    $report += '### Duplicate local clones (same remote)'
    foreach ($d in $dupes) {
        $paths = ($d.Group | ForEach-Object { $_.Path }) -join ', '
        $report += "- $($d.Name): $paths"
    }
}

Set-Content -Path $ReportPath -Value ($report -join "`n")
Write-Output "Generated report: $ReportPath"
