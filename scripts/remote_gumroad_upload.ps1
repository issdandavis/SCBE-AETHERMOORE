param(
    [string]$ImagesDir = "",
    [switch]$DryRun,
    [switch]$Headless,
    [int]$Passes = 1,
    [int]$Timeout = 30,
    [string]$Targets = "",
    [string]$DebugAddress = ""
)

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runner = Join-Path $repoRoot "remote_gumroad_upload.py"

$argsList = @(
    "python",
    (Resolve-Path $runner).Path
)

if ($ImagesDir) {
    $argsList += "--images-dir"
    $argsList += $ImagesDir
}
if ($DryRun) { $argsList += "--dry-run" }
if ($Headless) { $argsList += "--headless" }
if ($Passes -gt 1) {
    $argsList += "--passes"
    $argsList += $Passes
}
if ($Timeout -ne 30) {
    $argsList += "--timeout"
    $argsList += $Timeout
}
if ($Targets) {
    $argsList += "--targets"
    $targetsList = $Targets.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    $argsList += $targetsList
}
if ($DebugAddress) {
    $argsList += "--no-start-chrome"
    $argsList += "--debugger-address"
    $argsList += $DebugAddress
}

& $argsList[0] @argsList[1..($argsList.Length - 1)]
