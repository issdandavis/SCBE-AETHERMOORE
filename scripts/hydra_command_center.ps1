Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ((Get-Variable -Scope Script -Name IssacCommandCenterLoaded -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Value -ErrorAction SilentlyContinue)) {
    return
}

$script:IssacCommandCenterLoaded = $true
$script:IssacCommandCenterRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$script:IssacHydraArtifactDir = Join-Path $script:IssacCommandCenterRoot "artifacts\hydra"
$script:IssacHydraLedgerPath = Join-Path $script:IssacHydraArtifactDir "ledger.db"
if (-not (Test-Path $script:IssacHydraArtifactDir)) {
    New-Item -ItemType Directory -Path $script:IssacHydraArtifactDir -Force | Out-Null
}
if ([string]::IsNullOrWhiteSpace($env:HYDRA_LEDGER_DB)) {
    $env:HYDRA_LEDGER_DB = $script:IssacHydraLedgerPath
}
$script:IssacHydraShim = Join-Path $script:IssacCommandCenterRoot "scripts\hydra.ps1"
$script:IssacSkillSummary = Join-Path $script:IssacCommandCenterRoot "artifacts\skill_synthesis\summary.md"
$script:IssacSkillRefreshScript = Join-Path $script:IssacCommandCenterRoot "scripts\system\refresh_universal_skill_synthesis.py"
$script:IssacSkillStackScript = "C:\Users\issda\.codex\skills\skill-synthesis\scripts\compose_skill_stack.py"
$script:IssacCrossTalkRelay = Join-Path $script:IssacCommandCenterRoot "scripts\system\crosstalk_relay.py"
$script:IssacActionMapScript = Join-Path $script:IssacCommandCenterRoot "scripts\system\action_map_protocol.py"
$script:IssacBrowserService = Join-Path $script:IssacCommandCenterRoot "scripts\run_aetherbrowse_service.ps1"
$script:IssacHydraTunnel = Join-Path $script:IssacCommandCenterRoot "scripts\system\start_hydra_terminal_tunnel.ps1"
$script:IssacGoalRaceScript = Join-Path $script:IssacCommandCenterRoot "scripts\system\goal_race_loop.py"
$script:IssacAetherbrowserSearchScript = Join-Path $script:IssacCommandCenterRoot "scripts\system\aetherbrowser_search.py"
$script:IssacGithubSweepScript = Join-Path $script:IssacCommandCenterRoot "scripts\system\run_github_sweep.py"
$script:IssacGithubNavScript = Join-Path $script:IssacCommandCenterRoot "scripts\system\aetherbrowser_github_nav.py"
$script:IssacYoutubeTranscriptScript = Join-Path $script:IssacCommandCenterRoot "scripts\system\youtube_transcript_pull.py"
$script:IssacColabCatalogScript = Join-Path $script:IssacCommandCenterRoot "scripts\system\colab_workflow_catalog.py"
$script:IssacColabBridgeScript = "C:\Users\issda\.codex\skills\scbe-n8n-colab-bridge\scripts\colab_n8n_bridge.py"
$script:IssacDeepResearchLoop = Join-Path $script:IssacCommandCenterRoot "scripts\system\run_deep_research_self_healing.ps1"
$script:IssacWorkflowVectorScript = Join-Path $script:IssacCommandCenterRoot "scripts\system\workflow_vector.py"
$script:IssacPostAllScript = Join-Path $script:IssacCommandCenterRoot "scripts\publish\post_all.py"
$script:IssacDailyTrainingWaveScript = Join-Path $script:IssacCommandCenterRoot "scripts\daily_training_wave.py"
$script:IssacGenerateSftScript = Join-Path $script:IssacCommandCenterRoot "scripts\generate_sft_from_modules.py"
$script:IssacHfTrainingLoopScript = Join-Path $script:IssacCommandCenterRoot "scripts\hf_training_loop.py"
$script:IssacN8nWorkflowDir = Join-Path $script:IssacCommandCenterRoot "workflows\n8n"
$script:IssacVoiceSpec = Join-Path $script:IssacCommandCenterRoot "docs\specs\SCBE_VOICE_EMOTIONAL_TIMBRE_SYSTEM.md"
$script:IssacVoiceManifest = Join-Path $script:IssacCommandCenterRoot "artifacts\voice\manifest.json"
$script:IssacVoiceStatusPacket = Join-Path $script:IssacCommandCenterRoot "artifacts\agent_comm\webtoon_pipeline_status.json"
$script:IssacVoiceGatePacket = Join-Path $script:IssacCommandCenterRoot "artifacts\agent_comm\20260315\cross-talk-agent-codex-stp-webtoon-voice-gate-20260315T012938Z.json"
$script:IssacVoiceProsodyResearch = Join-Path $script:IssacCommandCenterRoot "artifacts\research\arxiv\long_form_tts_prosody.json"
$script:IssacVideoPromptsDoc = Join-Path $script:IssacCommandCenterRoot "content\marketing\AI_VIDEO_PROMPTS_INTRO.md"
$script:IssacLayer9AudioAxisScript = Join-Path $script:IssacCommandCenterRoot "scripts\layer9_spectral_coherence.py"

function Get-IssacRepoRoot {
    return $script:IssacCommandCenterRoot
}

function Join-IssacText {
    param([string[]]$Parts)
    return (($Parts | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join " ").Trim()
}

function Assert-IssacText {
    param(
        [string]$Value,
        [string]$Usage
    )
    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw $Usage
    }
}

function Invoke-IssacInRepo {
    param([scriptblock]$Action)
    $previous = Get-Location
    try {
        Set-Location $script:IssacCommandCenterRoot
        & $Action
    } finally {
        Set-Location $previous
    }
}

function Invoke-IssacHydra {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$HydraArgs)
    Invoke-IssacInRepo {
        & $script:IssacHydraShim --no-banner @HydraArgs
    }
}

function Invoke-IssacPythonFile {
    param(
        [string]$FilePath,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$ScriptArgs
    )
    Invoke-IssacInRepo {
        & python $FilePath @ScriptArgs
    }
}

function Invoke-IssacPwshFile {
    param(
        [string]$FilePath,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$ScriptArgs
    )
    Invoke-IssacInRepo {
        & $FilePath @ScriptArgs
    }
}

function Invoke-IssacCascadeStep {
    param(
        [string]$Label,
        [scriptblock]$Action,
        [switch]$DryRun
    )
    Write-Host ("[{0}] {1}" -f ($(if ($DryRun) { "plan" } else { "run" }), $Label)) -ForegroundColor Cyan
    if ($DryRun) {
        return [pscustomobject]@{
            label = $Label
            status = "planned"
        }
    }
    & $Action
}

function Get-IssacN8nTemplateFile {
    param([string]$Name)
    Assert-IssacText $Name "Usage: n8-show <name>"
    $matches = Get-ChildItem -Path $script:IssacN8nWorkflowDir -File | Where-Object {
        $_.Name -like "*$Name*"
    } | Sort-Object Name
    if (-not $matches) {
        throw "No n8n workflow matched '$Name'"
    }
    return $matches | Select-Object -First 1
}

function Show-IssacTextFile {
    param(
        [string]$Path,
        [int]$Head = 80
    )
    if (-not (Test-Path $Path)) {
        throw "Path not found: $Path"
    }
    Write-Output ("# {0}" -f $Path)
    Get-Content -Path $Path -Encoding UTF8 -TotalCount $Head
}

function Show-IssacJsonFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        throw "Path not found: $Path"
    }
    Write-Output ("# {0}" -f $Path)
    Get-Content -Path $Path -Raw -Encoding UTF8 | ConvertFrom-Json | ConvertTo-Json -Depth 20
}

function Resolve-IssacAgent {
    param([string]$Name)
    if ([string]::IsNullOrWhiteSpace($Name)) {
        return "agent.codex"
    }
    if ($Name -match "^agent\.") {
        return $Name
    }
    return "agent.$($Name.Trim())"
}

function issac-help {
    $menu = @'
ISSAC'S COMMAND CENTER
======================

HYDRA CORE
  hstatus            System status (JSON)
  hinteractive       Interactive HYDRA session
  hresearch <q>      Quick research (2 subtasks)
  hdeep <q>          Deep research (5 subtasks, 3 models)
  hqueue             Switchboard queue stats
  hdoctor            Local HYDRA command-center smoke

HYDRA ARXIV
  harxiv <q>         Search cs.AI papers
  harxiv-ml <q>      Search cs.LG papers
  harxiv-get <id>    Fetch paper by ID
  harxiv-outline     Outline from papers

HYDRA CANVAS
  hcanvas            List recipes
  hcanvas-run        Run a recipe
  hpaint <topic>     Freeform article pipeline

HYDRA BRANCH
  hbranch            List branch graphs
  hbranch-run        Run a branch graph

HYDRA SWARM
  hswarm <task>      6-agent Sacred Tongue swarm

HYDRA MEMORY
  hremember k v      Store a fact
  hrecall k          Retrieve a fact
  hsearch <q>        Semantic search

HYDRA WORKFLOW
  hwf                List workflows
  hwf-run <name>     Run workflow
  hwf-show <name>    Show workflow

HYDRA LATTICE
  hlattice [n]       Sample lattice nodes
  hlattice-notes     Ingest docs to lattice

SKILL VAULT
  hskills-refresh    Refresh repo-local skill synthesis artifacts
  hskills            Show current skill synthesis summary
  hstack <task>      Compose a skill stack from a task prompt

CASCADE
  hcascade <topic>   Skill refresh -> research -> arXiv -> branch -> canvas -> lattice -> xtalk
  harticle <topic>   Deep research -> arXiv -> article canvas
  hmission <topic>   Skill stack -> deep research -> branch -> canvas
  htunnel            Start the HYDRA terminal tunnel stack

BUILDFLOW
  buildflow -Mode <lane> <topic>   Goal race + daily operator pipeline
  buildflow-marketing <topic>      Agentic marketing pipeline scaffold
  buildflow-research <topic>       Research pipeline scaffold
  buildflow-browser <topic>        Browser-first operator/search scaffold
  buildflow-publish <topic>        Publish/amplify pipeline scaffold
  buildflow-github <topic>         GitHub browse + sweep scaffold
  buildflow-youtube <url|id>       Transcript + video research scaffold
  buildflow-article <topic>        Article research loop scaffold
  buildflow-workflow <topic>       n8n/workflow mesh scaffold
  buildflow-training <topic>       HF specialist training scaffold
  buildflow-colab <topic>          Colab notebook + training scaffold

DAILY OPS
  gh-browse <q>            AetherBrowser GitHub search -> live vault
  gh-sweep                 Local repo sweep packet (-IncludeGitHub for remote inventory)
  yt-transcript <url|id>   Pull YouTube transcript to stdout/JSON
  article-loop <topic>     Deep research self-healing article loop
  publish-dryrun           Multi-platform article publisher evidence pass
  publish-all              Run the live article publisher
  n8-templates             List repo-local n8n workflow templates
  n8-show <name>           Preview an n8n workflow template
  video-prompts            Show the AI video prompt pack
  voice-spec               Show the governed voice/TTS spec
  voice-audio-axis         Run the spectral/audio telemetry demo
  voice-manifest           Show the current voice manifest
  voice-status             Show the current voice pipeline packet
  voice-gate               Show the latest voice gate packet
  voice-prosody-research   Show long-form TTS research packet
  hf-generate-sft          Generate specialist SFT pairs from modules
  hf-train-wave            Run daily training merge/upload wave
  hf-agent-loop            Run local HF agent training loop

COLAB
  colab-catalog            List repo Colab notebooks and purposes
  colab-show <name>        Show one notebook entry and Colab URL
  colab-url <name>         Print the direct Colab URL
  colab-bridge-status      Show saved local Colab bridge profile
  colab-bridge-env         Emit env exports for a saved bridge profile
  colab-bridge-set         Save/update a Colab local bridge profile

SERVICES
  scbe-bridge        Start n8n browser bridge (:8001)
  scbe-api           Start SCBE API (:8000)
  octo-serve         Start OctoArmor gateway (:8400)

ACTION MAP
  haction-start <task>      Open an action-map workflow run
  haction-step <run> <msg>  Append one workflow step
  haction-close <run> <msg> Close a workflow run
  haction-build <run>       Compile action map + training rows
  haction-status [run]      Show latest or specific run status

CROSS-TALK
  xtalk-send <to> <msg>  Emit packet to another agent
  xtalk-ack <id>         Ack a packet
  xtalk-pending [agent]  Pending packets for an agent
  xtalk-health           Cross-talk health report

NAV
  go-scbe  go-hydra  go-agents  go-train  go-armor  go-docs
  go-api   go-workflows  go-browser  go-scripts
'@
    Write-Output $menu
}

function hstatus {
    Invoke-IssacHydra status --json
}

function hinteractive {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    Invoke-IssacHydra interactive @Args
}

function hresearch {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $query = Join-IssacText $Args
    Assert-IssacText $query "Usage: hresearch <topic>"
    Invoke-IssacHydra research $query --mode httpx --max-subtasks 2 --discovery 3
}

function hdeep {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $query = Join-IssacText $Args
    Assert-IssacText $query "Usage: hdeep <topic>"
    Invoke-IssacHydra research $query --mode httpx --max-subtasks 5 --discovery 5 --providers claude,gpt,gemini
}

function hqueue {
    Invoke-IssacHydra switchboard stats
}

function hdoctor {
    hstatus | Out-Null
    hqueue | Out-Null
    hwf | Out-Null
    hcanvas | Out-Null
    hbranch | Out-Null
    hlattice 4 | Out-Null
    [pscustomobject]@{
        ok = $true
        repo = $script:IssacCommandCenterRoot
        checked = @("hstatus", "hqueue", "hwf", "hcanvas", "hbranch", "hlattice")
    } | ConvertTo-Json -Depth 4
}

function harxiv {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $query = Join-IssacText $Args
    Assert-IssacText $query "Usage: harxiv <topic>"
    Invoke-IssacHydra arxiv search $query --cat cs.AI --max 5
}

function harxiv-ml {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $query = Join-IssacText $Args
    Assert-IssacText $query "Usage: harxiv-ml <topic>"
    Invoke-IssacHydra arxiv search $query --cat cs.LG --max 5
}

function harxiv-get {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $paperIds = Join-IssacText $Args
    Assert-IssacText $paperIds "Usage: harxiv-get <id1,id2,...>"
    Invoke-IssacHydra arxiv get $paperIds
}

function harxiv-outline {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $query = Join-IssacText $Args
    Assert-IssacText $query "Usage: harxiv-outline <topic>"
    Invoke-IssacHydra arxiv outline $query --cat cs.AI --max 8
}

function hcanvas {
    Invoke-IssacHydra canvas list
}

function hcanvas-run {
    param(
        [string]$Recipe = "article",
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args
    )
    $topic = Join-IssacText $Args
    if ([string]::IsNullOrWhiteSpace($topic)) {
        Invoke-IssacHydra canvas run $Recipe
        return
    }
    Invoke-IssacHydra canvas run $Recipe --topic $topic
}

function hpaint {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $topic = Join-IssacText $Args
    Assert-IssacText $topic "Usage: hpaint <topic>"
    Invoke-IssacHydra canvas paint $topic
}

function hbranch {
    Invoke-IssacHydra branch list
}

function hbranch-run {
    param(
        [string]$Graph = "research_pipeline",
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args
    )
    $topic = Join-IssacText $Args
    if ([string]::IsNullOrWhiteSpace($topic)) {
        Invoke-IssacHydra branch run $Graph
        return
    }
    Invoke-IssacHydra branch run $Graph --topic $topic
}

function hswarm {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $task = Join-IssacText $Args
    Assert-IssacText $task "Usage: hswarm <task>"
    Invoke-IssacInRepo {
        & python -m hydra.cli_swarm $task
    }
}

function hremember {
    param(
        [string]$Key,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args
    )
    $value = Join-IssacText $Args
    Assert-IssacText $Key "Usage: hremember <key> <value>"
    Assert-IssacText $value "Usage: hremember <key> <value>"
    Invoke-IssacHydra remember $Key $value
}

function hrecall {
    param([string]$Key)
    Assert-IssacText $Key "Usage: hrecall <key>"
    Invoke-IssacHydra recall $Key
}

function hsearch {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $query = Join-IssacText $Args
    Assert-IssacText $query "Usage: hsearch <keywords>"
    Invoke-IssacHydra search $query
}

function hwf {
    Invoke-IssacHydra workflow list
}

function hwf-run {
    param([string]$Name)
    Assert-IssacText $Name "Usage: hwf-run <name>"
    Invoke-IssacHydra workflow run $Name
}

function hwf-show {
    param([string]$Name)
    Assert-IssacText $Name "Usage: hwf-show <name>"
    Invoke-IssacHydra workflow show $Name
}

function hlattice {
    param([int]$Count = 12)
    Invoke-IssacHydra lattice25d sample --count $Count
}

function hlattice-notes {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    if (-not $Args -or $Args.Count -eq 0) {
        Invoke-IssacHydra lattice25d notes --glob "docs/**/*.md" --max-notes 40
        return
    }
    Invoke-IssacHydra lattice25d notes @Args
}

function hskills-refresh {
    $outputDir = Split-Path -Parent $script:IssacSkillSummary
    Invoke-IssacPythonFile $script:IssacSkillRefreshScript --output-dir $outputDir
}

function hskills {
    if (-not (Test-Path $script:IssacSkillSummary)) {
        hskills-refresh | Out-Null
    }
    Get-Content $script:IssacSkillSummary
}

function hstack {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $task = Join-IssacText $Args
    Assert-IssacText $task "Usage: hstack <task>"
    Invoke-IssacPythonFile $script:IssacSkillStackScript --task $task --top 8
}

function hcascade {
    param(
        [switch]$DryRun,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args
    )
    $topic = Join-IssacText $Args
    Assert-IssacText $topic "Usage: hcascade <topic> [-DryRun]"

    Invoke-IssacCascadeStep "refresh skill synthesis" { hskills-refresh } -DryRun:$DryRun | Out-Null
    Invoke-IssacCascadeStep "remember topic" { hremember "__issac_last_cascade_topic__" $topic } -DryRun:$DryRun | Out-Null
    Invoke-IssacCascadeStep "deep research" { hdeep $topic } -DryRun:$DryRun | Out-Null
    Invoke-IssacCascadeStep "arXiv outline" { harxiv-outline $topic } -DryRun:$DryRun | Out-Null
    Invoke-IssacCascadeStep "branch research pipeline" { hbranch-run "research_pipeline" $topic } -DryRun:$DryRun | Out-Null
    Invoke-IssacCascadeStep "canvas research recipe" { hcanvas-run "research" $topic } -DryRun:$DryRun | Out-Null
    Invoke-IssacCascadeStep "lattice checkpoint" { hlattice-notes --no-glob --note "Cascade checkpoint: $topic" } -DryRun:$DryRun | Out-Null
    Invoke-IssacCascadeStep "cross-talk emit" { xtalk-send researcher "Cascade complete for '$topic'" } -DryRun:$DryRun | Out-Null
}

function harticle {
    param(
        [switch]$DryRun,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args
    )
    $topic = Join-IssacText $Args
    Assert-IssacText $topic "Usage: harticle <topic> [-DryRun]"
    Invoke-IssacCascadeStep "deep research" { hdeep $topic } -DryRun:$DryRun | Out-Null
    Invoke-IssacCascadeStep "arXiv paper scan" { harxiv $topic } -DryRun:$DryRun | Out-Null
    Invoke-IssacCascadeStep "article canvas" { hcanvas-run "article" $topic } -DryRun:$DryRun | Out-Null
}

function hmission {
    param(
        [switch]$DryRun,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args
    )
    $topic = Join-IssacText $Args
    Assert-IssacText $topic "Usage: hmission <topic> [-DryRun]"
    Invoke-IssacCascadeStep "compose skill stack" { hstack $topic } -DryRun:$DryRun | Out-Null
    Invoke-IssacCascadeStep "deep research" { hdeep $topic } -DryRun:$DryRun | Out-Null
    Invoke-IssacCascadeStep "branch training funnel" { hbranch-run "training_funnel" $topic } -DryRun:$DryRun | Out-Null
    Invoke-IssacCascadeStep "content canvas" { hcanvas-run "content" $topic } -DryRun:$DryRun | Out-Null
}

function Invoke-IssacBuildflow {
    param(
        [ValidateSet("marketing", "research", "browser", "publish", "github", "youtube", "article", "workflow", "training", "colab", "story", "custom")]
        [string]$Mode = "custom",
        [switch]$DryRun,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args
    )
    $topic = Join-IssacText $Args
    Assert-IssacText $topic "Usage: buildflow -Mode <$Mode> <topic> [-DryRun]"

    $goalRaceMode = switch ($Mode) {
        "marketing" { "money" }
        "github" { "browser" }
        "youtube" { "research" }
        "article" { "publish" }
        default { $Mode }
    }

    Write-Host ("Buildflow [{0}] :: {1}" -f $Mode, $topic) -ForegroundColor Green
    Invoke-IssacCascadeStep "goal race scaffold" {
        Invoke-IssacPythonFile $script:IssacGoalRaceScript --goal $topic --mode $goalRaceMode
    } -DryRun:$DryRun | Out-Null

    switch ($Mode) {
        "marketing" {
            Invoke-IssacCascadeStep "refresh skill synthesis" { hskills-refresh } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "compose marketing skill stack" { hstack "agentic marketing pipeline for $topic" } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "deep market research" { hdeep $topic } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "content canvas" { hcanvas-run "content" $topic } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "marketing relay packet" { xtalk-send marketer "Buildflow marketing ready for '$topic'" } -DryRun:$DryRun | Out-Null
        }
        "research" {
            Invoke-IssacCascadeStep "refresh skill synthesis" { hskills-refresh } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "compose research skill stack" { hstack "research pipeline for $topic" } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "deep research" { hdeep $topic } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "arXiv outline" { harxiv-outline $topic } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "research relay packet" { xtalk-send researcher "Buildflow research ready for '$topic'" } -DryRun:$DryRun | Out-Null
        }
        "browser" {
            Invoke-IssacCascadeStep "refresh skill synthesis" { hskills-refresh } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "compose browser skill stack" { hstack "browser operator pipeline for $topic" } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "browser-first search" {
                Invoke-IssacPythonFile $script:IssacAetherbrowserSearchScript "web" $topic --save-to-live-vault --json
            } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "browser relay packet" { xtalk-send browser "Buildflow browser ready for '$topic'" } -DryRun:$DryRun | Out-Null
        }
        "publish" {
            Invoke-IssacCascadeStep "refresh skill synthesis" { hskills-refresh } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "compose publish skill stack" { hstack "publishing pipeline for $topic" } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "article flow" { harticle $topic } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "publish evidence dry-run" {
                Invoke-IssacPythonFile $script:IssacPostAllScript --dry-run --only github,linkedin,medium,devto
            } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "publish relay packet" { xtalk-send publisher "Buildflow publish ready for '$topic'" } -DryRun:$DryRun | Out-Null
        }
        "github" {
            Invoke-IssacCascadeStep "refresh skill synthesis" { hskills-refresh } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "compose github skill stack" { hstack "github browser workflow for $topic" } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "github browser search" { gh-browse $topic } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "github sweep packet" { gh-sweep } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "github relay packet" { xtalk-send reviewer "Buildflow github ready for '$topic'" } -DryRun:$DryRun | Out-Null
        }
        "youtube" {
            Invoke-IssacCascadeStep "refresh skill synthesis" { hskills-refresh } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "compose video research skill stack" { hstack "youtube transcript research workflow for $topic" } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "youtube transcript pull" { yt-transcript $topic -Json } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "video relay packet" { xtalk-send researcher "Buildflow youtube ready for '$topic'" } -DryRun:$DryRun | Out-Null
        }
        "article" {
            Invoke-IssacCascadeStep "refresh skill synthesis" { hskills-refresh } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "compose article skill stack" { hstack "article research loop for $topic" } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "deep research loop" { article-loop $topic } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "article canvas" { harticle $topic } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "publish evidence dry-run" {
                Invoke-IssacPythonFile $script:IssacPostAllScript --dry-run --only github,linkedin,medium,devto
            } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "article relay packet" { xtalk-send author "Buildflow article ready for '$topic'" } -DryRun:$DryRun | Out-Null
        }
        "workflow" {
            Invoke-IssacCascadeStep "refresh skill synthesis" { hskills-refresh } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "compose workflow mesh skill stack" { hstack "n8n workflow mesh for $topic" } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "list n8n templates" { n8-templates } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "workflow vector baseline" {
                Invoke-IssacPythonFile $script:IssacWorkflowVectorScript --z 1,1,0,1,0 --threshold 0.5
            } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "workflow relay packet" { xtalk-send automator "Buildflow workflow ready for '$topic'" } -DryRun:$DryRun | Out-Null
        }
        "training" {
            Invoke-IssacCascadeStep "refresh skill synthesis" { hskills-refresh } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "compose training skill stack" { hstack "hugging face specialist training for $topic" } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "generate specialist sft" { hf-generate-sft } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "daily training wave" { hf-train-wave } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "training relay packet" { xtalk-send trainer "Buildflow training ready for '$topic'" } -DryRun:$DryRun | Out-Null
        }
        "colab" {
            Invoke-IssacCascadeStep "refresh skill synthesis" { hskills-refresh } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "compose colab skill stack" { hstack "google colab training workflow for $topic" } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "colab notebook catalog" { colab-catalog } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "pivot notebook route" { colab-show pivot } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "generate specialist sft" { hf-generate-sft } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "colab relay packet" { xtalk-send trainer "Buildflow colab ready for '$topic'" } -DryRun:$DryRun | Out-Null
        }
        "story" {
            Invoke-IssacCascadeStep "compose story skill stack" { hstack "story pipeline for $topic" } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "story relay packet" { xtalk-send storyteller "Buildflow story ready for '$topic'" } -DryRun:$DryRun | Out-Null
        }
        default {
            Invoke-IssacCascadeStep "compose custom skill stack" { hstack $topic } -DryRun:$DryRun | Out-Null
            Invoke-IssacCascadeStep "custom relay packet" { xtalk-send builder "Buildflow custom ready for '$topic'" } -DryRun:$DryRun | Out-Null
        }
    }
}

function buildflow {
    param(
        [ValidateSet("marketing", "research", "browser", "publish", "github", "youtube", "article", "workflow", "training", "colab", "story", "custom")]
        [string]$Mode = "custom",
        [switch]$DryRun,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args
    )
    Invoke-IssacBuildflow -Mode $Mode -DryRun:$DryRun @Args
}

function buildflow-marketing {
    param([switch]$DryRun, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    Invoke-IssacBuildflow -Mode "marketing" -DryRun:$DryRun @Args
}

function buildflow-research {
    param([switch]$DryRun, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    Invoke-IssacBuildflow -Mode "research" -DryRun:$DryRun @Args
}

function buildflow-browser {
    param([switch]$DryRun, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    Invoke-IssacBuildflow -Mode "browser" -DryRun:$DryRun @Args
}

function buildflow-publish {
    param([switch]$DryRun, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    Invoke-IssacBuildflow -Mode "publish" -DryRun:$DryRun @Args
}

function buildflow-github {
    param([switch]$DryRun, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    Invoke-IssacBuildflow -Mode "github" -DryRun:$DryRun @Args
}

function buildflow-youtube {
    param([switch]$DryRun, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    Invoke-IssacBuildflow -Mode "youtube" -DryRun:$DryRun @Args
}

function buildflow-article {
    param([switch]$DryRun, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    Invoke-IssacBuildflow -Mode "article" -DryRun:$DryRun @Args
}

function buildflow-workflow {
    param([switch]$DryRun, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    Invoke-IssacBuildflow -Mode "workflow" -DryRun:$DryRun @Args
}

function buildflow-training {
    param([switch]$DryRun, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    Invoke-IssacBuildflow -Mode "training" -DryRun:$DryRun @Args
}

function buildflow-colab {
    param([switch]$DryRun, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    Invoke-IssacBuildflow -Mode "colab" -DryRun:$DryRun @Args
}

function colab-catalog {
    param([switch]$Json)
    $scriptArgs = @("list")
    if ($Json) {
        $scriptArgs += "--json"
    }
    Invoke-IssacPythonFile $script:IssacColabCatalogScript @scriptArgs
}

function colab-show {
    param([string]$Name, [switch]$Json)
    Assert-IssacText $Name "Usage: colab-show <name> [-Json]"
    $scriptArgs = @("show", $Name)
    if ($Json) {
        $scriptArgs += "--json"
    }
    Invoke-IssacPythonFile $script:IssacColabCatalogScript @scriptArgs
}

function colab-url {
    param([string]$Name, [switch]$Json)
    Assert-IssacText $Name "Usage: colab-url <name> [-Json]"
    $scriptArgs = @("url", $Name)
    if ($Json) {
        $scriptArgs += "--json"
    }
    Invoke-IssacPythonFile $script:IssacColabCatalogScript @scriptArgs
}

function colab-bridge-status {
    param([string]$Name = "pivot")
    Invoke-IssacPythonFile $script:IssacColabBridgeScript --status --name $Name
}

function colab-bridge-env {
    param([string]$Name = "pivot")
    Invoke-IssacPythonFile $script:IssacColabBridgeScript --env --name $Name
}

function colab-bridge-set {
    param(
        [string]$Name = "pivot",
        [string]$BackendUrl,
        [string]$Token = "",
        [string]$N8nWebhook = "",
        [switch]$Probe
    )
    Assert-IssacText $BackendUrl "Usage: colab-bridge-set -BackendUrl <http://127.0.0.1:8888/?token=...> [-Name pivot] [-N8nWebhook <url>] [-Probe]"
    $scriptArgs = @("--set", "--name", $Name, "--backend-url", $BackendUrl)
    if (-not [string]::IsNullOrWhiteSpace($Token)) {
        $scriptArgs += @("--token", $Token)
    }
    if (-not [string]::IsNullOrWhiteSpace($N8nWebhook)) {
        $scriptArgs += @("--n8n-webhook", $N8nWebhook)
    }
    if ($Probe) {
        $scriptArgs += "--probe"
    }
    Invoke-IssacPythonFile $script:IssacColabBridgeScript @scriptArgs
}

function gh-browse {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $query = Join-IssacText $Args
    Assert-IssacText $query "Usage: gh-browse <query>"
    Invoke-IssacPythonFile $script:IssacAetherbrowserSearchScript github $query --save-to-live-vault --json
}

function gh-sweep {
    param([switch]$IncludeGitHub)
    $scriptArgs = @("--repo-root", $script:IssacCommandCenterRoot)
    if ($IncludeGitHub) {
        $scriptArgs += "--include-github"
    }
    Invoke-IssacPythonFile $script:IssacGithubSweepScript @scriptArgs
}

function yt-transcript {
    param(
        [string]$Target,
        [string]$Language = "en",
        [string]$Output = "",
        [switch]$Json
    )
    Assert-IssacText $Target "Usage: yt-transcript <video-url-or-id> [-Language en] [-Output path] [-Json]"
    $scriptArgs = @($Target, "--language", $Language)
    if (-not [string]::IsNullOrWhiteSpace($Output)) {
        $scriptArgs += @("--output", $Output)
    }
    if ($Json) {
        $scriptArgs += "--json"
    }
    Invoke-IssacPythonFile $script:IssacYoutubeTranscriptScript @scriptArgs
}

function article-loop {
    param(
        [int]$Cycles = 1,
        [switch]$UsePlaywriter,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args
    )
    $topic = Join-IssacText $Args
    Assert-IssacText $topic "Usage: article-loop <topic> [-Cycles 1] [-UsePlaywriter]"
    Invoke-IssacPwshFile $script:IssacDeepResearchLoop -Topic $topic -Cycles $Cycles -UsePlaywriter:$UsePlaywriter
}

function publish-dryrun {
    param([string]$Only = "")
    $scriptArgs = @("--dry-run")
    if (-not [string]::IsNullOrWhiteSpace($Only)) {
        $scriptArgs += @("--only", $Only)
    }
    Invoke-IssacPythonFile $script:IssacPostAllScript @scriptArgs
}

function publish-all {
    param([string]$Only = "")
    $scriptArgs = @()
    if (-not [string]::IsNullOrWhiteSpace($Only)) {
        $scriptArgs += @("--only", $Only)
    }
    Invoke-IssacPythonFile $script:IssacPostAllScript @scriptArgs
}

function n8-templates {
    Get-ChildItem -Path $script:IssacN8nWorkflowDir -File |
        Sort-Object Name |
        Select-Object Name, Length, LastWriteTime |
        Format-Table -AutoSize
}

function n8-show {
    param([string]$Name, [int]$Head = 80)
    $template = Get-IssacN8nTemplateFile $Name
    Show-IssacTextFile -Path $template.FullName -Head $Head
}

function video-prompts {
    param([int]$Head = 120)
    Show-IssacTextFile -Path $script:IssacVideoPromptsDoc -Head $Head
}

function voice-spec {
    param([int]$Head = 120)
    Show-IssacTextFile -Path $script:IssacVoiceSpec -Head $Head
}

function voice-audio-axis {
    Invoke-IssacPythonFile $script:IssacLayer9AudioAxisScript
}

function voice-manifest {
    if (-not (Test-Path $script:IssacVoiceManifest)) {
        [pscustomobject]@{
            selected_sample = $null
            status = "missing"
            path = $script:IssacVoiceManifest
        } | ConvertTo-Json -Depth 6
        return
    }
    Show-IssacJsonFile -Path $script:IssacVoiceManifest
}

function voice-status {
    if (-not (Test-Path $script:IssacVoiceStatusPacket)) {
        [pscustomobject]@{
            summary = "Voice status packet not generated yet."
            status = "missing"
            path = $script:IssacVoiceStatusPacket
        } | ConvertTo-Json -Depth 6
        return
    }
    Show-IssacJsonFile -Path $script:IssacVoiceStatusPacket
}

function voice-gate {
    Show-IssacJsonFile -Path $script:IssacVoiceGatePacket
}

function voice-prosody-research {
    Show-IssacJsonFile -Path $script:IssacVoiceProsodyResearch
}

function hf-generate-sft {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    Invoke-IssacPythonFile $script:IssacGenerateSftScript @Args
}

function hf-train-wave {
    param([switch]$Upload)
    $scriptArgs = @()
    if ($Upload) {
        $scriptArgs += "--upload"
    }
    Invoke-IssacPythonFile $script:IssacDailyTrainingWaveScript @scriptArgs
}

function hf-agent-loop {
    param(
        [int]$Steps = 300,
        [switch]$Push,
        [switch]$Continuous
    )
    $scriptArgs = @("--steps", "$Steps")
    if ($Push) {
        $scriptArgs += "--push"
    }
    if ($Continuous) {
        $scriptArgs += "--continuous"
    }
    Invoke-IssacPythonFile $script:IssacHfTrainingLoopScript @scriptArgs
}

function htunnel {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    Invoke-IssacPwshFile $script:IssacHydraTunnel @Args
}

function scbe-bridge {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    Invoke-IssacPwshFile $script:IssacBrowserService @Args
}

function scbe-api {
    param(
        [string]$Host = "127.0.0.1",
        [int]$Port = 8000
    )
    if (-not $env:SCBE_API_KEY) {
        Write-Warning "SCBE_API_KEY is not set. The API will start, but authenticated requests will be rejected."
    }
    Invoke-IssacInRepo {
        & python -m uvicorn api.main:app --host $Host --port $Port
    }
}

function octo-serve {
    param(
        [string]$Host = "127.0.0.1",
        [int]$Port = 8400
    )
    Invoke-IssacInRepo {
        & python -m uvicorn src.aethercode.gateway:app --host $Host --port $Port
    }
}

function haction-start {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $task = Join-IssacText $Args
    Assert-IssacText $task "Usage: haction-start <task>"
    Invoke-IssacPythonFile $script:IssacActionMapScript start --task $task --operator "agent.codex" --lane "command-center"
}

function haction-step {
    param(
        [string]$RunId,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args
    )
    $summary = Join-IssacText $Args
    Assert-IssacText $RunId "Usage: haction-step <run_id> <summary>"
    Assert-IssacText $summary "Usage: haction-step <run_id> <summary>"
    Invoke-IssacPythonFile $script:IssacActionMapScript step --run-id $RunId --summary $summary --operator "agent.codex" --lane "command-center"
}

function haction-close {
    param(
        [string]$RunId,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args
    )
    $summary = Join-IssacText $Args
    Assert-IssacText $RunId "Usage: haction-close <run_id> <summary>"
    Assert-IssacText $summary "Usage: haction-close <run_id> <summary>"
    Invoke-IssacPythonFile $script:IssacActionMapScript close --run-id $RunId --summary $summary --status completed --operator "agent.codex" --lane "command-center"
}

function haction-build {
    param([string]$RunId)
    Assert-IssacText $RunId "Usage: haction-build <run_id>"
    Invoke-IssacPythonFile $script:IssacActionMapScript build --run-id $RunId
}

function haction-status {
    param([string]$RunId = "")
    if ([string]::IsNullOrWhiteSpace($RunId)) {
        Invoke-IssacPythonFile $script:IssacActionMapScript status
        return
    }
    Invoke-IssacPythonFile $script:IssacActionMapScript status --run-id $RunId
}

function xtalk-send {
    param(
        [string]$To,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args
    )
    $message = Join-IssacText $Args
    Assert-IssacText $To "Usage: xtalk-send <to> <message>"
    Assert-IssacText $message "Usage: xtalk-send <to> <message>"
    $recipient = Resolve-IssacAgent $To
    $taskId = "XTALK-MANUAL-" + [DateTime]::UtcNow.ToString("yyyyMMddHHmmss")
    Invoke-IssacPythonFile $script:IssacCrossTalkRelay emit `
        --sender "agent.codex" `
        --recipient $recipient `
        --intent "sync" `
        --task-id $taskId `
        --summary $message `
        --status "in_progress" `
        --next-action "review packet"
}

function xtalk-ack {
    param([string]$PacketId)
    Assert-IssacText $PacketId "Usage: xtalk-ack <packet_id>"
    Invoke-IssacPythonFile $script:IssacCrossTalkRelay ack --packet-id $PacketId --agent "agent.codex"
}

function xtalk-pending {
    param([string]$Agent = "agent.codex")
    Invoke-IssacPythonFile $script:IssacCrossTalkRelay pending --agent (Resolve-IssacAgent $Agent)
}

function xtalk-health {
    Invoke-IssacPythonFile $script:IssacCrossTalkRelay health
}

function go-scbe { Set-Location $script:IssacCommandCenterRoot }
function go-hydra { Set-Location (Join-Path $script:IssacCommandCenterRoot "hydra") }
function go-agents { Set-Location (Join-Path $script:IssacCommandCenterRoot "agents") }
function go-train { Set-Location (Join-Path $script:IssacCommandCenterRoot "training") }
function go-armor { Set-Location (Join-Path $script:IssacCommandCenterRoot "src\aethercode") }
function go-docs { Set-Location (Join-Path $script:IssacCommandCenterRoot "docs") }
function go-api { Set-Location (Join-Path $script:IssacCommandCenterRoot "api") }
function go-workflows { Set-Location (Join-Path $script:IssacCommandCenterRoot "workflows") }
function go-browser { Set-Location (Join-Path $script:IssacCommandCenterRoot "aetherbrowse") }
function go-scripts { Set-Location (Join-Path $script:IssacCommandCenterRoot "scripts") }
