param(
    [Parameter(Mandatory)]
    [ValidateSet(
        'status',
        'checkout-pr',
        'inspect-pr',
        'run-list',
        'run-view',
        'scbe-governance',
        'scbe-kdf',
        'scbe-ci',
        'code-assistant-scan',
        'workflow-architect-scan',
        'aethermoore-demo-scan',
        'scbe-self-heal',
        'self-heal-catalog',
        'llm-training',
        'ai-nodal-dev-specialist'
    )]
    [string]$Mode,
    [string]$Repo = 'issdandavis/SCBE-AETHERMOORE',
    [string]$RepoPath = 'C:\Users\issda\SCBE-AETHERMOORE',
    [string]$KiroRepoPath = 'C:\Users\issda\Kiro_Version_ai-workflow-architect',
    [string]$DemoRepoPath = 'C:\Users\issda\scbe-aethermoore-demo',
    [string]$NotionDocPath = '',
    [string]$TrainingManifestOutput = '',
    [int]$Pr = 0,
    [int]$RunId = 0,
    [int]$Limit = 20,
    [string]$SelfHealScript = '',
    [string]$FailureFile = '',
    [string]$FailurePayload = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:MarkerPath = Join-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) '.scbe-next-coder-marker.json'

function Resolve-RepoPath {
    param(
        [string]$Primary,
        [string]$Fallback
    )
    $candidates = @()
    if ($Primary) { $candidates += $Primary }
    if ($Fallback) { $candidates += $Fallback }

    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
        if (Test-Path -Path $candidate) {
            return (Resolve-Path $candidate).Path
        }
    }

    throw "Could not resolve repository path. Checked: $($candidates -join ', ')"
}

function Invoke-Gh {
    param([string[]]$Args)
    & gh @Args
    if ($LASTEXITCODE -ne 0) { throw "gh command failed: gh $($Args -join ' ')" }
}

function Assert-GitRepo {
    param([string]$Path)
    if (-not (Test-Path -Path $Path)) {
        throw "Repo path not found: $Path"
    }
    if (-not (Test-Path -Path (Join-Path $Path '.git'))) {
        throw "Not a git repo: $Path"
    }
}

function Get-RelevantFiles {
    param([string]$Pattern, [string]$SearchPath)
    $files = Get-ChildItem -Path $SearchPath -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match $Pattern }
    return $files
}

function Get-SelfHealCatalog {
    param([string]$RootPath)
    if (-not (Test-Path -Path $RootPath)) {
        throw "Catalog root path not found: $RootPath"
    }

    $patterns = @(
        '*self*heal*.ps1',
        '*self*heal*.py',
        '*self*heal*.ts',
        '*workflow*architect*.ps1',
        '*workflow*architect*.py',
        '*workflow*architect*.ts',
        '*selfHealing*',
        '*quick*fix*',
        '*deep*healing*',
        '*healing*',
        '*quickFix*',
        '*deepHealing*'
    )

    $catalog = @()
    foreach ($pattern in $patterns) {
        $catalog += Get-ChildItem -Path $RootPath -Recurse -File -ErrorAction SilentlyContinue -Filter $pattern
    }

    return $catalog | Sort-Object FullName -Unique
}

function Get-PreferredSelfHealScripts {
    param([string]$RootPath)
    $relativePaths = @(
        'SCBE-AETHERMOORE-v3.0.0\src\selfHealing\selfHealingOrchestrator.py',
        'SCBE-AETHERMOORE-v3.0.0\src\selfHealing\coordinator.ts',
        'SCBE-AETHERMOORE-v3.0.0\src\selfHealing\quickFixBot.ts',
        'SCBE-AETHERMOORE-v3.0.0\src\selfHealing\deepHealing.ts',
        'src\selfHealing\coordinator.ts',
        'src\selfHealing\quickFixBot.ts',
        'src\selfHealing\deepHealing.ts',
        'src\selfHealing\selfHealingOrchestrator.py',
        'server\services\workflowHealer.ts',
        'server\services\selfHealing.ts',
        'script\workflow_healer.py',
        'script\email-router.py'
    )

    $results = @()
    foreach ($relative in $relativePaths) {
        $candidate = Join-Path $RootPath $relative
        if (Test-Path -Path $candidate) {
            $results += Get-Item -Path $candidate
        }
    }

    return $results | Sort-Object FullName -Unique
}

function Invoke-HealScript {
    param(
        [string]$ScriptPath,
        [string]$FailureFile,
        [string]$FailurePayload
    )

    if (-not (Test-Path -Path $ScriptPath)) {
        throw "Self-heal script not found: $ScriptPath"
    }

    $ext = [System.IO.Path]::GetExtension($ScriptPath).ToLowerInvariant()
    $args = @()

    if ($FailureFile) {
        $args += @('-FailureFile', $FailureFile)
    }
    if ($FailurePayload) {
        $args += @('-FailurePayload', $FailurePayload)
    }

    switch ($ext) {
        '.py' {
            & python $ScriptPath @args
        }
        '.ps1' {
            & $ScriptPath @args
        }
        '.js' {
            & node $ScriptPath @args
        }
        default {
            if ($ext -eq '.ts') {
                throw "TypeScript self-heal script requires a runner (for example ts-node or compiled JS). Pass a runnable script path."
            }
            & $ScriptPath @args
        }
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Self-heal script failed with exit code $LASTEXITCODE: $ScriptPath"
    }
}

function Invoke-PatternSurfaceScan {
    param(
        [string]$RootPath,
        [string]$Label,
        [string[]]$Patterns,
        [string[]]$KeyFiles
    )
    Assert-GitRepo -Path $RootPath

    Write-Host "== $Label: key artifact check =="
    foreach ($file in $KeyFiles) {
        $candidate = Join-Path $RootPath $file
        if (Test-Path -Path $candidate) {
            Write-Host "  + $candidate"
        }
    }
    Write-Host ""

    if (-not (Get-Command rg -ErrorAction SilentlyContinue)) {
        throw "ripgrep (rg) is required for pattern scans."
    }

    foreach ($pattern in $Patterns) {
        Write-Host "== Pattern: $pattern =="
        & rg -n -g "*.ts" -g "*.py" -g "*.js" -g "*.md" $pattern $RootPath
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  (no matches)"
        }
        Write-Host ""
    }
}

function Get-ArtifactMatches {
    param(
        [string]$RootPath,
        [string[]]$Patterns,
        [string[]]$Globs
    )

    if (-not (Get-Command rg -ErrorAction SilentlyContinue)) {
        throw "ripgrep (rg) is required for artifact scans."
    }

    if (-not (Test-Path -Path $RootPath)) {
        return @()
    }

    $results = @()
    foreach ($pattern in $Patterns) {
        $rgArgs = @('-n', '-l')
        foreach ($glob in $Globs) {
            $rgArgs += @('--glob', $glob)
        }
        $rgArgs += $pattern
        $rgArgs += $RootPath
        $matches = & rg @rgArgs 2>$null
        if ($LASTEXITCODE -eq 0 -and $matches) {
            $results += $matches
        }
    }

    return $results | ForEach-Object { $_.Trim() } | Sort-Object -Unique
}

function Build-LlmTrainingManifest {
    param(
        [string]$RepoRoot,
        [string]$NotionRoot
    )

    $globs = @("*.md", "*.ts", "*.tsx", "*.js", "*.json", "*.py", "*.yaml", "*.yml")

    $languagePatterns = @(
        "(?i)ko\\b|av\\b|ru\\b|ca\\b|um\\b|dr\\b|kor|avali|runethic|cassis|umbroth|draum",
        "(?i)6\\s*languages|six\\s*languages|six\\s*tongues|sacred\\s*tongue|tongue"
    )

    $vectorPatterns = @(
        "(?i)vector|21d|21\\s*d|hyperbolic|poincare|cochain|cohomolog|laplacian|lattice|cube|hypercube|tesseract|torus",
        "(?i)planner|state\\s*space|multi\\-planner|planner\\s*mesh|manifold|topology|cell"
    )

    $securityPatterns = @(
        "(?i)hmac|seal|envelope|pqc|notion|governance|decision|audit|flux|boundary",
        "(?i)mcp|assistant|code\\-assistant|analysis|proposal|autonomy|self\\-heal"
    )

    $langHitsRepo = Get-ArtifactMatches -RootPath $RepoRoot -Patterns $languagePatterns -Globs $globs
    $vectorHitsRepo = Get-ArtifactMatches -RootPath $RepoRoot -Patterns $vectorPatterns -Globs $globs
    $securityHitsRepo = Get-ArtifactMatches -RootPath $RepoRoot -Patterns $securityPatterns -Globs $globs

    $langHitsNotion = @()
    $vectorHitsNotion = @()
    if ($NotionRoot) {
        $langHitsNotion = Get-ArtifactMatches -RootPath $NotionRoot -Patterns $languagePatterns -Globs $globs
        $vectorHitsNotion = Get-ArtifactMatches -RootPath $NotionRoot -Patterns $vectorPatterns -Globs $globs
    }

    $manifest = [ordered]@{
        generatedAtUtc = (Get-Date).ToUniversalTime().ToString("o")
        repoRoot = $RepoRoot
        notionRoot = $NotionRoot
        sixLanguageSignals = @{
            count = $langHitsRepo.Count
            files = $langHitsRepo
            notionMatches = $langHitsNotion
        }
        sixVectorSignals = @{
            count = $vectorHitsRepo.Count
            files = $vectorHitsRepo
            notionMatches = $vectorHitsNotion
        }
        safetySecuritySignals = @{
            count = $securityHitsRepo.Count
            files = $securityHitsRepo
        }
        recommendedTrainingPipeline = @(
            "Ingest Notion markdown export and repo docs as paired language + vector sources",
            "Normalize text with section boundaries: language concept -> vector concept -> governance decision examples",
            "Split examples by layer (e.g., governance, encryption, self-heal, planner, audit, risk)",
            "Create train/val/test splits by release timeline to avoid leakage",
            "Add evaluation sets for: safety policy, planner consistency, traceability, and failure recovery"
        )
        realityChecks = Get-LlmRealityChecks -LanguageCount $langHitsRepo.Count -VectorCount $vectorHitsRepo.Count -SecurityCount $securityHitsRepo.Count
    }

    return $manifest
}

function Get-LlmRealityChecks {
    param(
        [int]$LanguageCount,
        [int]$VectorCount,
        [int]$SecurityCount
    )

    $checks = @()

    if ($LanguageCount -lt 6) {
        $checks += "Low language-signal confidence: only $LanguageCount language matches. Locate explicit Six Tongues definitions before training."
    } else {
        $checks += "Language signal density is sufficient for a first draft (>=6 matched anchors)."
    }

    if ($VectorCount -lt 6) {
        $checks += "Vector/math concept coverage appears thin: only $VectorCount vector matches. Expand source docs for 6 vectors and hyperbolic shaping."
    } else {
        $checks += "Vector-signaling terms are present and can support a lattice-based planner corpus."
    }

    if ($SecurityCount -lt 5) {
        $checks += "Security/audit context is sparse: only $SecurityCount matches. Add explicit governance and envelope examples."
    } else {
        $checks += "Security/audit anchors are present; include explicit boundary/deny cases for reliability."
    }

    $checks += "Reality check: treat 2D/3D/cube-composition as geometric abstraction, not proof of cryptographic security."
    $checks += "Reality check: any torus/hypercube narrative must specify metric, adjacency rules, and boundary conditions."
    $checks += "Reality check: validate generated planner behavior on synthetic and held-out tasks before production use."

    return $checks
}

function Write-TrainingManifest {
    param([hashtable]$Manifest)

    $payload = $Manifest | ConvertTo-Json -Depth 8
    Write-Host $payload

    if ($TrainingManifestOutput) {
        $parent = Split-Path -Path $TrainingManifestOutput -Parent
        if (-not (Test-Path -Path $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        Set-Content -Path $TrainingManifestOutput -Value $payload -Encoding UTF8
        Write-Host "Training manifest written: $TrainingManifestOutput"
    }
}

function Ensure-NextCoderMarker {
    param([string]$Note)
    $marker = @{
        updatedAtUtc = (Get-Date).ToUniversalTime().ToString("o")
        note = $Note
        mode = $Mode
        lastRepo = $RepoPath
    }
    if ($Note) {
        $markerJson = $marker | ConvertTo-Json -Depth 8
        Set-Content -Path $script:MarkerPath -Value $markerJson -Encoding UTF8
    }
}

switch ($Mode) {
    'status' {
        Invoke-Gh @('status', "--repo", $Repo)
    }
    'checkout-pr' {
        if ($Pr -le 0) { throw 'Provide -Pr <number> for checkout-pr mode.' }
        $targetRepo = Resolve-RepoPath -Primary $RepoPath
        Assert-GitRepo -Path $targetRepo
        Set-Location -Path $targetRepo
        Invoke-Gh @('pr', 'checkout', $Pr, '--repo', $Repo)
    }
    'inspect-pr' {
        if ($Pr -le 0) { throw 'Provide -Pr <number> for inspect-pr mode.' }
        Invoke-Gh @('pr', 'view', $Pr, '--repo', $Repo, '--json', 'title,number,state,files')
    }
    'run-list' {
        Invoke-Gh @('run', 'list', '--repo', $Repo, '--limit', $Limit)
    }
    'run-view' {
        if ($RunId -le 0) { throw 'Provide -RunId <id> for run-view mode.' }
        Invoke-Gh @('run', 'view', $RunId, '--repo', $Repo, '--log')
    }
    'scbe-governance' {
        $targetRepo = Resolve-RepoPath -Primary $RepoPath -Fallback $DemoRepoPath
        Assert-GitRepo -Path $targetRepo
        Write-Host "SCBE governance + envelope signals"
        Get-RelevantFiles -Pattern '(governance|envelope|seal|pqc|scbe_version|detectPolicyObstruction|make_envelope)' -SearchPath $targetRepo |
            Select-Object -ExpandProperty FullName
    }
    'scbe-kdf' {
        $targetRepo = Resolve-RepoPath -Primary $RepoPath -Fallback $DemoRepoPath
        Assert-GitRepo -Path $targetRepo
        Write-Host "SCBE KDF interoperability hotspots"
        Get-RelevantFiles -Pattern '(qrCubeKdf|length|le64|writeUInt32LE|writeBigUInt64LE|NOTION_API_KEY|secre\.tsNOTION_API_KEY)' -SearchPath $targetRepo |
            Select-Object -ExpandProperty FullName
    }
    'scbe-ci' {
        Write-Host "SCBE CI failure signals"
        Invoke-Gh @('run', 'list', '--repo', $Repo, '--limit', $Limit, '--json', 'name,status,conclusion,number')
        Invoke-Gh @('run', 'list', '--repo', $Repo, '--limit', $Limit)
    }
    'code-assistant-scan' {
        $targetRepo = Resolve-RepoPath -Primary $RepoPath -Fallback $DemoRepoPath
        Invoke-PatternSurfaceScan -RootPath $targetRepo -Label 'SCBE / local assistant surface' -Patterns @(
            '(?i)code[-_ ]?assistant',
            '(?i)assistant|chat|analysis|proposal|improve|improvement',
            '(?i)suggest|apply.*patch',
            '(?i)governance|envelope|audit|safe'
        ) -KeyFiles @(
            'README.md',
            'SCBE-AETHERMOORE-v3.0.0',
            'server/services/codeImprovement.ts',
            'src/sheafCohomology.ts',
            'src/ai_orchestration',
            'scbe-agent.py'
        )
    }
    'workflow-architect-scan' {
        $targetRepo = Resolve-RepoPath -Primary $RepoPath -Fallback $KiroRepoPath
        Invoke-PatternSurfaceScan -RootPath $targetRepo -Label 'Workflow Architect assistant + autonomy surfaces' -Patterns @(
            '(?i)codeImprovement|code-improvement',
            '(?i)assistant|assistant/chat|code-assistant|chat|propose|proposal',
            '(?i)autonomy|orchestrator|developerMode',
            '(?i)selfHealing|healing|quickFixBot|deepHealing'
        ) -KeyFiles @(
            'server/services/codeImprovement.ts',
            'server/services/developerMode.ts',
            'server/services/autonomyEngine.ts',
            'server/services/orchestrator.ts',
            'server/routes.ts',
            'script/email-router.py',
            'script/build.ts'
        )
    }
    'aethermoore-demo-scan' {
        $targetRepo = Resolve-RepoPath -Primary $RepoPath -Fallback $DemoRepoPath
        Invoke-PatternSurfaceScan -RootPath $targetRepo -Label 'SCBE-AETHERMOORE demo assistant + self-healing' -Patterns @(
            '(?i)selfHealingOrchestrator|selfHealing|quickFixBot|deepHealing|coordinator',
            '(?i)code[-_ ]?assistant|assistant|scbe-agent|setup_assistant',
            '(?i)api/v1/health|health|status',
            '(?i)governance|envelope|seal|kdf'
        ) -KeyFiles @(
            'SCBE-AETHERMOORE-v3.0.0/src/selfHealing/coordinator.ts',
            'SCBE-AETHERMOORE-v3.0.0/src/selfHealing/deepHealing.ts',
            'SCBE-AETHERMOORE-v3.0.0/src/selfHealing/quickFixBot.ts',
            'SCBE-AETHERMOORE-v3.0.0/src/selfHealing/selfHealingOrchestrator.py',
            'scbe-agent.py',
            'api/main.py'
        )
    }
    'self-heal-catalog' {
        $targetRepo = Resolve-RepoPath -Primary $RepoPath -Fallback $KiroRepoPath
        Assert-GitRepo -Path $targetRepo
        Get-SelfHealCatalog -RootPath $targetRepo | Select-Object -ExpandProperty FullName
    }
    'scbe-self-heal' {
        $targetRepo = Resolve-RepoPath -Primary $RepoPath -Fallback $DemoRepoPath
        Assert-GitRepo -Path $targetRepo

        $candidateScripts = @()
        $candidateScripts += Get-PreferredSelfHealScripts -RootPath $targetRepo
        if (-not $candidateScripts -or $candidateScripts.Count -eq 0) {
            $candidateScripts = Get-SelfHealCatalog -RootPath $targetRepo
        }

        if (-not $candidateScripts -or $candidateScripts.Count -eq 0) {
            Write-Host "No workflow-architect/self-heal scripts found under: $targetRepo"
            Write-Host "Pass -SelfHealScript with an explicit script path."
            Write-Host "Example: -SelfHealScript 'C:\path\to\your\script.py'"
            break
        }

        if ($SelfHealScript) {
            Invoke-HealScript -ScriptPath $SelfHealScript -FailureFile $FailureFile -FailurePayload $FailurePayload
            break
        }

        if ($candidateScripts.Count -gt 1) {
            Write-Host "Multiple candidates found. Use -SelfHealScript to select one:"
            $candidateScripts | ForEach-Object { Write-Host $_.FullName }
            break
        }

        Invoke-HealScript -ScriptPath $candidateScripts[0].FullName -FailureFile $FailureFile -FailurePayload $FailurePayload
    }
    'llm-training' {
        $targetRepo = Resolve-RepoPath -Primary $RepoPath -Fallback $DemoRepoPath
        Assert-GitRepo -Path $targetRepo
        $notionRoot = ''
        if ($NotionDocPath) {
            try { $notionRoot = Resolve-RepoPath -Primary $NotionDocPath -Fallback '' } catch {}
        }
        Write-Host "Generating training manifest for LLM/AI Nodal preparation..."
        $manifest = Build-LlmTrainingManifest -RepoRoot $targetRepo -NotionRoot $notionRoot
        Write-TrainingManifest -Manifest $manifest
        Ensure-NextCoderMarker -Note "llm-training manifest generated; inspect json and reality-checks before dataset build."
    }
    'ai-nodal-dev-specialist' {
        $targetRepo = Resolve-RepoPath -Primary $RepoPath -Fallback $DemoRepoPath
        Assert-GitRepo -Path $targetRepo
        $notionRoot = ''
        if ($NotionDocPath) {
            try { $notionRoot = Resolve-RepoPath -Primary $NotionDocPath -Fallback '' } catch {}
        }
        Write-Host "AI Nodal Dev Specialist mode: enforcing architecture-aware training posture."
        $manifest = Build-LlmTrainingManifest -RepoRoot $targetRepo -NotionRoot $notionRoot
        Write-Host "Recommended planner graph:"
        Write-Host "  1) Surface extraction -> 2) Concept layering -> 3) Deterministic parser + policy constraints -> 4) Human review -> 5) Closed-loop simulation."
        Write-TrainingManifest -Manifest $manifest
        Ensure-NextCoderMarker -Note "ai-nodal-dev-specialist run complete; use recommended planner graph."
    }
    default {
        throw "Unknown mode: $Mode"
    }
}
