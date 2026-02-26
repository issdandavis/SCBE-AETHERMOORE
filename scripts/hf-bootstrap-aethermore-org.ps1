param(
    [Parameter(Mandatory = $true)]
    [string]$Org,

    [switch]$PrivateByDefault,
    [switch]$MoveExisting,
    [switch]$Execute
)

$ErrorActionPreference = 'Stop'
$dryRun = -not $Execute

function Invoke-Step {
    param([string]$Cmd)
    if ($dryRun) {
        Write-Host "[DRY] $Cmd" -ForegroundColor Yellow
    }
    else {
        Write-Host "[RUN] $Cmd" -ForegroundColor Cyan
        Invoke-Expression $Cmd
    }
}

Write-Host "=== AetherMore HF Org Bootstrap ===" -ForegroundColor Green
Write-Host "Org: $Org"
Write-Host "Mode: $(if($dryRun){'DRY-RUN'}else{'EXECUTE'})"

Invoke-Step "hf auth whoami"

$repos = @(
    @{ Name = 'phdm-21d-embedding'; Type = 'model';   Source = 'issdandavis/phdm-21d-embedding' },
    @{ Name = 'spiralverse-ai-federated-v1'; Type = 'model'; Source = 'issdandavis/spiralverse-ai-federated-v1' },
    @{ Name = 'ultradata-math'; Type = 'dataset'; Source = 'issdandavis/UltraData-Math' },
    @{ Name = 'aethermoor-rag-training-data'; Type = 'dataset'; Source = 'issdandavis/aethermoor-rag-training-data' },
    @{ Name = 'scbe-aethermoore-datasets'; Type = 'dataset'; Source = 'issdandavis/scbe-aethermoore-datasets' },
    @{ Name = 'scbe-interaction-logs'; Type = 'dataset'; Source = 'issdandavis/scbe-interaction-logs' },
    @{ Name = 'scbe-aethermoore-training-data'; Type = 'dataset'; Source = 'issdandavis/scbe-aethermoore-training-data' },
    @{ Name = 'scbe-aethermoore-knowledge-base'; Type = 'dataset'; Source = 'issdandavis/scbe-aethermoore-knowledge-base' },
    @{ Name = 'perplexity-spaces-datacenter'; Type = 'dataset'; Source = 'issdandavis/perplexity-spaces-datacenter' }
)

$privacy = if ($PrivateByDefault) { '--private' } else { '--no-private' }

foreach ($r in $repos) {
    $target = "$Org/$($r.Name)"
    Invoke-Step "hf repo create $target --repo-type $($r.Type) $privacy --exist-ok"

    if ($MoveExisting -and $r.Source) {
        Invoke-Step "hf repo move $($r.Source) $target --repo-type $($r.Type)"
    }
}

Write-Host "`n=== Next Upload Pattern ===" -ForegroundColor Green
Write-Host "hf upload $Org/scbe-aethermoore-datasets . . --repo-type dataset"
Write-Host "# add commit message when executing: --commit-message 'publish: dataset $(Get-Date -Format s)'"

Write-Host "`nDone."

