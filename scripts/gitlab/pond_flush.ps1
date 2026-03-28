Param(
  [Parameter(Mandatory = $true)]
  [string]$GitLabRepoUrl,

  [switch]$CheckGhAuth
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
      $raw = $Matches[1].Trim()
      if ($raw.StartsWith('"') -and $raw.EndsWith('"')) { return $raw.Substring(1, $raw.Length - 2) }
      if ($raw.StartsWith("'") -and $raw.EndsWith("'")) { return $raw.Substring(1, $raw.Length - 2) }
      return $raw
    }
  }
  return $null
}

function Parse-GitLabProjectPath {
  param([Parameter(Mandatory = $true)][string]$RepoUrl)

  $u = [Uri]$RepoUrl
  if ($u.Scheme -ne "https") {
    throw "GitLabRepoUrl must be https://... (got: $RepoUrl)"
  }

  $path = $u.AbsolutePath.TrimStart("/")
  if ($path.EndsWith(".git")) { $path = $path.Substring(0, $path.Length - 4) }
  $path = $path.TrimEnd("/")

  if ([string]::IsNullOrWhiteSpace($path)) {
    throw "Unable to parse project path from: $RepoUrl"
  }

  return @{
    baseUrl = ($u.Scheme + "://" + $u.Host)
    projectPath = $path
  }
}

function Safe-Write {
  param([string]$Msg)
  Write-Host $Msg
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$dotEnv = Join-Path $repoRoot "config\\connector_oauth\\.env.connector.oauth"

$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$tz = (Get-TimeZone).Id
Safe-Write ("SCBE Pond Flush @ " + $ts + " " + $tz)
Safe-Write ("RepoRoot: " + $repoRoot)

$token = Get-EnvValueFromDotEnvFile -DotEnvPath $dotEnv -Key "GITLAB_TOKEN"
if ([string]::IsNullOrWhiteSpace($token)) {
  throw "GITLAB_TOKEN not found in $dotEnv"
}

$parsed = Parse-GitLabProjectPath -RepoUrl $GitLabRepoUrl
$baseUrl = $parsed.baseUrl
$projectPath = $parsed.projectPath
$projectId = [Uri]::EscapeDataString($projectPath)

$headers = @{ "PRIVATE-TOKEN" = $token }

Safe-Write ("GitLab Host: " + $baseUrl)
Safe-Write ("Project Path: " + $projectPath)

try {
  $user = Invoke-RestMethod -Method Get -Uri ($baseUrl + "/api/v4/user") -Headers $headers
  Safe-Write ("GitLab Auth: OK (" + $user.username + ")")
} catch {
  throw ("GitLab Auth: FAIL (token invalid/expired, or network issue). " + $_.Exception.Message)
}

try {
  $proj = Invoke-RestMethod -Method Get -Uri ($baseUrl + "/api/v4/projects/" + $projectId) -Headers $headers
  Safe-Write ("Project: OK (id=" + $proj.id + ", visibility=" + $proj.visibility + ", default_branch=" + $proj.default_branch + ")")
} catch {
  Safe-Write ("Project: WARN (cannot access project details; check path or permissions). " + $_.Exception.Message)
}

if ($CheckGhAuth) {
  Safe-Write ""
  Safe-Write "[gh] auth status"
  try {
    gh auth status
  } catch {
    Safe-Write ("WARN: gh auth status failed. " + $_.Exception.Message)
  }
}

Safe-Write ""
Safe-Write "Pond Flush: OK"
