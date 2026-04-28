param(
  [Parameter(Mandatory = $true)]
  [string]$SourcePath,

  [Parameter(Mandatory = $true)]
  [string]$RemoteObject,

  [string]$ManifestOut = ""
)

$ErrorActionPreference = "Stop"

$resolved = (Resolve-Path -LiteralPath $SourcePath).Path
$parent = Split-Path -Parent $resolved
$leaf = Split-Path -Leaf $resolved

$items = Get-ChildItem -LiteralPath $resolved -Recurse -Force -File -ErrorAction SilentlyContinue
$fileCount = ($items | Measure-Object).Count
$byteCount = [int64](($items | Measure-Object Length -Sum).Sum)

$manifest = [pscustomobject]@{
  schema = "scbe_stream_cloud_archive_manifest_v1"
  source_path = $resolved
  remote_object = $RemoteObject
  file_count = $fileCount
  byte_count = $byteCount
  started_at = (Get-Date -Format o)
  completed_at = $null
  tar_exit_code = $null
  rclone_exit_code = $null
  remote_size_bytes = $null
  remote_present = $false
}

if ($ManifestOut) {
  $manifest | ConvertTo-Json -Depth 4 | Set-Content -Path $ManifestOut -Encoding UTF8
}

# PowerShell cannot pipe Start-Process stdout handles cleanly here, so use a native command pipeline.
& tar.exe -C $parent -czf - $leaf | & rclone.exe rcat $RemoteObject --stats 30s --stats-one-line --log-level INFO
$rcloneExit = $LASTEXITCODE

$remoteSize = $null
$remotePresent = $false
if ($rcloneExit -eq 0) {
  $sizeText = & rclone.exe size $RemoteObject --json 2>$null
  if ($LASTEXITCODE -eq 0 -and $sizeText) {
    $sizeJson = $sizeText | ConvertFrom-Json
    $remoteSize = [int64]$sizeJson.bytes
    $remotePresent = ($sizeJson.count -ge 1 -and $remoteSize -gt 0)
  }
}

$manifest.completed_at = (Get-Date -Format o)
$manifest.rclone_exit_code = $rcloneExit
$manifest.remote_size_bytes = $remoteSize
$manifest.remote_present = $remotePresent

if ($ManifestOut) {
  $manifest | ConvertTo-Json -Depth 4 | Set-Content -Path $ManifestOut -Encoding UTF8
}

if (-not $remotePresent) {
  exit 2
}
exit $rcloneExit
