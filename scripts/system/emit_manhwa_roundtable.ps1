param(
  [ValidateSet("codex", "opus", "keeper", "grok", "imagen", "kokoro", "issac", "editor")]
  [string]$Role = "codex",
  [string]$Recipient = "",
  [string]$TaskId = "MANHWA-ROUNDTABLE",
  [string]$Summary = "Manhwa roundtable update.",
  [string]$Status = "in_progress",
  [string]$NextAction = "",
  [string]$Risk = "low",
  [string[]]$Proof = @(),
  [switch]$NewSession = $false,
  [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$emitScript = Join-Path $PSScriptRoot "terminal_crosstalk_emit.ps1"

$roleMap = @{
  "codex" = @{
    Sender = "agent.codex"
    Codename = "Codex"
    Lane = "pipeline + packet + render/edit wiring"
    Recipient = "agent.claude"
  }
  "opus" = @{
    Sender = "agent.claude"
    Codename = "Opus"
    Lane = "ledger + canon + overlays + narrative review"
    Recipient = "agent.codex"
  }
  "keeper" = @{
    Sender = "agent.keeper"
    Codename = "Keeper"
    Lane = "world bible + style rules + canon continuity"
    Recipient = "agent.codex"
  }
  "grok" = @{
    Sender = "agent.grok"
    Codename = "Grok"
    Lane = "hero concept art + quality bar setting"
    Recipient = "agent.codex"
  }
  "imagen" = @{
    Sender = "agent.imagen"
    Codename = "Imagen"
    Lane = "generation batches + hero rerenders + QA picks"
    Recipient = "agent.codex"
  }
  "kokoro" = @{
    Sender = "agent.kokoro"
    Codename = "Kokoro"
    Lane = "TTS schema + narration + timing"
    Recipient = "agent.codex"
  }
  "issac" = @{
    Sender = "agent.issac"
    Codename = "Issac"
    Lane = "approval + creative direction + final decisions"
    Recipient = "agent.codex"
  }
  "editor" = @{
    Sender = "agent.editor"
    Codename = "Editor"
    Lane = "fine-edit packets + Photoshop/Canva/Adobe passes"
    Recipient = "agent.codex"
  }
}

$cfg = $roleMap[$Role]
if (-not $cfg) {
  throw "Unknown role: $Role"
}

if (-not $Recipient) {
  $Recipient = [string]$cfg.Recipient
}

$where = "repo:notes/manhwa-project + artifacts/webtoon"
$why = "keep long-run manhwa production synchronized across story, render, edit, and review lanes"
$how = "append-only packet relay + ledger mirrors + proof paths"
$workspace = "notes/manhwa-project"

if ($DryRun) {
  [pscustomobject]@{
    role = $Role
    sender = $cfg.Sender
    recipient = $Recipient
    codename = $cfg.Codename
    lane = $cfg.Lane
    task_id = $TaskId
    status = $Status
    summary = $Summary
    next_action = $NextAction
    where = $where
    why = $why
    how = $how
    proof = $Proof
    new_session = [bool]$NewSession
  } | ConvertTo-Json -Depth 4
  exit 0
}

& $emitScript `
  -WorkspacePath $workspace `
  -Sender $cfg.Sender `
  -Recipient $Recipient `
  -Intent "handoff" `
  -Status $Status `
  -TaskId $TaskId `
  -Summary $Summary `
  -NextAction $NextAction `
  -Risk $Risk `
  -Repo "SCBE-AETHERMOORE" `
  -Branch "local" `
  -Codename $cfg.Codename `
  -Where $where `
  -Why $why `
  -How $how `
  -Proof $Proof `
  -NewSession:$NewSession
