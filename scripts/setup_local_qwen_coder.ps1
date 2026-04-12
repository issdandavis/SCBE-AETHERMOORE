param(
    [string]$AgentId = "qwen-local",
    [string]$Model = "qwen2.5-coder:7b",
    [string]$Endpoint = "http://127.0.0.1:11434/v1",
    [string]$ContextFile = "notes/agent-memory/local-qwen-coder-context.md",
    [string]$MemoryLogFile = "notes/agent-memory/local-qwen-coder-memory.md",
    [switch]$EnsureTemplates,
    [switch]$RegisterAgent,
    [switch]$PullModel,
    [switch]$ShowNextSteps
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonExe = "python"
$scbeSystemCli = Join-Path $repoRoot "scripts\scbe-system-cli.py"
$contextPath = Join-Path $repoRoot $ContextFile
$memoryPath = Join-Path $repoRoot $MemoryLogFile

function Write-Step {
    param([string]$Message)
    Write-Host "[SCBE local-qwen] $Message"
}

function Ensure-File {
    param(
        [string]$Path,
        [string]$Content
    )
    $dir = Split-Path -Parent $Path
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    if (-not (Test-Path $Path)) {
        Set-Content -Path $Path -Value $Content -Encoding UTF8
        Write-Step "Created $Path"
    } else {
        Write-Step "Kept existing $Path"
    }
}

$contextTemplate = @"
# Local Qwen Coder Context

## Role
- You are my local SCBE coding assistant.
- Prefer concrete code changes, short plans, and explicit file references.

## Repository
- Repo: SCBE-AETHERMOORE
- Main code lanes: src/, scripts/, tests/, docs/, notes/
- Prioritize deterministic fixes, test evidence, and minimal diffs.

## Operator Preferences
- Keep responses concise.
- Explain risky assumptions before acting.
- When blocked, propose the smallest next command to run.

## Current Objectives
- Improve the SCBE CLI and agent loop.
- Use Obsidian notes as persistent working memory.
- Support local coding cycles with Qwen through Ollama.

## Session Scratchpad
- Replace this section with current goals, bugs, and active file paths.
"@

$memoryTemplate = @"
# Local Qwen Coder Memory

Use this note as an append-only cycle log.

## Current State
- First boot pending.
- Add stable facts here that the model should remember across manual cycles.
"@

if ($EnsureTemplates) {
    Ensure-File -Path $contextPath -Content $contextTemplate
    Ensure-File -Path $memoryPath -Content $memoryTemplate
}

if ($PullModel) {
    Write-Step "Pulling model $Model through Ollama"
    & ollama pull $Model
}

if ($RegisterAgent) {
    Write-Step "Registering agent $AgentId against $Endpoint"
    & $pythonExe $scbeSystemCli agent register `
        --agent-id $AgentId `
        --provider openai-compatible `
        --display-name "Local Qwen Coder" `
        --description "Local free coding model via Ollama with Obsidian-backed context and memory." `
        --model $Model `
        --endpoint $Endpoint `
        --system-prompt "You are my local SCBE-AETHERMOORE coding agent. Be concise, implementation-focused, and precise about files, commands, and verification." `
        --context-file $ContextFile `
        --memory-log-file $MemoryLogFile
}

if ($ShowNextSteps -or (-not $PullModel -and -not $RegisterAgent)) {
    Write-Host ""
    Write-Host "Next commands:"
    Write-Host "  1. .\scripts\setup_local_qwen_coder.ps1 -EnsureTemplates"
    Write-Host "  2. .\scripts\setup_local_qwen_coder.ps1 -PullModel"
    Write-Host "  3. .\scripts\setup_local_qwen_coder.ps1 -RegisterAgent"
    Write-Host "  4. python .\scripts\scbe-system-cli.py agent cycle --agent-id $AgentId --interactive --append-memory --show-context"
}
