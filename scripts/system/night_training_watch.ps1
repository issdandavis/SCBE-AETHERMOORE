param(
  [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE",
  [string]$HfJobId = "69f83c4998a8d679adfb8ddd",
  [string]$KaggleRound = "coding-approval-metrics-v2",
  [string]$KaggleKernel = "issacizrealdavis/polly-auto-coding-approval-metrics-v1"
)

$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

Set-Location -LiteralPath $RepoRoot

python scripts/system/night_training_watch.py `
  --hf-job-id $HfJobId `
  --kaggle-round $KaggleRound `
  --kaggle-kernel $KaggleKernel `
  --json
