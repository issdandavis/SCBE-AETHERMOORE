param(
  [string]$RepoRoot = "",
  [string]$VaultRoot = "",
  [string]$LibraryFolderName = "System Library",
  [switch]$PruneMirror
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
  $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
} else {
  $RepoRoot = (Resolve-Path $RepoRoot).Path
}

if (-not $VaultRoot) {
  $VaultRoot = Join-Path $RepoRoot "notes"
}
$VaultRoot = (Resolve-Path $VaultRoot).Path

$LibraryRoot = Join-Path $VaultRoot $LibraryFolderName
$MirrorRoot = Join-Path $LibraryRoot "Repository Mirror"
$IndexRoot = Join-Path $LibraryRoot "Indexes"

$IncludedExtensions = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
@(".md", ".mdx", ".txt", ".csv", ".json", ".mmd", ".yaml", ".yml") | ForEach-Object {
  $null = $IncludedExtensions.Add($_)
}

$ExcludedSegments = @(
  ".git",
  ".codex_tmp",
  "node_modules",
  "notes",
  "dist",
  "coverage",
  "htmlcov",
  "jupyter-runtime",
  "__pycache__",
  ".pytest_cache",
  ".hypothesis",
  ".venv",
  "venv"
)

function Get-RelativeRepoPath {
  param([string]$FullPath)
  return Get-RelativePathCrossPlatform -BasePath $RepoRoot -TargetPath $FullPath
}

function Get-RelativePathCrossPlatform {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  $normalizedBase = [System.IO.Path]::GetFullPath($BasePath)
  $normalizedTarget = [System.IO.Path]::GetFullPath($TargetPath)

  if (-not $normalizedBase.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
    $normalizedBase += [System.IO.Path]::DirectorySeparatorChar
  }

  $baseUri = [System.Uri]::new($normalizedBase)
  $targetUri = [System.Uri]::new($normalizedTarget)
  $relativeUri = $baseUri.MakeRelativeUri($targetUri)
  return [System.Uri]::UnescapeDataString($relativeUri.ToString()) -replace "/", "\"
}

function Test-IsExcludedPath {
  param([string]$RelativePath)

  $parts = $RelativePath -split "[\\/]"
  foreach ($part in $parts) {
    if ($ExcludedSegments -contains $part) {
      return $true
    }
  }
  return $false
}

function Get-TopLevelSourceRoot {
  param([string]$RelativePath)

  $parts = $RelativePath -split "[\\/]"
  if ($parts.Count -le 1) {
    return "Repository Root"
  }
  return $parts[0]
}

function Get-DocumentChannel {
  param([string]$RelativePath)

  $normalized = ($RelativePath -replace "\\", "/").ToLowerInvariant()

  if ($normalized -match "(^|/)(archive)(/|$)" -or $normalized -match "^docs/08-reference/archive/" -or $normalized -match "^docs/archive/") {
    return "Archive Channel"
  }

  if ($normalized -match "^(artifacts|benchmarks|training|training-data)/" -or
      $normalized -match "^docs/(evidence|eval|reports|tested-results|proof)/") {
    return "Generated and Evidence Channel"
  }

  if ($normalized -match "^(articles|content|paper|lore)/" -or
      $normalized -match "^docs/(articles|blog|news|research|proposals|market|offers|outreach|patent|theories-untested)/") {
    return "Research and Publication Channel"
  }

  if ($normalized -match "^docs/" -or
      $normalized -match "^(api|apps|automation|aws|demo|deliverables|examples|guides|workflows)/" -or
      $normalized -notmatch "/") {
    return "Main and Operational Channel"
  }

  return "Support and Working Channel"
}

function Ensure-Directory {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    $null = New-Item -ItemType Directory -Force -Path $Path
  }
}

function New-FrontmatterBlock {
  param(
    [string]$Title,
    [hashtable]$Fields
  )

  $lines = @("---", "title: $Title")
  foreach ($key in ($Fields.Keys | Sort-Object)) {
    $value = $Fields[$key]
    $lines += "${key}: $value"
  }
  $lines += "---", ""
  return $lines
}

function Write-Utf8File {
  param(
    [string]$Path,
    [string[]]$Lines
  )

  $content = ($Lines -join "`r`n") + "`r`n"
  [System.IO.File]::WriteAllText($Path, $content, [System.Text.UTF8Encoding]::new($false))
}

Ensure-Directory -Path $LibraryRoot
Ensure-Directory -Path $MirrorRoot
Ensure-Directory -Path $IndexRoot

$sourceFiles = New-Object System.Collections.Generic.List[object]

Get-ChildItem -Path $RepoRoot -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
  $relativePath = Get-RelativeRepoPath -FullPath $_.FullName
  if (Test-IsExcludedPath -RelativePath $relativePath) {
    return
  }
  if (-not $IncludedExtensions.Contains($_.Extension)) {
    return
  }

  $sourceFiles.Add([PSCustomObject]@{
      FullName     = $_.FullName
      RelativePath = $relativePath
      TopLevelRoot = Get-TopLevelSourceRoot -RelativePath $relativePath
      Channel      = Get-DocumentChannel -RelativePath $relativePath
      Extension    = $_.Extension
      LastWriteUtc = $_.LastWriteTimeUtc
    })
}

$expectedMirrorFiles = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
$skippedFiles = New-Object System.Collections.Generic.List[string]

foreach ($file in $sourceFiles) {
  $destinationPath = Join-Path $MirrorRoot $file.RelativePath
  $destinationDirectory = Split-Path -Parent $destinationPath
  Ensure-Directory -Path $destinationDirectory
  try {
    Copy-Item -LiteralPath $file.FullName -Destination $destinationPath -Force -ErrorAction Stop
    $null = $expectedMirrorFiles.Add($destinationPath)
  } catch {
    $skippedFiles.Add($file.RelativePath) | Out-Null
  }
}

if ($PruneMirror) {
  Get-ChildItem -Path $MirrorRoot -Recurse -File | Where-Object {
    $_.Name -ne "_folder_index.md" -and -not $expectedMirrorFiles.Contains($_.FullName)
  } | Remove-Item -Force
}

$mirrorFiles = Get-ChildItem -Path $MirrorRoot -Recurse -File | Where-Object { $_.Name -ne "_folder_index.md" }
$allDirectories = New-Object System.Collections.Generic.List[string]
$allDirectories.Add($MirrorRoot)
Get-ChildItem -Path $MirrorRoot -Recurse -Directory | ForEach-Object { $allDirectories.Add($_.FullName) }

foreach ($directoryPath in ($allDirectories | Sort-Object -Unique)) {
  $directoryItem = Get-Item -LiteralPath $directoryPath
  $directoryRelativeToVault = (Get-RelativePathCrossPlatform -BasePath $VaultRoot -TargetPath $directoryPath) -replace "\\", "/"
  $directoryRelativeToMirror = (Get-RelativePathCrossPlatform -BasePath $MirrorRoot -TargetPath $directoryPath) -replace "\\", "/"
  if ($directoryRelativeToMirror -eq ".") {
    $directoryTitle = "Repository Mirror"
    $sourcePathLabel = "Repository Root Mirror"
  } else {
    $directoryTitle = Split-Path -Leaf $directoryPath
    $sourcePathLabel = $directoryRelativeToMirror
  }

  $childDirectories = Get-ChildItem -LiteralPath $directoryPath -Directory | Sort-Object Name
  $childFiles = Get-ChildItem -LiteralPath $directoryPath -File | Where-Object { $_.Name -ne "_folder_index.md" } | Sort-Object Name

  $indexLines = @()
  $indexLines += @(New-FrontmatterBlock -Title "$directoryTitle Folder Index" -Fields @{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    mirror_path  = $directoryRelativeToVault
    source_path  = $sourcePathLabel
  })
  $indexLines += "# $directoryTitle Folder Index"
  $indexLines += ""
  $indexLines += ('Source path: `' + $sourcePathLabel + '`')
  $indexLines += ""
  $indexLines += "Immediate folders: $($childDirectories.Count)"
  $indexLines += "Immediate files: $($childFiles.Count)"
  $indexLines += ""

  if ($childDirectories.Count -gt 0) {
    $indexLines += "## Folders"
    $indexLines += ""
    foreach ($childDirectory in $childDirectories) {
      $childIndexRelative = (Get-RelativePathCrossPlatform -BasePath $directoryPath -TargetPath (Join-Path $childDirectory.FullName "_folder_index.md")) -replace "\\", "/"
      $indexLines += "- [$($childDirectory.Name)]($childIndexRelative)"
    }
    $indexLines += ""
  }

  if ($childFiles.Count -gt 0) {
    $indexLines += "## Files"
    $indexLines += ""
    foreach ($childFile in $childFiles) {
      $childFileRelative = (Get-RelativePathCrossPlatform -BasePath $directoryPath -TargetPath $childFile.FullName) -replace "\\", "/"
      $indexLines += "- [$($childFile.Name)]($childFileRelative)"
    }
    $indexLines += ""
  }

  Write-Utf8File -Path (Join-Path $directoryPath "_folder_index.md") -Lines $indexLines
}

$bySourceRoot = $sourceFiles | Group-Object TopLevelRoot | Sort-Object Name
$byChannel = $sourceFiles | Group-Object Channel | Sort-Object Name
$sourceRootCount = @{}
foreach ($group in $bySourceRoot) {
  $sourceRootCount[$group.Name] = $group.Count
}

function Get-SourceRootTarget {
  param([string]$SourceRoot)

  if ($SourceRoot -eq "Repository Root") {
    return "Repository Mirror/_folder_index.md"
  }

  return "Repository Mirror/$SourceRoot/_folder_index.md"
}

$sourceRootLines = @()
$sourceRootLines += @(New-FrontmatterBlock -Title "Source Roots Index" -Fields @{
  generated_at = (Get-Date).ToUniversalTime().ToString("o")
  mirrored_document_count = $sourceFiles.Count
})
$sourceRootLines += "# Source Roots Index"
$sourceRootLines += ""
$sourceRootLines += "This note groups mirrored repository documents by their original top-level source root."
$sourceRootLines += ""
$sourceRootLines += "## Source Roots"
$sourceRootLines += ""
foreach ($group in $bySourceRoot) {
  $folderPath = Get-SourceRootTarget -SourceRoot $group.Name
  $sourceRootLines += "- [$($group.Name)](../$folderPath) - $($group.Count) files"
}
Write-Utf8File -Path (Join-Path $IndexRoot "Source Roots.md") -Lines $sourceRootLines

$channelLines = @()
$channelLines += @(New-FrontmatterBlock -Title "Document Channels Index" -Fields @{
  generated_at = (Get-Date).ToUniversalTime().ToString("o")
  mirrored_document_count = $sourceFiles.Count
})
$channelLines += "# Document Channels Index"
$channelLines += ""
$channelLines += "This note groups mirrored repository documents by navigation channel."
$channelLines += ""
$channelLines += "## Channels"
$channelLines += ""
foreach ($group in $byChannel) {
  $channelLines += "### $($group.Name)"
  foreach ($rootGroup in ($group.Group | Group-Object TopLevelRoot | Sort-Object Name)) {
    $folderPath = Get-SourceRootTarget -SourceRoot $rootGroup.Name
    $channelLines += "- [$($rootGroup.Name)](../$folderPath) - $($rootGroup.Count) files"
  }
  $channelLines += ""
}
Write-Utf8File -Path (Join-Path $IndexRoot "Document Channels.md") -Lines $channelLines

$coreSystemRoots = @(
  "docs",
  "src",
  "scripts",
  "tests",
  "training-data",
  "artifacts",
  "config",
  "workflows",
  "skills",
  "schemas",
  "policies",
  "api",
  "agents",
  "models",
  "Repository Root"
)

$researchRoots = @(
  "articles",
  "content",
  "deliverables",
  "demo",
  "examples",
  "shopify",
  "spiralverse-protocol",
  "kindle-app"
)

$archiveRoots = @(
  "external",
  "external_repos",
  "_staging",
  "training",
  "training-runs",
  "docs-build-smoke",
  "exports"
)

$curatedLines = @()
$curatedLines += @(New-FrontmatterBlock -Title "Curated Navigation" -Fields @{
  generated_at = (Get-Date).ToUniversalTime().ToString("o")
  mirrored_document_count = $sourceFiles.Count
})
$curatedLines += "# Curated Navigation"
$curatedLines += ""
$curatedLines += "This note puts the live system areas first, then research surfaces, then heavy archives and vendor mirrors."
$curatedLines += ""
$curatedLines += "## Core System"
$curatedLines += ""
foreach ($root in $coreSystemRoots) {
  if ($sourceRootCount.ContainsKey($root)) {
    $curatedLines += "- [$root](../$(Get-SourceRootTarget -SourceRoot $root)) - $($sourceRootCount[$root]) files"
  }
}
$curatedLines += ""
$curatedLines += "## Research and Publication"
$curatedLines += ""
foreach ($root in $researchRoots) {
  if ($sourceRootCount.ContainsKey($root)) {
    $curatedLines += "- [$root](../$(Get-SourceRootTarget -SourceRoot $root)) - $($sourceRootCount[$root]) files"
  }
}
$curatedLines += ""
$curatedLines += "## Archives, Experiments, and Vendor Mirrors"
$curatedLines += ""
foreach ($root in $archiveRoots) {
  if ($sourceRootCount.ContainsKey($root)) {
    $curatedLines += "- [$root](../$(Get-SourceRootTarget -SourceRoot $root)) - $($sourceRootCount[$root]) files"
  }
}
Write-Utf8File -Path (Join-Path $IndexRoot "Curated Navigation.md") -Lines $curatedLines

$homeLines = @()
$homeLines += @(New-FrontmatterBlock -Title "System Library Home" -Fields @{
  generated_at = (Get-Date).ToUniversalTime().ToString("o")
  mirrored_document_count = $sourceFiles.Count
  vault_root = $VaultRoot
})
$homeLines += "# System Library Home"
$homeLines += ""
$homeLines += "This library mirrors repository documentation-shaped text into the Obsidian vault for navigation and search."
$homeLines += ""
$homeLines += "## Summary"
$homeLines += ""
$homeLines += "- Mirrored document count: $($sourceFiles.Count)"
$homeLines += "- Skipped unreadable or transient files: $($skippedFiles.Count)"
$homeLines += ('- Vault root: `' + $VaultRoot + '`')
$homeLines += ('- Repository root: `' + $RepoRoot + '`')
$homeLines += ""
$homeLines += "## Navigation"
$homeLines += ""
$homeLines += "- [Curated Navigation](Indexes/Curated Navigation.md)"
$homeLines += "- [Repository Mirror](Repository Mirror/_folder_index.md)"
$homeLines += "- [Source Roots](Indexes/Source Roots.md)"
$homeLines += "- [Document Channels](Indexes/Document Channels.md)"
$homeLines += ""
$homeLines += "## Start Here"
$homeLines += ""
foreach ($root in $coreSystemRoots) {
  if ($sourceRootCount.ContainsKey($root)) {
    $homeLines += "- [$root]($(Get-SourceRootTarget -SourceRoot $root)) - $($sourceRootCount[$root]) files"
  }
}
$homeLines += ""
$homeLines += "## Heavy Mirrors and Archives"
$homeLines += ""
foreach ($root in $archiveRoots) {
  if ($sourceRootCount.ContainsKey($root)) {
    $homeLines += "- [$root]($(Get-SourceRootTarget -SourceRoot $root)) - $($sourceRootCount[$root]) files"
  }
}
Write-Utf8File -Path (Join-Path $LibraryRoot "Home.md") -Lines $homeLines

Write-Host "Mirrored $($sourceFiles.Count) documents into $LibraryRoot"
Write-Host "Home note: $(Join-Path $LibraryRoot 'Home.md')"
