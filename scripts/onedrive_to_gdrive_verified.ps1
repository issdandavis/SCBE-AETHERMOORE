param(
    [string]$SourceRoot = "C:\Users\issda\OneDrive",
    [string]$DestRoot = "gdrive:OneDrive_Migration_2026-03-20",
    [string[]]$Items = @(),
    [string[]]$ExcludeItems = @(
        ".849C9593-D756-4E56-8D6E-42412F2A707B",
        "desktop.ini"
    ),
    [string[]]$ExcludeGlobs = @(),
    [switch]$LocalOnly,
    [switch]$DeleteSource
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-Rclone {
    param(
        [Parameter(Mandatory)][string[]]$Arguments
    )

    & rclone @Arguments
    return $LASTEXITCODE
}

function Add-RcloneExcludes {
    param(
        [Parameter(Mandatory)][string[]]$Arguments,
        [string[]]$Patterns = @()
    )

    $nextArgs = @($Arguments)
    foreach ($pattern in $Patterns) {
        if (-not [string]::IsNullOrWhiteSpace($pattern)) {
            $nextArgs += @("--exclude", $pattern)
        }
    }
    return $nextArgs
}

function Test-RcloneSingleFileMd5 {
    param(
        [Parameter(Mandatory)][string]$LocalPath,
        [Parameter(Mandatory)][string]$RemotePath,
        [Parameter(Mandatory)][string]$CheckLog,
        [Parameter(Mandatory)][string]$CheckCombined
    )

    $localHash = (Get-FileHash -Algorithm MD5 -LiteralPath $LocalPath).Hash.ToLower()
    $remoteOutput = & rclone md5sum $RemotePath 2>&1
    $remoteExit = $LASTEXITCODE
    Set-Content -LiteralPath $CheckLog -Value ($remoteOutput | Out-String)

    if ($remoteExit -ne 0) {
        Set-Content -LiteralPath $CheckCombined -Value ("! {0}" -f [System.IO.Path]::GetFileName($LocalPath))
        return 1
    }

    $remoteLine = $remoteOutput | Select-Object -First 1
    $remoteHash = ""
    if ($remoteLine) {
        $remoteHash = (($remoteLine -split '\s+')[0]).ToLower()
    }

    if ([string]::IsNullOrWhiteSpace($remoteHash)) {
        Set-Content -LiteralPath $CheckCombined -Value ("! {0}" -f [System.IO.Path]::GetFileName($LocalPath))
        return 1
    }

    $isMatch = $localHash -eq $remoteHash
    $marker = if ($isMatch) { "=" } else { "!" }
    Set-Content -LiteralPath $CheckCombined -Value ("{0} {1}" -f $marker, [System.IO.Path]::GetFileName($LocalPath))
    Add-Content -LiteralPath $CheckLog -Value ("LOCAL_MD5={0}" -f $localHash)
    Add-Content -LiteralPath $CheckLog -Value ("REMOTE_MD5={0}" -f $remoteHash)
    return $(if ($isMatch) { 0 } else { 1 })
}

function Get-ItemSizeReport {
    param(
        [Parameter(Mandatory)][string]$Path
    )

    $item = Get-Item -LiteralPath $Path -Force
    if (-not $item.PSIsContainer) {
        return [pscustomobject]@{
            Bytes = [int64]$item.Length
            Text  = "Bytes : $($item.Length)"
        }
    }

    $raw = robocopy $Path "$env:TEMP\onedrive-migration-size-probe" /E /L /BYTES /NJH /NDL /NFL /R:0 /W:0 | Out-String
    $match = [regex]::Match($raw, "Bytes\s*:\s*(\d+)")
    $bytes = if ($match.Success) { [int64]$match.Groups[1].Value } else { 0 }

    return [pscustomobject]@{
        Bytes = $bytes
        Text  = $raw.Trim()
    }
}

function New-LogDirectory {
    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $path = Join-Path $repoRoot "artifacts\onedrive-migration\$stamp"
    New-Item -ItemType Directory -Force -Path $path | Out-Null
    return $path
}

function Get-LocalOnlyManifest {
    param(
        [Parameter(Mandatory)][string]$RootPath,
        [Parameter(Mandatory)][string]$ManifestPath
    )

    $rootItem = Get-Item -LiteralPath $RootPath -Force
    if (-not $rootItem.PSIsContainer) {
        throw "Local-only manifest only applies to directories: $RootPath"
    }

    $rootPrefix = $rootItem.FullName.TrimEnd("\") + "\"
    $localFiles = Get-ChildItem -LiteralPath $RootPath -Force -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { -not ($_.Attributes -band [System.IO.FileAttributes]::Offline) } |
        ForEach-Object {
            $_.FullName.Substring($rootPrefix.Length).Replace("\", "/")
        } |
        Sort-Object

    Set-Content -LiteralPath $ManifestPath -Value $localFiles -Encoding UTF8
    return $localFiles
}

function Remove-LocalFilesFromManifest {
    param(
        [Parameter(Mandatory)][string]$RootPath,
        [Parameter(Mandatory)][string[]]$RelativePaths
    )

    foreach ($relativePath in $RelativePaths) {
        $literalPath = Join-Path $RootPath ($relativePath.Replace("/", "\"))
        if (Test-Path -LiteralPath $literalPath) {
            Remove-Item -LiteralPath $literalPath -Force
        }
    }

    Get-ChildItem -LiteralPath $RootPath -Force -Recurse -Directory -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending |
        ForEach-Object {
            $entries = Get-ChildItem -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
            if (-not $entries) {
                Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
            }
        }
}

$logRoot = New-LogDirectory

if ($Items.Count -eq 0) {
    $Items = Get-ChildItem -LiteralPath $SourceRoot -Force |
        Where-Object { $_.Name -notin $ExcludeItems } |
        Select-Object -ExpandProperty Name
}

$summary = New-Object System.Collections.Generic.List[object]

foreach ($name in $Items) {
    $sourcePath = Join-Path $SourceRoot $name
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        throw "Source item not found: $sourcePath"
    }

    $item = Get-Item -LiteralPath $sourcePath -Force
    $isDirectory = $item.PSIsContainer
    $safeName = ($name -replace '[^A-Za-z0-9._-]', '_')
    $itemLogDir = Join-Path $logRoot $safeName
    New-Item -ItemType Directory -Force -Path $itemLogDir | Out-Null

    $sizeReport = Get-ItemSizeReport -Path $sourcePath
    Set-Content -LiteralPath (Join-Path $itemLogDir "source-size.txt") -Value $sizeReport.Text

    $destPath = ($DestRoot.TrimEnd("/") + "/" + $name.Replace("\", "/"))
    $copyLog = Join-Path $itemLogDir "copy.log"
    $checkLog = Join-Path $itemLogDir "check.log"
    $checkCombined = Join-Path $itemLogDir "check.combined.txt"
    $deleteLog = Join-Path $itemLogDir "delete.log"
    $manifestPath = Join-Path $itemLogDir "local-files.txt"
    $localRelativePaths = @()
    $useManifest = $false

    Write-Host ""
    Write-Host "Processing: $name" -ForegroundColor Cyan
    Write-Host "Source: $sourcePath"
    Write-Host "Dest:   $destPath"
    Write-Host ("Size:   {0:N2} GB" -f ($sizeReport.Bytes / 1GB))

    if ($LocalOnly -and $isDirectory) {
        $localRelativePaths = @(Get-LocalOnlyManifest -RootPath $sourcePath -ManifestPath $manifestPath)
        $useManifest = $true
        Write-Host ("Local-only files selected: {0}" -f $localRelativePaths.Count)
        if ($localRelativePaths.Count -eq 0) {
            $summary.Add([pscustomobject]@{
                Name         = $name
                Type         = "Directory"
                Bytes        = 0
                CopyExit     = 0
                CheckExit    = 0
                DeleteExit   = $null
                Deleted      = $false
                SourcePath   = $sourcePath
                DestPath     = $destPath
                ItemLogDir   = $itemLogDir
                CompletedUtc = (Get-Date).ToUniversalTime().ToString("o")
                Mode         = "local-only-skip-empty"
            }) | Out-Null
            continue
        }
    }

    if ($isDirectory) {
        $copyArgs = @(
            "copy",
            $sourcePath,
            $destPath,
            "-c",
            "--transfers", "1",
            "--checkers", "8",
            "--retries", "1",
            "--low-level-retries", "10",
            "--log-file", $copyLog,
            "--log-level", "INFO"
        )
        if ($useManifest) {
            $copyArgs += @("--files-from-raw", $manifestPath)
        }
        $copyArgs = Add-RcloneExcludes -Arguments $copyArgs -Patterns $ExcludeGlobs
        $copyExit = Invoke-Rclone -Arguments $copyArgs
    }
    else {
        $copyArgs = @(
            "copyto",
            $sourcePath,
            $destPath,
            "-c",
            "--transfers", "1",
            "--checkers", "8",
            "--retries", "1",
            "--low-level-retries", "10",
            "--log-file", $copyLog,
            "--log-level", "INFO"
        )
        $copyExit = Invoke-Rclone -Arguments $copyArgs
    }

    if ($copyExit -ne 0) {
        throw "Copy failed for $name. See $copyLog"
    }

    if ($isDirectory) {
        $checkArgs = @(
            "check",
            $sourcePath,
            $destPath,
            "-c",
            "--one-way",
            "--checkers", "8",
            "--combined", $checkCombined,
            "--log-file", $checkLog,
            "--log-level", "INFO"
        )
        if ($useManifest) {
            $checkArgs += @("--files-from-raw", $manifestPath)
        }
        $checkArgs = Add-RcloneExcludes -Arguments $checkArgs -Patterns $ExcludeGlobs
        $checkExit = Invoke-Rclone -Arguments $checkArgs
    }
    else {
        $checkExit = Test-RcloneSingleFileMd5 -LocalPath $sourcePath -RemotePath $destPath -CheckLog $checkLog -CheckCombined $checkCombined
    }

    if ($checkExit -ne 0) {
        throw "Checksum check failed for $name. See $checkCombined and $checkLog"
    }

    $deleteExit = $null
    if ($DeleteSource) {
        if ($useManifest) {
            Remove-LocalFilesFromManifest -RootPath $sourcePath -RelativePaths $localRelativePaths
            Set-Content -LiteralPath $deleteLog -Value ("Deleted local files from manifest: {0}" -f $localRelativePaths.Count)
            $deleteExit = 0
        }
        elseif ($isDirectory) {
            $deleteArgs = @(
                "delete",
                $sourcePath,
                "--rmdirs",
                "--log-file", $deleteLog,
                "--log-level", "INFO"
            )
            $deleteArgs = Add-RcloneExcludes -Arguments $deleteArgs -Patterns $ExcludeGlobs
            $deleteExit = Invoke-Rclone -Arguments $deleteArgs
        }
        else {
            $deleteArgs = @(
                "deletefile",
                $sourcePath,
                "--log-file", $deleteLog,
                "--log-level", "INFO"
            )
            $deleteExit = Invoke-Rclone -Arguments $deleteArgs
        }

        if ($deleteExit -ne 0) {
            throw "Source deletion failed for $name after verification. See $deleteLog"
        }
    }

    $summary.Add([pscustomobject]@{
        Name         = $name
        Type         = if ($isDirectory) { "Directory" } else { "File" }
        Bytes        = $sizeReport.Bytes
        CopyExit     = $copyExit
        CheckExit    = $checkExit
        DeleteExit   = $deleteExit
        Deleted      = [bool]$DeleteSource
        SourcePath   = $sourcePath
        DestPath     = $destPath
        ItemLogDir   = $itemLogDir
        CompletedUtc = (Get-Date).ToUniversalTime().ToString("o")
        Mode         = if ($useManifest) { "local-only" } else { "full-item" }
    }) | Out-Null
}

$summaryPath = Join-Path $logRoot "summary.json"
$summary | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $summaryPath

Write-Host ""
Write-Host "Completed. Summary written to $summaryPath" -ForegroundColor Green
$summary | Select-Object Name, Type, @{Name="GB";Expression={[math]::Round($_.Bytes / 1GB, 2)}}, Deleted, ItemLogDir |
    Format-Table -AutoSize
