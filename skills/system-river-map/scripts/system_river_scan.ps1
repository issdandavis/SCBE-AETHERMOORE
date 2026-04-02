[CmdletBinding()]
param(
  [string]$UserRoot = $env:USERPROFILE,
  [string]$RepoRoot = (Get-Location).Path,
  [string]$OutputDir = "artifacts/system-river-map"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RootSummary {
  param([string]$Path, [string]$Role)

  $exists = Test-Path -LiteralPath $Path
  $children = @()
  $errorText = $null
  $attributes = $null
  $itemType = $null

  if ($exists) {
    try {
      $item = Get-Item -LiteralPath $Path -Force
      $attributes = $item.Attributes.ToString()
      $itemType = if ($item.PSIsContainer) { "directory" } else { "file" }
      if ($item.PSIsContainer) {
        $children = @(Get-ChildItem -LiteralPath $Path -Force -ErrorAction Stop | Select-Object -ExpandProperty Name)
      }
    } catch {
      $errorText = $_.Exception.Message
    }
  }

  [pscustomobject]@{
    path = $Path
    role = $Role
    exists = $exists
    item_type = $itemType
    attributes = $attributes
    children = $children
    error = $errorText
  }
}

function Get-DriveSummary {
  Get-PSDrive -PSProvider FileSystem | Sort-Object Name | ForEach-Object {
    [pscustomobject]@{
      name = $_.Name
      root = $_.Root
      used_bytes = [int64]$_.Used
      free_bytes = [int64]$_.Free
    }
  }
}

function Get-TopLevelReparsePoints {
  param([string]$Path)

  if (-not (Test-Path -LiteralPath $Path)) {
    return @()
  }

  @(Get-ChildItem -LiteralPath $Path -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Attributes -match "ReparsePoint" } |
    ForEach-Object {
      $targets = @($_.Target | Where-Object { $_ })
      $targetText = if ($targets.Count -gt 0) { $targets -join "; " } else { $null }
      $reachableTargets = @($targets | Where-Object { Test-Path -LiteralPath $_ })
      $targetStatus =
        if ($targets.Count -eq 0) {
          "unresolved"
        } elseif ($reachableTargets.Count -gt 0) {
          "reachable"
        } else {
          "dry"
        }

      [pscustomobject]@{
        name = $_.Name
        full_name = $_.FullName
        link_type = $_.LinkType
        target = $targetText
        target_exists = ($reachableTargets.Count -gt 0)
        target_status = $targetStatus
        attributes = $_.Attributes.ToString()
      }
    })
}

function New-MarkdownReport {
  param($Scan)

  $lines = @()
  $lines += "# System River Scan"
  $lines += ""
  $lines += "- Generated: $($Scan.generated_at_utc)"
  $lines += "- User root: $($Scan.user_root)"
  $lines += "- Repo root: $($Scan.repo_root)"
  $lines += ""
  $lines += "## Drives"
  $lines += ""

  foreach ($drive in $Scan.drives) {
    $lines += ('- `{0}:` root `{1}` free={2} used={3}' -f $drive.name, $drive.root, $drive.free_bytes, $drive.used_bytes)
  }

  $lines += ""
  $lines += "## Root Channels"
  $lines += ""

  foreach ($root in $Scan.roots) {
    $childPreview = if ($root.children.Count -gt 0) {
      ($root.children | Select-Object -First 12) -join ", "
    } else {
      ""
    }
    $lines += ('- `{0}` [{1}] exists={2} type={3} attrs="{4}"' -f $root.path, $root.role, $root.exists, $root.item_type, $root.attributes)
    if ($childPreview) {
      $lines += ('  children: {0}' -f $childPreview)
    }
    if ($root.error) {
      $lines += ('  error: {0}' -f $root.error)
    }
  }

  $lines += ""
  $lines += "## Top-Level Reparse Points"
  $lines += ""

  foreach ($rp in $Scan.reparse_points) {
    $lines += ('- `{0}` type={1} target="{2}" status={3} attrs="{4}"' -f $rp.full_name, $rp.link_type, $rp.target, $rp.target_status, $rp.attributes)
  }

  $lines += ""
  $lines += "## Routing Hints"
  $lines += ""
  $lines += "- Prefer the live repo and canonical Drive roots for active work."
  $lines += "- Treat Dropbox current as a volatile sync edge."
  $lines += "- Treat Dropbox (Old) and external drives as archive/offload lanes."
  $lines += "- Treat unresolved reparse points as dry channels until the target exists."
  $lines += "- Treat permission errors as gated channels, not missing channels."
  $lines += ""

  $lines -join "`r`n"
}

$resolvedRepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$resolvedOutputDir = Join-Path $resolvedRepoRoot $OutputDir

New-Item -ItemType Directory -Force -Path $resolvedOutputDir | Out-Null

$roots = @(
  @{ Path = $UserRoot; Role = "profile-basin" }
  @{ Path = (Join-Path $UserRoot "SCBE-AETHERMOORE"); Role = "live-repo" }
  @{ Path = (Join-Path $UserRoot "Drive"); Role = "drive-sync-root" }
  @{ Path = (Join-Path $UserRoot "Drive\\SCBE"); Role = "canonical-scbe-root" }
  @{ Path = (Join-Path $UserRoot "Drive\\SCBE\\local-workspace-sync"); Role = "canonical-sync-ledger" }
  @{ Path = (Join-Path $UserRoot "Dropbox"); Role = "current-dropbox-edge" }
  @{ Path = (Join-Path $UserRoot "Dropbox (Old)"); Role = "archive-dropbox-root" }
  @{ Path = (Join-Path $UserRoot "Dropbox (Old)\\SCBE"); Role = "archive-scbe-root" }
  @{ Path = (Join-Path $UserRoot "OneDrive"); Role = "onedrive-root" }
  @{ Path = (Join-Path $UserRoot "OneDrive\\Offload"); Role = "onedrive-offload-lane" }
  @{ Path = "E:\\"; Role = "external-basin-e" }
  @{ Path = "F:\\"; Role = "external-basin-f" }
  @{ Path = "S:\\"; Role = "gated-basin-s" }
  @{ Path = "D:\\"; Role = "dry-or-unmounted-d" }
)

$scan = [pscustomobject]@{
  generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
  user_root = $UserRoot
  repo_root = $resolvedRepoRoot
  drives = @(Get-DriveSummary)
  roots = @($roots | ForEach-Object { Get-RootSummary -Path $_.Path -Role $_.Role })
  reparse_points = @(Get-TopLevelReparsePoints -Path $UserRoot)
}

$jsonPath = Join-Path $resolvedOutputDir "latest.json"
$mdPath = Join-Path $resolvedOutputDir "latest.md"

$scan | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
New-MarkdownReport -Scan $scan | Set-Content -LiteralPath $mdPath -Encoding UTF8

Write-Host "Wrote $jsonPath"
Write-Host "Wrote $mdPath"
