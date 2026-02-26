param(
    [string]$RepoRoot = "C:/Users/issda/SCBE-AETHERMOORE",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$skillRoot = "C:/Users/issda/.codex/skills/scbe-research-publishing-autopilot/scripts"
$artifacts = Join-Path $RepoRoot "artifacts/social"
$examples = Join-Path $RepoRoot "automation/social/examples"

New-Item -ItemType Directory -Force $artifacts | Out-Null
Copy-Item "$examples/*" $artifacts -Force

$posts = Join-Path $artifacts "campaign_posts.x-monetize.json"
$campaign = Join-Path $artifacts "campaign.x-monetize.json"
$connectors = Join-Path $artifacts "connectors.n8n.json"
$approvals = Join-Path $artifacts "approvals.x-monetize.json"
$claimReport = Join-Path $artifacts "claim_gate_report.json"
$plan = Join-Path $artifacts "dispatch_plan.json"
$dispatchLog = Join-Path $artifacts "dispatch_log.jsonl"
$dispatchState = Join-Path $artifacts "dispatch_state.json"

python "$skillRoot/claim_gate.py" `
  --posts $posts `
  --repo-root $RepoRoot `
  --out $claimReport

python "$skillRoot/campaign_orchestrator.py" `
  --campaign $campaign `
  --out $plan

$args = @(
  "$skillRoot/publish_dispatch.py",
  "--plan", $plan,
  "--posts", $posts,
  "--connectors", $connectors,
  "--approval", $approvals,
  "--claim-report", $claimReport,
  "--out-log", $dispatchLog,
  "--state", $dispatchState
)

if ($DryRun) {
  $args += "--dry-run"
}

python @args

Write-Host "Done. Artifacts at: $artifacts"

