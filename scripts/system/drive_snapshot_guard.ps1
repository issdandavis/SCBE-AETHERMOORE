<#
.SYNOPSIS
  Cap the local workspace-snapshot store at a fixed number of newest snapshots.

.DESCRIPTION
  SCBE-LocalCloudSync writes a timestamped snapshot folder (e.g. 20260608T012734Z)
  into -Root every run. Without pruning these accumulate without bound and fill the
  disk. This guard keeps only the -KeepLatest newest snapshot folders and removes the
  rest (when -Prune is set), then reports free space and warns below -WarnFreeGB.

  Snapshot folder names are UTC timestamps (yyyyMMddTHHmmssZ), so lexical sort == age
  sort. The newest -KeepLatest are retained; everything older is a prune candidate.

  Called by the scheduled task "SCBE-DriveSnapshotGuard". Re-creating this file fixes
  the runaway-snapshot disk fill (the task referenced a script that did not exist, so
  every run exited non-zero and never pruned).

.PARAMETER Root
  Directory that holds the timestamped snapshot folders.

.PARAMETER KeepLatest
  Number of newest snapshot folders to keep. Default 15.

.PARAMETER WarnFreeGB
  Emit a warning if C: free space is below this after pruning. Default 25.

.PARAMETER Prune
  Actually delete old snapshots. Without this switch the script is a dry run and only
  reports what it would remove.

.EXAMPLE
  pwsh -File drive_snapshot_guard.ps1 -Root "C:\Users\issda\Drive\SCBE\local-workspace-sync" -KeepLatest 15 -WarnFreeGB 25 -Prune
#>
param(
  [Parameter(Mandatory = $true)] [string] $Root,
  [int] $KeepLatest = 15,
  [int] $WarnFreeGB = 25,
  [switch] $Prune
)

$ErrorActionPreference = "Stop"

function Get-FreeGB {
  $d = Get-PSDrive -Name C -ErrorAction SilentlyContinue
  if ($d) { return [Math]::Round($d.Free / 1GB, 2) }
  return $null
}

if (-not (Test-Path -LiteralPath $Root)) {
  Write-Host "drive_snapshot_guard: Root not found: $Root"
  # Nothing to prune is not a failure — the task should stay green.
  exit 0
}

if ($KeepLatest -lt 1) { $KeepLatest = 1 }

# Snapshot folders only; names sort lexically == chronologically.
$snaps = Get-ChildItem -LiteralPath $Root -Directory -Force -ErrorAction SilentlyContinue |
  Sort-Object Name

$total = @($snaps).Count
Write-Host "=== drive_snapshot_guard ==="
Write-Host "Root:        $Root"
Write-Host "Snapshots:   $total   KeepLatest: $KeepLatest   Prune: $($Prune.IsPresent)"
Write-Host "Free before: $(Get-FreeGB) GB"

if ($total -le $KeepLatest) {
  Write-Host "Nothing to prune (have $total, keeping $KeepLatest)."
  $free = Get-FreeGB
  if ($free -ne $null -and $free -lt $WarnFreeGB) {
    Write-Warning "C: free ${free} GB is below WarnFreeGB ${WarnFreeGB} GB."
  }
  exit 0
}

# Oldest-first candidates = everything except the newest KeepLatest.
$remove = $snaps | Select-Object -First ($total - $KeepLatest)
Write-Host "Prune candidates: $(@($remove).Count) (oldest $(@($remove)[0].Name) .. newest-removed $(@($remove)[-1].Name))"

$freedBytes = 0L
$removed = 0
$failed = 0
foreach ($s in $remove) {
  try {
    $sz = (Get-ChildItem -LiteralPath $s.FullName -Recurse -File -Force -ErrorAction SilentlyContinue |
      Measure-Object Length -Sum).Sum
    if (-not $sz) { $sz = 0 }
    if ($Prune) {
      Remove-Item -LiteralPath $s.FullName -Recurse -Force -ErrorAction Stop
      $freedBytes += $sz
      $removed++
    } else {
      Write-Host "  [dry-run] would remove $($s.Name)  ($([Math]::Round($sz/1MB,1)) MB)"
      $freedBytes += $sz
    }
  } catch {
    $failed++
    Write-Warning "  failed to remove $($s.Name): $($_.Exception.Message)"
  }
}

$verb = if ($Prune) { "Removed" } else { "Would free" }
Write-Host "$verb $removed snapshot(s), ~$([Math]::Round($freedBytes/1GB,2)) GB. Failures: $failed."
$free = Get-FreeGB
Write-Host "Free after:  ${free} GB"
if ($free -ne $null -and $free -lt $WarnFreeGB) {
  Write-Warning "C: free ${free} GB is below WarnFreeGB ${WarnFreeGB} GB."
}

# Stay green for the scheduler unless we genuinely could not prune anything we tried.
if ($Prune -and $removed -eq 0 -and $failed -gt 0) { exit 1 }
exit 0
