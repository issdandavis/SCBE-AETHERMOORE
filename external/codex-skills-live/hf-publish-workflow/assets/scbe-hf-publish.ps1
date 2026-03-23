function scbe-hf-publish {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $true)]
    [string]$Repo,

    [string]$Dir = ".",

    [ValidateSet("model", "dataset", "space")]
    [string]$Type = "model",

    [string]$Message = "",

    [switch]$CreatePr
  )

  if (-not (Get-Command hf -ErrorAction SilentlyContinue)) {
    throw "Hugging Face CLI not found. Install it, then run: hf auth login"
  }

  if (-not (Test-Path -LiteralPath $Dir)) {
    throw "Upload directory does not exist: $Dir"
  }

  if ([string]::IsNullOrWhiteSpace($Message)) {
    $Message = "publish: $Type $(Get-Date -Format s)"
  }

  $readmePath = Join-Path $Dir "README.md"
  $prompt = @"
Create or update a Hugging Face README.md ($Type card) for SCBE-AETHERMOORE artifacts at path '$Dir'.
Include:
- Summary (kernel / governance / hyperbolic authorization)
- Intended use + limitations
- Security notes (no secrets, deterministic tests)
- Repro steps
- License + citation
- Tags: scbe, aethermoore, governance, cryptography, hyperbolic-geometry, safety
"@

  if (Get-Command codex -ErrorAction SilentlyContinue) {
    codex $prompt
  } elseif (-not (Test-Path -LiteralPath $readmePath)) {
    throw "README.md is missing in '$Dir'. Create it before upload or install Codex CLI for auto-generation."
  }

  $uploadArgs = @(
    "upload",
    $Repo,
    $Dir,
    ".",
    "--commit-message",
    $Message
  )

  switch ($Type) {
    "dataset" { $uploadArgs += "--repo-type=dataset" }
    "space" { $uploadArgs += "--repo-type=space" }
  }

  if ($CreatePr) {
    $uploadArgs += "--create-pr"
  }

  hf @uploadArgs
}
