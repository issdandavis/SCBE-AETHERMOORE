<#
.SYNOPSIS
  Bootstrap the vendored-by-reference Hermes engine for the Aether harness.

.DESCRIPTION
  Clones the pinned upstream commit, applies our reasoning_content patch,
  creates a Python 3.12 venv, installs deps, and installs the SCBE governance
  plugin. Idempotent-ish: re-running with an existing clone skips the clone and
  re-applies the patch/plugin only if needed.

.PARAMETER Dest
  Where to put the clone. Default: C:\Users\issda\harness-study\hermes-agent

.EXAMPLE
  pwsh ./bootstrap_hermes.ps1
  pwsh ./bootstrap_hermes.ps1 -Dest D:\engines\hermes
#>
param(
  [string]$Dest = "C:\Users\issda\harness-study\hermes-agent"
)

$ErrorActionPreference = "Stop"
$Pin    = "a72bb03757c0c925c686f9774eefc8dc5a77b329"
$Repo   = "https://github.com/NousResearch/Hermes-Agent"
$Here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Pkg    = (Resolve-Path (Join-Path $Here "..\..")).Path          # packages/aether-harness
$Patch  = Join-Path $Pkg "patches\0001-strip-reasoning-content-on-replay.patch"
$Plugin = Join-Path $Pkg "hermes_plugin"

Write-Host "== Aether harness: bootstrap Hermes @ $($Pin.Substring(0,8)) -> $Dest"

if (-not (Test-Path (Join-Path $Dest ".git"))) {
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Dest) | Out-Null
  git clone --no-checkout $Repo $Dest
  git -C $Dest checkout $Pin
} else {
  Write-Host "   clone exists; checking out pin"
  git -C $Dest fetch --depth 1 origin $Pin 2>$null
  git -C $Dest checkout $Pin
}

# Apply our patch only if it isn't already applied.
if (git -C $Dest apply --reverse --check $Patch 2>$null) {
  Write-Host "   patch already applied"
} else {
  git -C $Dest apply $Patch
  Write-Host "   patch applied: 0001-strip-reasoning-content-on-replay"
}

# Python 3.12 venv (upstream is 3.14-incompatible).
$Venv = Join-Path $Dest ".venv"
if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) {
  if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv venv --python 3.12 $Venv
  } else {
    py -3.12 -m venv $Venv
  }
}
$Py = Join-Path $Venv "Scripts\python.exe"
& $Py -m pip install --quiet -e $Dest
& $Py -m pip install --quiet "numpy>=2"   # required by the SCBE governance gate

# Install the governance plugin into the clone's bundled plugins dir.
$PluginDest = Join-Path $Dest "plugins\scbe-governance"
New-Item -ItemType Directory -Force -Path $PluginDest | Out-Null
Copy-Item (Join-Path $Plugin "plugin.yaml") $PluginDest -Force
Copy-Item (Join-Path $Plugin "__init__.py") $PluginDest -Force
Write-Host "   governance plugin installed -> plugins\scbe-governance"

Write-Host ""
Write-Host "Done. Run a governed task (PowerShell):"
Write-Host "  `$env:HERMES_HOME = '$Pkg\hermes_plugin'   # dir with config.example.yaml -> rename to config.yaml"
Write-Host "  & '$Py' '$Dest\cli.py' --query '...' --provider custom --base-url <url> --api-key `$env:CEREBRAS_API_KEY --model gpt-oss-120b --toolsets 'file,code_execution' --quiet"
