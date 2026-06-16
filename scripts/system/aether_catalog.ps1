<#
  aether_catalog.ps1 — inventory every code repo, Obsidian vault, and big project
  on this machine; classify backup tier accurately; save a catalog.

  Backup tiers:
    GITHUB        repo has a GitHub/remote origin (versioned offsite)
    ONEDRIVE      lives under OneDrive (cloud-synced, incl. cloud-only placeholders)
    LOCAL-ONLY    on local disk, NOT in OneDrive, NO remote  <-- the real at-risk set

  Outputs to the user profile root:  AETHER-CATALOG.md  +  AETHER-CATALOG.json
  Run:  powershell -ExecutionPolicy Bypass -File scripts\system\aether_catalog.ps1
#>
param(
  [string]$Root = "C:\Users\issda",
  [string]$OutDir = "C:\Users\issda"
)
$ErrorActionPreference = "SilentlyContinue"
$env:Path = "C:\Program Files\Git\cmd;" + $env:Path
$skip = 'node_modules|pytest_temp_root|\\liboqs\\|AppData\\Local\\Temp|\.codex\\\.tmp|\$Recycle'

function Get-Tier($path) {
  $remote = git -C $path config --get remote.origin.url 2>$null
  if ($remote) { return @{ tier = 'GITHUB'; remote = $remote } }
  if ($path -match 'OneDrive') { return @{ tier = 'ONEDRIVE'; remote = $null } }
  return @{ tier = 'LOCAL-ONLY'; remote = $null }
}

Write-Host "Scanning $Root..."

# --- code repos ---
$repos = Get-ChildItem $Root -Recurse -Directory -Force -Filter ".git" |
  Where-Object { $_.FullName -notmatch $skip } |
  ForEach-Object { $_.Parent.FullName } | Sort-Object -Unique
$repoData = foreach ($r in $repos) {
  $t = Get-Tier $r
  [pscustomobject]@{ path = $r; tier = $t.tier; remote = $t.remote }
}

# --- obsidian vaults ---
$vaultDirs = Get-ChildItem $Root -Recurse -Directory -Force -Filter ".obsidian" |
  Where-Object { $_.FullName -notmatch $skip } |
  ForEach-Object { $_.Parent.FullName } | Sort-Object -Unique
# Mirror/plugin/repo content masquerading as notes — exclude from real counts.
$junk = 'Repository Mirror|\\external\\|plugin-backups|node_modules|\\\.obsidian\\|\\\.git\\'
$vaultData = foreach ($v in $vaultDirs) {
  $allMd = @(Get-ChildItem $v -Recurse -File -Filter *.md -Force)
  $md = @($allMd | Where-Object { $_.FullName -notmatch $junk })
  $tier = if ($v -match 'OneDrive') { 'ONEDRIVE' } else { 'LOCAL-ONLY' }
  [pscustomobject]@{
    path = $v; notes = $md.Count; mirror_files = ($allMd.Count - $md.Count)
    mb = [math]::Round((($md | Measure-Object Length -Sum).Sum) / 1MB, 1)
    last_edit = ($md | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime
    tier = $tier
  }
}

$riskRepos  = @($repoData  | Where-Object tier -eq 'LOCAL-ONLY')
$riskVaults = @($vaultData | Where-Object { $_.tier -eq 'LOCAL-ONLY' -and $_.notes -gt 0 })

# --- JSON ---
[pscustomobject]@{
  generated = (Get-Date).ToString('s')
  repos = $repoData; vaults = $vaultData
  summary = @{
    repos = $repoData.Count
    repos_github = @($repoData | Where-Object tier -eq 'GITHUB').Count
    repos_onedrive = @($repoData | Where-Object tier -eq 'ONEDRIVE').Count
    repos_local_only = $riskRepos.Count
    vaults = $vaultData.Count
    total_notes = ($vaultData | Measure-Object notes -Sum).Sum
    vaults_local_only = $riskVaults.Count
  }
} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $OutDir "AETHER-CATALOG.json") -Encoding UTF8

# --- Markdown ---
$md = New-Object System.Text.StringBuilder
[void]$md.AppendLine("# AETHER CATALOG  ($((Get-Date).ToString('yyyy-MM-dd HH:mm')))`n")
[void]$md.AppendLine("Backup tiers: **GITHUB** (offsite) | **ONEDRIVE** (cloud) | **LOCAL-ONLY** (at risk!)`n")
[void]$md.AppendLine("## !! TRULY AT RISK - local only, no cloud, no GitHub`n")
if ($riskRepos.Count -or $riskVaults.Count) {
  foreach ($x in $riskRepos)  { [void]$md.AppendLine("- repo:  $($x.path)") }
  foreach ($x in $riskVaults) { [void]$md.AppendLine("- vault: $($x.path)  ($($x.notes) notes)") }
} else { [void]$md.AppendLine("- (nothing - everything is on GitHub or OneDrive)") }
[void]$md.AppendLine("`n## Code repos ($($repoData.Count))`n")
[void]$md.AppendLine("| Tier | Repo |")
[void]$md.AppendLine("|---|---|")
foreach ($x in ($repoData | Sort-Object tier)) { [void]$md.AppendLine("| $($x.tier) | $($x.path) |") }
[void]$md.AppendLine("`n## Obsidian vaults ($($vaultData.Count))`n")
[void]$md.AppendLine("| Real notes | Mirror files | MB | Last edit | Tier | Path |")
[void]$md.AppendLine("|---|---|---|---|---|---|")
foreach ($v in ($vaultData | Sort-Object notes -Descending)) {
  $le = if ($v.last_edit) { $v.last_edit.ToString('yyyy-MM-dd') } else { '-' }
  [void]$md.AppendLine("| $($v.notes) | $($v.mirror_files) | $($v.mb) | $le | $($v.tier) | $($v.path) |")
}
$md.ToString() | Set-Content (Join-Path $OutDir "AETHER-CATALOG.md") -Encoding UTF8

Write-Host "`nCatalog saved. Repos: $($repoData.Count) (LOCAL-ONLY at risk: $($riskRepos.Count)) | Vaults: $($vaultData.Count) (at risk: $($riskVaults.Count))"
