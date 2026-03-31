param(
    [string]$RemoteRoot = "gdrive:SCBE_Verified_Offload/core-snapshots",
    [string]$ArtifactDir = "",
    [switch]$KeepLocalZip
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-Command {
    param(
        [Parameter(Mandatory)][string]$Name
    )

    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw ("Required command not found on PATH: {0}" -f $Name)
    }
}

function New-ScbeCoreManifest {
    param(
        [Parameter(Mandatory)][string]$RepoRoot
    )

    $preferred = @(
        "src",
        "scripts",
        "docs",
        "notes",
        "config",
        "python",
        "api",
        "agents",
        "tests",
        "package.json",
        "package-lock.json",
        "pyproject.toml",
        "requirements.txt",
        "README.md",
        "tsconfig.json",
        "vitest.config.ts"
    )

    $items = New-Object System.Collections.Generic.List[string]
    foreach ($entry in $preferred) {
        $full = Join-Path $RepoRoot $entry
        if (Test-Path -LiteralPath $full) {
            $items.Add($entry) | Out-Null
        }
    }
    return $items
}

function Get-RemoteFileMd5 {
    param(
        [Parameter(Mandatory)][string]$RemoteFile
    )

    $output = & rclone md5sum $RemoteFile 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ("Unable to read remote md5: {0}" -f (($output | Out-String).Trim()))
    }

    $line = $output | Select-Object -First 1
    if (-not $line) {
        throw "Remote md5 output was empty."
    }

    $hash = ($line -split "\s+")[0].Trim().ToLower()
    if ([string]::IsNullOrWhiteSpace($hash)) {
        throw "Remote md5 output could not be parsed."
    }
    return $hash
}

Assert-Command -Name "tar"
Assert-Command -Name "rclone"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\\..")).Path
$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$artifactRoot = if ([string]::IsNullOrWhiteSpace($ArtifactDir)) {
    Join-Path $repoRoot "artifacts\\storage_ship"
} else {
    $ArtifactDir
}

New-Item -ItemType Directory -Force -Path $artifactRoot | Out-Null

$manifest = New-ScbeCoreManifest -RepoRoot $repoRoot
if ($manifest.Count -eq 0) {
    throw "No core project items were found to archive."
}

$zipName = "SCBE_CORE_{0}.zip" -f $stamp
$zipPath = Join-Path $artifactRoot $zipName
$remotePath = "{0}/{1}" -f $RemoteRoot.TrimEnd("/"), $zipName
$rcloneLog = Join-Path $artifactRoot ("SCBE_CORE_{0}.rclone.log" -f $stamp)
$metaPath = Join-Path $artifactRoot ("SCBE_CORE_{0}.json" -f $stamp)

Push-Location $repoRoot
try {
    & tar -a -cf $zipPath @manifest
    if ($LASTEXITCODE -ne 0) {
        throw ("Archive creation failed with exit code {0}" -f $LASTEXITCODE)
    }
}
finally {
    Pop-Location
}

& rclone copyto $zipPath $remotePath --log-file $rcloneLog --log-level INFO
if ($LASTEXITCODE -ne 0) {
    throw ("rclone upload failed with exit code {0}" -f $LASTEXITCODE)
}

$localMd5 = (Get-FileHash -LiteralPath $zipPath -Algorithm MD5).Hash.ToLower()
$remoteMd5 = Get-RemoteFileMd5 -RemoteFile $remotePath
$verified = $localMd5 -eq $remoteMd5

$meta = [ordered]@{
    repo_root = $repoRoot
    created_utc = [DateTime]::UtcNow.ToString("o")
    local_zip = $zipPath
    remote = $remotePath
    local_md5 = $localMd5
    remote_md5 = $remoteMd5
    verified = $verified
    included_items = @($manifest)
    rclone_log = $rcloneLog
}

$meta | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $metaPath -Encoding UTF8

if (-not $verified) {
    throw ("Backup uploaded but checksum verification failed. See {0}" -f $metaPath)
}

if (-not $KeepLocalZip) {
    Remove-Item -LiteralPath $zipPath -Force
}

Write-Host ("REMOTE={0}" -f $remotePath)
Write-Host ("META={0}" -f $metaPath)
Write-Host ("VERIFIED_MD5={0}" -f $remoteMd5)
