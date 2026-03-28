Param(
  [Parameter(Mandatory = $true)]
  [string]$GitLabRepoUrl,

  [string]$Branch = "main",

  [switch]$PushAllBranchesAndTags
)

$ErrorActionPreference = "Stop"

function Get-EnvValueFromDotEnvFile {
  param(
    [Parameter(Mandatory = $true)][string]$DotEnvPath,
    [Parameter(Mandatory = $true)][string]$Key
  )

  if (!(Test-Path $DotEnvPath)) {
    throw "Missing env file: $DotEnvPath"
  }

  $lines = Get-Content $DotEnvPath
  foreach ($line in $lines) {
    if ($line -match "^\s*#") { continue }
    if ($line -match "^\s*$") { continue }
    if ($line -match ("^\s*" + [regex]::Escape($Key) + "\s*=\s*(.*)\s*$")) {
      $raw = $Matches[1]
      $raw = $raw.Trim()
      if ($raw.StartsWith('\"') -and $raw.EndsWith('\"')) { return $raw.Substring(1, $raw.Length - 2) }
      if ($raw.StartsWith(\"'\") -and $raw.EndsWith(\"'\")) { return $raw.Substring(1, $raw.Length - 2) }
      return $raw
    }
  }
  return $null
}

function Add-OAuth2TokenToHttpsUrl {
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][string]$Token
  )

  # GitLab supports PAT authentication via `oauth2:<token>` over HTTPS.
  if (!($Url.StartsWith("https://"))) {
    throw "GitLabRepoUrl must be https://... (got: $Url)"
  }
  return $Url.Replace("https://", ("https://oauth2:" + $Token + "@"))
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$dotEnv = Join-Path $repoRoot "config\\connector_oauth\\.env.connector.oauth"

$token = Get-EnvValueFromDotEnvFile -DotEnvPath $dotEnv -Key "GITLAB_TOKEN"
if ([string]::IsNullOrWhiteSpace($token)) {
  throw "GITLAB_TOKEN not found in $dotEnv"
}

$authUrl = Add-OAuth2TokenToHttpsUrl -Url $GitLabRepoUrl -Token $token

Push-Location $repoRoot
try {
  $env:GIT_TERMINAL_PROMPT = "0"

  if ($PushAllBranchesAndTags) {
    Write-Host "Pushing all branches and tags to GitLab (sanitized)…"
    git push $authUrl --all | Out-Null
    git push $authUrl --tags | Out-Null
  } else {
    Write-Host "Pushing HEAD to GitLab branch '$Branch' (sanitized)…"
    git push $authUrl ("HEAD:refs/heads/" + $Branch) | Out-Null
  }

  Write-Host "Done."
} finally {
  Pop-Location
}

