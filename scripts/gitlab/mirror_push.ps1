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
      if ($raw.StartsWith('"') -and $raw.EndsWith('"')) { return $raw.Substring(1, $raw.Length - 2) }
      if ($raw.StartsWith("'") -and $raw.EndsWith("'")) { return $raw.Substring(1, $raw.Length - 2) }
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

  function Invoke-GitSafe {
    param(
      [Parameter(Mandatory = $true)][string[]]$Args,
      [Parameter(Mandatory = $true)][string]$Secret
    )

    $out = & git @Args 2>&1
    $code = $LASTEXITCODE

    $san = $out
    if (!([string]::IsNullOrEmpty($Secret))) {
      $san = ($san -replace [regex]::Escape($Secret), "***")
    }
    # Also redact token-bearing oauth2 URLs even if the token differs or is not a direct match.
    $san = ($san -replace "oauth2:[^@]+@", "oauth2:***@")

    if ($code -ne 0) {
      $argsJoined = ($Args -join " ")
      if (!([string]::IsNullOrEmpty($Secret))) {
        $argsJoined = ($argsJoined -replace [regex]::Escape($Secret), "***")
      }
      $argsJoined = ($argsJoined -replace "oauth2:[^@]+@", "oauth2:***@")
      throw ("git " + $argsJoined + " failed (sanitized):`n" + $san)
    }
  }

  if ($PushAllBranchesAndTags) {
    Write-Host "Pushing all branches and tags to GitLab (sanitized)…"
    Invoke-GitSafe -Args @("push", $authUrl, "--all") -Secret $token
    Invoke-GitSafe -Args @("push", $authUrl, "--tags") -Secret $token
  } else {
    Write-Host "Pushing HEAD to GitLab branch '$Branch' (sanitized)…"
    Invoke-GitSafe -Args @("push", $authUrl, ("HEAD:refs/heads/" + $Branch)) -Secret $token
  }

  Write-Host "Done."
} finally {
  Pop-Location
}
