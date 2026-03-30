param(
  # Source directory containing Codex skills (outside repo by default).
  [string]$Source = "$env:USERPROFILE\\.codex\\skills",
  # Destination inside this repo so MCP filesystem can read it.
  [string]$Dest = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")).Path "artifacts\\codex_skills_mirror"),
  # Optional: copy only specific skills (directory names under $Source).
  [string[]]$Skill = @(),
  # If set, copy all skills under $Source (ignores -Skill list).
  [switch]$All
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Source)) {
  throw "Codex skills source not found: $Source"
}

New-Item -ItemType Directory -Force -Path $Dest | Out-Null

$allowedExt = @(
  ".md", ".txt",
  ".py",
  ".ps1", ".sh",
  ".json", ".jsonl",
  ".yml", ".yaml",
  ".js", ".mjs", ".cjs",
  ".ts", ".tsx",
  ".html", ".css", ".scss",
  ".toml", ".ini", ".cfg",
  ".csv"
)

function Copy-SkillFiles([string]$skillName) {
  $srcDir = Join-Path $Source $skillName
  if (-not (Test-Path $srcDir)) {
    # Some skills live under .codex/skills/.system/<name>
    $altDir = Join-Path (Join-Path $Source ".system") $skillName
    if (Test-Path $altDir) {
      $srcDir = $altDir
    } else {
      Write-Warning "Skip missing skill dir: $skillName"
      return
    }
  }

  $dstDir = Join-Path $Dest $skillName
  New-Item -ItemType Directory -Force -Path $dstDir | Out-Null

  $files = Get-ChildItem -Path $srcDir -Recurse -File -ErrorAction SilentlyContinue
  foreach ($f in $files) {
    $ext = ($f.Extension ?? "").ToLowerInvariant()
    if (-not ($allowedExt -contains $ext)) { continue }

    $rel = $f.FullName.Substring($srcDir.Length).TrimStart("\\")
    $outPath = Join-Path $dstDir $rel
    $outDir = Split-Path $outPath -Parent
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    Copy-Item -Force -Path $f.FullName -Destination $outPath
  }

  # Always copy SKILL.md if it exists (even if extension filters change later).
  $skillMd = Join-Path $srcDir "SKILL.md"
  if (Test-Path $skillMd) {
    Copy-Item -Force -Path $skillMd -Destination (Join-Path $dstDir "SKILL.md")
  }
}

$skillNames = @()
if ($All) {
  $skillNames = Get-ChildItem -Path $Source -Directory | Select-Object -ExpandProperty Name
} elseif ($Skill.Count -gt 0) {
  $skillNames = $Skill
} else {
  # Safe default: mirror only the core ops/training skills we routinely need.
  $skillNames = @(
    "skill-creator",
    "skill-installer",
    "skill-synthesis",
    "skill-update",
    "gh-fix-ci",
    "hugging-face-cli",
    "hf-publish-workflow",
    "hugging-face-datasets",
    "hugging-face-model-trainer",
    "scbe-meridian-flush",
    "scbe-workflow-cultivation"
  )
}

foreach ($name in $skillNames) {
  Copy-SkillFiles $name
}

Write-Output "Mirrored $($skillNames.Count) skill(s) into: $Dest"
