param(
    [string]$Target = "help",
    [switch]$Open,
    [switch]$Explorer
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$homeRoot = [Environment]::GetFolderPath("UserProfile")

$targets = [ordered]@{
    "repo"             = $repoRoot
    "roots"            = Join-Path $repoRoot ".roots"
    "repo-home"        = Join-Path $repoRoot ".home"
    "repo-home-agents" = Join-Path $repoRoot ".home\.agents"
    "repo-home-plugins" = Join-Path $repoRoot ".home\plugins"
    "docs"             = Join-Path $repoRoot "docs"
    "notes"            = Join-Path $repoRoot "notes"
    "loop-records"     = Join-Path $repoRoot ".scbe\loop_records"
    "runners"          = Join-Path $repoRoot ".scbe\runners"
    "repo-marketplace" = Join-Path $repoRoot ".agents\plugins\marketplace.json"
    "home-marketplace" = Join-Path $homeRoot ".agents\plugins\marketplace.json"
    "home-agents"      = Join-Path $homeRoot ".agents"
    "repo-plugins"     = Join-Path $repoRoot "plugins"
    "home-plugins"     = Join-Path $homeRoot "plugins"
    "aetherbrowse-repo" = Join-Path $repoRoot "plugins\aetherbrowse"
    "aetherbrowse-home" = Join-Path $homeRoot "plugins\aetherbrowse"
    "nonstop-repo"     = Join-Path $repoRoot "plugins\nonstop"
    "nonstop-home"     = Join-Path $homeRoot "plugins\nonstop"
    "codex-home"       = Join-Path $homeRoot ".codex"
    "codex-skills"     = Join-Path $homeRoot ".codex\skills"
    "tokenizer-vault"  = Join-Path $repoRoot "notes\System Library\Tokenizer Vault"
    "plugins-vault"    = Join-Path $repoRoot "notes\System Library\Plugins Vault"
    "surface-map"      = Join-Path $repoRoot "docs\operations\LOCAL_SURFACE_QUICK_MAP.md"
}

function Show-Targets {
    Write-Host "SCBE local navigation targets`n"
    foreach ($entry in $targets.GetEnumerator()) {
        $exists = if (Test-Path $entry.Value) { "yes" } else { "no" }
        "{0,-18} {1,-3} {2}" -f $entry.Key, $exists, $entry.Value
    }

    Write-Host "`nExamples:"
    Write-Host "  pwsh -File scripts/system/scbe_nav.ps1 notes"
    Write-Host "  pwsh -File scripts/system/scbe_nav.ps1 home-marketplace -Open"
    Write-Host "  pwsh -File scripts/system/scbe_nav.ps1 plugins-vault -Open"
}

if ($Target -in @("help", "list", "targets", "?")) {
    Show-Targets
    exit 0
}

if (-not $targets.Contains($Target)) {
    Write-Error "Unknown target '$Target'. Run with 'help' to list valid names."
    exit 1
}

$resolved = $targets[$Target]
Write-Output $resolved

if (-not (Test-Path $resolved)) {
    Write-Warning "Target path does not exist: $resolved"
    exit 0
}

if ($Open -or $Explorer) {
    if (Test-Path $resolved -PathType Container) {
        Invoke-Item $resolved
    }
    else {
        Start-Process notepad.exe $resolved
    }
}
