param(
  [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'

Write-Host "[release-guard] npm run publish:prepare"
npm run publish:prepare

if (-not $SkipTests) {
  Write-Host "[release-guard] npm test"
  npm test
}

Write-Host "[release-guard] npm run publish:check:strict"
npm run publish:check:strict

Write-Host "[release-guard] complete"
