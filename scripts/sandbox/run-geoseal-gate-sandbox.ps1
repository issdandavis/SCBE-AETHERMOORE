<#
  Build + run the GeoSeal gate sandbox in a throwaway container (Windows).

  Anything a test passes through the gate only ever touches this container,
  removed on exit (--rm). Network disabled, all caps dropped, no privilege
  escalation. Pass extra args to override the default command.
#>
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repo
$image = "scbe-geoseal-gate-sandbox"

Write-Host "[sandbox] building $image ..."
docker build -f scripts/sandbox/Dockerfile.geoseal-gate -t $image .

Write-Host "[sandbox] running (isolated: --rm --network none --cap-drop ALL) ..."
docker run --rm `
  --network none `
  --cap-drop ALL `
  --security-opt no-new-privileges `
  --pids-limit 256 `
  $image @args
