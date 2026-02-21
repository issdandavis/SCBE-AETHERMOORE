param(
  [string]$DbPath = "artifacts/hydra/headless_ide/switchboard.db",
  [string]$OutDir = "artifacts/hydra/headless_ide",
  [string]$Workspace = "."
)

$ErrorActionPreference = "Stop"

python scripts/scbe_headless_ide_demo.py --db $DbPath --out-dir $OutDir --workspace $Workspace

Write-Host ""
Write-Host "Open dashboard:"
Write-Host "$OutDir/headless_ide_dashboard.html"
