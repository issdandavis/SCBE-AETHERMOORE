param(
    [string]$ProjectRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$N8nUserFolder = "C:\Users\issda\SCBE-AETHERMOORE\.n8n_local",
    [switch]$NoImportWorkflows,
    [switch]$ResetN8nUserFolder,
    [switch]$PublishWorkflows,
    [switch]$BuildTrainingFunnel,
    [switch]$StartServices
)

$ErrorActionPreference = "Stop"
$script:bootstrapSteps = @()

function Require-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "Required command not found: $Name"
    }
    return $cmd.Source
}

function Add-StepResult {
    param(
        [hashtable]$Report,
        [string]$Step,
        [string]$Status,
        [string]$Detail
    )

    $script:bootstrapSteps += ,([ordered]@{
        step = $Step
        status = $Status
        detail = $Detail
        timestamp_utc = [DateTime]::UtcNow.ToString("o")
    })
}

$report = [ordered]@{
    started_at_utc = [DateTime]::UtcNow.ToString("o")
    project_root = $ProjectRoot
    n8n_user_folder = $N8nUserFolder
    import_workflows = (-not [bool]$NoImportWorkflows)
    reset_n8n_user_folder = [bool]$ResetN8nUserFolder
    publish_workflows = [bool]$PublishWorkflows
    build_training_funnel = [bool]$BuildTrainingFunnel
    start_services = [bool]$StartServices
    steps = @()
}

try {
    if (-not (Test-Path $ProjectRoot)) {
        throw "Project root not found: $ProjectRoot"
    }

    Set-Location $ProjectRoot

    $pythonPath = Require-Command -Name "python"
    Add-StepResult -Report $report -Step "check_python" -Status "ok" -Detail $pythonPath

    $n8nPath = Require-Command -Name "n8n"
    Add-StepResult -Report $report -Step "check_n8n" -Status "ok" -Detail $n8nPath

    $bridgePath = Join-Path $ProjectRoot "workflows\n8n\scbe_n8n_bridge.py"
    if (-not (Test-Path $bridgePath)) {
        throw "Bridge file missing: $bridgePath"
    }
    Add-StepResult -Report $report -Step "check_bridge_file" -Status "ok" -Detail $bridgePath

    $bridgeImportOut = python -c "import workflows.n8n.scbe_n8n_bridge as b; print(b.app.title, b.app.version)"
    Add-StepResult -Report $report -Step "bridge_import" -Status "ok" -Detail ($bridgeImportOut -join ' ')

    if (-not $NoImportWorkflows) {
        $importScript = Join-Path $ProjectRoot "workflows\n8n\import_workflows.ps1"
        if (-not (Test-Path $importScript)) {
            throw "Import script missing: $importScript"
        }

        & $importScript `
            -ProjectRoot $ProjectRoot `
            -N8nUserFolder $N8nUserFolder `
            -ResetUserFolder:$ResetN8nUserFolder `
            -PublishWorkflows:$PublishWorkflows
        Add-StepResult -Report $report -Step "import_workflows" -Status "ok" -Detail "Workflow import completed"

        $env:N8N_USER_FOLDER = $N8nUserFolder
        $workflowCount = (n8n list:workflow | Measure-Object -Line).Lines
        Add-StepResult -Report $report -Step "workflow_count" -Status "ok" -Detail "Detected $workflowCount workflow(s)"
    }

    if ($BuildTrainingFunnel) {
        $funnelScript = Join-Path $ProjectRoot "scripts\build_hydra_training_funnel.py"
        if (-not (Test-Path $funnelScript)) {
            throw "Funnel script missing: $funnelScript"
        }

        python $funnelScript --repo-root $ProjectRoot --output-dir training-data/funnel --no-dedupe
        Add-StepResult -Report $report -Step "build_training_funnel" -Status "ok" -Detail "Funnel built at training-data/funnel"
    }

    if ($StartServices) {
        $startScript = Join-Path $ProjectRoot "workflows\n8n\start_n8n_local.ps1"
        if (-not (Test-Path $startScript)) {
            throw "Start script missing: $startScript"
        }

        & $startScript -ProjectRoot $ProjectRoot -N8nUserFolder $N8nUserFolder -ImportWorkflows:$false
        Add-StepResult -Report $report -Step "start_services" -Status "ok" -Detail "Bridge + n8n start command executed"
    }

    $report.status = "ok"
}
catch {
    $report.status = "error"
    $report.error = $_.Exception.Message
    Add-StepResult -Report $report -Step "bootstrap" -Status "error" -Detail $_.Exception.Message
}
finally {
    $report.steps = $script:bootstrapSteps
    $report.finished_at_utc = [DateTime]::UtcNow.ToString("o")

    $artifactDir = Join-Path $ProjectRoot "artifacts\bootstrap"
    New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null

    $stamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
    $reportPath = Join-Path $artifactDir "bootstrap_report_$stamp.json"
    $report | ConvertTo-Json -Depth 10 | Set-Content -Path $reportPath -Encoding UTF8

    Write-Host "SCBE bootstrap report: $reportPath"

    if ($report.status -ne "ok") {
        throw "Bootstrap failed: $($report.error)"
    }
}
