param(
    [string]$Root = "C:/Users/issda",
    [int]$TopN = 30,
    [string]$OutDir = "artifacts/system-audit"
)

$ErrorActionPreference = "Stop"

function SizeGB([string]$Path) {
    if (!(Test-Path $Path)) { return 0 }
    $sum = Get-ChildItem -LiteralPath $Path -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum
    return [Math]::Round(($sum.Sum / 1GB), 3)
}

$repo = "C:/Users/issda/SCBE-AETHERMOORE"
$outPath = Join-Path $repo $OutDir
New-Item -ItemType Directory -Force $outPath | Out-Null

$rows = Get-ChildItem -LiteralPath $Root -Directory -Force -ErrorAction SilentlyContinue |
    ForEach-Object { [PSCustomObject]@{ name=$_.Name; path=$_.FullName; gb=SizeGB $_.FullName } } |
    Sort-Object gb -Descending |
    Select-Object -First $TopN

$json = Join-Path $outPath "profile_disk_audit.json"
$md = Join-Path $outPath "profile_disk_audit.md"

$payload = [PSCustomObject]@{
  timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
  root = $Root
  top = $rows
}
$payload | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $json

$lines = @('# Profile Disk Audit','',"- root: $Root", "- timestamp_utc: $($payload.timestamp_utc)",'','| Name | GB |','|---|---:|')
foreach($r in $rows){ $lines += "| $($r.name) | $($r.gb) |" }
$lines -join "`n" | Set-Content -Encoding UTF8 $md

Write-Host "Wrote: $json"
Write-Host "Wrote: $md"
