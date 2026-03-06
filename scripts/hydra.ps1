param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$env:PYTHONPATH = "$repoRoot;$repoRoot\src;$env:PYTHONPATH"

& python -m hydra @Args
exit $LASTEXITCODE
