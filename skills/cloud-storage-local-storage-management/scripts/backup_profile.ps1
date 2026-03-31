param(
    [string]$SourceRoot = $env:USERPROFILE,
    [string]$TargetRoot = "",
    [string]$OutDir = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\\..\\..")) "artifacts\\storage-management"),
    [double]$MinFreeGb = 25,
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

function Convert-ToGiB {
    param([double]$Bytes)
    if ($Bytes -le 0) { return 0.0 }
    return [math]::Round($Bytes / 1GB, 2)
}

function Get-CloudCandidates {
    param([string]$UserRoot)
    $items = @(
        @{ name = "Dropbox"; path = (Join-Path $UserRoot "Dropbox") },
        @{ name = "GoogleDrive"; path = (Join-Path $UserRoot "Drive") },
        @{ name = "OneDrive"; path = (Join-Path $UserRoot "OneDrive") },
        @{ name = "ProtonDrive"; path = (Join-Path $UserRoot "Proton Drive") }
    )
    foreach ($item in $items) {
        if (Test-Path -LiteralPath $item.path) {
            try {
                $resolved = Get-Item -LiteralPath $item.path -Force
                $drive = Get-PSDrive -Name $resolved.PSDrive.Name -PSProvider FileSystem -ErrorAction Stop
                [pscustomobject]@{
                    name = $item.name
                    path = $resolved.FullName
                    free_gb = Convert-ToGiB $drive.Free
                }
            } catch {
            }
        }
    }
}

if (-not (Test-Path -LiteralPath $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

$resolvedSource = (Resolve-Path -LiteralPath $SourceRoot).Path
$candidates = @(Get-CloudCandidates -UserRoot $resolvedSource)

if ([string]::IsNullOrWhiteSpace($TargetRoot)) {
    $candidate = $candidates | Sort-Object free_gb -Descending | Select-Object -First 1
    if (-not $candidate) {
        throw "No cloud-sync target detected. Provide -TargetRoot explicitly."
    }
    $TargetRoot = Join-Path $candidate.path "machine-backup\\$([IO.Path]::GetFileName($resolvedSource))"
}

$resolvedTargetParent = Split-Path -Parent $TargetRoot
if (-not (Test-Path -LiteralPath $resolvedTargetParent)) {
    New-Item -ItemType Directory -Path $resolvedTargetParent -Force | Out-Null
}

$targetDriveLetter = (Get-Item -LiteralPath $resolvedTargetParent).PSDrive.Name
$targetDrive = Get-PSDrive -Name $targetDriveLetter -PSProvider FileSystem -ErrorAction Stop
$freeGb = Convert-ToGiB $targetDrive.Free

if ($freeGb -lt $MinFreeGb) {
    throw "Target drive only has $freeGb GB free. Minimum required is $MinFreeGb GB."
}

$excludeDirs = New-Object System.Collections.Generic.List[string]
foreach ($candidate in $candidates) {
    $excludeDirs.Add($candidate.path)
}

$staticExcludes = @(
    (Join-Path $resolvedSource "AppData\\Local\\Temp"),
    (Join-Path $resolvedSource "AppData\\Roaming\\protonmail\\bridge-v3\\gluon\\backend\\store"),
    (Join-Path $resolvedSource ".cache"),
    (Join-Path $resolvedSource ".npm"),
    (Join-Path $resolvedSource ".nuget\\packages")
)

foreach ($path in $staticExcludes) {
    if (Test-Path -LiteralPath $path) {
        $excludeDirs.Add($path)
    }
}

$excludeDirs = $excludeDirs | Where-Object { $_ } | Select-Object -Unique

$logPath = Join-Path $OutDir ("backup-profile-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")
$xdArgs = ($excludeDirs | ForEach-Object { '"' + $_ + '"' }) -join " "
$command = "robocopy `"$resolvedSource`" `"$TargetRoot`" /E /Z /FFT /XJ /R:1 /W:1 /MT:16 /COPY:DAT /DCOPY:DAT /XD $xdArgs /LOG:`"$logPath`""

Write-Output "Source: $resolvedSource"
Write-Output "Target: $TargetRoot"
Write-Output "Free GB on target drive: $freeGb"
Write-Output "Exclude count: $($excludeDirs.Count)"
Write-Output "Log: $logPath"
Write-Output "Command: $command"

if (-not $Apply) {
    Write-Output "Dry run only. Re-run with -Apply to execute."
    return
}

Invoke-Expression $command
$exitCode = $LASTEXITCODE
Write-Output "robocopy exit code: $exitCode"
