param(
    [string]$ProjectRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$N8nUserFolder = "C:\Users\issda\SCBE-AETHERMOORE\.n8n_local",
    [switch]$ForceImport,
    [switch]$ResetUserFolder,
    [switch]$PublishWorkflows
)

$ErrorActionPreference = "Stop"
$workflowDir = Join-Path $ProjectRoot "workflows\n8n"

if (-not (Test-Path $workflowDir)) {
    throw "Workflow directory not found: $workflowDir"
}

$env:N8N_USER_FOLDER = $N8nUserFolder
if ($ResetUserFolder -and (Test-Path $N8nUserFolder)) {
    Write-Host "Resetting N8N user folder: $N8nUserFolder"
    Remove-Item -Recurse -Force $N8nUserFolder
}
New-Item -ItemType Directory -Force -Path $N8nUserFolder | Out-Null

$files = Get-ChildItem -Path $workflowDir -Filter *.workflow.json | Sort-Object Name
if (-not $files) {
    throw "No workflow JSON files found in $workflowDir"
}

Write-Host "Using N8N_USER_FOLDER=$N8nUserFolder"

function Normalize-WorkflowName {
    param([string]$Name)
    if (-not $Name) { return "" }
    $lower = $Name.ToLowerInvariant()
    # Remove punctuation/symbol differences (emdash, arrows, etc.) and normalize spacing.
    $alnum = [regex]::Replace($lower, "[^a-z0-9]+", " ")
    return ($alnum -replace "\s+", " ").Trim()
}

# Build a set of existing workflow names so reruns are idempotent by default.
$existingByName = @{}
$targetWorkflowKeys = @{}
if (-not $ForceImport) {
    $existingRaw = n8n list:workflow 2>$null
    foreach ($line in $existingRaw) {
        if ($line -match "^[^|]+\|(.+)$") {
            $normalized = Normalize-WorkflowName $Matches[1].Trim()
            if ($normalized) {
                $existingByName[$normalized] = $true
            }
        }
    }
}

foreach ($f in $files) {
    $workflowJson = Get-Content -Path $f.FullName -Raw | ConvertFrom-Json
    $workflowName = [string]$workflowJson.name

    if (-not $workflowName) {
        throw "Workflow file missing name: $($f.FullName)"
    }

    $workflowKey = Normalize-WorkflowName $workflowName
    if ($workflowKey) {
        $targetWorkflowKeys[$workflowKey] = $workflowName
    }

    if (-not $ForceImport -and $existingByName.ContainsKey($workflowKey)) {
        Write-Host "Skipping existing workflow: $workflowName"
        continue
    }

    Write-Host "Importing $workflowName"
    n8n import:workflow --input "$($f.FullName)"
    if ($workflowKey) {
        $existingByName[$workflowKey] = $true
    }
}

if ($PublishWorkflows) {
    Write-Host "Publishing workflows for local stack activation"

    $publishTargets = @{}
    $listedWorkflows = n8n list:workflow 2>$null

    foreach ($line in $listedWorkflows) {
        if ($line -match "^([^|]+)\|(.+)$") {
            $workflowId = $Matches[1].Trim()
            $workflowName = $Matches[2].Trim()
            $workflowKey = Normalize-WorkflowName $workflowName

            if ($workflowId -and $workflowKey -and $targetWorkflowKeys.ContainsKey($workflowKey)) {
                $publishTargets[$workflowId] = $workflowName
            }
        }
    }

    if ($publishTargets.Count -eq 0) {
        Write-Warning "No matching workflows found to publish."
    } else {
        foreach ($entry in $publishTargets.GetEnumerator()) {
            Write-Host "Publishing $($entry.Value) [$($entry.Key)]"
            n8n publish:workflow --id "$($entry.Key)"
        }
        Write-Host "Published $($publishTargets.Count) workflow(s)."
    }
}

$exportCheck = Join-Path $N8nUserFolder "export_check"
New-Item -ItemType Directory -Force -Path $exportCheck | Out-Null
$exportFile = Join-Path $exportCheck "workflows.json"
n8n export:workflow --all --output "$exportFile"

Write-Host "Import complete. Export verification written to: $exportFile"
