param(
    [ValidateSet("about", "dirs", "files", "mkdir", "put-file", "put-dir", "get-file", "get-dir", "verify-file")]
    [string]$Action = "about",
    [string]$Remote = "gdrive",
    [string]$RemotePath = "",
    [string]$LocalPath = "",
    [switch]$Recurse
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-Rclone {
    $cmd = Get-Command rclone -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "rclone is not installed or not on PATH."
    }
}

function Invoke-Rclone {
    param(
        [Parameter(Mandatory)][string[]]$Arguments
    )

    & rclone @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw ("rclone failed with exit code {0}: {1}" -f $LASTEXITCODE, ($Arguments -join " "))
    }
}

function Resolve-RemoteSpec {
    param(
        [string]$Path
    )

    if (-not [string]::IsNullOrWhiteSpace($Path) -and $Path -match "^[A-Za-z0-9_-]+:") {
        return $Path
    }

    $base = "{0}:SCBE_Verified_Offload" -f $Remote
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $base
    }

    $trimmed = $Path.Trim().TrimStart("/").Replace("\", "/")
    if ([string]::IsNullOrWhiteSpace($trimmed)) {
        return $base
    }

    return "$base/$trimmed"
}

function Get-RemoteFileMd5 {
    param(
        [Parameter(Mandatory)][string]$RemoteFile
    )

    $output = & rclone md5sum $RemoteFile 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ("Unable to read remote md5: {0}" -f ($output | Out-String).Trim())
    }

    $line = ($output | Select-Object -First 1)
    if (-not $line) {
        throw "Remote md5 output was empty."
    }

    $hash = ($line -split "\s+")[0].Trim().ToLower()
    if ([string]::IsNullOrWhiteSpace($hash)) {
        throw "Remote md5 output could not be parsed."
    }
    return $hash
}

Assert-Rclone

switch ($Action) {
    "about" {
        Invoke-Rclone @("about", ("{0}:" -f $Remote))
        break
    }
    "dirs" {
        Invoke-Rclone @("lsd", (Resolve-RemoteSpec -Path $RemotePath))
        break
    }
    "files" {
        $args = @("lsf", "--files-only", (Resolve-RemoteSpec -Path $RemotePath))
        if ($Recurse) {
            $args = @("lsf", "--files-only", "-R", (Resolve-RemoteSpec -Path $RemotePath))
        }
        Invoke-Rclone -Arguments $args
        break
    }
    "mkdir" {
        Invoke-Rclone @("mkdir", (Resolve-RemoteSpec -Path $RemotePath))
        break
    }
    "put-file" {
        if ([string]::IsNullOrWhiteSpace($LocalPath)) {
            throw "put-file requires -LocalPath."
        }
        if (-not (Test-Path -LiteralPath $LocalPath -PathType Leaf)) {
            throw ("Local file not found: {0}" -f $LocalPath)
        }
        $leaf = Split-Path -Leaf $LocalPath
        $remoteFile = if ([string]::IsNullOrWhiteSpace($RemotePath)) { Resolve-RemoteSpec -Path $leaf } else { Resolve-RemoteSpec -Path $RemotePath }
        Invoke-Rclone @("copyto", $LocalPath, $remoteFile)
        Write-Host ("uploaded {0} -> {1}" -f $LocalPath, $remoteFile)
        break
    }
    "put-dir" {
        if ([string]::IsNullOrWhiteSpace($LocalPath)) {
            throw "put-dir requires -LocalPath."
        }
        if (-not (Test-Path -LiteralPath $LocalPath -PathType Container)) {
            throw ("Local directory not found: {0}" -f $LocalPath)
        }
        $leaf = Split-Path -Leaf $LocalPath
        $remoteDir = if ([string]::IsNullOrWhiteSpace($RemotePath)) { Resolve-RemoteSpec -Path $leaf } else { Resolve-RemoteSpec -Path $RemotePath }
        Invoke-Rclone @("copy", $LocalPath, $remoteDir)
        Write-Host ("uploaded {0} -> {1}" -f $LocalPath, $remoteDir)
        break
    }
    "get-file" {
        if ([string]::IsNullOrWhiteSpace($RemotePath)) {
            throw "get-file requires -RemotePath."
        }
        if ([string]::IsNullOrWhiteSpace($LocalPath)) {
            throw "get-file requires -LocalPath."
        }
        $remoteFile = Resolve-RemoteSpec -Path $RemotePath
        $parent = Split-Path -Parent $LocalPath
        if ($parent) {
            New-Item -ItemType Directory -Force -Path $parent | Out-Null
        }
        Invoke-Rclone @("copyto", $remoteFile, $LocalPath)
        Write-Host ("downloaded {0} -> {1}" -f $remoteFile, $LocalPath)
        break
    }
    "get-dir" {
        if ([string]::IsNullOrWhiteSpace($RemotePath)) {
            throw "get-dir requires -RemotePath."
        }
        if ([string]::IsNullOrWhiteSpace($LocalPath)) {
            throw "get-dir requires -LocalPath."
        }
        New-Item -ItemType Directory -Force -Path $LocalPath | Out-Null
        $remoteDir = Resolve-RemoteSpec -Path $RemotePath
        Invoke-Rclone @("copy", $remoteDir, $LocalPath)
        Write-Host ("downloaded {0} -> {1}" -f $remoteDir, $LocalPath)
        break
    }
    "verify-file" {
        if ([string]::IsNullOrWhiteSpace($RemotePath)) {
            throw "verify-file requires -RemotePath."
        }
        if ([string]::IsNullOrWhiteSpace($LocalPath)) {
            throw "verify-file requires -LocalPath."
        }
        if (-not (Test-Path -LiteralPath $LocalPath -PathType Leaf)) {
            throw ("Local file not found: {0}" -f $LocalPath)
        }
        $remoteFile = Resolve-RemoteSpec -Path $RemotePath
        $localMd5 = (Get-FileHash -LiteralPath $LocalPath -Algorithm MD5).Hash.ToLower()
        $remoteMd5 = Get-RemoteFileMd5 -RemoteFile $remoteFile
        $match = $localMd5 -eq $remoteMd5
        [pscustomobject]@{
            local_path = $LocalPath
            remote_path = $remoteFile
            local_md5 = $localMd5
            remote_md5 = $remoteMd5
            match = $match
        }
        if (-not $match) {
            throw "MD5 mismatch."
        }
        break
    }
}
