param(
    [ValidateSet("status", "kaggle", "hf", "env", "routes", "inventory-kaggle", "inventory-hf", "inventory-colab", "colab-url", "colab-show", "training-audit")]
    [string]$Action = "status",
    [string]$Notebook = "generator",
    [switch]$ListInventory
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$EnvFile = Join-Path $RepoRoot "config\connector_oauth\.env.connector.oauth"
$RouteMapPath = Join-Path $RepoRoot "config\system\host_compute_routes.json"

function Load-ScbeEnvFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return
    }

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }
        $parts = $line -split "=", 2
        if ($parts.Count -ne 2) {
            return
        }
        $name = $parts[0].Trim()
        $value = $parts[1].Trim().Trim('"').Trim("'")
        if ($name) {
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

function Mask-Value {
    param([string]$Value)
    if (-not $Value) {
        return "MISSING"
    }
    if ($Value.Length -le 6) {
        return "SET"
    }
    return "{0}...{1}" -f $Value.Substring(0, 3), $Value.Substring($Value.Length - 3)
}

function Initialize-HostEnv {
    Load-ScbeEnvFile -Path $EnvFile

    if (-not $env:KAGGLE_API_TOKEN -and $env:KAGGLE_KEY) {
        $env:KAGGLE_API_TOKEN = $env:KAGGLE_KEY
    }
    if (-not $env:KAGGLE_KEY -and $env:KAGGLE_API_TOKEN) {
        $env:KAGGLE_KEY = $env:KAGGLE_API_TOKEN
    }
}

function Get-KaggleStatus {
    $kaggleExe = (Get-Command kaggle -ErrorAction SilentlyContinue)
    $hasUser = [string]::IsNullOrWhiteSpace($env:KAGGLE_USERNAME) -eq $false
    $hasApiToken = [string]::IsNullOrWhiteSpace($env:KAGGLE_API_TOKEN) -eq $false
    $hasKey = [string]::IsNullOrWhiteSpace($env:KAGGLE_KEY) -eq $false
    $ok = ($kaggleExe -and $hasUser -and ($hasApiToken -or $hasKey))
    $detail = if ($ok) { "credentials loaded" } else { "not checked" }
    $authMode = if ($hasApiToken) { "api_token" } elseif ($hasKey) { "legacy_key" } else { "missing" }

    if ($kaggleExe -and $hasUser -and $hasKey) {
        try {
            $configOut = & $kaggleExe.Source config view 2>$null
            if ($LASTEXITCODE -eq 0 -or (($configOut -join "`n") -match "username:")) {
                $ok = $true
                $detail = "authenticated"
            } else {
                $detail = "credentials loaded"
            }
        } catch {
            $detail = "credentials loaded"
        }
    } elseif ($kaggleExe) {
        $detail = "CLI present, credentials incomplete"
    } else {
        $detail = "CLI missing"
    }

    [pscustomobject]@{
        host = "kaggle"
        cli = if ($kaggleExe) { $kaggleExe.Source } else { "MISSING" }
        username = if ($hasUser) { $env:KAGGLE_USERNAME } else { "MISSING" }
        auth_mode = $authMode
        api_token = Mask-Value -Value $env:KAGGLE_API_TOKEN
        key = Mask-Value -Value $env:KAGGLE_KEY
        ok = $ok
        detail = $detail
    }
}

function Get-HfStatus {
    $hfExe = (Get-Command hf -ErrorAction SilentlyContinue)
    $hasToken = [string]::IsNullOrWhiteSpace($env:HF_TOKEN) -eq $false
    $ok = ($hfExe -and $hasToken)
    $detail = if ($ok) { "token loaded" } else { "not checked" }
    $who = $null

    if ($hfExe -and $hasToken) {
        try {
            $who = & $hfExe.Source auth whoami 2>$null
            if ($LASTEXITCODE -eq 0) {
                $ok = $true
                $detail = "authenticated"
            } else {
                $detail = "token loaded, live auth check failed"
            }
        } catch {
            $detail = "token loaded, live auth check failed"
        }
    } elseif ($hfExe) {
        $detail = "CLI present, token missing"
    } else {
        $detail = "CLI missing"
    }

    [pscustomobject]@{
        host = "huggingface"
        cli = if ($hfExe) { $hfExe.Source } else { "MISSING" }
        token = Mask-Value -Value $env:HF_TOKEN
        ok = $ok
        detail = $detail
        whoami = if ($who) { ($who -join "`n").Trim() } else { "" }
    }
}

function Show-InventoryHint {
    param([string]$Host)
    switch ($Host) {
        "kaggle" {
            Write-Output "Inventory commands:"
            Write-Output "  kaggle models list --user $env:KAGGLE_USERNAME"
            Write-Output "  kaggle datasets list --user $env:KAGGLE_USERNAME"
        }
        "hf" {
            Write-Output "Inventory commands:"
            Write-Output "  hf models ls --author issdandavis --limit 50"
            Write-Output "  hf datasets ls --author issdandavis --limit 50"
            Write-Output "  hf spaces ls --author issdandavis --limit 50"
            Write-Output "  hf models ls --author SCBE-AETHER --limit 50"
            Write-Output "  hf datasets ls --author SCBE-AETHER --limit 50"
            Write-Output "  hf spaces ls --author SCBE-AETHER --limit 50"
        }
    }
}

function Get-RouteMapStatus {
    [pscustomobject]@{
        route_map = if (Test-Path $RouteMapPath) { $RouteMapPath } else { "MISSING" }
        host_inventory_dir = Join-Path $RepoRoot "artifacts\host_inventory"
        hf_eval_script = Join-Path $RepoRoot "scripts\eval_legacy_hf_model.py"
        colab_catalog_script = Join-Path $RepoRoot "scripts\system\colab_workflow_catalog.py"
        dataset_pipeline_script = Join-Path $RepoRoot "scripts\cloud_kernel_data_pipeline.py"
        hf_training_loop = Join-Path $RepoRoot "scripts\hf_training_loop.py"
    }
}

function Invoke-HfInventory {
    $outDir = Join-Path $RepoRoot "artifacts\host_inventory"
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"

    $files = @{
        user_models = Join-Path $outDir "hf_models_issdandavis.txt"
        user_datasets = Join-Path $outDir "hf_datasets_issdandavis.txt"
        user_spaces = Join-Path $outDir "hf_spaces_issdandavis.txt"
        org_models = Join-Path $outDir "hf_models_scbe_aether.txt"
        org_datasets = Join-Path $outDir "hf_datasets_scbe_aether.txt"
        org_spaces = Join-Path $outDir "hf_spaces_scbe_aether.txt"
    }

    & hf models ls --author issdandavis --limit 20 | Set-Content -Encoding utf8 $files.user_models
    & hf datasets ls --author issdandavis --limit 20 | Set-Content -Encoding utf8 $files.user_datasets
    & hf spaces ls --author issdandavis --limit 20 | Set-Content -Encoding utf8 $files.user_spaces
    & hf models ls --author SCBE-AETHER --limit 20 | Set-Content -Encoding utf8 $files.org_models
    & hf datasets ls --author SCBE-AETHER --limit 20 | Set-Content -Encoding utf8 $files.org_datasets
    & hf spaces ls --author SCBE-AETHER --limit 20 | Set-Content -Encoding utf8 $files.org_spaces

    [pscustomobject]@{
        ok = $true
        host = "huggingface"
        files = $files
    }
}

function Invoke-KaggleInventory {
    $outDir = Join-Path $RepoRoot "artifacts\host_inventory"
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    if (-not $env:KAGGLE_KEY -and $env:KAGGLE_API_TOKEN) {
        $env:KAGGLE_KEY = $env:KAGGLE_API_TOKEN
    }

    $files = @{
        competitions = Join-Path $outDir "kaggle_competitions.csv"
        datasets = Join-Path $outDir "kaggle_datasets.csv"
        kernels = Join-Path $outDir "kaggle_kernels.csv"
        models = Join-Path $outDir "kaggle_models.csv"
        config = Join-Path $outDir "kaggle_config.txt"
    }

    & kaggle config view | Set-Content -Encoding utf8 $files.config
    & kaggle competitions list -v | Set-Content -Encoding utf8 $files.competitions
    & kaggle datasets list --mine -v | Set-Content -Encoding utf8 $files.datasets
    & kaggle kernels list --mine --page-size 50 -v | Set-Content -Encoding utf8 $files.kernels
    & kaggle models list --owner issacizrealdavis --page-size 50 -v | Set-Content -Encoding utf8 $files.models

    [pscustomobject]@{
        ok = $true
        host = "kaggle"
        files = $files
    }
}

function Invoke-ColabInventory {
    $outDir = Join-Path $RepoRoot "artifacts\host_inventory"
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    $catalogPath = Join-Path $outDir "colab_catalog.json"
    & python (Join-Path $RepoRoot "scripts\system\colab_workflow_catalog.py") list --json | Set-Content -Encoding utf8 $catalogPath

    [pscustomobject]@{
        ok = $true
        host = "colab"
        catalog = $catalogPath
    }
}

function Get-ColabNotebookUrl {
    param([string]$Name)
    & python (Join-Path $RepoRoot "scripts\system\colab_workflow_catalog.py") url $Name
}

function Show-ColabNotebook {
    param([string]$Name)
    & python (Join-Path $RepoRoot "scripts\system\colab_workflow_catalog.py") show $Name --json
}

function Invoke-TrainingAudit {
    & python (Join-Path $RepoRoot "scripts\system\training_ops_audit.py") --json
}

Initialize-HostEnv

switch ($Action) {
    "env" {
        [pscustomobject]@{
            KAGGLE_USERNAME = if ($env:KAGGLE_USERNAME) { $env:KAGGLE_USERNAME } else { "MISSING" }
            KAGGLE_API_TOKEN = Mask-Value -Value $env:KAGGLE_API_TOKEN
            KAGGLE_KEY = Mask-Value -Value $env:KAGGLE_KEY
            HF_TOKEN = Mask-Value -Value $env:HF_TOKEN
            HF_CHAT_MODEL = if ($env:HF_CHAT_MODEL) { $env:HF_CHAT_MODEL } else { "MISSING" }
            AETHERBOT_HF_MODEL = if ($env:AETHERBOT_HF_MODEL) { $env:AETHERBOT_HF_MODEL } else { "MISSING" }
        } | ConvertTo-Json -Depth 3
    }
    "kaggle" {
        Get-KaggleStatus | ConvertTo-Json -Depth 4
        if ($ListInventory) {
            Show-InventoryHint -Host "kaggle"
        }
    }
    "hf" {
        Get-HfStatus | ConvertTo-Json -Depth 5
        if ($ListInventory) {
            Show-InventoryHint -Host "hf"
        }
    }
    "routes" {
        Get-RouteMapStatus | ConvertTo-Json -Depth 4
    }
    "inventory-hf" {
        Invoke-HfInventory | ConvertTo-Json -Depth 5
    }
    "inventory-kaggle" {
        Invoke-KaggleInventory | ConvertTo-Json -Depth 5
    }
    "inventory-colab" {
        Invoke-ColabInventory | ConvertTo-Json -Depth 5
    }
    "colab-url" {
        Get-ColabNotebookUrl -Name $Notebook
    }
    "colab-show" {
        Show-ColabNotebook -Name $Notebook
    }
    "training-audit" {
        Invoke-TrainingAudit
    }
    default {
        [pscustomobject]@{
            kaggle = Get-KaggleStatus
            huggingface = Get-HfStatus
            routes = Get-RouteMapStatus
        } | ConvertTo-Json -Depth 6
        if ($ListInventory) {
            Show-InventoryHint -Host "kaggle"
            Show-InventoryHint -Host "hf"
        }
    }
}
