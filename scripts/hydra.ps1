param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$env:PYTHONPATH = "$repoRoot;$repoRoot\src;$env:PYTHONPATH"
$ledgerDir = Join-Path $repoRoot "artifacts\hydra"
if (-not (Test-Path $ledgerDir)) {
    New-Item -ItemType Directory -Path $ledgerDir -Force | Out-Null
}
if ([string]::IsNullOrWhiteSpace($env:HYDRA_LEDGER_DB)) {
    $env:HYDRA_LEDGER_DB = Join-Path $ledgerDir "ledger.db"
}

& python -m hydra @Args
exit $LASTEXITCODE
