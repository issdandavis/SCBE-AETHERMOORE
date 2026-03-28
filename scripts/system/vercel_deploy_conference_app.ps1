<#
.SYNOPSIS
  Safe, official Vercel deploy for SCBE conference-app.

.DESCRIPTION
  This script uses the official Vercel CLI via `npx vercel@latest`.
  It does NOT tar and POST your project to any third-party endpoint.

  Optional: if $env:VERCEL_TOKEN is not set, it will attempt to resolve it from
  the SCBE DPAPI key mirror (if installed) under service name `vercel`.

.PARAMETER Prod
  Deploy to production (`vercel deploy --prod`).

.PARAMETER Yes
  Pass `--yes` to Vercel CLI (non-interactive). Requires existing auth/link.

.PARAMETER Login
  Run `vercel login` before deploy (interactive).
#>

param(
  [switch]$Prod,
  [switch]$Yes,
  [switch]$Login
)

$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
  return (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
}

function Try-Resolve-VercelToken {
  if ($env:VERCEL_TOKEN) { return }

  $mirror = "C:\\Users\\issda\\.codex\\skills\\scbe-api-key-local-mirror\\scripts\\key_mirror.py"
  if (-not (Test-Path $mirror)) { return }

  try {
    $json = (python $mirror resolve --service vercel --env-out VERCEL_TOKEN 2>$null | ConvertFrom-Json)
    if ($json -and $json.ok -and $json.powershell) {
      Invoke-Expression $json.powershell
    }
  } catch {
    # Best-effort only. If token isn't stored, Vercel CLI will fall back to login.
  }
}

$repoRoot = Resolve-RepoRoot
$appDir = Join-Path $repoRoot "conference-app"
if (-not (Test-Path $appDir)) {
  throw "conference-app not found at: $appDir"
}

Try-Resolve-VercelToken

Push-Location $appDir
try {
  if ($Login) {
    npx vercel@latest login
  }

  $args = @("vercel@latest", "deploy")
  if ($Prod) { $args += "--prod" }
  if ($Yes) { $args += "--yes" }

  npx @args
} finally {
  Pop-Location
}

